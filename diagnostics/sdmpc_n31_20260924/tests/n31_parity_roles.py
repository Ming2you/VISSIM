"""T3/T3b roles, each run in its own fresh interpreter (python -B n31_parity_roles.py <role> <dir>).

parent: the adapter's parent sequence for the freeway plant. Build the v2
        component from the reference config (its module hooks first, as
        load_sources does), then configure_freeway_runtime(full cfg) as
        configure_runtime does (RS:105), bind the refined kernels
        (_bind_refined) and copy their FD rows into the full cfg (LPR:436).
        Step both roads 450 s through the aggregate branch
        (_freeway_substep_events, exogenous releases/capacities, no ledger)
        and pickle everything a worker receives.
worker: a fresh interpreter that only unpickles the payload and reinstalls the
        worker freeway hooks from the full cfg (install_freeway_runtime(cfg, None),
        the freeway part of install_worker_runtime, RS:263), then steps the same
        inputs. It also re-derives the A1 blocks from the pickled cfg and reads
        every refined cell's VSL through the pickled per-road configs.
The test compares the two result files.
"""
from __future__ import annotations

import copy
import json
import pickle
import sys
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for extra in (HERE, ROOT, ROOT / 'vendor/NumSim-mine'):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

T0 = 900.0
STEPS = 450
VSL = {'FW_E__seg10': 80.0, 'FW_W__seg5': 80.0}
ZONE_VALUES = {0: 101.0, 5: 102.0, 10: 103.0, 15: 104.0}


def inputs(component):
    return {'source': {'FW_E': 6000.0, 'FW_W': 4000.0},
            'ramp': {r: 700.0 for r in component.ramps}, 'cap': {o: 1800.0 for o in component.offramps},
            'split': {o: 0.12 for o in component.offramps}, 'vsl': dict(VSL)}


def initial(confs):
    from evaluation.controllers import area_freeway_accounting as acc
    out = {}
    for road, conf in confs.items():
        lanes = conf.network.freeway_segment_lanes[road]
        lengths = acc.cell_lengths_km(conf, road, len(lanes))
        rho = [12.0 + (7 * i) % 34 for i in range(len(lanes))]
        out[road] = {'n': [r * l * w for r, l, w in zip(rho, lengths, lanes)], 'v': [95.0 - r for r in rho]}
    return out


def step_all(confs, init, boundary):
    from evaluation.controllers import area_freeway_accounting as acc
    from src.models.state import TrafficState, ControlAction
    from src.models.demand import DemandStep
    out = {}
    for road, conf in confs.items():
        cfg = copy.deepcopy(conf)
        net = cfg.network
        lanes = net.freeway_segment_lanes[road]
        n = len(lanes)
        lengths = acc.cell_lengths_km(cfg, road, n)
        state = TrafficState.initial(cfg)
        state.time_sec = T0
        state.freeway_effective_lanes[road] = list(lanes)
        state.freeway_density[road] = [init[road]['n'][c] / (lengths[c] * lanes[c]) for c in range(n)]
        state.freeway_speed[road] = list(init[road]['v'])
        state.mainline_origin_queue[road] = 0.0
        state.urban_link_storage = dict(net.urban_link_storage_veh)
        control = ControlAction.uncontrolled(cfg)
        control.vsl.update(boundary['vsl'])
        rows = []
        for _ in range(STEPS):
            releases = {r: boundary['ramp'][r] for r in net.ramps}
            caps = {o: boundary['cap'][o] for o in net.off_ramps}
            net.off_ramp_split_ratio = {o: boundary['split'][o] for o in net.off_ramps}
            demand = DemandStep({road: boundary['source'][road]}, {}, {})
            ttt, diagnostic = acc._freeway_substep_events(
                state, control, demand, cfg, offramp_capacity_veh_h=caps, ramp_release_veh_h=releases,
                ramp_release_diagnostics={'total_no_meter_flow': sum(releases.values()), 'mean_ramp_receiving_factor': 1.0},
                update_ramp_queues=False, include_ramp_queue_ttt=False, complete_allocator_scope=False)
            state.time_sec += cfg.simulation.T_f_sec
            rows.append([float(ttt), *map(float, state.freeway_density[road]), *map(float, state.freeway_speed[road]),
                         float(state.mainline_origin_queue[road]),
                         *(float(diagnostic['offramp_flow_' + o]) for o in sorted(caps))])
        out[road] = rows
    return out


def vsl_reads(confs):
    from src.models import state as st
    from src.models.state import ControlAction
    reads = {}
    for road, conf in confs.items():
        control = ControlAction.uncontrolled(conf)
        control.vsl = {road: 33.0, **{f'{road}__seg{h}': v for h, v in ZONE_VALUES.items()}}
        reads[road] = [st.segment_vsl(control, road, c, conf) for c in range(len(conf.network.freeway_segment_lanes[road]))]
    return reads


def a1_record(cfg):
    """The C4(i) record LPR stores on the full cfg, from a fixed observation."""
    from evaluation.controllers import obs150_contract as oc
    from evaluation.controllers import source_boundary as sb
    import n31_fixtures as fx
    schedules = fx.calibration_schedules()
    native = {'schema': 'native-input-schedule/v1', 'freeway_link_by_input': {'1098': 'FW_E', '1099': 'FW_W'},
              'inputs': {no: {'schedule': [{'start_sec': r.start_sec, 'rate_veh_h': r.vph} for r in schedules[road]]}
                         for no, road in (('1098', 'FW_E'), ('1099', 'FW_W'))}}
    observation = {'information_cutoff_s': int(T0), 'source_boundary': {}}
    for road, (window, cum) in (('FW_E', (260, 1900)), ('FW_W', (160, 1100))):
        integral = oc.schedule_integral_veh(schedules[road], 0.0, T0)
        observation['source_boundary'][road] = {
            'admitted_window': window, 'admitted_cum': cum, 'interval_s': 150, 'recent_vph': 24.0 * window,
            'schedule_integral_veh': integral, 'backlog_veh': max(0.0, integral - cum)}
    net = cfg.network
    net.native_input_schedule = native
    net.lane_plant_enabled = True
    net.lane_plant_sources = {'source_boundary': dict(oc.SOURCE_BOUNDARY_BLOCK)}
    net.freeway_source_boundary_observed = sb.observed_block(observation, sb.road_schedules(native))
    return sb.demand_blocks(cfg, T0, 5)


def parent(folder):
    import n31_fixtures as fx
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from evaluation.controllers import runtime_setup
    from evaluation.controllers import lane_plant_runtime as lpr
    from evaluation.controllers.freeway_refined_geometry import parents
    from src.models.demand import DemandStep
    component = fx.component()
    tuning = fx.build_full_tuning()
    mapping = json.loads((fx.ROOT / tuning['mapping_json']).read_text(encoding='utf-8-sig'))
    cfg = adapter.build_config(fx.ROOT / 'vendor/NumSim-mine', 150.0, 9000.0, 'normal', {}, tuning,
                               local_observation=True, flagship=True)
    runtime_setup.configure_freeway_runtime(adapter, cfg, tuning, mapping)
    params = fx.parameters()['by_direction']
    confs = {road: component._config(road, params[road]) for road in component.roads}
    geometry = fx.load_json(fx.GEOMETRY)
    context = {'parents': parents(geometry), 'geometry': geometry, 'component': component,
               'document': {'vsl_command_space': 'parent_21'}}
    cells = {r: [c for c in geometry['cells'] if c['road'] == r] for r in component.roads}
    state = types.SimpleNamespace(time_sec=int(T0), freeway_density={r: [20.0] * 31 for r in cells},
                                  freeway_speed={r: [80.0] * 31 for r in cells},
                                  freeway_effective_lanes={r: [c['lane_km'] / c['length_km'] for c in cells[r]] for r in cells},
                                  freeway_flow={})
    rows_before = {road: len(cfg.network.freeway_segment_params[road]) for road in component.roads}
    binding = lpr._bind_refined(context, {'offramp_10643_lane_shares': [0.5, 0.5]}, cfg, state,
                                types.SimpleNamespace(configs=confs))
    for road, conf in confs.items():
        cfg.network.freeway_segment_params[road] = copy.deepcopy(conf.network.freeway_segment_params[road])
    rows_after = {road: len(cfg.network.freeway_segment_params[road]) for road in component.roads}
    blocks = a1_record(cfg)
    demand = [DemandStep({road: blocks[road][i] for road in blocks}, {}, {}) for i in range(5)]
    boundary = inputs(component)
    init = initial(confs)
    payload = {'cfg': cfg, 'confs': confs, 'init': init, 'inputs': boundary, 'demand': demand}
    (folder / 'payload.pickle').write_bytes(pickle.dumps(payload, protocol=pickle.HIGHEST_PROTOCOL))
    result = {'rollout': step_all(confs, init, boundary), 'vsl_reads': vsl_reads(confs),
              'head_of_cell': {r: c.network.freeway_vsl_zone_head_of_cell[r] for r, c in confs.items()},
              'binding_head_of_cell': binding['vsl_zone_head_of_cell'],
              'full_cfg_fd_rows_before_bind': rows_before, 'full_cfg_fd_rows_after_bind': rows_after,
              'a1_blocks': blocks}
    (folder / 'parent.json').write_text(json.dumps(result), encoding='utf-8')


def worker(folder):
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from evaluation.controllers import runtime_setup
    from evaluation.controllers import source_boundary as sb
    payload = pickle.loads((folder / 'payload.pickle').read_bytes())
    cfg = payload['cfg']
    runtime_setup.install_freeway_runtime(adapter, cfg, None)
    confs = payload['confs']
    blocks = sb.demand_blocks(cfg, T0, len(payload['demand']))
    received = [{road: step.freeway_mainline[road] for road in step.freeway_mainline} for step in payload['demand']]
    result = {'rollout': step_all(confs, payload['init'], payload['inputs']), 'vsl_reads': vsl_reads(confs),
              'head_of_cell': {r: c.network.freeway_vsl_zone_head_of_cell[r] for r, c in confs.items()},
              'full_cfg_fd_rows': {r: len(cfg.network.freeway_segment_params[r]) for r in confs},
              'a1_blocks': blocks, 'demand_received': received}
    (folder / 'worker.json').write_text(json.dumps(result), encoding='utf-8')


if __name__ == '__main__':
    role, folder = sys.argv[1], Path(sys.argv[2])
    {'parent': parent, 'worker': worker}[role](folder)
    print('N31_PARITY_ROLE_OK ' + role)
