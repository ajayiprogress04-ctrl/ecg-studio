import json
import os
from pathlib import Path
import shutil
import threading
import time
import secrets
import zipfile
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, request, jsonify, send_file
from werkzeug.exceptions import HTTPException
from backend.splitter import split_ecg

ROOT = Path(os.environ.get("ECG_DATA_DIR", "./private-jobs")).resolve()
ROOT.mkdir(parents=True, exist_ok=True)
MAX_FILE = int(os.environ.get("ECG_MAX_FILE_BYTES", 20 * 1024**3))
MAX_JOBS = int(os.environ.get("ECG_MAX_JOBS", 8))
TTL = int(os.environ.get("ECG_RETENTION_SECONDS", 86400))
RESERVE = int(os.environ.get("ECG_DISK_RESERVE_BYTES", 1024**3))
ORIGIN = os.environ.get("ECG_FRONTEND_ORIGIN", "http://localhost:8000")
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024**2
lock = threading.RLock()
executor = ThreadPoolExecutor(max_workers=1)
jobs = {}


def persist(j):
    p = ROOT / j["id"] / "job.json"
    p.with_suffix(".tmp").write_text(json.dumps(j))
    p.with_suffix(".tmp").replace(p)


for folder in ROOT.iterdir():
    if folder.is_dir() and (folder / "job.json").exists():
        try:
            j = json.loads((folder / "job.json").read_text())
            if j["state"] in ("queued", "processing", "packaging"):
                j.update(state="failed", error="The processing service restarted. Delete this job and upload again.")
                (folder/"input.csv").unlink(missing_ok=True)
                shutil.rmtree(folder/"outputs", ignore_errors=True)
                (folder/"results.zip").unlink(missing_ok=True)
            jobs[j["id"]] = j
            persist(j)
        except (ValueError, KeyError, OSError):
            pass


def cleanup():
    with lock:
        now = time.time()
        for key, j in list(jobs.items()):
            if j["state"] not in ("queued", "processing", "packaging") and now-j["touched"] > TTL:
                shutil.rmtree(ROOT/key, ignore_errors=True)
                del jobs[key]


def sweeper():
    while True:
        time.sleep(60)
        cleanup()

threading.Thread(target=sweeper, daemon=True).start()


def authorize(key):
    j = jobs.get(key)
    if not j or not secrets.compare_digest((request.form.get("token", "") if request.endpoint == "download" else request.headers.get("X-Job-Token", "")), j["token"]):
        return None
    j["touched"] = time.time()
    return j


@app.after_request
def headers(response):
    if request.headers.get("Origin") == ORIGIN:
        response.headers["Access-Control-Allow-Origin"] = ORIGIN
        response.headers["Vary"] = "Origin"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Job-Token, X-Upload-Offset"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.errorhandler(Exception)
def error(exc):
    if isinstance(exc, HTTPException):
        return jsonify(error=exc.description), exc.code
    # Never return parser exceptions: they may contain recording data.
    return jsonify(error="The operation failed. Check service storage and retry."), 500


@app.get("/health")
def health():
    return jsonify(status="ok", max_file_bytes=MAX_FILE, max_chunk_bytes=8*1024**2,
                   retention_seconds=TTL, max_jobs=MAX_JOBS)


@app.post("/jobs")
def create():
    payload = request.get_json()
    name = str(payload.get("name", ""))
    size = payload.get("size")
    if not name.lower().endswith(".csv") or type(size) is not int or size <= 0:
        return jsonify(error="Select a nonempty .csv file."), 400
    if size > MAX_FILE:
        return jsonify(error="This file exceeds the processing service's configured file-size limit."), 413
    cleanup()
    with lock:
        if len(jobs) >= MAX_JOBS:
            return jsonify(error="Job capacity reached. Delete finished jobs or wait for expiry."), 429
        # Reserve room for other uploads, expanded CSV output and a ZIP copy.
        outstanding = sum(j["size"]*8 for j in jobs.values() if j["state"] != "complete")
        if shutil.disk_usage(ROOT).free < size*8 + outstanding + RESERVE:
            return jsonify(error="Insufficient disk capacity for this recording and its outputs."), 507
        key = secrets.token_hex(16)
        (ROOT/key).mkdir(mode=0o700)
        j = dict(id=key, token=secrets.token_urlsafe(32), name=Path(name).name,
                 size=size, offset=0, state="uploading", touched=time.time())
        jobs[key] = j
        persist(j)
        return jsonify(j), 201


@app.route("/jobs/<key>", methods=["GET", "DELETE"])
def job(key):
    with lock:
        j = authorize(key)
        if j is None:
            return jsonify(error="Job unavailable or expired."), 404
        if request.method == "DELETE":
            if j["state"] in ("queued", "processing", "packaging"):
                return jsonify(error="Wait for processing to finish before deleting this job."), 409
            shutil.rmtree(ROOT/key)
            del jobs[key]
            return jsonify(deleted=True)
        return jsonify({k:v for k,v in j.items() if k != "token"})


@app.put("/jobs/<key>/upload")
def upload(key):
    with lock:
        j = authorize(key)
        if j is None:
            return jsonify(error="Job unavailable or expired."), 404
        if j["state"] != "uploading":
            return jsonify(error="This job is no longer accepting uploads."), 409
        try:
            offset = int(request.headers.get("X-Upload-Offset", "-1"))
        except ValueError:
            offset = -1
        if offset != j["offset"]:
            return jsonify(error="Upload offset differs. Read job status before retrying.", offset=j["offset"]), 409
        data = request.get_data()
        if not data or offset+len(data) > j["size"]:
            return jsonify(error="Invalid upload chunk length."), 400
        if shutil.disk_usage(ROOT).free < len(data)+RESERVE:
            return jsonify(error="The service has insufficient free disk space."), 507
        path = ROOT/key/"input.csv"
        with path.open("r+b" if path.exists() else "w+b") as f:
            f.seek(offset)
            f.write(data)
            f.truncate()
        j["offset"] += len(data)
        persist(j)
        return jsonify(offset=j["offset"])


def process(key):
    j = jobs[key]
    folder = ROOT/key
    try:
        with lock:
            j.update(state="processing", touched=time.time())
            persist(j)
        def report(**values):
            if shutil.disk_usage(ROOT).free < RESERVE:
                raise OSError("Insufficient disk space")
            with lock:
                j.update(values, touched=time.time())
                persist(j)
        result = split_ecg(folder/"input.csv", folder/"outputs", report)
        if not result["outputs"]:
            raise ValueError("No valid rows")
        with lock:
            j.update(result, state="packaging", touched=time.time())
            persist(j)
        with zipfile.ZipFile(folder/"results.zip", "w", zipfile.ZIP_DEFLATED, allowZip64=True) as z:
            for output in result["outputs"]:
                if shutil.disk_usage(ROOT).free < RESERVE:
                    raise OSError("Insufficient disk space")
                z.write(folder/"outputs"/output["name"], output["name"])
        with lock:
            j.update(state="complete", touched=time.time())
            persist(j)
    except Exception:
        shutil.rmtree(folder/"outputs", ignore_errors=True)
        (folder/"results.zip").unlink(missing_ok=True)
        with lock:
            j.update(state="failed", error="No downloadable result was produced. The file may contain no valid rows, use an unsupported CSV/timestamp format, or exceed available processing resources.", touched=time.time())
            j.pop("outputs", None)
            persist(j)
    finally:
        (folder/"input.csv").unlink(missing_ok=True)


@app.post("/jobs/<key>/start")
def start(key):
    with lock:
        j = authorize(key)
        if j is None:
            return jsonify(error="Job unavailable or expired."), 404
        if j["state"] != "uploading" or j["offset"] != j["size"]:
            return jsonify(error="Upload must finish before starting this job."), 409
        j.update(state="queued", touched=time.time())
        persist(j)
        executor.submit(process, key)
        return jsonify(state="queued"), 202


@app.post("/jobs/<key>/download/<name>")
def download(key, name):
    with lock:
        j = authorize(key)
        if j is None:
            return jsonify(error="Job unavailable or expired."), 404
        allowed = {o["name"] for o in j.get("outputs", [])}
        if j["state"] != "complete" or (name != "results.zip" and name not in allowed):
            return jsonify(error="Output unavailable."), 404
        # Open a handle before releasing lock, so cleanup cannot remove an unopened file.
        path = ROOT/key/("results.zip" if name == "results.zip" else "outputs/"+name)
        handle = path.open("rb")
        response = send_file(handle, as_attachment=True, download_name=name,
                             mimetype="application/zip" if name.endswith(".zip") else "text/csv")
        response.call_on_close(handle.close)
        return response


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
