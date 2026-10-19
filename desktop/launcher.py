"""Starts ECG Studio on a random loopback port; no hosted service or internet required."""
import ctypes
import os
from pathlib import Path
import sys
import threading
import time
import webbrowser


def main():
    if os.name=='nt':ctypes.windll.kernel32.SetConsoleTitleW('ECG Studio — keep open while processing')
    from waitress import create_server
    from desktop.service import create_app
    app=create_app()
    if '--self-test' in sys.argv:
        import tempfile
        from backend.splitter import split_ecg
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'sample.csv'
            source.write_text('local_time,ecg,ecg_mV\n2026-06-18 08:52:24.000,1,0.1\n2026-06-18 14:52:24.000,2,0.2\n',encoding='utf-8')
            result=split_ecg(source,Path(temp)/'outputs')
            assert result['valid_rows']==2 and len(result['outputs'])==2
            app.config['DESKTOP_HOST']='localhost'
            with app.test_client() as client:
                page=client.get('/')
                assert page.status_code==200 and b'__SESSION_TOKEN__' not in page.data
                assert client.get('/assets/favicon.png').status_code==200
        app.desktop_executor.shutdown(wait=True)
        return
    server=create_server(app,host='127.0.0.1',port=0,threads=6,clear_untrusted_proxy_headers=True)
    port=server.effective_port
    app.config['DESKTOP_HOST']=f'127.0.0.1:{port}'
    thread=threading.Thread(target=server.run,daemon=True);thread.start()
    url=f'http://127.0.0.1:{port}/'
    print('ECG Studio is running locally. Your recordings are not uploaded.')
    print('If a browser does not open automatically, open: '+url)
    print('Keep this window open. Use Close application inside ECG Studio to exit.')
    webbrowser.open(url)
    try:
        while not app.desktop_stop.wait(.5):pass
        time.sleep(.5)
    except KeyboardInterrupt:
        # Do not tear down a worker in the middle of writing a CSV.
        while app.desktop_state['busy']:
            app.desktop_state['cancel_requested']=True
            time.sleep(.2)
    finally:
        app.desktop_executor.shutdown(wait=True)
        server.close()

if __name__=='__main__':
    try:main()
    except Exception as exc:
        message='ECG Studio could not start. Extract the entire ZIP into a writable folder, then double-click ECG_Studio.exe.\n\nStartup issue: '+type(exc).__name__
        print(message)
        if os.name=='nt':ctypes.windll.user32.MessageBoxW(0,message,'ECG Studio',0x10)
        sys.exit(1)
