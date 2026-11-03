"""Back up and restore the FCS assets referenced by a consistent SQLite snapshot."""
import hashlib,json,os,shutil,sqlite3
from pathlib import Path
from fcs_storage import digest,immutable_copy,CHUNK

def backup_assets(snapshot,live_db,destination):
 snapshot=Path(snapshot);dest=Path(destination);root=Path(live_db).parent/'fcs';manifest={'version':1,'database':snapshot.name,'files':[]}
 with sqlite3.connect(snapshot) as c:
  c.row_factory=sqlite3.Row
  if not c.execute("SELECT 1 FROM sqlite_master WHERE name='fcs_files'").fetchone():return None
  external_exists=c.execute("SELECT 1 FROM sqlite_master WHERE name='fcs_external'").fetchone()
  manifest['external_sources']=[dict(r) for r in c.execute('SELECT e.*,f.sha256,f.filename FROM fcs_external e JOIN fcs_files f ON f.id=e.file_id')] if external_exists else []
  query='SELECT DISTINCT sha256 FROM fcs_files'+(' WHERE id NOT IN (SELECT file_id FROM fcs_external)' if external_exists else '')
  for row in c.execute(query):
   sha=row['sha256'];target=dest/'fcs-assets/objects'/sha;immutable_copy(root/'objects'/sha,target,sha)
   manifest['files'].append({'path':'objects/'+sha,'backup':str(target.relative_to(dest)),'sha256':sha})
  for row in c.execute("SELECT result FROM fcs_runs WHERE status='done'"):
   result=json.loads(row['result']);folder=Path(result['artifact_dir'])
   for name in ['events.npy','masks.npy','result.json','request.json']:
    source=root/folder/name;sha=digest(source);target=dest/'fcs-assets'/folder/name;immutable_copy(source,target,sha)
    manifest['files'].append({'path':str(folder/name),'backup':str(target.relative_to(dest)),'sha256':sha})
  for row in c.execute('SELECT id,received FROM fcs_transfers WHERE file_id IS NULL'):
   source=root/'staging'/row['id'];target=dest/(snapshot.name+'.staging')/row['id'];target.parent.mkdir(exist_ok=True,parents=True)
   with open(source,'rb') as src,open(target,'xb') as dst:
    remaining=row['received']
    while remaining:
     b=src.read(min(CHUNK,remaining))
     if not b:raise ValueError('Incomplete staged upload during backup')
     dst.write(b);remaining-=len(b)
    dst.flush();os.fsync(dst.fileno())
   manifest['files'].append({'path':'staging/'+row['id'],'backup':str(target.relative_to(dest)),'sha256':digest(target)})
 path=dest/(snapshot.name+'.assets.json')
 with open(path,'x') as f:json.dump(manifest,f,indent=2);f.flush();os.fsync(f.fileno())
 return str(path)

def restore_bundle(snapshot,destination):
 snapshot=Path(snapshot).resolve();dest=Path(destination).resolve()
 if dest.exists():raise ValueError('Restore destination must not exist. Live data are never overwritten.')
 manifest=json.loads(Path(str(snapshot)+'.assets.json').read_text())
 # Verify all assets before creating the restored copy.
 for item in manifest['files']:
  source=(snapshot.parent/item['backup']).resolve()
  if not source.is_relative_to(snapshot.parent) or digest(source)!=item['sha256']:raise ValueError('Backup asset verification failed')
 dest.mkdir(mode=0o700,parents=True)
 with sqlite3.connect('file:'+str(snapshot)+'?mode=ro',uri=True) as src,sqlite3.connect(dest/'lab.sqlite') as db:
  src.backup(db)
  if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Restored DB integrity check failed')
 for item in manifest['files']:
  target=(dest/'fcs'/item['path']).resolve()
  if not target.is_relative_to(dest/'fcs'):raise ValueError('Invalid restore path')
  immutable_copy(snapshot.parent/item['backup'],target,item['sha256'])
  if item['path'].startswith('objects/'):
   immutable_copy(target,dest/'fcs/mirror'/target.name,item['sha256'])
  if item['path'].startswith('staging/'):target.chmod(0o600)
 return {'database':str(dest/'lab.sqlite'),'assets_verified':len(manifest['files'])}
