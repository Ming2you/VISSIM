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
        if (int(row['sc_no']) != meter['sc_no'] or row['metadata'].split(';')[0] != 'ok'
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


def leader_seed_domain(controller, state, forecast, historical, *, check_budget=None):
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
