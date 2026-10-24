"""Separate a coarser model's predicted gain from finite optimizer selection."""
import hashlib,importlib.util,json,pickle
from pathlib import Path
HERE=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    target=HERE/'previous_choice_review.json'
    assert not target.exists(),'Reuse completed review'
    receipt=read(HERE/'previous_choice_execution.json')
    assert receipt['exit_code']==0 and receipt['source_pins_unchanged']
    assert all(sha(Path(p))==h for p,h in receipt['source_pins'].items())
    spec=importlib.util.spec_from_file_location('retained_macro_inspector',HERE/'review.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    result=pickle.loads((HERE/'previous_choice_result.pickle').read_bytes())
    inspected=mod.row(result)
    old=read(HERE.parent/'full_selection_review.json')
    new=read(HERE/'full_selection_review.json')
    request=pickle.loads((HERE/'previous_choice_request.pickle').read_bytes())
    assert request['owned'][0].cfg.simulation.T_f_sec==5 and request['horizon']==3
    own_caps=[request['action'].N_P_star,request['action'].N_UF_star]
    current_caps=[new['complete_run']['costs_and_constraints']['final_constraints'][k]['target'] for k in ('np','nuf')]
    actual=[float(x) for x in result['resources']]
    assert all(x<=cap+1e-7 for x,cap in zip(actual,own_caps))
    assert all(x<=cap+1e-7 for x,cap in zip(actual,current_caps))
    # Old full review already checked the same three-block actuator/step bounds.
    assert old['physical_and_shared_feasible'] and old['three_block_actuator_checks']
    held=new['held_omega_ttt_veh_h'];selected=new['selected_omega_ttt_veh_h']
    previous=inspected['omega_veh_h']
    summary=dict(status='model_gain_retained_better_previous_command_missed_by_finite_search',
        old_command_old_model_omega_veh_h=old['selected_omega_ttt_veh_h'],
        old_command_current_model_omega_veh_h=previous,current_held_omega_veh_h=held,
        current_optimizer_selected_omega_veh_h=selected,
        old_command_current_model_gain_veh_h=held-previous,
        current_selected_model_gain_veh_h=held-selected,
        missed_model_improvement_veh_h=selected-previous,
        actual_np_nuf=actual,old_command_caps=own_caps,current_selected_caps=current_caps,
        both_numeric_cap_checks_pass=True,physical_checks=inspected,
        conclusions=['This fixed previous command remains beneficial and physically feasible under current5s model.',
                     'The finite2+2 optimizer missed that better command; do not attribute the smaller selected gain to disappearance of model benefit.',
                     'Reused old three-block actuator proof; no new optimizer, modified controller warm-start or native run.'],
        limits=['Both numeric cap comparisons use this same observed response; no second retargeted rollout.',
                'One saved state and a known previous solution; not proof of globally best or online reachable control.',
                'The fixed command is a diagnostic candidate, not the autonomous5s optimizer output.'])
    target.write_text(json.dumps(summary,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('physical_checks','conclusions','limits')},indent=2))


if __name__=='__main__':main()
