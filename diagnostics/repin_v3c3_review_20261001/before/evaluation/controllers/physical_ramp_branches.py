"""Physical on-ramp reservoirs for the canonical coupled model.

One connector has one stock, one service ceiling and its own merge cell.
The existing urban approach stocks remain the sole owners of approach traffic.
This migration does not create another copy of those vehicles or infer their
destinations from a grouped observed discharge rate.
"""
from __future__ import annotations

import copy
import csv
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]


def enabled(cfg):
    return hasattr(cfg.network, 'physical_ramp_branches')


def _read(pin):
    path = ROOT / pin['path']
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != pin['sha256']:
        raise ValueError('Physical ramp source changed: ' + str(path))
    return content


def configure(cfg, tuning, mapping, detectors, raw):
    path = tuning.get('urban', {}).get('physical_ramp_branches')
    if path is None:
        return detectors, {}
    if enabled(cfg):
        raise ValueError('Physical ramps must be configured once before projection')
    spec = json.loads((ROOT / path).read_text(encoding='utf-8'))
    from evaluation.controllers.network_provenance import snapshot_network_sha256
    if snapshot_network_sha256(raw) != spec['network']['sha256']:
        raise ValueError('Physical ramps and observed network differ')
    tree = ET.fromstring(_read(spec['network']))
    if json.loads(_read(spec['mapping']))['ramp_meters'] != mapping['ramp_meters']:
        raise ValueError('Physical ramp writer mapping differs')
    jam = float(json.loads(_read(spec['jam_source']))['jam_density_veh_km_lane'])
    if not math.isfinite(jam) or jam <= 0:
        raise ValueError('Positive declared ramp storage density required')
    settings = tuning['actuation']['real_world_ramp_metering']
    if settings['cycle_sec'] != 10 or settings['max_green_sec'] != 10 or settings.get('amber_sec') != 0:
        raise ValueError('Physical ramp migration requires the declared10s RED/GREEN-only meter cycle')
    table = settings['per_lane_veh_per_cycle']
    if (type(spec['max_green_change_sec']) not in (int,float)
            or not math.isfinite(spec['max_green_change_sec']) or spec['max_green_change_sec'] < 0
            or any(type(v) not in (int,float) or not math.isfinite(v) or v < 0 for v in table.values())):
        raise ValueError('Invalid physical service table or declared green change limit')
    rows = {}
    old = set(cfg.network.ramps)
    for meter in mapping['ramp_meters']:
        mid, connector = meter['id'], str(meter['connector'])
        node = tree.find("./links/link[@no='%s']" % connector)
        if node is None or mid in rows or meter['model_ramp_key'] not in old:
            raise ValueError('Invalid physical ramp catalog')
        start, end = node.find('fromLinkEndPt'), node.find('toLinkEndPt')
        if (int(start.get('lane').split()[0]) != meter['from_link']
                or int(end.get('lane').split()[0]) != meter['to_link']):
            raise ValueError('Physical ramp endpoints differ from writer mapping')
        points = [(float(p.get('x')), float(p.get('y'))) for p in node.iter('linkPolyPoint')]
        length = math.fsum(math.dist(a, b) for a, b in zip(points, points[1:]))
        lanes = len(node.findall('./lanes/lane'))
        if length <= 0 or lanes < 1 or settings.get('meter_lanes', {}).get(mid, 1) != lanes:
            raise ValueError('Physical ramp geometry/service lane count mismatch')
        capacity = lanes * float(table['10']) * 3600 / settings['cycle_sec']
        rows[mid] = {**copy.deepcopy(meter), 'legacy_group': meter['model_ramp_key'],
            'length_m': length, 'lane_count': lanes, 'storage_veh': length/1000*lanes*jam,
            'service_capacity_veh_h': capacity,
            'service_by_green_veh_h': {'0': 0., **{g: lanes*float(n)*3600/settings['cycle_sec'] for g,n in table.items()}}}
    if len(rows) != 8 or any(sum(r['to_model_link'] == owner for r in rows.values()) != 4 for owner in ('FW_E','FW_W')):
        raise ValueError('Exactly eight physical ramps, four per freeway required')
    net = cfg.network
    city = copy.deepcopy(spec.get('shared_city_arrival'))
    if city is not None:
        branch=net.shared_approach['branches'][city['branch']]
        decision=tree.find("./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no='%s']" % city['decision_no'])
        movements=city['movement_connectors']
        if (branch['target_kind']!='storage' or branch['target']!=city['receiver'] or decision is None
                or decision.get('link')!=branch['physical_receiver_start']):
            raise ValueError('City arrival route does not follow the declared shared branch')
        seen=set()
        for route in decision.findall('./vehRoutSta/vehicleRouteStatic'):
            path_links=[decision.get('link'),*[p.get('key') for p in route.findall('./linkSeq/intObjectRef')],route.get('destLink')]
            matches=[m for m,c in movements.items() if c in path_links]
            if len(matches)!=1 or any(str(row['connector']) in path_links for row in rows.values()):
                raise ValueError('Declared city arrival can reach a ramp or lacks one reviewed movement')
            seen.add(matches[0])
        if seen!=set(movements) or any(net.urban_movements[m].get('origin')!=city['receiver'] or net.urban_movements[m].get('ramp') for m in movements):
            raise ValueError('City arrival movement/source catalog differs')
        weights={m:float(net.urban_movements[m]['beta']) for m in movements}
        if any(not math.isfinite(v) or v<=0 for v in weights.values()):
            raise ValueError('City conditional turn weights must be positive and finite')
        total=math.fsum(weights.values())
        city['conditional_shares']={m:v/total for m,v in weights.items()}
        city['share_policy']='Existing city conditional beta preserved; forbidden on-ramp reselection removed'
    # Validate the complete source catalog before modifying the configured model.
    active = {m:s['ramp'] for m,s in net.urban_movements.items() if s.get('ramp')}
    if set(active) != set(spec['movement_receivers']):
        raise ValueError('Physical ramp source movement catalog changed')
    for movement, mid in spec['movement_receivers'].items():
        if mid not in rows or active[movement] != rows[mid]['legacy_group']:
            raise ValueError('Physical movement receiver changes its freeway destination')
    for name in ('shared_approach', 'sc2001_corridor'):
        obj = getattr(net, name)
        for branch in obj['branches'].values():
            if branch['target_kind'] == 'ramp':
                physical = branch.get('physical_receiver_start', branch['path'][-1])
                matches = [mid for mid,r in rows.items() if str(r['connector']) == str(physical)]
                if len(matches) != 1 or rows[matches[0]]['legacy_group'] != branch['target']:
                    raise ValueError('Physical corridor receiver is ambiguous')
    for source, choices in net.boundary_out_ramp_split.items():
        if set(choices['ramps']) != set(spec['out_link_receivers'][source]):
            raise ValueError('Physical out-link routing catalog changed')
        for group, mid in spec['out_link_receivers'][source].items():
            if rows[mid]['legacy_group'] != group:
                raise ValueError('Out-link destination changed freeway direction')
    copied = copy.deepcopy(detectors)
    for mid, row in rows.items():
        connector = str(row['connector'])
        if copied['ramp_link_to_queues'].get(connector) != [row['legacy_group']]:
            raise ValueError('Physical ramp projection is not the declared legacy source')
        copied['ramp_link_to_queues'][connector] = [mid]
    net.physical_ramp_branches = {'schema': 'physical-ramp-branches/v1', 'ramps': rows,
        'writer_mapping': copy.deepcopy(mapping['ramp_meters']),
        'network': spec['network'], 'cycle_sec': settings['cycle_sec'],
        'minimum_green_sec': settings['min_green_sec'], 'legacy_groups': sorted(old),
        'max_green_change_sec': spec['max_green_change_sec'],
        'unresolved': copy.deepcopy(spec.get('unresolved', []))}
    if city is not None:
        net.physical_ramp_branches['shared_city_arrival']=city
    net.ramps = list(rows)
    net.ramp_to_freeway = {mid:r['to_model_link'] for mid,r in rows.items()}
    net.ramp_merge_segment_index = {mid:r['to_model_segment_index'] for mid,r in rows.items()}
    net.ramp_capacity_veh_h = {mid:r['service_capacity_veh_h'] for mid,r in rows.items()}
    net.ramp_queue_max_veh_by_ramp = {mid:r['storage_veh'] for mid,r in rows.items()}
    # Preserve the existing suppression of duplicate external arrivals at the
    # urban allocator; a renamed ramp must not regain the grouped proxy source.
    gate_ramps = set(getattr(net, 'gate_onramp_queue_ramps', ()))
    net.gate_onramp_queue_ramps = [mid for mid,r in rows.items() if r['legacy_group'] in gate_ramps]
    net.on_ramp_to_movement = {mid:[] for mid in rows}
    for movement, mid in spec['movement_receivers'].items():
        net.urban_movements[movement]['ramp'] = mid
        net.on_ramp_to_movement[mid].append(movement)
    for name in ('shared_approach', 'sc2001_corridor'):
        for branch in getattr(net, name)['branches'].values():
            if branch['target_kind'] == 'ramp':
                physical = branch.get('physical_receiver_start', branch['path'][-1])
                branch['target'] = next(mid for mid,r in rows.items() if str(r['connector']) == str(physical))
    for source, choices in net.boundary_out_ramp_split.items():
        choices['ramps'] = {spec['out_link_receivers'][source][group]: share for group,share in choices['ramps'].items()}
    net.boundary_out_ramp_position_m = {
        source:{spec['out_link_receivers'][source][group]:value for group,value in positions.items()}
        for source,positions in net.boundary_out_ramp_position_m.items()}
    from evaluation.controllers.physical_movement_routes import invalidate_topology_cache
    invalidate_topology_cache(net)
    return copied, {'physical_ramp_branch_count': 8, 'physical_ramp_approach_stocks_duplicated': False,
                    'physical_ramp_observed_regions': observed_regions(raw, rows, tree),
                    'physical_ramp_source_limitations': net.physical_ramp_branches['unresolved']}


def observed_regions(raw, ramps, tree):
    """Eight disjoint source-link plus connector views of existing observations.

    This is not eight additional stocks. Mixed approach traffic stays in its
    sole urban owner. Current route tags distinguish this ramp, another ramp,
    no ramp in the remaining current route, and unresolved future choice.
    """
    from evaluation.controllers.projection_support import complete_records
    from evaluation.controllers.vehicle_routes import complete_vehicle_routes
    records, routes = complete_records(raw), complete_vehicle_routes(raw, required=True)
    connector_owner = {str(row['connector']):mid for mid,row in ramps.items()}
    support = {mid:{str(row['from_link']),str(row['connector'])} for mid,row in ramps.items()}
    if len(set().union(*support.values())) != sum(len(v) for v in support.values()):
        raise ValueError('Physical ramp observation regions overlap')
    paths={}
    for decision in tree.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic'):
        for route in decision.findall('./vehRoutSta/vehicleRouteStatic'):
            paths[decision.get('no')+':'+route.get('no')]=[decision.get('link')]+[
                ref.get('key') for ref in route.findall('./linkSeq/intObjectRef')]+[route.get('destLink')]
    result={}
    for mid,row in ramps.items():
        total={'approach_veh':0,'connector_veh':0,'this_ramp_veh':0,
            'other_ramp_veh':{},'current_route_without_ramp_veh':0,'unresolved_veh':0}
        for record in records:
            link=str(record['link_no'])
            if link not in support[mid]:continue
            if link==str(row['connector']):
                total['connector_veh']+=1;total['this_ramp_veh']+=1;continue
            total['approach_veh']+=1
            route=routes[record['veh_no']]
            key=(str(route['route_decision_no'])+':'+str(route['route_no'])
                 if route['route_decision_type']=='STATIC' else None)
            path=paths.get(key,[])
            if path.count(link)!=1:
                total['unresolved_veh']+=1;continue
            target=next((connector_owner[p] for p in path[path.index(link)+1:] if p in connector_owner),None)
            if target==mid:total['this_ramp_veh']+=1
            elif target is None:total['current_route_without_ramp_veh']+=1
            else:total['other_ramp_veh'][target]=total['other_ramp_veh'].get(target,0)+1
        total['region_veh']=total['approach_veh']+total['connector_veh']
        if total['region_veh']!=total['this_ramp_veh']+sum(total['other_ramp_veh'].values())+total['current_route_without_ramp_veh']+total['unresolved_veh']:
            raise ValueError('Physical ramp region classification lost an observed vehicle')
        result[mid]={'physical_links':sorted(support[mid]),**total}
    return result


def tag_shared_city_arrival(state,cfg,branch,step,vehicles):
    """Retain destination restrictions inside the existing parent travel stock."""
    spec=getattr(cfg.network,'physical_ramp_branches',{}).get('shared_city_arrival')
    if spec is None or branch!=spec['branch']:
        return
    if type(step) is not int or step<0 or type(vehicles) not in (int,float) or not math.isfinite(vehicles) or vehicles<0:
        raise ValueError('Invalid route-locked city arrival')
    tags=state.shared_approach_state.setdefault('city_arrival_tags',{})
    tags[step]=tags.get(step,0.)+vehicles


def split_tagged_arrival(state,cfg,source,step,arrived,routing):
    """Split tagged and untagged cohorts without creating another stock.

    The same parent arrival/release buffers still control travel and capacity.
    Only vehicles already committed to the city branch lose the on-ramp choice.
    Initial70 traffic and all unrelated sources retain their existing treatment.
    """
    initial=getattr(state,'gate_initial_route_tags',{}).get(source,{})
    named=initial.get(step)
    if named is not None:
        tagged=sum(named.values())
        if tagged>arrived+1e-8 or tagged<0 or not set(named)<=dict(routing).keys():
            raise ValueError('Initial gate route tags exceed their parent arrival or movement catalog')
        untagged=max(0.,arrived-tagged)
        values={m:beta*untagged+named.get(m,0.) for m,beta in routing}
        initial.pop(step)
        return list(values.items())
    spec=getattr(cfg.network,'physical_ramp_branches',{}).get('shared_city_arrival')
    if spec is None or source!=spec['receiver']:
        return None
    tags=getattr(state,'shared_approach_state',{}).get('city_arrival_tags',{})
    tagged=tags.get(step,0.)
    if not tagged:
        return None
    if not math.isfinite(arrived) or arrived<0 or tagged>arrived+1e-8:
        raise ValueError('Route-locked arrivals exceed their parent travel count')
    weights=spec['conditional_shares']
    if not set(weights)<=dict(routing).keys():
        raise ValueError('Route-locked city movement catalog changed')
    untagged=max(0.,arrived-tagged)
    values={m:beta*untagged for m,beta in routing}
    allocated=0.
    for i,(movement,share) in enumerate(weights.items()):
        amount=tagged-allocated if i==len(weights)-1 else tagged*share
        values[movement]+=amount;allocated+=amount
    tags.pop(step)
    return list(values.items())


def _native_gate_future_spec(state,cfg,tuning,raw):
    """Geometry of unborn1102 cohorts; independent of current route capture."""
    from evaluation.controllers.projection_support import complete_records
    from evaluation.controllers.route_choice_corridor import _length,_validate_path,_travel_segments,_speed
    from evaluation.controllers.offramp_routing import _weight
    from evaluation.controllers.control_area_objective import physical_membership_from_ledger
    source='in_SC1001_W';net=cfg.network
    if state.urban_inflow_transit_buffer.get('gate:'+source):
        raise ValueError('Future gate travel cannot reinterpret an initialized untagged transit stock')
    root=ET.fromstring(_read(net.physical_ramp_branches['network']))
    links={n.get('no'):n for n in root.findall('./links/link')}
    decision=root.find("./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no='1136']")
    if decision is None or decision.get('link')!='32' or decision.get('allVehTypes')!='true' or decision.get('routeChoiceMeth')!='STATIC':
        raise ValueError('Future gate routes require the reviewed native1136 decision')
    expected={'1':['32','10482','120'],'2':['32','10778','129','10777','127'],
              '3':['32','10778','129','10490','119']}
    native={r.get('no'):['32',*[n.get('key') for n in r.findall('./linkSeq/intObjectRef')],r.get('destLink')]
            for r in decision.findall('./vehRoutSta/vehicleRouteStatic')}
    weights={r.get('no'):_weight(r) for r in decision.findall('./vehRoutSta/vehicleRouteStatic')}
    if native!=expected or sum(weights.values())<=0:raise ValueError('Native1136 paths changed')
    priors={k:w/sum(weights.values()) for k,w in weights.items()}
    inputs=[n.get('no') for n in root.findall('./vehicleInputs/vehicleInput') if n.get('link')=='32']
    if inputs!=['1102']:raise ValueError('Native gate input source changed')
    managed={'32','10778','129','10777','127'}
    inside=physical_membership_from_ledger(json.loads((ROOT/tuning['control_area_objective']['membership_path']).read_bytes()))
    if not all(inside.get(k) is True for k in managed):raise ValueError('Future gate source has mixed area membership')
    movements={'1':'SC1001_W_to_onW','3':'SC1001_W_to_onE'}
    for route,m in movements.items():
        spec=net.urban_movements[m]
        if spec.get('origin')!=source or spec.get('ramp')!='RM_C'+expected[route][-2]:
            raise ValueError('Native gate movement receiver differs')
    city={m:float(s['beta']) for m,s in net.urban_movements.items() if s.get('origin')==source and not s.get('ramp')}
    if not city or sum(city.values())<=0:raise ValueError('City conditional movements missing')
    city={m:v/sum(city.values()) for m,v in city.items()}
    heads=[float(h.get('pos')) for h in root.findall('./signalHeads/signalHead')
           if h.get('lane').split()[0]=='127' and h.get('sg').split()[0]=='1001']
    if not heads:raise ValueError('City gate has no reviewed source head')
    paths={'1':['32'],'3':['32','10778','129'],'2':['32','10778','129','10777','127']}
    terminals={'1':float(links['10482'].find('fromLinkEndPt').get('pos')),
               '3':float(links['10490'].find('fromLinkEndPt').get('pos')),'2':min(heads)}
    lengths={k:_length(links[k]) for k in managed};geometry={}
    for route,path in paths.items():
        _validate_path(path,links)
        geometry[route]=_travel_segments(path,links,lengths,terminals[route])
    records=complete_records(raw);road_speeds={}
    for link in managed:
        observed=[r['speed_kph'] for r in records if str(r['link_no'])==link]
        if observed:road_speeds[link]=_speed(state,cfg,sum(observed)/len(observed))
    timings={}
    for route,segments in geometry.items():
        seconds=0.;parts=[]
        for segment in segments:
            link=segment['link'];distance=segment['stop']-segment['start']
            connector=links[link].find('fromLinkEndPt');speed=road_speeds.get(link)
            if speed is None and connector is not None:speed=road_speeds.get(connector.get('lane').split()[0])
            if speed is None:speed=_speed(state,cfg)
            seconds+=distance/(speed/3.6)
            parts.append(dict(link=link,distance_m=distance,speed_kph=speed))
        timings[route]=dict(delay_steps=max(1,math.ceil(seconds/cfg.simulation.T_u_sec)),parts=parts)
    return dict(source=source,input_no='1102',geometry=geometry,priors=priors,
                timings=timings,movements=movements,city=city,
                speed_evidence='Current per-link arithmetic mean; held over this forecast',
                admission='Aggregate physical approach space only; no input headway model')


def _native_gate_entry_capacities(cfg, entry_rate):
    """Geometry-only approach ceilings; independent of route IDs and RM greens."""
    from evaluation.controllers.route_choice_corridor import _validate_path
    net=cfg.network
    root=ET.fromstring(_read(net.physical_ramp_branches['network']))
    links={n.get('no'):n for n in root.findall('./links/link')}
    decision=root.find("./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no='1136']")
    if decision is None or decision.get('link')!='32':
        raise ValueError('Gate entry native decision changed')
    expected={'1':['32','10482','120'],'3':['32','10778','129','10490','119']}
    routes={r.get('no'):['32',*[n.get('key') for n in r.findall('./linkSeq/intObjectRef')],r.get('destLink')]
            for r in decision.findall('./vehRoutSta/vehicleRouteStatic')}
    capacities={}
    for route,movement in (('1','SC1001_W_to_onW'),('3','SC1001_W_to_onE')):
        path=expected[route]; connector=path[-2]
        spec=net.urban_movements[movement]
        if (routes.get(route)!=path or spec.get('origin')!='in_SC1001_W'
                or spec.get('ramp')!='RM_C'+connector):
            raise ValueError('Gate entry route or movement receiver changed')
        _validate_path(path,links)
        node=links[connector]; lanes=len(node.findall('./lanes/lane'))
        if lanes<1:raise ValueError('Gate entry connector has no lanes')
        for endpoint,road in (('fromLinkEndPt',path[-3]),('toLinkEndPt',path[-1])):
            end=node.find(endpoint); tokens=end.get('lane').split()
            first=int(tokens[1]); available=len(links[road].findall('./lanes/lane'))
            if tokens[0]!=road or first<1 or first+lanes-1>available:
                raise ValueError('Gate entry lane geometry changed')
        capacities[movement]=entry_rate*lanes
    return capacities


def initialize_gate_routes(state,cfg,tuning,raw):
    """Retain current1136 ramp destinations in the existing approach stock.

    Opt-in initialization only. Future gate generation and accepted downstream
    arrivals retain their existing model; no new demand or duplicate stock.
    Unknown CITY turns retain the existing city-conditional mix. A missing
    past ramp choice is never redrawn; only vehicles before1136 may choose.
    """
    flag=tuning.get('urban',{}).get('ramp',{}).get('initial_native_gate_routes',False)
    city_lock=tuning.get('urban',{}).get('ramp',{}).get('initial_gate_city_lock',False)
    if type(city_lock) is not bool:
        raise ValueError('initial_gate_city_lock must be boolean')
    if city_lock and flag:
        raise ValueError('Choose topology-only city locking or complete native gate routes')
    future=tuning.get('urban',{}).get('ramp',{}).get('native_gate_travel',False)
    geometry_timing=tuning.get('urban',{}).get('ramp',{}).get('initial_gate_geometry_timing',False)
    if type(geometry_timing) is not bool or (geometry_timing and not (city_lock and future)):
        raise ValueError('Initial gate geometry timing requires boolean city locking and native gate travel')
    entry_rate=tuning.get('urban',{}).get('ramp',{}).get('gate_entry_capacity_per_lane_veh_h')
    if entry_rate is not None and (not (flag or city_lock) or type(entry_rate) not in (int,float)
                                  or not math.isfinite(entry_rate) or entry_rate<=0):
        raise ValueError('Explicit positive gate entry capacity requires reviewed initial gate geometry')
    if type(future) is not bool or (future and not (flag or city_lock)):
        raise ValueError('native_gate_travel requires reviewed native routes or topology initialization')
    if type(flag) is not bool:raise ValueError('initial_native_gate_routes must be boolean')
    if not flag:
        if not city_lock:return {}
        # Validate future transport before committing any initial route tags.
        future_spec=_native_gate_future_spec(state,cfg,tuning,raw) if future else None
        entry_caps=_native_gate_entry_capacities(cfg,entry_rate) if entry_rate is not None else {}
        report=_initialize_gate_city_lock(state,cfg,tuning,raw,
            geometry_timing=future_spec if geometry_timing else None)
        if entry_caps:
            cfg.network.movement_capacity_by_movement_veh_h={
                **cfg.network.movement_capacity_by_movement_veh_h,**entry_caps}
            report['gate_entry_capacity_veh_h']=entry_caps
        if future_spec is not None:
            cfg.network.physical_gate_travel=future_spec
            state.gate_future_route_tags={}
            state.gate_future_accounting=dict(desired_veh=0.,admitted_veh=0.,arrived_veh=0.)
            report['gate_future_travel']=future_spec
        return report
    if hasattr(state,'gate_initial_route_tags'):raise ValueError('Initial gate routes already initialized')
    from evaluation.controllers.projection_support import complete_records
    from evaluation.controllers.vehicle_routes import complete_vehicle_routes
    from evaluation.controllers.route_choice_corridor import (
        _length, _validate_path, _travel_segments, _known_remaining, _speed)
    from evaluation.controllers.offramp_routing import _weight
    from evaluation.controllers.control_area_objective import physical_membership_from_ledger
    # Reuse the physical ramp network pin, never the filename of another run.
    net=cfg.network;root=ET.fromstring(_read(net.physical_ramp_branches['network']))
    links={n.get('no'):n for n in root.findall('./links/link')}
    source='in_SC1001_W'
    movements={'1':'SC1001_W_to_onW','3':'SC1001_W_to_onE'}
    expected={'1':['32','10482','120'],'2':['32','10778','129','10777','127'],
              '3':['32','10778','129','10490','119']}
    decision=root.find("./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no='1136']")
    if (decision is None or decision.get('link')!='32' or decision.get('allVehTypes')!='true'
            or decision.get('routeChoiceMeth')!='STATIC'):
        raise ValueError('Initial gate routes require the reviewed native1136 decision')
    native={};weights={}
    for r in decision.findall('./vehRoutSta/vehicleRouteStatic'):
        key=r.get('no');native[key]=['32',*[x.get('key') for x in r.findall('./linkSeq/intObjectRef')],r.get('destLink')]
        weights[key]=_weight(r)
    if native!=expected or sum(weights.values())<=0:raise ValueError('Native1136 paths changed')
    priors={k:w/sum(weights.values()) for k,w in weights.items()}
    specs=net.urban_movements
    for route,m in movements.items():
        if specs[m].get('origin')!=source or specs[m].get('ramp')!='RM_C'+expected[route][-2]:
            raise ValueError('Native gate movement receiver differs')
    city={m:float(s['beta']) for m,s in specs.items() if s.get('origin')==source and not s.get('ramp')}
    if not city or sum(city.values())<=0:raise ValueError('City conditional movements missing')
    city={m:v/sum(city.values()) for m,v in city.items()}
    # All physical source links are insideOmega; no mixed-area stock is split.
    membership_path=tuning['control_area_objective']['membership_path']
    inside=physical_membership_from_ledger(json.loads((ROOT/membership_path).read_text(encoding='utf-8')))
    managed={'32','10778','129','10777','127'}
    if not all(inside.get(k) is True for k in managed):raise ValueError('Gate source has mixed area membership')
    heads=[float(h.get('pos')) for h in root.findall('./signalHeads/signalHead')
           if h.get('lane').split()[0]=='127' and h.get('sg').split()[0]=='1001']
    if not heads:raise ValueError('City gate has no reviewed source head')
    paths={'1':['32'],'3':['32','10778','129'],'2':['32','10778','129','10777','127']}
    terminals={'1':float(links['10482'].find('fromLinkEndPt').get('pos')),
               '3':float(links['10490'].find('fromLinkEndPt').get('pos')),'2':min(heads)}
    lengths={k:_length(links[k]) for k in managed}
    geometry={}
    for route,path in paths.items():
        _validate_path(path,links)
        geometry[route]=_travel_segments(path,links,lengths,terminals[route])
    route_paths={}
    for d in root.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic'):
        for r in d.findall('./vehRoutSta/vehicleRouteStatic'):
            route_paths[(int(d.get('no')),int(r.get('no')))]=[d.get('link'),*[x.get('key') for x in r.findall('./linkSeq/intObjectRef')],r.get('destLink')]
    records=complete_records(raw);routes=complete_vehicle_routes(raw,required=True)
    assigned=state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
    owned={k:row.get('storage:'+source,0.) for k,row in assigned.items() if row.get('storage:'+source,0.)>0}
    if not set(owned)<=managed:raise ValueError('Unreviewed physical link shares gate stock')
    threshold=raw['vehicle_records']['stopped_threshold_kph'];selected=[];city_only=0.
    for link,amount in owned.items():
        allrows=[r for r in records if str(r['link_no'])==link]
        # These links are already beyond both ramp choices. The legacy stopped
        # projection does not identify which individual vehicles own its city
        # storage share. Keep its timing, but prohibit another ramp choice.
        if link in ('127','10777'):
            if amount>len(allrows)+1e-8:raise ValueError('City gate storage exceeds observed vehicles')
            city_only+=amount
            continue
        moving=[r for r in allrows if r['speed_kph']>threshold]
        chosen=allrows if abs(amount-len(allrows))<1e-8 else moving
        if abs(amount-len(chosen))>1e-8:
            raise ValueError(f'Initial gate storage lacks exact physical vehicle allocation: link={link}, assigned={amount}, total={len(allrows)}, moving={len(moving)}, threshold={threshold}')
        selected.extend(chosen)
    count=sum(owned.values());capacity=net.urban_link_storage_veh[source]
    if abs(capacity-state.urban_link_storage[source]-count)>1e-7:raise ValueError('Initial gate stock mismatch')
    for buffers in (state.urban_arrival_buffer,state.urban_storage_release_buffer):
        if abs(sum(buffers.get(source,{}).values())-count)>1e-7:raise ValueError('Initial gate transit is not paired')
    tags={};proof=[];dt=cfg.simulation.T_u_sec;now=state.time_sec
    if city_only:
        for due,amount in state.urban_arrival_buffer[source].items():
            tags[due]={m:amount*city_only/count*w for m,w in city.items()}
        proof.append(dict(vehicle=None,route_family='2',vehicles=city_only,
                          timing='retained_legacy_city_schedule; no individual stock attribution'))
    for record in selected:
        link=str(record['link_no']);pos=record['position_m'];speed=_speed(state,cfg,record['speed_kph']);r=routes[record['veh_no']]
        if link in ('127','10777'):
            choices={'2':1.}
        elif link=='32' and pos<float(decision.get('pos')) and r['route_decision_no'] is None:
            choices=priors
        else:
            path=route_paths.get((r['route_decision_no'],r['route_no']),[])
            if r['route_decision_type']!='STATIC' or path.count(link)!=1:raise ValueError('Missing committed gate route after decision')
            remaining=path[path.index(link)+1:]
            chosen=[k for k in ('1','3') if expected[k][-2] in remaining]
            if len(chosen)>1:raise ValueError('Ambiguous current gate ramp destination')
            choices={chosen[0]:1.} if chosen else {'2':1.}
        for route,share in choices.items():
            path=paths[route]
            if link not in path:raise ValueError('Current gate route cannot reach its selected ramp')
            distance=_known_remaining(geometry[route],link,pos)
            due=int(round(now/dt))+max(1,math.ceil(distance/(speed/3.6)/dt))
            row=tags.setdefault(due,{})
            allocation={movements[route]:1.} if route in movements else city
            for movement,w in allocation.items():row[movement]=row.get(movement,0.)+share*w
            proof.append(dict(vehicle=record['veh_no'],link=link,route_family=route,vehicles=share,
                              remaining_m=distance,speed_kph=speed,due_sec=due*dt))
    paired={k:sum(row.values()) for k,row in tags.items()}
    if abs(sum(paired.values())-count)>1e-7:raise ValueError('Initial gate route tagging lost vehicles')
    future_spec=None
    entry_caps=_native_gate_entry_capacities(cfg,entry_rate) if entry_rate is not None else {}
    if future:
        future_spec=_native_gate_future_spec(state,cfg,tuning,raw)
    # Commit only after every vehicle and physical proof has passed.
    state.urban_arrival_buffer[source]=dict(paired)
    state.urban_storage_release_buffer[source]=dict(paired)
    state.gate_initial_route_tags={source:tags}
    state.gate_initial_route_evidence=proof
    if entry_caps:
        cfg.network.movement_capacity_by_movement_veh_h={
            **cfg.network.movement_capacity_by_movement_veh_h,**entry_caps}
    if future_spec is not None:
        cfg.network.physical_gate_travel=future_spec
        state.gate_future_route_tags={}
        state.gate_future_accounting=dict(desired_veh=0.,admitted_veh=0.,arrived_veh=0.)
    return {'gate_initial_route_tagged_veh':count,'gate_initial_native_priors':priors,
            'gate_initial_future_generation_changed':False,'gate_initial_new_stock_veh':0.,
            **({'gate_entry_capacity_veh_h':entry_caps} if entry_caps else {}),
            **({'gate_future_travel':future_spec} if future_spec is not None else {})}


def _geometry_gate_initial_tags(state,cfg,raw,records,owned,known,city,arrival,count,spec):
    """Causal remaining-distance timing for topology-conditional initial stock.

    No current route ID is inferred. Existing movement shares are conditioned
    on physical reachability. Already-city stock retains its original schedule.
    """
    source=spec['source'];net=cfg.network;dt=cfg.simulation.T_u_sec
    city_count=math.fsum(owned.get(k,0.) for k in known);city_total=math.fsum(city.values())
    tags={step:{m:n*city_count/count*v/city_total for m,v in city.items()}
          for step,n in arrival.items()} if count else {}
    shares={route:float(net.urban_movements[m]['beta']) for route,m in spec['movements'].items()}
    shares['2']=city_total
    if any(not math.isfinite(v) or v<0 for v in shares.values()) or abs(sum(shares.values())-1.)>1e-7:
        raise ValueError('Initial gate geometry requires normalized existing shares')
    proof=[dict(vehicle=None,vehicles=city_count,route_family='city',
                timing='retained_parent_city_schedule; no individual city ownership')]
    retimed=0.;threshold=raw['vehicle_records']['stopped_threshold_kph']
    for link,amount in owned.items():
        if link in known:continue
        allrows=[r for r in records if str(r['link_no'])==link]
        chosen=allrows if abs(amount-len(allrows))<1e-8 else [r for r in allrows if r['speed_kph']>threshold]
        if abs(amount-len(chosen))>1e-8:
            raise ValueError('Initial gate geometry requires exact physical vehicle ownership: '+link)
        for vehicle in chosen:
            position=vehicle['position_m'];eligible={}
            for route,segments in spec['geometry'].items():
                indices=[j for j,s in enumerate(segments) if s['link']==link]
                if not indices:continue
                if len(indices)!=1:raise ValueError('Repeated link in initial gate path')
                j=indices[0];segment=segments[j]
                if position>segment['stop']+1e-3:continue
                if position<segment['start']-1e-3:raise ValueError('Initial gate position precedes path')
                parts=spec['timings'][route]['parts']
                if len(parts)!=len(segments):raise ValueError('Gate speed/path geometry mismatch')
                seconds=0.
                for n,s in enumerate(segments[j:],j):
                    part=parts[n];speed=part['speed_kph']
                    if part['link']!=s['link'] or not math.isfinite(speed) or speed<=0:
                        raise ValueError('Invalid causal gate travel speed')
                    distance=max(0.,s['stop']-(max(position,s['start']) if n==j else s['start']))
                    seconds+=distance/(speed/3.6)
                eligible[route]=(shares[route],seconds)
            total=math.fsum(v[0] for v in eligible.values())
            if total<=0:raise ValueError('No reachable initial gate destination')
            for route,(weight,seconds) in eligible.items():
                if not weight:continue
                share=weight/total
                due=int(round(state.time_sec/dt))+max(1,math.ceil(seconds/dt))
                allocation={spec['movements'][route]:1.} if route in spec['movements'] else {m:v/city_total for m,v in city.items()}
                row=tags.setdefault(due,{})
                for m,w in allocation.items():row[m]=row.get(m,0.)+share*w
                proof.append(dict(vehicle=vehicle['veh_no'],link=link,position_m=position,
                    route_family=route,vehicles=share,due_sec=due*dt,remaining_travel_sec=seconds,
                    timing='current_position_and_causal_link_speeds; conditional_expectation_not_observed_route'))
            retimed+=1.
    paired={step:math.fsum(row.values()) for step,row in tags.items()}
    if abs(math.fsum(paired.values())-count)>1e-7 or abs(retimed+city_count-count)>1e-7:
        raise ValueError('Initial gate geometry timing lost physical stock')
    return paired,tags,proof,retimed


def _initialize_gate_city_lock(state,cfg,tuning,raw,*,geometry_timing=None):
    """Exclude passed branches; retain stock and, by default, legacy timing.

    Upstream traffic retains its legacy split. Traffic beyond the10482 fork
    uses that split conditioned on remaining reachable destinations; it is an
    aggregate expectation, not recovery of a missing committed vehicle route.
    Optional geometry timing requires exact current vehicle ownership upstream.
    Fractional city ownership keeps its prior timing; no arbitrary vehicle IDs
    or future trajectory frames are needed here.
    """
    from evaluation.controllers.projection_support import complete_records
    from evaluation.controllers.control_area_objective import physical_membership_from_ledger
    if hasattr(state,'gate_initial_route_tags'):
        raise ValueError('Initial gate routes already initialized')
    source='in_SC1001_W'; net=cfg.network
    root=ET.fromstring(_read(net.physical_ramp_branches['network']))
    links={n.get('no'):n for n in root.findall('./links/link')}
    for connector,start,end in (('10777','129','127'),('10695','127','38'),
            ('10482','32','120'),('10778','32','129'),('10490','129','119')):
        node=links.get(connector)
        if (node is None or node.find('fromLinkEndPt').get('lane').split()[0]!=start
                or node.find('toLinkEndPt').get('lane').split()[0]!=end):
            raise ValueError('Reviewed gate branch topology changed')
    if float(links['10482'].find('fromLinkEndPt').get('pos')) >= float(links['10778'].find('fromLinkEndPt').get('pos')):
        raise ValueError('10482 must branch before the10778 approach')
    known={'10777','127','10695'}
    managed={'32','10778','129'}|known
    assigned=state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
    owned={k:row['storage:'+source] for k,row in assigned.items() if row.get('storage:'+source,0.)>0}
    if not set(owned)<=managed:
        raise ValueError('Unreviewed physical link shares gate stock')
    inside=physical_membership_from_ledger(json.loads((ROOT/tuning['control_area_objective']['membership_path']).read_bytes()))
    if not all(type(inside.get(k)) is bool for k in owned):
        raise ValueError('Gate source lacks physical area membership')
    records=complete_records(raw)
    counts={k:sum(str(r['link_no'])==k for r in records) for k in owned}
    if any(not math.isfinite(v) or v>counts[k]+1e-8 for k,v in owned.items()):
        raise ValueError('Gate storage exceeds current physical vehicles')
    count=math.fsum(owned.values()); city_count=math.fsum(owned.get(k,0.) for k in known)
    if abs(net.urban_link_storage_veh[source]-state.urban_link_storage[source]-count)>1e-7:
        raise ValueError('Initial gate stock mismatch')
    arrival=state.urban_arrival_buffer.get(source,{})
    release=state.urban_storage_release_buffer.get(source,{})
    if (arrival!=release or abs(math.fsum(arrival.values())-count)>1e-7
            or any(not math.isfinite(v) or v<0 for v in arrival.values())):
        raise ValueError('Initial gate transit is not paired')
    city={m:float(s['beta']) for m,s in net.urban_movements.items()
          if s.get('origin')==source and not s.get('ramp')}
    total=math.fsum(city.values())
    if not city or total<=0 or any(not math.isfinite(v) or v<0 for v in city.values()):
        raise ValueError('City conditional movements missing')
    tags={step:{m:n*(city_count/count)*(v/total) for m,v in city.items()}
          for step,n in arrival.items()} if count else {}
    passed={'10778','129'}
    passed_count=math.fsum(owned.get(k,0.) for k in passed)
    east='SC1001_W_to_onE'; west='SC1001_W_to_onW'
    feasible=dict(city)
    for movement,expected_ramp in ((east,'RM_C10490'),(west,'RM_C10482')):
        spec=net.urban_movements.get(movement,{})
        if spec.get('origin')!=source or spec.get('ramp')!=expected_ramp:
            raise ValueError('Gate branch movement receiver differs')
        beta=float(spec['beta'])
        if not math.isfinite(beta) or beta<0:raise ValueError('Invalid gate branch share')
        if movement==east:feasible[movement]=beta
    feasible_total=math.fsum(feasible.values())
    if passed_count:
        for step,n in arrival.items():
            for movement,beta in feasible.items():
                tags[step][movement]=tags[step].get(movement,0.)+n*(passed_count/count)*(beta/feasible_total)
    if abs(sum(sum(row.values()) for row in tags.values())-city_count-passed_count)>1e-7:
        raise ValueError('City destination tagging lost vehicles')
    if geometry_timing is not None:
        paired,tags,proof,retimed=_geometry_gate_initial_tags(
            state,cfg,raw,records,owned,known,city,arrival,count,geometry_timing)
        state.urban_arrival_buffer[source]=dict(paired)
        state.urban_storage_release_buffer[source]=dict(paired)
        state.gate_initial_route_tags={source:tags}
        state.gate_initial_route_evidence=proof
        return dict(gate_initial_city_locked_veh=city_count,
            gate_initial_city_locked_outside_veh=sum(owned.get(k,0.) for k in known if not inside.get(k)),
            gate_initial_unresolved_destination_veh=count-city_count,
            gate_initial_reachability_conditioned_veh=passed_count,
            gate_initial_geometry_retimed_veh=retimed,
            gate_initial_new_stock_veh=0.,gate_initial_future_generation_changed=False,
            gate_initial_timing_changed=True,gate_initial_committed_routes_observed=False)
    # Tags constrain the existing parent stock, never add a second stock or
    # retime it. Preserve unknown upstream traffic's previous representation.
    state.gate_initial_route_tags={source:tags}
    state.gate_initial_route_evidence=[dict(link=k,vehicles=owned.get(k,0.),route_family='city',
        timing='retained_parent_schedule; topology-only ownership') for k in sorted(known)]
    state.gate_initial_route_evidence.extend(dict(link=k,vehicles=owned.get(k,0.),
        route_family='onE_or_city',conditional_shares={m:v/feasible_total for m,v in feasible.items()},
        timing='retained_parent_schedule; conditional expectation, committed route unobserved')
        for k in sorted(passed) if owned.get(k,0.)>0)
    return dict(gate_initial_city_locked_veh=city_count,
                gate_initial_city_locked_outside_veh=sum(owned.get(k,0.) for k in known if not inside.get(k)),
                gate_initial_unresolved_destination_veh=count-city_count,
                gate_initial_reachability_conditioned_veh=passed_count,
                gate_initial_unreachable_onW_removed_veh=passed_count*float(net.urban_movements[west]['beta']),
                gate_initial_new_stock_veh=0.,gate_initial_future_generation_changed=False,
                gate_initial_timing_changed=False)


def advance_gate(state,cfg,source,step,desired):
    """Generate, admit, and transport1102 cohorts in existing counted buffers.

    Uninserted demand stays outsideOmega in a distinct transit buffer. Accepted
    vehicles occupy the existing inside transit stock once. Tags are metadata;
    known destinations cannot change when another candidate changes a beta.
    """
    spec=getattr(cfg.network,'physical_gate_travel',None)
    if spec is None or source!=spec['source']:return None
    if not math.isfinite(desired) or desired<0:raise ValueError('Invalid physical gate demand')
    from evaluation.controllers.control_area_objective import emit_transfer,get_ledger
    from evaluation.controllers.lane_urban_runtime import observe_ready
    buffers=state.urban_inflow_transit_buffer
    travel=buffers.setdefault('gate:'+source,{})
    waiting=buffers.setdefault('gate_wait:'+source,{0:0.})
    if set(waiting)!={0}:raise ValueError('Physical gate waiting stock has an invalid schedule')
    tags=state.gate_future_route_tags;stats=state.gate_future_accounting
    arrived=travel.get(step,0.);named=tags.get(step,{})
    if abs(sum(named.values())-arrived)>1e-8:raise ValueError('Physical gate destination tags differ from transit stock')
    if set(named)-set(cfg.network.urban_movements):raise ValueError('Physical gate arrival movement vanished')
    travel.pop(step,None);tags.pop(step,None)
    for movement,amount in named.items():
        state.urban_movement_queue[movement]+=amount
        observe_ready(state,cfg,movement,amount)
        emit_transfer(state,cfg,'transit:gate:'+source,'movement:'+movement,amount,
                      route_key='arrival:'+movement)
    stats['arrived_veh']+=arrived
    waiting[0]+=desired;stats['desired_veh']+=desired
    emit_transfer(state,cfg,None,'transit:gate_wait:'+source,desired,
                  route_key='input:gate_wait:'+source,source_inside=False,target_inside=False)
    # Movement queues and travel stock share the physical approach capacity.
    # Do not use the distant CITY stopline's short queue cap for both ramps.
    queued=sum(state.urban_movement_queue[m] for m,s in cfg.network.urban_movements.items()
               if s.get('origin')==source)
    space=max(0.,state.urban_link_storage[source]-queued-sum(travel.values()))
    admitted=min(waiting[0],space)
    ledger=get_ledger(state)
    if ledger is not None and ledger.captures_response:
        ledger.record_resource_allocation('urban_gate_approach_space',source,space,
                                          {'input:gate:'+source:admitted})
    waiting[0]-=admitted;stats['admitted_veh']+=admitted
    emit_transfer(state,cfg,'transit:gate_wait:'+source,'transit:gate:'+source,admitted,
                  route_key='admit:gate:'+source,target_inside=True)
    allocated=0.
    for i,(route,share) in enumerate(spec['priors'].items()):
        amount=admitted-allocated if i==len(spec['priors'])-1 else admitted*share
        allocated+=amount
        if amount<=0:continue
        due=step+spec['timings'][route]['delay_steps']
        travel[due]=travel.get(due,0.)+amount
        from evaluation.controllers.omega_distance import record_gate
        record_gate(state,cfg,route,amount,step,due)
        row=tags.setdefault(due,{})
        choices={spec['movements'][route]:1.} if route in spec['movements'] else spec['city']
        for movement,weight in choices.items():row[movement]=row.get(movement,0.)+amount*weight
    if (abs(stats['desired_veh']-stats['admitted_veh']-waiting[0])>1e-7
            or abs(stats['admitted_veh']-stats['arrived_veh']-sum(travel.values()))>1e-7):
        raise ValueError('Physical gate demand/admission/travel conservation failed')
    return dict(desired_veh=desired,admitted_veh=admitted,arrived_veh=arrived,
                outside_wait_veh=waiting[0])


def prepare_control(control, cfg):
    """Decode explicit recorded eight-SG greens; never divide a group rate."""
    if not enabled(cfg):
        return control
    spec = cfg.network.physical_ramp_branches
    old_rates = dict(control.ramp_metering)
    if set(old_rates) not in (set(spec['ramps']), set(spec['legacy_groups'])):
        raise ValueError('Incomplete physical or historical ramp action')
    rates = {}
    for mid, row in spec['ramps'].items():
        green = control.diagnostics.get('rw_meter_green_' + mid)
        if (type(green) not in (int,float) or not math.isfinite(green) or green != int(green)
                or (green != 0 and green < spec['minimum_green_sec'])
                or str(int(green)) not in row['service_by_green_veh_h']):
            raise ValueError('Explicit quantized physical green required: '+mid)
        rates[mid] = row['service_by_green_veh_h'][str(int(green))]
    if set(old_rates) == set(spec['ramps']) and old_rates != rates:
        raise ValueError('Physical service rates differ from eight green commands')
    if set(old_rates) == set(spec['legacy_groups']):
        control.diagnostics['physical_ramp_historical_group_rates'] = old_rates
        control.diagnostics['physical_ramp_historical_nuf_target'] = control.N_UF_star
    control.ramp_metering = rates
    control.diagnostics['physical_ramp_quantity_semantics'] = 'service_ceiling_only; predicted_merge_is_separate'
    return control


def read_recorded_control(control, cfg, path):
    if not enabled(cfg):
        return control
    # A historical no-control JSON may have no meter diagnostics. Its sibling
    # command CSV supplies explicit eight-SG greens, never a divided group sum.
    source = Path(path).with_suffix('.csv')
    content = source.read_bytes()
    rows = [row for row in csv.DictReader(content.decode('utf-8-sig').splitlines()) if row['kind']=='ramp_meter']
    spec = cfg.network.physical_ramp_branches
    if len(rows) != 8 or {row['id'] for row in rows} != set(spec['ramps']):
        raise ValueError('Recorded CSV requires exactly eight physical meter rows')
    for row in rows:
        meter = spec['ramps'][row['id']]
        green = float(row['green_sec'])
        # The canonical writer also labels fixed-command replay explicitly.
        # Parsing either status is not a certificate of native execution.
        if (int(row['sc_no']) != meter['sc_no'] or row['metadata'].split(';')[0] not in ('ok','fixed_command_replay')
                or float(row['rate_vph']) != green*meter['capacity_vph']/meter['cycle_sec']):
            raise ValueError('Recorded physical meter CSV address/encoding mismatch')
        key = 'rw_meter_green_'+row['id']
        if key in control.diagnostics and control.diagnostics[key] != green:
            raise ValueError('Recorded JSON/CSV physical meter green mismatch')
        control.diagnostics[key] = green
    control.diagnostics['physical_ramp_recorded_csv'] = {'path':str(source), 'sha256':hashlib.sha256(content).hexdigest()}
    return prepare_control(control, cfg)


def held_actual_reference(historical, cfg):
    """Verify the eight recorded commands without a current-demand allocator."""
    proof = historical.diagnostics.get('physical_ramp_recorded_csv')
    if not isinstance(proof, dict) or set(proof) != {'path', 'sha256'}:
        raise ValueError('Physical held reference requires its recorded command CSV')
    source = Path(proof['path'])
    if hashlib.sha256(source.read_bytes()).hexdigest() != proof['sha256']:
        raise ValueError('Physical held command CSV changed')
    reference = read_recorded_control(historical.copy(), cfg, source)
    if (reference.ramp_metering != historical.ramp_metering
            or physical_commands(reference, cfg) != physical_commands(historical, cfg)):
        raise ValueError('Physical held command differs from its recorded eight SGs')
    # N_UF is a leader target, never the service ceiling sum. In a first
    # migration decision its historical legacy value remains evidence only.
    if reference.N_UF_star != historical.N_UF_star:
        raise ValueError('Physical held reference changed its historical target')
    return reference


def candidate_from_greens(incumbent, actual_reference, cfg, greens):
    """Realize eight coordinates inside one actual-action green box."""
    if not enabled(cfg):
        raise ValueError('Eight-green candidate requires physical ramps')
    spec = cfg.network.physical_ramp_branches
    if type(greens) is not dict or set(greens) != set(spec['ramps']):
        raise ValueError('Exactly eight explicit candidate greens required')
    prepare_control(actual_reference.copy(), cfg)
    prepare_control(incumbent.copy(), cfg)
    limit = spec['max_green_change_sec']
    if type(limit) not in (int,float) or not math.isfinite(limit) or limit < 0:
        raise ValueError('Explicit finite actual-green change limit required')
    candidate = incumbent.copy()
    for mid, value in greens.items():
        key = 'rw_meter_green_'+mid
        if type(value) not in (int,float) or not math.isfinite(value) or abs(value-actual_reference.diagnostics[key]) > limit:
            raise ValueError('Outside fixed actual-green box: '+mid)
        if value != int(value) or str(int(value)) not in spec['ramps'][mid]['service_by_green_veh_h']:
            raise ValueError('Unrealizable physical meter green: '+mid)
        candidate.diagnostics[key] = float(value)
        candidate.ramp_metering[mid] = spec['ramps'][mid]['service_by_green_veh_h'][str(int(value))]
    return prepare_control(candidate, cfg)


def candidate_from_services(incumbent, actual_reference, cfg, services):
    """Decode exact service-table coordinates, without allocation or rounding."""
    if not enabled(cfg) or set(services) != set(cfg.network.physical_ramp_branches['ramps']):
        raise ValueError('Exactly eight physical service coordinates required')
    greens={}
    for mid,row in cfg.network.physical_ramp_branches['ramps'].items():
        value=services[mid]
        if type(value) not in (int,float) or not math.isfinite(value):
            raise ValueError('Finite physical service required: '+mid)
        matches=[int(g) for g,rate in row['service_by_green_veh_h'].items() if value==rate]
        if len(matches)!=1:
            raise ValueError('Service coordinate has no unique physical green: '+mid)
        greens[mid]=matches[0]
    return candidate_from_greens(incumbent,actual_reference,cfg,greens)


def leader_seed_domain(controller, state, forecast, historical, *, check_budget=None, np_only=False):
    """Explicit seeds from both installed meter neighborhoods, before scoring.

    Keep all installed NP proposals. Cross both complete one-owner meter seed
    sets; the follower's full green/offset/VSL/meter neighborhoods are unchanged.
    Each seed's NUF is measured lazily from its accepted-flow response BEFORE
    its game starts, then frozen. Unvisited quantities stay unknown, not zero.
    This is a structural eight-ramp domain migration, not a speed-equivalent
    replacement of the legacy four-group service-budget domain.
    """
    from itertools import product
    from evaluation.controllers.joint_owner_neighbors import _physical_meter_points
    from evaluation.controllers.area_follower_objective import shared_query_runtime_scope
    private, state, forecast, anchor = copy.deepcopy(
        (controller, state, forecast, held_actual_reference(historical, controller.cfg)))
    with shared_query_runtime_scope():
        raw = tuple(private.leader.candidates(state, anchor.copy(), forecast=forecast))
    np_values = tuple(dict.fromkeys(float(a.N_P_star) for a in raw))
    if not np_values or any(not math.isfinite(v) for v in np_values):
        raise ValueError('Physical leader requires finite installed NP proposals')
    if np_only:
        # SDMPC owns its explicit green coordinates. Enumerating the legacy
        # service-rate seeds here would require an unnecessary, nonunique
        # inverse when several greens share the same saturated service rate.
        return {'schema':'joint-leader-np-domain/v1', 'np_values':np_values,
            'objective_queries':0, 'leader_target_selected':False,
            'scope':'Installed NP proposals only; caller owns the physical command search.'}
    groups = []
    for owner in private.cfg.network.freeway_links:
        points, mode, budget, proof = _physical_meter_points(private.nash_solver, owner, anchor, anchor)
        if mode != 'none' or budget is not None:
            raise ValueError('Physical leader cannot inherit a service-sum budget')
        groups.append(points)
    candidates = []
    for index, pair in enumerate(product(*groups)):
        if check_budget: check_budget('physical_leader_seeds')
        services = {r:v for _,rates in pair for r,v in rates.items()}
        control = candidate_from_services(anchor, anchor, private.cfg, services)
        rows = physical_commands(control, private.cfg)
        for np_value in np_values:
            action = control.copy(); action.N_P_star = np_value
            candidates.append({'control':action, 'target_np_veh':np_value,
                'target_nuf_veh_h':None, 'requires_merge_prediction':True,
                'directional_budgets':{}, 'meter_bank_index':index,
                'physical_meter_rows':copy.deepcopy(rows)})
    return {'schema':'joint-leader-realized-domain/v1', 'candidates':candidates,
        'candidate_count':len(candidates), 'np_values':np_values,
        'quantity_semantics':'predicted_accepted_mainline_merge',
        'objective_queries':0, 'leader_target_selected':False,
        'scope':'All installed NP caps crossed with the product of both physical meter seed neighborhoods; NUF measured from each seed before its fixed-target game. Unvisited seeds remain unknown. No directional service-sum shares.'}


def physical_commands(control, cfg, *, actuation=None, mapping=None):
    if not enabled(cfg):
        return None
    spec = cfg.network.physical_ramp_branches
    if mapping is not None and mapping.get('ramp_meters') != spec['writer_mapping']:
        raise ValueError('Physical ramp writer mapping changed after model configuration')
    if actuation is not None:
        settings = actuation.get('real_world_ramp_metering', {})
        if (not settings.get('enabled') or settings.get('cycle_sec') != spec['cycle_sec']
                or settings.get('amber_sec') != 0):
            raise ValueError('Physical ramp execution cycle/enabled state differs from model')
        if 'diagnostic_green_sec' in settings:
            override = settings['diagnostic_green_sec']
            if set(override)-set(spec['ramps']) or any(control.diagnostics['rw_meter_green_'+mid] != override.get(mid,spec['cycle_sec']) for mid in spec['ramps']):
                raise ValueError('Late diagnostic meter override differs from scored physical green')
    checked = prepare_control(control.copy(), cfg)
    return {mid:{'sc_no':float(row['sc_no']), 'sg_no':float(row['sg_no']),
        'rate_vph':checked.diagnostics['rw_meter_green_'+mid]*row['capacity_vph']/row['cycle_sec'],
        'group_rate_vph':checked.ramp_metering[mid],
        'green_sec':float(checked.diagnostics['rw_meter_green_'+mid]), 'model_ramp_key':mid}
        for mid,row in cfg.network.physical_ramp_branches['ramps'].items()}


def predicted_merge_quantity(response, cfg, *, start_sec, end_sec):
    """Count accepted physical merge flow over a complete, explicit window."""
    if not enabled(cfg):
        raise ValueError('Predicted eight-ramp merge requires physical branches')
    if any(type(value) not in (int,float) or not math.isfinite(value) for value in (start_sec,end_sec)):
        raise ValueError('Finite explicit physical merge window required')
    rows = cfg.network.physical_ramp_branches['ramps']
    values = {mid:[] for mid in rows}
    cursor = start_sec
    for frame in response['freeway_frames']:
        if frame['start_sec'] != cursor or frame['end_sec'] <= cursor or frame['end_sec'] > end_sec:
            raise ValueError('Missing/overlapping physical merge window')
        flows = frame['actual_ramp_release_veh_h']
        if set(flows) != set(rows):
            raise ValueError('Actual merge flow must retain all eight branches')
        for mid, flow in flows.items():
            if type(flow) not in (int,float) or not math.isfinite(flow) or flow < 0:
                raise ValueError('Invalid accepted physical merge flow')
            values[mid].append(flow*(frame['end_sec']-cursor)/3600)
        cursor = frame['end_sec']
    if cursor != end_sec or end_sec <= start_sec:
        raise ValueError('Incomplete physical merge horizon')
    vehicles = {mid:math.fsum(v) for mid,v in values.items()}
    rates = {mid:v*3600/(end_sec-start_sec) for mid,v in vehicles.items()}
    return {'schema':'predicted-physical-ramp-merge/v1', 'start_sec':start_sec,'end_sec':end_sec,
        'accepted_vehicles_by_ramp':vehicles,'rate_veh_h_by_ramp':rates,
        'rate_veh_h_by_owner':{owner:math.fsum(rates[mid] for mid,r in rows.items() if r['to_model_link']==owner) for owner in ('FW_E','FW_W')},
        'total_rate_veh_h':math.fsum(rates.values()),'boundary':'ramp_to_mainline',
        'omega_ttd':False,'leader_target_inherited':False}


def checked_merge_rates(quantity, cfg, *, start_sec, end_sec):
    """Validate the compact quantity transported with its bound response."""
    if not enabled(cfg) or not isinstance(quantity,dict):
        raise ValueError('Explicit physical predicted-merge quantity required')
    if any(type(v) not in (int,float) or not math.isfinite(v) for v in (start_sec,end_sec)):
        raise ValueError('Finite physical merge window required')
    if (quantity.get('schema') != 'predicted-physical-ramp-merge/v1'
            or quantity.get('boundary') != 'ramp_to_mainline'
            or quantity.get('start_sec') != start_sec or quantity.get('end_sec') != end_sec
            or quantity.get('omega_ttd') is not False or quantity.get('leader_target_inherited') is not False
            or end_sec <= start_sec):
        raise ValueError('Physical merge definition/window mismatch')
    rows=cfg.network.physical_ramp_branches['ramps']
    vehicles=quantity.get('accepted_vehicles_by_ramp',{})
    rates=quantity.get('rate_veh_h_by_ramp',{})
    if set(vehicles) != set(rows) or set(rates) != set(rows):
        raise ValueError('Physical merge quantity requires all eight branches')
    for mid in rows:
        if any(type(v) not in (int,float) or not math.isfinite(v) or v < 0 for v in (vehicles[mid],rates[mid])):
            raise ValueError('Invalid physical accepted-merge quantity')
        if rates[mid] != vehicles[mid]*3600/(end_sec-start_sec):
            raise ValueError('Physical merge rate does not match its accepted vehicles/window')
    owners={owner:math.fsum(rates[mid] for mid,row in rows.items() if row['to_model_link']==owner) for owner in ('FW_E','FW_W')}
    if quantity.get('rate_veh_h_by_owner') != owners or quantity.get('total_rate_veh_h') != math.fsum(rates.values()):
        raise ValueError('Physical merge total/owner aggregates mismatch')
    return dict(rates), owners
