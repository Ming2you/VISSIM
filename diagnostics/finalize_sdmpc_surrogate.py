"""Summarize a changed approximation without asserting identical decisions."""
from pathlib import Path
import hashlib
import json
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1]


def main():
    folder=ROOT/'diagnostics/sdmpc_surrogate_reuse_20260922'
    read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    solve=read(folder/'full_decision_v1/result.json')
    baseline=read(ROOT/'diagnostics/sdmpc_trial_20260922/full_decision_v1/result.json')
    jac=read(folder/'surrogate_h3_v2/comparison.json')
    default=read(folder/'default_h3_v1/comparison.json')
    audit=read(folder/'exact_audit_v1/result.json')
    selection=solve['selection'];q=solve['query']
    derivatives=selection['tangent_derivatives']
    config=ROOT/'diagnostics/sdmpc_trial_20260922/config_candidate.json'
    traces=selection['local_rows']
    checks=dict(completed=solve['completed'],same_saved_time=solve['sim_sec']==baseline['sim_sec']==900.,
        no_runtime_source_changes=not solve['source_changes'] and all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
            for p,h in solve['source_sha256'].items()),
        previous_config_unchanged=hashlib.sha256(config.read_bytes()).hexdigest()=='5c708fcff3cdda8abc33ee35a65d35613153f49fe233b745b9ba0ddeeb289fe4',
        same_iteration_limit=solve['policy']['max_iterations']==baseline['policy']['max_iterations']==2,
        derivative_match_to_audited_baseline=jac['pass_all'],default_derivative_unchanged=default['pass_all'],
        model_feasible=solve['response']['feasible'],
        approximation_explicit=solve['response'].get('execution_model_evaluated') is False
            and selection.get('independent_ad_witness_performed') is False,
        no_false_audit_pass=bool(derivatives) and all(r['complete_primal_state_match'] is False
            and r['max_primal_state_error'] is None and r['primal_audit_performed'] is False for r in derivatives),
        same_model_anchors=all(max(abs(v) for v in r['anchor_correction_'+name])<=1e-8
            for r in derivatives for name in ('costs','resources')),
        candidate_ad_reused=all(r['candidate_prediction_reused']['physical_inputs_exact'] for r in derivatives),
        no_local_qp_rollouts=bool(traces) and all(r['traffic_rollouts']==0 for r in traces),
        explicit_rollout_accounting=q['total_rollouts']==q['scalar_rollouts']+q['tangent_rollouts']
            ==sum(r['scalar_rollouts']+r['tangent_rollouts'] for r in q['rows']),
        no_hidden_exact_or_witness_rollouts=q['exact_execution_rollouts']==q['independent_ad_witness_rollouts']==0,
        no_failed_batches=q['failed_batches']==q['failed_predictions_with_unknown_rollout_count']==0,
        closed=q['closed'] and not q['owned_workers_alive'],
        physical_commands_checked=not any(audit['command_differences'].values()),
        all_three_blocks_checked=audit['control_sequence']['all_actuator_and_step_constraints_checked'],
        exact_audit_recorded=audit['audit_completed'] and not audit['source_changes'],
        regression='Ran 145 tests' in (folder/'regression_v1.log').read_text() and '\nOK' in (folder/'regression_v1.log').read_text(),
        final_reuse_tests='Ran 9 tests' in (folder/'tests_v2.log').read_text() and '\nOK' in (folder/'tests_v2.log').read_text(),
        parameters='PASS' in (folder/'parameters_v1.log').read_text(encoding='utf-8'))
    old_rollouts=baseline['query']['endpoint_calls']+sum(r['scalar_rollouts']+r['tangent_rollouts']
        for r in baseline['selection']['tangent_derivatives'])+2*sum(r['unused_derivatives']
        for r in baseline['selection']['trial_derivative_overlaps'])
    result=dict(scope=__doc__,checks=checks,implementation_checks_all_pass=all(checks.values()),
        before_sec=baseline['wall_sec'],after_sec=solve['wall_sec'],
        reduction_percent=100*(1-solve['wall_sec']/baseline['wall_sec']),
        decision_150s_target_met=solve['wall_sec']<=150,
        before_rollouts=old_rollouts,after_rollouts=q['total_rollouts'],
        before_candidates=baseline['selection']['candidates'],iteration_context=solve['iteration_context'],
        candidates=selection['candidates'],rollout_breakdown=q,
        exact_model_audit_feasible=audit['exact_model_feasible'],
        exact_selected_cost=audit['selected_exact_cost'],exact_held_cost=audit['held_exact_cost'],
        exact_cost_reduction_percent=audit['exact_cost_reduction_percent'],
        surrogate_selected_cost=selection['selected_objective'],surrogate_held_cost=selection['held_objective'],
        selected_physical_commands_equal_to_previous=(solve['response']['command_evidence']['ordered_rows']
            == baseline['response']['command_evidence']['ordered_rows']),
        native_applied=False,native9000_completed=False,
        timing_scope='Single complete decisions, two-iteration cap; different approximation may change selected actions and candidate work.',
        adopted_default=False)
    paths=['evaluation/controllers/sdmpc.py','evaluation/controllers/sdmpc_tangent.py',
        'evaluation/controllers/sdmpc_tangent_worker.py','evaluation/controllers/sdmpc_tangent_surrogate.py',
        'diagnostics/test_sdmpc_surrogate_reuse.py','diagnostics/check_sdmpc_reverse.py',
        'diagnostics/check_sdmpc_full_decision.py','diagnostics/audit_sdmpc_surrogate.py',
        'diagnostics/finalize_sdmpc_surrogate.py','docs/SDMPC_SURROGATE_REUSE_20260922.md']
    manifest={}
    for name in paths:
        source=ROOT/name;target=folder/'final_sources'/name
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
        manifest[name]=hashlib.sha256(source.read_bytes()).hexdigest()
    result['source_sha256']=manifest
    with (folder/'summary.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    print(json.dumps({k:v for k,v in result.items() if k not in ('rollout_breakdown','source_sha256')},indent=2))
    return 0 if result['implementation_checks_all_pass'] else 1


if __name__=='__main__':raise SystemExit(main())
