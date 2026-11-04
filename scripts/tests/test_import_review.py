import base64,tempfile,unittest
from pathlib import Path
from scripts.app.service import Store,Problem
class ImportReviewTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'lab.sqlite');self.actor=self.s.create_user('reviewer','test-long-password',role='admin',setup=True)['id'];self.mapping={'id_column':'id','group_column':'group','measurements':[{'column':'weight','name':'Weight','unit':'g'}]}
 def tearDown(self):self.tmp.cleanup()
 def upload(self,text):return self.s.stage('test.csv',base64.b64encode(text.encode()).decode(),self.actor)['upload_id']
 def test_unknown_ids_explicit_registration_and_read_only_preview(self):
  uid=self.upload('id,group,weight\nM001,A,0\nM002,A,\n');r=self.s.review_import(uid,self.mapping,self.actor)
  self.assertFalse(r['ok']);self.assertEqual(r['new_mouse_count'],2);self.assertEqual(r['missing_count'],1);self.assertEqual(r['preview'][0]['value'],0)
  with self.s.db() as c:self.assertEqual(c.execute('select count(*) from mice').fetchone()[0],0);self.assertEqual(c.execute('select count(*) from metrics').fetchone()[0],0)
  self.mapping['allow_new_mice']=True;r=self.s.review_import(uid,self.mapping,self.actor);self.assertTrue(r['ok'])
  self.s.commit_import(uid,self.mapping,self.actor,'reviewed',r['review_token'],True)
  self.assertEqual(len(self.s.snapshot()['mice']),2)
 def test_duplicate_file_database_and_roster_mismatch(self):
  uid=self.upload('id,group,weight\nM001,A,10\n');self.s.commit_import(uid,self.mapping,self.actor,'seed')
  uid=self.upload('id,group,weight\nM001,B,12\nM001,B,13\n');r=self.s.review_import(uid,self.mapping,self.actor);codes={i['code'] for i in r['issues']}
  self.assertTrue({'duplicate_file','duplicate_database','roster_mismatch'}<=codes)
  with self.assertRaises(Problem):self.s.commit_import(uid,self.mapping,self.actor,'blocked','bad',True)
  self.assertEqual(len(self.s.snapshot()['measurements']),1)
 def test_token_binds_mapping_and_database_revision(self):
  uid=self.upload('id,group,weight\nM001,A,10\n');self.mapping['allow_new_mice']=True;r=self.s.review_import(uid,self.mapping,self.actor)
  altered={**self.mapping,'measurements':[{'column':'weight','name':'Changed','unit':'g'}]}
  with self.assertRaises(Problem):self.s.commit_import(uid,altered,self.actor,'changed',r['review_token'],True)
  self.s.create_user('another','other-long-password',actor=self.actor)
  with self.assertRaises(Problem):self.s.commit_import(uid,self.mapping,self.actor,'stale',r['review_token'],True)
  fresh=self.s.review_import(uid,self.mapping,self.actor);self.s.commit_import(uid,self.mapping,self.actor,'fresh',fresh['review_token'],True)
 def test_owner_and_invalid_values(self):
  uid=self.upload('id,group,weight\n,A,5\nM001,A,nope\n');r=self.s.review_import(uid,self.mapping,self.actor)
  self.assertTrue({'mouse_id','invalid_value'}<={i['code'] for i in r['issues']})
  with self.assertRaises(Problem):self.s.review_import(uid,self.mapping,-1)
