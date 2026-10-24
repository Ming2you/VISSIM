"""Summarize completed offline qualification; never converts missing work to PASS."""
from pathlib import Path
import hashlib
import json


def main():
    root=Path(__file__).resolve().parents[1]
    folder=root/'diagnostics/sdmpc_reverse_20260921'
    read=lambda p:json.loads((folder/p).read_text(encoding='utf-8'))
    jac=read('reverse_concurrent_h3_v2/result.json')
    comparison=read('reverse_concurrent_h3_v2/comparison.json')
    native=read('native_check/report.json')
    full=read('full_decision_v2/result.json')
    selected=full.get('selection',{})
    derivatives=selected.get('tangent_derivatives',[])
    sequence=full.get('response',{}).get('control_sequence',{})
    checks=dict(jacobian_matches_forward=comparison['pass_all'],
        all_states_match=jac['complete_primal_state_match'],
        prior_native_actions_match=native['pass_all'],
        full_decision_completed=full['completed'],
        full_decision_feasible=full.get('response',{}).get('feasible') is True,
        no_live_source_changes=not full['source_changes'],
        three_blocks_first_only=(sequence.get('blocks')==3 and sequence.get('applied_block')==0
            and sequence.get('all_actuator_and_step_constraints_checked') is True),
        all_full_jacobians_verified=(bool(derivatives) and all(r['complete_primal_state_match']
            and not r['fallback_reasons'] and len(r['ad_axes'])==231 for r in derivatives)),
        final_sources_unchanged=all(hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()==row['sha256']
            for row in read('change_sources_v2.json')))
    baseline=523.46831
    result=dict(scope='Offline saved-state qualification; no VISSIM application or 9000s outcome',
        checks=checks,pass_all=all(checks.values()),baseline_jacobian_sec=baseline,
        jacobian_sec=jac['wall_sec_including_spawn'],
        jacobian_reduction_pct=100*(1-jac['wall_sec_including_spawn']/baseline),
        full_decision_sec=full['wall_sec'],full_decision_minutes=full['wall_sec']/60,
        previous_full_decision_sec=read('full_decision_export/result.json')['wall_sec'],
        decision_150s_target_met=full['wall_sec']<=150,
        full_jacobian_calls=len(derivatives),
        full_jacobian_times=[r['wall_sec_including_spawn'] for r in derivatives],
        reused_gradients=len(selected.get('gradient_reuse',[])),
        candidates=selected.get('candidates'),
        held_model_ttt=selected.get('held_objective'),selected_model_ttt=selected.get('selected_objective'),
        final_constraints=selected.get('final_constraints'),
        selection_status=selected.get('selection_status'),converged=selected.get('converged'),
        native_applied=False)
    (folder/'qualification_summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))
    return 0 if result['pass_all'] else 1


if __name__=='__main__':raise SystemExit(main())
