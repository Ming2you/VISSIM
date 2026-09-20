"""Validate the completed population pilots and audit USED training support.

No native run, model refit, controller edit, or predictive success declaration.
"""
from pathlib import Path
from collections import Counter
import ast, hashlib, sys
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import speed_population as p


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def row_levels(tables, grid):
    answer = {}
    for rho in range(4):
        for gradient in range(3):
            rows = []
            for node in range(3 * len(grid)):
                level_used = -1
                for level, key in ((2, (rho, gradient, node)), (1, (node,)), (0, (node % len(grid),))):
                    value = tables[level].get(key)
                    if value is not None and value.sum() >= p.MIN_SUPPORT:
                        level_used = level
                        break
                rows.append(level_used)
            answer[rho, gradient] = np.array(rows)
    return answer


def main():
    out = p.d.HERE / 'speed_population_validation_v1'
    out.mkdir(exist_ok=False)
    geometry_path = p.d.H / 'controller_response_s23_v1/none/geometry.json'
    geo = {r['cell']: r for r in p.d.e.load(geometry_path)['cells'] if r['road'] == 'FW_E'}
    rho_max = p.d.e.load(p.d.HERE / 'compact_lane_state_v1/result.json')['rho_max']
    old_path = p.d.HERE / 'speed_population_v1/result.json'
    old = p.d.e.load(old_path)
    archive = p.d.HERE / 'speed_population_v1/source_absolute.py.txt'
    old_source_key = next(k for k in old['pins'] if Path(k).name == 'speed_population.py')
    assert sha(archive) == old['pins'][old_source_key]
    archive_receipt = p.d.HERE / 'speed_population_v1/source_archive.json'
    archive_data = dict(original_path=old_source_key, archived_path=str(archive.relative_to(p.d.ROOT)), sha256=sha(archive))
    if archive_receipt.exists():
        assert p.d.e.load(archive_receipt) == archive_data
    else:
        p.d.e.save(archive_receipt, archive_data)

    checks = Counter()
    support = []
    input_pins = {}
    for folder in ('speed_population_v1', 'speed_population_increment_s10_v1'):
        base = p.d.HERE / folder
        doc = p.d.e.load(base / 'model.json')
        result = p.d.e.load(base / 'result.json')
        for name, digest in result['pins'].items():
            path = p.d.ROOT / name
            if folder == 'speed_population_v1' and name == old_source_key:
                path = archive
            assert sha(path) == digest, (folder, name)
            checks['historical_source_pins'] += 1
        grid = np.array(doc['grid'])
        tables = [{ast.literal_eval(k): np.array(v) for k, v in bank.items()} for bank in doc['tables']]
        kernels, fallback = p.compile_kernel(tables, grid)
        for k, matrix in kernels.items():
            assert np.array_equal(matrix, np.array(doc['kernels'][str(k)]))
            checks['exact_recompiled_kernels'] += 1
        levels = row_levels(tables, grid)
        initials = p.d.e.load(base / 'initials.json')
        for run in result['autonomous_runs']:
            init = initials[run['arm']][str(run['start_s'])]
            state = {int(c): np.array(v) for c, v in init['populations'].items()}
            queue = 0.
            weighted = Counter()
            first = Counter()
            for t in range(30):
                stats = {c: p.moments(v, grid) for c, v in state.items()}
                for c in p.m.CELLS:
                    used = levels[p.contexts(stats, c, geo)]
                    for level in (-1, 0, 1, 2):
                        mass = float(state[c][used == level].sum())
                        weighted[level] += mass
                        if t == 0:
                            first[level] += mass
                state, queue, _ = p.step(state, init['rate'], queue, geo, rho_max, grid, kernels)
                checks['conserved_realizable_steps'] += 1
            assert queue == run['final_queue']
            for c, population in state.items():
                assert p.moments(population, grid) == run['final_states'][str(c)]
            checks['exact_final_replays'] += 1
            support.append(dict(model=folder, arm=run['arm'], start_s=run['start_s'],
                initial_mass_by_level=dict(first), rollout_vehicle_seconds_by_level=dict(weighted),
                initial_fraction={k: v / sum(first.values()) for k, v in first.items()},
                rollout_fraction={k: v / sum(weighted.values()) for k, v in weighted.items()}))
        for name in ('model.json', 'initials.json', 'result.json'):
            path = base / name
            input_pins[str(path.relative_to(p.d.ROOT))] = sha(path)

    grid = np.arange(0., 211., 10.)
    # An unchanged speed must not pull neighboring basis nodes toward the
    # training observation. The former absolute mapping does precisely that.
    identity_example = {}
    for kind in ('absolute', 'increment'):
        means = []
        for node in (len(grid) + 10, len(grid) + 11):
            target = p.transition_targets(node, 105., 105., 1, grid, kind)
            means.append(sum(weight * grid[j % len(grid)] for j, weight in target))
        identity_example[kind] = means
    assert identity_example == {'absolute': [105., 105.], 'increment': [100., 110.]}
    # Both endpoints, off-grid means, deceleration, acceleration and zero delta.
    for before in (0., .1, 35.7, 105., 209.9, 210.):
        for after in (0., .1, 35.7, 105., 209.9, 210.):
            for ph in range(3):
                value = 0.
                for node, w0 in p.encode(before, ph, grid):
                    row = p.transition_targets(node, before, after, 1, grid, 'increment')
                    assert abs(sum(w for _, w in row) - 1.) < 1e-12
                    assert all(w >= 0 for _, w in row)
                    value += w0 * sum(w * grid[j % len(grid)] for j, w in row)
                    if before == after:
                        assert row == [(len(grid) + node % len(grid), 1.)]
                assert abs(value - after) < 1e-10
                checks['bounded_mean_mapping_cases'] += 1

    # Calling the forecaster has no label/native-state argument. Altering the
    # independently saved observations therefore cannot enter its computation.
    core = p.d.e.load(p.d.HERE / 'transport_step_work_v1/checkpoint.json')['sha256']
    protected = [k for k in core if k.startswith('evaluation\\controllers\\') or k.endswith('canonical_harness.py')]
    for name in protected:
        assert sha(p.d.ROOT / name) == core[name]
        checks['unchanged_canonical_core'] += 1
    p.d.e.save(out / 'result.json', dict(status='REJECTED_PREDICTION_ACCURACY_NOT_SUPPORT_FAILURE',
        checks=dict(checks), zero_delta_example=identity_example, used_support=support,
        pins={**input_pins, str(Path(__file__).relative_to(p.d.ROOT)): sha(Path(__file__))},
        evidence_scope='Positive local populations and exact historical replay pass. Local30s forecast and full450s gain do not qualify.',
        qualified=False, new_native_runs=0, production_changes=0))
    print('CHECKS', dict(checks), flush=True)
    for r in support:
        if r['model'].endswith('s10_v1') and r['arm'] == 'none':
            print('USED_SUPPORT', r['start_s'], r['initial_fraction'], r['rollout_fraction'], flush=True)


if __name__ == '__main__':
    main()
