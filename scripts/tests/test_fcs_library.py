import io,json,sqlite3,tempfile,unittest
from pathlib import Path
from scripts.app.service import Store,Problem
from scripts.fcs.fcs_storage import FCSLibrary,CHUNK,digest
from scripts.maintenance.fcs_backup import backup_assets,restore_bundle
class LibraryTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.store=Store(self.root/'data/lab.sqlite')
  self.admin=self.store.create_user('admin','test-password-123',role='admin',setup=True)['id'];self.other=self.store.create_user('other','test-password-456',actor=self.admin)['id']
  self.lib=FCSLibrary(self.store,start_worker=False)
 def tearDown(self):self.tmp.cleanup()
 def upload(self,payload=b'FCS3.0'+b'0'*100):
  t=self.lib.begin({'filename':'Liver_146.fcs','size':len(payload)},self.admin)
  for offset in range(0,len(payload),CHUNK):self.lib.append(t['id'],self.admin,offset,payload[offset:offset+CHUNK])
  return t,self.lib.finish(t['id'],self.admin)
 def test_large_resumable_upload_integrity_and_idempotence(self):
  payload=b'FCS3.0'+b'a'*(11*1024**2);t=self.lib.begin({'filename':'Liver_146.fcs','size':len(payload)},self.admin)
  self.lib.append(t['id'],self.admin,0,payload[:CHUNK]);self.lib.append(t['id'],self.admin,0,payload[:CHUNK])
  reloaded=FCSLibrary(self.store,start_worker=False);self.assertEqual(reloaded.transfer(t['id'],self.admin)['received'],CHUNK)
  with self.assertRaises(Problem):reloaded.transfer(t['id'],self.other)
  with self.assertRaises(Problem):reloaded.append(t['id'],self.admin,0,b'wrong')
  with self.assertRaises(Problem):reloaded.finish(t['id'],self.admin)
  for offset in range(CHUNK,len(payload),CHUNK):reloaded.append(t['id'],self.admin,offset,payload[offset:offset+CHUNK])
  f=reloaded.finish(t['id'],self.admin);self.assertEqual(f['size'],len(payload));self.assertEqual(reloaded.finish(t['id'],self.admin)['id'],f['id'])
  for folder in ['objects','mirror']:self.assertEqual((self.lib.root/folder/f['sha256']).read_bytes(),payload)
 def test_crash_tail_recovery_and_immutable_catalogue(self):
  t=self.lib.begin({'filename':'a.fcs','size':9},self.admin);self.lib.append(t['id'],self.admin,0,b'FCS3.0')
  with open(self.lib.root/'staging'/t['id'],'ab') as f:f.write(b'uncommitted tail')
  self.lib.append(t['id'],self.admin,6,b'abc');f=self.lib.finish(t['id'],self.admin)
  for statement in ['DELETE FROM fcs_files','UPDATE fcs_files SET filename="changed"']:
   with self.assertRaises(sqlite3.IntegrityError),self.store.db() as c:c.execute(statement)
  self.assertEqual(self.lib.source(f['id'])[1].read_bytes(),b'FCS3.0abc')
 def test_invalid_type_and_xml_entities_rejected(self):
  for name,payload in [('a.fcs',b'not fcs'),('a.wsp',b'<!DOCTYPE x [<!ENTITY x SYSTEM "file:///etc/passwd">]><Workspace/>')]:
   t=self.lib.begin({'filename':name,'size':len(payload)},self.admin);self.lib.append(t['id'],self.admin,0,payload)
   with self.assertRaises((Problem,ValueError)):self.lib.finish(t['id'],self.admin)
  for name in ['../a.fcs','a.exe','x\\a.fcs']:
   with self.assertRaises(Problem):self.lib.begin({'filename':name,'size':4},self.admin)
  self.assertEqual(self.lib.catalog()['files'],[])
 def test_full_backup_restore_keeps_originals_and_pending_uploads(self):
  _,f=self.upload();t=self.lib.begin({'filename':'pending.fcs','size':20},self.admin);self.lib.append(t['id'],self.admin,0,b'FCS3.0')
  folder=self.root/'backup';folder.mkdir();snapshot=folder/'lab.sqlite'
  with self.store.db() as src,sqlite3.connect(snapshot) as dst:src.backup(dst)
  backup_assets(snapshot,self.store.path,folder);result=restore_bundle(snapshot,self.root/'restored')
  restored=FCSLibrary(Store(result['database']),start_worker=False)
  self.assertEqual(restored.file(f['id'])['sha256'],f['sha256']);self.assertEqual(digest(restored.source(f['id'])[1]),f['sha256'])
  self.assertEqual(restored.transfer(t['id'],self.admin)['received'],6)
  with self.assertRaises(ValueError):restore_bundle(snapshot,self.root/'restored')
 def test_analysis_metadata_does_not_modify_existing_measurements(self):
  _,f=self.upload();before=self.store.snapshot();run=self.lib.queue({'fcs_id':f['id'],'organ':'Liver'},self.admin)
  self.assertEqual(self.lib.run(run['id'])['status'],'queued');self.assertEqual(self.store.snapshot()['measurements'],before['measurements'])
  with self.assertRaises(Problem):self.lib.queue({'fcs_id':f['id'],'mouse_id':'unknown','organ':'Liver'},self.admin)
 def test_gate_edit_is_append_only_and_records_lineage(self):
  _,f=self.upload();base=self.lib.queue({'fcs_id':f['id'],'organ':'Liver'},self.admin)['id']
  info={'events':4,'channels':[{},{}],'gates':[]}
  with self.store.db() as c:c.execute("UPDATE fcs_runs SET status='done',result=? WHERE id=?",(json.dumps(info),base))
  change={'target':-1,'parent_index':-1,'name':'New gate','kind':'RectangleGate','axes':[0,1],'bounds':[[0,2],[0,2]]}
  edit=self.lib.edit({'base_run':base,'reason':'QA gate test','change':change},self.admin)
  self.assertNotEqual(edit['id'],base);self.assertEqual(self.lib.run(base)['result'],info)
  spec=json.loads(self.lib.run(edit['id'])['edit_spec']);self.assertEqual(spec['base_run'],base);self.assertEqual(spec['changes'][0]['name'],'New gate')
  with self.assertRaises(sqlite3.IntegrityError),self.store.db() as c:c.execute("UPDATE fcs_runs SET edit_spec='{}' WHERE id=?",(edit['id'],))
if __name__=='__main__':unittest.main()
