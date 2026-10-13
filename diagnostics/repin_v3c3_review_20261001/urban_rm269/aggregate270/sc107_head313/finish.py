from pathlib import Path
from datetime import datetime,timezone
import json,hashlib

HERE=Path(__file__).resolve().parent;A=HERE.parent;H=A.parent
read=lambda p:json.loads(Path(p).read_bytes())
def sha(p):
    p=Path(p)
    if not p.is_absolute():p=HERE.parents[4]/p
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    report=read(HERE/'comparison.json');assert not report['adopted']
    for p,h in report['source_pins'].items():assert sha(p)==h,p
    assert report['absolute_error_reduction']<0
    assert all(r['shared_constraints']['feasible'] for r in report['results']['new'].values())
    assert 'Ran 7 tests' in (HERE/'tests_v3.log').read_text(encoding='utf8')
    unseen=read(HERE/'unseen_initial3300.json');assert unseen['status']=='initial_projection_pass_only'
    for p,h in unseen['source_pins'].items():assert sha(p)==h,p
    now=datetime.now(timezone.utc).isoformat()
    complete=dict(status=report['status'],goal_complete=False,production_adopted=False,current_workers=[],
        previous_goal_turn='progress: positional and head-phase mismatch confirmed from existing geometry and observations',
        this_goal_turn='progress: current-head candidate integrated with receiving/Omega/unique owner;7tests+unseen initial check;2retained450responses reject whole-gain adoption;future head diagnosis demonstrates dynamic lane access is missing',
        updated_utc=now,tests_passed=7,budget=report['budget'],owned_tool_sessions_closed=[21666,77124,37723],
        final_execution_exit_code=0,delta_omega=report['delta_omega_veh_h'],native_delta=report['native_delta_omega_veh_h'],
        next_step=report['next_action'],source_pins={str(p):sha(p) for p in HERE.iterdir() if p.suffix in ('.py','.md','.json','.log')})
    dest=HERE/'completion.json';assert not dest.exists();dest.write_text(json.dumps(complete,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for p in (A/'plan.json',H/'plan.json'):
        backup=p.with_name('plan.before313.json');assert not backup.exists();backup.write_bytes(p.read_bytes())
        d=read(p);d.update(current_stage='sc107_current_head313_not_adopted_dynamic_lane_access_missing',goal_complete=False,current_workers=[],updated_utc=now,
            latest_stage=str(HERE/'README.md'),next_step=report['next_action'],latest_goal_turn_audit=dict(previous=complete['previous_goal_turn'],current=complete['this_goal_turn']))
        d['sc107_head313']=dict(status=report['status'],completion=str(dest),sha256=sha(dest),adopted=False)
        temp=p.with_suffix('.json.tmp313');temp.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8');temp.replace(p)
    print('RECORDED313: goal active, candidate not adopted, all workers closed')


if __name__=='__main__':main()
