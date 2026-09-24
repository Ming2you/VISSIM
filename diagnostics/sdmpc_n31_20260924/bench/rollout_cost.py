"""C0(a): 31-cell vs 21-cell freeway component cost on one 450 s rollout.

Early decision-time estimate without VISSIM (plan C0). The b110 boundary
component (the calibration's boundary_config.json with the boundary-family
parameters; physical_integration_step_sec 1) is built twice: on the refined
31-cell calibration geometry and on the 21 parents it was split from. Both roll
out the same 1 s history_forecast window (BF, the calibration's own step) from
the same observed state; the 21-cell initial state is the parent sum of the
31-cell counts (speed: vehicle-weighted mean).

The plant reference (reference_config_n31_v2.json) adds only the five
transport keys (ramp receiving nodes, residence, interval service): per-port
work that does not depend on the cell count, and a rollout with them needs the
explicit 1 s ramp buffers (canonical_harness:696-697). The kernel whose cost the
refinement changes is the same in both configs. Measured:

- primal wall time of CanonicalFreewayModel.rollout (both roads, 450 s)
- reverse-tape node count of the same rollout with two Dual axes (FW_E VSL zone
  2 command and RM_C10681 release), in an isolated instrumented process

This is the freeway component only. The SDMPC decision also contains the urban
and ramp/port models, which the refinement does not change, so the whole-
decision ratio is lower than the component ratio; section `decision_estimate`
scales only the freeway share by the measured ratio.

Run from the worktree root:
  python -B diagnostics/sdmpc_n31_20260924/bench/rollout_cost.py --observations <B110 s31_v2nc_observations> [--cutoff 2700.1]
  python -B diagnostics/sdmpc_n31_20260924/bench/rollout_cost.py --rescale --freeway-share S --freeway-share-source TEXT
    (decision_estimate only, from the measured blocks already in rollout_cost.json)
Writes bench/rollout_cost.json. Read only outside this folder.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

HERE = Path(__file__).resolve().parent
N31D = HERE.parent
CAL = 'diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1'
B110 = CAL + '/res10_b110_20260923'
GEOMETRY = ROOT / B110 / 'observations/s31_v2nc_observations/geometry.json'
PARAMETERS = ROOT / B110 / 'train_s31_v2nc/boundary_literature_v1/boundary_fit/parameters.json'
CONFIG = ROOT / B110 / 'train_s31_v2nc/boundary_literature_v1/boundary_config.json'
DEFAULT_OBSERVATIONS = Path(r'D:\VISSIM-merge\sim3') / B110 / 'observations/s31_v2nc_observations'


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def models():
    from diagnostics.demand_sweep.user_native_20260914.metanet_calibration_v1.canonical_harness import CanonicalFreewayModel
    from evaluation.controllers.freeway_refined_geometry import collapse_to_parents, parents
    refined = load_json(GEOMETRY)
    parent = collapse_to_parents(refined)
    return {31: CanonicalFreewayModel(refined, CONFIG),
            21: CanonicalFreewayModel(parent, CONFIG)}, parents(refined)


def window(observations, cutoff, horizon, step):
    sys.path.insert(0, str(ROOT / CAL))
    from boundary_factory import ObservationData, build_window
    data = ObservationData(observations)
    return build_window(data, cutoff, 'history_forecast', model_step_sec=step, horizon_sec=horizon)


def initial_cells(window_doc, table, cells):
    if cells == 31:
        return window_doc['initial_cells']
    out = []
    by_road = {}
    for row in window_doc['initial_cells']:
        by_road.setdefault(row['road'], []).append(row)
    for road, rows in by_road.items():
        rows = sorted(rows, key=lambda r: int(r['cell']))
        for p in range(21):
            members = [r for r, q in zip(rows, table[road]) if q == p]
            n = math.fsum(float(r['n_veh']) for r in members)
            weighted = [(float(r['n_veh']), float(r['v_kmh'])) for r in members
                        if r['v_kmh'] not in (None, '') and float(r['n_veh']) > 0]
            v = math.fsum(a*b for a, b in weighted)/math.fsum(a for a, _ in weighted) if weighted else None
            out.append({'time_s': members[0]['time_s'], 'road': road, 'cell': p, 'n_veh': n, 'v_kmh': v})
    return out


def zone_key(model, parent_head):
    heads = model.base.network.freeway_vsl_zone_heads['FW_E']
    # The component's own zone head for the requested parent zone (21: 10, 31: 14).
    cells = len(model.base.network.freeway_segment_lanes['FW_E'])
    return 'FW_E__seg%d' % (heads[[0, 5, 10, 15].index(parent_head)] if cells != 21 else parent_head)


def primal(args):
    built, table = models()
    step = int(built[31].base.simulation.T_f_sec)
    if step != int(built[21].base.simulation.T_f_sec):
        raise ValueError('Both components must integrate at the same step')
    doc = window(args.observations, args.cutoff, args.horizon, step)
    params = load_json(PARAMETERS)['parameters']
    result = {'model_step_sec': step}
    for cells, model in built.items():
        init = initial_cells(doc, table, cells)
        steps = copy.deepcopy(doc['boundary_steps'])
        key = zone_key(model, 10)
        for s in steps:
            s['vsl_commands'] = {key: 80.0}
        times = []
        for _ in range(args.repeats):
            t = time.perf_counter()
            out = model.rollout(init, steps, params, doc['initial_origin_queue'], horizon_sec=args.horizon)
            times.append(time.perf_counter() - t)
        end = [c for c in out['cells'] if abs(c['time_s'] - (args.cutoff + args.horizon)) < 1e-6]
        result[str(cells)] = {'rollout_wall_sec': times, 'min_sec': min(times), 'median_sec': statistics.median(times),
                              'cells_per_road': {r: len(model.base.network.freeway_segment_lanes[r]) for r in model.roads},
                              'end_vehicles': math.fsum(float(c['n_veh']) for c in end), 'vsl_key': key}
    result['ratio_min'] = result['31']['min_sec'] / result['21']['min_sec']
    result['ratio_median'] = result['31']['median_sec'] / result['21']['median_sec']
    return result


def tape_child(args):
    """Isolated instrumented process: node count of one taped rollout."""
    from evaluation.controllers import sdmpc_tangent_runtime as runtime
    finder = runtime.install(ROOT, 'reverse-v1')
    ad = finder.ad
    built, table = models()
    model = built[args.cells]
    doc = window(args.observations, args.cutoff, args.horizon, int(model.base.simulation.T_f_sec))
    params = load_json(PARAMETERS)['parameters']
    trace = ad.Trace([1.0, 1.0])
    steps = copy.deepcopy(doc['boundary_steps'])
    key = zone_key(model, 10)
    for s in steps:
        s['vsl_commands'] = {key: ad.Dual(80.0, {0: 1.0}, trace)}
        s['ramp_release_vph']['RM_C10681'] = ad.Dual(max(300.0, float(s['ramp_release_vph']['RM_C10681'])), {1: 1.0}, trace)
    t = time.perf_counter()
    out = model.rollout(initial_cells(doc, table, args.cells), steps, params, doc['initial_origin_queue'],
                        horizon_sec=args.horizon)
    wall = time.perf_counter() - t
    end = [c for c in out['cells'] if abs(c['time_s'] - (args.cutoff + args.horizon)) < 1e-6]
    total = sum(c['n_veh'] for c in end)
    print(json.dumps({'cells': args.cells, 'tape_nodes': len(trace.p1) - 1, 'taped_rollout_wall_sec': wall,
                      'end_vehicles': float(ad.primal(total))}))


def tape(args):
    out = {}
    for cells in (21, 31):
        command = [sys.executable, '-B', str(Path(__file__).resolve()), '--tape-child', str(cells),
                   '--observations', str(args.observations), '--cutoff', repr(args.cutoff),
                   '--horizon', str(args.horizon)]
        env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUTF8': '1'}
        done = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, timeout=3600)
        if done.returncode:
            out[str(cells)] = {'error': done.stderr[-2000:]}
            continue
        out[str(cells)] = json.loads(done.stdout.strip().splitlines()[-1])
    if all('tape_nodes' in out[k] for k in ('21', '31')):
        out['node_ratio'] = out['31']['tape_nodes'] / out['21']['tape_nodes']
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--observations', type=Path, default=DEFAULT_OBSERVATIONS)
    parser.add_argument('--cutoff', type=float, default=2700.1)
    parser.add_argument('--horizon', type=int, default=450)
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--no-tape', action='store_true')
    parser.add_argument('--tape-child', type=int, dest='cells')
    parser.add_argument('--decision-sec', type=float, default=505.0,
                        help='measured 21-cell decision wall time used for the scaled estimate')
    parser.add_argument('--freeway-share', type=float, default=None,
                        help='freeway share of the decision tape, if known (else only the bounds are reported)')
    parser.add_argument('--freeway-share-source', default=None,
                        help='where the freeway share comes from (recorded with it)')
    parser.add_argument('--rescale', action='store_true',
                        help='recompute decision_estimate of the existing rollout_cost.json only (no rollout)')
    args = parser.parse_args()
    if args.cells:
        return tape_child(args)
    if args.rescale:
        return rescale(args)
    report ={'schema': 'sdmpc31-rollout-cost/v1', 'cutoff_s': args.cutoff, 'horizon_s': args.horizon,
              'geometry': str(GEOMETRY.relative_to(ROOT)).replace('\\', '/'),
              'component_config': str(CONFIG.relative_to(ROOT)).replace('\\', '/'),
              'observations': str(args.observations), 'primal': primal(args)}
    if not args.no_tape:
        report['tape'] = tape(args)
    report['decision_estimate'] = decision_estimate(report, args)
    (HERE / 'rollout_cost.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(report, indent=2))


def decision_estimate(report, args):
    ratio = report.get('tape', {}).get('node_ratio', report['primal']['ratio_median'])
    share = args.freeway_share
    if share is not None and not 0.0 <= share <= 1.0:
        raise ValueError('freeway share must lie in [0, 1]')
    return {
        'basis_21cell_decision_sec': args.decision_sec, 'component_ratio': ratio,
        'upper_bound_sec': args.decision_sec * ratio,
        'scaled_sec': None if share is None else args.decision_sec * (1 - share + share * ratio),
        'freeway_share': share, 'freeway_share_source': None if share is None else args.freeway_share_source,
        'note': 'upper bound assumes the whole decision scales with the freeway component; the urban/port share '
                'does not. A tape-node share is not a wall-time share; G1 measures the real decision time.'}


def rescale(args):
    """Recompute decision_estimate only; the measured primal and tape blocks are kept as written."""
    path = HERE / 'rollout_cost.json'
    report = json.loads(path.read_text(encoding='utf-8'))
    report['decision_estimate'] = decision_estimate(report, args)
    path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(report['decision_estimate'], indent=2))


if __name__ == '__main__':
    main()
