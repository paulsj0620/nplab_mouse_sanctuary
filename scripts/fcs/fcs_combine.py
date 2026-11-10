"""Combine immutable analysis coordinates; originals are never rewritten."""
import copy,json,os
from pathlib import Path
import numpy as np

def signature(source):
 info=source['result']
 identity={'channels':info['channels'],'base':info['base_channel_count'],'space':info['space']}
 if source.get('wsp_path'):
  from flowkit._utils.wsp_utils import parse_wsp
  p=parse_wsp(source['wsp_path'])['samples'][source['filename']]
  comp=p['compensation']
  identity['compensation']=None if comp is None else {'detectors':comp['detectors'],'matrix':comp['matrix_array'].tolist()}
  identity['transforms']={k:{'type':type(t).__name__,**{a:v for a,v in vars(t).items() if not a.startswith('_') and isinstance(v,(str,int,float,bool))}} for k,t in p['transforms'].items()}
  # Acquisition duration varies by sample; Time is normalized into template coordinates below.
  if 'Time' in identity['transforms']:identity['transforms']['Time']={'type':identity['transforms']['Time']['type']}
  strategy=p['gating_strategy'];keys=[]
  for name,path in strategy.get_gate_ids():
   gate=strategy.get_gate(name,path,sample_id=source['filename'])
   effective=tuple(sorted({d.compensation_ref for d in gate.dimensions if d.compensation_ref not in (None,'uncompensated')}))
   for d in gate.dimensions:
    key=(d.id,effective,d.transformation_ref)
    if key not in keys:keys.append(key)
  identity['gate_axes']=keys
 return json.dumps(identity,sort_keys=True,default=lambda x:x.tolist() if hasattr(x,'tolist') else float(x))

def combine(spec):
 from flowutils import gating
 from scripts.fcs.fcs_edit import apply_edits
 sources=spec['combine_sources'];out=Path(spec['out']);out.mkdir(parents=True,exist_ok=True)
 first=sources[0];info=copy.deepcopy(first['result']);expected=signature(first)
 for source in sources[1:]:
  if signature(source)!=expected:raise ValueError('Cannot combine: channel order, compensation or transform settings differ. Use analyses with matching settings.')
 total=sum(s['result']['events'] for s in sources);width=len(info['channels'])
 if total>2000000 or total*width>60000000 or total*len(info['gates'])>100000000:raise ValueError('Combined preview limit exceeded: 2 million events, 60 million coordinates or 100 million gate memberships.')
 events=np.lib.format.open_memmap(out/'events.npy',mode='w+',dtype='float64',shape=(total,width));offset=0;provenance=[]
 for source in sources:
  arr=np.load(Path(source['folder'])/'events.npy',mmap_mode='r',allow_pickle=False);n=source['result']['events']
  if arr.shape!=(n,width):raise ValueError('Source analysis coordinates do not match metadata.')
  events[offset:offset+n]=arr
  if source is not first and source.get('wsp_path'):
   from flowkit._utils.wsp_utils import parse_wsp
   source_t=parse_wsp(source['wsp_path'])['samples'][source['filename']]['transforms'].get('Time')
   template_t=parse_wsp(first['wsp_path'])['samples'][first['filename']]['transforms'].get('Time')
   if source_t is not None and template_t is not None:
    for j,ch in enumerate(info['channels']):
     if ch['name']=='Time' and (j<info['base_channel_count'] or ch.get('transform')=='Time'):
      values=np.asarray(arr[:,j]).reshape(-1,1)
      converted=template_t.apply(source_t.inverse(values))
      if not np.all(np.isfinite(converted)):raise ValueError('Time normalization produced invalid coordinates.')
      events[offset:offset+n,j]=converted.ravel()
  provenance.append({'run_id':source['run_id'],'fcs_id':source['fcs_id'],'filename':source['filename'],'sha256':source['result']['source_fcs_sha256'],'start':offset,'stop':offset+n,'events':n})
  offset+=n
 events.flush();gates=info['gates'];masks=np.zeros((len(gates),total),dtype=bool);done=set()
 def evaluate(i):
  if i in done:return
  g=gates[i];parent=g['parent_index']
  if parent>=0:evaluate(parent)
  arr=events[:,g['axes']]
  if g['kind']=='PolygonGate':own=gating.points_in_polygon(np.asarray(g['vertices'],float),arr)
  elif g['kind']=='RectangleGate':
   own=np.ones(total,bool)
   for j,(lo,hi) in enumerate(g['bounds']):
    if lo is not None:own &= arr[:,j]>=lo
    if hi is not None:own &= arr[:,j]<hi
  else:raise ValueError('Unsupported common gate type.')
  if g.get('complement'):own=~own
  masks[i]=own if parent<0 else own&masks[parent]
  pc=total if parent<0 else int(masks[parent].sum());n=int(masks[i].sum())
  g.update(count=n,parent_count=pc,frequency_parent=100*n/pc if pc else None,flowjo_count=None,difference=None)
  done.add(i)
 for i in range(len(gates)):evaluate(i)
 gates,masks=apply_edits(gates,events,masks,spec['edit_spec'].get('changes',[]),info['channels'])
 for i,g in enumerate(gates):g['source_counts']=[{'run_id':p['run_id'],'filename':p['filename'],'count':int(masks[i,p['start']:p['stop']].sum())} for p in provenance]
 np.save(out/'masks.npy',masks,allow_pickle=False)
 info.update(events=total,gates=gates,combined=True,combined_name=spec['edit_spec']['combine_name'],sources=provenance,template_run=first['run_id'],source_fcs_sha256=None,source_wsp_sha256=None,workspace_sample_id=None,different_gate_counts=0,gate_edit=spec['edit_spec'])
 info.pop('artifact_dir',None)
 info['notes']=['Combined events from '+str(len(sources))+' immutable analyses. Common gates are copied from the first selected template and recalculated for every event.','Time coordinates are normalized to the template acquisition scale; fluorescence compensation and transforms must match.','Original FCS/WSP files are unchanged. Source event numbers are retained via source ranges. Pooled counts are not independent mouse replicates.','WSP export applies the common gates to each original FCS sample; original files must be downloaded or reconnected.']
 for name in ['events.npy','masks.npy']:
  with open(out/name,'rb') as f:os.fsync(f.fileno())
 with open(out/'result.json','w') as f:json.dump(info,f,ensure_ascii=False,allow_nan=False);f.flush();os.fsync(f.fileno())
 return info
