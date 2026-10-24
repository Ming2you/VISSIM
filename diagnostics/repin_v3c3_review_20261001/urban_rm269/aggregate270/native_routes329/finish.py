from pathlib import Path
from datetime import datetime,timezone
import hashlib,json

HERE=Path(__file__).resolve().parent;A=HERE.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    out=HERE/'completion.json';assert not out.exists()
    r=json.loads((HERE/'assessment.json').read_bytes())
    for p,h in r['source_pins'].items():assert sha(p)==h,p
    t=(HERE/'tests.log').read_text(encoding='utf8');assert 'Ran 6 tests' in t and 'OK' in t
    log=(HERE/'run.log').read_text(encoding='utf8')
    assert 'SC108_GEOMETRY311 hold' in log and 'SC108_GEOMETRY311 city' in log and 'DONE329' in log
    q=json.loads(Path('E:/VISSIM_runtime/20261008_coupling268_vsl_three/queue_state.json').read_bytes())
    assert q['stage']=='complete_unanalyzed' and q['freeze_count']==1 and q['native_launches']==3 and q['automatic_retries']==0
    now=datetime.now(timezone.utc).isoformat()
    done=dict(status=r['status'],goal_complete=False,production_adopted=False,current_workers=[],
        previous_goal_turn='progress328_source_history_diagnostic; intervening user answer was a clock status explanation without new computation',
        this_goal_turn='progress329_declared_source_routes_and_eligibility_six_tests_two450_gain_effect_negligible',
        closed_tool_session=15000,execution_exit_code=0,budget=r['budget'],updated_at=now,
        delta_omega_veh_h=r['delta_omega_veh_h'],native_delta_omega_veh_h=r['native_delta_omega_veh_h'],
        next_step=r['next_step'],queue_preserved=dict(stage=q['stage'],freeze_count=1,native_launches=3,automatic_retries=0),
        source_pins={str(p):sha(p) for p in HERE.iterdir() if p.suffix in ('.py','.json','.log','.md')})
    out.write_text(json.dumps(done,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for path in (A/'plan.json',A.parent/'plan.json'):
        backup=path.with_name('plan.before329.json');assert not backup.exists();backup.write_bytes(path.read_bytes())
        d=json.loads(path.read_bytes());d.update(current_stage='native_routes329_effect_negligible_latest_RM_contrast_next',
            latest_stage=str(HERE/'README.md'),current_workers=[],goal_complete=False,updated_at=now,
            next_step=done['next_step'],latest_goal_turn_audit=dict(previous=done['previous_goal_turn'],current=done['this_goal_turn']))
        d['native_routes329']=dict(status=done['status'],completion=str(out),sha256=sha(out),adopted=False)
        tmp=path.with_suffix('.tmp329.json');tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8');tmp.replace(path)
    print('RECORDED329:6 tests,2 forecasts; native route contract proved for2sources; whole gain remains unqualified; goal active.')

if __name__=='__main__':main()

