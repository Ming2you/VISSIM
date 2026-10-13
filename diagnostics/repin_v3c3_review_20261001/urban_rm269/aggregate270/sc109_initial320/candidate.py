"""Timing-only diagnostic of the current SC109 residual stock; no future input."""
from collections import defaultdict
from pathlib import Path
import copy
import hashlib
import math
import pickle
import xml.etree.ElementTree as ET

TARGET = 'SC108_to_SC109'
LINKS = {'173', '174', '10280', '10281', '10285'}
NETWORK_SHA = '64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc'
# Claude U7a / existing kinematic-projection rule, declared before forecasts.
SPEED_FLOOR_KPH = 20.


def arrival_step(distance_m, speed_kph, mean_kph, now, dt):
    values = (distance_m, speed_kph, mean_kph, now, dt)
    if not all(math.isfinite(x) for x in values) or min(values[:4]) < 0 or dt <= 0:
        raise ValueError('Invalid current geometry, speed or time')
    eta = distance_m / (max(speed_kph, mean_kph, SPEED_FLOOR_KPH) / 3.6)
    return int(round(now / dt)) + max(1, math.ceil(eta / dt))


def remaining_distance(vehicle, next_link, links, stop):
    from evaluation.controllers.route_choice_corridor import _length, _validate_path, _travel_segments
    link = str(vehicle['link_no'])
    pos = vehicle['position_m']
    if link == '173':
        paths = [[link]]
    elif link in ('10280', '10281'):
        if next_link not in (None, '173'):
            raise ValueError('Current connector route does not enter SC109')
        paths = [[link, '173']]
    elif link == '174':
        if next_link is not None:
            if next_link not in ('10280', '10281'):
                raise ValueError('Unknown current connector on SC109 corridor')
            connectors = [next_link]
        else:
            connectors = []
            for key in ('10280', '10281'):
                start = links[key].find('fromLinkEndPt')
                first = int(start.get('lane').split()[1])
                lanes = range(first, first + len(links[key].findall('./lanes/lane')))
                if vehicle['lane_no'] in lanes:
                    connectors.append(key)
        if not connectors:
            raise ValueError('Current lane has no supported physical connector')
        paths = [['174', key, '173'] for key in connectors]
    else:
        raise ValueError('Post-head ownership must be explicitly retained, not sent backwards')
    choices = []
    for path in paths:
        _validate_path(path, links)
        pieces = _travel_segments(path, links, {k: _length(links[k]) for k in path}, stop)
        if pos > pieces[0]['stop'] + 1e-6 or pos < 0:
            raise ValueError('Observed vehicle passed the candidate receiving point')
        pieces[0]['start'] = pos
        distance = math.fsum(x['stop'] - x['start'] for x in pieces)
        choices.append((distance, path))
    return min(choices)


def install(cfg, state, raw, frame, network, lane_queues):
    """Only replace paired ETA calendars; retain queues, beta and all stock owners."""
    dt = cfg.simulation.T_u_sec
    records = raw['vehicle_records']
    if (dt != 10 or cfg.simulation.T_f_sec != 5 or not records.get('complete')
            or not frame.get('complete') or raw['sim_sec'] != state.time_sec
            or frame['time_s'] != state.time_sec
            or records['capture_sim_sec_before'] != state.time_sec
            or records['capture_sim_sec_after'] != state.time_sec):
        raise ValueError('Complete, simultaneous current state and FW5/U10 required')
    if hashlib.sha256(network).hexdigest() != NETWORK_SHA:
        raise ValueError('Unreviewed physical geometry')
    if getattr(state, 'gate_initial_route_tags', {}).get(TARGET):
        raise ValueError('Cannot retime an existing tagged owner implicitly')
    before = {k: pickle.dumps(v, protocol=5) for k, v in vars(state).items()}
    provenance = state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
    owners = {k for k, support in provenance.items() if support.get('storage:' + TARGET, 0) > 0}
    if not owners <= LINKS:
        raise ValueError('Initial corridor has uncovered physical owners')
    tree = ET.fromstring(network)
    links = {x.get('no'): x for x in tree.findall('./links/link')}
    stop = min(float(x.get('pos')) for x in tree.findall('./signalHeads/signalHead')
               if x.get('lane').split()[0] == '173' and x.get('sg').split()[0] == '109')
    frames = {int(v[0]): v for v in frame['vehicles']}
    selected = [v for v in records['records'] if str(v['link_no']) in LINKS]
    if len({v['veh_no'] for v in selected}) != len(selected):
        raise ValueError('Duplicate current vehicle')
    residual = []
    ready_ids = set()
    means = {}
    for link in sorted(LINKS):
        rows = [v for v in selected if str(v['link_no']) == link]
        support = provenance.get(link, {})
        if abs(math.fsum(support.values()) - len(rows)) > 1e-7:
            raise ValueError('Current physical stock does not cover original owners')
        expected_q = math.fsum(n for k, n in support.items() if k.startswith('movement:'))
        ready = set()
        if expected_q:
            for lane in {v['lane_no'] for v in rows}:
                n = lane_queues.get((link, str(lane)), 0.)
                front = sorted((v for v in rows if v['lane_no'] == lane), key=lambda v: -v['position_m'])[:int(n)]
                if n != int(n) or len(front) != n or any(not v['stopped'] for v in front):
                    raise ValueError('Cannot identify original contiguous queue')
                ready.update(v['veh_no'] for v in front)
        if abs(len(ready) - expected_q) > 1e-7:
            raise ValueError('Ready queue differs from original projection')
        rest = [v for v in rows if v['veh_no'] not in ready]
        if abs(len(rest) - support.get('storage:' + TARGET, 0.)) > 1e-7:
            raise ValueError('Residual differs from source-owned stock')
        ready_ids.update(ready)
        residual.extend(rest)
        means[link] = math.fsum(v['speed_kph'] for v in rows) / len(rows) if rows else SPEED_FLOOR_KPH
    old = dict(state.urban_arrival_buffer.get(TARGET, {}))
    if old != state.urban_storage_release_buffer.get(TARGET, {}):
        raise ValueError('Initial arrival/release calendars are not paired')
    expected = defaultdict(float)
    calendar = defaultdict(float)
    receipt = []
    for v in residual:
        link = str(v['link_no'])
        row = frames[v['veh_no']]
        if (int(row[1]) != int(link) or int(row[2]) != v['lane_no']
                or abs(row[3] - v['position_m']) > 1e-6 or abs(row[4] - v['speed_kph']) > 1e-6):
            raise ValueError('Current route/lane frame and stock record differ')
        legacy = int(round(state.time_sec / dt)) + math.ceil((105 if v['stopped'] else 15) / dt)
        expected[legacy] += 1
        next_link = str(int(row[9])) if row[9] is not None else None
        if link == '10285':
            # Existing projection owns this post-head vehicle in the source.
            # Keep its reservation, rather than silently removing/reassigning it.
            step, distance, path = legacy, None, [link]
        else:
            distance, path = remaining_distance(v, next_link, links, stop)
            step = arrival_step(distance, v['speed_kph'], means[link], state.time_sec, dt)
        calendar[step] += 1
        receipt.append(dict(vehicle=v['veh_no'], link=link, lane=v['lane_no'], position_m=v['position_m'],
                            speed_kph=v['speed_kph'], link_mean_kph=means[link], current_next_link=next_link,
                            current_route=row[6:9], physical_path=path, remaining_m=distance,
                            old_due_sec=legacy*dt, new_due_sec=step*dt, post_head_retained=link == '10285'))
    if dict(expected) != old or sum(calendar.values()) != sum(old.values()):
        raise ValueError('Initial reservation has another cohort or loses mass')
    state.urban_arrival_buffer = copy.deepcopy(state.urban_arrival_buffer)
    state.urban_storage_release_buffer = copy.deepcopy(state.urban_storage_release_buffer)
    state.urban_arrival_buffer[TARGET] = dict(sorted(calendar.items()))
    state.urban_storage_release_buffer[TARGET] = dict(sorted(calendar.items()))
    changed = {k for k, v in vars(state).items() if pickle.dumps(v, protocol=5) != before[k]}
    if changed != {'urban_arrival_buffer', 'urban_storage_release_buffer'}:
        raise ValueError('Timing-only candidate altered another state field')
    return dict(source=TARGET, time_sec=state.time_sec, changed_fields=sorted(changed),
                ready_queue_veh=len(ready_ids), residual_veh=len(residual), old_calendar=old,
                new_calendar=dict(sorted(calendar.items())), vehicles=receipt, speed_floor_kph=SPEED_FLOOR_KPH,
                future_observation_inputs=False, composition_unchanged=True,
                limitations=['Original beta and ready-queue movement composition retained; not corrected by this timing ablation.',
                             'Original post-head10285 owner/reservation retained explicitly.',
                             'Current-speed point-queue ETA; no future stop duration or signal-dependent bonus.'])
