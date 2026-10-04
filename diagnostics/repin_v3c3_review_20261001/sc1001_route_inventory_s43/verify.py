"""Verify saved bounded diagnostics without starting a forecast or native run."""
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
R = HERE.parent
C = R / 'sc1001_connection'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def top_functions(path):
    return {n.name: ast.dump(n, include_attributes=False)
            for n in ast.parse(path.read_text(encoding='utf-8')).body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def main():
    target = HERE / 'verification.json'
    if target.exists():
        raise FileExistsError(target)
    protocol = read(HERE / 'protocol.json')
    previous = read(R / 'sc1001_independent_s43/verification.json')
    history = read(R / 'sc1001_service_history/verification.json')
    checked = {}
    for name, expected in {**history['unchanged_core_pins'], **protocol['source_pins']}.items():
        assert sha(ROOT / name) == expected, name
        checked[name] = expected
    wrapper = C / 'check_connection.py'
    old_key = next(k for k in previous['source_pins'] if k.replace('\\', '/').endswith('/check_connection.py'))
    assert sha(HERE / 'check_connection.before.py.txt') == previous['source_pins'][old_key]
    old, new = top_functions(HERE / 'check_connection.before.py.txt'), top_functions(wrapper)
    assert old.keys() == new.keys()
    assert [k for k in old if old[k] != new[k]] == ['main']
    old_assess, new_assess = top_functions(HERE / 'assess_four_executed.py.txt'), top_functions(HERE / 'assess.py')
    assert all(new_assess[k] == v for k, v in old_assess.items())
    assert set(new_assess) - set(old_assess) == {'rm47_ledger'}
    base, routed = read(C / 'candidate_config.json'), read(C / 'candidate_route_inventory.json')
    route_path = routed['freeway'].pop('offramp_route_inventory')
    assert routed == base
    checked[str(C.relative_to(ROOT) / 'candidate_route_inventory.json')] = sha(C / 'candidate_route_inventory.json')
    assert checked[str(C.relative_to(ROOT) / 'candidate_route_inventory.json')] == '397b8d0b54329749ed6b36c06a0579a622a45f30bdeae284938997e46044c2bc'
    checked[route_path] = sha(ROOT / route_path)
    assessment = read(HERE / 'assessment.json')
    assert assessment['completed_forecasts'] == 4
    assert assessment['new_native'] == assessment['fitting'] == assessment['optimizer_iterations'] == 0
    assert assessment['max_route_partition_residual'] < 1e-7
    assert assessment['max_resource_exceedance'] < 1e-7
    for arm, record in assessment['native_east_ttt_flow_decomposition'].items():
        expected_delta = assessment['cases'][arm]['east_ttt']['native'] - assessment['cases']['nc']['east_ttt']['native']
        assert abs(sum(record['contributions_veh_h'].values()) - expected_delta) < 1e-9
    assert assessment['marginal_costs']['vsl']['native_omega_veh_h'] > 0
    assert assessment['marginal_costs']['vsl']['predicted_omega_veh_h'] < 0
    ledger = read(HERE / 'native_rm47_flow_ledger.json')
    contrast = read(HERE / 'rm47_model_flow_comparison.json')
    for name, expected in contrast['source_pins'].items():
        assert sha(Path(name)) == expected, name
        checked[name] = expected
    sums = {k: sum(b[k] - a[k] for a, b in zip(ledger['native']['hold'], ledger['native']['release']))
            for k in ('source', 'merge', 'off', 'terminal')}
    assert sums == contrast['release_minus_hold']['native'] == dict(source=1, merge=50, off=-18, terminal=-37)
    assert all(row['residual'] == row['removed'] == 0 for rows in ledger['native'].values() for row in rows)
    actual = read(C / 'assessment.json')['rm_delta_veh_h']
    assert abs(actual['actual_FW_E'] - 4.8699444444444) < 1e-9
    assert abs(actual['actual_ramps'] + 2.6797222222222246) < 1e-9
    checked[str(C.relative_to(ROOT) / 'assessment.json')] = sha(C / 'assessment.json')
    snapshot = HERE / 'check_connection.executed.py.txt'
    if snapshot.exists():
        assert snapshot.read_bytes() == wrapper.read_bytes()
    else:
        snapshot.write_bytes(wrapper.read_bytes())
    artifacts = {p.name: sha(p) for p in sorted(HERE.iterdir()) if p.is_file() and p != target}
    result = dict(status='SAVED_DIAGNOSTICS_VERIFIED_NOT_GAIN_QUALIFIED',
        source_pins=checked, artifacts=artifacts, config_change_only='freeway.offramp_route_inventory',
        diagnostic_wrapper_changed_functions=['main'], assess_added_functions=['rm47_ledger'],
        completed_forecasts=4, forecast_compute_sec=assessment['compute_sec'],
        unit_tests_reused=23, unit_tests_rerun=0, coefficient_fit=0, new_native=0, fzp_reads=0,
        optimizer=0, push=0, model_core_changed=False, production_default_enabled=False,
        full_AD_or_native_gain_qualification=False, remaining_owned_processes=0,
        previous_wrapper_pin_resolved_by='check_connection.before.py.txt',
        verification_retry='Initial verification used wrong existing JSON key; corrected before any output was written. No forecast repeated.',
        goal='ACTIVE / NOT_QUALIFIED', classification='PROGRESS',
        source_receipts='Prior same-prefix/native-execution receipts reused; no new full trace census.')
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k not in ('source_pins', 'artifacts')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
