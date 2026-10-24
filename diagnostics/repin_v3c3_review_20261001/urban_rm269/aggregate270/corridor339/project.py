"""Current SC109 aggregate arrival/route projection over all physical owners.

Uses the existing317 path catalog and native-input lane/head partitions. A
legacy shared ownership fraction is retained explicitly; it is not a claim
about which individual vehicle belongs to that source. No future observation.
"""
from evaluation.controllers.calibrated_initial_projection import initial_calendar as _repair_initial_calendar
from collections import defaultdict
from copy import deepcopy
import math
import xml.etree.ElementTree as ET

from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc109_initial320 import candidate as timing
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc109_routes321 import candidate as routes
from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.transfer331.inputs import validate

TARGET = timing.TARGET
STORAGE = 'storage:' + TARGET


def catalog(cfg):
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc109_transport317.candidate import geometry
    g = getattr(cfg.network, 'sc109_transport317', None) or geometry(cfg)
    paths = {}
    for item in g['sources'].values():
        for full in item['paths']:
            for index, link in enumerate(full):
                suffix = full[index:]
                if suffix not in paths.setdefault(link, []):
                    paths[link].append(suffix)
    return paths


def route_weights(row, vehicle, root, routing, paths):
    connector = str(vehicle['link_no'])
    selected = next((m for m,c in routes.MOVEMENTS.items() if c == connector),None)
    if selected is not None:
        # Occupied turn connectors identify the turn even without a later route.
        weights,known,path = routes.current_weights(row,vehicle,root,routing)
        if known and weights != {selected:1.}:
            raise ValueError('Occupied SC109 connector conflicts with current route')
        return {selected:1.},True,path
    if str(vehicle['link_no']) in timing.LINKS:
        return routes.current_weights(row, vehicle, root, routing)
    if all(x is None for x in row[6:10]):
        return dict(routing), False, None
    if any(x is None for x in row[6:9]) or row[8] != 'STATIC':
        raise ValueError('Partial or unsupported current route')
    decision = root.find(f"./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no='{int(row[6])}']")
    route = decision.find(f"./vehRoutSta/vehicleRouteStatic[@no='{int(row[7])}']") if decision is not None else None
    if route is None:
        raise ValueError('Current native route missing')
    full = [decision.get('link'), *[x.get('key') for x in route.findall('./linkSeq/intObjectRef')], route.get('destLink')]
    link = str(vehicle['link_no'])
    if full.count(link) != 1:
        raise ValueError('Current path location ambiguous')
    suffix = full[full.index(link):]
    if row[9] is not None and (len(suffix) < 2 or suffix[1] != str(int(row[9]))):
        raise ValueError('Current next connector disagrees with native route')
    if '173' in suffix:
        return routes.current_weights(row, vehicle, root, routing)
    if not any(path[:len(suffix)] == suffix for path in paths.get(link, [])):
        raise ValueError('Current route does not lead along the reviewed corridor')
    # The currently selected route ends before the later SC109 route decision.
    return dict(routing), False, full


def owned_residual(cfg, raw, link, residual, support):
    from evaluation.controllers.native_internal_input import record_partition, _signal_authority
    partitions, proof = record_partition(cfg, raw)
    if link in partitions:
        _, authority = _signal_authority(cfg, proof[link]['input_no'])
        selected = []
        for vehicle in residual:
            lane = str(vehicle['lane_no'])
            pos = authority['head_position_by_lane_m'][lane]
            owner = authority['pre_head_storage'] if vehicle['position_m'] <= pos else authority['post_head_storage']
            if owner == TARGET:
                selected.append((vehicle, 1.))
        if abs(len(selected)-support.get(STORAGE, 0.)) > 1e-8:
            raise ValueError('Native head/position partition differs from stock provenance')
        return selected, 'exact_current_native_head_partition'
    count = support.get(STORAGE, 0.)
    if not residual:
        if count:
            raise ValueError('Owned stock has no physical records')
        return [], 'empty'
    fraction = count/len(residual)
    if not 0 <= count <= len(residual)+1e-8:
        raise ValueError('Invalid existing fractional ownership')
    whole = abs(count-len(residual)) <= 1e-8
    if not whole and any(n > 0 and k.startswith('movement:') for k,n in support.items()):
        raise ValueError('Ambiguous ownership of shared ready queues')
    return [(v, fraction) for v in residual if fraction], ('whole_source' if whole else 'retained_aggregate_ownership_fraction')


def distance(vehicle, next_link, paths, links, stop):
    link = str(vehicle['link_no'])
    if link in timing.LINKS:
        return timing.remaining_distance(vehicle, next_link, links, stop)
    from evaluation.controllers.route_choice_corridor import _length, _validate_path, _travel_segments
    choices = []
    for path in paths[link]:
        if next_link is not None and (len(path) < 2 or next_link != path[1]):
            continue
        _validate_path(path, links)
        pieces = _travel_segments(path, links, {k: _length(links[k]) for k in path}, stop)
        position = vehicle['position_m']
        if not 0 <= position <= pieces[0]['stop']+1e-6:
            raise ValueError('Current position lies beyond the reviewed physical path')
        pieces[0]['start'] = position
        choices.append((math.fsum(x['stop']-x['start'] for x in pieces), path))
    if not choices:
        raise ValueError('No reviewed continuation for current connector')
    return min(choices)


def post_head_geometry(root, links):
    heads = {}
    for h in root.findall('./signalHeads/signalHead'):
        link,lane = h.get('lane').split()
        if link == '173' and h.get('sg').split()[0] == '109':
            heads[int(lane)] = min(heads.get(int(lane),float('inf')),float(h.get('pos')))
    if not heads:raise ValueError('SC109 receiving heads missing')
    for connector in routes.MOVEMENTS.values():
        node = links[connector];start = node.find('fromLinkEndPt')
        link,first = start.get('lane').split()
        lanes = range(int(first),int(first)+len(node.findall('./lanes/lane')))
        if link != '173' or any(lane not in heads or float(start.get('pos')) < heads[lane] for lane in lanes):
            raise ValueError('SC109 turn connector is not downstream of its lane head')
    return heads,set(routes.MOVEMENTS.values())


def install(cfg, state, raw, frame, network, lane_queues):
    from evaluation.controllers.area_runtime import model_inventory
    from evaluation.controllers.control_area_objective import get_ledger
    from src.models.urban_queue_model import approach_routing
    import hashlib

    validate(raw, frame, state.time_sec)
    if cfg.simulation.T_f_sec != 5 or cfg.simulation.T_u_sec != 10 or hashlib.sha256(network).hexdigest() != timing.NETWORK_SHA:
        raise ValueError('Reviewed network and5/10 clocks required')
    if TARGET in getattr(state, 'gate_initial_route_tags', {}) or TARGET in getattr(cfg.network, 'physical_gate_travel', {}):
        raise ValueError('Initial source already has another arrival/tag owner')
    ledger = get_ledger(state)
    if ledger.event_count or ledger.ttt_veh_h or ledger.captures_response:
        raise ValueError('Only initial assimilation can relabel queues')
    provenance = state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
    relevant = {STORAGE, *('movement:'+m for m in routes.MOVEMENTS)}
    owners = {link for link, row in provenance.items() if any(row.get(k, 0.) for k in relevant)}
    paths = catalog(cfg)
    root = ET.fromstring(network)
    links = {x.get('no'):x for x in root.findall('./links/link')}
    heads,post_connectors = post_head_geometry(root,links)
    if not owners <= set(paths)|post_connectors:
        raise ValueError('Unreviewed SC109 owner: '+str(owners-set(paths)-post_connectors))
    stop = min(heads.values())
    current = {int(r[0]):r for r in frame['vehicles']}
    routing = dict(approach_routing(cfg)[TARGET])
    if set(routing) != set(routes.MOVEMENTS) or abs(sum(routing.values())-1)>1e-10:
        raise ValueError('SC109 movement catalog changed')
    old = _repair_initial_calendar(state,cfg,TARGET)
    if old != state.urban_storage_release_buffer.get(TARGET,{}):
        raise ValueError('Initial calendars are not paired')
    expected, calendar, tags = defaultdict(float), defaultdict(float), {}
    assigned, details, ownership = {}, [], {}
    dt = cfg.simulation.T_u_sec
    now = int(round(state.time_sec/dt))
    for link in sorted(owners):
        rows = [v for v in raw['vehicle_records']['records'] if str(v['link_no']) == link]
        support = provenance[link]
        if abs(sum(support.values())-len(rows))>1e-8:
            raise ValueError('Physical records do not cover existing link stocks')
        qn = sum(support.get('movement:'+m, 0.) for m in routes.MOVEMENTS)
        if any(n for k,n in support.items() if k.startswith('movement:') and k not in relevant):
            raise ValueError('Another signal owns part of this ready queue')
        ready = set()
        if qn:
            for lane in {v['lane_no'] for v in rows}:
                n = lane_queues.get((link,str(lane)),0.)
                front = sorted((v for v in rows if v['lane_no']==lane),key=lambda v:-v['position_m'])[:int(n)]
                if n != int(n) or len(front)!=n or any(not v['stopped'] for v in front):
                    raise ValueError('Current contiguous ready queue does not match')
                ready.update(v['veh_no'] for v in front)
        if abs(len(ready)-qn)>1e-8:
            raise ValueError('Ready queue ownership mismatch')
        residual, rule = owned_residual(cfg,raw,link,[v for v in rows if v['veh_no'] not in ready],support)
        ownership[link] = dict(source_vehicles=sum(w for _,w in residual), rule=rule,
                               other_owners={k:n for k,n in support.items() if k not in relevant})
        mean = sum(v['speed_kph'] for v in rows)/len(rows) if rows else timing.SPEED_FLOOR_KPH
        assigned[link] = dict.fromkeys(routes.MOVEMENTS,0.)
        for vehicle, fraction in [(v,1.) for v in rows if v['veh_no'] in ready]+residual:
            row = current[vehicle['veh_no']]
            weights, known, native_path = route_weights(row,vehicle,root,routing,paths)
            is_ready = vehicle['veh_no'] in ready
            if is_ready:
                for movement, weight in weights.items():
                    assigned[link][movement] += fraction*weight
                continue
            legacy = now+math.ceil((105 if vehicle['stopped'] else 15)/dt)
            expected[legacy] += fraction
            nxt = str(int(row[9])) if row[9] is not None else None
            receiving = heads[int(vehicle['lane_no'])] if link == '173' else stop
            post_head = link in post_connectors or (link == '173' and vehicle['position_m'] > receiving+1e-6)
            if post_head:
                due, remaining, path = legacy, None, [link]
            else:
                remaining, path = distance(vehicle,nxt,paths,links,receiving)
                due = timing.arrival_step(remaining,vehicle['speed_kph'],mean,state.time_sec,dt)
            calendar[due] += fraction
            if known:
                bucket = tags.setdefault(due,{})
                for movement, weight in weights.items():
                    bucket[movement] = bucket.get(movement,0.)+fraction*weight
            details.append(dict(vehicle=vehicle['veh_no'],link=link,owned_vehicles=fraction,
                lane=vehicle['lane_no'],position_m=vehicle['position_m'],physical_path=path,
                old_due_sec=legacy*dt,new_due_sec=due*dt,remaining_m=remaining,
                current_route=row[6:9],native_path=native_path,known_sc109_turn=known,
                post_head_owner_retained=post_head,receiving_head_m=receiving))
        if abs(sum(assigned[link].values())-qn)>1e-8:
            raise ValueError('Queue relabeling lost vehicles')
    if any(abs(expected.get(k,0.)-old.get(k,0.))>1e-8 for k in set(expected)|set(old)):
        raise ValueError('Weighted current cohorts do not reproduce original reservations')
    if abs(sum(calendar.values())-sum(old.values()))>1e-8:
        raise ValueError('Arrival retiming lost source stock')
    if any(sum(row.values())>calendar.get(k,0.)+1e-8 for k,row in tags.items()):
        raise ValueError('Known route tags exceed parent reservation')
    result = deepcopy(state)
    result.urban_arrival_buffer[TARGET] = dict(sorted(calendar.items()))
    result.urban_storage_release_buffer[TARGET] = dict(sorted(calendar.items()))
    for link, row in assigned.items():
        side = 'inside' if routes.membership()[0][link] else 'outside'
        for movement, n in row.items():
            key = 'movement:'+movement
            delta = n-provenance[link].get(key,0.)
            if delta:
                result.urban_movement_queue[movement] += delta
                result.local_observation_summary['urban_movement_queue'][movement] += delta
                result.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link'][link][key] = n
                get_ledger(result).stocks[key][side] += delta
    result.gate_initial_route_tags[TARGET] = tags
    get_ledger(result).assert_stocks(model_inventory(result,cfg))
    for side in ('inside','outside'):
        if abs(sum(v[side] for v in ledger.stocks.values())-sum(v[side] for v in get_ledger(result).stocks.values()))>1e-8:
            raise ValueError('Projection changed area ownership')
    return result, dict(source=TARGET,at_sec=state.time_sec,ownership=ownership,
        old_calendar=old,new_calendar=dict(sorted(calendar.items())),tagged_arrivals=tags,vehicles=details,
        source_vehicles=sum(calendar.values()),known_residual_vehicles=sum(sum(v.values()) for v in tags.values()),
        physical_conservation=True,new_fits=0,future_observation_inputs=False,
        limitations=['Shared non-native partitions retain existing aggregate ownership fractions; vehicle identity is not inferred.',
                     'Post-head173/10285/10286 source ownership and reservations remain unchanged; downstream reassignment is not claimed.',
                     'Unselected later SC109 routes stay unknown; existing beta applies only on arrival.'])
