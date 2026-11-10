import base64, copy, tempfile, unittest
from pathlib import Path
from scripts.imports.facs import describe
from scripts.app.service import Store, Problem

class FacsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.s=Store(Path(self.temp.name)/'test.sqlite')
        self.actor=self.s.create_user('test','test-password-123',setup=True)['id']
        self.header=['Sample','Live cells/CD3+ | Count']
        self.rows=[['Liver_48.fcs','0'],['Liver_FMO CD3_012.fcs','999'],['Liver_49.fcs','n/a'],['Mean','500']]
        self.table={'headers':self.header,'rows':self.rows,'source_rows':[2,3,4,5],'sheets':['Sheet0'],'sheet':'Sheet0','facs':describe(self.header,self.rows,[2,3,4,5])}
        self.s.read_table=lambda *args,**kwargs:copy.deepcopy(self.table)
        self.upload=self.s.stage('test.xls',base64.b64encode(b'fixture').decode(),self.actor)['upload_id']
        self.mp={'id_column':'Sample','sheet':'Sheet0','measurements':self.table['facs']['specs'],'facs_reviewed':True,'sample_rows':[{'row':2,'mouse_id':'48','group':'A'},{'row':4,'mouse_id':'49','group':'B'}]}
    def tearDown(self):self.temp.cleanup()
    def commit(self):return self.s.commit_import(self.upload,self.mp,self.actor,'reviewed import')
    def test_samples_control_summary_and_acquisition_suffix(self):
        f=describe(self.header,[['2025-07-31_Liver_102_001.fcs','1'],['Liver_Live dead_009.fcs','2'],['SD','3']],[2,3,4])
        self.assertEqual([r['kind'] for r in f['samples']],['sample','control / unmapped','summary'])
        self.assertEqual(f['samples'][0]['mouse_id'],'102')
        self.assertEqual(f['samples'][0]['acquisition_suffix'],'001')
    def test_zero_missing_controls_and_provenance(self):
        self.assertEqual(self.commit()['measurements'],2)
        snap=self.s.snapshot();self.assertEqual([r['value'] for r in snap['measurements']],[0,None])
        self.assertEqual(snap['measurements'][1]['missing_reason'],'원본 n/a')
        self.assertEqual([r['source_row'] for r in snap['measurements']],[2,4])
        self.assertIn('source_interpretation',self.s.audit()[0]['after_json'])
    def test_review_and_control_inclusion_guard(self):
        self.mp['facs_reviewed']=False
        with self.assertRaises(Problem):self.commit()
        self.mp['facs_reviewed']=True;self.mp['sample_rows'][0]['row']=3
        with self.assertRaises(Problem):self.commit()
        self.assertEqual(self.s.snapshot()['measurements'],[])
    def test_calculated_block_requires_definition(self):
        self.table['facs']['needs_statistic']=True
        with self.assertRaises(Problem):self.commit()
        self.mp.update(facs_statistic='User-defined corrected count',facs_unit='cells/µL')
        self.commit();self.assertEqual(self.s.snapshot()['metrics'][0]['unit'],'cells/µL')
    def test_duplicate_mouse_mapping_rolls_back(self):
        self.mp['sample_rows'][1]['mouse_id']='48';self.mp['sample_rows'][1]['group']='A'
        with self.assertRaises(Problem):self.commit()
        self.assertEqual(self.s.snapshot()['mice'],[])
    def test_mfi_snapshot_uses_exact_original_column_without_changing_metric_identity(self):
        header='Live cells/CD3+ | Geometric Mean (CD3)'
        self.table['headers']=['Sample',header]
        self.table['facs']=describe(self.table['headers'],self.rows,[2,3,4,5])
        self.mp['measurements']=self.table['facs']['specs']
        self.commit()
        metric=self.s.snapshot()['metrics'][0]
        self.assertEqual(metric['source_header'],header)
        self.assertEqual(metric['name'],'Geometric Mean (CD3)')
        self.assertNotIn('source_header',__import__('json').loads(metric['identity']))

if __name__=='__main__':unittest.main()
