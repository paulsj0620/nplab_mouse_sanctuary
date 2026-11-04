import http.client,json,threading,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts.app.server import make_server
class AccessTests(unittest.TestCase):
 def test_access(self):
  with tempfile.TemporaryDirectory() as tmp:
   s=make_server('127.0.0.1',0,str(Path(tmp)/'lab.sqlite'))
   a=s.store.create_user('qa_admin','test-password-admin',role='admin',setup=True)['id']
   b=s.store.create_user('regular','test-password-other',role='admin',actor=a)['id']
   ta,ua=s.store.login('qa_admin','test-password-admin');tb,ub=s.store.login('regular','test-password-other')
   t=threading.Thread(target=s.serve_forever,daemon=True);t.start()
   def req(path,method='GET',token=tb,csrf=ub['csrf'],body=None):
    c=http.client.HTTPConnection('127.0.0.1',s.server_port);c.request(method,path,json.dumps(body or {}) if method!='GET' else None,{'Cookie':'lab_session='+token,'X-CSRF-Token':csrf,'Content-Type':'application/json'});r=c.getresponse();result=(r.status,json.loads(r.read()));c.close();return result
   try:
    with patch('scripts.app.server.fcs_allowed',side_effect=lambda u:bool(u) and u['id']==a):
     for method,path in [('GET','library'),('GET','runs/no'),('GET','transfers/no'),('GET','source/no'),('POST','chunks/no'),('POST','transfers'),('POST','finish'),('POST','plot'),('POST','analyze'),('POST','experiment-link'),('POST','edit'),('POST','combine'),('POST','export'),('POST','import-reference'),('POST','link-reference'),('GET','workspace-files/no')]:self.assertEqual(req('/api/fcs/'+path,method)[0],403)
     self.assertNotIn('available_files',req('/api/experiments?experiment=Exp20')[1])
     self.assertFalse(req('/api/me')[1]['user']['fcs_access']);self.assertTrue(req('/api/me',token=ta)[1]['user']['fcs_access'])
     self.assertEqual(req('/api/fcs/library',token=ta)[0],200)
     self.assertNotIn('fcs_runs',req('/api/export')[1]);self.assertIn('fcs_runs',req('/api/export',token=ta)[1])
     self.assertEqual(req('/api/account','PATCH',body={'username':'qa_imposter','expected_username':'regular'})[0],200)
     self.assertEqual(req('/api/fcs/library')[0],403);self.assertEqual(req('/api/state')[0],200)
   finally:s.shutdown();s.server_close();t.join()
