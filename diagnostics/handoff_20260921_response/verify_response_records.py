"""Read-only verification of saved response diagnostics; no native/forecast run."""
from pathlib import Path
import hashlib
import importlib.util
import json

ROOT = Path(__file__).resolve().parents[2]
K = ROOT / 'diagnostics/demand_sweep/ramp_dsd_20260916_v2/cohort_dynamics_20260920'
ARMS = ('none', 'rm_ramp', 'vsl', 'both')


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def close(a, b, tolerance=1e-7):
    assert abs(a-b) < tolerance, (a, b)


def main():
    pin_count = 0
    for name in ('marginal_cohort_paths_v1/result.json', 'marginal_cohort_paths_v1/validation.json',
                 'downstream_response_terms_v4/result.json', 'downstream_relaxation_check_v2/protocol.json',
                 'merge_speed_timing_v1/result.json', 'downstream_terms_reference_v3/protocol.json',
                 'downstream_tau30_fixed_nu_v1/protocol.json', 'downstream_tau30_preserve_pressure_v1/protocol.json'):
        record = load(K/name)
        for relative, digest in record['source_pins'].items():
            p = ROOT / relative.replace('\\', '/')
            assert hashlib.sha256(p.read_bytes()).hexdigest() == digest, relative
            pin_count += 1
    old = load(K/'downstream_relaxation_check_v1/protocol.json')
    name = (K/'downstream_relaxation_check.py').relative_to(ROOT).as_posix()
    archived = K/'downstream_relaxation_check_v1/source_before_result_reader_fix.txt'
    assert hashlib.sha256(archived.read_bytes()).hexdigest() == old['source_pins'][name]

    updates = west_checks = 0
    traces = {}
    for arm in ARMS:
        base = load(K/'transport_step1_exchange_off_v2'/f'prediction_{arm}.json')
        assert load(K/'downstream_terms_reference_v3'/f'prediction_{arm}.json') == base
        rows = load(K/'downstream_response_terms_v4'/f'{arm}_terms.json')
        traces[arm] = {(r['time_s'], r['cell'], r['group']): r for r in rows}
        assert len(rows) == len(traces[arm]) == 5400
        for r in rows:
            close(r['v_at_equation'] + sum(r['terms'].values()), r['equation_output'])
            close(r['v0'] + r['pre_equation_shift'] + sum(r['terms'].values()) + r['post_equation_shift'], r['v1'])
            if r['cell'] >= 15:
                assert r['tau_s'] == 12 and r['nu'] == 35
                close(r['post_equation_shift'], 0)
            updates += 1
        for candidate in ('downstream_tau30_fixed_nu_v1', 'downstream_tau30_preserve_pressure_v1'):
            got = load(K/candidate/f'prediction_{arm}.json')
            for field in ('cells', 'flows', 'ports', 'ramps'):
                assert [r for r in got[field] if r.get('road') == 'FW_W'] == [r for r in base[field] if r.get('road') == 'FW_W']
            assert got['local_ramp_audit']['passed']
            for d in got['diagnostics']['roads']:
                assert d['continuity_residual_max_veh'] < 1e-7
                assert d['negative_density_count'] == d['jam_density_exceedance_count'] == 0
            west_checks += 1
    audit = load(K/'downstream_response_terms_v4/result.json')
    for arm, budgets in audit['term_budgets'].items():
        for b in budgets:
            c = b['cell']
            close(sum(b['final_terms'].values()), b['final_delta_v'])
            close(sum(b['speed_time_terms'].values()), b['speed_time_delta_kmh_s'], 1e-6)
            actual = sum(traces[arm][t,c,0]['v1']-traces['none'][t,c,0]['v1'] for t in range(2400,2850))
            close(actual, b['speed_time_delta_kmh_s'], 1e-6)
    for folder in ('transport_step1_exchange_off_v2', 'downstream_tau30_fixed_nu_v1', 'downstream_tau30_preserve_pressure_v1'):
        for delta in load(K/folder/'result.json')['deltas'].values():
            close(sum(delta[f] for f in ('mainline', 'on', 'off')), delta['total'])

    cohort = load(K/'marginal_cohort_paths_v1/vehicles.json')
    assert len(cohort) == 676 and sum(r['delta_residence_s'] for r in cohort) == 1553
    for row in cohort:
        for arm in ('rm8', 'rm_ramp'):
            r = row['arms'][arm]
            assert sum(r['by_cell'].values()) == r['residence_s']
    receipt = load(K/'marginal_cohort_paths_v1/validation.json')
    assert receipt['passed'] and receipt['stock_checks'] == 900
    assert receipt['same_recorded_exit_vehicles'] == 665 and not receipt['changed_recorded_exit_vehicles']

    spec = importlib.util.spec_from_file_location('saved_merge_exposure', K/'merge_speed_timing_summary.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    exposure = load(K/'merge_speed_timing_v1/result.json')
    for case, arms in exposure['results'].items():
        start = int(case.removeprefix('start'))
        for arm, expected in arms.items():
            path = K.parent/'controller_response_s23_v1/none' if arm == 'none' else K.parent/'response_late_s23_v1/observations'/arm
            got, _ = module.summarize(path, start, start+450)
            assert got == expected
    print(json.dumps(dict(passed=True, source_pin_checks=pin_count, full_reference_jsons_exact=4,
        reconstructed_speed_updates=updates, candidate_west_and_conservation_checks=west_checks,
        cohort_vehicle_cell_sum_checks=1352, merge_exposure_comparisons=6,
        new_forecasts=0, new_native_runs=0, qualified=False)))


if __name__ == '__main__':
    main()
