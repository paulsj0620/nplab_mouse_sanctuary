import json,sqlite3,tempfile,unittest
from pathlib import Path
from scripts.app.service import Store
from scripts.fcs.fcs_storage import FCSLibrary
from scripts.maintenance.smb_backup import snapshot,transfer,restore
class BackupTests(unittest.TestCase):
 def test_roundtrip_and_corrupt_existing_destination(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)/'project';root.mkdir();(root/'archives').mkdir();(root/'config').mkdir();(root/'archives/original.xlsx').write_bytes(b'original bytes');(root/'config/settings.json').write_text('{}')
   store=Store(root/'data/lab.sqlite');lib=FCSLibrary(store,start_worker=False)
   manifest=snapshot(root);remote=Path(tmp)/'remote';published=transfer(manifest,remote)
   result=restore(published,Path(tmp)/'restored');self.assertEqual((Path(result['restored'])/'archives/original.xlsx').read_bytes(),b'original bytes')
   transfer(manifest,remote) # retry is idempotent
   with self.assertRaises(ValueError):restore(published,Path(result['restored']))
   info=json.loads(manifest.read_text());(remote/info['files'][0]['backup']).write_bytes(b'corrupt')
   with self.assertRaises(ValueError):transfer(manifest,remote)
 def test_traversal_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'bad.complete.json';p.write_text(json.dumps({'files':[{'backup':'../escape','restore':'x','sha256':'bad'}]}))
   with self.assertRaises(ValueError):transfer(p,Path(tmp)/'remote')
