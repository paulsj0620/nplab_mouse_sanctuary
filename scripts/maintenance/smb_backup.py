"""Verified snapshot backup, resumable SMB publication, and non-overwriting restore."""
import argparse,datetime,fcntl,json,os,shutil,sqlite3,subprocess,sys,uuid
from pathlib import Path
from scripts.paths import ROOT
from scripts.fcs.fcs_storage import digest,immutable_copy
from scripts.deployment.macmini import backup

def write_json(path,value):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
 with open(tmp,'x') as f:json.dump(value,f,indent=2);f.flush();os.fsync(f.fileno())
 os.replace(tmp,path)

def safe_path(root,relative):
 root=Path(root).resolve();p=(root/relative).resolve()
 if not p.is_relative_to(root):raise ValueError('Path outside backup root')
 return p

def snapshot(root=ROOT):
 root=Path(root).resolve();dest=root/'backups';result=backup(root/'data/lab.sqlite',dest);db=Path(result['backup']);entries=[]
 def record(source,restore):
  source=Path(source);entries.append({'backup':str(source.relative_to(dest)),'restore':restore,'sha256':digest(source)})
 record(db,'data/lab.sqlite')
 assets=json.loads(Path(result['fcs_assets']).read_text()) if result['fcs_assets'] else {'files':[],'external_sources':[]}
 if result['fcs_assets']:record(result['fcs_assets'],'backup-metadata/fcs-assets.json')
 for item in assets['files']:
  record(dest/item['backup'],'data/fcs/'+item['path'])
  if item['path'].startswith('objects/'):record(dest/item['backup'],'data/fcs/mirror/'+Path(item['path']).name)
 for directory in ['archives','config']:
  for source in sorted((root/directory).rglob('*')):
   if source.is_symlink():raise ValueError('Backup refuses symlink: '+str(source))
   if not source.is_file():continue
   sha=digest(source);target=dest/'extra-assets'/sha;immutable_copy(source,target,sha);record(target,str(source.relative_to(root)))
 manifest={'version':1,'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':entries,'external_sources':assets.get('external_sources',[]),'note':'External SMB originals are referenced, not copied. Restore code/environment separately from GitHub.'}
 path=dest/(db.name+'.complete.json');write_json(path,manifest);return path

def copy_verified(source,target,sha):
 source=Path(source);target=Path(target)
 if target.exists():
  if digest(target)!=sha:raise ValueError('Existing backup differs: '+str(target))
  return
 target.parent.mkdir(parents=True,exist_ok=True);tmp=target.with_name('.'+target.name+'.'+uuid.uuid4().hex+'.partial')
 try:
  with open(source,'rb') as src,open(tmp,'xb') as dst:shutil.copyfileobj(src,dst,2*1024**2);dst.flush();os.fsync(dst.fileno())
  if digest(tmp)!=sha:raise ValueError('Backup copy hash mismatch')
  os.rename(tmp,target)
 finally:
  if tmp.exists():tmp.unlink()

def transfer(manifest,destination):
 manifest=Path(manifest);destination=Path(destination);data=json.loads(manifest.read_text())
 for item in data['files']:copy_verified(safe_path(manifest.parent,item['backup']),safe_path(destination,item['backup']),item['sha256'])
 # Completion marker is published only after every referenced file verifies.
 copy_verified(manifest,destination/manifest.name,digest(manifest))
 return destination/manifest.name

def restore(manifest,destination):
 manifest=Path(manifest).resolve();dest=Path(destination).resolve();data=json.loads(manifest.read_text())
 if dest.exists():raise ValueError('Restore destination must not exist; live data are never overwritten.')
 for item in data['files']:
  safe_path(dest,item['restore'])
  if digest(safe_path(manifest.parent,item['backup']))!=item['sha256']:raise ValueError('Backup verification failed')
 dest.mkdir(parents=True,mode=0o700)
 for item in data['files']:copy_verified(safe_path(manifest.parent,item['backup']),safe_path(dest,item['restore']),item['sha256'])
 with sqlite3.connect('file:'+str(dest/'data/lab.sqlite')+'?mode=ro',uri=True) as c:
  if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Restored DB integrity check failed')
 return {'restored':str(dest),'files_verified':len(data['files']),'external_sources':len(data['external_sources'])}

def network_worker(manifest,config):
 if not config.get('enabled',False):raise ValueError('Backup is disabled by user request.')
 mount=Path(config['mount']);dest=Path(config['destination'])
 if not os.path.ismount(mount):raise ValueError('SMB share is not mounted; local backup retained.')
 mounts=subprocess.check_output(['/sbin/mount'],text=True,timeout=10)
 if not any(' on '+str(mount)+' ' in line and '(smbfs,' in line for line in mounts.splitlines()):raise ValueError('Expected an SMB filesystem at configured mount.')
 if not dest.resolve().is_relative_to(mount.resolve()):raise ValueError('Destination is outside SMB mount')
 dest.mkdir(parents=True,exist_ok=True)
 print(transfer(manifest,dest),flush=True)

def scheduled(force=False):
 config=json.loads((ROOT/'config/backup.json').read_text())
 if not config.get('enabled',False):
  print('Backup disabled; no snapshot or SMB transfer performed.');return
 logs=ROOT/'logs';logs.mkdir(exist_ok=True)
 with open(logs/'smb-backup.lock','w') as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:return
  statepath=logs/'backup-status.json';state=json.loads(statepath.read_text()) if statepath.exists() else {}
  now=datetime.datetime.now().astimezone();today=now.date().isoformat()
  try:
   if force or not state.get('local_manifest') or (now.hour>=3 and state.get('local_date')!=today):
    state['phase']='local';write_json(statepath,state)
    p=snapshot();state.update(local_manifest=str(p),local_date=today,local_success_at=now.isoformat());write_json(statepath,state)
   # Retry every complete snapshot without a receipt, including earlier failed transfers.
   for p in sorted((ROOT/'backups').glob('*.complete.json')):
    receipt=p.with_name(p.name+'.sent')
    if receipt.exists() and json.loads(receipt.read_text()).get('destination')==config['destination']:continue
    state.update(phase='smb',pending_manifest=str(p));write_json(statepath,state)
    done=subprocess.run([sys.executable,'-m','scripts.maintenance.smb_backup','send',str(p)],cwd=ROOT,capture_output=True,text=True,timeout=1800)
    if done.returncode:raise RuntimeError(done.stderr.strip()[-1500:] or 'SMB transfer failed')
    write_json(receipt,{'destination':config['destination'],'sent_at':datetime.datetime.now().astimezone().isoformat()})
    state['remote_manifest']=str(Path(config['destination'])/p.name)
   state.update(phase='complete',last_success_at=datetime.datetime.now().astimezone().isoformat(),error=None)
  except Exception as e:
   state.update(phase='failed',error=str(e),failed_at=datetime.datetime.now().astimezone().isoformat());write_json(statepath,state);raise
  write_json(statepath,state);print(json.dumps(state,indent=2))

def main():
 p=argparse.ArgumentParser();p.add_argument('command',choices=['run','send','restore']);p.add_argument('manifest',nargs='?');p.add_argument('destination',nargs='?');p.add_argument('--force',action='store_true');a=p.parse_args()
 if a.command=='run':scheduled(a.force)
 elif a.command=='send':network_worker(a.manifest,json.loads((ROOT/'config/backup.json').read_text()))
 else:print(json.dumps(restore(a.manifest,a.destination)))
if __name__=='__main__':main()
