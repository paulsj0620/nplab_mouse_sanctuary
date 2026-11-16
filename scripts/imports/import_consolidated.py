"""Audited local-only consolidated workbook import; dry-run unless --apply."""
import argparse, hashlib, json, sqlite3, collections
from pathlib import Path
import openpyxl
from scripts.app.service import Store, metric_identity, number, stamp, dump

def run(db, workbook, apply=False):
    db=Path(db).resolve();workbook=Path(workbook).resolve()
    expected=Path(__file__).resolve().parents[2]/'data/lab.sqlite'
    if apply and db!=expected:raise ValueError('Apply is restricted to the development database.')
    w=openpyxl.load_workbook(workbook,read_only=True,data_only=True)
    def records(sheet):
        it=iter(w[sheet].values);headers=next(it)
        return [(n,dict(zip(headers,row))) for n,row in enumerate(it,2) if any(v is not None for v in row)]
    mice=records('Mice');metrics={m['metric_id']:m for _,m in records('Metric definitions')};measurements=records('Measurements')
    provenance=collections.defaultdict(list)
    for _,r in records('Provenance'):provenance[r['record_id']].append(r)
    assert len(mice)==183 and len({str(m['mouse_id']) for _,m in mice})==183
    store=Store(db,existing_only=True);raw=workbook.read_bytes();sha=hashlib.sha256(raw).hexdigest();uid='consolidated-'+sha[:24]
    report={'workbook_sha256':sha,'status_counts':dict(collections.Counter(r['status'] for _,r in measurements)),'inserted':0,'duplicates':0,'conflicts':[],'invalid':[],'qa_excluded':[],'roster_updated':0}
    with store.db() as c:
        c.execute('BEGIN IMMEDIATE')
        actor=c.execute("select id from users where username='qa_admin' and role='admin'").fetchone()[0]
        if c.execute('select 1 from uploads where id=?',(uid,)).fetchone():raise ValueError('This workbook was already imported.')
        reason='Development test: import reviewed consolidated workbook; preserve existing observations'
        for mid in ('QA-001','QA-002','QA-003','QA-004','QA-UI-001','QA-UI-002'):
            old=c.execute('select * from mice where mouse_id=?',(mid,)).fetchone()
            if old and not old['excluded']:
                c.execute('update mice set excluded=1,version=version+1 where mouse_id=?',(mid,));store.event(c,actor,'exclude','mouse',mid,dict(old),dict(c.execute('select * from mice where mouse_id=?',(mid,)).fetchone()),reason);report['qa_excluded'].append(mid)
        roster={str(m['mouse_id']) for _,m in mice}
        for _,m in mice:
            mid=str(m['mouse_id']);old=c.execute('select * from mice where mouse_id=?',(mid,)).fetchone()
            if not old:raise ValueError('Roster mouse missing: '+mid)
            # Retain existing display group; normalized original group and descriptions stay in provenance.
            fields={'experiment':str(m['experiment'] or ''),'diet':str(m['diet'] or ''),'weeks':str(m['weeks'] or ''),'source':dump({'consolidated_upload':uid,'metadata':m,'previous_source':old['source']})}
            c.execute('update mice set experiment=?,diet=?,weeks=?,source=?,version=version+1 where mouse_id=?',(*fields.values(),mid))
            store.event(c,actor,'edit','mouse',mid,dict(old),dict(c.execute('select * from mice where mouse_id=?',(mid,)).fetchone()),reason);report['roster_updated']+=1
        c.execute('insert into uploads(id,filename,sha256,original,owner,created_at,status,mapping) values(?,?,?,?,?,?,?,?)',(uid,workbook.name,sha,raw,actor,stamp(),'committed','{}'))
        specs={};sources={}
        for row,r in measurements:
            if r['status']!='ready':continue
            mid=str(r['mouse_id']);m=metrics[r['metric_id']]
            gate=str(m.get('gate') or '');meta={k:str(m.get(k) or '') for k in ('name','unit','organ','gate','parent_gate','denominator')}
            meta['parent_gate']=gate.rpartition('/')[0] or ('All events' if gate else '')
            if meta['name'].startswith('MFI Geometric Mean ('):
                meta['name']=meta['name'][4:]
                meta['denominator']=meta['denominator'] or 'Not applicable (fluorescence intensity)'
            spec={**meta,'panel':str(m.get('panel') or ''),'column':next((p['source_header'] for p in provenance[r['record_id']] if p.get('source_header')),meta['name'])}
            try:
                if mid not in roster:raise ValueError('Unknown mouse')
                if not meta['name'] or not meta['unit']:raise ValueError('Missing metric name/unit')
                if gate and (not meta['organ'] or not meta['denominator']):raise ValueError('Missing gating definition')
                value=number(r['value'],'',meta['unit'])
                if value is None:raise ValueError('Ready value is empty')
            except Exception as e:report['invalid'].append({'record_id':r['record_id'],'reason':str(e)});continue
            identity=metric_identity(meta,spec)
            existing_metric=c.execute('select id from metrics where identity=?',(identity,)).fetchone()
            if existing_metric:
                existing=c.execute('select id,value from measurements where mouse_id=? and metric_id=? and timepoint=? and replicate=?',(mid,existing_metric[0],str(r['timepoint']),str(r['replicate']))).fetchone()
                if existing:
                    if existing['value']==value:report['duplicates']+=1
                    else:report['conflicts'].append({'record_id':r['record_id'],'existing_id':existing['id'],'existing_value':existing['value'],'incoming_value':value})
                    continue
            c.execute('insert or ignore into metrics(identity,name,unit,organ,gate,parent_gate,denominator) values(?,?,?,?,?,?,?)',(identity,*meta.values()))
            metric=c.execute('select id from metrics where identity=?',(identity,)).fetchone()[0]
            rid=c.execute('insert into measurements(mouse_id,metric_id,timepoint,replicate,value,missing_reason,upload_id,source_row) values(?,?,?,?,?,?,?,?)',(mid,metric,str(r['timepoint']),str(r['replicate']),value,'',uid,row)).lastrowid
            store.event(c,actor,'create','measurement',rid,None,{'record_id':r['record_id'],'value':value,'mouse_id':mid,'metric_id':metric,'source_row':row},reason)
            sources[str(row)]={'record_id':r['record_id'],'sources':provenance[r['record_id']]};specs[identity]=spec;report['inserted']+=1
        for mid in roster:c.execute('insert or ignore into upload_mice values(?,?)',(uid,mid))
        c.execute('update uploads set mapping=? where id=?',(dump({'consolidated':True,'sheet':'Measurements','measurements':list(specs.values()),'provenance':sources,'report':report}),uid))
        store.event(c,actor,'import','upload',uid,None,report,reason)
        if c.execute('pragma foreign_key_check').fetchall():raise ValueError('Foreign key check failed')
        if not apply:c.rollback()
    w.close();return report
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--db',required=True);p.add_argument('--workbook',required=True);p.add_argument('--apply',action='store_true');p.add_argument('--report',required=True);a=p.parse_args()
    result=run(a.db,a.workbook,a.apply);Path(a.report).write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:len(v) if isinstance(v,list) else v for k,v in result.items()},ensure_ascii=False,indent=2))
