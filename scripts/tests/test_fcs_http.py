import http.client,json,threading,tempfile,unittest
from pathlib import Path
from scripts.app.server import make_server
class FCSHTTPTests(unittest.TestCase):
 def test_binary_upload_csrf_owner_download_and_immutable_bytes(self):
  with tempfile.TemporaryDirectory() as tmp:
   s=make_server('127.0.0.1',0,str(Path(tmp)/'lab.sqlite'));a=s.store.create_user('a','test-password-a',role='admin',setup=True)['id'];s.store.create_user('b','test-password-b',actor=a)
   ta,ua=s.store.login('a','test-password-a');tb,ub=s.store.login('b','test-password-b');thread=threading.Thread(target=s.serve_forever,daemon=True);thread.start()
   def req(path,body=None,method='GET',token=ta,csrf=ua['csrf'],binary=False):
    c=http.client.HTTPConnection('127.0.0.1',s.server_port);headers={'Cookie':'lab_session='+token,'X-CSRF-Token':csrf,'Content-Type':'application/octet-stream' if binary else 'application/json'}
    c.request(method,path,body if binary else json.dumps(body) if body is not None else None,headers);r=c.getresponse();b=r.read();status=r.status;c.close();return status,b
   try:
    status,body=req('/api/fcs/transfers',{'filename':'fixture.fcs','size':9},'POST');self.assertEqual(status,201);tid=json.loads(body)['id']
    path='/api/fcs/chunks/'+tid+'?offset=0'
    self.assertEqual(req(path,b'FCS3.0abc','POST',csrf='invalid',binary=True)[0],403)
    self.assertEqual(req(path,b'FCS3.0abc','POST',token=tb,csrf=ub['csrf'],binary=True)[0],404)
    self.assertEqual(req(path,b'FCS3.0abc','POST',binary=True)[0],200)
    status,body=req('/api/fcs/finish',{'id':tid},'POST');self.assertEqual(status,200);fid=json.loads(body)['id']
    self.assertEqual(req('/api/fcs/source/'+fid,token=tb)[1],b'FCS3.0abc')
    self.assertEqual(req('/api/fcs/source/'+fid,token='')[0],401)
   finally:s.shutdown();s.server_close();thread.join()
