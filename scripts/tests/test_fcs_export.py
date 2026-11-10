import copy, hashlib, json, tempfile, unittest
from pathlib import Path
from lxml import etree as E
from scripts.fcs.fcs_export import export_workspace, G, D, T, q
from flowkit._utils.wsp_utils import parse_wsp

class ExportTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  root=E.Element('Workspace',version='20.0',flowJoVersion='10.10.0',nsmap={'gating':G,'data-type':D,'transforms':T})
  E.SubElement(root,'Groups');samples=E.SubElement(root,'SampleList')
  sample=E.SubElement(samples,'Sample')
  E.SubElement(sample,'DataSet',sampleID='1',uri='file:/old/sample.fcs')
  transforms=E.SubElement(sample,'Transformations')
  for label in ['FSC-A','SSC-A']:
   transform=E.SubElement(transforms,q(T,'linear'),{q(T,'minRange'):'0',q(T,'maxRange'):'100','gain':'1'})
   E.SubElement(transform,q(D,'parameter'),{q(D,'name'):label})
  E.SubElement(sample,'Keywords')
  node=E.SubElement(sample,'SampleNode',name='sample.fcs',sampleID='1',count='100',owningGroup='')
  sub=E.SubElement(node,'Subpopulations');pop=E.SubElement(sub,'Population',name='Parent',owningGroup='',count='90')
  wrapper=E.SubElement(pop,'Gate',{q(G,'id'):'ID1'});shape=E.SubElement(wrapper,q(G,'RectangleGate'),eventsInside='1')
  for label in ['FSC-A','SSC-A']:
   dimension=E.SubElement(shape,q(G,'dimension'),{q(G,'min'):'10',q(G,'max'):'90'})
   E.SubElement(dimension,q(D,'fcs-dimension'),{q(D,'name'):label})
  self.source=self.root/'original.wsp';self.source.write_bytes(E.tostring(root))
  channels=[{'name':label,'transform':'LinearTransform'} for label in ['FSC-A','SSC-A']]*2
  gate=dict(index=0,name='Parent',parent_index=-1,path=['root'],kind='RectangleGate',axes=[2,3],bounds=[[.1,.9],[.1,.9]],vertices=None,complement=False)
  self.result={'source_wsp_sha256':hashlib.sha256(self.source.read_bytes()).hexdigest(),'workspace_sample_id':'1','base_channel_count':2,'channels':channels,'gates':[gate]}
 def tearDown(self):self.tmp.cleanup()
 def export(self,result,changes):
  dst=self.root/'export.wsp'
  report=export_workspace({'wsp_path':str(self.source),'filename':'sample.fcs','run_id':'test','result':result,'edit_spec':{'changes':changes},'output':str(dst)})
  return report,E.parse(str(dst)),parse_wsp(str(dst))['samples']['sample.fcs']['gating_strategy']
 def test_rename_move_and_new_child_preserve_transform(self):
  result=copy.deepcopy(self.result);g=result['gates'][0];g.update(name='Renamed',bounds=[[.2,.6],[.3,.7]],edited=True)
  child=dict(index=1,name='Child',parent_index=0,path=['root','Renamed'],kind='PolygonGate',axes=[0,1],bounds=[[None,None],[None,None]],vertices=[[.3,.4],[.5,.4],[.4,.6]],complement=False,edited=True)
  result['gates'].append(child)
  report,doc,strategy=self.export(result,[{'target':0},{'target':-1,'parent_index':0}])
  self.assertEqual(report['gates_verified'],2)
  self.assertEqual(strategy.get_gate('Renamed',('root',),sample_id='sample.fcs').dimensions[0].min,.2)
  self.assertEqual(E.tostring(doc.find('.//Transformations')),E.tostring(E.parse(str(self.source)).find('.//Transformations')))
  self.assertIsNone(doc.find('.//Population').get('count'))
  self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(),self.result['source_wsp_sha256'])
 def test_wrong_hash_and_axis_layout_fail_closed(self):
  result=copy.deepcopy(self.result);result['source_wsp_sha256']='wrong'
  with self.assertRaises(ValueError):self.export(result,[])
  result=copy.deepcopy(self.result);result['channels']=result['channels'][:2]
  with self.assertRaises(ValueError):self.export(result,[])
 def test_unedited_geometry_kept_verbatim(self):
  _,doc,_=self.export(self.result,[])
  self.assertEqual(E.tostring(doc.find('.//Gate')),E.tostring(E.parse(str(self.source)).find('.//Gate')))

 def test_delete_original_then_add_new(self):
  result=copy.deepcopy(self.result)
  result['gates'][0].update(name='Replacement',edited=True)
  report,doc,strategy=self.export(result,[{'operation':'delete','target':0},{'target':-1,'parent_index':-1}])
  self.assertEqual(report['gates_verified'],1)
  self.assertEqual([p.get('name') for p in doc.findall('.//Population')],['Replacement'])
 def test_delete_all(self):
  result=copy.deepcopy(self.result);result['gates']=[]
  report,doc,strategy=self.export(result,[{'operation':'delete','target':0}])
  self.assertEqual(report['gates_verified'],0)
  self.assertEqual(doc.findall('.//Population'),[])
