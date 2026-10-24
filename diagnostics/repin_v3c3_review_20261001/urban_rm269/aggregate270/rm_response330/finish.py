from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
HERE=Path(__file__).resolve().parent;A=HERE.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    output=HERE/'completion.json';assert not output.exists()
    r=json.loads((HERE/'assessment.json').read_bytes())
    for p,h in r['source_pins'].items():assert sha(p)==h,p
    t=(HERE/'tests.log').read_text(encoding='utf8')
    assert 'Ran 3 tests' in t and 'OK' in t
    log=(HERE/'run_v2.log').read_text(encoding='utf8')
    assert 'RM_RESPONSE330_JOINT' in log and 'DONE330:one forecast' in log
    assert 'capture_response' in (HERE/'run.log').read_text(encoding='utf8')
    q=json.loads(Path('E:/VISSIM_runtime/20261008_coupling268_vsl_three/queue_state.json').read_bytes())
    assert q['stage']=='complete_unanalyzed' and q['native_launches']==3 and q['automatic_retries']==0
    now=datetime.now(timezone.utc).isoformat()
    next_step='Stop small RM gain/coefficient tuning: latest model preserved native RM marginal gain and major component directions. Audit transfer of the fixed accumulated aggregate model from2400 to saved3300 observations/commands, checking which geometry/current-route projection contracts are general and which diagnostic loaders hardcode2400. Reconstruct3300 with current observations only before bounded unused-state RM-response and full AD/SDMPC qualification. Do not claim329 diagnostic integration from older285 full selections; whole city/joint ranking remains open. KeepFW5/urban10,450,terminalOFF,Omega701,same demand; no unchanged native/full optimizer repeats or gain bonuses.'
    done=dict(status=r['status'],goal_complete=False,current_workers=[],production_adopted=False,
        previous_goal_turn='progress329_actual_future_route_contract_and_two_predictions_changed_next_action',
        this_goal_turn='progress330_latest_RM_vector_one_prediction_plus_cached_city_and_native_balance_validation',
        valid_output='E:/VISSIM_analysis/20261010_rm_response330/forecast2400_v2',
        closed_tool_session=18789,execution_exit_code=0,failed_pre_prediction_session=63695,
        actual_forecasts_completed=1,bootstrap_attempts=2,tests=3,budget=r['budget'],
        native_delta_omega=r['native_cost_delta']['omega'],model_delta_omega=r['model_cost_delta']['omega'],
        ramp10681=r['ramp_merges']['RM_C10681'],next_step=next_step,updated_at=now,
        source_pins={str(p):sha(p) for p in HERE.iterdir() if p.suffix in ('.py','.md','.json','.log')})
    output.write_text(json.dumps(done,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for path in (A/'plan.json',A.parent/'plan.json'):
        backup=path.with_name('plan.before330.json');assert not backup.exists();backup.write_bytes(path.read_bytes())
        d=json.loads(path.read_bytes())
        d.update(current_stage='rm_response330_direction_preserved_unused_state_integration_audit_next',
            latest_stage=str(HERE/'README.md'),current_workers=[],goal_complete=False,updated_at=now,next_step=next_step,
            latest_goal_turn_audit=dict(previous=done['previous_goal_turn'],current=done['this_goal_turn']))
        d['rm_response330']=dict(status=done['status'],completion=str(output),sha256=sha(output),adopted=False,
            native_delta_omega=done['native_delta_omega'],model_delta_omega=done['model_delta_omega'])
        tmp=path.with_suffix('.tmp330.json');tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8');tmp.replace(path)
    print('RECORDED330:RM gain direction preserved;1 forecast,3tests;wholecity/unused-state/integration still open;goal active.')

if __name__=='__main__':main()

