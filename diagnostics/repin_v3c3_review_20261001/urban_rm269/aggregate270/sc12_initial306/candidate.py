"""Diagnostic initial composition repair; existing arrival times are retained.

Current paused records are consumed only at assimilation. The forecast keeps
aggregate movement tags in the existing parent reservation, not vehicle agents.
"""
from copy import deepcopy
import math
import xml.etree.ElementTree as ET

SOURCE = 'SC11_to_SC12'
LINK = '1220012103'
MOVEMENTS = {
    'SC12_W_SC11_to_E_SC106': '10241',
    'SC12_W_SC11_to_N_SC6': '10242',
    'SC12_W_SC11_to_S_SC16': '10243',
}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def project(state, cfg, raw, frame, network_bytes, inside, lane_queue):
    """Return a private initial state; reject unsupported or repeated projection."""
    from evaluation.controllers.area_runtime import model_inventory
    from evaluation.controllers.control_area_objective import get_ledger
    from src.models.urban_queue_model import approach_routing
    require(frame.get('schema') == 'lane-plant-frame/v1' and frame.get('complete') is True,
            'Complete current route frame required')
    require(raw['sim_sec'] == frame['time_s'] == state.time_sec,
            'Route and stock snapshots must have the same current time')
    records = raw['vehicle_records']
    require(records['complete'] is True and all(records[k] == state.time_sec for k in
            ('paused_at_sim_sec', 'capture_sim_sec_before', 'capture_sim_sec_after')),
            'Physical records must be complete and paused')
    physical = [v for v in records['records'] if str(v['link_no']) == LINK]
    current = {v[0]: v for v in frame['vehicles'] if str(v[1]) == LINK}
    require(len(current) == len(physical) and set(current) == {v['veh_no'] for v in physical},
            'Current frame IDs differ from physical records')
    for v in physical:
        r = current[v['veh_no']]
        require(r[2] == v['lane_no'] and abs(r[3]-v['position_m']) < 1e-8
                and abs(r[4]-v['speed_kph']) < 1e-8, 'Route frame geometry differs')
    require(SOURCE not in getattr(state, 'gate_initial_route_tags', {}), 'Source already tagged')
    require(SOURCE not in getattr(cfg.network, 'physical_gate_travel', {}), 'Source has another owner')
    require(hasattr(cfg.network, 'physical_ramp_branches'), 'Existing tag consumer required')
    support = state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link'][LINK]
    allowed = {'storage:'+SOURCE, *('movement:'+m for m in MOVEMENTS)}
    require(set(support) <= allowed and abs(sum(support.values())-len(physical)) < 1e-8,
            'Physical provenance does not cover the current subset')
    root = ET.fromstring(network_bytes)
    links = {n.get('no'): n for n in root.findall('./links/link')}
    geometry = {}
    routing = dict(approach_routing(cfg)[SOURCE])
    require(set(routing) == set(MOVEMENTS), 'Origin movement catalog changed')
    for m, connector in MOVEMENTS.items():
        require(cfg.network.urban_movements[m]['origin'] == SOURCE, 'Wrong movement owner')
        node = links[connector]; start = node.find('fromLinkEndPt')
        link, lane = start.get('lane').split()
        require(link == LINK, 'Connector leaves another physical link')
        geometry[m] = (float(start.get('pos')), set(range(int(lane), int(lane)+len(node.findall('./lanes/lane')))))
    ready = set()
    for lane in {v['lane_no'] for v in physical}:
        count = lane_queue.get((LINK, str(lane)), 0.)
        require(count == int(count), 'Fractional observed queue membership')
        front = sorted((v for v in physical if v['lane_no'] == lane), key=lambda v: -v['position_m'])[:int(count)]
        require(len(front) == count and all(v['stopped'] for v in front), 'Contiguous queue not reproducible')
        ready.update(v['veh_no'] for v in front)
    require(abs(len(ready)-sum(support.get('movement:'+m, 0.) for m in MOVEMENTS)) < 1e-8,
            'Queue total differs from physical projection')
    residual = len(physical)-len(ready)
    require(abs(residual-support.get('storage:'+SOURCE, 0.)) < 1e-8, 'Residual provenance differs')
    arrival = state.urban_arrival_buffer.get(SOURCE, {})
    require(arrival == state.urban_storage_release_buffer.get(SOURCE, {}),
            'Current arrival and release must have a paired reservation')
    step, parent = None, sum(arrival.values())
    # All observed vehicles can already be queued. There is then no moving
    # cohort to tag, and no reason to invent an arrival reservation for it.
    residual_due = {}
    if residual:
        require(all(n >= 0 and k*cfg.simulation.T_u_sec > state.time_sec for k,n in arrival.items()),
                'Residual requires future nonnegative paired reservations')
        if len(arrival) == 1:
            step = next(iter(arrival))
            residual_due = {v['veh_no']:step for v in physical if v['veh_no'] not in ready}
        else:
            # Native initialization first reserves +15/+105 seconds on its
            # 1s clock, then coarsens by ceiling to the urban10s clock. Preserve
            # those two distinct cohorts; never merge stopped stock into moving.
            now = int(round(state.time_sec/cfg.simulation.T_u_sec))
            steps = {stopped:now+math.ceil(tau/cfg.simulation.T_u_sec)
                     for stopped,tau in ((False,15.),(True,105.))}
            require(set(arrival) <= set(steps.values()), 'Unreviewed initial reservation timing')
            residual_due = {v['veh_no']:steps[bool(v['stopped'])]
                            for v in physical if v['veh_no'] not in ready}
        require(all(sum(due == k for due in residual_due.values()) <= arrival.get(k,0.)+1e-8
                    for k in set(residual_due.values())), 'Residual exceeds pending parent')
    queues = dict.fromkeys(MOVEMENTS, 0.); tags = {}; calendar_tags = {}; details = []
    for v in physical:
        r = current[v['veh_no']]
        selected = None
        if all(x is not None for x in r[6:9]):
            require(r[8] == 'STATIC', 'Unsupported current route type')
            dec, route = str(int(r[6])), str(int(r[7]))
            d = root.find(f"./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no='{dec}']")
            rn = d.find(f"./vehRoutSta/vehicleRouteStatic[@no='{route}']") if d is not None else None
            require(rn is not None, 'Observed route absent from current network')
            path = [d.get('link'), *[x.get('key') for x in rn.findall('./linkSeq/intObjectRef')], rn.get('destLink')]
            require(path.count(LINK) == 1 and path.index(LINK)+1 < len(path), 'Ambiguous current route position')
            connector = path[path.index(LINK)+1]
            selected = next((m for m,c in MOVEMENTS.items() if c == connector), None)
            require(selected is not None and (r[9] is None or int(r[9]) == int(connector)), 'Route and next link conflict')
            require(v['position_m'] <= geometry[selected][0]+1e-6, 'Known turn lies behind vehicle')
            choices = {selected: 1.}
        else:
            require(all(x is None for x in r[6:10]), 'Partially missing route cannot be imputed')
            choices = {m: b for m,b in routing.items() if v['lane_no'] in geometry[m][1]
                       and v['position_m'] <= geometry[m][0]+1e-6}
        total = sum(choices.values())
        require(math.isfinite(total) and total > 0, 'No supported current lane choices')
        weights = {m:b/total for m,b in choices.items()}
        target = queues if v['veh_no'] in ready else tags
        for m,b in weights.items(): target[m] = target.get(m, 0.)+b
        if v['veh_no'] not in ready:
            bucket = calendar_tags.setdefault(residual_due[v['veh_no']],{})
            for m,b in weights.items():bucket[m] = bucket.get(m,0.)+b
        details.append(dict(vehicle=v['veh_no'], lane=v['lane_no'], ready=v['veh_no'] in ready,
                            known=selected is not None, weights=weights))
    require(abs(sum(queues.values())-len(ready)) < 1e-8 and abs(sum(tags.values())-residual) < 1e-8,
            'Projection must conserve current queue and residual separately')
    ledger = get_ledger(state)
    require(type(inside) is bool and ledger.event_count == 0 and ledger.ttt_veh_h == 0
            and not ledger.captures_response, 'Only initial assimilation may relabel ledger stocks')
    side = 'inside' if inside else 'outside'
    for m in MOVEMENTS:
        require(ledger.stocks['movement:'+m][side]+queues[m]-support.get('movement:'+m,0.) >= -1e-8,
                'Insufficient physical cohort in ledger')
    result = deepcopy(state)
    summary = result.local_observation_summary
    new_support = summary['projection_diagnostics']['physical_stock_assignment_by_link'][LINK]
    for m,n in queues.items():
        delta = n-support.get('movement:'+m,0.)
        result.urban_movement_queue[m] += delta
        summary['urban_movement_queue'][m] += delta
        new_support['movement:'+m] = n
        get_ledger(result).stocks['movement:'+m][side] += delta
    if residual:
        result.gate_initial_route_tags[SOURCE] = calendar_tags
    get_ledger(result).assert_stocks(model_inventory(result,cfg))
    receipt = dict(source=SOURCE, physical_link=LINK, at_sec=state.time_sec,
        queue_before={m:support.get('movement:'+m,0.) for m in MOVEMENTS}, queue_after=queues,
        tagged_residual=tags, due_step=step, due_sec=step*cfg.simulation.T_u_sec if step is not None else None,
        parent_veh=parent, untouched_parent_veh=parent-residual, vehicles=details,
        tagged_residual_by_step=calendar_tags,
        unchanged_arrival_release=True, future_observation_inputs=False,
        unknown_rule='Current lane feasible movements; normalized existing beta, not observed destination')
    return result, receipt
