"""Validate isolated mean-speed conditioning and replay prior local pilots."""
from pathlib import Path
from collections import defaultdict, Counter
import ast, hashlib, sys
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920 import speed_population as p


def main():
    directory = p.d.HERE / 'speed_population_increment_s10_mean_speed_v1'
    base = p.d.HERE / 'speed_population_increment_s10_v1'
    model = p.d.e.load(directory / 'model.json')
    old = p.d.e.load(base / 'model.json')
    result = p.d.e.load(directory / 'result.json')
    checks = Counter()
    # Same rows/targets in the unchanged backoff banks. Sum the new context
    # dimension out of the finest bank to recover the old conditional counts.
    assert model['tables'][:2] == old['tables'][:2]
    folded = defaultdict(lambda: np.zeros(3 * len(model['grid'])))
    for key_s, values in model['tables'][3].items():
        rho, gradient, mean, node = ast.literal_eval(key_s)
        folded[rho, gradient, node] += np.array(values)
    reference = {ast.literal_eval(k): np.array(v) for k, v in old['tables'][2].items()}
    assert reference.keys() == folded.keys()
    largest = 0.
    for key in reference:
        largest = max(largest, float(np.max(np.abs(reference[key] - folded[key]))))
        assert np.allclose(reference[key], folded[key], rtol=1e-12, atol=1e-8)
        checks['context_counts_collapsed'] += 1
    assert p.d.e.load(directory / 'initials.json') == p.d.e.load(base / 'initials.json')
    checks['initial_populations_and_boundary_identical'] += 1
    geo = {r['cell']: r for r in p.d.e.load(p.d.H / 'controller_response_s23_v1/none/geometry.json')['cells'] if r['road'] == 'FW_E'}
    rho_max = p.d.e.load(p.d.HERE / 'compact_lane_state_v1/result.json')['rho_max']
    support = []
    for folder in ('speed_population_v1', 'speed_population_increment_s10_v1',
                   'speed_population_increment_s10_phase5_v1', directory.name):
        path = p.d.HERE / folder
        doc = p.d.e.load(path / 'model.json')
        grid = np.array(doc['grid'])
        phases = len(doc.get('history_edges_kmh', [-1., 1.])) + 1
        mode = doc.get('context_mode', 'basic')
        tables = [{ast.literal_eval(k): np.array(v) for k, v in bank.items()} for bank in doc['tables']]
        kernels, _ = p.compile_kernel(tables, grid, phases, mode)
        for context, matrix in kernels.items():
            assert np.array_equal(matrix, np.array(doc['kernels'][str(context)]))
            checks['exact_kernel_recompiles'] += 1
        initials = p.d.e.load(path / 'initials.json')
        for run in p.d.e.load(path / 'result.json')['autonomous_runs']:
            initial = initials[run['arm']][str(run['start_s'])]
            state = {int(c): np.array(v) for c, v in initial['populations'].items()}
            trace, final = p.rollout(state, initial['rate'], geo, rho_max, grid, kernels, context_mode=mode)
            assert trace[-1]['inlet_queue'] == run['final_queue']
            assert all(p.moments(v, grid) == run['final_states'][str(c)] for c, v in final.items())
            checks['exact_final_replays'] += 1
            checks['conserved_realizable_steps'] += len(trace)
            if mode == 'mean_speed':
                queue = 0.
                mass = Counter()
                for _ in range(30):
                    stats = {c: p.moments(v, grid) for c, v in state.items()}
                    for c in p.m.CELLS:
                        ctx = p.contexts(stats, c, geo, mode)
                        for node, amount in enumerate(state[c]):
                            used = -1
                            for level, key in ((3, (*ctx, node)), (2, (ctx[2], node)), (1, (node,)), (0, (node % len(grid),))):
                                values = tables[level].get(key)
                                if values is not None and values.sum() >= p.MIN_SUPPORT:
                                    used = level
                                    break
                            mass[used] += float(amount)
                    state, queue, _ = p.step(state, initial['rate'], queue, geo, rho_max, grid, kernels, mode)
                support.append(dict(arm=run['arm'], start_s=run['start_s'],
                    used_vehicle_seconds=dict(mass), fractions={k: v / sum(mass.values()) for k, v in mass.items()}))
    for name, digest in result['pins'].items():
        assert hashlib.sha256((p.d.ROOT / name).read_bytes()).hexdigest() == digest
        checks['current_source_pins'] += 1
    for folder in ('speed_population_v1', 'speed_population_increment_s10_v1', 'speed_population_increment_s10_phase5_v1'):
        path = p.d.HERE / folder
        manifest = p.d.e.load(path / 'source_archive.json')
        archive = p.d.ROOT / manifest['archived_path']
        assert hashlib.sha256(archive.read_bytes()).hexdigest() == manifest['sha256']
        checks['historical_source_archives'] += 1
    core = p.d.e.load(p.d.HERE / 'transport_step_work_v1/checkpoint.json')['sha256']
    for name, digest in core.items():
        if name.startswith('evaluation\\controllers\\') or name.endswith('canonical_harness.py'):
            assert hashlib.sha256((p.d.ROOT / name).read_bytes()).hexdigest() == digest
            checks['unchanged_core'] += 1
    p.d.e.save(directory / 'validation.json', dict(status='REJECTED_LOCAL_ACCURACY_GATE', checks=dict(checks),
        max_context_count_collapse_error=largest, used_support=support,
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), qualified=False))
    print('CHECKS', dict(checks), 'COLLAPSE_ERROR', largest, flush=True)


if __name__ == '__main__':
    main()
