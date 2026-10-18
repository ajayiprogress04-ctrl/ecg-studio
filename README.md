# ECG Studio — six-hour CSV splitter

A compact browser interface around the supplied pandas ECG-splitting workflow. The frontend is static and can be hosted on Vercel. A separately deployed Python service processes uploads. Users of the deployed app do not need Python, packages or JupyterLab.

**Status:** source packaged and automated tests passed. No GitHub repository, Vercel project or backend service has been created or deployed. Browser interaction and real-recording compatibility remain unverified. See TEST_REPORT.md.

## Contents

| Path | Purpose |
| --- | --- |
| frontend/index.html | Upload, processing and download interface |
| frontend/styles.css | Responsive ruby-accented Light/OLED/Colored themes |
| frontend/app.js | Sequential batches, chunk uploads, status and download actions |
| frontend/config.js | Public Python-service address |
| frontend/vercel.json | Static hosting response headers |
| backend/app.py | Job API, worker, downloads and cleanup |
| backend/splitter.py | Original pandas transformations and segmentation |
| reference/original_splitter.py | Unmodified supplied script, used as test oracle |
| tests/ | Generated synthetic fixtures and automated checks |
| requirements.txt | Python dependencies |
| Dockerfile | Python-service container |
| .env.example | Backend configuration reference |

## Exact input and splitting behaviour

CSV text, comma delimiter; `#` comment lines ignored. The reader retains `skiprows=1`, `header=None`, and three assigned columns: `timestamp`, `ecg_raw`, `ecg_mv`. It processes 100,000 rows per chunk. Actual Firstbeat column labels may read `local_time,ecg,ecg_mV`; the original code does not use them to choose columns.

Timestamp parsing remains `%Y-%m-%d %H:%M:%S.%f`, e.g. `2026-06-18 08:52:24.000`. The screenshot metadata uses this format; the spreadsheet display of the data timestamps is abbreviated, so exact exported data-line compatibility still needs a real-file check. The implementation does not infer or reconstruct dates from `52:24.0`.

Timestamp whitespace is stripped. Both signal columns undergo pandas numeric conversion. Rows with invalid timestamps or invalid/missing signal values are dropped. Other pandas behaviours, including numeric inference per chunk, are preserved. No additional filtering, interpolation, resampling, sorting or timezone conversion occurs. The 256 Hz metadata does not determine boundaries. Metadata comments and timezone annotations are not retained in outputs, as in the reference.

The first valid timestamp anchors the recording. Block number is `floor((timestamp - first_valid_timestamp) / 6 hours)`. A sample exactly at six hours goes into block 1. Empty windows are omitted. The final partial window is kept. Earlier out-of-order timestamps can produce negative block numbers and filenames: this is existing behaviour. Daylight-saving changes are not corrected because timestamps are parsed without a timezone, matching the source.

Files are named `ECG_00h_to_06h.csv`, `ECG_06h_to_12h.csv`, etc. Output columns are `timestamp,ecg_raw,ecg_mv,continuous_time,elapsed_time,block_number`. The plain column-header row can be counted as discarded because `skiprows=1` acts on physical lines, not the first non-comment line. No speculative header correction has been introduced.

## Approved operational changes

Every input has a fresh, random job directory; existing output folders are never reused. Chunk appends within one recording are preserved. Re-running a recording creates separate outputs instead of duplicating old rows. Batches queue independently, so identically named inputs cannot collide. Each recording has an individual ZIP and individual CSV downloads; there is no combined cross-recording ZIP. Invalid inputs fail without preventing the next recording from running. If no valid output exists, the app reports failure instead of claiming success.

## Capacity and privacy

Defaults: 20 GiB maximum input, eight retained jobs, 8 MiB per upload request, one processing worker, 24-hour inactivity retention, and a 1 GiB disk reserve. These are explicit adjustable limits, not an unlimited-capacity promise. Disk admission conservatively estimates eight times the input size for uploads, expanded outputs and ZIPs, but actual expansion varies; insufficient disk space can still fail a job safely. A small CSV can expand substantially if it has unusually short values. Hosting proxies must accept 8 MiB requests. ZIP compression adds processing time and disk usage.

Uploads travel directly from the browser to your Python host, never through Vercel Functions. Vercel documents a 4.5 MB Function request/response limit: https://vercel.com/docs/functions/limitations . The static frontend therefore does not act as an upload proxy.

The app reads small file slices in the browser and uploads sequential chunks. Brief upload retries reconcile the server offset; reloading the page does not resume a job. Processing progress shows actual chunk/row counts, without a fabricated percentage. Downloads use native browser form navigation rather than buffering a large ZIP into JavaScript memory. Browser-native downloads cannot report final saving success in the app; check the browser downloads list.

Inputs are deleted after processing or failure. Failed partial outputs are removed. Completed outputs remain for download until manual deletion or expiry. Abandoned uploads expire too. Cleanup runs about once per minute while the service runs and on new job creation; it cannot run while the host is stopped. Expired files on persistent storage are removed after the service resumes. Host snapshots/backups are outside this cleanup and must be configured for your data-retention policy.

Random per-job tokens protect status/deletion/downloads and are held in page memory. No recording values or parser stack traces are logged. Do not enable request-body logging at the proxy. There are no accounts or administrator login: job creation is reachable by anyone who can reach the API. Use an institution-controlled/private deployment for sensitive recordings; CORS is not authentication or a network firewall. Access controls and clinical/regulatory suitability have not been assessed. This tool splits data and makes no diagnostic interpretation.

## Developer local setup

These commands are for the developer, not app users. Use Python 3.12, and open a terminal in this extracted project folder.

```sh
python -m venv .venv
```

Activate on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Or on macOS/Linux:

```sh
source .venv/bin/activate
```

Install and start the backend:

```sh
python -m pip install -r requirements.txt
python -m backend.app
```

Leave it running. In a second terminal:

```sh
python -m http.server 8000 --directory frontend
```

Open http://localhost:8000 . Keep the hostname `localhost` consistently: the default allowed origin is exactly `http://localhost:8000`. Local defaults write temporary jobs to `private-jobs`, which is excluded from Git. The frontend already points to http://localhost:5000 . This HTTP configuration is local testing only; hosted services should use HTTPS.

Run tests from the project folder:

```sh
python -W ignore::ResourceWarning -m unittest discover -s tests -v
node --check frontend/app.js
```

Node is only needed for this optional JavaScript syntax check, not serving the frontend. The ignored warnings come from open file handles in the unchanged reference script.

## GitHub setup

1. Create a new **private** empty repository named `ecg-splitter` on GitHub. Do not add a generated README there because this project already contains one.
2. Open this project directory in GitHub Desktop. Use **File → Add local repository**; if it is not yet a repository, use the offered **create a repository here** action.
3. Review the changed files. Include source, requirements, Dockerfile and documentation. Never include ECG exports, private job folders or secrets.
4. Commit with a message such as `Add ECG splitter and equivalence tests`.
5. Publish to your account, preserving private visibility. Alternatively, use these commands with your actual repository URL:

```sh
git init
git add .
git commit -m "Add ECG splitter and equivalence tests"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/ecg-splitter.git
git push -u origin main
```

No GitHub actions have been performed on your behalf.

## Deploy the Python backend first

Use a persistent Python/container service. One practical route is a Render Docker Web Service. Provider plans and capacity must suit your actual recordings; no plan or paid resource has been selected here.

1. In Render, choose **New → Web Service**, connect your GitHub repository and select the Docker runtime. Use the project root as the service root and `Dockerfile` as the Dockerfile path.
2. Configure a persistent disk mounted at `/data`, with enough usable space for the admission estimate and all retained jobs. The container user must have write permission there. Configure the disk/provider permissions if startup reports a permission error.
3. Set `PORT=5000`, `ECG_DATA_DIR=/data/ecg-jobs`, and an initial `ECG_FRONTEND_ORIGIN` of your intended Vercel HTTPS origin. Set the file/job/retention limits from `.env.example` to match your storage allocation. This example file is documentation; the app does not automatically load it.
4. Keep exactly **one service instance and one Gunicorn worker**. The bundled Dockerfile starts a threaded HTTP server and one background processor. Multiple workers/replicas cannot share this in-memory queue safely.
5. Set the health-check path to `/health`, deploy, and record the returned HTTPS address. Open `<backend-url>/health` to confirm JSON containing `status: ok`.
6. Do not redeploy during processing. A restarted worker marks interrupted processing jobs failed; upload state and completed outputs can survive only when the disk persists. The interface does not provide cross-page session recovery.
7. Confirm the host/proxy allows 8 MiB request bodies and native streaming downloads. Run a synthetic smoke test before any sensitive data. Backend hosting has not been tested here.

Provider references: https://render.com/docs/docker , https://render.com/docs/disks , https://render.com/docs/web-services . Render persistent disks are attached to paid services; do not assume a free ephemeral service can retain large recordings. Snapshots can retain data beyond application deletion.

## Deploy the frontend to Vercel

1. Edit `frontend/config.js`: replace `http://localhost:5000` with the backend's actual HTTPS address. This address is public configuration; no API secret belongs here.
2. Commit and push the change.
3. In Vercel, create/import a project from this GitHub repository.
4. Set **Root Directory** to `frontend`; use the static/Other preset, no build command and no install command. Serve the root directory as the output directory (`.` if requested).
5. Deploy. Record the Vercel HTTPS origin, without a trailing slash.
6. Update the backend environment variable `ECG_FRONTEND_ORIGIN` to that exact origin, then redeploy/restart the backend while no jobs are running.
7. Open the Vercel site and expand **Service connection & privacy**. Confirm it reports Connected.
8. Process a small synthetic CSV first. Inspect output names, six-hour boundaries and downloaded row values. Then try a de-identified representative recording, followed by progressively larger files. Compare with the original script run into an empty output folder using the pinned pandas version.
9. Check mobile layout, keyboard access, themes, file selection, upload retries, individual downloads, ZIP downloads and deletion. These browser checks have not yet been completed.

A successful Vercel frontend deployment does **not** deploy the Python service. No secret frontend environment variables are needed by this buildless app. Backend settings belong in the backend host's environment dashboard.

## Updating safely

Keep synthetic equivalence tests passing before pushing a processing change. Avoid changing pandas versions without rechecking outputs; numeric inference and CSV serialization may change. Preserve the original reference script. Deploy outside active jobs, inspect `/health`, check the service connection and repeat a synthetic smoke test. Never commit real ECG recordings as regression fixtures.

## Known limits

No unlimited capacity, folder import, server-side batch-wide archive, active-job cancellation, durable external queue, or refresh/session recovery. Browser processing and full real-file checks are outstanding. Errors intentionally avoid parser exception text because it can reveal raw data; the UI reports broad format/resource causes rather than claiming an exact diagnosis. Large-scale concurrency needs a different queue/storage design. This is a single-instance implementation for the requested simple workflow.
