"""Append-only original-file catalogue, resumable binary upload and serial analysis queue."""
import hashlib,json,os,re,secrets,shutil,sqlite3,subprocess,threading,time
from pathlib import Path
from scripts.paths import ROOT as PROJECT_ROOT
from scripts.app.service import Problem,stamp,dump,required
MAX_FILE=2*1024**3
CHUNK=2*1024**2

def digest(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for b in iter(lambda:f.read(CHUNK),b''):h.update(b)
 return h.hexdigest()

def durable_dir(path):
 fd=os.open(path,os.O_RDONLY)
 try:os.fsync(fd)
 finally:os.close(fd)

def immutable_copy(source,target,sha):
 target=Path(target);target.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
 if target.exists():
  if digest(target)!=sha:raise Problem('Original-file integrity check failed. No file was overwritten.',500)
  return
 temp=target.parent/('.'+secrets.token_hex(16)+'.tmp')
 try:
  with open(source,'rb') as src,open(temp,'xb') as dst:
   shutil.copyfileobj(src,dst,CHUNK);dst.flush();os.fsync(dst.fileno())
  if digest(temp)!=sha:raise Problem('File copy verification failed.',500)
  temp.chmod(0o400)
  try:os.link(temp,target)
  except FileExistsError:
   if digest(target)!=sha:raise Problem('Original-file integrity check failed.',500)
  durable_dir(target.parent)
 finally:
  if temp.exists():temp.unlink()

class FCSLibrary:
 def __init__(self,store,root=None,worker_python=None,start_worker=True):
  self.store=store;self.root=Path(root or Path(store.path).parent/'fcs');self.root.mkdir(mode=0o700,parents=True,exist_ok=True)
  for name in ['objects','staging','runs','mirror']: (self.root/name).mkdir(mode=0o700,exist_ok=True)
  self.worker_python=str(worker_python or PROJECT_ROOT/'.fcs-venv/bin/python')
  self.lock=threading.RLock();self.wake=threading.Event();self.stop=threading.Event()
  with store.db() as c:
   c.executescript('''
CREATE TABLE IF NOT EXISTS fcs_transfers(id TEXT PRIMARY KEY,owner INTEGER NOT NULL REFERENCES users(id),filename TEXT NOT NULL,size INTEGER NOT NULL,received INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL,file_id TEXT);
CREATE TABLE IF NOT EXISTS fcs_files(id TEXT PRIMARY KEY,owner INTEGER NOT NULL REFERENCES users(id),filename TEXT NOT NULL,kind TEXT NOT NULL,size INTEGER NOT NULL,sha256 TEXT NOT NULL,created_at TEXT NOT NULL,note TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS fcs_external(file_id TEXT PRIMARY KEY REFERENCES fcs_files(id),source_uri TEXT NOT NULL);
CREATE TRIGGER IF NOT EXISTS fcs_external_no_update BEFORE UPDATE ON fcs_external BEGIN SELECT RAISE(ABORT,'External source identity is immutable'); END;
CREATE TRIGGER IF NOT EXISTS fcs_external_no_delete BEFORE DELETE ON fcs_external BEGIN SELECT RAISE(ABORT,'External source identity is retained'); END;
CREATE TABLE IF NOT EXISTS fcs_runs(id TEXT PRIMARY KEY,owner INTEGER NOT NULL REFERENCES users(id),fcs_id TEXT NOT NULL REFERENCES fcs_files(id),wsp_id TEXT REFERENCES fcs_files(id),mouse_id TEXT REFERENCES mice(mouse_id),organ TEXT NOT NULL,status TEXT NOT NULL,created_at TEXT NOT NULL,finished_at TEXT,error TEXT,result TEXT);
CREATE TRIGGER IF NOT EXISTS fcs_original_no_update BEFORE UPDATE ON fcs_files BEGIN SELECT RAISE(ABORT,'FCS originals are immutable'); END;
CREATE TRIGGER IF NOT EXISTS fcs_original_no_delete BEFORE DELETE ON fcs_files BEGIN SELECT RAISE(ABORT,'FCS originals are immutable'); END;
CREATE TRIGGER IF NOT EXISTS fcs_run_no_delete BEFORE DELETE ON fcs_runs BEGIN SELECT RAISE(ABORT,'FCS runs are retained'); END;
CREATE TRIGGER IF NOT EXISTS fcs_run_identity_no_update BEFORE UPDATE OF owner,fcs_id,wsp_id,mouse_id,organ,created_at ON fcs_runs BEGIN SELECT RAISE(ABORT,'analysis provenance is immutable'); END;
CREATE TRIGGER IF NOT EXISTS fcs_run_finished_no_update BEFORE UPDATE ON fcs_runs WHEN OLD.status IN ('done','failed') BEGIN SELECT RAISE(ABORT,'finished analysis is immutable'); END;
''')
   if 'edit_spec' not in [r[1] for r in c.execute('PRAGMA table_info(fcs_runs)')]:c.execute('ALTER TABLE fcs_runs ADD COLUMN edit_spec TEXT')
   c.execute("CREATE TRIGGER IF NOT EXISTS fcs_edit_spec_immutable BEFORE UPDATE OF edit_spec ON fcs_runs BEGIN SELECT RAISE(ABORT,'gate edit provenance is immutable'); END")
   c.execute("UPDATE fcs_runs SET status='queued',error='Resuming after server restart' WHERE status='running'")
  if start_worker:self.thread=threading.Thread(target=self.loop,daemon=True,name='fcs-analysis');self.thread.start()
 def transfer(self,tid,actor):
  with self.store.db() as c:r=c.execute('SELECT * FROM fcs_transfers WHERE id=? AND owner=?',(tid,actor)).fetchone()
  if not r:raise Problem('Upload not found for this account.',404)
  return dict(r)
 def begin(self,d,actor):
  name=required(d.get('filename'),'Filename',250)
  if '/' in name or '\\' in name or '\x00' in name:raise Problem('Use a plain filename.')
  ext=Path(name).suffix.lower()
  if ext not in ('.fcs','.wsp'):raise Problem('Choose an FCS or WSP file.')
  size=d.get('size')
  if type(size)!=int or size<=0 or size>MAX_FILE or (ext=='.wsp' and size>100*1024**2):raise Problem('Limit: 2 GB per FCS file, 100 MB per WSP file.')
  with self.lock,self.store.db() as c:
   pending=c.execute('SELECT coalesce(sum(size-received),0) FROM fcs_transfers WHERE file_id IS NULL').fetchone()[0]
   if shutil.disk_usage(self.root).free<3*(size+pending)+1024**3:raise Problem('Not enough disk space for verified original copies.',507)
   tid=secrets.token_hex(16)
   with open(self.root/'staging'/tid,'xb') as f:f.flush();os.fsync(f.fileno())
   durable_dir(self.root/'staging')
   c.execute('INSERT INTO fcs_transfers(id,owner,filename,size,created_at) VALUES(?,?,?,?,?)',(tid,actor,name,size,stamp()))
  return self.transfer(tid,actor)
 def append(self,tid,actor,offset,body):
  if type(offset)!=int or offset<0:raise Problem('Invalid upload offset.')
  if not body or len(body)>CHUNK:raise Problem('Invalid upload chunk size.')
  with self.lock:
   t=self.transfer(tid,actor)
   if t['file_id']:raise Problem('Upload is already finalized.',409)
   path=self.root/'staging'/tid
   if offset<t['received']:
    with open(path,'rb') as f:f.seek(offset);previous=f.read(len(body))
    if offset<0 or offset+len(body)>t['received'] or previous!=body:raise Problem('Upload chunk conflict.',409)
    return t
   if offset!=t['received'] or offset+len(body)>t['size']:raise Problem('Upload offset mismatch. Resume from the saved offset.',409)
   with open(path,'r+b') as f:
    if os.fstat(f.fileno()).st_size<t['received']:raise Problem('Staged upload is incomplete on disk.',500)
    f.truncate(t['received']);f.seek(offset);f.write(body);f.flush();os.fsync(f.fileno())
   with self.store.db() as c:c.execute('UPDATE fcs_transfers SET received=? WHERE id=?',(offset+len(body),tid))
   return self.transfer(tid,actor)
 def finish(self,tid,actor):
  with self.lock:
   t=self.transfer(tid,actor)
   if t['file_id']:return self.file(t['file_id'])
   if t['received']!=t['size']:raise Problem('Upload is incomplete.',409)
   path=self.root/'staging'/tid
   if path.stat().st_size!=t['size']:raise Problem('Upload size verification failed.',409)
   sha=digest(path);kind=Path(t['filename']).suffix.lower()[1:]
   # Type validation before publication. Original bytes are never parsed as executable content.
   if kind=='fcs':
    with path.open('rb') as f:header=f.read(58)
    if header[:6] not in (b'FCS2.0',b'FCS3.0',b'FCS3.1'):raise Problem('Not a supported FCS file.')
   else:
    from scripts.fcs.fcs_worker import workspace_metadata
    try:workspace_metadata(path)  # safe XML only; no external files are followed
    except Exception as e:raise Problem('Cannot read this WSP: '+str(e)[:250])
   immutable_copy(path,self.root/'objects'/sha,sha)
   immutable_copy(path,self.root/'mirror'/sha,sha)
   fid=secrets.token_hex(16)
   with self.store.db() as c:
    c.execute('BEGIN IMMEDIATE')
    c.execute('INSERT INTO fcs_files VALUES(?,?,?,?,?,?,?,?)',(fid,actor,t['filename'],kind,t['size'],sha,stamp(),'Original preserved; local mirror verified'))
    c.execute('UPDATE fcs_transfers SET file_id=? WHERE id=?',(fid,tid))
    self.store.event(c,actor,'upload','fcs_file',fid,None,{'filename':t['filename'],'sha256':sha,'size':t['size']},'Shared FCS library upload; original bytes preserved')
   # Staging retained for recovery. No deletion endpoint exists.
   return self.file(fid)
 def file(self,fid):
  with self.store.db() as c:r=c.execute('SELECT f.*,u.username,CASE WHEN EXISTS(SELECT 1 FROM fcs_external e WHERE e.file_id=f.id) THEN "smb" ELSE "local" END AS storage FROM fcs_files f JOIN users u ON f.owner=u.id WHERE f.id=?',(fid,)).fetchone()
  if not r:raise Problem('File not found.',404)
  return dict(r)
 def source(self,fid):
  f=self.file(fid)
  with self.store.db() as c:external=c.execute('SELECT source_uri FROM fcs_external WHERE file_id=?',(fid,)).fetchone()
  if external:
   info=self.probe_reference(external['source_uri'])
   if info['sha256']!=f['sha256'] or info['size']!=f['size']:raise Problem('The SMB original has changed since linking. Link it again as a new file version; existing analysis provenance is unchanged.',409)
   return f,Path(info['path'])
  p=self.root/'objects'/f['sha256']
  if not p.is_file() or digest(p)!=f['sha256']:raise Problem('Original integrity check failed. Restore from a verified backup.',500)
  return f,p
 def catalog(self):
  with self.store.db() as c:
   files=[dict(r) for r in c.execute('SELECT f.*,u.username,CASE WHEN EXISTS(SELECT 1 FROM fcs_external e WHERE e.file_id=f.id) THEN "smb" ELSE "local" END AS storage FROM fcs_files f JOIN users u ON f.owner=u.id ORDER BY f.created_at DESC')]
   runs=[dict(r) for r in c.execute('SELECT r.id,r.owner,u.username,r.fcs_id,r.wsp_id,r.mouse_id,r.organ,r.status,r.created_at,r.error,r.edit_spec FROM fcs_runs r JOIN users u ON r.owner=u.id ORDER BY r.created_at DESC LIMIT 100')]
  return {'files':files,'runs':runs,'chunk_size':CHUNK,'max_file':MAX_FILE,'backup':'Local uploads have a verified mirror on this Mac. Linked SMB originals are not copied or backed up by this app; the share must remain available. Analysis caches use local space.'}
 def workspace_files(self,wid):
  from scripts.fcs.fcs_references import references
  w,path=self.source(wid)
  if w['kind']!='wsp':raise Problem('Select a WSP file.')
  return {'workspace':w,'samples':references(path,self.catalog()['files'])}
 def probe_reference(self,uri):
  import sys
  try:done=subprocess.run([sys.executable,'-m','scripts.fcs.fcs_probe',uri],cwd=PROJECT_ROOT,capture_output=True,timeout=120)
  except subprocess.TimeoutExpired:raise Problem('SMB read timed out. Check the mounted share and network volume permissions.',504)
  try:info=json.loads(done.stdout)
  except (ValueError,UnicodeDecodeError):raise Problem('Cannot read the SMB original.',409)
  if done.returncode or 'error' in info:raise Problem(info.get('error','Cannot read the SMB original.'),409)
  return info
 def link_reference(self,d,actor):
  rows=self.workspace_files(d.get('wsp_id'))['samples']
  matches=[r for r in rows if r['sample_id']==d.get('sample_id')]
  if len(matches)!=1:raise Problem('Select a unique workspace sample.')
  row=matches[0]
  if row['status']!='Available':raise Problem('SMB original is not available.',409)
  info=self.probe_reference(row['original_uri'])
  with self.lock,self.store.db() as c:
   c.execute('BEGIN IMMEDIATE')
   existing=c.execute('SELECT f.id FROM fcs_files f JOIN fcs_external e ON e.file_id=f.id WHERE e.source_uri=? AND f.sha256=?',(row['original_uri'],info['sha256'])).fetchone()
   fid=existing['id'] if existing else secrets.token_hex(16)
   if not existing:
    c.execute('INSERT INTO fcs_files VALUES(?,?,?,?,?,?,?,?)',(fid,actor,row['name'],'fcs',info['size'],info['sha256'],stamp(),'Linked SMB original; no local original copy or mirror'))
    c.execute('INSERT INTO fcs_external VALUES(?,?)',(fid,row['original_uri']))
   self.store.event(c,actor,'link_reference','fcs_file',fid,None,{'wsp_id':d['wsp_id'],'sample_id':row['sample_id'],'source_uri':row['original_uri'],'sha256':info['sha256']},'Read-only SMB reference; no original bytes copied')
  return self.file(fid)
 def import_reference(self,d,actor):
  rows=self.workspace_files(d.get('wsp_id'))['samples']
  matches=[r for r in rows if r['sample_id']==d.get('sample_id')]
  if len(matches)!=1:raise Problem('Select a unique workspace sample.')
  row=matches[0]
  if row['status']!='Available':raise Problem('The referenced FCS is not available on the approved SMB share.',409)
  if not row['size'] or row['size']>MAX_FILE:raise Problem('FCS limit: 2 GB.',413)
  transfer=self.begin({'filename':row['name'],'size':row['size']},actor)
  import sys
  destination=self.root/'staging'/transfer['id']
  try:
   done=subprocess.run([sys.executable,'-m','scripts.fcs.fcs_copy',row['original_uri'],str(destination),str(row['size'])],cwd=PROJECT_ROOT,capture_output=True,timeout=120)
  except subprocess.TimeoutExpired:
   raise Problem('SMB read timed out after 2 minutes. Check that the share is connected and macOS permits the server to read network volumes. No file was published; retry when access is ready.',504)
  try:copied=json.loads(done.stdout)
  except (ValueError,UnicodeDecodeError):copied={'error':'Could not copy the SMB source.'}
  if done.returncode or 'error' in copied:raise Problem(copied.get('error','SMB copy failed.'),422)
  if destination.stat().st_size!=row['size'] or digest(destination)!=copied['sha256']:raise Problem('SMB copy integrity verification failed.',422)
  with self.store.db() as c:c.execute('UPDATE fcs_transfers SET received=? WHERE id=?',(row['size'],transfer['id']))
  copied_hash=digest(self.root/'staging'/transfer['id'])
  with self.store.db() as c:
   existing=c.execute("SELECT id FROM fcs_files WHERE kind='fcs' AND sha256=? ORDER BY created_at LIMIT 1",(copied_hash,)).fetchone()
   if existing:c.execute('UPDATE fcs_transfers SET file_id=? WHERE id=?',(existing['id'],transfer['id']))
  file=self.file(existing['id']) if existing else self.finish(transfer['id'],actor)
  with self.store.db() as c:
   self.store.event(c,actor,'import_reference','fcs_file',file['id'],None,{'wsp_id':d['wsp_id'],'sample_id':row['sample_id'],'source_uri':row['original_uri'],'sha256':file['sha256']},'Copied from approved SMB path; source unchanged')
  return file
 def export_workspace(self,rid,actor):
  r=self.run(rid)
  if r['status']!='done':raise Problem('Select a completed analysis.',409)
  if not r['wsp_id']:raise Problem('FlowJo export currently requires an imported WSP. Attach its original workspace and reanalyze.',422)
  f,fp=self.source(r['fcs_id']);w,wp=self.source(r['wsp_id'])
  import tempfile
  with self.lock,tempfile.TemporaryDirectory(prefix='mouse-wsp-export-') as tmp:
   folder=Path(tmp);output=folder/'workspace.wsp';report=folder/'report.json'
   spec={'wsp_path':str(wp.resolve()),'filename':f['filename'],'run_id':r['id'],'result':r['result'],'edit_spec':json.loads(r['edit_spec']) if r.get('edit_spec') else None,'output':str(output),'report':str(report)}
   if r['result'].get('combined'):
    spec['combine_sources']=[];spec['artifact_dir']=str((self.root/r['result']['artifact_dir']).resolve())
    for source_id in spec['edit_spec']['combine_runs']:
     sr=self.run(source_id);sf,sfp=self.source(sr['fcs_id'])
     if not sr['wsp_id']:raise Problem('Combined WSP export requires WSP-backed source analyses.',422)
     sw,swp=self.source(sr['wsp_id'])
     spec['combine_sources'].append({'filename':sf['filename'],'fcs_path':str(sfp.resolve()),'wsp_path':str(swp.resolve()),'result':sr['result'],'file':sf})
   request=folder/'request.json';request.write_text(dump(spec))
   try:
    done=subprocess.run([self.worker_python,'-m','scripts.fcs.fcs_export',str(request)],cwd=PROJECT_ROOT,capture_output=True,timeout=900 if spec.get('combine_sources') else 120,env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'})
   except subprocess.TimeoutExpired:raise Problem('WSP export timed out. Original files and analysis are unchanged.',422)
   result=json.loads(report.read_text()) if report.exists() else {'error':'WSP export validation failed.'}
   if done.returncode or 'error' in result:raise Problem(result.get('error','WSP export validation failed.'),422)
   for source in spec.get('combine_sources',[]):self.source(source['file']['id'])
   filename='MouseSanctuary-'+Path(f['filename']).stem[:100]+'-'+rid[:8]+'.wsp'
   transfer=self.begin({'filename':filename,'size':output.stat().st_size},actor);offset=0
   with output.open('rb') as source:
    while True:
     block=source.read(CHUNK)
     if not block:break
     self.append(transfer['id'],actor,offset,block);offset+=len(block)
   file=self.finish(transfer['id'],actor)
   with self.store.db() as c:
    self.store.event(c,actor,'export','fcs_file',file['id'],None,{'source_run':rid,'source_wsp':w['id'],'source_fcs':f['id'],'export_sha256':file['sha256'],'validation':result},'FlowJo WSP export; original compensation/transforms retained; FlowJo application validation pending')
   return {'file':file,'fcs':f,'sources':[s['file'] for s in spec.get('combine_sources',[])],'report':result}
 def edit(self,d,actor):
  from scripts.fcs.fcs_edit import validate_edit
  base=self.run(d.get('base_run'))
  if base['status']!='done':raise Problem('Select a completed analysis.',409)
  reason=required(d.get('reason'),'Reason for gate change',500)
  try:change=validate_edit(d.get('change'),base['result'])
  except ValueError as e:raise Problem(str(e))
  prior=json.loads(base['edit_spec'])['changes'] if base.get('edit_spec') else []
  if len(prior)>=100:raise Problem('This preview supports up to 100 edits per analysis lineage.')
  spec={**(json.loads(base['edit_spec']) if base.get('edit_spec') else {}),'base_run':base['id'],'reason':reason,'changes':prior+[change]}
  return self.queue({'fcs_id':base['fcs_id'],'wsp_id':base['wsp_id'],'mouse_id':base['mouse_id'],'organ':base['organ']},actor,edit_spec=spec)
 def combine(self,d,actor):
  ids=d.get('run_ids');name=required(d.get('name'),'Combined analysis name',100)
  if not isinstance(ids,list) or not 2<=len(ids)<=8 or any(not isinstance(x,str) for x in ids) or len(set(ids))!=len(ids):raise Problem('Select 2–8 distinct completed analyses.')
  runs=[self.run(i) for i in ids]
  if any(r['status']!='done' or r['result'].get('combined') for r in runs):raise Problem('Choose completed single-file analyses.')
  if len({r['result']['source_fcs_sha256'] for r in runs})!=len(runs):raise Problem('Each original FCS may appear only once in a combined analysis.')
  if len({r['organ'] for r in runs})!=1:raise Problem('Select analyses of the same organ.')
  if sum(r['result']['events'] for r in runs)>2000000:raise Problem('Combined preview supports up to 2 million events.')
  first=runs[0]
  total=sum(r['result']['events'] for r in runs);values=total*len(first['result']['channels']);memberships=total*len(first['result']['gates'])
  if values>60000000 or memberships>100000000:raise Problem('Combined coordinate or gate membership limit exceeded.')
  if shutil.disk_usage(self.root).free < values*8+memberships+1024**3:raise Problem('Not enough disk space for the combined analysis cache.',507)
  return self.queue({'fcs_id':first['fcs_id'],'wsp_id':first['wsp_id'],'organ':first['organ']},actor,edit_spec={'combine_runs':ids,'combine_name':name,'changes':[]})
 def queue(self,d,actor,edit_spec=None):
  f=self.file(d.get('fcs_id'));w=self.file(d['wsp_id']) if d.get('wsp_id') else None
  if f['kind']!='fcs' or (w and w['kind']!='wsp'):raise Problem('Select an FCS file and optionally a WSP file.')
  mid=d.get('mouse_id') or None;organ=required(d.get('organ','Liver'),'Organ',100)
  with self.store.db() as c:
   c.execute('BEGIN IMMEDIATE')
   if mid and not c.execute('SELECT 1 FROM mice WHERE mouse_id=?',(mid,)).fetchone():raise Problem('Mouse ID is not in the roster. Leave blank to analyze without linking.')
   if c.execute("SELECT count(*) FROM fcs_runs WHERE status IN ('queued','running')").fetchone()[0]>=20:raise Problem('The analysis queue is full. Try again later.',429)
   rid=secrets.token_hex(16)
   c.execute('INSERT INTO fcs_runs(id,owner,fcs_id,wsp_id,mouse_id,organ,status,created_at,edit_spec) VALUES(?,?,?,?,?,?,?,?,?)',(rid,actor,f['id'],w['id'] if w else None,mid,organ,'queued',stamp(),dump(edit_spec) if edit_spec else None))
   self.store.event(c,actor,'analyze','fcs_run',rid,None,{'fcs_id':f['id'],'wsp_id':w['id'] if w else None,'mouse_id':mid,'organ':organ,'gate_edit':edit_spec},'New immutable analysis version')
  self.wake.set();return {'id':rid,'status':'queued'}
 def run(self,rid):
  with self.store.db() as c:r=c.execute('SELECT * FROM fcs_runs WHERE id=?',(rid,)).fetchone()
  if not r:raise Problem('Analysis not found.',404)
  d=dict(r);d['result']=json.loads(d['result']) if d['result'] else None;return d
 def loop(self):
  while not self.stop.is_set():
   with self.store.db() as c:r=c.execute("SELECT id FROM fcs_runs WHERE status='queued' ORDER BY created_at LIMIT 1").fetchone()
   if not r:self.wake.wait(2);self.wake.clear();continue
   self.process(r[0])
 def process(self,rid):
  try:
   r=self.run(rid)
   with self.store.db() as c:c.execute("UPDATE fcs_runs SET status='running',error=NULL WHERE id=?",(rid,))
   f,fp=self.source(r['fcs_id']);w,wp=self.source(r['wsp_id']) if r['wsp_id'] else (None,None)
   attempt=self.root/'runs'/rid/secrets.token_hex(8);attempt.mkdir(parents=True,mode=0o700)
   spec={'fcs_path':str(fp.resolve()),'filename':f['filename'],'wsp_path':str(wp.resolve()) if wp else None,'out':str(attempt.resolve()),'fcs_sha256':f['sha256'],'wsp_sha256':w['sha256'] if w else None}
   if r.get('edit_spec'):spec['edit_spec']=json.loads(r['edit_spec'])
   if spec.get('edit_spec',{}).get('combine_runs'):
    spec['combine_sources']=[]
    for source_id in spec['edit_spec']['combine_runs']:
     source_run=self.run(source_id);sf,sfp=self.source(source_run['fcs_id']);sw,swp=self.source(source_run['wsp_id']) if source_run['wsp_id'] else (None,None)
     spec['combine_sources'].append({'run_id':source_id,'fcs_id':sf['id'],'filename':sf['filename'],'wsp_path':str(swp.resolve()) if swp else None,'result':source_run['result'],'folder':str((self.root/source_run['result']['artifact_dir']).resolve())})
   specpath=attempt/'request.json';specpath.write_text(dump(spec))
   with (attempt/'worker.log').open('w') as log:
    result=subprocess.run([self.worker_python,'-m','scripts.fcs.fcs_worker',str(specpath)],cwd=PROJECT_ROOT,stdout=log,stderr=log,timeout=900,env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1'})
   resultpath=attempt/'result.json'
   if result.returncode or not resultpath.exists():
    err=(attempt/'error.json');raise Problem(json.loads(err.read_text())['error'] if err.exists() else 'Analysis failed. Original files remain preserved.',422)
   # Revalidate shared original after the worker read, before publishing results.
   if f.get('storage')=='smb':self.source(f['id'])
   for source in spec.get('combine_sources',[]):self.source(source['fcs_id'])
   info=json.loads(resultpath.read_text());info['artifact_dir']=str(attempt.relative_to(self.root))
   with self.store.db() as c:
    c.execute("UPDATE fcs_runs SET status='done',finished_at=?,result=?,error=NULL WHERE id=?",(stamp(),dump(info),rid))
    self.store.event(c,r['owner'],'complete','fcs_run',rid,None,{'gates':len(info['gates']),'events':info['events']},'FCS analysis completed; original data unchanged')
  except Exception as e:
   message=e.message if isinstance(e,Problem) else 'Analysis failed or exceeded 15 minutes. Original files remain preserved.'
   with self.store.db() as c:c.execute("UPDATE fcs_runs SET status='failed',finished_at=?,error=? WHERE id=? AND status IN ('queued','running')",(stamp(),message[:1500],rid))
 def plot(self,rid,d):
  import numpy as np
  r=self.run(rid)
  if r['status']!='done':raise Problem('Analysis is not ready.',409)
  info=r['result'];folder=self.root/info['artifact_dir'];channels=info['channels']
  try:x=int(d.get('x',0));y=int(d.get('y',3));gate=int(d.get('gate',-1))
  except (ValueError,TypeError):raise Problem('Invalid plot selection.')
  if x not in range(len(channels)) or y not in range(len(channels)) or gate not in range(-1,len(info['gates'])):raise Problem('Invalid plot selection.')
  events=np.load(folder/'events.npy',mmap_mode='r',allow_pickle=False)
  masks=np.load(folder/'masks.npy',mmap_mode='r',allow_pickle=False)
  selected=info['gates'][gate] if gate>=0 else None
  parent=gate if d.get('parent_only') is True else selected['parent_index'] if selected else -1
  if d.get('parent_only') is True:selected=None
  population=np.flatnonzero(masks[parent]) if parent>=0 else np.arange(len(events))
  count=len(population);rng=np.random.default_rng(20261103)
  ids=np.sort(rng.choice(population,20000,replace=False)) if count>20000 else population
  a=np.array(events[ids,x]);b=np.array(events[ids,y]);valid=np.isfinite(a)&np.isfinite(b)
  ids=ids[valid];a=a[valid];b=b[valid]
  hit=masks[gate,ids].astype(int).tolist() if selected else [1]*len(ids)
  return {'x':a.tolist(),'y':b.tolist(),'hit':hit,'indices':ids.tolist(),'sources':info.get('sources',[]),'parent_count':count,'displayed':len(ids),'seed':20261103,'gate':selected,'x_label':channels[x]['label'],'y_label':channels[y]['label'],'space':info['space'],'nonfinite_in_preview':int((~valid).sum())}
