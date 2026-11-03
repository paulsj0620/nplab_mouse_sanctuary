"""Consistent SQLite backup. Never copy a live database file by hand."""
import argparse,sqlite3
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('destination');p.add_argument('--db',default=str(Path(__file__).parent/'data/lab.sqlite'));args=p.parse_args()
target=Path(args.destination)
if target.exists():p.error('기존 백업 파일을 덮어쓰지 않습니다.')
target.parent.mkdir(parents=True,exist_ok=True)
src=sqlite3.connect('file:'+str(Path(args.db).resolve())+'?mode=ro',uri=True);dst=sqlite3.connect(target)
try:src.backup(dst)
finally:dst.close();src.close()
target.chmod(0o600)
from fcs_backup import backup_assets
assets=backup_assets(target,args.db,target.parent)
print('Backup complete:',target,'FCS assets:',assets)
