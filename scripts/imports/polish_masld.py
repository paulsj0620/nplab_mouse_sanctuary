"""Read-only MASLD extraction. Never opens a database or writes source workbooks.

Produces a JSON intermediate for the audited XLSX builder. Mouse-info is the
authoritative roster; ambiguous units, dates and IDs remain review records.
"""
import argparse, collections, datetime as dt, hashlib, json, math, re
from pathlib import Path
import openpyxl


def text(v):
    return '' if v is None else str(v).strip()


def diet(v):
    s=text(v).lower()
    if '10:14' in s:return 'TRF 10:14'
    if '6:18' in s:return 'TRF 6:18'
    if 'reverse' in s or s=='rf':return 'Reverse'
    if 'alternate' in s or s=='adf':return 'ADF'
    if 'chow' in s or s in ('cd','ko','ko1','ko2'):return 'Chow'
    if 'western' in s or s in ('wd','wd1','wd2'):return 'Western'
    return text(v)


def digest(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,default=str).encode()).hexdigest()[:16]


def run(root, output):
    files=sorted(root.glob('*.xlsx')); hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    books={p.name:openpyxl.load_workbook(p,data_only=False) for p in files}
    cached={p.name:openpyxl.load_workbook(p,data_only=True) for p in files}
    roster={}; aliases=collections.defaultdict(set); reviews=[]; defs={}; records=[]; used=set(); links=[]
    def issue(code,f,s,a,detail,mouse='',action='Confirm before import'):
        reviews.append(dict(issue_id='R'+str(len(reviews)+1).zfill(5),code=code,mouse_id=mouse,source_file=f,sheet=s,cell=a,detail=detail,action=action,resolution=''))
    def val(f,s,r,c):return books[f][s].cell(r,c).value
    rs=books['Mouse-info.xlsx'].active
    for offset in (0,6):
        exp=''
        for r in range(2,rs.max_row+1):
            if rs.cell(r,offset+1).value:exp=re.sub(r'\s+','',text(rs.cell(r,offset+1).value))
            mid=rs.cell(r,offset+2).value
            if not isinstance(mid,(int,float)):continue
            mid=str(int(mid));raw=text(rs.cell(r,offset+3).value);week=re.search(r'(\d+)\s*weeks',raw)
            assert mid not in roster, 'Duplicate authoritative roster ID'
            roster[mid]=dict(mouse_id=mid,experiment=exp,diet=diet(raw),weeks=int(week[1]) if week else None,group=raw,notes=text(rs.cell(r,offset+4).value),source_file='Mouse-info.xlsx',source_sheet=rs.title,source_cell=rs.cell(r,offset+2).coordinate)
    assert len(roster)==183 and set(roster)==set(map(str,range(1,184)))
    # Only explicit Perakakis ID / Pyret rows establish cross-identifiers.
    alias_rows=[]
    for f,w in books.items():
        if 'Available Material for future' not in w:continue
        s=w['Available Material for future']
        for row in s:
            mid=row[0].value;pyret=text(row[1].value)
            if isinstance(mid,(int,float)) and pyret.startswith('HH1-'):
                mid=str(int(mid))
                if mid in roster:
                    aliases[pyret].add(mid)
                    alias_rows.append(dict(mouse_id=mid,alias=pyret,earmark=row[2].value,source_file=f,source_sheet=s.title,source_cell=row[1].coordinate))
    for alias,ids in aliases.items():
        if len(ids)>1:issue('ALIAS_CONFLICT','','',alias,','.join(sorted(ids)))
    def resolve(raw,exp):
        s=text(raw)
        if s in aliases:return next(iter(aliases[s])) if len(aliases[s])==1 else None
        m=re.fullmatch(r'(?:Liver|Gut|Spleen)[_ -](\d+)(?:\.fcs)?',s,re.I)
        if not m:m=re.search(r'-(\d+)_Unmixed\.fcs$',s,re.I)
        if m:return m[1] if m[1] in roster else None
        if re.fullmatch(r'\d+(?:\.0)?',s):
            k=str(int(float(s)))
            if k in roster and roster[k]['experiment']==exp:return k
        return None
    # Cage / earmark lookup is specific to an experiment and uses explicit weight rows.
    cage_map=collections.defaultdict(set);ear_map=collections.defaultdict(set)
    for f,w in books.items():
        if 'Metabolic Biochemical outcomes' not in w:continue
        exp=f.replace('.xlsx','').replace(' ','');s=w['Metabolic Biochemical outcomes']
        for row in s:
            if len(row)<4:continue
            alias=text(row[1].value);cage=text(row[3].value);ear=row[2].value
            if alias.startswith('HH1-') and cage.startswith('EHH1-'):
                mid=resolve(alias,exp)
                if mid:
                    cage_map[(exp,int(cage.split('-')[-1]),text(ear))].add(mid)
                    ear_map[(exp,roster[mid]['diet'],text(ear))].add(mid)
    def add(f,s,r,c,mid,category,name,unit,organ='',panel='',gate='',denominator='',timepoint='endpoint',raw_id='',hold='',header=''):
        cell=books[f][s].cell(r,c);raw=cell.value;v=raw;formula='';reasons=[]
        if hold:reasons.append(hold)
        if not mid:reasons.append('ID_NOT_IN_ROSTER_OR_AMBIGUOUS')
        if cell.data_type=='f':formula=raw;v=cached[f][s][cell.coordinate].value;reasons.append('SOURCE_FORMULA_REQUIRES_REVIEW')
        missing=''
        if v is None:missing='Blank source cell'
        elif isinstance(v,str):
            if v.strip().lower() in ('n/a','na','keine probe','-','nd','not measured'):missing=v;v=None
            else:reasons.append('NON_NUMERIC_MEASUREMENT');v=None
        elif not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v):reasons.append('INVALID_NUMBER');v=None
        scale=100 if unit=='%' and '%' in cell.number_format else 1
        normalized=v*scale if v is not None else None
        if normalized is not None and unit=='%' and not 0<=normalized<=100:reasons.append('PERCENT_OUT_OF_RANGE')
        if normalized is not None and normalized<0 and name!='MFI':reasons.append('NEGATIVE_VALUE')
        # Red highlights are annotations requiring interpretation, not automatic exclusion.
        colors=[cell.fill.fgColor.index,cell.font.color.index if cell.font.color else None]
        if any(isinstance(x,str) and x.upper() in ('FFFF0000','00FF0000','FFFFC7CE') for x in colors):reasons.append('SOURCE_COLOR_ANNOTATION')
        identity=[category,name,unit,organ,panel,gate,denominator]
        metric='M'+digest(identity)
        defs.setdefault(metric,dict(metric_id=metric,category=category,name=name,unit=unit,organ=organ,panel=panel,gate=gate,display_gate=gate.rsplit('/',1)[-1],denominator=denominator))
        rec=dict(mouse_id=mid or '',metric_id=metric,timepoint=timepoint,replicate='1',value=normalized,missing_reason=missing,status='review' if reasons else ('missing' if v is None else 'ready'),review_reason='; '.join(sorted(set(reasons))),raw_id=text(raw_id),raw_value=raw,source_formula=formula,source_format=cell.number_format,scale_factor=scale,source_header=header,source_file=f,source_sheet=s,source_cell=cell.coordinate)
        records.append(rec);used.add((f,s,cell.coordinate))
    for f,w in books.items():
        if f=='Mouse-info.xlsx':continue
        exp=f.replace('.xlsx','').replace(' ','')
        ds=w['Description - Experiment'];title=text(ds['A8'].value)
        if re.sub(r'\D','',title)!=re.sub(r'\D','',exp):issue('EXPERIMENT_TITLE_MISMATCH',f,ds.title,'A8',title+'; file '+exp,action='Roster experiment retained')
        for sn in ['FACS panels Liver','FACS panels Gut']:
            s=w[sn];organ='Liver' if 'Liver' in sn else 'Gut';panel='Gut DC Panel' if organ=='Gut' else '';block=None
            for r in range(1,s.max_row+1):
                a=text(s.cell(r,1).value);b=text(s.cell(r,2).value)
                if a.lower() in ('t cell panel','treg panel'):panel='T Cell Panel' if a.lower()=='t cell panel' else 'Treg Panel';block=None
                if b in ('Frequency','MFI','Count'):
                    block=(r,b);continue
                if not block or not (isinstance(s.cell(r,2).value,(int,float)) or re.search(r'\.fcs$',b,re.I)):continue
                mid=resolve(b,exp)
                # Gut copies use authoritative IDs even when the containing filename differs.
                if organ=='Gut' and isinstance(s.cell(r,2).value,(int,float)):
                    k=str(int(s.cell(r,2).value));mid=k if k in roster else None
                if mid and roster[mid]['experiment']!=exp:issue('SOURCE_EXPERIMENT_MISMATCH',f,sn,f'B{r}',f'{exp} contains {roster[mid]["experiment"]} mouse',mid,'Retain roster experiment; deduplicate exact observations')
                hr,stat=block
                for c in range(3,s.max_column+1):
                    h=text(s.cell(hr,c).value)
                    if not h:continue
                    gate,_,statlabel=h.partition(' | ');den='';hold=''
                    if stat=='Frequency':
                        den=statlabel.replace('Freq. of ','') if statlabel else ''
                        if not den:hold='FREQUENCY_DENOMINATOR_UNSPECIFIED'
                    name='Absolute Count' if stat=='Count' else ('MFI '+statlabel if stat=='MFI' else 'Frequency')
                    if stat=='Count':den='Calculated cells per microlitre (user confirmed 2026-11-10)'
                    add(f,sn,r,c,mid,'Flow cytometry',name,{'Count':'cells/µL','MFI':'a.u.','Frequency':'%'}[stat],organ,panel,gate,den,raw_id=b,hold=hold,header=h)
        s=w['Liver Histology and genes']
        for r in range(9,s.max_row+1):
            raw=s.cell(r,1).value
            if not isinstance(raw,(int,float)):continue
            mid=resolve(raw,exp)
            for c,name in [(3,'PSR'),(4,'HE')]:add(f,s.title,r,c,mid,'Histology',name,'%',organ='Liver',raw_id=raw,header=text(s.cell(8,c).value))
            for c in range(6,s.max_column+1):
                h=text(s.cell(8,c).value)
                if h:add(f,s.title,r,c,mid,'qPCR',h,'fold change',organ='Liver',raw_id=raw,header=h)
        s=w['Neutrophil panels'];organ='';headers={}
        for r in range(1,s.max_row+1):
            title=text(s.cell(r,2).value).lower()
            if 'granulopoiesis panel for' in title:organ='Spleen' if 'spleen' in title else 'Liver';headers={}
            if text(s.cell(r,4).value).startswith('%Neu'):headers={c:text(s.cell(r,c).value) for c in range(4,s.max_column+1) if s.cell(r,c).value};continue
            sample=text(s.cell(r,3).value)
            if not headers or not sample.lower().endswith('.fcs'):continue
            mid=resolve(sample,exp)
            for c,h in headers.items():
                count=h.startswith('#');gate=h.replace('%','').replace('#','').replace(' in singlet','').replace(' insinglet','').replace(' count','').strip()
                add(f,s.title,r,c,mid,'Flow cytometry','Absolute Count' if count else 'Frequency','cells/µL' if count else '%',organ,'Granulopoiesis Panel',gate,'Calculated cells per microlitre (user confirmed 2026-11-10)' if count else 'singlet',raw_id=sample,hold='PANEL_EXCLUSION_ANNOTATIONS_REQUIRE_REVIEW',header=h)
        s=w['Metabolic Biochemical outcomes'];sn=s.title
        weight_headers=[r for r in range(1,s.max_row+1) if text(s.cell(r,2).value)=='ID' and text(s.cell(r,3).value)=='Lab-ID']
        last_date=None
        for hr in weight_headers:
            for c in range(5,s.max_column+1):
                hv=s.cell(hr,c).value;h=text(hv);hold='';timepoint='endpoint';name='';unit='';organ=''
                if isinstance(hv,dt.datetime):
                    name='Body weight';unit='g';timepoint=hv.date().isoformat()
                    if hv.year<2020 or (last_date and hv.date()<=last_date):hold='DATE_ORDER_OR_YEAR_REQUIRES_REVIEW'
                    else:last_date=hv.date()
                elif re.fullmatch(r'\d{1,2}\.\d{1,2}\.?',h):name='Body weight';unit='g';timepoint='source-date:'+h;hold='DATE_YEAR_UNSPECIFIED'
                elif any(x in h.lower() for x in ('liver','bat','scwat','sc wat','gowat')):
                    name='Tissue weight';organ='Liver' if 'liver' in h.lower() else ('BAT' if 'bat' in h.lower() else ('scWAT' if 'sc' in h.lower() else 'goWAT'));unit='g' if '(g)' in h else '';hold='' if unit else 'TISSUE_WEIGHT_UNIT_UNSPECIFIED'
                elif 'weight gain' in h.lower():name='Body weight gain';unit='%' if '%' in h else 'g';hold='DERIVED_ENDPOINT_REQUIRES_REVIEW'
                else:continue
                if hold:issue(hold,f,sn,s.cell(hr,c).coordinate,h)
                for r in range(hr+1,s.max_row+1):
                    alias=text(s.cell(r,2).value)
                    if not alias.startswith('HH1-'):break
                    add(f,sn,r,c,resolve(alias,exp),'Metabolic outcome',name,unit,organ=organ,timepoint=timepoint,raw_id=alias,hold=hold,header=h)
        for hr in range(1,s.max_row+1):
            if text(s.cell(hr,1).value)!='EXP' or text(s.cell(hr,5).value)!='Cholesterin':continue
            started=False
            for r in range(hr+1,s.max_row+1):
                raw=s.cell(r,4).value
                valid=isinstance(raw,(float,int)) and isinstance(s.cell(r,1).value,(float,int))
                if not valid:
                    if started:break
                    continue
                started=True
                for c,name in [(5,'Total Cholesterol'),(6,'Glucose'),(7,'Triglycerides'),(8,'HDL-C'),(9,'LDL-C'),(10,'ALAT'),(11,'ASAT')]:
                    u=text(s.cell(hr+1,c).value);u=u if u in ('mmol/L','uKat/L') else ''
                    add(f,sn,r,c,resolve(raw,exp),'Metabolic outcome',name,u,raw_id=raw,hold='' if u else 'SERUM_UNIT_UNSPECIFIED',header=text(s.cell(hr,c).value))
        test='';cage=None;head=None
        for r in range(12,s.max_row+1):
            vals={c:text(s.cell(r,c).value) for c in range(1,s.max_column+1)}
            if vals[1] in ('ITT','OGTT','oGTT','ipGTT'):test=vals[1];head=None;cage=None;continue
            if not test:continue
            if 'ID' in vals.values() and '0' in vals.values():
                head=r;idc=next(c for c,v in vals.items() if v=='ID');times={c:int(v) for c,v in vals.items() if v in ('0','15','30','60','90','120')};continue
            if not head:continue
            raw=s.cell(r,idc).value
            if raw is None:continue
            # Prefer explicit Pyret anywhere before the glucose columns.
            pyrets=[v for c,v in vals.items() if c<min(times) and v.startswith('HH1-')]
            mid=resolve(pyrets[0],exp) if pyrets else None
            if not pyrets:
                if exp=='Exp2':mid=resolve(raw,exp)
                elif exp in ('Exp3','Exp4') and (isinstance(raw,str) and '/' in raw or exp=='Exp4' and test!='ITT'):
                    n=int(float(text(raw).split('/')[0]));mid=resolve('HH1-'+str(n).zfill(5),exp)
                elif exp=='Exp4':
                    candidates=ear_map[(exp,diet(vals[1]),text(raw))];mid=next(iter(candidates)) if len(candidates)==1 else None
                elif exp in ('Exp6','Exp7'):
                    if isinstance(s.cell(r,1).value,(int,float)):cage=int(s.cell(r,1).value)
                    candidates=cage_map[(exp,cage,text(raw))];mid=next(iter(candidates)) if len(candidates)==1 else None
            for c,minute in times.items():add(f,sn,r,c,mid,'Metabolic outcome',test,'',timepoint=f'{minute} min',raw_id=pyrets[0] if pyrets else raw,hold='GLUCOSE_UNIT_UNSPECIFIED',header=str(minute))
            # Test-day weights are distinct from endpoint and longitudinal weights.
            for c in range(1,min(times)):
                if text(s.cell(head,c).value)=='Bodyweight':add(f,sn,r,c,mid,'Metabolic outcome','Body weight','g',timepoint=test+' test day',raw_id=raw,hold='TEST_DAY_WEIGHT_UNIT_UNSPECIFIED')
    # Exact duplicates merge only at the complete observation identity. Conflicts hold all versions.
    buckets=collections.defaultdict(list)
    for rec in records:
        key=(rec['mouse_id'],rec['metric_id'],rec['timepoint'],rec['replicate'])
        if not rec['mouse_id']:key+= (rec['source_file'],rec['source_sheet'],rec['source_cell'])
        buckets[key].append(rec)
    consolidated=[];duplicates=0
    for key,rs in buckets.items():
        versions=collections.defaultdict(list)
        for rec in rs:versions[(rec['value'],rec['missing_reason'],rec['review_reason'])].append(rec)
        conflict=len({(x['value'],x['missing_reason']) for x in rs})>1
        for ix,vs in enumerate(versions.values()):
            rec=vs[0].copy();rec['record_id']='O'+digest([key,ix]);rec['source_count']=len(vs);duplicates+=len(vs)-1
            if conflict:rec['status']='review';rec['review_reason']+='; CONFLICTING_OBSERVATIONS'
            consolidated.append(rec)
            for source in vs:links.append(dict(record_id=rec['record_id'],source_file=source['source_file'],source_sheet=source['source_sheet'],source_cell=source['source_cell'],raw_value=source['raw_value'],source_formula=source['source_formula'],source_format=source['source_format'],scale_factor=source['scale_factor'],source_header=source['source_header']))
    # Complete cell archive: annotations, formula text and out-of-roster material are retained.
    source_cells=[]
    for f,w in books.items():
        for s in w:
            for row in s:
                for cell in row:
                    if cell.value is None:continue
                    source_cells.append(dict(source_file=f,source_sheet=s.title,cell=cell.coordinate,value=cell.value,cached_value=cached[f][s.title][cell.coordinate].value,number_format=cell.number_format,fill=str(cell.fill.fgColor.index),font_color=str(cell.font.color.index if cell.font.color else ''),extracted_measurement=(f,s.title,cell.coordinate) in used))
    counts=collections.Counter(r['status'] for r in consolidated)
    for reason,n in collections.Counter(reason for r in consolidated for reason in r['review_reason'].split('; ') if reason).items():issue(reason,'','','',f'{n} observations; filter Measurements.review_reason')
    unresolved=collections.defaultdict(list)
    for rec in consolidated:
        if not rec['mouse_id']:unresolved[(rec['source_file'],rec['raw_id'])].append(rec)
    for (f,raw_id),rs in unresolved.items():
        issue('UNRESOLVED_MOUSE_ID',f,rs[0]['source_sheet'],rs[0]['source_cell'],f'Source ID {raw_id}; {len(rs)} observations',action='Provide an explicit mapping to the 183-mouse roster, or confirm out of scope')
    for f,w in books.items():
        if 'Available Material for future' not in w:continue
        exp=f.replace('.xlsx','').replace(' ','')
        wrong=[r[0].value for r in w['Available Material for future'] if isinstance(r[0].value,(int,float)) and str(int(r[0].value)) in roster and roster[str(int(r[0].value))]['experiment']!=exp]
        if wrong:issue('MATERIAL_ROSTER_FROM_OTHER_EXPERIMENT',f,'Available Material for future','',f'{len(wrong)} IDs belong to another experiment in Mouse-info; copied roster suspected')
    summary=dict(roster_count=len(roster),source_files=len(files),source_observations=len(records),consolidated_observations=len(consolidated),exact_duplicates_merged=duplicates,status_counts=dict(counts),metric_count=len(defs),source_cell_count=len(source_cells),review_count=len(reviews),roster_scope='Mouse-info.xlsx only; exactly 183 mice',production_uploaded=False)
    result=dict(summary=summary,mice=list(roster.values()),aliases=alias_rows,metrics=list(defs.values()),measurements=consolidated,provenance=links,review=reviews,sources=[dict(file=p.name,path=str(p.resolve()),sha256=hashes[p.name],bytes=p.stat().st_size) for p in files],source_cells=source_cells)
    for p in files:assert hashlib.sha256(p.read_bytes()).hexdigest()==hashes[p.name], 'Source changed during extraction'
    assert len(records)==len(consolidated)+duplicates
    assert all(not r['mouse_id'] or r['mouse_id'] in roster for r in consolidated)
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,ensure_ascii=False,default=str,allow_nan=False))
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();run(a.source,a.output)
