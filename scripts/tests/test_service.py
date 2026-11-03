import base64, concurrent.futures, io, json, sqlite3, tempfile, unittest
from pathlib import Path
from scripts.app.service import Store, Problem

def encoded(s):return base64.b64encode(s.encode()).decode()
def mapping(name='Body weight',column='weight',unit='g'):
    return {'id_column':'id','group_column':'group','measurements':[{'column':column,'name':name,'unit':unit,'timepoint':'endpoint'}]}
class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.store=Store(Path(self.tmp.name)/'lab.sqlite')
        self.admin=self.store.create_user('admin','test-password-strong',role='admin',setup=True)['id']
        self.editor=self.store.create_user('editor','other-password-strong',actor=self.admin)['id']
    def tearDown(self):self.tmp.cleanup()
    def add(self,raw,actor=None,mp=None):
        actor=actor or self.admin;stage=self.store.stage('values.csv',encoded(raw),actor)
        return self.store.commit_import(stage['upload_id'],mp or mapping(),actor,'test import')
    def test_new_mice_dynamic_metrics_missing_zero_and_reopen(self):
        r=self.add('id,group,weight\n184,A,0\n185,B,\n')
        self.assertEqual(r,{'measurements':2,'new_mice':2})
        again=Store(self.store.path).snapshot();self.assertEqual([r['value'] for r in again['measurements']],[0,None])
        self.add('id,group,weight\n184,A,99\n',mp=mapping('Custom marker',unit='ng/mL'))
        self.assertEqual(len(self.store.snapshot()['metrics']),2)
    def test_duplicate_rolls_back_new_mouse_metric_and_audit(self):
        self.add('id,group,weight\n184,A,25\n');before=self.store.snapshot();events=len(self.store.audit())
        with self.assertRaises(Problem):self.add('id,group,weight\n185,A,20\n184,A,30\n')
        self.assertEqual(self.store.snapshot()['mice'],before['mice']);self.assertEqual(len(self.store.audit()),events)
        self.assertEqual(self.store.snapshot()['measurements'][0]['value'],25)
    def test_two_editors_conflict_never_overwrites(self):
        self.add('id,group,weight\n184,A,25\n');rid=self.store.snapshot()['measurements'][0]['id']
        def edit(args):
            actor,value=args
            try:self.store.edit_measurement(rid,{'value':value,'version':1,'reason':'concurrent edit'},actor);return 'saved'
            except Problem as e:return e.status
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:out=list(pool.map(edit,[(self.admin,26),(self.editor,27)]))
        self.assertCountEqual(out,['saved',409]);self.assertEqual(self.store.snapshot()['measurements'][0]['version'],2)
        event=self.store.audit()[0];self.assertIn(event['username'],['admin','editor']);self.assertEqual(json.loads(event['before_json'])['value'],25)
    def test_simultaneous_uploads_and_owner_isolation(self):
        a=self.store.stage('a.csv',encoded('id,group,weight\n200,A,24\n'),self.admin)
        b=self.store.stage('b.csv',encoded('id,group,weight\n201,A,25\n'),self.editor)
        with self.assertRaises(Problem):self.store.commit_import(a['upload_id'],mapping(),self.editor,'invalid owner')
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            out=list(pool.map(lambda x:self.store.commit_import(x[0]['upload_id'],mapping(),x[1],'parallel'),[(a,self.admin),(b,self.editor)]))
        self.assertEqual(len(self.store.snapshot()['measurements']),2)
    def test_global_exclusion_restore_and_immutable_sources(self):
        self.add('id,group,weight\n184,A,25\n');self.add('id,group,weight\n184,A,80\n',mp=mapping('OGTT',unit='mg/dL'))
        before=self.store.snapshot()['measurements']
        self.store.edit_mouse('184',{'version':1,'excluded':True,'reason':'QC sample'},self.editor)
        self.assertEqual(self.store.snapshot()['mice'][0]['excluded'],1)
        self.store.edit_mouse('184',{'version':2,'excluded':False,'reason':'QC reviewed'},self.admin)
        self.assertEqual(self.store.snapshot()['measurements'],before)
        with self.assertRaises(sqlite3.IntegrityError):
            with self.store.db() as c:c.execute("UPDATE uploads SET original=x'00'")
        with self.assertRaises(sqlite3.IntegrityError):
            with self.store.db() as c:c.execute('DELETE FROM events')
    def test_login_role_and_preset_conflict(self):
        token,u=self.store.login('editor','other-password-strong');self.assertEqual(self.store.session(token)['id'],self.editor)
        with self.assertRaises(Problem):self.store.create_user('bad','valid-password-123',actor=self.editor)
        with self.assertRaises(Problem):self.store.login('editor','wrong')
        self.store.preset({'name':'lab','config':{'error':'SD'}},self.admin)
        self.store.preset({'name':'lab','config':{'error':'SEM'},'version':1},self.editor)
        with self.assertRaises(Problem):self.store.preset({'name':'lab','config':{},'version':1},self.admin)
    def test_xlsx_and_source_row_preserved(self):
        # In-memory fixture only. No authored spreadsheet deliverable.
        from openpyxl import Workbook
        w=Workbook();s=w.active;s.append(['id','group','weight']);s.append([184,'A',0]);s.append([None,None,None]);s.append([185,'B',30]);b=io.BytesIO();w.save(b)
        stage=self.store.stage('test.xlsx',base64.b64encode(b.getvalue()).decode(),self.admin)
        self.store.commit_import(stage['upload_id'],mapping(),self.admin,'xlsx import')
        self.assertEqual([r['source_row'] for r in self.store.snapshot()['measurements']],[2,4])
    def test_invalid_nonfinite_or_percent_does_not_commit(self):
        for v in ['NaN','inf','101','-1']:
            with self.assertRaises(Problem):self.add(f'id,group,weight\n184,A,{v}\n',mp=mapping('PSR',unit='%'))
        self.assertEqual(len(self.store.snapshot()['mice']),0)
    def test_sample_selection_saves_global_exclusions_and_audit(self):
        self.add('id,group,weight\n184,A,25\n185,B,30\n')
        before=self.store.snapshot()['measurements']
        result=self.store.set_sample_inclusion({'reason':'sample quality review','changes':[{'mouse_id':'184','version':1,'included':False},{'mouse_id':'185','version':1,'included':False}]},self.editor)
        self.assertEqual(result['updated'],['184','185'])
        self.assertTrue(all(m['excluded'] for m in self.store.snapshot()['mice']))
        self.assertEqual(self.store.snapshot()['measurements'],before)
        self.assertEqual(self.store.audit()[0]['username'],'editor')
        self.store.set_sample_inclusion({'reason':'review complete','changes':[{'mouse_id':'184','version':2,'included':True}]},self.admin)
        self.assertEqual(self.store.snapshot()['mice'][0]['excluded'],0)
    def test_sample_selection_conflict_rolls_back_entire_batch(self):
        self.add('id,group,weight\n184,A,25\n185,B,30\n')
        before=self.store.snapshot();events=len(self.store.audit())
        with self.assertRaises(Problem) as err:
            self.store.set_sample_inclusion({'reason':'review','changes':[{'mouse_id':'184','version':1,'included':False},{'mouse_id':'185','version':0,'included':False}]},self.editor)
        self.assertEqual(err.exception.status,409)
        self.assertEqual(self.store.snapshot()['mice'],before['mice'])
        self.assertEqual(len(self.store.audit()),events)
        with self.assertRaises(Problem):self.store.set_sample_inclusion({'reason':'','changes':[{'mouse_id':'184','version':1,'included':False}]},self.editor)
    def test_dashboard_preset_keeps_independent_panels_and_validates_limits(self):
        panels=[{'metric':str(i),'type':'bar','error':'SD' if i%2 else 'SEM','styles':{}} for i in range(8)]
        self.store.preset({'name':'board','config':{'error':'SD','dashboard':{'panels':panels,'count':5,'active':4}}},self.admin)
        saved=self.store.snapshot()['presets'][0]['config']['dashboard']
        self.assertEqual(saved['count'],5);self.assertEqual(saved['panels'],panels)
        for board in [{'panels':panels,'count':9},{'panels':panels[:3],'count':3},{'panels':panels,'count':4,'active':5}]:
            with self.assertRaises(Problem):self.store.preset({'name':'invalid','config':{'dashboard':board}},self.admin)
if __name__=='__main__':unittest.main()
