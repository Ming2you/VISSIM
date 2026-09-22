"""Verify completed conditional memory diagnostics; no native or forecasts."""
from pathlib import Path
import ast
import hashlib
import json
import subprocess

K = Path(__file__).resolve().parent
ROOT = K.parents[3]


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    age = load(K/'interaction_duration_audit_v2/result.json')
    target = load(K/'target_history_audit_v1/result.json')
    old = load(K/'current_interaction_response_v1/result.json')
    pins = resolved = comparator = survival = 0
    archive = K/'interaction_duration_audit_v2/source_before_target_history.py'
    for result in (age, target):
        assert not result['qualified'] and not result['production_adopted']
        assert result['new_native_runs'] == 0 and result['future_training_canary_ignored']
        for name, digest in result['source_pins'].items():
            p = ROOT/name
            if hashlib.sha256(p.read_bytes()).hexdigest() != digest:
                assert p.name == 'interaction_duration_audit.py'
                assert hashlib.sha256(archive.read_bytes()).hexdigest() == digest
                resolved += 1
            pins += 1
        for arm, row in result['precontrol_prefix'].items():
            assert row['frames'] == 9 and row['rows'] == 1865
            assert row['all_except_desired_exact'] and not row['desired_used_in_predictor']
            assert row['desired_rounding_only_rows'] == (1732 if arm == 'rm_ramp' else 0)
        for period in ('nc_time_validation', 'nc_control', 'vsl_control', 'focused_cell16'):
            for h, row in result['scores'][period].items():
                a, b = row['existing'], old['scores'][period]['target_state'][h]
                assert a['n'] == b['n']
                for key in ('rmse_kmh', 'bias_kmh'):
                    assert abs(a[key]-b[key]) < 1e-10
                comparator += 1
    for arm in ('none', 'rm_ramp', 'vsl'):
        a = load(K/f'interaction_duration_audit_v2/duration_observations_{arm}.json')
        b = load(K/f'target_history_audit_v1/duration_observations_{arm}.json')
        assert a == b
        for rows in a.values():
            for row in rows:
                assert 0 <= row['elapsed_bin'] <= 3
                for value in row['horizons'].values():
                    assert value['initial_samples'] == value['observed_samples']+value.get('censored', 0)
                    assert 0 <= value.get('uninterrupted_same_state', 0) <= value['observed_samples']
                    survival += 1
    failed = load(K/'interaction_duration_audit_v1/prefix_failure.json')
    assert failed['fields'] == {'desired':1732}
    assert hashlib.sha256((K/'interaction_duration_audit_v1/source_before.py').read_bytes()).hexdigest() == failed['script_sha256']
    for path in (K/'interaction_duration_audit.py', archive, K/'interaction_duration_audit_v1/source_before.py', Path(__file__)):
        ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    core = ['evaluation/controllers/physical_lane_groups.py', 'evaluation/controllers/physical_ramp_boundary.py',
        'evaluation/controllers/vissim_stackelberg_adapter.py',
        'diagnostics/demand_sweep/user_native_20260914/metanet_calibration_v1/canonical_harness.py']
    for name in core:
        assert subprocess.check_output(['git','show','fbdbeed:'+name],cwd=ROOT) == (ROOT/name).read_bytes()
    result = dict(passed=True, qualified=False, source_pins=pins, historical_source_resolved=resolved,
        original_comparator_scores_exact=comparator, duration_survival_cells_checked=survival,
        repeated_observation_banks_exact=3, parsed_sources=4, core_unchanged_from='fbdbeed',
        new_native_runs=0, forecasts_recomputed=False,
        previous_goal_turn='progress: model/evidence delivery committed and remotely verified',
        current_goal_turn='progress: duration candidate rejected, target acceleration dependence isolated',
        goal_status='active; NOT_QUALIFIED',
        terminated_owned_sessions={'18065':'exit1 prefix precision assertion, preserved',
            '77134':'exit0 prefix discrepancy diagnosed','69657':'exit0 duration audit','14824':'exit0 target-history audit'},
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    destination = K/'target_history_audit_v1/verification.json'
    if destination.exists():
        assert load(destination) == result
    else:
        with destination.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
