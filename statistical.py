"""Independent-group one-way ANOVA and Tukey HSD/Kramer on one graph's data."""
import hashlib, json, math
from datetime import datetime, timezone

def analyze_panel(snapshot, config, overrides, Problem):
    unavailable=lambda message,**extra: {'status':'unavailable','message':message,**extra}
    if config.get('type')=='line':return unavailable('Time courses require repeated-measures analysis. Use a single-timepoint bar or scatter graph for this test.')
    if config.get('grouping') not in ('group_name','diet'):return unavailable('Check the grouping field.')
    try:metric_id=int(config.get('metric'))
    except (ValueError,TypeError):return unavailable('Select a metric.')
    if not any(m['id']==metric_id for m in snapshot['metrics']):return unavailable('Metric not found.')
    selected={}
    for row in overrides:
        if not isinstance(row,dict) or not isinstance(row.get('included'),bool) or not isinstance(row.get('mouse_id'),str):raise Problem('Invalid sample selection')
        if row['mouse_id'] in selected:raise Problem('Duplicate IDs in the sample selection.')
        selected[row['mouse_id']]=row['included']
    known={m['mouse_id'] for m in snapshot['mice']}
    if set(selected)-known:raise Problem('A selected sample ID was not found.')
    roster={m['mouse_id']:m for m in snapshot['mice'] if (not config.get('experiment') or m['experiment']==config['experiment']) and (not config.get('weeks') or str(m['weeks'])==str(config['weeks']))}
    styles=config.get('styles',{})
    if not isinstance(styles,dict):raise Problem('Invalid group settings')
    groups={};seen=set()
    for row in snapshot['measurements']:
        if row['metric_id']!=metric_id or row['mouse_id'] not in roster:continue
        if config.get('replicate') and row['replicate']!=config['replicate']:continue
        if config.get('timepoint') and row['timepoint']!=config['timepoint']:continue
        mouse=roster[row['mouse_id']];group=mouse.get(config['grouping']) or '미기재'
        if not isinstance(styles.get(group,{}),dict):raise Problem('Invalid group settings')
        style=styles.get(group,{})
        if 'include' in style and not isinstance(style['include'],bool):raise Problem('Invalid group inclusion status')
        if type(style.get('order',0)) not in (int,float) or not math.isfinite(style.get('order',0)):raise Problem('Invalid group order')
        if styles.get(group,{}).get('include') is False:continue
        if not selected.get(mouse['mouse_id'],not mouse['excluded']) or row['value'] is None:continue
        if mouse['mouse_id'] in seen:return unavailable('Multiple timepoints or replicates of a mouse are mixed. Select one timepoint and one replicate.')
        seen.add(mouse['mouse_id'])
        if not math.isfinite(row['value']):return unavailable('Only finite measurement values can be analyzed.')
        groups.setdefault(group,[]).append({'mouse_id':mouse['mouse_id'],'value':row['value']})
    ordered=sorted(groups,key=lambda g:(styles.get(g,{}).get('order',0),g))
    counts=[{'group':g,'n':len(groups[g]),'mouse_ids':[r['mouse_id'] for r in groups[g]]} for g in ordered]
    if len(ordered)<2:return unavailable('At least two groups with measured values are required.',groups=counts)
    if len(ordered)>20:return unavailable('A graph can compare at most 20 groups.',groups=counts)
    if any(len(groups[g])<2 for g in ordered):return unavailable('Every comparison group must contain at least two mice.',groups=counts)
    values=[[r['value'] for r in groups[g]] for g in ordered]
    within=sum(sum((v-sum(vs)/len(vs))**2 for v in vs) for vs in values)
    if within==0:return unavailable('The test cannot be calculated because all within-group variances are zero.',groups=counts)
    try:
        import scipy
        from scipy.stats import f_oneway,tukey_hsd
    except ImportError:return unavailable('Statistical packages are required. Install requirements.txt in the server environment.')
    anova=f_oneway(*values,equal_var=True,nan_policy='raise')
    tukey=tukey_hsd(*values,equal_var=True)
    if not math.isfinite(float(anova.statistic)) or not math.isfinite(float(anova.pvalue)):return unavailable('A valid ANOVA result could not be calculated.',groups=counts)
    pairs=[]
    for i,a in enumerate(ordered):
        for j in range(i+1,len(ordered)):
            p=float(tukey.pvalue[i,j]);difference=float(tukey.statistic[i,j])
            if not math.isfinite(p) or not 0<=p<=1:return unavailable('Valid Tukey p-values could not be calculated.',groups=counts)
            pairs.append({'a':a,'b':ordered[j],'p_adjusted':p,'mean_difference':difference})
    engine='Tukey HSD' if len({len(vs) for vs in values})==1 else 'Tukey–Kramer'
    fingerprint=hashlib.sha256(json.dumps({'metric':metric_id,'groups':groups},sort_keys=True).encode()).hexdigest()
    return {'status':'ok','method':'One-way ANOVA + '+engine,'engine':'SciPy '+scipy.__version__,'assumptions':['independent observations','normal populations','equal variances'],'groups':counts,'anova':{'f':float(anova.statistic),'p':float(anova.pvalue),'df_between':len(ordered)-1,'df_within':sum(map(len,values))-len(ordered)},'pairs':pairs,'correction_scope':'all pairwise comparisons within this graph; no across-graph adjustment','preview':bool(overrides),'data_sha256':fingerprint,'revision':snapshot['revision'],'calculated_at':datetime.now(timezone.utc).isoformat()}

def analyze_board(snapshot,request,Problem):
    if request.get('revision')!=snapshot['revision']:raise Problem('Data have changed. Reload the latest data and recalculate.',409)
    panels=request.get('panels');overrides=request.get('sample_selection',[])
    if not isinstance(panels,list) or not 1<=len(panels)<=8 or not isinstance(overrides,list) or len(overrides)>10000:raise Problem('Invalid analysis request')
    results=[];seen=set()
    for item in panels:
        if not isinstance(item,dict) or not isinstance(item.get('key'),str) or len(item['key'])>20000 or not isinstance(item.get('config'),dict):raise Problem('Invalid graph settings')
        if item['key'] in seen:raise Problem('Duplicate analysis requests.')
        seen.add(item['key']);results.append({'key':item['key'],'result':analyze_panel(snapshot,item['config'],overrides,Problem)})
    return {'revision':snapshot['revision'],'results':results}
