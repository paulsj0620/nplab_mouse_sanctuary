import unittest,numpy as np
from fcs_edit import validate_edit,apply_edits
class GateTests(unittest.TestCase):
 def test_parent_changes_propagate_and_originals_survive(self):
  events=np.array([[0,0],[1,1],[2,2],[3,3],[4,4]],float);channels=[{},{}]
  gates=[dict(index=0,name='P',parent_index=-1,path=['root'],kind='RectangleGate',axes=[0,1],bounds=[[0,4],[0,4]],vertices=None,complement=False,flowjo_count=4),dict(index=1,name='C',parent_index=0,path=['root','P'],kind='RectangleGate',axes=[0,1],bounds=[[1,4],[1,4]],vertices=None,complement=False,flowjo_count=3)]
  masks=np.array([[1,1,1,1,0],[0,1,1,1,0]],bool)
  edit=dict(target=0,name='Changed',kind='RectangleGate',axes=[0,1],bounds=[[0,2],[0,2]])
  g,m=apply_edits(gates,events,masks,[edit],channels)
  self.assertEqual([x['count'] for x in g],[2,1]);self.assertEqual(g[1]['path'],['root','Changed']);self.assertIsNone(g[1]['flowjo_count']);self.assertEqual(gates[0]['name'],'P');self.assertEqual(int(masks[0].sum()),4)
  new=dict(target=-1,parent_index=0,name='Poly',kind='PolygonGate',axes=[0,1],vertices=[[-.5,-.5],[1.5,-.5],[1.5,1.5],[-.5,1.5]])
  g2,m2=apply_edits(gates,events,masks,[edit,new],channels);self.assertEqual(g2[2]['count'],2);self.assertEqual(g2[2]['parent_count'],2)
 def test_invalid_shapes(self):
  r={'events':5,'channels':[{},{}],'gates':[]}
  for bounds in ([[0,0],[1,2]],[[0,float('nan')],[1,2]]):
   with self.assertRaises(ValueError):validate_edit(dict(name='A',kind='RectangleGate',axes=[0,1],bounds=bounds),r)
  with self.assertRaises(ValueError):validate_edit(dict(name='A',kind='PolygonGate',axes=[0,1],vertices=[[0,0],[1,1],[2,2]]),r)
