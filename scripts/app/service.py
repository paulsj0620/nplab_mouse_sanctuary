"""Persistent laboratory data service. All writes are transactional and audited."""
import base64, csv, hashlib, io, json, math, os, re, secrets, sqlite3, time, zipfile
from pathlib import Path
from datetime import datetime, timezone

def stamp(): return datetime.now(timezone.utc).isoformat()
def dump(v): return json.dumps(v, ensure_ascii=False, allow_nan=False)
class Problem(Exception):
    def __init__(self, message, status=400): self.message,self.status=message,status
def required(v, name, limit=200):
    if not isinstance(v,str) or not v.strip() or len(v)>limit: raise Problem(f'{name}: Enter a value (maximum {limit} characters).')
    return v.strip()
def clean(v): return '' if v is None else str(v).strip()
def number(v, reason, unit=''):
    if v is None or clean(v)=='':
        if not clean(reason): raise Problem('A missing reason is required for a blank value.')
        return None
    try: n=float(v)
    except (ValueError,TypeError): raise Problem(f'Not a number: {v}')
    if not math.isfinite(n): raise Problem('Enter a finite number.')
    if unit=='%' and not 0<=n<=100: raise Problem('Percentage values must be between 0 and 100.')
    if clean(reason): raise Problem('Clear the missing reason when a measured value is present.')
    return n

class ClosingConnection(sqlite3.Connection):
    def __exit__(self,exc_type,exc_value,traceback):
        try:return super().__exit__(exc_type,exc_value,traceback)
        finally:self.close()

class Store:
    def __init__(self, path, seed=None, *, existing_only=False):
        self.import_review_secret=secrets.token_bytes(32)
        self.existing_only = existing_only
        if existing_only:
            self.path = Path(path).resolve().as_uri() + '?mode=rw'
            with self.db() as c:
                if not c.execute('SELECT 1 FROM users LIMIT 1').fetchone():
                    raise RuntimeError('Expected an initialized site with existing accounts.')
            return
        self.path=str(path);Path(path).parent.mkdir(parents=True,exist_ok=True)
        with self.db() as c:
            c.executescript('''
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT UNIQUE NOT NULL,password TEXT NOT NULL,salt TEXT NOT NULL,role TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS login_history(id INTEGER PRIMARY KEY,user_id INTEGER REFERENCES users(id),username TEXT NOT NULL,outcome TEXT NOT NULL CHECK(outcome IN ('success','failure','blocked')),created_at TEXT NOT NULL);
CREATE TRIGGER IF NOT EXISTS login_history_no_update BEFORE UPDATE ON login_history BEGIN SELECT RAISE(ABORT,'login history is append-only'); END;
CREATE TRIGGER IF NOT EXISTS login_history_no_delete BEFORE DELETE ON login_history BEGIN SELECT RAISE(ABORT,'login history is append-only'); END;
CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id INTEGER REFERENCES users(id),csrf TEXT NOT NULL,expires REAL NOT NULL);
CREATE TABLE IF NOT EXISTS mice(mouse_id TEXT PRIMARY KEY,group_name TEXT NOT NULL,experiment TEXT NOT NULL DEFAULT '',weeks TEXT NOT NULL DEFAULT '',diet TEXT NOT NULL DEFAULT '',note TEXT NOT NULL DEFAULT '',excluded INTEGER NOT NULL DEFAULT 0,version INTEGER NOT NULL DEFAULT 1,source TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS metrics(id INTEGER PRIMARY KEY,identity TEXT UNIQUE NOT NULL,name TEXT NOT NULL,unit TEXT NOT NULL,organ TEXT NOT NULL,gate TEXT NOT NULL,parent_gate TEXT NOT NULL,denominator TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS uploads(id TEXT PRIMARY KEY,filename TEXT NOT NULL,sha256 TEXT NOT NULL,original BLOB NOT NULL,owner INTEGER REFERENCES users(id),created_at TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'pending',mapping TEXT);
CREATE TABLE IF NOT EXISTS experiment_files(id INTEGER PRIMARY KEY,file_id TEXT NOT NULL REFERENCES fcs_files(id),experiment TEXT NOT NULL,mouse_id TEXT NOT NULL DEFAULT '',created_by INTEGER NOT NULL REFERENCES users(id),created_at TEXT NOT NULL,UNIQUE(file_id,experiment,mouse_id));
CREATE TABLE IF NOT EXISTS upload_mice(upload_id TEXT NOT NULL REFERENCES uploads(id),mouse_id TEXT NOT NULL REFERENCES mice(mouse_id),PRIMARY KEY(upload_id,mouse_id));
CREATE TABLE IF NOT EXISTS measurements(id INTEGER PRIMARY KEY,mouse_id TEXT NOT NULL REFERENCES mice(mouse_id),metric_id INTEGER NOT NULL REFERENCES metrics(id),timepoint TEXT NOT NULL,replicate TEXT NOT NULL,value REAL,missing_reason TEXT NOT NULL DEFAULT '',version INTEGER NOT NULL DEFAULT 1,upload_id TEXT REFERENCES uploads(id),source_row INTEGER,UNIQUE(mouse_id,metric_id,timepoint,replicate));
CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,actor INTEGER REFERENCES users(id),action TEXT NOT NULL,entity TEXT NOT NULL,entity_id TEXT NOT NULL,before_json TEXT,after_json TEXT,reason TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS presets(id INTEGER PRIMARY KEY,name TEXT UNIQUE NOT NULL,config TEXT NOT NULL,version INTEGER NOT NULL DEFAULT 1,updated_at TEXT NOT NULL);
CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT,'audit is append-only'); END;
CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT,'audit is append-only'); END;
CREATE TRIGGER IF NOT EXISTS uploads_no_original_update BEFORE UPDATE OF original,sha256 ON uploads BEGIN SELECT RAISE(ABORT,'source is immutable'); END;
CREATE TRIGGER IF NOT EXISTS uploads_no_delete BEFORE DELETE ON uploads BEGIN SELECT RAISE(ABORT,'source is immutable'); END;
''')
            if seed and not c.execute('SELECT 1 FROM mice LIMIT 1').fetchone():
                data=json.loads(Path(seed).read_text())
                for m in data['mice']:
                    c.execute('INSERT INTO mice(mouse_id,group_name,experiment,weeks,diet,note,source) VALUES(?,?,?,?,?,?,?)',(m['mouse_id'],m['group'],m['experiment'],str(m['weeks']) if m['weeks'] is not None else '',m['diet'],m['note'],dump({'sheet':'Sheet1','cell':m['source_cell'],'sha256':data['sha256'],'raw_group':m['raw_group']})))
    def db(self):
        c=sqlite3.connect(self.path,uri=self.existing_only,timeout=15,factory=ClosingConnection);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');return c
    def event(self,c,actor,action,entity,eid,before,after,reason):
        c.execute('INSERT INTO events(actor,action,entity,entity_id,before_json,after_json,reason,created_at) VALUES(?,?,?,?,?,?,?,?)',(actor,action,entity,str(eid),dump(before),dump(after),required(reason,'Reason',2000),stamp()))
    def create_user(self,username,password,role='editor',actor=None,setup=False):
        username=required(username,'Username',80)
        if not isinstance(password,str) or len(password)<12 or len(password)>200: raise Problem('Passwords must contain 12–200 characters.')
        if role not in ('admin','editor'):raise Problem('Invalid role')
        salt=secrets.token_hex(16);hashed=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),600000).hex()
        with self.db() as c:
            c.execute('BEGIN IMMEDIATE')
            if setup and c.execute('SELECT COUNT(*) FROM users').fetchone()[0]:raise Problem('An administrator has already been set up.',409)
            if not setup:
                u=c.execute('SELECT role FROM users WHERE id=?',(actor,)).fetchone()
                if not u or u['role']!='admin':raise Problem('Only administrators can add accounts.',403)
            try: uid=c.execute('INSERT INTO users(username,password,salt,role,created_at) VALUES(?,?,?,?,?)',(username,hashed,salt,role,stamp())).lastrowid
            except sqlite3.IntegrityError:raise Problem('This username already exists.',409)
            self.event(c,actor or uid,'create','user',uid,None,{'username':username,'role':role},'Account created')
        return {'id':uid,'username':username,'role':role}
    def rename_user(self, target_id, username, expected_username, actor):
        username=required(username,'Username',80)
        expected_username=required(expected_username,'Previous username',80)
        with self.db() as c:
            c.execute('BEGIN IMMEDIATE')
            author=c.execute('SELECT role FROM users WHERE id=?',(actor,)).fetchone()
            if not author or (actor!=target_id and author['role']!='admin'):
                raise Problem('You can only rename your own account.',403)
            target=c.execute('SELECT id,username,role,created_at FROM users WHERE id=?',(target_id,)).fetchone()
            if not target:raise Problem('User not found.',404)
            if target['username']!=expected_username:
                raise Problem('This username has changed. Reload the latest account details.',409)
            if username!=target['username']:
                try:c.execute('UPDATE users SET username=? WHERE id=?',(username,target_id))
                except sqlite3.IntegrityError:raise Problem('This username already exists.',409)
                self.event(c,actor,'rename','user',target_id,{'username':target['username']},{'username':username},'Username changed')
            return {**dict(target),'username':username}

    def change_password(self, actor, current_password, new_password):
        if not isinstance(new_password,str) or not 12<=len(new_password)<=200:
            raise Problem('Passwords must contain 12–200 characters.')
        if not isinstance(current_password,str) or not 1<=len(current_password)<=200:
            raise Problem('The current password is incorrect.',403)
        with self.db() as c:
            c.execute('BEGIN IMMEDIATE')
            account=c.execute('SELECT password,salt FROM users WHERE id=?',(actor,)).fetchone()
            if not account:raise Problem('User not found.',404)
            candidate=hashlib.pbkdf2_hmac('sha256',current_password.encode(),bytes.fromhex(account['salt']),600000).hex()
            if not secrets.compare_digest(candidate,account['password']):
                raise Problem('The current password is incorrect.',403)
            if secrets.compare_digest(current_password.encode(),new_password.encode()):
                raise Problem('Choose a different new password.')
            salt=secrets.token_hex(16)
            hashed=hashlib.pbkdf2_hmac('sha256',new_password.encode(),bytes.fromhex(salt),600000).hex()
            c.execute('UPDATE users SET password=?,salt=? WHERE id=?',(hashed,salt,actor))
            c.execute('DELETE FROM sessions WHERE user_id=?',(actor,))
            self.event(c,actor,'password_change','user',actor,None,{'sessions_revoked':True},'Password changed by account owner')
        return {'ok':True}

    def record_login(self,username,outcome):
        name=username[:80] if isinstance(username,str) else '(invalid username)'
        with self.db() as c:
            u=c.execute('SELECT id FROM users WHERE username=?',(name,)).fetchone()
            c.execute('INSERT INTO login_history(user_id,username,outcome,created_at) VALUES(?,?,?,?)',(u['id'] if u else None,name,outcome,stamp()))

    def login_history(self,actor,before=0):
        with self.db() as c:
            u=c.execute('SELECT role FROM users WHERE id=?',(actor,)).fetchone()
            if not u or u['role']!='admin':raise Problem('Only administrators can view this.',403)
            rows=[dict(r) for r in c.execute('SELECT * FROM login_history WHERE (?=0 OR id<?) ORDER BY id DESC LIMIT 101',(before,before))]
        return {'rows':rows[:100],'next_before':rows[99]['id'] if len(rows)>100 else None}

    def login(self,username,password):
        name=username[:80] if isinstance(username,str) else '(invalid username)'
        with self.db() as c:
            u=c.execute('SELECT * FROM users WHERE username=?',(username if isinstance(username,str) else '',)).fetchone()
            valid=False
            if u and isinstance(password,str):
                candidate=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(u['salt']),600000).hex()
                valid=secrets.compare_digest(candidate,u['password'])
            c.execute('INSERT INTO login_history(user_id,username,outcome,created_at) VALUES(?,?,?,?)',(u['id'] if u else None,name,'success' if valid else 'failure',stamp()))
            if valid:
                token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(24)
                c.execute('DELETE FROM sessions WHERE expires<?',(time.time(),))
                c.execute('INSERT INTO sessions VALUES(?,?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),u['id'],csrf,time.time()+43200))
        if not valid:raise Problem('Check your username and password.',401)
        return token,{'id':u['id'],'username':u['username'],'role':u['role'],'csrf':csrf}
    def session(self,token):
        with self.db() as c:
            r=c.execute('SELECT u.id,u.username,u.role,s.csrf FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=? AND s.expires>?',(hashlib.sha256(token.encode()).hexdigest(),time.time())).fetchone()
        if not r: raise Problem('Please log in.',401)
        return dict(r)
    def snapshot(self,include_audit=False):
        with self.db() as c:
            c.execute('BEGIN')
            data={'mice':[dict(r) for r in c.execute('SELECT * FROM mice ORDER BY length(mouse_id),mouse_id')], 'metrics':[dict(r) for r in c.execute('SELECT * FROM metrics ORDER BY name,organ,gate')], 'measurements':[dict(r) for r in c.execute('SELECT * FROM measurements')], 'presets':[{**dict(r),'config':json.loads(r['config'])} for r in c.execute('SELECT * FROM presets')], 'uploads':[dict(r) for r in c.execute("SELECT uploads.id,filename,sha256,uploads.created_at,status,u.username AS uploaded_by FROM uploads JOIN users u ON u.id=uploads.owner WHERE status='committed' ORDER BY uploads.created_at DESC")], 'revision':c.execute('SELECT coalesce(max(id),0) FROM events').fetchone()[0]}
            from scripts.paths import ROOT
            try: data['experiment_types']=json.loads((ROOT/'config/experiment_types.json').read_text())
            except (OSError,ValueError): data['experiment_types']={}
            metrics_by_identity={m['identity']:m for m in data['metrics']}
            for upload in c.execute("SELECT mapping FROM uploads WHERE status='committed' ORDER BY created_at DESC,id"):
                for spec in json.loads(upload['mapping'] or '{}').get('measurements',[]):
                    if not str(spec.get('name','')).startswith('Geometric Mean ('):continue
                    meta={k:clean(spec.get(k)) for k in ('name','unit','organ','gate','parent_gate','denominator')}
                    metric=metrics_by_identity.get(dump(meta))
                    if metric is not None and spec.get('column'):metric.setdefault('source_header',spec['column'])
            if include_audit:return {'schema_version':2,'data':data,'audit':[dict(r) for r in c.execute('SELECT e.*,u.username FROM events e LEFT JOIN users u ON e.actor=u.id ORDER BY e.id DESC')]}
            return data
    def audit(self):
        with self.db() as c:return [dict(r) for r in c.execute('SELECT e.*,u.username FROM events e LEFT JOIN users u ON e.actor=u.id ORDER BY e.id DESC')]
    def archive_upload(self, uid, actor, reason):
        reason = required(reason, 'Removal reason', 2000)
        with self.db() as c:
            c.execute('BEGIN IMMEDIATE')
            upload = c.execute('SELECT filename,owner,status FROM uploads WHERE id=?', (uid,)).fetchone()
            if not upload:
                raise Problem('Upload not found.', 404)
            role = c.execute('SELECT role FROM users WHERE id=?', (actor,)).fetchone()
            if not role or not (role[0] == 'admin' or (role[0] == 'editor' and upload['owner'] == actor)):
                raise Problem('Only the uploader or an administrator can remove this import.', 403)
            if upload['status'] == 'archived':
                return {'removed': 0}
            if upload['status'] != 'committed':
                raise Problem('Only a saved import can be removed.', 409)
            c.execute('CREATE TABLE IF NOT EXISTS archived_test_measurements AS SELECT * FROM measurements WHERE 0')
            c.execute('INSERT INTO archived_test_measurements SELECT * FROM measurements WHERE upload_id=?', (uid,))
            count = c.execute('DELETE FROM measurements WHERE upload_id=?', (uid,)).rowcount
            linked = [r[0] for r in c.execute('SELECT mouse_id FROM upload_mice WHERE upload_id=?', (uid,))]
            c.execute('DELETE FROM upload_mice WHERE upload_id=?', (uid,))
            c.execute("UPDATE uploads SET status='archived' WHERE id=?", (uid,))
            self.event(c, actor, 'archive', 'upload', uid,
                       {'filename': upload['filename'], 'measurements': count, 'linked_mice': linked},
                       {'status': 'archived'}, reason)
            return {'removed': count}

    def stage(self,filename,encoded,actor):
        filename=required(filename,'Filename',250)
        try:raw=base64.b64decode(encoded,validate=True)
        except Exception:raise Problem('Invalid file data')
        if len(raw)>10*1024*1024:raise Problem('Files must not exceed 10 MB.')
        table=self.read_table(filename,raw)
        uid=secrets.token_hex(16)
        with self.db() as c:c.execute('INSERT INTO uploads(id,filename,sha256,original,owner,created_at) VALUES(?,?,?,?,?,?)',(uid,filename,hashlib.sha256(raw).hexdigest(),raw,actor,stamp()))
        return {'upload_id':uid,**table,'rows':table['rows'][:8],'row_count':len(table['rows'])}
    def read_table(self,filename,raw,sheet=None):
        if filename.lower().endswith('.xls'):
            from scripts.imports.facs import read_xls
            return read_xls(raw,sheet,Problem)
        if filename.lower().endswith('.csv'):
            try:rows=list(csv.reader(io.StringIO(raw.decode('utf-8-sig'))))
            except Exception:raise Problem('Save the file as UTF-8 CSV.')
            sheets=[];selected='CSV'
        elif filename.lower().endswith('.xlsx'):
            try:
                from openpyxl import load_workbook
                with zipfile.ZipFile(io.BytesIO(raw)) as z:
                    if sum(x.file_size for x in z.infolist())>60*1024*1024:raise Problem('The uncompressed file is too large.')
                w=load_workbook(io.BytesIO(raw),read_only=True,data_only=False)
                sheets=w.sheetnames;selected=sheet or sheets[0]
                if selected not in sheets:raise Problem('Sheet not found.')
                s=w[selected]
                if s.max_row>10001 or s.max_column>200:raise Problem('The limit is 10,000 rows and 200 columns per import.')
                rows=[]
                for line in s:
                    if any(c.data_type=='f' for c in line):raise Problem('Upload a copy with formulas pasted as values. Original formulas are not recalculated.')
                    rows.append([c.value for c in line])
                w.close()
            except ImportError:raise Problem('The server requires openpyxl.')
            except Problem:raise
            except Exception:raise Problem('Could not read the Excel file.')
        else:raise Problem('Supported formats: CSV, XLSX and FACS XLS.')
        while rows and not any(clean(v) for v in rows[-1]):rows.pop()
        if len(rows)<2:raise Problem('A header row and at least one data row are required.')
        if filename.lower().endswith('.xlsx'):
            from scripts.imports.histology import normalize
            normalized=normalize(rows,sheets,selected,Problem)
            if normalized is not None:
                if selected == 'Sheet1' and hashlib.sha256(raw).hexdigest() == '022f8c6047d10bcaa322649f261db6eccb74faceed87b8264084fd5f387314f2':
                    normalized['confirmed_histology'] = {'organ': 'Liver', 'unit': '%'}
                return normalized
        headers=[clean(v) for v in rows[0]]
        while headers and not headers[-1]:headers.pop()
        if len(headers)>200 or len(rows)>10001:raise Problem('The limit is 10,000 rows and 200 columns.')
        if not all(headers) or len(set(headers))!=len(headers):raise Problem('Column headers must be nonempty and unique. Normalize merged rosters before uploading.')
        data=[];source_rows=[]
        for n,row in enumerate(rows[1:],2):
            if not any(clean(v) for v in row):continue
            if any(clean(v) for v in row[len(headers):]):raise Problem(f'Row {n} contains values without a column header.')
            data.append([clean(row[i]) if i<len(row) else '' for i in range(len(headers))]);source_rows.append(n)
        return {'headers':headers,'rows':data,'source_rows':source_rows,'sheets':sheets,'sheet':selected}
    def preview(self,uid,actor,sheet=None):
        with self.db() as c:r=c.execute('SELECT * FROM uploads WHERE id=? AND owner=?',(uid,actor)).fetchone()
        if not r:raise Problem('Your upload was not found.',404)
        t=self.read_table(r['filename'],r['original'],sheet)
        return {'upload_id':uid,**t,'rows':t['rows'][:8],'row_count':len(t['rows'])}
    def review_import(self,uid,mapping,actor):
        from scripts.imports.validation import review
        with self.db() as c:return review(self,c,uid,mapping,actor)
    def commit_import(self,uid,mapping,actor,reason,review_token=None,require_review=False):
        required(reason,'Import reason',2000)
        with self.db() as c:
            c.execute('BEGIN IMMEDIATE')
            if require_review:
                from scripts.imports.validation import review
                report=review(self,c,uid,mapping,actor)
                if not report['ok']:raise Problem('Import validation failed. Review the file again before saving.',409)
                if not isinstance(review_token,str) or not secrets.compare_digest(review_token,report['review_token']):raise Problem('Mapping or database changed. Run validation again before saving.',409)
            u=c.execute('SELECT * FROM uploads WHERE id=? AND owner=?',(uid,actor)).fetchone()
            if not u:raise Problem('Your upload was not found.',404)
            if u['status']!='pending':raise Problem('This file has already been imported.',409)
            table=self.read_table(u['filename'],u['original'],mapping.get('sheet'))
            facs=table.get('facs');selected_rows={}
            if facs:
                if mapping.get('facs_reviewed') is not True:raise Problem('Verify the sample-to-mouse ID mapping.')
                candidates={r['row']:r for r in facs['samples'] if r['kind']=='sample'}
                for entry in mapping.get('sample_rows',[]):
                    n=entry.get('row')
                    if n not in candidates or n in selected_rows:raise Problem('Invalid or duplicate FACS sample rows.')
                    selected_rows[n]={**candidates[n],'mouse_id':required(entry.get('mouse_id'),'Mouse ID',100),'group':clean(entry.get('group'))}
                if not selected_rows:raise Problem('Select samples to import.')
                if len({r['organ'] for r in selected_rows.values()})!=1:raise Problem('Select one organ at a time.')
                if facs['needs_statistic']:
                    required(mapping.get('facs_statistic'),'Calculated statistic name')
                    required(mapping.get('facs_unit'),'Calculated statistic unit')
            headers=table['headers'];id_col=mapping.get('id_column');group_col=mapping.get('group_column')
            if id_col not in headers:raise Problem('Select the Mouse ID column.')
            specs=mapping.get('measurements',[])
            meta_only=mapping.get('metadata_only') is True
            if meta_only and (specs or facs):raise Problem('Metadata-only import cannot contain measurements or a FACS table.')
            if not specs and not meta_only:raise Problem('Select at least one measurement column.')
            if len(specs)>200 or len(specs)*len(table['rows'])>100000:raise Problem('The limit is 200 columns and 100,000 observations per import.')
            metric_specs=[]
            for spec in specs:
                if spec.get('column') not in headers:raise Problem('Invalid measurement column')
                meta={k:clean(spec.get(k)) for k in ('name','unit','organ','gate','parent_gate','denominator')}
                if facs:
                    if spec['column'] not in {s['column'] for s in facs['specs']}:raise Problem('Sample names are not a measurement column.')
                    if meta['organ']!=next(iter(selected_rows.values()))['organ']:raise Problem('Match the metric definition to the selected samples\' organ.')
                    if facs['needs_statistic']:
                        meta['name']=mapping['facs_statistic'].strip();meta['unit']=mapping['facs_unit'].strip()
                        meta['denominator']='사용자 확인 계산값'
                required(meta['name'],'Metric');required(meta['unit'],'Unit')
                if meta['gate'] and not all(meta[k] for k in ('organ','parent_gate','denominator')):raise Problem('A gate requires an organ, parent gate and denominator.')
                identity=dump(meta)
                c.execute('INSERT OR IGNORE INTO metrics(identity,name,unit,organ,gate,parent_gate,denominator) VALUES(?,?,?,?,?,?,?)',(identity,*meta.values()))
                mid=c.execute('SELECT id FROM metrics WHERE identity=?',(identity,)).fetchone()[0]
                metric_specs.append((spec,meta,mid))
            added=0;new_mice=0
            for index,values in zip(table['source_rows'],table['rows']):
                if facs and index not in selected_rows:continue
                row=dict(zip(headers,values));mouse_id=required(row[id_col],f'Row {index}: mouse ID',100)
                if facs:mouse_id=selected_rows[index]['mouse_id']
                found=c.execute('SELECT * FROM mice WHERE mouse_id=?',(mouse_id,)).fetchone()
                group=clean(row.get(group_col))
                if facs:group=selected_rows[index]['group']
                if meta_only and not found and not group:group=clean(row.get(mapping.get('diet_column')))
                if not found:
                    required(group,f'Row {index}: group for new mouse {mouse_id}')
                    m={'mouse_id':mouse_id,'group_name':group,'experiment':clean(row.get(mapping.get('experiment_column'))),'weeks':clean(row.get(mapping.get('weeks_column'))),'diet':clean(row.get(mapping.get('diet_column'))),'note':''}
                    c.execute('INSERT INTO mice(mouse_id,group_name,experiment,weeks,diet,note,source) VALUES(?,?,?,?,?,?,?)',(*m.values(),dump({'upload_id':uid,'row':index})))
                    self.event(c,actor,'create','mouse',mouse_id,None,m,reason);new_mice+=1
                elif group and group!=found['group_name']:raise Problem(f'Row {index}: group differs from the existing group for {mouse_id}. Change it in the mouse roster editor.',409)
                c.execute('INSERT OR IGNORE INTO upload_mice(upload_id,mouse_id) VALUES(?,?)',(uid,mouse_id))
                for spec,meta,mid in metric_specs:
                    tp=clean(row.get(spec.get('time_column'))) if spec.get('time_column') else clean(spec.get('timepoint')) or 'endpoint'
                    if not tp:raise Problem(f'Row {index}: timepoint is blank.')
                    rep=clean(row.get(mapping.get('replicate_column'))) or '1'
                    v=row[spec['column']];missing=clean(spec.get('missing_reason')) or '업로드 파일의 빈 셀'
                    if facs and v.lower()=='n/a':v='';missing='원본 n/a'
                    val=number(v,missing if v=='' else '',meta['unit'])
                    try:rid=c.execute('INSERT INTO measurements(mouse_id,metric_id,timepoint,replicate,value,missing_reason,upload_id,source_row) VALUES(?,?,?,?,?,?,?,?)',(mouse_id,mid,tp,rep,val,missing if val is None else '',uid,index)).lastrowid
                    except sqlite3.IntegrityError:raise Problem(f'Row {index}: duplicate mouse {mouse_id} / {meta["name"]} / {tp} / replicate {rep}. Edit existing values in the measurement editor.',409)
                    self.event(c,actor,'create','measurement',rid,None,{'mouse_id':mouse_id,'metric_id':mid,'timepoint':tp,'replicate':rep,'value':val,'missing_reason':missing if val is None else ''},reason);added+=1
            c.execute("UPDATE uploads SET status='committed',mapping=? WHERE id=?",(dump(mapping),uid))
            self.event(c,actor,'import','upload',uid,None,{'measurements':added,'new_mice':new_mice,'sha256':u['sha256'],'mapping':mapping,'source_interpretation':facs},reason)
        return {'measurements':added,'new_mice':new_mice}
    def edit_measurement(self,rid,data,actor):
        reason=required(data.get('reason'),'Edit reason',2000)
        with self.db() as c:
            c.execute('BEGIN IMMEDIATE');old=c.execute('SELECT m.*,d.unit FROM measurements m JOIN metrics d ON m.metric_id=d.id WHERE m.id=?',(rid,)).fetchone()
            if not old:raise Problem('Measurement not found.',404)
            if data.get('version')!=old['version']:raise Problem('Another user has edited this value. Reload the latest value.',409)
            missing=clean(data.get('missing_reason'));value=number(data.get('value'),missing,old['unit'])
            c.execute('UPDATE measurements SET value=?,missing_reason=?,version=version+1 WHERE id=?',(value,missing,rid))
            new=dict(c.execute('SELECT * FROM measurements WHERE id=?',(rid,)).fetchone());self.event(c,actor,'edit','measurement',rid,dict(old),new,reason)
        return new
    def edit_mouse(self,mid,data,actor):
        reason=required(data.get('reason'),'Change reason',2000)
        with self.db() as c:
            c.execute('BEGIN IMMEDIATE');old=c.execute('SELECT * FROM mice WHERE mouse_id=?',(mid,)).fetchone()
            if not old:raise Problem('Mouse not found.',404)
            if data.get('version')!=old['version']:raise Problem('Another user has made changes. Reload the latest state.',409)
            new=dict(old)
            for k in ('group_name','experiment','weeks','diet','note'):
                if k in data:new[k]=clean(data[k])
            required(new['group_name'],'Group')
            if 'excluded' in data:
                if not isinstance(data['excluded'],bool):raise Problem('Invalid exclusion status')
                new['excluded']=int(data['excluded'])
            c.execute('UPDATE mice SET group_name=?,experiment=?,weeks=?,diet=?,note=?,excluded=?,version=version+1 WHERE mouse_id=?',tuple(new[k] for k in ('group_name','experiment','weeks','diet','note','excluded'))+(mid,))
            new=dict(c.execute('SELECT * FROM mice WHERE mouse_id=?',(mid,)).fetchone());action=('exclude' if new['excluded'] else 'restore') if old['excluded']!=new['excluded'] else 'edit'
            self.event(c,actor,action,'mouse',mid,dict(old),new,reason)
        return new
    def set_sample_inclusion(self,data,actor):
        reason=required(data.get('reason'),'Sample selection reason',2000)
        changes=data.get('changes')
        if not isinstance(changes,list) or not changes or len(changes)>10000:raise Problem('Select samples to change.')
        seen=set();updated=[]
        with self.db() as c:
            c.execute('BEGIN IMMEDIATE')
            for item in changes:
                if not isinstance(item,dict):raise Problem('Invalid sample selection')
                mid=required(item.get('mouse_id'),'Mouse ID',100)
                if mid in seen:raise Problem('Duplicate Mouse IDs.')
                seen.add(mid)
                if not isinstance(item.get('included'),bool):raise Problem('Invalid inclusion status')
                old=c.execute('SELECT * FROM mice WHERE mouse_id=?',(mid,)).fetchone()
                if not old:raise Problem(f'Mouse {mid} was not found.',404)
                if item.get('version')!=old['version']:raise Problem(f'Mouse {mid}: another user has made changes. Reload the latest state and select again.',409)
                excluded=int(not item['included'])
                if old['excluded']==excluded:continue
                c.execute('UPDATE mice SET excluded=?,version=version+1 WHERE mouse_id=?',(excluded,mid))
                new=dict(c.execute('SELECT * FROM mice WHERE mouse_id=?',(mid,)).fetchone())
                self.event(c,actor,'exclude' if excluded else 'restore','mouse',mid,dict(old),new,reason)
                updated.append(mid)
        return {'updated':updated}
    def preset(self,data,actor):
        name=required(data.get('name'),'Preset name',100);config=data.get('config')
        if not isinstance(config,dict) or len(dump(config))>50000:raise Problem('Invalid preset')
        board=config.get('dashboard')
        if board is not None:
            if not isinstance(board,dict) or not isinstance(board.get('panels'),list) or not 4<=len(board['panels'])<=8:raise Problem('Save between 4 and 8 graphs.')
            count=board.get('count',len(board['panels']))
            if type(count) is not int or not 4<=count<=len(board['panels']):raise Problem('Invalid graph count')
            active=board.get('active',0)
            if type(active) is not int or not 0<=active<count:raise Problem('Invalid active graph')
            for panel in board['panels']:
                if not isinstance(panel,dict) or panel.get('type') not in ('bar','scatter','line') or panel.get('error') not in ('SD','SEM','none'):raise Problem('Check the graph type and error bars for each graph.')
            shared=board.get('groupSettings')
            if shared is not None:
                if not isinstance(shared,dict) or len(shared)>200:raise Problem('Invalid shared group formatting')
                for key,style in shared.items():
                    if not isinstance(key,str) or not 1<=len(key)<=200 or not isinstance(style,dict):raise Problem('Invalid shared group formatting')
                    if not re.fullmatch(r'#[0-9a-fA-F]{6}',str(style.get('color',''))) or style.get('shape') not in ('square','triangle','down','diamond','circle') or style.get('fill') not in ('solid','outline'):raise Problem('Check the shared group colors, symbols and fills.')
                    if type(style.get('order')) is not int or style['order']<1 or not isinstance(style.get('include'),bool):raise Problem('Check shared group visibility and order.')
        if config.get('error','SD') not in ('SD','SEM','none'):raise Problem('Invalid error bars')
        if config.get('type','bar') not in ('bar','scatter','line'):raise Problem('Invalid graph type')
        if not isinstance(config.get('styles',{}),dict):raise Problem('Invalid group formatting')
        for group,style in config.get('styles',{}).items():
            if not isinstance(style,dict) or not re.fullmatch(r'#[0-9a-fA-F]{6}',style.get('color','')):raise Problem('Colors must use the #RRGGBB format.')
            if style.get('shape') not in ('square','triangle','down','diamond','circle') or style.get('fill') not in ('solid','outline'):raise Problem('Invalid symbol or fill')
            order=style.get('order')
            if not isinstance(order,(int,float)) or not math.isfinite(order):raise Problem('Group order must be numeric.')
            if not isinstance(style.get('include'),bool):raise Problem('Invalid group selection')
        with self.db() as c:
            c.execute('BEGIN IMMEDIATE');old=c.execute('SELECT * FROM presets WHERE name=?',(name,)).fetchone()
            if old and data.get('version')!=old['version']:raise Problem('The preset has changed. Reload it.',409)
            if old:c.execute('UPDATE presets SET config=?,version=version+1,updated_at=? WHERE id=?',(dump(config),stamp(),old['id']))
            else:c.execute('INSERT INTO presets(name,config,updated_at) VALUES(?,?,?)',(name,dump(config),stamp()))
            new=dict(c.execute('SELECT * FROM presets WHERE name=?',(name,)).fetchone());self.event(c,actor,'save','preset',new['id'],dict(old) if old else None,new,'Graph preset saved')
        return new
