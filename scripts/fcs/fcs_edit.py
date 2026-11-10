"""Versioned gate edits in the immutable analysis's exact transformed coordinates."""
import copy, math

def validate_edit(change,result):
 if not isinstance(change,dict):raise ValueError('Provide a gate change.')
 g=copy.deepcopy(change);gates=result['gates'];target=g.get('target',-1)
 if type(target) is not int or target not in range(-1,len(gates)):raise ValueError('Invalid target gate.')
 if g.get('operation')=='delete':
  if target<0:raise ValueError('Select a gate to delete.')
  return {'operation':'delete','target':target}
 if g.get('operation') not in (None,'edit'):raise ValueError('Unknown gate operation.')
 parent=gates[target]['parent_index'] if target>=0 else g.get('parent_index',-1)
 if type(parent) is not int or parent not in range(-1,len(gates)):raise ValueError('Invalid parent gate.')
 name=g.get('name','').strip()
 if not name or len(name)>100 or '/' in name:raise ValueError('Use a gate name of 1–100 characters without /.')
 if any(i!=target and x['parent_index']==parent and x['name']==name for i,x in enumerate(gates)):raise ValueError('A sibling gate already has this name.')
 axes=g.get('axes');kind=g.get('kind')
 if kind not in ('RectangleGate','PolygonGate'):raise ValueError('Only rectangle and polygon editing is supported.')
 if not isinstance(axes,list) or len(axes)!=2 or len(set(axes))!=2 or any(type(a) is not int or a not in range(len(result['channels'])) for a in axes):raise ValueError('Select two distinct valid axes.')
 def num(x):return type(x) in (float,int) and math.isfinite(x) and abs(x)<1e15
 bounds=g.get('bounds');vertices=g.get('vertices')
 if kind=='RectangleGate':
  if not isinstance(bounds,list) or len(bounds)!=2 or any(not isinstance(b,list) or len(b)!=2 or not all(num(v) for v in b) or b[0]>=b[1] for b in bounds):raise ValueError('Draw a rectangle with positive width and height.')
  vertices=None
 else:
  if not isinstance(vertices,list) or not 3<=len(vertices)<=128 or any(not isinstance(v,list) or len(v)!=2 or not all(num(n) for n in v) for v in vertices):raise ValueError('A polygon needs 3–128 valid vertices.')
  area=sum(vertices[i][0]*vertices[(i+1)%len(vertices)][1]-vertices[(i+1)%len(vertices)][0]*vertices[i][1] for i in range(len(vertices)))
  if abs(area)<1e-12:raise ValueError('Polygon area must be nonzero.')
  def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
  for i,a in enumerate(vertices):
   b=vertices[(i+1)%len(vertices)]
   if a==b:raise ValueError('Remove duplicate polygon vertices.')
   for j in range(i+1,len(vertices)):
    if j==i+1 or (i==0 and j==len(vertices)-1):continue
    c,d=vertices[j],vertices[(j+1)%len(vertices)]
    if max(min(a[0],b[0]),min(c[0],d[0]))<=min(max(a[0],b[0]),max(c[0],d[0])) and max(min(a[1],b[1]),min(c[1],d[1]))<=min(max(a[1],b[1]),max(c[1],d[1])) and cross(a,b,c)*cross(a,b,d)<=0 and cross(c,d,a)*cross(c,d,b)<=0:raise ValueError('Polygon edges must not cross or touch each other.')
  bounds=[[None,None],[None,None]]
 if target<0 and (len(gates)>=1000 or (len(gates)+1)*result['events']>100000000):raise ValueError('Gate/event preview limit reached.')
 return {'target':target,'parent_index':parent,'name':name,'kind':kind,'axes':axes,'bounds':bounds,'vertices':vertices,'complement':bool(gates[target].get('complement')) if target>=0 else False}

def apply_edits(gates,events,masks,changes,channels):
 import numpy as np
 from flowutils import gating
 gates=copy.deepcopy(gates);masks=[m.copy() for m in masks]
 for change in changes:
  g=validate_edit(change,{'gates':gates,'channels':channels,'events':len(events)})
  if g.get('operation')=='delete':
   removed={g['target']}
   while True:
    more={i for i,x in enumerate(gates) if x['parent_index'] in removed}
    if more<=removed:break
    removed|=more
   keep=[i for i in range(len(gates)) if i not in removed];mapping={old:new for new,old in enumerate(keep)}
   gates=[gates[i] for i in keep];masks=[masks[i] for i in keep]
   for i,x in enumerate(gates):x.update(index=i,parent_index=mapping.get(x['parent_index'],-1))
   continue
  idx=g.pop('target');idx=len(gates) if idx<0 else idx;g['index']=idx
  if idx==len(gates):gates.append(g);masks.append(np.zeros(len(events),bool))
  else:gates[idx].update(g)
  affected={idx}
  while True:
   more={i for i,x in enumerate(gates) if x['parent_index'] in affected}
   if more<=affected:break
   affected|=more
  done=set()
  def evaluate(i):
   if i in done:return
   gate=gates[i];pi=gate['parent_index']
   if pi in affected:evaluate(pi)
   gate['path']=['root'] if pi<0 else gates[pi]['path']+[gates[pi]['name']]
   arr=events[:,gate['axes']]
   if gate['kind']=='PolygonGate':own=gating.points_in_polygon(np.asarray(gate['vertices'],dtype=float),arr)
   else:
    own=np.ones(len(events),bool)
    for j,(lo,hi) in enumerate(gate['bounds']):
     if lo is not None:own &= arr[:,j]>=lo
     if hi is not None:own &= arr[:,j]<hi
   if gate.get('complement'):own=~own
   masks[i]=own if pi<0 else own & masks[pi]
   pc=len(events) if pi<0 else int(masks[pi].sum());count=int(masks[i].sum())
   gate.update(count=count,parent_count=pc,frequency_parent=100*count/pc if pc else None,flowjo_count=None,difference=None,edited=True)
   done.add(i)
  for i in sorted(affected):evaluate(i)
 return gates,np.asarray(masks,dtype=bool).reshape((len(gates),len(events)))
