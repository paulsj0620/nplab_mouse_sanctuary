import copy,json,tempfile,unittest
from pathlib import Path
import numpy as np
from scripts.fcs.fcs_combine import combine
class CombineTests(unittest.TestCase):
 def test_pool_common_gates_edit_and_source_counts(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);sources=[]
   for i,points in enumerate([[[0,0],[1,1]],[[2,2],[3,3],[4,4]]]):
    folder=root/str(i);folder.mkdir();np.save(folder/'events.npy',np.asarray(points,float))
    info={'events':len(points),'channels':[{'name':'x'},{'name':'y'}],'base_channel_count':2,'space':'raw','source_fcs_sha256':str(i),'gates':[dict(index=0,name='Common',parent_index=-1,path=['root'],kind='RectangleGate',axes=[0,1],bounds=[[0,3],[0,3]],vertices=None,complement=False)]}
    sources.append(dict(result=info,folder=str(folder),filename=str(i)+'.fcs',run_id=str(i),fcs_id=str(i)))
   spec=dict(out=str(root/'out'),combine_sources=sources,edit_spec={'combine_name':'Test','changes':[]})
   info=combine(spec);self.assertEqual(info['events'],5);self.assertEqual(info['gates'][0]['count'],3);self.assertEqual([s['count'] for s in info['gates'][0]['source_counts']],[2,1]);self.assertEqual(info['sources'][1]['start'],2)
   self.assertEqual(np.load(root/'0'/'events.npy').tolist(),[[0,0],[1,1]])
   spec['edit_spec']['changes']=[{'operation':'delete','target':0}];spec['out']=str(root/'deleted');self.assertEqual(combine(spec)['gates'],[])
   sources[1]['result']['channels'][0]['name']='different'
   with self.assertRaisesRegex(ValueError,'Cannot combine'):combine(spec)
