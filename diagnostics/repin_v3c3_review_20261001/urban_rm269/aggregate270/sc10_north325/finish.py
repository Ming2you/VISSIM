from pathlib import Path
from datetime import datetime,timezone
import hashlib,json

HERE=Path(__file__).resolve().parent;A=HERE.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    out=HERE/'completion.json';assert not out.exists()
    report=json.loads((HERE/'review.json').read_bytes())
    for p,h in report['source_pins'].items():assert sha(p)==h,p
    log=(HERE/'tests.log').read_text(encoding='utf8');assert 'Ran 6 tests' in log and 'OK' in log
    run=(HERE/'run.log').read_text(encoding='utf8');assert 'SC108_GEOMETRY311 hold' in run and 'SC108_GEOMETRY311 city' in run
    now=datetime.now(timezone.utc).isoformat()
    done=dict(status=report['status'],goal_complete=False,production_adopted=False,current_workers=[],
        previous_goal_turn='progress324_same_initial_platoon_middle_signal_bypass_reproduced',
        this_goal_turn='progress325_aggregate_fixed_middle_signal_and_current_routes_6tests_two450_local_loss_direction_whole_gain_unqualified',
        closed_tool_session=74548,execution_exit_code=0,budget=report['budget'],
        delta_omega_veh_h=report['delta_omega_veh_h'],updated_utc=now,next_step=report['next_step'],
        source_pins={str(p):sha(p) for p in HERE.iterdir() if p.suffix in ('.py','.json','.log','.md')})
    out.write_text(json.dumps(done,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for path in (A/'plan.json',A.parent/'plan.json'):
        backup=path.with_name('plan.before325.json');assert not backup.exists();backup.write_bytes(path.read_bytes())
        d=json.loads(path.read_bytes());d.update(current_stage='sc10_north325_local_missed_green_loss_whole_gain_still_unqualified',
            latest_stage=str(HERE/'README.md'),current_workers=[],goal_complete=False,updated_utc=now,next_step=done['next_step'],
            latest_goal_turn_audit=dict(previous=done['previous_goal_turn'],current=done['this_goal_turn']))
        d['sc10_north325']=dict(status=done['status'],completion=str(out),sha256=sha(out),adopted=False)
        tmp=path.with_suffix('.tmp325.json');tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8');tmp.replace(path)
    print('RECORDED325: six tests/two predictions complete; no production adoption; goal active.')

if __name__=='__main__':main()
