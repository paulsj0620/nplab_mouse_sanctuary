import base64
import concurrent.futures
import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from scripts.app.security import LoginLimiter, client_ip
from scripts.app.service import Store, Problem
from scripts.app.server import make_server


class LimiterTests(unittest.TestCase):
    def test_success_does_not_exhaust_limit_and_failures_expire(self):
        limiter=LoginLimiter(account_limit=2)
        with patch('scripts.app.security.time.monotonic',return_value=1):
            for _ in range(40):
                ticket,_=limiter.begin('one','alice');self.assertIsNotNone(ticket)
                limiter.finish(ticket,True)
            self.assertIsNotNone(limiter.begin('one','alice')[0])
            self.assertIsNotNone(limiter.begin('two','alice')[0])
            self.assertEqual(limiter.begin('three','alice'),(None,True))
            self.assertEqual(limiter.begin('three','alice'),(None,False))
            self.assertIsNotNone(limiter.begin('two','bob')[0])
        with patch('scripts.app.security.time.monotonic',return_value=302):
            self.assertIsNotNone(limiter.begin('three','alice')[0])

    def test_ip_inflight_and_memory_bounds(self):
        limiter=LoginLimiter(ip_limit=2,capacity=5)
        self.assertIsNotNone(limiter.begin('one','a')[0])
        self.assertIsNotNone(limiter.begin('one','b')[0])
        self.assertIsNone(limiter.begin('one','c')[0])
        self.assertIsNotNone(limiter.begin('two','c')[0])
        for i in range(50):limiter.begin(str(i),str(i))
        self.assertLessEqual(len(limiter.entries),5)
        self.assertLessEqual(len(limiter.blocked),5)

    def test_only_hosted_trusts_replaced_proxy_header(self):
        headers={'X-Real-IP':'192.0.2.1','X-Forwarded-For':'198.51.100.2'}
        self.assertEqual(client_ip('127.0.0.1',headers,True),'192.0.2.1')
        self.assertEqual(client_ip('127.0.0.1',headers,False),'127.0.0.1')
        self.assertEqual(client_ip('127.0.0.1',{'X-Real-IP':'spoof,more'},True),'127.0.0.1')


class StoreSecurityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/'test.sqlite'
        self.store=Store(self.path)
        self.admin=self.store.create_user('admin','long-test-password',role='admin',setup=True)['id']
        self.editor=self.store.create_user('editor','long-test-password',actor=self.admin)['id']
    def tearDown(self):self.tmp.cleanup()
    def upload(self,name='test.csv',raw=b'id,value\n1,2\n',actor=None):
        return self.store.stage(name,base64.b64encode(raw).decode(),actor or self.editor)
    def preserved(self):
        with self.store.db() as c:
            return {t:[tuple(r) for r in c.execute('SELECT * FROM '+t)] for t in ('users','uploads','mice','metrics','measurements')}

    def test_access_revocation_authorization_and_preservation(self):
        self.upload();before=self.preserved()
        token,_=self.store.login('editor','long-test-password')
        for actor,target in ((self.editor,self.admin),(self.admin,self.admin)):
            with self.assertRaises(Problem):self.store.set_user_access(target,True,False,actor,'test')
        with self.assertRaises(Problem):self.store.set_user_access(self.editor,True,False,self.admin,'')
        self.store.set_user_access(self.editor,True,False,self.admin,'temporarily suspend')
        with self.assertRaises(Problem):self.store.session(token)
        with self.assertRaises(Problem):self.store.login('editor','long-test-password')
        with self.assertRaises(Problem):self.store.set_user_access(self.editor,False,False,self.admin,'stale')
        self.store.set_user_access(self.editor,False,True,self.admin,'restore')
        self.store.login('editor','long-test-password')
        with self.assertRaises(Problem):self.store.session(token)
        self.assertEqual(before,self.preserved())
        self.assertFalse(any(u['disabled'] for u in self.store.list_users()))

    def test_hosted_start_does_not_migrate_or_change_existing_data(self):
        before=self.path.read_bytes()
        hosted=Store(self.path,existing_only=True)
        self.assertFalse(any(u['disabled'] for u in hosted.list_users()))
        self.assertEqual(before,self.path.read_bytes())

    def test_duplicate_pending_upload_reuses_original_at_limit(self):
        self.store.upload_pending_count=1
        one=self.upload();two=self.upload()
        self.assertEqual(one['upload_id'],two['upload_id'])
        before=self.preserved()
        with self.assertRaises(Problem):self.upload('other.csv')
        self.assertEqual(before,self.preserved())
        # Another owner must not reuse this owner's private upload.
        other=self.upload(actor=self.admin)
        self.assertNotEqual(other['upload_id'],one['upload_id'])

    def test_total_user_pending_and_disk_limits_preserve_files(self):
        raw=b'id,value\n1,2\n'
        self.upload();before=self.preserved()
        for attr in ('upload_total_limit','upload_user_limit','upload_pending_limit'):
            old=getattr(self.store,attr);setattr(self.store,attr,len(raw))
            with self.assertRaises(Problem):self.upload('second.csv')
            setattr(self.store,attr,old)
        with patch('scripts.app.service.shutil.disk_usage') as disk:
            disk.return_value.free=1
            with self.assertRaises(Problem):self.upload('second.csv')
        self.assertEqual(before,self.preserved())

    def test_concurrent_quota_enforcement(self):
        self.store.upload_pending_count=1
        def attempt(i):
            try:self.upload(str(i)+'.csv');return True
            except Problem:return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sum(pool.map(attempt,range(2))),1)

    def test_csv_limits_and_oversized_encoded_input(self):
        for raw in (b'id,value\n'+b'1,2\n'*10001,(','.join(['a']*201)+'\n1\n').encode()):
            with self.assertRaises(Problem):self.upload(raw=raw)
        with self.assertRaises(Problem):self.store.stage('a.csv','a'*(14*1024*1024),self.editor)
        with self.store.db() as c:self.assertEqual(c.execute('SELECT count(*) FROM uploads').fetchone()[0],0)

    def test_http_access_csrf_and_hsts(self):
        server=make_server('127.0.0.1',0,self.path,secure=True,hosted=True)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        admin_token,admin=self.store.login('admin','long-test-password')
        editor_token,editor=self.store.login('editor','long-test-password')
        def request(path,token='',csrf='',body=None):
            conn=http.client.HTTPConnection('127.0.0.1',server.server_port)
            conn.request(('PATCH' if path.endswith('/access') else 'POST') if body is not None else 'GET',path,json.dumps(body) if body is not None else None,{'Content-Type':'application/json','Cookie':'lab_session='+token,'X-CSRF-Token':csrf})
            res=conn.getresponse();status=res.status;headers=dict(res.getheaders());data=json.loads(res.read());conn.close();return status,headers,data
        try:
            self.assertEqual(request('/api/login',body={'username':'admin','password':'x'*17000})[0],413)
            for _ in range(8):server.request_slots.acquire()
            try:self.assertEqual(request('/api/me')[0],503)
            finally:
                for _ in range(8):server.request_slots.release()
            endpoint=f'/api/users/{self.editor}/access';body={'disabled':True,'expected_disabled':False,'reason':'test'}
            self.assertEqual(request(endpoint,body=body)[0],401)
            self.assertEqual(request(endpoint,admin_token,'bad',body)[0],403)
            self.assertEqual(request(endpoint,editor_token,editor['csrf'],body)[0],403)
            self.assertEqual(request(endpoint,admin_token,admin['csrf'],body)[0],200)
            self.assertEqual(request('/api/state',editor_token)[0],401)
            status,headers,users=request('/api/users',admin_token)
            self.assertEqual(status,200);self.assertEqual(headers['Strict-Transport-Security'],'max-age=31536000')
            self.assertTrue(next(u for u in users if u['id']==self.editor)['disabled'])
            server.import_slot.acquire()
            try:self.assertEqual(request('/api/upload',admin_token,admin['csrf'],{'filename':'x.csv','content':'a'})[0],503)
            finally:server.import_slot.release()
        finally:server.shutdown();server.server_close();thread.join()
