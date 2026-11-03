"""Read WSP references and map only administrator-configured SMB roots."""
import json, re, stat
from pathlib import Path
from urllib.parse import unquote, urlsplit
from fcs_worker import workspace_metadata
from service import Problem

def mappings():
    try:
        data=json.loads(Path(__file__).with_name('fcs_paths.json').read_text())
        return data['mappings']
    except (OSError,ValueError,KeyError,TypeError):
        return []

def windows_path(uri):
    value=unquote(str(uri or ''))
    if value.lower().startswith('file:'):
        parsed=urlsplit(value)
        if parsed.netloc and parsed.netloc.lower()!='localhost':
            value='//'+parsed.netloc+parsed.path
        else:value=parsed.path
    value=value.replace('\\','/')
    if re.match(r'^/[A-Za-z]:/',value):value=value[1:]
    return value

def mapped_path(uri, rules=None):
    value=windows_path(uri)
    if '\x00' in value:raise ValueError('Invalid file path.')
    for rule in mappings() if rules is None else rules:
        prefix=windows_path(rule['workspace_prefix']).rstrip('/')+'/'
        if not value.casefold().startswith(prefix.casefold()):continue
        relative=value[len(prefix):]
        if any(p in ('..','.') for p in relative.split('/')):raise ValueError('Path traversal is not allowed.')
        root=Path(rule['server_root']).resolve()
        path=(root/relative).resolve()
        if not path.is_relative_to(root):raise ValueError('Path leaves the approved shared folder.')
        if path.suffix.lower()!='.fcs':raise ValueError('Only FCS source files may be imported.')
        return path,root
    return None,None

def references(path, catalog=(), rules=None):
    # shared safe parser rejects document types/entities
    meta=workspace_metadata(path)
    import xml.etree.ElementTree as E
    root=E.parse(path).getroot()
    raw={}
    for sample in root.findall('SampleList/Sample'):
        node=sample.find('SampleNode');dataset=sample.find('DataSet')
        if node is not None:
            sid=node.get('sampleID')
            if sid in raw:raise Problem('Duplicate WSP sample identifiers.',422)
            raw[sid]=dataset.get('uri','') if dataset is not None else ''
    rows=[]
    for sample in meta['samples']:
        uri=raw.get(sample['sample_id'],'');mapped=None;state='Unmapped';size=None
        try:
            mapped,approved=mapped_path(uri,rules)
            if mapped is not None:
                if not approved.is_dir():state='Share not mounted'
                elif not mapped.exists():state='File not found'
                else:
                    st=mapped.stat()
                    state='Available' if stat.S_ISREG(st.st_mode) else 'Not a regular file'
                    size=st.st_size if state=='Available' else None
        except (ValueError,OSError):state='Path unavailable'
        rows.append({'sample_id':sample['sample_id'],'name':sample['name'],'events':sample['events'],
                     'original_uri':uri,'server_path':str(mapped) if mapped else None,'status':state,'size':size,
                     'uploaded_name_matches':[f['id'] for f in catalog if f['kind']=='fcs' and f['filename']==sample['name']]})
    return rows
