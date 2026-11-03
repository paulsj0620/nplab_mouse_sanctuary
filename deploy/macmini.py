"""Prepare reviewable macOS user services. Does not install or enable remote access."""
import argparse,datetime,json,os,plistlib,sqlite3,urllib.parse,urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent

def prepare(root,output,db,port,require_setup=False):
    root=Path(root).resolve();output=Path(output).resolve();db=Path(db).resolve()
    if not (root/'server.py').is_file():raise ValueError('앱 폴더의 server.py를 찾을 수 없습니다.')
    if not 1024<=port<=65535:raise ValueError('포트는 1024–65535로 지정하세요.')
    if require_setup:
        if not (root/'.venv/bin/python3').exists():raise ValueError('먼저 start.command로 설치·초기 계정 설정을 완료하세요.')
        with sqlite3.connect('file:'+urllib.parse.quote(str(db))+'?mode=ro',uri=True) as c:
            if not c.execute('SELECT count(*) FROM users').fetchone()[0]:raise ValueError('먼저 localhost에서 관리자 계정을 생성하세요.')
    output.mkdir(parents=True,exist_ok=True)
    logs=root/'logs';logs.mkdir(mode=0o700,exist_ok=True)
    base={'WorkingDirectory':str(root),'EnvironmentVariables':{'PYTHONUNBUFFERED':'1'},'Umask':0o077}
    server={**base,'Label':'com.mouselab.server','ProgramArguments':['/usr/bin/caffeinate','-is',str(root/'.venv/bin/python3'),str(root/'server.py'),'--host','127.0.0.1','--port',str(port),'--db',str(db),'--secure-cookie'],'RunAtLoad':True,'KeepAlive':True,'ThrottleInterval':10,'StandardOutPath':str(logs/'server.log'),'StandardErrorPath':str(logs/'server-error.log')}
    backup={**base,'Label':'com.mouselab.backup','ProgramArguments':[str(root/'.venv/bin/python3'),str(root/'deploy/macmini.py'),'backup','--db',str(db),'--destination',str(root/'backups')],'StartCalendarInterval':{'Hour':3,'Minute':0},'StandardOutPath':str(logs/'backup.log'),'StandardErrorPath':str(logs/'backup-error.log')}
    for label,config in [('com.mouselab.server',server),('com.mouselab.backup',backup)]:
        path=output/(label+'.plist')
        with path.open('wb') as f:plistlib.dump(config,f)
        path.chmod(0o600)
    return {'server':str(output/'com.mouselab.server.plist'),'backup':str(output/'com.mouselab.backup.plist'),'backend':f'http://127.0.0.1:{port}','db':str(db),'installed':False,'remote_enabled':False}

def backup(db,destination):
    db=Path(db).resolve();destination=Path(destination).resolve();destination.mkdir(mode=0o700,parents=True,exist_ok=True)
    name='lab-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.sqlite';target=destination/name
    # No original or existing backup is overwritten. No retention deletion is performed.
    with sqlite3.connect('file:'+urllib.parse.quote(str(db))+'?mode=ro',uri=True) as src:
        target.touch(mode=0o600,exist_ok=False)
        with sqlite3.connect(target) as dst:
            src.backup(dst)
            if dst.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('백업 무결성 검증에 실패했습니다.')
    import sys
    sys.path.insert(0,str(ROOT))
    from fcs_backup import backup_assets
    assets=backup_assets(target,db,destination)
    return {'backup':str(target),'integrity':'ok','fcs_assets':assets}

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('prepare');a.add_argument('--app-root',type=Path,default=ROOT);a.add_argument('--output',type=Path,default=ROOT/'deploy/generated');a.add_argument('--db',type=Path,default=ROOT/'data/lab.sqlite');a.add_argument('--port',type=int,default=8767);a.add_argument('--require-setup',action='store_true')
    b=sub.add_parser('backup');b.add_argument('--db',type=Path,default=ROOT/'data/lab.sqlite');b.add_argument('--destination',type=Path,default=ROOT/'backups')
    c=sub.add_parser('check-initialized');c.add_argument('--port',type=int,default=8767)
    args=p.parse_args()
    if args.command=='prepare':result=prepare(args.app_root,args.output,args.db,args.port,args.require_setup)
    elif args.command=='backup':result=backup(args.db,args.destination)
    else:
        with urllib.request.urlopen(f'http://127.0.0.1:{args.port}/api/me',timeout=5) as r:state=json.load(r)
        if state.get('setup_required'):raise ValueError('먼저 관리자 계정 설정을 완료하세요.')
        result={'initialized':True}
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
