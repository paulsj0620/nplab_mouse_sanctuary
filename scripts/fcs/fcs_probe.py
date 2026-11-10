"""Read-only, bounded by caller: validate and hash an approved shared FCS."""
import hashlib,json,os,stat,sys
from scripts.fcs.fcs_references import mapped_path

def probe(uri):
 path,root=mapped_path(uri)
 if path is None or not root.is_dir():raise ValueError('Approved SMB share is not mounted.')
 with path.open('rb') as f:
  before=os.fstat(f.fileno())
  if not stat.S_ISREG(before.st_mode):raise ValueError('Not a regular FCS file.')
  if f.read(6) not in (b'FCS2.0',b'FCS3.0',b'FCS3.1'):raise ValueError('Not an FCS acquisition.')
  f.seek(0);h=hashlib.sha256()
  for block in iter(lambda:f.read(2*1024**2),b''):h.update(block)
  after=os.fstat(f.fileno())
  if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise ValueError('SMB source changed while reading.')
 return {'path':str(path),'sha256':h.hexdigest(),'size':after.st_size}
if __name__=='__main__':
 try:print(json.dumps(probe(sys.argv[1])))
 except Exception as e:print(json.dumps({'error':str(e)[:500]}));sys.exit(1)
