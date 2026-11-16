"""Read-only Excel image extraction and audited, versioned strategy assignments."""
import hashlib, io, json, posixpath, re, zipfile
from pathlib import PurePosixPath
import xml.etree.ElementTree as ET
from scripts.app.service import Problem, required, stamp

NS={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships','a':'http://schemas.openxmlformats.org/drawingml/2006/main','x':'http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing'}

def extract(raw):
    if len(raw)>10*1024*1024:raise Problem('Workbook exceeds 10 MB.')
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            if sum(i.file_size for i in z.infolist())>60*1024*1024 or len(z.infolist())>5000:raise Problem('Workbook expands beyond the allowed limit.')
            def xml(path):return ET.fromstring(z.read(path))
            def rels(part):
                p=PurePosixPath(part);rp=str(p.parent/'_rels'/(p.name+'.rels'))
                if rp not in z.namelist():return {}
                return {e.attrib['Id']:posixpath.normpath(posixpath.join(str(p.parent),e.attrib['Target'])) if not e.attrib['Target'].startswith('/') else e.attrib['Target'].lstrip('/') for e in xml(rp) if e.attrib.get('TargetMode')!='External'}
            wr=rels('xl/workbook.xml');locations={}
            for sheet in xml('xl/workbook.xml').find('m:sheets',NS):
                part=wr.get(sheet.attrib.get('{'+NS['r']+'}id'));sr=rels(part)
                for draw in xml(part).findall('m:drawing',NS):
                    dp=sr.get(draw.attrib.get('{'+NS['r']+'}id'))
                    if not dp:continue
                    dr=rels(dp)
                    for anchor in xml(dp).iter():
                        if anchor.tag.rsplit('}',1)[-1] not in ('twoCellAnchor','oneCellAnchor','absoluteAnchor'):continue
                        row=anchor.find('x:from/x:row',NS);col=anchor.find('x:from/x:col',NS)
                        location=f'row {int(row.text)+1}, column {int(col.text)+1}' if row is not None and col is not None else 'absolute anchor'
                        for blip in anchor.findall('.//a:blip',NS):
                            target=dr.get(blip.attrib.get('{'+NS['r']+'}embed'))
                            if target:locations.setdefault(target,set()).add((sheet.attrib['name'],location))
            result=[]
            for member in sorted(z.namelist()):
                if not member.startswith('xl/media/') or member.endswith('/'):continue
                content=z.read(member);ext=PurePosixPath(member).suffix.lower();ext=ext if ext in ('.png','.jpg','.jpeg','.emf','.wmf','.wdp','.gif','.tiff') else '.bin'
                mime='image/png' if content.startswith(b'\x89PNG\r\n\x1a\n') else ('image/jpeg' if content.startswith(b'\xff\xd8\xff') else '')
                for sheet,anchor in sorted(locations.get(member,{('','Unmapped media; inspect original workbook')})):
                    result.append(dict(member=member,sheet=sheet,anchor=anchor,original=content,mime=mime,extension=ext))
            if len(result)>500:raise Problem('Too many workbook images.')
            return result
    except (zipfile.BadZipFile,KeyError,ValueError,ET.ParseError,TypeError) as e:raise Problem('Cannot read XLSX image relationships.') from e

class StrategyLibrary:
    def __init__(self,store):
        self.store=store
        with store.db() as c:c.executescript('''
CREATE TABLE IF NOT EXISTS strategy_sources(id TEXT PRIMARY KEY,filename TEXT NOT NULL,original BLOB NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS strategy_images(id TEXT PRIMARY KEY,source_id TEXT NOT NULL REFERENCES strategy_sources(id),member TEXT NOT NULL,sheet TEXT NOT NULL,anchor TEXT NOT NULL,original BLOB NOT NULL,mime TEXT NOT NULL,extension TEXT NOT NULL,experiment TEXT NOT NULL DEFAULT '',organ TEXT NOT NULL DEFAULT '',panel TEXT NOT NULL DEFAULT '',description TEXT NOT NULL DEFAULT '',status TEXT NOT NULL DEFAULT 'pending',version INTEGER NOT NULL DEFAULT 1);
''')
    def admin(self,c,actor):
        u=c.execute('SELECT role FROM users WHERE id=?',(actor,)).fetchone()
        if not u or u['role']!='admin':raise Problem('Only administrators can review strategy images.',403)
    def ingest(self,filename,raw,actor):
        with self.store.db() as c:self.admin(c,actor)
        if not str(filename).lower().endswith('.xlsx'):raise Problem('Choose an XLSX workbook.')
        images=extract(raw);sid=hashlib.sha256(raw).hexdigest();added=0
        with self.store.db() as c:
            c.execute('BEGIN IMMEDIATE');self.admin(c,actor)
            total=c.execute('SELECT coalesce(sum(length(original)),0) FROM strategy_sources').fetchone()[0]
            if total+len(raw)>100*1024*1024 and not c.execute('SELECT 1 FROM strategy_sources WHERE id=?',(sid,)).fetchone():raise Problem('Strategy source library exceeds 100 MB.')
            c.execute('INSERT OR IGNORE INTO strategy_sources VALUES(?,?,?,?)',(sid,str(filename)[:200],raw,stamp()))
            for item in images:
                iid=hashlib.sha256(json.dumps([sid,item['member'],item['sheet'],item['anchor']]).encode()).hexdigest()
                added+=c.execute('INSERT OR IGNORE INTO strategy_images(id,source_id,member,sheet,anchor,original,mime,extension) VALUES(?,?,?,?,?,?,?,?)',(iid,sid,item['member'],item['sheet'],item['anchor'],item['original'],item['mime'],item['extension'])).rowcount
            if added:self.store.event(c,actor,'extract','strategy_source',sid,None,{'filename':filename,'images':added},'Extract original workbook images for review')
        return {'added':added,'source_id':sid}
    def catalog(self,user,review=False):
        with self.store.db() as c:
            if review:self.admin(c,user['id'])
            rows=[dict(r) for r in c.execute("SELECT i.id,i.source_id,s.filename,i.member,i.sheet,i.anchor,i.mime,i.extension,i.experiment,i.organ,i.panel,i.description,i.status,i.version FROM strategy_images i JOIN strategy_sources s ON s.id=i.source_id "+('' if review else "WHERE i.status='approved'")+" ORDER BY s.filename,i.sheet,i.anchor,i.member")]
        return rows
    def source(self,iid,user,kind):
        with self.store.db() as c:
            r=c.execute('SELECT i.*,s.original AS workbook FROM strategy_images i JOIN strategy_sources s ON s.id=i.source_id WHERE i.id=?',(iid,)).fetchone()
            if not r or (r['status']!='approved' and user['role']!='admin'):raise Problem('Strategy image not found.',404)
            if kind=='workbook':return r['workbook'],'application/octet-stream','strategy-source.xlsx'
            if kind=='preview':
                if not r['mime']:raise Problem('Preview unavailable. Download the original workbook.',404)
                return r['original'],r['mime'],None
            return r['original'],'application/octet-stream','strategy-original'+r['extension']
    def review(self,iid,d,user):
        with self.store.db() as c:
            c.execute('BEGIN IMMEDIATE');self.admin(c,user['id'])
            old=c.execute('SELECT experiment,organ,panel,description,status,version FROM strategy_images WHERE id=?',(iid,)).fetchone()
            if not old:raise Problem('Image not found.',404)
            if d.get('version')!=old['version']:raise Problem('This image was changed by another user. Reload it.',409)
            status=d.get('status')
            if status not in ('pending','approved','not_strategy'):raise Problem('Invalid review status.')
            values={k:str(d.get(k,'')).strip() for k in ('experiment','organ','panel','description')}
            if any(len(v)>2000 for v in values.values()):raise Problem('Description is too long.')
            if status=='approved':
                for k in ('experiment','organ','panel'):values[k]=required(values[k],k)
            after={**values,'status':status,'version':old['version']+1}
            reason=required(d.get('reason'),'Reason',2000)
            c.execute('UPDATE strategy_images SET experiment=?,organ=?,panel=?,description=?,status=?,version=? WHERE id=?',(*values.values(),status,after['version'],iid))
            self.store.event(c,user['id'],'review','strategy_image',iid,dict(old),after,reason)
        return after
