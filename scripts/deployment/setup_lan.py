"""Install private-subnet-only user services; never opens router/firewall rules."""
import argparse,ipaddress,os,plistlib,shutil,subprocess
from pathlib import Path
from scripts.deployment.macmini import prepare,ROOT
p=argparse.ArgumentParser();p.add_argument('--host',required=True);p.add_argument('--network',required=True);p.add_argument('--install',action='store_true');a=p.parse_args()
host=ipaddress.ip_address(a.host);network=ipaddress.ip_network(a.network,strict=True)
if host not in network or host.is_loopback or not host.is_private:raise ValueError('로컬 내부망 IP와 범위를 지정하세요.')
output=ROOT/'deploy/generated-lan';prepare(ROOT,output,ROOT/'data/lab.sqlite',8000,True)
path=output/'com.mouselab.server.plist'
with path.open('rb') as f:config=plistlib.load(f)
args=config['ProgramArguments'];args[args.index('--host')+1]=str(host);args.remove('--secure-cookie');args+=['--allow-network',str(network)]
with path.open('wb') as f:plistlib.dump(config,f)
if a.install:
 target=Path.home()/'Library/LaunchAgents';target.mkdir(exist_ok=True)
 for label in ['com.mouselab.server','com.mouselab.backup','com.mouselab.workday-awake']:
  existing=subprocess.run(['launchctl','print',f'gui/{os.getuid()}/{label}'],capture_output=True)
  if existing.returncode==0:raise RuntimeError('이미 실행 중인 서비스가 있습니다: '+label)
 for label in ['com.mouselab.server','com.mouselab.backup','com.mouselab.workday-awake']:
  dest=target/(label+'.plist');shutil.copy2(output/(label+'.plist'),dest);dest.chmod(0o600)
  subprocess.run(['launchctl','bootstrap',f'gui/{os.getuid()}',str(dest)],check=True)
print(f'http://{host}:8000/ · allowed network {network}')
