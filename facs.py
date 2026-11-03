"""Read FlowJo-style XLS tables without changing the source workbook."""
import hashlib, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'vendor'))

SAMPLE = re.compile(r'^(?:\d{4}-\d{2}-\d{2}_)?([A-Za-z][A-Za-z -]*)_(\d+)(?:_(\d+))?\.fcs$', re.I)
STAT = re.compile(r'^(.+)\s+\|\s+(Count|Freq\. of Parent(?: \(%\))?|Geometric Mean \(.+\))$')

def is_header(row):
    return len(row)>1 and all(STAT.fullmatch(str(x).strip()) for x in row[1:] if str(x).strip()) and any(str(x).strip() for x in row[1:])

def describe(headers, rows, source_rows, block=1):
    if not is_header(headers):return None
    samples=[]
    for row, index in zip(rows,source_rows):
        name=str(row[0]).strip();match=SAMPLE.fullmatch(name)
        kind='sample' if match else 'summary' if name.lower() in ('mean','sd','median','cv') else 'control / unmapped'
        samples.append({'row':index,'sample':name,'kind':kind,'mouse_id':match[2] if match else '', 'organ':match[1] if match else '', 'acquisition_suffix':match[3] or '' if match else ''})
    organs=sorted({r['organ'] for r in samples if r['kind']=='sample'})
    specs=[]
    for header in headers[1:]:
        m=STAT.fullmatch(header)
        if not m:continue
        gate,stat=m.groups();parent=gate.rpartition('/')[0] or '원본에 상위 경로 없음'
        specs.append({'column':header,'name':stat,'unit':'events' if stat=='Count' else '%' if stat.startswith('Freq.') else 'a.u.', 'organ':organs[0] if len(organs)==1 else '', 'gate':gate,'parent_gate':parent,'denominator':parent if stat.startswith('Freq.') else '해당 gate의 event 수' if stat=='Count' else '해당 gate의 형광 강도', 'timepoint':'endpoint'})
    return {'samples':samples,'specs':specs,'block':block,'needs_statistic':block>1,'organs':organs}

def read_xls(raw, selected, Problem):
    try:
        import xlrd
        w=xlrd.open_workbook(file_contents=raw,formatting_info=True)
    except Exception as e:raise Problem('Could not read the XLS file.') from e
    choices={}
    for s in w.sheets():
        if s.nrows>10001 or s.ncols>200:raise Problem('The limit is 10,000 rows and 200 columns per import.')
        starts=[r for r in range(s.nrows) if is_header(s.row_values(r))]
        if not starts or starts[0]!=0:continue
        for b,start in enumerate(starts):
            label=s.name if len(starts)==1 else f'{s.name} ⟦표 {b+1}: {start+1}행⟧'
            choices[label]=(s,start,starts[b+1] if b+1<len(starts) else s.nrows,b+1)
    if not choices:raise Problem('XLS supports FACS exports with gate | statistic headers. Save ordinary tables as XLSX or CSV.')
    profiles_path=Path(__file__).with_name('import_profiles.json')
    profiles=json.loads(profiles_path.read_text()) if profiles_path.exists() else {}
    profile=profiles.get(hashlib.sha256(raw).hexdigest(),{})
    selected=selected or profile.get('table') or next(iter(choices))
    if selected not in choices:raise Problem('Sheet or table not found.')
    s,start,end,block=choices[selected]
    headers=[str(v).strip() for v in s.row_values(start)];headers[0]=headers[0] or 'Sample'
    if not all(headers) or len(set(headers))!=len(headers):raise Problem('FACS headers must be nonempty and unique.')
    rows=[];indices=[];percent_cells=0
    for r in range(start+1,end):
        values=s.row_values(r)
        if not any(str(v).strip() for v in values):continue
        for col in range(1,len(values)):
            cell=s.cell(r,col)
            fmt=w.format_map[w.xf_list[cell.xf_index].format_key].format_str
            # An Excel percentage stores a fraction. Use its displayed percentage units.
            if cell.ctype==xlrd.XL_CELL_NUMBER and '%' in fmt and STAT.fullmatch(headers[col])[2].startswith('Freq.'):
                values[col]*=100;percent_cells+=1
            if cell.ctype==xlrd.XL_CELL_ERROR:values[col]='n/a'
        rows.append([str(v).strip() for v in values]);indices.append(r+1)
    facs=describe(headers,rows,indices,block)
    facs['percent_cells_converted']=percent_cells
    facs['source_sheet']=s.name
    facs['header_row']=start+1
    facs['confirmed_definition']=profile if profile.get('table')==selected else None
    sample_indices={r['row'] for r in facs['samples'] if r['kind']=='sample'}
    for spec in facs['specs']:
        column=headers.index(spec['column'])
        spec['has_values']=any(row[column] and row[column].lower()!='n/a' for row,index in zip(rows,indices) if index in sample_indices)
    facs['notice']='Numbers in filenames are candidate mouse IDs. Control and unmapped rows are excluded by default. The source owner must verify ID changes between sheets and the meaning of calculated tables. Excel percentage cells are multiplied by 100 for display. Original gate paths are preserved.'
    return {'headers':headers,'rows':rows,'source_rows':indices,'sheets':list(choices),'sheet':selected,'facs':facs}
