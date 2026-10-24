"""Review completed saved-state checks only; no predictions or native analysis."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def save(path,value):
    assert not path.exists(), 'Reuse prior review'
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')


def main():
    mode=sys.argv[1]
    assert mode in ('response','full')
    label='unseen3300_joint2' if mode=='response' else 'full2400'
    execution=read(HERE/(label+'_execution.json'))
    assert execution['status']=='complete_pending_review' and execution['exit_code']==0
    assert execution['source_pins_unchanged']
    for p,h in execution['source_pins'].items():assert sha(Path(p))==h,p
    if mode=='response':
        out=HERE/'unseen3300_fw5_joint2'
        old=read(HERE.parent/'unseen3300_routes/response_validation.json')
        new=read(out/'response_validation.json')
        assert new['clocks']==dict(freeway_sec=5,urban_sec=1)
        assert new['command_pins']==old['command_pins'] and new['target_pins']==old['target_pins']
        assert new['resource_max_exceedance_veh']<1e-7
        assert new['initial_group_errors']==old['initial_group_errors']
        differences={k:new['stock_changes'][k]['predicted']-old['stock_changes'][k]['predicted'] for k in old['stock_changes']}
        merge_old,merge_new=(r['predicted_merge10681'] for r in (old,new))
        arrival_old,arrival_new=(r['predicted_arrival10681'] for r in (old,new))
        # Practical coarsening gate, not a claim of improved native accuracy.
        # Review tolerance is declared here after inspecting the response.
        gate=(max(abs(x) for x in differences.values())<3
              and abs(merge_new-merge_old)<.05*merge_old
              and abs(arrival_new-arrival_old)<.05*arrival_old
              and abs(new['predicted_omega_ttt_veh_h']/old['predicted_omega_ttt_veh_h']-1)<.01)
        result=dict(status='coarsening_response_reviewed_with_retained_upstream_bias',
            physical_and_major_response_gate_pass=gate,stock_changes=new['stock_changes'],
            change_from_one_second_veh=differences,
            merge10681=dict(native=sum(x['merge'] for x in new['native_windows']),old=merge_old,new=merge_new),
            arrival10681=dict(native=sum(x['arrival'] for x in new['native_windows']),old=arrival_old,new=arrival_new),
            omega_ttt_veh_h=dict(old=old['predicted_omega_ttt_veh_h'],new=new['predicted_omega_ttt_veh_h']),
            physical_checks_pass=True,response_sec=new['wall_sec'],total_check_sec=execution['wall_sec'],
            tolerance_scope='Post-result engineering acceptance: stock3veh, merge/arrival5%, total model cost1%. Not preregistered statistical criteria.',
            limits=['Actual recorded commands supplied; response check, not counterfactual gain or independent seed.',
                    'Approach52 remains wrong: native increases21 vehicles while both models decrease about24.',
                    'No calibration or native analysis performed; full SDMPC wall still unmeasured.'])
        save(out/'comparison.json',result)
    else:
        spec=importlib.util.spec_from_file_location('retained_full_inspector',HERE.parent.parent/'runtime_pair2400_numericfix/compare.py')
        mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        run=mod.inspect(HERE/'full2400_fw5',dict(status='complete_uncompared',exit_code=0,
            external_process_wall_sec=execution['wall_sec']))
        assert run['policy']['max_iterations']==run['policy']['pfo_cap_options']['max_iterations']==2
        old=read(HERE.parent/'full_selection_review.json')
        assert run['policy']==old['complete_run']['policy'], 'Search budget/policy changed'
        costs=run['costs_and_constraints']
        result=dict(status='complete_decision_reviewed',
            measured_whole_check_wall_sec=execution['wall_sec'],full_time_target_met=execution['wall_sec']<=600,
            old_whole_process_sec=old['process_wall_seconds'],
            held_omega_ttt_veh_h=costs['held_objective'],selected_omega_ttt_veh_h=costs['selected_objective'],
            delta_model_omega_veh_h=costs['selected_objective']-costs['held_objective'],
            physical_and_shared_feasible=True,three_block_actuator_checks=True,query_stats=run['query_stats'],
            selected_rm_by_block=run['selected_rm_by_block'],converged=run['converged'],
            selection_status=run['selection_status'],pfo_sec=run['pfo_seconds'],
            sdmpc_after_pfo_sec=run['sdmpc_after_pfo_seconds'],same_search_policy_and_budget=True,
            native_runs=0,complete_run=run,
            limits=['One saved2400 state under uncontrolled concurrent native load; not a full-run or causal speedup guarantee.',
                    'Old decision predates both route-bin10 and freeway5 changes; not freeway5-only attribution.',
                    'Timer includes verifier imports and complete selection but excludes wrapper startup and this review.',
                    'Model gain is not measured native gain; nonconverged selection is best observed feasible, not optimum.',
                    'Urban physics remains1s and approach52 bias remains. No broader VSL or independent-seed validation.'])
        save(HERE/'full_selection_review.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('complete_run','limits','selected_rm_by_block')},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
