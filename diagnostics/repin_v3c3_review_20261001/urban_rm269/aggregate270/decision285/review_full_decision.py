"""Inspect the one finished decision; do not repeat any optimization."""
import hashlib,importlib.util,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_bytes())
def main():
    receipt=read(HERE/'full_decision_execution.json')
    assert receipt['status']=='complete_pending_review'
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in receipt['source_pins'].items())
    spec=importlib.util.spec_from_file_location('retained_full_inspector',HERE.parent.parent/'runtime_pair2400_numericfix/compare.py')
    inspector=importlib.util.module_from_spec(spec);spec.loader.exec_module(inspector)
    run=inspector.inspect(Path(receipt['output']),dict(status='complete_uncompared',exit_code=0,external_process_wall_sec=receipt['wall_sec']))
    old=read(HERE.parent/'urban_clock277/full_selection_review.json')
    assert not inspector.difference(run['policy'],old['complete_run']['policy'])
    assert run['policy']['max_iterations']==run['policy']['pfo_cap_options']['max_iterations']==2
    costs=run['costs_and_constraints']
    report=dict(status='complete_decision_reviewed',measured_whole_check_wall_sec=receipt['wall_sec'],
        full_time_target_met=receipt['wall_sec']<=600,previous_fw5_urban10_wall_sec=old['measured_whole_check_wall_sec'],
        held_omega_ttt_veh_h=costs['held_objective'],selected_omega_ttt_veh_h=costs['selected_objective'],
        delta_model_omega_veh_h=costs['selected_objective']-costs['held_objective'],
        physical_and_shared_feasible=True,three_block_actuator_checks=True,query_stats=run['query_stats'],
        converged=run['converged'],selection_status=run['selection_status'],
        selected_rm_by_block=run['selected_rm_by_block'],pfo_sec=run['pfo_seconds'],
        sdmpc_after_pfo_sec=run['sdmpc_after_pfo_seconds'],same_search_policy_and_budget=True,
        native_runs=0,complete_run=run,
        limits=['One3300s saved-state decision,not general timing or native benefit qualification.',
            'Urban10 changes endpoint quadrature and arrival resolution; native control remains150s and simulations are unchanged.',
            'Same iteration policy,not necessarily same number of response queries; machine load is uncontrolled.',
            'Best observed feasible command is not a proven optimum if not converged.',
            'This configuration additionally fixes the pre-head unsignalized10686 movement; speedup is not attributed to that geometry correction.',
            'Current isolated10681 and seed47 fixed responses are separate validation; this selected joint command has no native counterfactual.'])
    target=HERE/'full_selection_review.json';assert not target.exists()
    target.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('complete_run','limits','selected_rm_by_block')},ensure_ascii=False))
if __name__=='__main__':main()
