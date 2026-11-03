"""FlowJo v10 WSP copy with selected-sample gate changes, preserving other XML."""
import copy, hashlib, json, math, sys
from pathlib import Path
from urllib.parse import quote
import numpy as np
from lxml import etree as E
from flowkit._utils.wsp_utils import parse_wsp
from fcs_worker import workspace_metadata

G = 'http://www.isac-net.org/std/Gating-ML/v2.0/gating'
D = 'http://www.isac-net.org/std/Gating-ML/v2.0/datatypes'
T = 'http://www.isac-net.org/std/Gating-ML/v2.0/transformations'
def q(ns, name): return '{'+ns+'}'+name

def population_map(node):
    found = {}
    def walk(parent, path):
        for pop in parent.findall('Subpopulations/Population'):
            key = (pop.get('name'), tuple(path))
            if key in found: raise ValueError('Duplicate population paths cannot be exported safely.')
            found[key] = pop
            walk(pop, path+[pop.get('name')])
    walk(node, ['root'])
    return found

def export_workspace(spec):
    source = Path(spec['wsp_path'])
    metadata = workspace_metadata(source)  # rejects DTD/entities before lxml or FlowKit
    info = spec['result']; name = spec['filename']
    if hashlib.sha256(source.read_bytes()).hexdigest() != info['source_wsp_sha256']:
        raise ValueError('Workspace hash differs from the analyzed original.')
    parser = E.XMLParser(resolve_entities=False, no_network=True, load_dtd=False)
    root = E.fromstring(source.read_bytes(), parser)
    matches = [s for s in root.findall('SampleList/Sample')
               if s.find('SampleNode') is not None and s.find('SampleNode').get('name') == name]
    if len(matches) != 1: raise ValueError('Exactly one matching sample is required.')
    sample = matches[0]; node = sample.find('SampleNode')
    if node.get('sampleID') != info['workspace_sample_id']:
        raise ValueError('Workspace sample identity mismatch.')
    parsed = parse_wsp(str(source))['samples'][name]
    strategy = parsed['gating_strategy']; ids = strategy.get_gate_ids()
    populations = population_map(node)
    originals = [strategy.get_gate(n, p, sample_id=name) for n, p in ids]
    nodes = [populations[(n, tuple(p))] for n, p in ids]
    comp = parsed['compensation']; transforms = parsed['transforms']
    detectors = set(comp['detectors']) if comp else set()
    comp_name = comp['matrix_name'] if comp else None
    # Reconstruct the version-pinned worker axis order without changing old immutable runs.
    axes = []
    for channel in info['channels'][:info['base_channel_count']]:
        dim = channel['name'].replace('/', '_')
        axes.append((dim, (comp_name,) if dim in detectors else (), dim if dim in transforms else None))
    cache = {}
    for gate in originals:
        effective = tuple(sorted({d.compensation_ref for d in gate.dimensions
                                  if d.compensation_ref not in (None, 'uncompensated')}))
        for d in gate.dimensions:
            key = (d.id, effective, d.transformation_ref)
            if key not in cache:
                cache[key] = len(axes); axes.append(key)
    if len(axes) != len(info['channels']): raise ValueError('Unsupported analysis axis layout; reanalyze before export.')
    for descriptor, channel in zip(axes, info['channels']):
        if descriptor[0] != channel['name'].replace('/', '_'):
            raise ValueError('Analysis axis identity mismatch.')
    final = info['gates']
    lineage = [{'node':pop,'parent':ids.index((path[-1],path[:-1])) if len(path)>1 else -1,'changed':False} for pop,(_,path) in zip(nodes,ids)]
    for change in (spec.get('edit_spec') or {}).get('changes', []):
        target = change['target']
        if change.get('operation') == 'delete':
            removed = {target}
            while True:
                more = {i for i,x in enumerate(lineage) if x['parent'] in removed}
                if more <= removed: break
                removed |= more
            for i in removed:
                pop = lineage[i]['node']
                if pop is not None and pop.getparent() is not None: pop.getparent().remove(pop)
            keep = [i for i in range(len(lineage)) if i not in removed]
            mapping = {old:new for new,old in enumerate(keep)}
            lineage = [lineage[i] for i in keep]
            for x in lineage: x['parent'] = mapping.get(x['parent'],-1)
        elif target < 0:
            lineage.append({'node':None,'parent':change['parent_index'],'changed':True})
        else: lineage[target]['changed'] = True
    if len(lineage) != len(final): raise ValueError('Gate edit lineage does not match analysis.')
    nodes = [x['node'] for x in lineage]
    changed = {i for i,x in enumerate(lineage) if x['changed']}
    used_ids = {e.get(q(G, 'id')) for e in root.iter() if e.get(q(G, 'id'))}
    next_id = 2000000000
    for i in range(len(final)):
        if nodes[i] is not None: continue
        gate = final[i]; parent = node if gate['parent_index'] < 0 else nodes[gate['parent_index']]
        sub = parent.find('Subpopulations')
        if sub is None: sub = E.SubElement(parent, 'Subpopulations')
        pop = E.SubElement(sub, 'Population', name=gate['name'], annotation='', owningGroup='', expanded='1')
        while 'ID'+str(next_id) in used_ids: next_id += 1
        wrapper = E.SubElement(pop, 'Gate', {q(G, 'id'): 'ID'+str(next_id)})
        used_ids.add('ID'+str(next_id)); next_id += 1
        nodes[i] = pop

    def inverse(value, ref):
        if value is None: return None
        transform = transforms.get(ref) if ref else None
        raw = float(transform.inverse(np.array([[value]], dtype=float))[0, 0]) if transform else float(value)
        if not math.isfinite(raw): raise ValueError('Gate coordinate cannot be inverted for FlowJo.')
        back = float(transform.apply(np.array([[raw]], dtype=float))[0, 0]) if transform else raw
        if not np.isclose(back, value, rtol=1e-9, atol=1e-8):
            raise ValueError('A gate exceeds the invertible transform range. Adjust its boundary before exporting.')
        return repr(raw)

    for i, gate in enumerate(final):
        pop = nodes[i]
        if i in changed:
            if gate['kind'] not in ('PolygonGate', 'RectangleGate'): raise ValueError('Unsupported edited gate.')
            descriptors = [axes[a] for a in gate['axes']]
            # FlowJo chooses compensation per fluorescence channel; reject mixed/unrepresentable coordinate spaces.
            for dim, effective, ref in descriptors:
                expected = (comp_name,) if dim in detectors else ()
                if dim in detectors and effective != expected:
                    raise ValueError('This gate mixes compensation spaces that cannot be represented in FlowJo.')
                if ref != (dim if dim in transforms else None):
                    raise ValueError('This gate uses a transform not representable by the original WSP.')
            pop.set('name', gate['name']); pop.set('owningGroup', '')
            pop.set('annotation', (pop.get('annotation','')+' | Mouse Sanctuary analysis '+spec['run_id']).strip(' |'))
            wrapper = pop.find('Gate')
            attributes = dict(wrapper[0].attrib) if len(wrapper) else {}
            for child in list(wrapper): wrapper.remove(child)
            for key in (q(G,'id'), q(G,'parent_id'), 'quadID', 'quadId'): attributes.pop(key,None)
            attributes.update(eventsInside='0' if gate.get('complement') else '1', userDefined='1')
            if gate['kind'] == 'PolygonGate': attributes.update(gateResolution='256', quadId='-1')
            else: attributes.update(percentX='0', percentY='0')
            shape = E.SubElement(wrapper, q(G, gate['kind']), attributes)
            parent_index = gate['parent_index']
            if parent_index >= 0: wrapper.set(q(G,'parent_id'), nodes[parent_index].find('Gate').get(q(G,'id')))
            else: wrapper.attrib.pop(q(G,'parent_id'), None)
            labels = []
            for j, (dim, effective, ref) in enumerate(descriptors):
                label = comp['prefix']+dim+comp['suffix'] if dim in detectors else dim
                labels.append(label)
                dimension = E.SubElement(shape, q(G,'dimension'))
                E.SubElement(dimension, q(D,'fcs-dimension'), {q(D,'name'):label})
                if gate['kind'] == 'RectangleGate':
                    for attr, value in zip(('min','max'), gate['bounds'][j]):
                        raw = inverse(value,ref)
                        if raw is not None: dimension.set(q(G,attr),raw)
            if gate['kind'] == 'PolygonGate':
                for vertex in gate['vertices']:
                    element = E.SubElement(shape,q(G,'vertex'))
                    for value, (_,_,ref) in zip(vertex,descriptors):
                        E.SubElement(element,q(G,'coordinate'),{q(D,'value'):inverse(value,ref)})
            graph = pop.find('Graph')
            if graph is None: graph = E.SubElement(pop,'Graph',type='Pseudocolor')
            for axis in list(graph.findall('Axis')): graph.remove(axis)
            for dimension,label in zip(('x','y'), labels):
                E.SubElement(graph,'Axis',dimension=dimension,name=label,label='',auto='auto')
        if gate.get('edited'):
            # Historical FlowJo counts/statistics must not masquerade as recomputed results.
            pop.attrib.pop('count',None)
            pop.set('owningGroup','')
            for statistic in pop.findall('Statistic'): pop.remove(statistic)
    dataset = sample.find('DataSet')
    if dataset is not None: dataset.set('uri',quote(name,safe=''))
    root.attrib.pop('nonAutoSaveFileName',None)
    output = Path(spec['output'])
    output.write_bytes(E.tostring(root,xml_declaration=True,encoding='UTF-8'))
    # Validate export by independently parsing its serialized bytes.
    workspace_metadata(output)
    check = parse_wsp(str(output))['samples'][name]['gating_strategy']
    expected_ids = {(g['name'],tuple(g['path'])) for g in final}
    if set(check.get_gate_ids()) != expected_ids: raise ValueError('Exported gate hierarchy failed round-trip validation.')
    for g in final:
        actual = check.get_gate(g['name'],tuple(g['path']),sample_id=name)
        if type(actual).__name__ != g['kind'] or bool(getattr(actual,'use_complement',False)) != bool(g.get('complement')):
            raise ValueError('Exported gate type/complement failed validation.')
        for d,a,b in zip(actual.dimensions,g['axes'],g['bounds']):
            if d.id != axes[a][0]: raise ValueError('Exported gate axis failed validation.')
            for observed,expected in zip((d.min,d.max),b):
                if observed is None or expected is None:
                    if observed is not expected: raise ValueError('Exported bound failed validation.')
                elif not np.isclose(observed,expected,rtol=1e-9,atol=1e-8):
                    raise ValueError('Exported bound failed validation.')
        if g['kind']=='PolygonGate' and not np.allclose(actual.vertices,g['vertices'],rtol=1e-9,atol=1e-8):
            raise ValueError('Exported polygon failed validation.')
    return {'gates_verified':len(final),'edited_gates':len(changed),'workspace_samples':len(metadata['samples']),
            'selected_sample':name,'validation':'WSP reimport: hierarchy, gate geometry and axis identity',
            'flowjo_application_verified':False}

if __name__ == '__main__':
    spec=json.loads(Path(sys.argv[1]).read_text())
    try:
        report=export_workspace(spec)
        Path(spec['report']).write_text(json.dumps(report))
    except Exception as e:
        Path(spec['report']).write_text(json.dumps({'error':str(e)[:1000]}))
        sys.exit(1)
