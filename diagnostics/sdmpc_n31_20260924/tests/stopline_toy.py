"""Toy SC1001 EB fixtures for the K8-6 stopline approach (SA) module tests.

Synthetic cfg/state/evidence with the deployed names and the spec 1.9 values;
no capture, adapter run, rollout or VISSIM. `drive` replays the UFA/LOR order
of one urban second (amendment 2.3) around the SA hooks, so module tests and
the tangent probe subprocess exercise the same sequence. Imported by the probe
after the tangent Finder is installed, so it must not import src.models at
module import time (all model imports are inside functions).
"""
from __future__ import annotations

import math
import types

E, S, N = 'SC1001_W_to_E_SC1002', 'SC1001_W_to_S_SC1003', 'SC1001_W_to_N_SC2002'
ONE, ONW = 'SC1001_W_to_onE', 'SC1001_W_to_onW'
IN = 'in_SC1001_W'
RECV = {E: 'SC1001_to_SC1002', S: 'SC1001_to_SC1003', N: 'SC1001_to_SC2002'}
HEADS = {1: 621.666240433568, 2: 621.5682806829368, 3: 621.461546643362}
SAT = {1: 2030.9375, 2: 1581.7040358744396, 3: 2101.923076923077}
OBSERVED = {1: 81.0, 2: 63.0, 3: 621.461546643362 / 6.0}
P1 = 0.5240301626237849
EXIT129 = 301.926
LANDING = {'10491': ('129', 239.38422422843928), '10481': ('127', 210.27144602258932)}
OFF_BETA = {'E': 0.7193087723508941, 'N': 0.20904836193447737, 'S': 0.07164286571462858, 'W_RAMP': 0.0}
GATE_BETA = {E: 0.107895, N: 0.031365000000000004, S: 0.01074, ONE: 0.223560998727537, ONW: 0.6264390012724629}
CAPS = {IN: 1237.8, 'SC1001_to_SC1002': 400.0, 'SC1001_to_SC1003': 400.0, 'SC1001_to_SC2002': 400.0,
        'OR_D_W_storage': 38.582370152536015, 'OR_D_E_storage': 151.4720025513158,
        'SC1001_R_E': 100.0, 'SC1001_R_W': 100.0, 'SC1001_W_out': 100.0}
GREENS = {'SC1001_p1': 46.0, 'SC1001_p2': 23.0, 'SC1001_p3': 45.0, 'SC1001_p4': 24.0}


class ToyNetwork(types.SimpleNamespace):
    def signal_cycle_length(self, signal):
        return self.cycle_length


def evidence(**changes):
    lanes = {str(l): {'members': list(('E', 'S') if l == 1 else ('E',) if l == 2 else ('N',)),
                      'phase': 'SC1001_p4' if l == 3 else 'SC1001_p3', 'head_pos_m': HEADS[l],
                      's_veh_h_lane': SAT[l],
                      'storage_veh': {'geometric': HEADS[l] / 6.0, 'observed_full': OBSERVED[l]}}
             for l in (1, 2, 3)}
    approach = {
        'signal': 'SC1001', 'stopline_link': '127', 'receiver': IN,
        'members': {'E': E, 'S': S, 'N': N}, 'lanes': lanes, 'p_lane1_given_E': P1,
        'upstream_lane_prior': {'1': {'E': 0.62523, 'N': 0.00394, 'S': 0.37083},
                                '2': {'E': 0.99248, 'N': 0.00731, 'S': 0.00021},
                                '3': {'E': 0.15476, 'N': 0.83036, 'S': 0.01488}},
        'posthead_lane_prior': {'1': {'E': 5768 / 6850, 'S': 1082 / 6850},
                                '2': {'E': 5239 / 5280, 'S': 41 / 5280}, '3': {'N': 1.0}},
        'posthead_connectors': {'10118': {'from_lanes': [1, 2], 'receiver': 'SC1001_to_SC1002'},
                                '10368': {'from_lanes': [1], 'receiver': 'SC1001_to_SC1003'},
                                '10695': {'from_lanes': [3], 'receiver': 'SC1001_to_SC2002'}},
        'posthead_rehome': {'10695': 'SC1001_to_SC2002'},
        'pre_stopline_links': ['32', '10778', '129', '10777', '127'],
        'ports': {'10491': {'off_ramp': 'OR_D_W', 'landing': list(LANDING['10491']),
                            'distance_m': {str(l): EXIT129 - LANDING['10491'][1] + HEADS[l] for l in (1, 2, 3)}},
                  '10481': {'off_ramp': 'OR_D_E', 'landing': list(LANDING['10481']),
                            'distance_m': {str(l): HEADS[l] - LANDING['10481'][1] for l in (1, 2, 3)}}},
        'd1117_m': 228.91967281006077, 'tail129_from_m': 239.38422422843928, 'link10777_m': 1.001500000142622,
        'port_progress_route': {'1132:2': 'OR_D_W'},
        'route_exit': {'1117:3': 'E', '1117:1': 'S', '1117:2': 'N'},
        'init_origin_routes': {'1132:2': 'port', '1131:2': 'port', '1136:2': 'city', '1117': 'unknown'},
        'speed_floor_kmh': 20.0, 'jam_spacing_m': 6.0}
    approach.update(changes)
    return {'schema': 'stopline-approach-evidence/v2',
            'inputs': {'g2_inpx': {'sha256': '69d4a5b5', 'extract_sha12': '910bc37a8d69'}},
            'approaches': {'SC1001_EB': approach}}


def section(storage='observed_full', sha='0' * 64, path='diagnostics/x.json'):
    return {'schema': 'stopline-approach/v2', 'evidence': {'path': path, 'sha256': sha},
            'approaches': ['SC1001_EB'], 'lane_model': 'lane_fifo', 'storage': storage,
            'merge_rule': 'zipper', 'city_admission': 'unconditional', 'origin_tags': 'report'}


def movements():
    out = {}
    for name in (E, N, S, ONE, ONW):
        ramp = {ONE: 'RM_C10490', ONW: 'RM_C10482'}.get(name)
        out[name] = {'kind': 'boundary_in', 'origin': IN, 'beta': GATE_BETA[name],
                     'phase': 'SC1001_p4' if name == N else 'SC1001_p3',
                     'receiving_link': RECV.get(name, {ONE: 'SC1001_R_E', ONW: 'SC1001_R_W'}.get(name)),
                     'destination': 'x', 'ramp': ramp, 'unsignalized': True if ramp else None}
    for tag, off in (('offW', 'OR_D_W'), ('offE', 'OR_D_E')):
        for dest, target in (('E_SC1002', 'SC1001_to_SC1002'), ('N_SC2002', 'SC1001_to_SC2002'),
                             ('S_SC1003', 'SC1001_to_SC1003'), ('W_RAMP', 'SC1001_W_out')):
            out[f'SC1001_{tag}_to_{dest}'] = {'kind': 'off_ramp', 'origin': off, 'off_ramp': off,
                                              'beta': OFF_BETA['W_RAMP' if dest == 'W_RAMP' else dest[0]], 'phase': 'SC1001_p3',
                                              'receiving_link': target, 'destination': 'x', 'ramp': None}
    return out


def routes_table():
    table = {}
    for name in (E, S, N, ONE, ONW):
        table['arrival:' + name] = {'target_inside': True, 'inside_to_inside': 1.0, 'outside_to_inside': 1.0}
    for name in (E, S):
        table['movement:' + name] = {'status': 'unique', 'source_inside': True, 'target_inside': True,
                                     'inside_to_inside': 1.0, 'outside_to_inside': 1.0}
    table['movement:' + N] = {'status': 'unique', 'source_inside': True, 'target_inside': False,
                              'inside_to_inside': 0.0, 'outside_to_inside': 0.0,
                              'outward_crossings_per_vehicle': 1, 'inward_crossings_per_vehicle': 0}
    return table


def config(*, routes=True):
    net = ToyNetwork(
        urban_movements=movements(), urban_link_storage_veh=dict(CAPS), urban_stopline_storage_veh={},
        boundary_queue_max_veh=100.0, urban_avg_vehicle_length_m=6.0, urban_avg_speed_km_h=50.0,
        num_phases=4, lost_time=12.0, cycle_length=150.0, movement_capacity_veh_h=1400.0,
        movement_capacity_by_movement_veh_h={},
        off_ramp_storage_link={'OR_D_W': 'OR_D_W_storage', 'OR_D_E': 'OR_D_E_storage'},
        off_ramp_to_movement={'OR_D_W': [m for m in movements() if m.startswith('SC1001_offW')],
                              'OR_D_E': [m for m in movements() if m.startswith('SC1001_offE')]},
        physical_ramp_branches={'shared_city_arrival': {'receiver': 'in_SC1004_W'}})
    if routes:
        net.control_area_routes = routes_table()
    sim = types.SimpleNamespace(T_u_h=1.0 / 3600.0, T_u_sec=1.0)
    return types.SimpleNamespace(network=net, simulation=sim,
                                 urban_follower=types.SimpleNamespace(receiving_space_rule='proportional'))


def control(greens=None, offset=0.0):
    return types.SimpleNamespace(green_times=dict(GREENS if greens is None else greens),
                                 offsets={'SC1001': offset})


def offramp_rows():
    return {
        '10491': {'id': 'OR_D_W_signal', 'group': 'OR_D_W', 'branch': 'signal', 'connector': 10491, 'from_link': 26,
                  'to_link': 129, 'to_pos_m': LANDING['10491'][1], 'length_m': 231.4942209152161, 'lanes': 1,
                  'storage_capacity_veh': CAPS['OR_D_W_storage'], 'storage': 'OR_D_W_storage', 'direct': False,
                  'target': None, 'local_upstream': False},
        '10481': {'id': 'OR_D_E_signal', 'group': 'OR_D_E', 'branch': 'signal', 'connector': 10481, 'from_link': 2,
                  'to_link': 127, 'to_pos_m': LANDING['10481'][1], 'length_m': 454.41600765394736, 'lanes': 2,
                  'storage_capacity_veh': CAPS['OR_D_E_storage'], 'storage': 'OR_D_E_storage', 'direct': False,
                  'target': None, 'local_upstream': False}}


def state(cfg, t0, *, cohorts=None):
    """Lane plant pieces SA reads: storages, queues, buffers and the two real DelayedPorts."""
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.canonical_harness import DelayedPort
    from evaluation.controllers.lane_offramp_runtime import LaneOfframpRuntime
    rows = offramp_rows()
    cohorts = cohorts or {}
    ports = {off: DelayedPort(row['storage_capacity_veh'], row['length_m'], 60.0, cohorts.get(off, []), t0,
                              interval_service=True) for off, row in rows.items()}
    lor = LaneOfframpRuntime(ports, rows, None, {'10491': True, '10481': True, '129': True, '127': True})
    storage = dict(CAPS)
    for off, row in rows.items():
        storage[row['storage']] = row['storage_capacity_veh'] - ports[off].stock
    return types.SimpleNamespace(
        time_sec=float(t0), urban_link_storage=storage,
        urban_movement_queue={m: 0.0 for m in cfg.network.urban_movements},
        urban_arrival_buffer={}, urban_storage_release_buffer={}, urban_link_speed_kph={}, ramp_queue={},
        local_observation_summary={'projection_diagnostics': {'physical_stock_assignment_by_link': {}}},
        lane_offramp_runtime=lor)


def bare(t0=120, *, arm='observed_full', cohorts=None, speed_kmh=30.0, cfg=None):
    """Configured view + bound ports + empty index (no initialize): dynamics tests."""
    from evaluation.controllers import stopline_approach as SA
    cfg = cfg or config()
    cfg.network.stopline_approach = SA.build_view(cfg, section(arm), evidence(), 'f' * 64)
    st = state(cfg, t0, cohorts=cohorts)
    SA._bind_ports(st, cfg, cfg.network.stopline_approach)
    st.stopline_approach_state = SA._new_state(cfg.network.stopline_approach)
    st.stopline_approach_state['speed_kmh'] = speed_kmh
    return cfg, st


def add_ready(st, cfg, lane, member, amount, step, source='init:city'):
    from evaluation.controllers import stopline_approach as SA
    s = st.stopline_approach_state
    packet = SA._insert(s, lane, step, source, member, amount)
    s['stock'][lane] = s['stock'][lane] + amount
    st.urban_movement_queue[member] = st.urban_movement_queue[member] + amount
    return packet


def add_moving(st, cfg, lane, member, amount, due, source='init:port'):
    from src.models import urban_queue_model as uqm
    from evaluation.controllers import stopline_approach as SA
    s = st.stopline_approach_state
    packet = SA._insert(s, lane, due, source, member, amount)
    s['stock'][lane] = s['stock'][lane] + amount
    tags = s['tags'].setdefault(due, {})
    tags[(lane, member, source)] = tags.get((lane, member, source), 0.0) + amount
    uqm._schedule(st.urban_arrival_buffer, IN, due, amount)
    uqm._schedule(st.urban_storage_release_buffer, IN, due, amount)
    st.urban_link_storage[IN] = st.urban_link_storage[IN] - amount
    return packet


def inventory(st, cfg):
    net = cfg.network
    out = {'storage:' + k: net.urban_link_storage_veh[k] - st.urban_link_storage[k] for k in net.urban_link_storage_veh}
    out.update({'movement:' + m: q for m, q in st.urban_movement_queue.items()})
    return out


def attach_ledger(st, cfg, *, capture=False):
    from evaluation.controllers.control_area_objective import ModelAreaLedger
    from evaluation.controllers.sdmpc_dual import primal
    stocks = {k: {'inside': primal(v), 'outside': 0.0} for k, v in inventory(st, cfg).items()}
    st._control_area_ledger = ModelAreaLedger(stocks, capture_response=capture)
    return st._control_area_ledger


def drive(st, cfg, ctl, step, *, landing=None, gate=0.0, checks=True):
    """One urban second in UFA order around the SA hooks; returns (end_step diagnostics, record)."""
    from src.models import urban_queue_model as uqm
    from evaluation.controllers import stopline_approach as SA
    from evaluation.controllers import urban_flow_accounting as ufa
    from evaluation.controllers.control_area_objective import emit_transfer, get_ledger
    from evaluation.controllers.lane_urban_runtime import _debit_stock
    net = cfg.network
    spec = SA.view(cfg)
    ledger = get_ledger(st)
    if ledger is not None:
        ledger.begin_response_step('urban', step, step + 1)
    record = {'arrived': {}, 'released': {}, 'departed': {}, 'counted': {}}
    released = uqm._pop_buffer(st.urban_storage_release_buffer, IN, step)
    if released > 0.0:
        st.urban_link_storage[IN] = min(CAPS[IN], st.urban_link_storage[IN] + released)
    routing = uqm.approach_routing(cfg)
    arrived = uqm._pop_buffer(st.urban_arrival_buffer, IN, step)
    for movement, amount in SA.split_arrival(st, cfg, step, arrived, routing[IN]):
        st.urban_movement_queue[movement] += amount
        record['arrived'][movement] = amount
        emit_transfer(st, cfg, 'storage:' + IN, 'movement:' + movement, amount, route_key='arrival:' + movement)
    if gate > 0.0:
        for movement, beta in routing[IN]:
            st.urban_movement_queue[movement] += beta * gate
            if movement in spec['members']:
                SA.enqueue_city(st, cfg, movement, beta * gate, step)
            emit_transfer(st, cfg, None, 'movement:' + movement, beta * gate, source_inside=True,
                          target_inside=True)
    lor = st.lane_offramp_runtime
    for off, port in lor.ports.items():
        row = lor.descriptions[off]
        key = row['storage']
        requests = [SA.allocate(st, cfg, step, off, port)]
        limit = math.fsum(x[2] for x in requests)
        actual = port.release(step, 1., limit * 3600.)
        if actual > limit + 1e-7:
            raise ArithmeticError('toy port exceeded its limit')
        for _movement, target, amount, _service, _room in requests:
            n = amount * actual / limit if limit else 0.
            if n <= 0:
                continue
            st.urban_link_storage[key] += n
            st.urban_link_storage[target] = _debit_stock(st.urban_link_storage[target], n)
            SA.land_release(st, cfg, step, off, n, routing)
            record['released'][off] = n
    specs = uqm.movement_specs(cfg)
    by_storage = {}
    for movement in specs:
        if movement in spec['members']:
            wanted = SA.intended(st, ctl, cfg, step)[movement]
            by_storage.setdefault(specs[movement]['receiving_link'], {})[movement] = wanted
    departures = {}
    for storage, wanted in by_storage.items():
        space = uqm._effective_available_space(st, cfg, storage)
        departures.update(uqm._allocate_receiving_counts('proportional', wanted, space))
    departures.update(SA.resolve(st, cfg, departures))
    for movement, departed in departures.items():
        if departed <= 0.0:
            continue
        before = st.urban_movement_queue.get(movement, 0.0)
        actual = min(before, departed)
        counted = SA.depart(st, cfg, movement, actual, step, specs[movement]['receiving_link'])
        st.urban_movement_queue[movement] = max(0.0, before - actual)
        ufa._post_service(st, cfg, movement, actual, step, routing, str(specs[movement].get('receiving_link', '')))
        record['departed'][movement] = actual
        record['counted'][movement] = counted
    diag = SA.end_step(st, cfg, step)
    for off, amount in (landing or {}).items():
        port = lor.ports[off]
        key = lor.descriptions[off]['storage']
        port.accept(step + 1, amount)
        st.urban_link_storage[key] = _debit_stock(st.urban_link_storage[key], amount)
        emit_transfer(st, cfg, None, 'storage:' + key, amount, source_inside=True, target_inside=True)
    if checks:
        lor.assert_mirrors(st, cfg)
        if ledger is not None:
            ledger.assert_stocks(inventory(st, cfg))
    return diag, record
