from test_fcs_references import ReferenceTests
from fcs_storage import FCSLibrary,digest
from service import Store,Problem
from fcs_probe import probe
from unittest.mock import patch
from fcs_backup import backup_assets,restore_bundle
import sqlite3,json
class LinkTests(ReferenceTests):
 def test_link_no_copy_change_detection_and_backup(self):
  store=Store(self.root/'db.sqlite');actor=store.create_user('qa','test-password-123',role='admin',setup=True)['id'];lib=FCSLibrary(store,start_worker=False)
  data=self.wsp.read_bytes();t=lib.begin({'filename':'source.wsp','size':len(data)},actor);lib.append(t['id'],actor,0,data);w=lib.finish(t['id'],actor)
  before={p.relative_to(lib.root) for p in lib.root.rglob('*')};sha=digest(self.source)
  with patch('fcs_references.mappings',return_value=self.rules),patch.object(lib,'probe_reference',side_effect=probe):
   f=lib.link_reference({'wsp_id':w['id'],'sample_id':'123'},actor)
   self.assertEqual(f['storage'],'smb');self.assertEqual(lib.source(f['id'])[1],self.source.resolve())
   self.assertEqual(lib.link_reference({'wsp_id':w['id'],'sample_id':'123'},actor)['id'],f['id'])
   self.assertEqual(before,{p.relative_to(lib.root) for p in lib.root.rglob('*')});self.assertEqual(digest(self.source),sha)
   self.source.write_bytes(b'FCS3.0xyz')
   with self.assertRaises(Problem):lib.source(f['id'])
   changed=lib.link_reference({'wsp_id':w['id'],'sample_id':'123'},actor);self.assertNotEqual(f['id'],changed['id'])
  snapshot=self.root/'snapshot.sqlite'
  with store.db() as c,sqlite3.connect(snapshot) as dst:c.backup(dst)
  report=backup_assets(snapshot,store.path,self.root)
  manifest=json.loads(__import__('pathlib').Path(report).read_text());self.assertEqual(len(manifest['external_sources']),2)
  self.assertFalse(any(x['path']=='objects/'+sha for x in manifest['files']))
  restore_bundle(snapshot,self.root/'restored')
