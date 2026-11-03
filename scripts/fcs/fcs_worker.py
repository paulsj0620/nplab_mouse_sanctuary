"""Isolated FlowKit worker. Original FCS/WSP files are read-only inputs."""
import json,os,sys,traceback,warnings
from pathlib import Path
import xml.etree.ElementTree as ET

def workspace_metadata(path):
 raw=Path(path).read_bytes()
 markup=raw.replace(b'\x00',b'').upper()
 if b'<!DOCTYPE' in markup or b'<!ENTITY' in markup:raise ValueError('WSP external entities and document types are not supported.')
 root=ET.fromstring(raw)
 if root.tag.split('}')[-1]!='Workspace':raise ValueError('Not a FlowJo workspace.')
 samples=[]
 for s in root.iter('Sample'):
  node=s.find('SampleNode')
  if node is None:continue
  gates=[]
  def walk(parent,path):
   sub=parent.find('Subpopulations')
   if sub is None:return
   for pop in sub.findall('Population'):
    name=pop.get('name');gates.append({'name':name,'path':list(path),'count':int(pop.get('count')) if pop.get('count') is not None else None})
    walk(pop,path+[name])
  walk(node,['root'])
  samples.append({'name':node.get('name'),'sample_id':node.get('sampleID'),'events':int(node.get('count','0')),'gates':gates})
 if not samples:raise ValueError('The WSP file contains no sample definitions.')
 return {'flowjo_version':root.get('flowJoVersion'),'samples':samples}

def analyze(spec):
 if spec.get('combine_sources'):
  from scripts.fcs.fcs_combine import combine
  return combine(spec)
 import flowkit as fk
 import numpy as np
 warnings.filterwarnings('ignore',message='.*was not found.*')
 out=Path(spec['out']);out.mkdir(parents=True,exist_ok=True)
 import flowio
 with open(spec['fcs_path'],'rb') as f:header=f.read(58)
 text_start,text_end=int(header[10:18]),int(header[18:26])
 if not 58<=text_start<=text_end<Path(spec['fcs_path']).stat().st_size or text_end-text_start>16*1024**2:raise ValueError('Unsupported FCS metadata segment size or offsets.')
 metadata=flowio.FlowData(spec['fcs_path'],only_text=True)
 if metadata.event_count>2000000 or metadata.event_count*metadata.channel_count>50000000:raise ValueError('Analysis preview limit: 2 million events and 50 million channel values. The uploaded original remains preserved.')
 sample=fk.Sample(spec['fcs_path'],sample_id=spec['filename'])
 if sample.event_count>2000000 or sample.event_count*len(sample.pnn_labels)>50000000:raise ValueError('This preview supports up to 2 million events and 50 million values per sample. Original is preserved.')
 original=list(sample.pnn_labels);markers=list(sample.pns_labels);notes=[];gates=[];maskrows=[];w=None
 meta=sample.get_metadata();workspace=None
 if spec.get('wsp_path'):
  workspace=workspace_metadata(spec['wsp_path'])
  matches=[s for s in workspace['samples'] if s['name']==spec['filename']]
  if len(matches)!=1:raise ValueError('The FCS filename must match exactly one WSP SampleNode name. No automatic mouse-ID matching was attempted.')
  reference=matches[0]
  if reference['events']!=sample.event_count:raise ValueError('FCS event count differs from the matching WSP sample. Verify that these are the same acquisition.')
  normalized=[n.replace('/','_') for n in original]
  if len(set(normalized))!=len(normalized):raise ValueError('Ambiguous FlowJo channel aliases after slash normalization.')
  for name,alias in zip(original,normalized):
   if name!=alias:sample.rename_channel(name,alias)
  notes.append('FlowJo channel aliases (/ → _) are applied in memory only; original labels and bytes are retained.')
  with warnings.catch_warnings():
   warnings.simplefilter('ignore');w=fk.Workspace(spec['wsp_path'],fcs_samples=[sample],find_fcs_files_from_wsp=False)
  if w.get_sample_ids()!=[sample.id]:raise ValueError('Could not uniquely link the FCS sample to the workspace.')
  w.analyze_samples(sample_id=sample.id,use_mp=False,cache_events=False)
  base=w.get_gate_events(sample.id,source='xform').iloc[:,1:].to_numpy(dtype='float64')
  transforms=w.get_transforms(sample.id)
  space='WSP compensation + WSP channel transforms (transformed axis coordinates)'
  notes.append('WSP compensation is applied to acquisition events. FCS metadata alone does not establish whether an exported file is already compensated; do not use precompensated exports without review.')
 else:
  base=sample.get_events(source='raw');transforms={};space='Acquisition channels (FCS gain/time preprocessing; no compensation or display transform)'
  notes.append('No WSP selected: no compensation or biexponential transform is applied. FCS gain/time preprocessing is applied by the reader.')
 columns=[base[:,i] for i in range(len(original))]
 channels=[{'name':name,'marker':markers[i],'label':f'{markers[i]} · {name}' if markers[i] else name,'transform':type(transforms.get(sample.pnn_labels[i])).__name__ if sample.pnn_labels[i] in transforms else 'None'} for i,name in enumerate(original)]
 if w:
  strategy=w.get_gating_strategy(sample.id);ids=w.get_gate_ids(sample.id)
  if len(ids)*sample.event_count>100000000:raise ValueError('This gate/event combination exceeds the preview memory limit. Original files remain preserved.')
  if len(ids)>1000:raise ValueError('More than 1,000 gates are not supported in this preview.')
  lookup={(name,tuple(path)):i for i,(name,path) in enumerate(ids)}
  refs={(g['name'],tuple(g['path'])):g['count'] for g in reference['gates']};axis_cache={}
  for index,(name,path) in enumerate(ids):
   gate=w.get_gate(sample.id,name,path)
   if type(gate).__name__ not in ('PolygonGate','RectangleGate'):raise ValueError('Unsupported gate type: '+type(gate).__name__+'. Original workspace is preserved.')
   if len(gate.dimensions) not in (1,2):raise ValueError('Only 1D/2D gates are supported in this preview.')
   # Version-pinned adapter: same preprocessing as FlowKit membership evaluation.
   # This avoids drawing a gate over a differently transformed or compensated channel.
   effective_comp=tuple(sorted({d.compensation_ref for d in gate.dimensions if d.compensation_ref not in (None,'uncompensated')}))
   keys=[(d.id,effective_comp,d.transformation_ref) for d in gate.dimensions]
   prepared=None;axes=[]
   for dim,key in zip(gate.dimensions,keys):
    if key not in axis_cache:
     if prepared is None:prepared=strategy._preprocess_sample_events(sample,gate,cache_events=False)
     col=prepared[dim.id].to_numpy(dtype='float64');axis_cache[key]=len(columns);columns.append(col)
     try:ci=sample.get_channel_index(dim.id);label=channels[ci]['label']
     except Exception:label=dim.id
     channels.append({'name':dim.id,'marker':'','label':label+' [gate coordinates]','transform':dim.transformation_ref or 'None'})
    axes.append(axis_cache[key])
   mask=w.get_gate_membership(sample.id,name,path);maskrows.append(mask)
   parent_index=lookup.get((path[-1],tuple(path[:-1])),-1) if path!=('root',) else -1
   parent_count=sample.event_count if parent_index<0 else int(w.get_gate_membership(sample.id,path[-1],path[:-1]).sum())
   count=int(mask.sum());saved=refs.get((name,tuple(path)))
   gates.append({'index':index,'name':name,'path':list(path),'parent_index':parent_index,'kind':type(gate).__name__,'axes':axes,'bounds':[[d.min,d.max] for d in gate.dimensions],'vertices':getattr(gate,'vertices',None),'complement':getattr(gate,'use_complement',False),'count':count,'parent_count':parent_count,'frequency_parent':100*count/parent_count if parent_count else None,'flowjo_count':saved,'difference':count-saved if saved is not None else None})
  notes.append('WSP stored counts are historical reference values, not newly computed results. Differences require review; existing summary measurements are never overwritten.')
 if len(columns)*sample.event_count>60000000:raise ValueError('Too many plot coordinates for this preview. Original files remain preserved.')
 events=np.column_stack(columns)
 np.save(out/'events.npy',events,allow_pickle=False)
 masks=np.asarray(maskrows,dtype=bool) if maskrows else np.empty((0,sample.event_count),dtype=bool)
 if spec.get('edit_spec'):
  from scripts.fcs.fcs_edit import apply_edits
  gates,masks=apply_edits(gates,events,masks,spec['edit_spec']['changes'],channels)
  notes.append('QA gate edits: changed gates and descendants are recalculated on all events. Their historical FlowJo comparisons are cleared. Original FCS/WSP and prior analyses are unchanged.')
 np.save(out/'masks.npy',masks,allow_pickle=False)
 result={'schema':1,'engine':'FlowKit '+fk.__version__,'events':sample.event_count,'base_channel_count':len(original),'channels':channels,'gates':gates,'space':space,'notes':notes,'source_fcs_sha256':spec['fcs_sha256'],'source_wsp_sha256':spec.get('wsp_sha256'),'workspace_sample_id':reference['sample_id'] if w else None,'workspace_sample_count':len(workspace['samples']) if w else 0,'flowjo_version':workspace['flowjo_version'] if w else None,'different_gate_counts':sum(g['difference'] not in (None,0) for g in gates),'display_sample_limit':20000,'sample_seed':20261103}
 result['gate_edit']=spec.get('edit_spec')
 for file in [out/'events.npy',out/'masks.npy']:
  with open(file,'rb') as f:os.fsync(f.fileno())
 with open(out/'result.json','w') as f:json.dump(result,f,ensure_ascii=False,allow_nan=False);f.flush();os.fsync(f.fileno())
 return result
if __name__=='__main__':
 spec=json.loads(Path(sys.argv[1]).read_text())
 try:analyze(spec)
 except Exception as e:
  Path(spec['out'],'error.json').write_text(json.dumps({'error':str(e)[:1500]}));traceback.print_exc();sys.exit(1)
