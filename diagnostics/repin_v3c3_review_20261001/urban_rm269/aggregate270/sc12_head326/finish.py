from pathlib import Path
from datetime import datetime,timezone
import hashlib,json

HERE=Path(__file__).resolve().parent;A=HERE.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    out=HERE/'completion.json';assert not out.exists()
    r=json.loads((HERE/'review.json').read_bytes())
    for p,h in r['source_pins'].items():assert sha(p)==h,p
    t=(HERE/'tests.log').read_text(encoding='utf8');assert 'Ran 6 tests' in t and 'OK' in t
    log=(HERE/'run.log').read_text(encoding='utf8');assert 'SC108_GEOMETRY311 hold' in log and 'SC108_GEOMETRY311 city' in log
    now=datetime.now(timezone.utc).isoformat()
    done=dict(status=r['status'],goal_complete=False,production_adopted=False,current_workers=[],
        previous_goal_turn='progress325_aggregate_middle_signal_local_direction_whole_gain_unqualified',
        this_goal_turn='progress326_physical_shared_member_caps_six_tests_two450_not_adopted',
        closed_tool_session=24313,execution_exit_code=0,budget=r['budget'],updated_utc=now,
        delta_omega_veh_h=r['delta_omega_veh_h'],next_step=r['next_step'],
        source_pins={str(p):sha(p) for p in HERE.iterdir() if p.suffix in ('.py','.json','.log','.md')})
    out.write_text(json.dumps(done,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for path in (A/'plan.json',A.parent/'plan.json'):
        backup=path.with_name('plan.before326.json');assert not backup.exists();backup.write_bytes(path.read_bytes())
        d=json.loads(path.read_bytes());d.update(current_stage='sc12_head326_shared_service_not_sufficient_whole_gain_unqualified',
            latest_stage=str(HERE/'README.md'),current_workers=[],goal_complete=False,updated_utc=now,
            next_step=done['next_step'],latest_goal_turn_audit=dict(previous=done['previous_goal_turn'],current=done['this_goal_turn']))
        d['sc12_head326']=dict(status=done['status'],completion=str(out),sha256=sha(out),adopted=False)
        tmp=path.with_suffix('.tmp326.json');tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8');tmp.replace(path)
    print('RECORDED326:6 tests,2 predictions; candidate not adopted; active goal incomplete; no workers.')

if __name__=='__main__':main()
