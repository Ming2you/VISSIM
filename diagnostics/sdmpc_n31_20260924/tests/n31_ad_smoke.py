"""T9 (plan C11, N31 review B13) + the T2 tangent check, in an isolated instrumented process.

Run: python -B n31_ad_smoke.py <out.json>. Installs the forward tangent
instrumentation (sdmpc_tangent_runtime, as the SDMPC workers do) before any
model import, builds the v2 component from the reference config, binds the
parent-space VSL tables (_bind_refined) and steps the per-road kernels the way
LaneFreewayRuntime does (aggregate _freeway_substep_events).

Cases:
  merge_open_exit  FW_E, delta_merge 1 (AFA:363-366) and the open-exit terminal
                   (AFA:285-288): forward AD of total TTT and end vehicles w.r.t.
                   a FW_E ramp release, the FW_E source and the 10643 capacity
                   against central finite differences.
  vsl_anchor_max   Dual(110 = vsl_max) on FW_E__seg10 with the branch VSL model
                   (Carlson A0.5/E4 + exposure transport): the one-sided (left)
                   tangent, against left differences P(110) - P(110 - h) at h = 1, 2
                   and their Richardson extrapolation (h >= 1 clears the 0.5 gate).
                   FW_W has no fitted law: its 110 anchor stays a zero column.
  vsl_below_max    Dual(80) on FW_E__seg10: forward AD against the central
                   difference at h = 0.25 (both sides active Carlson).
  vsl_zone_reach   Dual(80) on FW_W__seg10, one step: speed tangents exactly on
                   the parent zone's refined cells 15-24.
"""
from __future__ import annotations

import copy
import json
import math
import sys
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for extra in (ROOT, ROOT / 'vendor/NumSim-mine'):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

from evaluation.controllers import sdmpc_tangent_runtime as runtime  # noqa: E402

FINDER = runtime.install(ROOT, 'forward')
ad = FINDER.ad

B110 = 'diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/res10_b110_20260923'
GEOMETRY = ROOT / ('diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/v3b_nc_20260925/'
                   'observations/s31_v3bnc_observations/geometry.json')   # = make_plant_n31.SOURCES['geometry']
PARAMETERS = ROOT / B110 / 'train_s31_v2nc/boundary_literature_v1/boundary_fit/parameters.json'
REFERENCE = ROOT / 'diagnostics/sdmpc_n31_20260924/reference_config_n31_v2.json'
T0 = 900.0


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def build():
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.canonical_harness import CanonicalFreewayModel
    from evaluation.controllers import lane_plant_runtime as lpr
    from evaluation.controllers.freeway_refined_geometry import parents
    geometry = load(GEOMETRY)
    component = CanonicalFreewayModel(geometry, REFERENCE)
    params = load(PARAMETERS)['parameters']['by_direction']
    confs = {road: component._config(road, params[road]) for road in component.roads}
    cells = {r: [c for c in geometry['cells'] if c['road'] == r] for r in component.roads}
    state = types.SimpleNamespace(time_sec=int(T0), freeway_density={r: [20.0] * 31 for r in cells},
                                  freeway_speed={r: [80.0] * 31 for r in cells},
                                  freeway_effective_lanes={r: [c['lane_km'] / c['length_km'] for c in cells[r]] for r in cells},
                                  freeway_flow={})
    cfg = types.SimpleNamespace(network=types.SimpleNamespace(
        freeway_variable_cell_lengths=True, freeway_vsl_zone_heads={'FW_E': [0, 5, 10, 15], 'FW_W': [0, 5, 10, 15]},
        freeway_vsl_zone_free=[0, 1, 2], freeway_segment_length_profile_km={}))
    context = {'parents': parents(geometry), 'geometry': geometry, 'component': component,
               'document': {'vsl_command_space': 'parent_21'}}
    lpr._bind_refined(context, {'offramp_10643_lane_shares': [0.5, 0.5]}, cfg, state,
                      types.SimpleNamespace(configs=confs))
    return component, confs


def rollout(conf, road, steps, *, rho, v, source, ramp, cap, vsl):
    from evaluation.controllers import area_freeway_accounting as acc
    from src.models.state import TrafficState, ControlAction
    from src.models.demand import DemandStep
    cfg = copy.deepcopy(conf)
    net = cfg.network
    lanes = net.freeway_segment_lanes[road]
    n = len(lanes)
    lengths = acc.cell_lengths_km(cfg, road, n)
    state = TrafficState.initial(cfg)
    state.time_sec = T0
    state.freeway_effective_lanes[road] = list(lanes)
    state.freeway_density[road] = [rho(i) for i in range(n)]
    state.freeway_speed[road] = [v(i) for i in range(n)]
    state.mainline_origin_queue[road] = 0.0
    state.urban_link_storage = dict(net.urban_link_storage_veh)
    control = ControlAction.uncontrolled(cfg)
    control.vsl.update(vsl)
    ttt = 0.0
    for _ in range(steps):
        releases = {r: ramp.get(r, 600.0) for r in net.ramps}
        caps = {o: cap.get(o, 1800.0) for o in net.off_ramps}
        net.off_ramp_split_ratio = {o: 0.12 for o in net.off_ramps}
        demand = DemandStep({road: source}, {}, {})
        cost, _ = acc._freeway_substep_events(
            state, control, demand, cfg, offramp_capacity_veh_h=caps, ramp_release_veh_h=releases,
            ramp_release_diagnostics={'total_no_meter_flow': 0.0, 'mean_ramp_receiving_factor': 1.0},
            update_ramp_queues=False, include_ramp_queue_ttt=False, complete_allocator_scope=False)
        ttt = ttt + cost
        state.time_sec += cfg.simulation.T_f_sec
    vehicles = sum(d * l * w for d, l, w in zip(state.freeway_density[road], lengths, lanes))
    return ttt, vehicles, list(state.freeway_speed[road])


def finite(value):
    if isinstance(value, ad.Dual):
        return math.isfinite(value.value) and all(math.isfinite(x) for x in value.tangent.values())
    return math.isfinite(value)


def merge_open_exit(component, confs):
    conf = confs['FW_E']
    net = conf.network
    ramps = sorted(r for r, p in component.ramps.items() if p['road'] == 'FW_E')
    ramp = ramps[0]
    base = dict(rho=lambda i: 18.0 + (5 * i) % 17, v=lambda i: 90.0, source=5200.0, ramp={ramp: 700.0},
                cap={'10643': 250.0}, vsl={})
    trace = ad.Trace([1.0, 1.0, 1.0], track_stencils=False)
    dual = dict(base, source=ad.Dual(5200.0, {0: 1.0}, trace), ramp={ramp: ad.Dual(700.0, {1: 1.0}, trace)},
                cap={'10643': ad.Dual(250.0, {2: 1.0}, trace)})
    ttt, vehicles, speeds = rollout(conf, 'FW_E', 450, **dual)
    checks = []
    # h = 0.01 veh/h: the 10643 capacity has a regime switch 1 veh/h above the
    # anchor (forward FD at h = 1 is off by 48%); central FD converges to AD below 0.1.
    for axis, key, h in ((0, 'source', 0.01), (1, 'ramp', 0.01), (2, 'cap', 0.01)):
        def shifted(sign):
            args = copy.deepcopy(base)
            if key == 'source':
                args['source'] += sign * h
            elif key == 'ramp':
                args['ramp'][ramp] += sign * h
            else:
                args['cap']['10643'] += sign * h
            return rollout(conf, 'FW_E', 450, **args)
        plus, minus = shifted(1.0), shifted(-1.0)
        for name, value, index in (('ttt', ttt, 0), ('vehicles', vehicles, 1)):
            fd = (plus[index] - minus[index]) / (2 * h)
            checks.append({'axis': key, 'output': name, 'ad': ad.derivative(value).get(axis, 0.0), 'fd': fd})
    return {'ramp': ramp, 'delta_merge': float(net.metanet_delta_merge),
            'terminal_capacity_is_open': (getattr(net, 'freeway_terminal_capacity_veh_h', {}) or {}).get('FW_E', 0.0) is None,
            'terminal_zero_gradient': bool(getattr(net, 'terminal_zero_gradient', False)),
            'source_capacity_is_admitted': (getattr(net, 'freeway_source_capacity_veh_h', {}) or {}).get('FW_E', 0.0) is None,
            'finite': finite(ttt) and finite(vehicles) and all(finite(s) for s in speeds), 'checks': checks}


VSL_CASE = dict(rho=lambda i: 22.0 + (7 * i) % 23, v=lambda i: 85.0, source=6800.0, ramp={}, cap={})


def vsl_column(conf, road, key, anchor, steps=300):
    trace = ad.Trace([1.0], track_stencils=False)
    ttt, vehicles, speeds = rollout(conf, road, steps, **VSL_CASE, vsl={key: ad.Dual(anchor, {0: 1.0}, trace)})
    return ttt, vehicles, speeds


def plain(conf, road, key, value, steps=300):
    ttt, vehicles, _ = rollout(conf, road, steps, **VSL_CASE, vsl={key: value})
    return ad.primal(ttt), ad.primal(vehicles)


def vsl_anchor_max(confs):
    conf = confs['FW_E']
    vsl_max = max(conf.freeway_follower.vsl_set)
    ttt, vehicles, speeds = vsl_column(conf, 'FW_E', 'FW_E__seg10', vsl_max)
    base = plain(conf, 'FW_E', 'FW_E__seg10', vsl_max)
    left = {h: plain(conf, 'FW_E', 'FW_E__seg10', vsl_max - h) for h in (1.0, 2.0)}
    checks = []
    for index, (name, value) in enumerate((('ttt', ttt), ('vehicles', vehicles))):
        d1 = (base[index] - left[1.0][index]) / 1.0
        d2 = (base[index] - left[2.0][index]) / 2.0
        checks.append({'output': name, 'ad': ad.derivative(value).get(0, 0.0), 'left_h1': d1, 'left_h2': d2,
                       'richardson': 2 * d1 - d2, 'primal': ad.primal(value), 'plain_110': base[index]})
    tangents = [ad.derivative(x).get(0, 0.0) for x in (ttt, vehicles, *speeds)]
    west = confs['FW_W']
    w_ttt, w_vehicles, w_speeds = vsl_column(west, 'FW_W', 'FW_W__seg10', vsl_max)
    west_tangents = [ad.derivative(x).get(0, 0.0) for x in (w_ttt, w_vehicles, *w_speeds)]
    return {'vsl_max': vsl_max, 'max_abs_tangent': max(abs(t) for t in tangents), 'checks': checks,
            'cells_with_tangent': [i for i, s in enumerate(speeds) if abs(ad.derivative(s).get(0, 0.0)) > 0.0],
            'west_max_abs_tangent': max(abs(t) for t in west_tangents),
            'finite': finite(ttt) and finite(vehicles) and all(finite(s) for s in speeds)}


def vsl_below_max(confs):
    conf = confs['FW_E']
    anchor, h = 80.0, 0.25
    ttt, vehicles, _ = vsl_column(conf, 'FW_E', 'FW_E__seg10', anchor)
    plus, minus = plain(conf, 'FW_E', 'FW_E__seg10', anchor + h), plain(conf, 'FW_E', 'FW_E__seg10', anchor - h)
    return {'anchor': anchor, 'checks': [{'output': name, 'ad': ad.derivative(value).get(0, 0.0),
                                          'fd': (plus[index] - minus[index]) / (2 * h)}
                                         for index, (name, value) in enumerate((('ttt', ttt), ('vehicles', vehicles)))]}


def vsl_zone_reach(confs):
    conf = confs['FW_W']
    trace = ad.Trace([1.0], track_stencils=False)
    _, _, speeds = rollout(conf, 'FW_W', 1, rho=lambda i: 10.0, v=lambda i: 100.0, source=3000.0, ramp={}, cap={},
                           vsl={'FW_W__seg10': ad.Dual(80.0, {0: 1.0}, trace)})
    return {'cells_with_tangent': [i for i, s in enumerate(speeds) if abs(ad.derivative(s).get(0, 0.0)) > 0.0]}


def vsl_unit(confs):
    """The two AD pieces of the port, checked in this instrumented process.

    law_left: literature_desired_speed at the inactive 110 anchor keeps the
      target value and carries d law/dc, equal to the one-sided difference of
      the (ungated) Carlson law itself.
    merge: same-valued cohorts from two command axes merge under one key with a
      mass-weighted zero-valued sensitivity (first-order exact).
    """
    from evaluation.controllers import freeway_fd as fd
    conf = confs['FW_E']
    spec = conf.network.freeway_vsl_fd_response['FW_E']
    trace = ad.Trace([1.0, 1.0], track_stencils=False)
    rows = []
    for cell in (10, 16):
        for rho in (10.0, 30.0, 45.0):
            target = 97.25
            value = fd.literature_desired_speed(spec, conf, 'FW_E', cell, rho, target,
                                                ad.Dual(110.0, {0: 1.0}, trace), False)
            h = 1e-6
            law = lambda c: fd._literature_speed(spec, conf, 'FW_E', cell, rho, c)
            rows.append({'cell': cell, 'rho': rho, 'value': ad.primal(value), 'target': target,
                         'ad': ad.derivative(value).get(0, 0.0), 'left_fd': (law(110.0) - law(110.0 - h)) / h,
                         'nominal_equals_law_at_110': law(110.0)})
    x = fd.VSLExposure([10.0, 10.0], dict(sign_cells=[0], initial_command=110.0, ramp_command=110.0), 110.0)
    x.advance([10.0, 10.0], [10.0, 10.0], [2.0], [2.0, 2.0], 2.0, [0.0, 0.0], [ad.Dual(110.0, {0: 1.0}, trace), 110.0])
    first = [{str(k): ad.derivative(v) for k, v in row.items()} for row in x.tangents]
    x.advance([10.0, 10.0], [10.0, 10.0], [2.0], [2.0, 2.0], 2.0, [0.0, 0.0], [ad.Dual(110.0, {1: 1.0}, trace), 110.0])
    second = [{str(k): ad.derivative(v) for k, v in row.items()} for row in x.tangents]
    return {'law_left': rows, 'merge_keys': [sorted(c) for c in x.cohorts],
            'merge_first': first, 'merge_second': second, 'cohorts': [{str(k): v for k, v in c.items()} for c in x.cohorts]}


def main(out):
    component, confs = build()
    result = {'instrumented': '_tangent_float' in vars(sys.modules['evaluation.controllers.area_freeway_accounting']),
              'merge_open_exit': merge_open_exit(component, confs), 'vsl_anchor_max': vsl_anchor_max(confs),
              'vsl_below_max': vsl_below_max(confs), 'vsl_unit': vsl_unit(confs),
              'vsl_zone_reach': vsl_zone_reach(confs)}
    Path(out).write_text(json.dumps(result, indent=1), encoding='utf-8')
    print('N31_AD_SMOKE_OK')


if __name__ == '__main__':
    main(sys.argv[1])
