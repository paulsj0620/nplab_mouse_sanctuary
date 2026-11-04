#!/usr/bin/env python3
import argparse, ipaddress, json, os, mimetypes, secrets, sqlite3, time, threading, traceback
from pathlib import Path
from scripts.paths import ROOT as PROJECT_ROOT
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import SimpleCookie
from urllib.parse import urlparse, unquote, parse_qs, quote
from scripts.app.service import Store, Problem, dump

ROOT=PROJECT_ROOT

def fcs_allowed(user):
    # Explicit stable IDs; renaming an account never grants preview access.
    try: ids=json.loads((ROOT/'config/fcs_access.json').read_text()).get('user_ids',[])
    except (OSError,ValueError):return False
    return bool(user) and user['id'] in ids

def public_user(user):
    return {**user,'fcs_access':fcs_allowed(user)} if user else None

def visible_audit(rows,user):
    return rows if fcs_allowed(user) else [r for r in rows if not str(r.get('entity','')).startswith('fcs_')]

class Handler(BaseHTTPRequestHandler):
    def log_message(self,fmt,*args): pass
    def respond(self,status,data,ctype='application/json; charset=utf-8',cookie=None,download=None):
        body=dump(data).encode() if ctype.startswith('application/json') else data
        self.send_response(status);self.send_header('Content-Type',ctype);self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','same-origin')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
        if cookie:self.send_header('Set-Cookie',cookie)
        if download:self.send_header('Content-Disposition',f'attachment; filename="{download}"')
        self.end_headers();self.wfile.write(body)
    def token(self):
        cookie=SimpleCookie()
        try:cookie.load(self.headers.get('Cookie',''));return cookie['lab_session'].value if 'lab_session' in cookie else ''
        except Exception:return ''
    def body(self):
        if not self.headers.get('Content-Type','').startswith('application/json'):raise Problem('A JSON request is required.',415)
        try:n=int(self.headers.get('Content-Length','0'))
        except ValueError:raise Problem('Invalid request length')
        if n<=0 or n>15*1024*1024:raise Problem('Check the request size.',413)
        try:d=json.loads(self.rfile.read(n))
        except Exception:raise Problem('Invalid JSON')
        if not isinstance(d,dict):raise Problem('A JSON object is required.')
        return d
    def dispatch(self):
        if self.server.allowed_networks and not any(ipaddress.ip_address(self.client_address[0]) in network for network in self.server.allowed_networks):raise Problem('Access is restricted to the permitted laboratory network.',403)
        store=self.server.store;path=unquote(urlparse(self.path).path)
        if self.command=='GET' and not path.startswith('/api/'):
            files={'/':'index.html','/app.js':'app.js','/chart.js':'chart.js','/style.css':'style.css','/fcs.js':'fcs.js','/mouse-cemetery.png':'mouse-cemetery.png'}
            if path not in files:raise Problem('Not found.',404)
            p=ROOT/'static'/files[path];return self.respond(200,p.read_bytes(),mimetypes.guess_type(p.name)[0]+('' if p.suffix=='.png' else '; charset=utf-8'))
        if self.command=='GET' and path=='/api/me':
            with store.db() as c:setup=c.execute('SELECT count(*) FROM users').fetchone()[0]==0
            try:u=store.session(self.token())
            except Problem:u=None
            return self.respond(200,{'user':public_user(u),'setup_required':setup,'local_setup_allowed':self.client_address[0] in ('127.0.0.1','::1')})
        if self.command=='POST' and path in ('/api/login','/api/setup'):
            d=self.body()
            with self.server.rate_lock:
                now=time.time();attempts=[t for t in self.server.attempts.get(self.client_address[0],[]) if now-t<300]
                if len(attempts)>=15:raise Problem('Please wait before trying to log in again.',429)
                self.server.attempts[self.client_address[0]]=attempts+[now]
            if path=='/api/setup':
                if self.client_address[0] not in ('127.0.0.1','::1'):raise Problem('Set up the first administrator on the server computer.',403)
                store.create_user(d.get('username'),d.get('password'),'admin',setup=True)
            token,user=store.login(d.get('username'),d.get('password'))
            secure='; Secure' if self.server.secure else ''
            return self.respond(200,public_user(user),cookie=f'lab_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=43200{secure}')
        user=store.session(self.token())
        if path.startswith('/api/fcs/') and not fcs_allowed(user):raise Problem('FCS Explorer is currently available to QA accounts only.',403)
        if self.command!='GET':
            if not secrets.compare_digest(self.headers.get('X-CSRF-Token',''),user['csrf']):raise Problem('Refresh the page to renew request authentication.',403)
            if self.command=='POST' and path.startswith('/api/fcs/chunks/'):
                if self.headers.get('Content-Type')!='application/octet-stream':raise Problem('Binary upload required.',415)
                length=int(self.headers.get('Content-Length','0'))
                from scripts.fcs.fcs_storage import CHUNK
                if not 0<length<=CHUNK:raise Problem('Invalid upload chunk size.',413)
                body=self.rfile.read(length)
                if len(body)!=length:raise Problem('Incomplete upload chunk.',400)
                offset=int(parse_qs(urlparse(self.path).query).get('offset',['-1'])[0])
                return self.respond(200,self.server.fcs.append(path.rsplit('/',1)[1],user['id'],offset,body))
            d=self.body()
        if self.command=='GET':
            if path=='/api/experiments':
                from scripts.app.experiments import workspace
                return self.respond(200,workspace(store,parse_qs(urlparse(self.path).query).get('experiment',[''])[0],fcs_allowed(user)))
            if path.startswith('/api/fcs/workspace-files/'):return self.respond(200,self.server.fcs.workspace_files(path.rsplit('/',1)[1]))
            if path=='/api/fcs/library':return self.respond(200,self.server.fcs.catalog())
            if path.startswith('/api/fcs/transfers/'):return self.respond(200,self.server.fcs.transfer(path.rsplit('/',1)[1],user['id']))
            if path.startswith('/api/fcs/runs/'):return self.respond(200,self.server.fcs.run(path.rsplit('/',1)[1]))
            if path.startswith('/api/fcs/source/'):
                info,source=self.server.fcs.source(path.rsplit('/',1)[1])
                self.send_response(200);self.send_header('Content-Type','application/octet-stream');self.send_header('Content-Length',str(info['size']))
                self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
                self.send_header('Content-Disposition',"attachment; filename*=UTF-8''"+quote(info['filename'],safe=''));self.end_headers()
                with source.open('rb') as f:
                    import shutil
                    shutil.copyfileobj(f,self.wfile,1024*1024)
                return
            if path=='/api/state':return self.respond(200,store.snapshot())
            if path=='/api/audit':return self.respond(200,visible_audit(store.audit(),user))
            if path=='/api/export':
                bundle=store.snapshot(include_audit=True);bundle['schema_version']=3
                with store.db() as c:
                    bundle['fcs_files']=[dict(r) for r in c.execute('SELECT * FROM fcs_files')]
                    bundle['fcs_runs']=[dict(r) for r in c.execute('SELECT * FROM fcs_runs')]
                if not fcs_allowed(user):
                    bundle.pop('fcs_files',None);bundle.pop('fcs_runs',None);bundle['audit']=visible_audit(bundle['audit'],user)
                bundle['fcs_note']='Manifest only: original FCS/WSP bytes are available through authenticated original-file downloads and full backup bundles.'
                return self.respond(200,bundle,download='mouse-lab-data.json')
            if path=='/api/users':
                if user['role']!='admin':raise Problem('Only administrators can view this.',403)
                with store.db() as c:users=[dict(r) for r in c.execute('SELECT id,username,role,created_at FROM users')]
                return self.respond(200,users)
            if path=='/api/source/seed':return self.respond(200,(ROOT/'archives/seed/Mouse-info.xlsx').read_bytes(),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',download='Mouse-info.xlsx')
            if path.startswith('/api/source/'):
                uid=path.rsplit('/',1)[1]
                with store.db() as c:u=c.execute("SELECT original,filename FROM uploads WHERE id=? AND (status='committed' OR owner=?)",(uid,user['id'])).fetchone()
                if not u:raise Problem('File not found.',404)
                ext=Path(u['filename']).suffix.lower()
                if ext not in ('.xlsx','.xls','.csv'):ext='.bin'
                return self.respond(200,u['original'],'application/octet-stream',download='source-'+uid+ext)
        if self.command=='POST':
            if path=='/api/fcs/experiment-link':
                from scripts.app.experiments import link_file
                return self.respond(200,link_file(store,d,user['id']))
            if path=='/api/fcs/transfers':return self.respond(201,self.server.fcs.begin(d,user['id']))
            if path=='/api/fcs/finish':return self.respond(200,self.server.fcs.finish(d.get('id'),user['id']))
            if path=='/api/fcs/export':return self.respond(201,self.server.fcs.export_workspace(d.get('id'),user['id']))
            if path=='/api/fcs/link-reference':return self.respond(201,self.server.fcs.link_reference(d,user['id']))
            if path=='/api/fcs/import-reference':return self.respond(201,self.server.fcs.import_reference(d,user['id']))
            if path=='/api/fcs/edit':return self.respond(202,self.server.fcs.edit(d,user['id']))
            if path=='/api/fcs/combine':return self.respond(202,self.server.fcs.combine(d,user['id']))
            if path=='/api/fcs/analyze':return self.respond(202,self.server.fcs.queue(d,user['id']))
            if path=='/api/fcs/plot':return self.respond(200,self.server.fcs.plot(d.get('id'),d))
            if path=='/api/account/password':
                with self.server.rate_lock:
                    now=time.time();key=('password',user['id'])
                    attempts=[t for t in self.server.attempts.get(key,[]) if now-t<300]
                    if len(attempts)>=5:raise Problem('Too many password change attempts. Try again in five minutes.',429)
                    self.server.attempts[key]=attempts+[now]
                result=store.change_password(user['id'],d.get('current_password'),d.get('new_password'))
                return self.respond(200,result,cookie='lab_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')
            if path=='/api/analyze':
                from scripts.statistics.statistical import analyze_board
                return self.respond(200,analyze_board(store.snapshot(),d,Problem))
            if path=='/api/mice/inclusion':return self.respond(200,store.set_sample_inclusion(d,user['id']))
            if path=='/api/logout':
                import hashlib
                with store.db() as c:c.execute('DELETE FROM sessions WHERE token=?',(hashlib.sha256(self.token().encode()).hexdigest(),))
                return self.respond(200,{'ok':True},cookie='lab_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')
            if path=='/api/users':return self.respond(201,store.create_user(d.get('username'),d.get('password'),d.get('role','editor'),user['id']))
            if path=='/api/upload':return self.respond(201,store.stage(d.get('filename'),d.get('content'),user['id']))
            if path=='/api/preview':return self.respond(200,store.preview(d.get('upload_id'),user['id'],d.get('sheet')))
            if path=='/api/import/review':return self.respond(200,store.review_import(d.get('upload_id'),d.get('mapping',{}),user['id']))
            if path=='/api/import':return self.respond(201,store.commit_import(d.get('upload_id'),d.get('mapping',{}),user['id'],d.get('reason'),review_token=d.get('review_token'),require_review=True))
            if path=='/api/presets':return self.respond(200,store.preset(d,user['id']))
        if self.command=='PATCH':
            if path=='/api/account':return self.respond(200,store.rename_user(user['id'],d.get('username'),d.get('expected_username'),user['id']))
            if path.startswith('/api/users/'):return self.respond(200,store.rename_user(int(path.rsplit('/',1)[1]),d.get('username'),d.get('expected_username'),user['id']))
            if path.startswith('/api/measurements/'):return self.respond(200,store.edit_measurement(int(path.rsplit('/',1)[1]),d,user['id']))
            if path.startswith('/api/mice/'):return self.respond(200,store.edit_mouse(path.rsplit('/',1)[1],d,user['id']))
        raise Problem('Not found.',404)
    def handle_request(self):
        self.connection.settimeout(30)
        try:self.dispatch()
        except Problem as e:self.respond(e.status,{'error':e.message})
        except sqlite3.OperationalError as e:self.respond(503,{'error':'The database is busy. Please retry your changes.'})
        except (ValueError,TypeError,KeyError) as e:self.respond(400,{'error':'Check the request format.'})
        except (BrokenPipeError,ConnectionResetError):pass
        except Exception:traceback.print_exc();self.respond(500,{'error':'An error occurred while processing the request.'})
    do_GET=handle_request;do_POST=handle_request;do_PATCH=handle_request

def make_server(host,port,db,secure=False,allowed_networks=()):
    server=ThreadingHTTPServer((host,port),Handler);server.daemon_threads=True
    server.allowed_networks=tuple(ipaddress.ip_network(n,strict=True) for n in allowed_networks)
    server.store=Store(db,ROOT/'archives/seed/roster.json')
    from scripts.fcs.fcs_storage import FCSLibrary
    server.fcs=FCSLibrary(server.store)
    server.secure=secure;server.attempts={};server.rate_lock=threading.Lock()
    original_close=server.server_close
    def close():
        server.fcs.stop.set();server.fcs.wake.set();server.fcs.thread.join(timeout=2);original_close()
    server.server_close=close
    return server
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,default=8000);p.add_argument('--db',default=str(ROOT/'data/lab.sqlite'));p.add_argument('--secure-cookie',action='store_true');p.add_argument('--allow-network',action='append',default=[],type=lambda n:str(ipaddress.ip_network(n,strict=True)));args=p.parse_args()
    server=make_server(args.host,args.port,args.db,args.secure_cookie,args.allow_network)
    print(f'Mouse Sanctuary: http://{args.host}:{args.port}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:server.server_close()
