"""Bounded check of already completed forecasts; no forecast or VISSIM run."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
K = ROOT / 'diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    hashes = {
        'evaluation/controllers/vissim_stackelberg_adapter.py': 'efbe61b061166055f5abce97ae090d3e69f4c650d9b91a978e5b9e7e70313c28',
        'evaluation/controllers/physical_lane_groups.py': 'c673b8c192bdd2d7aff4d077cc184161c7da0901bda94b90adac28c2054ed0ce',
        'evaluation/controllers/physical_ramp_boundary.py': 'bb39499da435ee0dc6bc76def2f191938497d6c35d92131d78c08f60e53a9e01',
        'diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/canonical_harness.py': '0154f149c8ee24a81049336d0b9169190bbda6033fdc8888d3fd77a4fac0b593'}
    for name, digest in hashes.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    traces = load(K / 'coupled_population_work_v1/trace.json')
    assert len(traces) == 10800
    for row in traces:
        assert abs(row['mass_residual']) < 1e-7 and row['n'] >= 0 and 0 <= row['v'] <= 120
        assert 0 <= row['sd']**2 <= row['v'] * (120 - row['v']) + 1e-7
    arms = ['none', 'rm_ramp', 'vsl', 'both']
    for arm in arms:
        reference = load(K / 'coupled_population_reference_v1' / f'prediction_{arm}.json')
        old = load(K / 'transport_step1_exchange_off_v2' / f'prediction_{arm}.json')
        assert reference == old, arm
        for folder in ['coupled_population_candidate_v1', 'merge_partition10483_v1']:
            candidate = load(K / folder / f'prediction_{arm}.json')
            for field in ['cells', 'flows', 'ports', 'ramps']:
                assert [v for v in candidate[field] if v.get('road') == 'FW_W'] == [v for v in reference[field] if v.get('road') == 'FW_W'], (folder, arm, field)
            assert candidate['local_ramp_audit']['passed'], (folder, arm)
    for folder in ['coupled_population_candidate_v1', 'merge_partition10483_v1']:
        result = load(K / folder / 'result.json')
        for arm in arms[1:]:
            expected = {key: result['costs'][arm][key] - result['costs']['none'][key] for key in ['mainline', 'on', 'off']}
            expected['total'] = sum(expected.values())
            for key, value in expected.items():
                assert abs(value - result['deltas'][arm][key]) < 1e-10
        assert result['qualified'] is False
    summary = {'passed': True, 'exact_reference_forecasts': 4, 'west_unchanged_forecasts': 8,
               'population_conservative_realizable_steps': len(traces), 'core_hashes_unchanged': hashes,
               'latest_candidates_qualified': False, 'new_forecasts': 0, 'new_native_runs': 0}
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
