"""Normalize the two side-by-side mouse histology tables; retain source rows/cells."""
def normalize(rows,sheets,sheet,Problem):
    h=rows[0] if rows else []
    if len(h)!=14 or [h[i] for i in (1,2,4,5,9,10,12,13)]!=['Mouse number','weeks, diet','PSR','HE']*2:return None
    data=[];sources=[];cells=[];seen=set()
    for offset in (0,8):
        exp=''
        for n,row in enumerate(rows[1:],2):
            row=list(row)+[None]*max(0,14-len(row))
            if row[offset] is not None:exp=str(row[offset]).strip()
            mid=row[offset+1]
            if mid is None:
                if any(row[offset+i] is not None for i in (4,5)):raise Problem(f'Row {n}: measurement has no mouse ID.')
                continue
            if not isinstance(mid,(int,float)) or isinstance(mid,bool) or int(mid)!=mid:raise Problem(f'Row {n}: check the mouse ID.')
            mid=str(int(mid))
            if mid in seen:raise Problem(f'Duplicate mouse {mid}.')
            seen.add(mid)
            vals=[mid,exp,row[offset+2],row[offset+3],row[offset+4],row[offset+5]]
            data.append(['' if v is None else str(v).strip() for v in vals]);sources.append(n)
            cells.append({'mouse_id':mid,'row':n,'PSR':('E' if offset==0 else 'M')+str(n),'HE':('F' if offset==0 else 'N')+str(n)})
    return {'headers':['Mouse number','Experiment','weeks, diet','Note','PSR','HE'],'rows':data,'source_rows':sources,'sheets':sheets,'sheet':sheet,'histology_source_cells':cells}
