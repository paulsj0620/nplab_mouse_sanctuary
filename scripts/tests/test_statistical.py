import copy,unittest
from scripts.statistics.statistical import analyze_panel,analyze_board
from scripts.app.service import Problem

def snapshot(groups):
    data={'metrics':[{'id':1}],'mice':[],'measurements':[],'revision':12}
    for group,values in groups.items():
        for value in values:
            mid=str(len(data['mice'])+1)
            data['mice'].append({'mouse_id':mid,'group_name':group,'diet':group,'experiment':'Exp1','weeks':'36','excluded':0,'version':1})
            data['measurements'].append({'mouse_id':mid,'metric_id':1,'value':value,'timepoint':'endpoint','replicate':'1'})
    return data

CFG={'metric':1,'type':'bar','grouping':'group_name','replicate':'1','timepoint':'endpoint','styles':{}}
class StatisticalTests(unittest.TestCase):
    def test_experiment_scope_keeps_di_controls_and_empty_scope(self):
        data=snapshot({'Chow':[1,2,30,40],'Western':[4,5,60,70]})
        for i,mouse in enumerate(data['mice']):mouse['experiment']='Exp1' if i%4<2 else 'Exp9'
        basic=analyze_panel(data,{**CFG,'scope_experiments':['Exp1']},[],Problem)
        di=analyze_panel(data,{**CFG,'scope_experiments':['Exp9']},[],Problem)
        self.assertEqual([g['mouse_ids'] for g in basic['groups']],[['1','2'],['5','6']])
        self.assertEqual([g['mouse_ids'] for g in di['groups']],[['3','4'],['7','8']])
        self.assertNotEqual(basic['data_sha256'],di['data_sha256'])
        self.assertEqual(analyze_panel(data,{**CFG,'scope_experiments':[]},[],Problem)['groups'],[])
        with self.assertRaises(Problem):analyze_panel(data,{**CFG,'scope_experiments':'Exp9'},[],Problem)

    def test_mouse_scope_matches_selected_controls_and_exclusions(self):
        data=snapshot({'Chow':[1,2,100],'ADF':[4,5,200]})
        cfg={**CFG,'scope_mouse_ids':['1','2','4','5']}
        result=analyze_panel(data,cfg,[],Problem)
        self.assertEqual({m for g in result['groups'] for m in g['mouse_ids']},{'1','2','4','5'})
        changed=analyze_panel(data,cfg,[{'mouse_id':'1','included':False}],Problem)
        self.assertEqual(next(g['n'] for g in changed['groups'] if g['group']=='Chow'),1)
        self.assertEqual(analyze_panel(data,{**CFG,'scope_mouse_ids':[]},[],Problem)['groups'],[])
        with self.assertRaises(Problem):analyze_panel(data,{**CFG,'scope_mouse_ids':'1'},[],Problem)

    def test_analytical_anova_and_all_pairs_family(self):
        result=analyze_panel(snapshot({'A':[1,2,3],'B':[4,5,6],'C':[7,8,9]}),CFG,[],Problem)
        self.assertEqual(result['status'],'ok');self.assertAlmostEqual(result['anova']['f'],27)
        self.assertAlmostEqual(result['anova']['p'],.001);self.assertEqual(len(result['pairs']),3)
        self.assertEqual(result['anova']['df_within'],6)
        self.assertEqual(result['method'],'One-way ANOVA + Tukey HSD')
    def test_tukey_matches_published_scipy_example(self):
        # https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.tukey_hsd.html
        result=analyze_panel(snapshot({'group0':[24.5,23.5,26.4,27.1,29.9],'group1':[28.4,34.2,29.5,32.2,30.1],'group2':[26.1,28.3,24.3,26.2,27.8]}),CFG,[],Problem)
        p={(r['a'],r['b']):r['p_adjusted'] for r in result['pairs']}
        self.assertAlmostEqual(p['group0','group1'],.014,delta=.0005)
        self.assertAlmostEqual(p['group0','group2'],.980,delta=.0005)
        self.assertAlmostEqual(p['group1','group2'],.020,delta=.0005)
    def test_selection_missing_zero_and_hidden_groups_change_the_analysis(self):
        data=snapshot({'A':[0,2,4,None,100],'B':[5,6,8],'hidden':[100,200,300]})
        data['mice'][4]['excluded']=1
        cfg={**CFG,'styles':{'hidden':{'include':False}}}
        baseline=copy.deepcopy(data);result=analyze_panel(data,cfg,[],Problem)
        self.assertEqual([g['n'] for g in result['groups']],[3,3])
        self.assertIn('1',result['groups'][0]['mouse_ids'])
        preview=analyze_panel(data,cfg,[{'mouse_id':'1','included':False}],Problem)
        self.assertEqual(preview['groups'][0]['n'],2);self.assertTrue(preview['preview'])
        self.assertNotEqual(result['data_sha256'],preview['data_sha256'])
        self.assertNotEqual(result['anova']['p'],preview['anova']['p'])
        self.assertIn('Tukey–Kramer',preview['method']);self.assertEqual(data,baseline)
    def test_insufficient_constant_and_repeated_data_are_not_reported_as_pvalues(self):
        for groups in [{'A':[1],'B':[2,3]},{'A':[1,1],'B':[2,2]},{'A':[None,None],'B':[2,3]}]:
            result=analyze_panel(snapshot(groups),CFG,[],Problem)
            self.assertEqual(result['status'],'unavailable');self.assertNotIn('anova',result)
        data=snapshot({'A':[1,2,3],'B':[4,5,6]});data['measurements'].append(dict(data['measurements'][0],replicate='2'))
        self.assertEqual(analyze_panel(data,{**CFG,'replicate':''},[],Problem)['status'],'unavailable')
        self.assertEqual(analyze_panel(data,{**CFG,'type':'line'},[],Problem)['status'],'unavailable')
    def test_revision_and_filters(self):
        data=snapshot({'A':[1,2,3],'B':[4,5,6]})
        with self.assertRaises(Problem) as error:analyze_board(data,{'revision':11,'panels':[{'key':'one','config':CFG}]},Problem)
        self.assertEqual(error.exception.status,409)
        result=analyze_panel(data,{**CFG,'experiment':'Exp2'},[],Problem)
        self.assertEqual(result['status'],'unavailable')
        out=analyze_board(data,{'revision':12,'panels':[{'key':'one','config':CFG}]},Problem)
        self.assertEqual(out['results'][0]['result']['revision'],12)

if __name__=='__main__':unittest.main()
