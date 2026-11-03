import http.client,json,threading
from scripts.tests import test_accounts
import unittest
from scripts.app.server import make_server
class AccountHTTPTests(unittest.TestCase):
 setUp=test_accounts.AccountTests.setUp
 tearDown=test_accounts.AccountTests.tearDown
 def test_http_csrf_self_scope_and_password_revocation(self):
  server=make_server('127.0.0.1',0,self.store.path);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  try:
   token,user=self.store.login('editor','editor-password-123')
   def request(path,body,method='POST',csrf=user['csrf']):
    conn=http.client.HTTPConnection('127.0.0.1',server.server_port)
    conn.request(method,path,json.dumps(body),{'Content-Type':'application/json','Cookie':'lab_session='+token,'X-CSRF-Token':csrf})
    response=conn.getresponse();result=(response.status,json.loads(response.read()));conn.close();return result
   self.assertEqual(request('/api/account',{'username':'new','expected_username':'editor'},'PATCH',csrf='wrong')[0],403)
   self.assertEqual(request('/api/users/'+str(self.admin),{'username':'new','expected_username':'admin'},'PATCH')[0],403)
   self.assertEqual(request('/api/account',{'username':'new','expected_username':'editor'},'PATCH')[0],200)
   self.assertEqual(request('/api/account/password',{'current_password':'editor-password-123','new_password':'replacement-password-456','user_id':self.admin})[0],200)
   self.assertEqual(request('/api/account',{'username':'later','expected_username':'new'},'PATCH')[0],401)
   self.store.login('admin','admin-password-123');self.store.login('new','replacement-password-456')
  finally:server.shutdown();server.server_close();thread.join()
 def test_password_attempt_limit(self):
  server=make_server('127.0.0.1',0,self.store.path);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  try:
   token,user=self.store.login('editor','editor-password-123')
   for n in range(6):
    conn=http.client.HTTPConnection('127.0.0.1',server.server_port)
    conn.request('POST','/api/account/password',json.dumps({'current_password':'wrong','new_password':'replacement-password'}),{'Content-Type':'application/json','Cookie':'lab_session='+token,'X-CSRF-Token':user['csrf']})
    response=conn.getresponse();self.assertEqual(response.status,403 if n<5 else 429);response.read();conn.close()
  finally:server.shutdown();server.server_close();thread.join()
