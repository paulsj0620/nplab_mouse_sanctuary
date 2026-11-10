"""Bounded subprocess for reading an approved SMB source; never writes to that share."""
import hashlib,json,os,stat,sys
from pathlib import Path
from scripts.fcs.fcs_references import mapped_path

def copy_source(uri,destination,expected_size):
    path,root=mapped_path(uri)
    if path is None or not root.is_dir():raise ValueError('Approved SMB share is not mounted.')
    target=Path(destination)
    if target.resolve().is_relative_to(root):raise ValueError('The copy destination cannot be on the source share.')
    with path.open('rb') as source:
        before=os.fstat(source.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size!=expected_size:raise ValueError('Source size changed; refresh the workspace file list.')
        if source.read(6) not in (b'FCS2.0',b'FCS3.0',b'FCS3.1'):raise ValueError('Not an FCS acquisition.')
        source.seek(0);sha=hashlib.sha256();copied=0
        with target.open('wb') as out:
            while copied<expected_size:
                block=source.read(min(2*1024**2,expected_size-copied))
                if not block:raise ValueError('The SMB source changed while copying.')
                out.write(block);sha.update(block);copied+=len(block)
            out.flush();os.fsync(out.fileno())
        after=os.fstat(source.fileno())
        if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise ValueError('The SMB source changed while copying; retry after acquisition finishes.')
    return {'size':copied,'sha256':sha.hexdigest()}

if __name__=='__main__':
    try:
        result=copy_source(sys.argv[1],sys.argv[2],int(sys.argv[3]))
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({'error':str(e)[:500]}));sys.exit(1)
