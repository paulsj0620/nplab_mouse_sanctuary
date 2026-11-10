import io, tempfile, unittest, zipfile
from pathlib import Path
from scripts.app.service import Store, Problem
from scripts.app.strategies import StrategyLibrary,extract

def workbook():
    b=io.BytesIO()
    with zipfile.ZipFile(b,'w') as z:
        z.writestr('xl/workbook.xml','<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="FACS Liver" r:id="r1"/></sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels','<Relationships><Relationship Id="r1" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr('xl/worksheets/sheet1.xml','<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"/>')
        z.writestr('xl/media/image1.png',b'\x89PNG\r\n\x1a\nfixture')
    return b.getvalue()

class StrategyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.store=Store(Path(self.tmp.name)/'test.sqlite');self.lib=StrategyLibrary(self.store)
        a=self.store.create_user('admin','admin-password123',role='admin',setup=True)['id'];e=self.store.create_user('editor','editor-password123',actor=a)['id']
        self.admin={'id':a,'role':'admin'};self.editor={'id':e,'role':'editor'}
    def tearDown(self):self.tmp.cleanup()
    def test_preservation_idempotence_visibility_and_review(self):
        raw=workbook();self.assertEqual(self.lib.ingest('Exp 9.xlsx',raw,self.admin['id'])['added'],1)
        self.assertEqual(self.lib.ingest('Exp 9.xlsx',raw,self.admin['id'])['added'],0)
        self.assertEqual(self.lib.catalog(self.editor),[])
        row=self.lib.catalog(self.admin,True)[0];iid=row['id']
        with self.assertRaises(Problem):self.lib.source(iid,self.editor,'original')
        d={'version':1,'experiment':'Exp9','organ':'Liver','panel':'T Cell Panel','description':'verified','status':'approved','reason':'Reviewed source'}
        with self.assertRaises(Problem):self.lib.review(iid,d,self.editor)
        self.lib.review(iid,d,self.admin)
        self.assertEqual(len(self.lib.catalog(self.editor)),1)
        self.assertEqual(self.lib.source(iid,self.editor,'workbook')[0],raw)
        with self.assertRaises(Problem) as e:self.lib.review(iid,d,self.admin)
        self.assertEqual(e.exception.status,409)
        self.assertTrue(any(x['entity']=='strategy_image' for x in self.store.audit()))
        d.update(version=2,status='not_strategy');self.lib.review(iid,d,self.admin)
        self.assertEqual(self.lib.catalog(self.editor),[])
        self.assertEqual(self.lib.source(iid,self.admin,'workbook')[0],raw)
    def test_invalid_and_admin_only(self):
        with self.assertRaises(Problem):extract(b'not zip')
        with self.assertRaises(Problem):self.lib.ingest('a.xlsx',workbook(),self.editor['id'])
        with self.assertRaises(Problem):self.lib.catalog(self.editor,True)
        self.lib.ingest('a.xlsx',workbook(),self.admin['id']);r=self.lib.catalog(self.admin,True)[0]
        with self.assertRaises(Problem):self.lib.review(r['id'],{'version':1,'status':'approved','reason':'x'},self.admin)

if __name__=='__main__':unittest.main()
