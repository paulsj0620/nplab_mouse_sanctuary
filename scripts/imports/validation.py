"""Read-only import review. No measurement, mouse or metric is written."""
import difflib,hashlib,hmac,json
from scripts.app.service import Problem,clean,number,metric_identity

def review(store,c,uid,mapping,actor):
 if not isinstance(mapping,dict):raise Problem('Invalid import mapping.')
 upload=c.execute('SELECT * FROM uploads WHERE id=? AND owner=?',(uid,actor)).fetchone()
 if not upload:raise Problem('Your upload was not found.',404)
 if upload['status']!='pending':raise Problem('This file has already been imported.',409)
 revision=c.execute('SELECT coalesce(max(id),0) FROM events').fetchone()[0]
 table=store.read_table(upload['filename'],upload['original'],mapping.get('sheet'));headers=table['headers'];facs=table.get('facs');issues=[];preview=[];seen={};new={};missing=0;observations=0;selected={}
 def issue(code,row,column,mouse,message):issues.append({'code':code,'row':row,'column':column,'mouse_id':mouse,'message':message})
 meta_only=mapping.get('metadata_only') is True
 if meta_only and facs:raise Problem('Use FACS Data to import this file.')
 rows_reviewed=0;meta_seen=set()
 specs=mapping.get('measurements',[])
 if not isinstance(specs,list) or (not specs and not meta_only) or (meta_only and bool(specs)) or len(specs)>200 or len(specs)*len(table['rows'])>100000:raise Problem('Select 1–200 columns, up to 100,000 observations.')
 if mapping.get('id_column') not in headers:raise Problem('Select the Mouse ID column.')
 for key in ['group_column','experiment_column','weeks_column','diet_column','replicate_column']:
  if mapping.get(key) and mapping[key] not in headers:raise Problem('Invalid column: '+key)
 if facs:
  candidates={s['row']:s for s in facs['samples'] if s['kind']=='sample'}
  if mapping.get('facs_reviewed') is not True:issue('mapping',None,'','','Confirm the FACS sample-to-mouse mapping.')
  for item in mapping.get('sample_rows',[]):
   n=item.get('row')
   if n not in candidates or n in selected:raise Problem('Invalid or duplicate FACS sample rows.')
   selected[n]={**candidates[n],'mouse_id':clean(item.get('mouse_id')),'group':clean(item.get('group'))}
  if not selected:raise Problem('Select samples to import.')
  organs={s['organ'] for s in selected.values()}
  if len(organs)!=1:raise Problem('Select one organ at a time.')
 mice={m['mouse_id']:dict(m) for m in c.execute('SELECT * FROM mice')};metrics={m['identity']:m['id'] for m in c.execute('SELECT id,identity FROM metrics')}
 existing={(m['mouse_id'],m['metric_id'],m['timepoint'],m['replicate']):m['value'] for m in c.execute('SELECT mouse_id,metric_id,timepoint,replicate,value FROM measurements')}
 prepared=[]
 for spec in specs:
  if not isinstance(spec,dict) or spec.get('column') not in headers:raise Problem('Invalid measurement column.')
  if spec.get('time_column') and spec['time_column'] not in headers:raise Problem('Invalid timepoint column.')
  meta={k:clean(spec.get(k)) for k in ('name','unit','organ','gate','parent_gate','denominator')}
  if facs:
   if spec['column'] not in {s['column'] for s in facs['specs']}:raise Problem('Sample names are not a measurement column.')
   if meta['organ'] not in organs:issue('definition',None,spec['column'],'','Organ does not match selected FACS samples.')
   if facs['needs_statistic']:meta.update(name=clean(mapping.get('facs_statistic')),unit=clean(mapping.get('facs_unit')),denominator='사용자 확인 계산값')
  if not meta['name'] or not meta['unit']:issue('definition',None,spec['column'],'','Metric name and unit are required.')
  if meta['gate'] and not all(meta[k] for k in ('organ','parent_gate','denominator')):issue('definition',None,spec['column'],'','Gate requires organ, parent gate and denominator.')
  prepared.append((spec,meta,metric_identity(meta,spec)))
 for n,values in zip(table['source_rows'],table['rows']):
  if facs and n not in selected:continue
  row=dict(zip(headers,values));mouse=selected[n]['mouse_id'] if facs else clean(row[mapping['id_column']]);group=selected[n]['group'] if facs else clean(row.get(mapping.get('group_column')))
  if not mouse or len(mouse)>100:issue('mouse_id',n,mapping['id_column'],mouse,'Mouse ID must contain 1–100 characters.');continue
  found=mice.get(mouse);rows_reviewed+=1
  if meta_only:
   if mouse in meta_seen:issue('duplicate_file',n,mapping['id_column'],mouse,'Duplicate Mouse ID in metadata file.')
   meta_seen.add(mouse)
   if not found and not group:group=clean(row.get(mapping.get('diet_column')))
   if not found and not clean(row.get(mapping.get('experiment_column'))):issue('experiment',n,'Exp',mouse,'Exp is required for new metadata-only mice.')
   if len(preview)<100:preview.append({'row':n,'mouse_id':mouse,'metric':'Mouse metadata','unit':'','timepoint':'','replicate':'','value':' / '.join([clean(row.get(mapping.get('experiment_column'))),clean(row.get(mapping.get('diet_column'))),clean(row.get(mapping.get('weeks_column')))]),'new_mouse':not bool(found)})
  if not found:
   if mouse not in new:
    new[mouse]={'mouse_id':mouse,'group':group,'row':n,'suggestions':difflib.get_close_matches(mouse,list(mice),n=3,cutoff=.6)}
   elif group!=new[mouse]['group']:issue('group_mismatch',n,'group',mouse,'Conflicting groups for this new mouse in the file.')
   if not group:issue('unknown_mouse',n,'group',mouse,'ID is not in the roster. A group is required to register it.')
   elif mapping.get('allow_new_mice') is not True:issue('unknown_mouse',n,mapping['id_column'],mouse,'ID is not in the roster. Correct the ID or explicitly allow new mice.')
  else:
   for field,key,incoming in [('group_name','group_column',group),('experiment','experiment_column',clean(row.get(mapping.get('experiment_column')))),('diet','diet_column',clean(row.get(mapping.get('diet_column')))),('weeks','weeks_column',clean(row.get(mapping.get('weeks_column'))))]:
    if incoming and incoming!=str(found[field]):issue('roster_mismatch',n,mapping.get(key) or field,mouse,f'Roster {field}: {found[field]}; file: {incoming}. Review the ID or roster metadata.')
  for spec,meta,identity in prepared:
   tp=clean(row.get(spec.get('time_column'))) if spec.get('time_column') else clean(spec.get('timepoint')) or 'endpoint';rep=clean(row.get(mapping.get('replicate_column'))) or '1';key=(mouse,identity,tp,rep);observations+=1
   if not tp:issue('timepoint',n,spec['column'],mouse,'Timepoint is blank.')
   if key in seen:issue('duplicate_file',n,spec['column'],mouse,f'Duplicate mouse/metric/timepoint/replicate in file; first seen at row {seen[key]}.')
   else:seen[key]=n
   dbkey=(mouse,metrics.get(identity),tp,rep)
   if dbkey in existing:issue('duplicate_database',n,spec['column'],mouse,f'Already stored: {meta["name"]}, {tp}, replicate {rep}; existing value {existing[dbkey]}. Existing data will not be overwritten.')
   v=row[spec['column']];v='' if facs and v.lower()=='n/a' else v
   try:val=number(v,'Blank imported cell' if v=='' else '',meta['unit'])
   except Problem as e:issue('invalid_value',n,spec['column'],mouse,e.message);val=None
   if v=='':missing+=1
   if len(preview)<100:preview.append({'row':n,'mouse_id':mouse,'metric':meta['name'],'unit':meta['unit'],'timepoint':tp,'replicate':rep,'value':val,'new_mouse':not bool(found)})
 if not observations and not (meta_only and rows_reviewed):issue('empty',None,'','','No observations selected.')
 payload=json.dumps([uid,actor,revision,mapping],sort_keys=True,ensure_ascii=False).encode()
 token=hmac.new(store.import_review_secret,payload,hashlib.sha256).hexdigest() if not issues else None
 return {'ok':not issues,'issue_count':len(issues),'issues':issues[:300],'new_mice':list(new.values())[:300],'new_mouse_count':len(new),'missing_count':missing,'observations':observations,'metadata_only':meta_only,'rows_reviewed':rows_reviewed,'preview':preview,'review_token':token}
