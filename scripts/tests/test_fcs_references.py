import tempfile, unittest
from pathlib import Path
import json, subprocess
from unittest.mock import patch
from scripts.fcs.fcs_references import mapped_path, references
from scripts.fcs.fcs_storage import FCSLibrary, digest
from scripts.app.service import Store, Problem

class ReferenceTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.share=self.root/'share';self.share.mkdir()
  self.rules=[{'workspace_prefix':'S:/MK3/research/','server_root':str(self.share)}]
  self.path=self.share/'folder name';self.path.mkdir();self.source=self.path/'mouse.fcs';self.source.write_bytes(b'FCS3.0abc')
  self.wsp=self.root/'source.wsp'
  self.wsp.write_text('<Workspace flowJoVersion="10.10"><SampleList><Sample><DataSet uri="file:/S:/MK3/research/folder%20name/mouse.fcs"/><SampleNode name="mouse.fcs" sampleID="123" count="5"/></Sample></SampleList></Workspace>')
 def tearDown(self):self.tmp.cleanup()
 def test_path_mapping_and_denial(self):
  self.assertEqual(mapped_path('file:/S:/MK3/research/folder%20name/mouse.fcs',self.rules)[0],self.source.resolve())
  self.assertIsNone(mapped_path('file:/etc/passwd',self.rules)[0])
  for name in ['../escape.fcs','%2e%2e/escape.fcs','file.txt']:
   with self.assertRaises(ValueError):mapped_path('S:/MK3/research/'+name,self.rules)
  outside=self.root/'outside.fcs';outside.write_bytes(b'FCS3.0abc')
  (self.share/'link.fcs').symlink_to(outside)
  with self.assertRaises(ValueError):mapped_path('S:/MK3/research/link.fcs',self.rules)
 def test_list_missing_files_and_original_uri(self):
  row=references(self.wsp,rules=self.rules)[0]
  self.assertEqual(row['status'],'Available');self.assertEqual(row['sample_id'],'123')
  self.assertIn('%20',row['original_uri'])
  self.source.unlink();self.assertEqual(references(self.wsp,rules=self.rules)[0]['status'],'File not found')
 def test_import_copies_without_touching_source_and_audits(self):
  store=Store(self.root/'db.sqlite');actor=store.create_user('qa','test-password-123',role='admin',setup=True)['id']
  library=FCSLibrary(store,start_worker=False)
  data=self.wsp.read_bytes();transfer=library.begin({'filename':'source.wsp','size':len(data)},actor)
  library.append(transfer['id'],actor,0,data);file=library.finish(transfer['id'],actor)
  before=digest(self.source)
  def copy_process(args,**kwargs):
   from scripts.fcs.fcs_copy import copy_source
   try:return subprocess.CompletedProcess(args,0,json.dumps(copy_source(args[-3],args[-2],int(args[-1]))).encode(),b'')
   except Exception as e:return subprocess.CompletedProcess(args,1,json.dumps({'error':str(e)}).encode(),b'')
  with patch('scripts.fcs.fcs_references.mappings',return_value=self.rules),patch('scripts.fcs.fcs_storage.subprocess.run',side_effect=copy_process):
   new=library.import_reference({'wsp_id':file['id'],'sample_id':'123'},actor)
   again=library.import_reference({'wsp_id':file['id'],'sample_id':'123'},actor)
   self.assertEqual(new['id'],again['id'])
   with self.assertRaises(Problem):library.import_reference({'wsp_id':file['id'],'sample_id':'wrong'},actor)
  with patch('scripts.fcs.fcs_references.mappings',return_value=self.rules),patch('scripts.fcs.fcs_storage.subprocess.run',side_effect=subprocess.TimeoutExpired('copy',120)):
   with self.assertRaises(Problem) as error:library.import_reference({'wsp_id':file['id'],'sample_id':'123'},actor)
   self.assertEqual(error.exception.status,504)
  self.assertEqual(len(library.catalog()['files']),2)
  self.assertEqual(new['sha256'],before);self.assertEqual(digest(self.source),before)
  self.assertEqual(library.source(new['id'])[1].read_bytes(),self.source.read_bytes())
  self.assertEqual(digest(library.root/'mirror'/before),before)
  self.assertTrue(any(e['action']=='import_reference' for e in store.audit()))

if __name__=='__main__':unittest.main()
