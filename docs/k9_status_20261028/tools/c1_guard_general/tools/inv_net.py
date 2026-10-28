# -*- coding: utf-8 -*-
"""inv_net.py (guard/general, 2026-10-27 KST) — read-only facts from the v3c3 .inpx.

Usage: python -B inv_net.py <inpx> <out.json>
Writes only <out.json>. No VISSIM, no COM.
Collects: links/connectors (3D polyline length = codex route_choice_corridor._length), lanes, from/to ends,
link behaviour type, signal heads, signal controllers, vehicle inputs, static routing decisions (+ link
sequences), queue counters, data collection points, driving behaviours (standstill parameters),
2D/3D model lengths, vehicle compositions, conflict areas (link pairs only).
"""
import hashlib
import json
import math
import os
import sys
import xml.etree.ElementTree as ET


def plen(node):
    pts = [tuple(float(p.get(k, 0)) for k in ('x', 'y', 'zOffset'))
           for p in node.findall('./geometry/linkPolyPts/linkPolyPoint')]
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def main():
    inpx, out = sys.argv[1], sys.argv[2]
    raw = open(inpx, 'rb').read()
    root = ET.fromstring(raw)
    res = {'tool': 'inv_net.py', 'inpx_sha256': hashlib.sha256(raw).hexdigest()}
    links = {}
    for ln in root.find('links').findall('link'):
        no = ln.get('no')
        fr, to = ln.find('fromLinkEndPt'), ln.find('toLinkEndPt')
        lanes = ln.findall('./lanes/lane')
        row = {'no': no, 'name': ln.get('name'), 'lanes': len(lanes), 'length_m': plen(ln),
               'behav': ln.get('linkBehavType'), 'lnChgDist': ln.get('lnChgDist'),
               'is_connector': fr is not None}
        if fr is not None:
            fl, fi = fr.get('lane').split()
            tl, ti = to.get('lane').split()
            row.update(from_link=fl, from_lane=int(fi), from_pos=float(fr.get('pos')),
                       to_link=tl, to_lane=int(ti), to_pos=float(to.get('pos')))
        links[no] = row
    res['links'] = links
    heads = []
    for h in root.find('signalHeads').findall('signalHead'):
        lk, li = h.get('lane').split()
        sc, sg = h.get('sg').split()
        heads.append({'no': h.get('no'), 'name': h.get('name'), 'link': lk, 'lane': int(li),
                      'pos': float(h.get('pos')), 'sc': sc, 'sg': sg, 'allVehTypes': h.get('allVehTypes'),
                      'type': h.get('type'), 'isBlockSig': h.get('isBlockSig')})
    res['signal_heads'] = heads
    scs = []
    for c in root.find('signalControllers').findall('signalController'):
        scs.append({'no': c.get('no'), 'name': c.get('name'), 'type': c.get('type'),
                    'supply2': c.get('supplyFile2'), 'active': c.get('active')})
    res['signal_controllers'] = scs
    inputs = []
    for vi in root.find('vehicleInputs').findall('vehicleInput'):
        inputs.append({'no': vi.get('no'), 'name': vi.get('name'), 'link': vi.get('link')})
    res['vehicle_inputs'] = inputs
    rds = []
    for d in root.iter('vehicleRoutingDecisionStatic'):
        routes = []
        for r in d.iter('vehicleRouteStatic'):
            routes.append({'no': r.get('no'), 'name': r.get('name'), 'destLink': r.get('destLink'),
                           'destPos': float(r.get('destPos')), 'relFlow': r.get('relFlow'),
                           'linkSeq': [x.get('key') for x in r.findall('./linkSeq/intObjectRef')]})
        rds.append({'no': d.get('no'), 'name': d.get('name'), 'link': d.get('link'), 'pos': float(d.get('pos')),
                    'allVehTypes': d.get('allVehTypes'), 'routes': routes})
    res['routing_static'] = rds
    other_rd = {}
    for tag in ('vehicleRoutingDecisionPartial', 'vehicleRoutingDecisionDynamic', 'vehicleRoutingDecisionManagedLanes',
                'vehicleRoutingDecisionClosure', 'vehicleRoutingDecisionParking'):
        other_rd[tag] = len(list(root.iter(tag)))
    res['routing_other_counts'] = other_rd
    qcs = []
    qq = root.find('queueCounters')
    if qq is not None:
        for q in qq.findall('queueCounter'):
            qcs.append({'no': q.get('no'), 'name': q.get('name'), 'link': q.get('link'), 'pos': float(q.get('pos'))})
    res['queue_counters'] = qcs
    dcps = []
    dd = root.find('dataCollectionPoints')
    if dd is not None:
        for q in dd.findall('dataCollectionPoint'):
            lk, li = q.get('lane').split()
            dcps.append({'no': q.get('no'), 'name': q.get('name'), 'link': lk, 'lane': int(li), 'pos': float(q.get('pos'))})
    res['data_collection_points'] = dcps
    dbs = {}
    for d in root.iter('drivingBehavior'):
        a = d.attrib
        dbs[a['no']] = {k: a.get(k) for k in ('name', 'carFollowModType', 'w74ax', 'w74bxAdd', 'w74bxMult', 'w99cc0',
                                               'w99cc1Distr', 'standDist', 'standDistIsFix', 'lnChgRule')}
    res['driving_behaviours'] = dbs
    lbt = {}
    for t in root.iter('linkBehaviorType'):
        lbt[t.get('no')] = {'name': t.get('name'), 'drivBehavDef': t.get('drivBehavDef'),
                            'by_class': [c.attrib for c in t.iter() if c is not t and c.attrib]}
    res['link_behaviour_types'] = lbt
    # 2D/3D model distributions and model lengths
    mods = {}
    for m in root.iter('model2D3D'):
        segs = [float(s.get('length')) for s in m.iter('model2D3DSegment') if s.get('length') is not None]
        mods[m.get('no')] = {'name': m.get('name'), 'seg_lengths': segs, 'length_sum': sum(segs)}
    res['models2d3d'] = mods
    mdist = {}
    for m in root.iter('model2D3DDistribution'):
        els = []
        for e in m.iter('model2D3DDistributionElement'):
            els.append({'model': e.get('model2D3D'), 'share': e.get('share')})
        mdist[m.get('no')] = {'name': m.get('name'), 'elements': els}
    res['model_distributions'] = mdist
    vts = {}
    for vt in root.iter('vehicleType'):
        vts[vt.get('no')] = {'name': vt.get('name'), 'category': vt.get('category'), 'model2D3DDistr': vt.get('model2D3DDistr')}
    res['vehicle_types'] = vts
    comps = {}
    for c in root.iter('vehicleComposition'):
        rel = [{'vehType': r.get('vehType'), 'relFlow': r.get('relFlow'), 'desSpeedDistr': r.get('desSpeedDistr')}
               for r in c.iter('vehicleCompositionRelativeFlow')]
        comps[c.get('no')] = {'name': c.get('name'), 'rel': rel}
    res['vehicle_compositions'] = comps
    cas = []
    ca = root.find('conflictAreas')
    if ca is not None:
        for c in ca.findall('conflictArea'):
            cas.append({'no': c.get('no'), 'link1': c.get('link1'), 'link2': c.get('link2'), 'status': c.get('status')})
    res['conflict_areas'] = cas
    tmp = out + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as g:
        json.dump(res, g, ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(tmp, out)
    print('links', len(links), 'heads', len(heads), 'scs', len(scs), 'inputs', len(inputs), 'rd', len(rds),
          'qc', len(qcs), 'dcp', len(dcps), 'models', len(mods), 'mdist', len(mdist), 'comps', len(comps),
          'ca', len(cas), 'other_rd', other_rd)
    print(hashlib.sha256(open(out, 'rb').read()).hexdigest())


if __name__ == '__main__':
    main()
