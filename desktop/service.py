"""Loopback-only desktop service. Recording data never leaves this computer."""
import base64
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException
from backend.splitter import split_ecg
from desktop.diagnostics import InsufficientSpace, NoValidRows, describe_failure

ROOT=Path(__file__).resolve().parents[1]

class Cancelled(Exception):pass

def windows_dialog(kind):
    if os.name!='nt':raise RuntimeError('Windows file dialogs require Windows.')
    # Static script; user-selected paths are returned as base64 JSON, never shell code.
    setup="""Add-Type -AssemblyName System.Windows.Forms
$owner = New-Object System.Windows.Forms.Form
$owner.TopMost = $true
$owner.ShowInTaskbar = $false
$owner.Width = 1
$owner.Height = 1
$owner.StartPosition = 'CenterScreen'
"""
    if kind=='files':
        script=setup+"""$d = New-Object System.Windows.Forms.OpenFileDialog
$d.Title = 'Choose ECG CSV recordings'
$d.Filter = 'CSV recordings (*.csv)|*.csv'
$d.Multiselect = $true
if ($d.ShowDialog($owner) -eq 'OK') { $value = @($d.FileNames) } else { $value = @() }
$json = ConvertTo-Json -InputObject $value -Compress
"""
    else:
        script=setup+"""$d = New-Object System.Windows.Forms.FolderBrowserDialog
$d.Description = 'Choose where ECG Studio should save the split files'
$d.ShowNewFolderButton = $true
if ($d.ShowDialog($owner) -eq 'OK') { $value = $d.SelectedPath } else { $value = '' }
$json = ConvertTo-Json -InputObject $value -Compress
"""
    script+="""[Console]::Write([Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json)))
$d.Dispose()
$owner.Dispose()
"""
    result=subprocess.run(['powershell.exe','-NoProfile','-STA','-Command',script],
        capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:raise RuntimeError('Windows could not open the file picker.')
    return json.loads(base64.b64decode(result.stdout.strip()).decode('utf-8'))


def create_app(dialog=windows_dialog,opener=None):
    app=Flask(__name__,static_folder=None)
    app.config['MAX_CONTENT_LENGTH']=16384
    token=secrets.token_urlsafe(32)
    lock=threading.RLock()
    picker_lock=threading.Lock()
    executor=ThreadPoolExecutor(max_workers=1)
    state={'busy':False,'files':[],'output_root':'','batch_folder':'','jobs':[],
           'cancel_requested':False,'finished':False}
    settings_path=None
    if os.name=='nt' and os.environ.get('LOCALAPPDATA'):
        settings_path=Path(os.environ['LOCALAPPDATA'])/'ECG Studio'/'preferences.json'
    state['theme']='light'
    if settings_path and settings_path.is_file():
        try:
            saved=json.loads(settings_path.read_text(encoding='utf-8'))
            if saved.get('theme') in ('light','dark','colored'):state['theme']=saved['theme']
        except (OSError,ValueError):pass
    selected=[]
    stop_event=threading.Event()
    app.desktop_state=state
    app.desktop_executor=executor
    app.desktop_stop=stop_event
    app.desktop_token=token
    app.config['DESKTOP_HOST']='127.0.0.1:0'
    def open_folder(path):
        if opener:opener(path)
        elif os.name=='nt':os.startfile(str(path))
        else:raise RuntimeError('Opening folders requires Windows.')

    @app.before_request
    def guard():
        host=app.config['DESKTOP_HOST']
        if request.host!=host:return jsonify(error='Unknown local host.'),403
        origin=request.headers.get('Origin')
        if origin and origin!='http://'+host:return jsonify(error='Only this local app can make this request.'),403
        if request.path.startswith('/api/') and not secrets.compare_digest(request.headers.get('X-Desktop-Token',''),token):
            return jsonify(error='Reopen ECG Studio from its launcher.'),403

    @app.after_request
    def headers(r):
        r.headers['Cache-Control']='no-store'
        r.headers['X-Content-Type-Options']='nosniff'
        r.headers['Referrer-Policy']='no-referrer'
        r.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        return r

    @app.errorhandler(Exception)
    def error(exc):
        if isinstance(exc,HTTPException):return jsonify(error=exc.description),exc.code
        return jsonify(error='The operation failed. Check folder access and available disk space, then retry.'),500

    @app.get('/')
    def index():
        html=(ROOT/'frontend/index.html').read_text(encoding='utf-8').replace('__SESSION_TOKEN__',token)
        return app.response_class(html,mimetype='text/html')

    @app.get('/<path:name>')
    def assets(name):return send_from_directory(ROOT/'frontend',name)

    @app.get('/api/state')
    def get_state():
        with lock:return jsonify(state)

    @app.post('/api/theme')
    def theme():
        value=(request.get_json(silent=True) or {}).get('theme')
        if value not in ('light','dark','colored'):return jsonify(error='Unknown theme.'),400
        with lock:
            state['theme']=value
            if settings_path:
                try:
                    settings_path.parent.mkdir(parents=True,exist_ok=True)
                    settings_path.write_text(json.dumps({'theme':value}),encoding='utf-8')
                except OSError:pass
        return get_state()

    @app.post('/api/choose-files')
    def choose_files():
        with picker_lock:
            with lock:
                if state['busy']:return jsonify(error='A batch is running.'),409
            paths=dialog('files')
            if isinstance(paths,str):paths=[paths]
            if not paths:return get_state()
            items=[];seen=set()
            for value in paths:
                p=Path(value).resolve()
                if p in seen:continue
                seen.add(p)
                if not p.is_file() or p.suffix.lower()!='.csv':
                    return jsonify(error='Choose existing CSV files.'),400
                if p.stat().st_size==0:return jsonify(error='An empty recording was selected.'),400
                items.append({'name':p.name,'path':str(p),'bytes':p.stat().st_size})
            with lock:
                selected.clear();selected.extend(Path(x['path']) for x in items)
                state['files']=items
            return get_state()

    @app.post('/api/choose-folder')
    def choose_folder():
        with picker_lock:
            with lock:
                if state['busy']:return jsonify(error='A batch is running.'),409
            value=dialog('folder')
            if not value:return get_state()
            p=Path(value).resolve()
            if not p.is_dir():return jsonify(error='Choose an existing output folder.'),400
            try:
                probe=p/('.ecg-write-check-'+secrets.token_hex(8))
                with probe.open('x'):pass
                probe.unlink()
            except OSError:return jsonify(error='This folder is not writable. Choose another folder.'),400
            with lock:state['output_root']=str(p)
            return get_state()

    @app.post('/api/clear')
    def clear():
        with lock:
            if state['busy']:return jsonify(error='A batch is running.'),409
            selected.clear();state['files']=[]
        return get_state()

    def run_batch(inputs,batch_folder):
        try:
            for i,p in enumerate(inputs):
                with lock:
                    if state['cancel_requested']:
                        for remaining in state['jobs'][i:]:remaining.update(status='cancelled',message='Not processed; batch stopped.')
                        break
                    job=state['jobs'][i];job.update(status='processing',message='Reading recording…')
                name=re.sub(r'[^\w .-]','_',p.stem)[:70].strip(' .') or 'recording'
                dest=batch_folder/f'{i+1:03d}_{name}'
                try:
                    # Input stays at its original path. New output folders prevent overwrites.
                    required=p.stat().st_size*6+256*1024**2
                    available=shutil.disk_usage(batch_folder).free
                    if available < required:
                        raise InsufficientSpace(required,available,'before processing')
                    def report(**values):
                        with lock:
                            if state['cancel_requested']:raise Cancelled()
                            job.update(values)
                        available=shutil.disk_usage(batch_folder).free
                        if available < 128*1024**2:raise InsufficientSpace(128*1024**2,available,'during processing')
                    result=split_ecg(p,dest,report)
                    with lock:
                        if state['cancel_requested']:raise Cancelled()
                    if not result['outputs']:raise NoValidRows()
                    with lock:job.update(result,status='complete',folder=str(dest),message='Saved successfully.')
                except Cancelled:
                    shutil.rmtree(dest,ignore_errors=True)
                    with lock:job.update(status='cancelled',message='Stopped. Incomplete output removed.')
                except Exception as error:
                    shutil.rmtree(dest,ignore_errors=True)
                    with lock:job.update(status='failed',**describe_failure(error))
            with lock:
                summary={k:v for k,v in state.items() if k not in ('busy','cancel_requested')}
            try:(batch_folder/'ECG_Studio_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
            except OSError:pass
        finally:
            try:(batch_folder/'INCOMPLETE.txt').unlink(missing_ok=True)
            except OSError:pass
            with lock:state.update(busy=False,finished=True)

    @app.post('/api/start')
    def start():
        with picker_lock,lock:
            if state['busy']:return jsonify(error='A batch is already running.'),409
            if not selected:return jsonify(error='Choose at least one CSV recording.'),400
            if not state['output_root']:return jsonify(error='Choose an output folder first.'),400
            batch_folder=Path(state['output_root'])/('ECG_Studio_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+secrets.token_hex(3))
            try:
                batch_folder.mkdir()
                (batch_folder/'INCOMPLETE.txt').write_text('This batch did not finish. Do not treat partial CSV files as complete. Rerun the original recordings into a fresh batch folder.\n',encoding='utf-8')
            except OSError:return jsonify(error='Cannot create output folder. Choose another location.'),400
            state.update(busy=True,finished=False,cancel_requested=False,batch_folder=str(batch_folder),
                         jobs=[{'name':p.name,'status':'queued','message':'Waiting…'} for p in selected])
            executor.submit(run_batch,list(selected),batch_folder)
            return jsonify(state),202

    @app.post('/api/cancel')
    def cancel():
        with lock:
            if state['busy']:state['cancel_requested']=True
        return get_state()

    @app.post('/api/open-folder')
    def open_output():
        with lock:
            index=(request.get_json(silent=True) or {}).get('index')
            if type(index) is int and 0<=index<len(state['jobs']):
                folder=state['jobs'][index].get('folder')
            elif index is None:folder=state['batch_folder'] or state['output_root']
            else:return jsonify(error='Unknown output folder.'),400
        if not folder or not Path(folder).is_dir():return jsonify(error='Output folder unavailable.'),404
        try:open_folder(Path(folder))
        except Exception:return jsonify(error='Windows could not open this folder. Use the displayed folder path.'),500
        return jsonify(opened=True)

    @app.post('/api/quit')
    def quit_app():
        with lock:
            if state['busy']:return jsonify(error='Stop the batch and wait for it to finish before closing.'),409
            stop_event.set()
        return jsonify(closed=True)

    return app
