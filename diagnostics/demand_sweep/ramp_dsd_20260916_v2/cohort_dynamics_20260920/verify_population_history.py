"""Refinement, backward replay and used-support checks for phase5 pilot."""
from pathlib import Path
from collections import defaultdict, Counter
import ast, hashlib, sys
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import speed_population as p


def main():
    base = p.d.HERE / 'speed_population_increment_s10_phase5_v1'
    old_base = p.d.HERE / 'speed_population_increment_s10_v1'
    doc, old = (p.d.e.load(x / 'model.json') for x in (base, old_base))
    result = p.d.e.load(base / 'result.json')
    grid = np.array(doc['grid'])
    size = len(grid)
    phase_map = (0, 0, 1, 2, 2)
    node_map = np.array([phase_map[j // size] * size + j % size for j in range(size * 5)])
    errors = []
    checks = Counter()
    for level in range(3):
        folded = defaultdict(lambda: np.zeros(3 * size))
        for key_s, values in doc['tables'][level].items():
            key = ast.literal_eval(key_s)
            mapped_key = key if level == 0 else (*key[:-1], int(node_map[key[-1]]))
            np.add.at(folded[mapped_key], node_map, np.array(values))
        reference = {ast.literal_eval(k): np.array(v) for k, v in old['tables'][level].items()}
        assert folded.keys() == reference.keys()
        for key in folded:
            error = float(np.max(np.abs(folded[key] - reference[key])))
            errors.append(error)
            assert np.allclose(folded[key], reference[key], rtol=1e-12, atol=1e-8)
            checks['training_rows_collapsed_to_phase3'] += 1
    initial = p.d.e.load(base / 'initials.json')
    previous = p.d.e.load(old_base / 'initials.json')
    for arm, starts in initial.items():
        for t, entry in starts.items():
            assert entry['rate'] == previous[arm][t]['rate']
            for c, values in entry['populations'].items():
                collapsed = np.zeros(3 * size)
                np.add.at(collapsed, node_map, np.array(values))
                assert np.allclose(collapsed, previous[arm][t]['populations'][c], rtol=0, atol=1e-12)
                checks['initial_state_collapses'] += 1
    geo = {r['cell']: r for r in p.d.e.load(p.d.H / 'controller_response_s23_v1/none/geometry.json')['cells'] if r['road'] == 'FW_E'}
    rho_max = p.d.e.load(p.d.HERE / 'compact_lane_state_v1/result.json')['rho_max']
    weighted_support = []
    for directory, phase_count in ((p.d.HERE / 'speed_population_v1', 3), (old_base, 3), (base, 5)):
        model = p.d.e.load(directory / 'model.json')
        fitted = [{ast.literal_eval(k): np.array(v) for k, v in bank.items()} for bank in model['tables']]
        kernels, _ = p.compile_kernel(fitted, grid, phase_count)
        for key, matrix in kernels.items():
            assert np.array_equal(matrix, np.array(model['kernels'][str(key)]))
            checks['exact_kernel_recompiles'] += 1
        starts = p.d.e.load(directory / 'initials.json')
        for run in p.d.e.load(directory / 'result.json')['autonomous_runs']:
            entry = starts[run['arm']][str(run['start_s'])]
            state = {int(c): np.array(v) for c, v in entry['populations'].items()}
            trace, final = p.rollout(state, entry['rate'], geo, rho_max, grid, kernels)
            assert trace[-1]['inlet_queue'] == run['final_queue']
            for c, values in final.items():
                assert p.moments(values, grid) == run['final_states'][str(c)]
            checks['exact_autonomous_replays'] += 1
            if directory == base:
                levels = {}
                for context in kernels:
                    levels[context] = []
                    for node in range(phase_count * size):
                        used = -1
                        for level, key in ((2, (*context, node)), (1, (node,)), (0, (node % size,))):
                            values = fitted[level].get(key)
                            if values is not None and values.sum() >= p.MIN_SUPPORT:
                                used = level
                                break
                        levels[context].append(used)
                queue = 0.
                mass = Counter()
                for _ in range(30):
                    stats = {c: p.moments(v, grid) for c, v in state.items()}
                    for c in p.m.CELLS:
                        for node, level in enumerate(levels[p.contexts(stats, c, geo)]):
                            mass[level] += float(state[c][node])
                    state, queue, _ = p.step(state, entry['rate'], queue, geo, rho_max, grid, kernels)
                weighted_support.append(dict(arm=run['arm'], start_s=run['start_s'],
                    vehicle_seconds_by_level=dict(mass), fractions={k: v / sum(mass.values()) for k, v in mass.items()}))
    for name, digest in result['pins'].items():
        assert hashlib.sha256((p.d.ROOT / name).read_bytes()).hexdigest() == digest
        checks['phase5_source_pins'] += 1
    archive = old_base / 'source_before_history.py.txt'
    original_key = next(k for k in p.d.e.load(old_base / 'result.json')['pins'] if Path(k).name == 'speed_population.py')
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == p.d.e.load(old_base / 'result.json')['pins'][original_key]
    checks['phase3_source_archive'] += 1
    core = p.d.e.load(p.d.HERE / 'transport_step_work_v1/checkpoint.json')['sha256']
    for name, digest in core.items():
        if name.startswith('evaluation\\controllers\\') or name.endswith('canonical_harness.py'):
            assert hashlib.sha256((p.d.ROOT / name).read_bytes()).hexdigest() == digest
            checks['unchanged_core'] += 1
    p.d.e.save(base / 'validation.json', dict(status='VERIFIED_LOCAL_PILOT_NO_ACCURACY_QUALIFICATION',
        checks=dict(checks), largest_training_collapse_error=max(errors), support=weighted_support,
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), qualified=False))
    print('CHECKS', dict(checks), 'MAX_COLLAPSE_ERROR', max(errors), flush=True)


if __name__ == '__main__':
    main()
