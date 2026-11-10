import base64,tempfile,unittest
from pathlib import Path
from scripts.app.service import Store,Problem
from scripts.fcs.fcs_storage import FCSLibrary
from scripts.app.experiments import workspace,link_file
class ExperimentTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.s=Store(Path(self.tmp.name)/'data/lab.sqlite');self.lib=FCSLibrary(self.s,start_worker=False);self.actor=self.s.create_user('test','test-long-password',role='admin',setup=True)['id']
  self.mapping={'id_column':'id','experiment_column':'exp','diet_column':'diet','weeks_column':'weeks','metadata_only':True,'allow_new_mice':True,'measurements':[]}
 def tearDown(self):self.tmp.cleanup()
 def upload(self,text):return self.s.stage('meta.csv',base64.b64encode(text.encode()).decode(),self.actor)['upload_id']
 def register(self):
  uid=self.upload('id,exp,diet,weeks\nM1,Exp20,Chow,36\n');r=self.s.review_import(uid,self.mapping,self.actor);self.assertTrue(r['ok'],r);self.s.commit_import(uid,self.mapping,self.actor,'Register metadata',r['review_token'],True);return uid
 def test_metadata_only_and_later_measurements(self):
  uid=self.register();state=self.s.snapshot();self.assertEqual(len(state['measurements']),0);self.assertEqual(len(state['metrics']),0);self.assertEqual(state['mice'][0]['group_name'],'Chow')
  w=workspace(self.s,'Exp20',False);self.assertEqual(w['spreadsheets'][0]['id'],uid);self.assertNotIn('files',w)
  u=self.upload('id,value\nM1,12\n');mp={'id_column':'id','measurements':[{'column':'value','name':'Frequency','unit':'%'}]};report=self.s.review_import(u,mp,self.actor);self.assertTrue(report['ok']);self.s.commit_import(u,mp,self.actor,'Later value',report['review_token'],True);self.assertEqual(len(self.s.snapshot()['mice']),1)
 def test_metadata_duplicate_and_conflict(self):
  self.register();uid=self.upload('id,exp,diet,weeks\nM1,Exp21,Chow,36\nM1,Exp21,Chow,36\n');report=self.s.review_import(uid,self.mapping,self.actor);codes={i['code'] for i in report['issues']};self.assertTrue({'duplicate_file','roster_mismatch'}<=codes)
 def test_file_link_and_unlink_preserve_original(self):
  self.register();raw=b'<Workspace><SampleList><Sample><SampleNode name="sample.fcs" sampleID="1" count="0"/></Sample></SampleList></Workspace>';t=self.lib.begin({'filename':'sample.wsp','size':len(raw)},self.actor);self.lib.append(t['id'],self.actor,0,raw);f=self.lib.finish(t['id'],self.actor)
  data={'experiment':'Exp20','mouse_id':'M1','file_id':f['id'],'reason':'Link metadata'};link_file(self.s,data,self.actor);w=workspace(self.s,'Exp20',True);self.assertEqual(w['files'][0]['id'],f['id'])
  with self.assertRaises(Problem):link_file(self.s,{**data,'mouse_id':'M2'},self.actor)
  link_file(self.s,{**data,'remove':True},self.actor);self.assertEqual(workspace(self.s,'Exp20',True)['files'],[]);self.assertEqual(self.lib.source(f['id'])[1].read_bytes(),raw)
