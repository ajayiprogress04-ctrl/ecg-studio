import os,tempfile,time,unittest,zipfile,io
from pathlib import Path
TEMP=tempfile.TemporaryDirectory()
os.environ['ECG_DATA_DIR']=TEMP.name
os.environ['ECG_DISK_RESERVE_BYTES']='0'
from backend.app import app,jobs,cleanup,TTL
class Api(unittest.TestCase):
    def setUp(self):self.client=app.test_client()
    def create(self,name='sample.csv',size=1):
        r=self.client.post('/jobs',json={'name':name,'size':size});self.assertEqual(r.status_code,201);j=r.json
        return j,{'X-Job-Token':j['token']}
    def test_lifecycle_and_zip(self):
        data=b'# exported\nlocal_time,ecg,ecg_mV\n2026-06-18 08:52:24.000,1,0.1\n2026-06-18 14:52:24.000,2,0.2\n'
        j,h=self.create(size=len(data));p='/jobs/'+j['id'];self.assertEqual(self.client.get(p).status_code,404)
        self.assertEqual(self.client.post(p+'/start',headers=h).status_code,409)
        mid=len(data)//2
        for start,end in [(0,mid),(mid,len(data))]:
            r=self.client.put(p+'/upload',data=data[start:end],headers={**h,'X-Upload-Offset':str(start)},content_type='application/octet-stream');self.assertEqual(r.status_code,200)
        self.assertEqual(self.client.put(p+'/upload',data=b'x',headers={**h,'X-Upload-Offset':'0'}).status_code,409)
        self.assertEqual(self.client.post(p+'/start',headers=h).status_code,202)
        for _ in range(200):
            state=self.client.get(p,headers=h).json
            if state['state'] in ('complete','failed'):break
            time.sleep(.01)
        self.assertEqual(state['state'],'complete');self.assertEqual(len(state['outputs']),2)
        response=self.client.post(p+'/download/results.zip',data={'token':j['token']});self.assertEqual(response.status_code,200)
        with zipfile.ZipFile(io.BytesIO(response.data)) as z:self.assertEqual(len(z.namelist()),2)
        response.close()
        self.assertEqual(self.client.post(p+'/download/fake.csv',data={'token':j['token']}).status_code,404)
        self.assertEqual(self.client.delete(p,headers=h).status_code,200)
    def test_validation(self):
        self.assertEqual(self.client.post('/jobs',json={'name':'x.exe','size':5}).status_code,400)
        self.assertEqual(self.client.post('/jobs',json={'name':'x.csv','size':0}).status_code,400)
        self.assertEqual(self.client.post('/jobs',json={'name':'x.csv','size':2**50}).status_code,413)
    def test_failure_cleans_input(self):
        data=b'header\ninvalid,1,2\n';j,h=self.create(size=len(data));p='/jobs/'+j['id']
        self.client.put(p+'/upload',data=data,headers={**h,'X-Upload-Offset':'0'});self.client.post(p+'/start',headers=h)
        for _ in range(200):
            state=self.client.get(p,headers=h).json
            if state['state']=='failed' and not (Path(TEMP.name)/j['id']/'input.csv').exists():break
            time.sleep(.01)
        self.assertEqual(state['state'],'failed');self.assertFalse((Path(TEMP.name)/j['id']/'input.csv').exists());self.client.delete(p,headers=h)
    def test_expiry_and_cors(self):
        j,h=self.create();jobs[j['id']]['touched']=time.time()-TTL-10;cleanup()
        self.assertEqual(self.client.get('/jobs/'+j['id'],headers=h).status_code,404)
        r=self.client.options('/jobs',headers={'Origin':'http://localhost:8000'});self.assertEqual(r.headers['Access-Control-Allow-Origin'],'http://localhost:8000')
        r=self.client.get('/health',headers={'Origin':'https://other.example'});self.assertNotIn('Access-Control-Allow-Origin',r.headers)

    def test_same_filename_isolation(self):
        first,h1=self.create(name='same.csv');second,h2=self.create(name='same.csv')
        self.assertNotEqual(first['id'],second['id'])
        self.assertEqual(self.client.get('/jobs/'+first['id'],headers=h2).status_code,404)
        self.client.delete('/jobs/'+first['id'],headers=h1)
        self.client.delete('/jobs/'+second['id'],headers=h2)
