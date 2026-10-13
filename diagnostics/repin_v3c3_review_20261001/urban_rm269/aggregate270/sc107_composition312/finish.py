"""Persist diagnosis and next structural action without altering live runs."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json

HERE=Path(__file__).resolve().parent;A=HERE.parent;H=A.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_bytes())


def main():
    report=read(HERE/'assessment.json')
    assert all(sha(p)==h for p,h in report['source_pins'].items())
    assert report['current_right_reachable_count']==0 and report['current_stopped_count']==26
    assert report['geometry']['through']['lanes']==[2,3,4,5]
    assert 'Ran 6 tests' in (HERE/'tests_all_v2.log').read_text(encoding='utf8')
    now=datetime.now(timezone.utc).isoformat()
    done=dict(status=report['status'],goal_complete=False,production_adopted=False,native_changed=False,
        previous_goal_turn='no_progress: clock clarification reused completed evidence without changing model or validation',
        this_goal_turn='progress: retained pre2400 route evidence, corrected connector-lane interpretation, confirmed impossible current right queue and unrepresented phase5-to-through service;6diagnostic tests; native future used only for diagnosis',
        updated_utc=now,budget=report['budget'],source_pins={str(p):sha(p) for p in HERE.iterdir() if p.suffix in ('.py','.md','.json','.log')},
        native_launches=0,full_forecasts=0,full_ad=0,full_selections=0,coefficient_fits=0,pushes=0,
        next_step=report['next_action'])
    target=HERE/'completion.json';assert not target.exists();target.write_text(json.dumps(done,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    for p in (A/'plan.json',H/'plan.json'):
        backup=p.with_name('plan.before312.json');assert not backup.exists();backup.write_bytes(p.read_bytes())
        d=read(p);d.update(current_stage='sc107_position_phase_contract312_confirmed_not_repaired',goal_complete=False,current_workers=[],updated_utc=now,
            latest_stage=str(HERE/'README.md'),next_step=report['next_action'],
            latest_goal_turn_audit=dict(previous=done['previous_goal_turn'],current=done['this_goal_turn']))
        d['sc107_composition312']=dict(completion=str(target),sha256=sha(target),adopted=False,status=report['status'])
        temp=p.with_suffix('.json.tmp312');temp.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8');temp.replace(p)
    print('RECORDED_SC107312 goal_complete=false production_changed=false')


if __name__=='__main__':main()
