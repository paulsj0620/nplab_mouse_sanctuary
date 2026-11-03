import json,tempfile,unittest
from pathlib import Path
from service import Store,Problem
class AccountTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.store=Store(Path(self.tmp.name)/'test.sqlite')
  self.admin=self.store.create_user('admin','admin-password-123',role='admin',setup=True)['id']
  self.editor=self.store.create_user('editor','editor-password-123',actor=self.admin)['id']
 def tearDown(self):self.tmp.cleanup()
 def test_admin_and_self_rename_preserve_id_session_and_history(self):
  token,_=self.store.login('editor','editor-password-123')
  result=self.store.rename_user(self.editor,'renamed','editor',self.admin)
  self.assertEqual(result['id'],self.editor);self.assertEqual(self.store.session(token)['username'],'renamed')
  self.store.rename_user(self.editor,'self-renamed','renamed',self.editor)
  self.assertEqual(self.store.login('self-renamed','editor-password-123')[1]['id'],self.editor)
  with self.assertRaises(Problem):self.store.login('editor','editor-password-123')
  event=self.store.audit()[0];self.assertEqual(json.loads(event['before_json']),{'username':'renamed'})
 def test_authorization_duplicate_conflict_and_blank(self):
  for target,name,expected,actor,status in [(self.admin,'hijack','admin',self.editor,403),(self.editor,'admin','editor',self.editor,409),(self.editor,'new','stale',self.admin,409),(self.editor,' ','editor',self.admin,400)]:
   with self.assertRaises(Problem) as e:self.store.rename_user(target,name,expected,actor)
   self.assertEqual(e.exception.status,status)
  self.assertEqual(self.store.login('editor','editor-password-123')[1]['username'],'editor')
 def test_password_change_revokes_only_owner_sessions_and_does_not_log_secrets(self):
  a,_=self.store.login('editor','editor-password-123');b,_=self.store.login('editor','editor-password-123');admin,_=self.store.login('admin','admin-password-123')
  with self.store.db() as c:old=dict(c.execute('SELECT password,salt FROM users WHERE id=?',(self.editor,)).fetchone())
  self.store.change_password(self.editor,'editor-password-123','replacement-password-456')
  for token in [a,b]:
   with self.assertRaises(Problem):self.store.session(token)
  self.assertEqual(self.store.session(admin)['id'],self.admin)
  with self.assertRaises(Problem):self.store.login('editor','editor-password-123')
  self.assertEqual(self.store.login('editor','replacement-password-456')[1]['id'],self.editor)
  with self.store.db() as c:new=dict(c.execute('SELECT password,salt FROM users WHERE id=?',(self.editor,)).fetchone())
  self.assertNotEqual(old['salt'],new['salt'])
  audit=json.dumps(self.store.audit())
  for secret in ['editor-password-123','replacement-password-456',old['password'],new['password'],old['salt'],new['salt']]:self.assertNotIn(secret,audit)
 def test_rejected_password_changes_preserve_sessions_and_password(self):
  token,_=self.store.login('editor','editor-password-123');events=len(self.store.audit())
  for current,new in [('wrong','replacement-password'),('editor-password-123','short'),('editor-password-123','editor-password-123')]:
   with self.assertRaises(Problem):self.store.change_password(self.editor,current,new)
  self.assertEqual(self.store.session(token)['id'],self.editor);self.assertEqual(len(self.store.audit()),events)
  self.store.login('editor','editor-password-123')
if __name__=='__main__':unittest.main()
