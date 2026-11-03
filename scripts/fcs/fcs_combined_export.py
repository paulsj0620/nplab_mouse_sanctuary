"""Multi-sample WSP carrying the combined common gates, with event-mask validation."""
import copy,json,tempfile
from pathlib import Path
from urllib.parse import quote
import numpy as np
from lxml import etree as E
from scripts.fcs.fcs_worker import analyze,workspace_metadata

def export_combined(spec):
 from scripts.fcs.fcs_export import export_workspace,G,q
 sources=spec['combine_sources'];info=spec['result'];first=sources[0]
 if len({s['filename'] for s in sources})!=len(sources):raise ValueError('Combined WSP requires unique original FCS filenames.')
 base=copy.deepcopy(first['result']);base['gates']=copy.deepcopy(info['gates'])
 for g in base['gates']:g['edited']=True
 from flowkit._utils.wsp_utils import parse_wsp
 ids=parse_wsp(first['wsp_path'])['samples'][first['filename']]['gating_strategy'].get_gate_ids()
 roots=sum(tuple(path)==('root',) for _,path in ids)
 changes=[{'operation':'delete','target':0} for _ in range(roots)]+[{'target':-1,'parent_index':g['parent_index']} for g in base['gates']]
 with tempfile.TemporaryDirectory(prefix='combined-wsp-') as tmp:
  tmp=Path(tmp);template=tmp/'template.wsp'
  export_workspace({'wsp_path':first['wsp_path'],'filename':first['filename'],'run_id':spec['run_id'],'result':base,'edit_spec':{'changes':changes},'output':str(template)})
  parser=E.XMLParser(resolve_entities=False,no_network=True,load_dtd=False)
  root=E.parse(str(template),parser).getroot();samples=root.find('SampleList')
  template_sample=next(s for s in samples if s.find('SampleNode').get('name')==first['filename'])
  template_sample=copy.deepcopy(template_sample)
  for s in list(samples):samples.remove(s)
  groups=root.find('Groups')
  if groups is None:groups=E.SubElement(root,'Groups')
  for g in list(groups):groups.remove(g)
  group=E.SubElement(groups,'GroupNode',name='All Samples',owningGroup='All Samples',expanded='1');refs=E.SubElement(group,'SampleRefs')
  for i,source in enumerate(sources,1):
   workspace_metadata(source['wsp_path'])
   source_root=E.parse(source['wsp_path'],parser)
   original=next(s for s in source_root.findall('SampleList/Sample') if s.find('SampleNode').get('name')==source['filename'])
   sample=copy.deepcopy(template_sample);sid=str(i);node=sample.find('SampleNode')
   node.set('name',source['filename']);node.set('sampleID',sid);node.set('count',str(source['result']['events']));node.set('owningGroup','')
   node.set('annotation','Common gates from Mouse Sanctuary combined analysis '+spec['run_id'])
   dataset=sample.find('DataSet');dataset.set('sampleID',sid);dataset.set('uri',quote(source['filename'],safe=''))
   for tag in ['Keywords']:
    old=sample.find(tag)
    if old is not None:sample.remove(old)
    replacement=original.find(tag)
    if replacement is not None:sample.append(copy.deepcopy(replacement))
   ids={p.find('Gate').get(q(G,'id')):'ID'+str(i*100000+j) for j,p in enumerate(node.findall('.//Population'))}
   for gate in node.findall('.//Gate'):
    for attr in ['id','parent_id']:
     old=gate.get(q(G,attr))
     if old in ids:gate.set(q(G,attr),ids[old])
   samples.append(sample);E.SubElement(refs,'SampleRef',sampleID=sid)
  output=Path(spec['output']);output.write_bytes(E.tostring(root,xml_declaration=True,encoding='UTF-8'))
  masks=np.load(Path(spec['artifact_dir'])/'masks.npy',mmap_mode='r',allow_pickle=False)
  offset=0;verified=[]
  for source in sources:
   folder=tmp/('verify-'+str(len(verified)))
   result=analyze({'fcs_path':source['fcs_path'],'filename':source['filename'],'wsp_path':str(output),'fcs_sha256':source['result']['source_fcs_sha256'],'wsp_sha256':None,'out':str(folder)})
   actual=np.load(folder/'masks.npy',mmap_mode='r',allow_pickle=False);lookup={(g['name'],tuple(g['path'])):i for i,g in enumerate(result['gates'])};n=source['result']['events']
   if len(lookup)!=len(info['gates']):raise ValueError('Combined WSP gate hierarchy mismatch.')
   for j,g in enumerate(info['gates']):
    k=lookup.get((g['name'],tuple(g['path'])))
    if k is None or not np.array_equal(actual[k],masks[j,offset:offset+n]):raise ValueError('Combined WSP event membership differs for '+source['filename']+' / '+g['name'])
   offset+=n;verified.append(source['filename'])
 return {'gates_verified':len(info['gates']),'workspace_samples':len(sources),'selected_sample':info['combined_name'],'samples_verified':verified,'validation':'Every source FCS reanalyzed: all common gate event memberships match combined analysis','flowjo_application_verified':False,'combined':True}
