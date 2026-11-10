import tempfile,unittest,sqlite3,threading,http.client,json
from pathlib import Path
from scripts.app.service import Store,Problem
from scripts.app.server import make_server
class LoginHistoryTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'lab.sqlite');self.admin=self.s.create_user('admin','test-long-password',role='admin',setup=True)['id'];self.editor=self.s.create_user('editor','test-long-password',actor=self.admin)['id']
 def tearDown(self):self.tmp.cleanup()
 def test_success_failure_and_immutable_secret_free_records(self):
  token,_=self.s.login('admin','test-long-password')
  for name in ['admin','unknown']:
   with self.assertRaises(Problem):self.s.login(name,'wrong-password')
  rows=self.s.login_history(self.admin)['rows'];self.assertEqual([r['outcome'] for r in rows],['failure','failure','success']);self.assertIsNone(rows[0]['user_id']);self.assertEqual(rows[1]['user_id'],self.admin)
  self.assertNotIn(token,json.dumps(rows));self.assertNotIn('password',json.dumps(rows));self.assertEqual(set(rows[0]),{'id','user_id','username','outcome','created_at'})
  with self.s.db() as c:
   with self.assertRaises(sqlite3.IntegrityError):c.execute('DELETE FROM login_history')
  with self.assertRaises(Problem):self.s.login_history(self.editor)
 def test_pagination_and_snapshot_username(self):
  for i in range(105):self.s.record_login('editor','blocked')
  self.s.rename_user(self.editor,'renamed','editor',self.admin)
  first=self.s.login_history(self.admin);second=self.s.login_history(self.admin,first['next_before']);self.assertEqual(len(first['rows']),100);self.assertEqual(len(second['rows']),5);self.assertEqual(second['rows'][0]['username'],'editor');self.assertFalse(set(r['id'] for r in first['rows'])&set(r['id'] for r in second['rows']))
 def test_http_admin_only_and_rate_limited_attempts(self):
  server=make_server('127.0.0.1',0,self.s.path);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  ta,_=self.s.login('admin','test-long-password');te,_=self.s.login('editor','test-long-password')
  def req(path,token='',body=None):
   conn=http.client.HTTPConnection('127.0.0.1',server.server_port);conn.request('POST' if body else 'GET',path,json.dumps(body) if body else None,{'Cookie':'lab_session='+token,'Content-Type':'application/json'});res=conn.getresponse();status=res.status;data=json.loads(res.read());conn.close();return status,data
  try:
   self.assertEqual(req('/api/login-history')[0],401);self.assertEqual(req('/api/login-history',te)[0],403);self.assertEqual(req('/api/login-history',ta)[0],200)
   for i in range(16):status,_=req('/api/login',body={'username':'unknown','password':'not-recorded'})
   self.assertEqual(status,429);self.assertEqual(req('/api/login-history',ta)[1]['rows'][0]['outcome'],'blocked')
  finally:server.shutdown();server.server_close();thread.join()
