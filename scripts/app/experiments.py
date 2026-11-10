"""Experiment workspace: roster, source spreadsheets and explicit FCS associations."""
import json
from scripts.app.service import Problem,required,stamp

def workspace(store,experiment,include_fcs):
 with store.db() as c:
  names=[r[0] for r in c.execute("SELECT DISTINCT experiment FROM mice WHERE experiment<>'' ORDER BY experiment")]
  mice=[dict(r) for r in c.execute('SELECT * FROM mice WHERE experiment=? ORDER BY length(mouse_id),mouse_id',(experiment,))] if experiment else []
  ids={m['mouse_id'] for m in mice};uploads=set()
  for m in mice:
   try:
    src=json.loads(m['source']);uid=src.get('upload_id')
    if uid:uploads.add(uid)
   except (ValueError,TypeError):pass
  uploads|={r['upload_id'] for r in c.execute('SELECT upload_id,mouse_id FROM upload_mice') if r['mouse_id'] in ids}
  uploads|={r['upload_id'] for r in c.execute('SELECT DISTINCT upload_id,mouse_id FROM measurements WHERE upload_id IS NOT NULL') if r['mouse_id'] in ids}
  spreadsheets=[dict(r) for r in c.execute("SELECT id,filename,created_at,status FROM uploads WHERE status='committed'") if r['id'] in uploads]
  result={'experiments':names,'experiment':experiment,'mice':mice,'spreadsheets':spreadsheets,'fcs_enabled':include_fcs}
  if include_fcs:
   links=[dict(r) for r in c.execute('SELECT * FROM experiment_files WHERE experiment=?',(experiment,))]
   files=[dict(r) for r in c.execute('SELECT id,filename,kind,created_at FROM fcs_files ORDER BY created_at DESC')]
   runs=[dict(r) for r in c.execute('SELECT id,fcs_id,wsp_id,mouse_id,organ,status,created_at,edit_spec FROM fcs_runs ORDER BY created_at DESC')]
   fileids={r['file_id'] for r in links};selected={r['id'] for r in runs if r['mouse_id'] in ids or r['fcs_id'] in fileids}
   for r in runs:
    edit=json.loads(r['edit_spec'] or '{}');r['combined_name']=edit.get('combine_name')
   changed=True
   while changed:
    old=len(selected)
    for r in runs:
     if set(json.loads(r['edit_spec'] or '{}').get('combine_runs',[]))&selected:selected.add(r['id'])
    changed=len(selected)!=old
   analyses=[r for r in runs if r['id'] in selected]
   for r in analyses:fileids.update(x for x in [r['fcs_id'],r['wsp_id']] if x)
   result.update(files=[f for f in files if f['id'] in fileids],analyses=analyses,links=links,available_files=files)
  return result

def link_file(store,data,actor):
 exp=required(data.get('experiment'),'Experiment',100);fid=required(data.get('file_id'),'File',100);mid=str(data.get('mouse_id') or '').strip();reason=required(data.get('reason'),'Reason',500)
 with store.db() as c:
  c.execute('BEGIN IMMEDIATE')
  if c.execute('SELECT role FROM users WHERE id=?',(actor,)).fetchone()[0] not in ('admin','editor'):raise Problem('Editor access required.',403)
  if not c.execute('SELECT 1 FROM mice WHERE experiment=?',(exp,)).fetchone():raise Problem('Experiment not found.')
  if not c.execute('SELECT 1 FROM fcs_files WHERE id=?',(fid,)).fetchone():raise Problem('File not found.')
  if mid and not c.execute('SELECT 1 FROM mice WHERE mouse_id=? AND experiment=?',(mid,exp)).fetchone():raise Problem('Mouse ID is not in this experiment.')
  old=c.execute('SELECT * FROM experiment_files WHERE file_id=? AND experiment=? AND mouse_id=?',(fid,exp,mid)).fetchone()
  if data.get('remove') is True:
   if not old:raise Problem('Link not found.',404)
   c.execute('DELETE FROM experiment_files WHERE id=?',(old['id'],));store.event(c,actor,'unlink','fcs_experiment_link',old['id'],dict(old),None,reason)
  else:
   if old:return {'ok':True}
   ident=c.execute('INSERT INTO experiment_files(file_id,experiment,mouse_id,created_by,created_at) VALUES(?,?,?,?,?)',(fid,exp,mid,actor,stamp())).lastrowid
   store.event(c,actor,'link','fcs_experiment_link',ident,None,{'file_id':fid,'experiment':exp,'mouse_id':mid},reason)
 return {'ok':True}
