from pathlib import Path
from datetime import datetime,timezone
import hashlib,json

HERE=Path(__file__).resolve().parent;A=HERE.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    out=HERE/'completion.json';assert not out.exists()
    report=json.loads((HERE/'review.json').read_bytes())
    for p,h in report['source_pins'].items():assert sha(p)==h,p
    assert 'Ran 5 tests' in (HERE/'tests.log').read_text(encoding='utf8') and 'OK' in (HERE/'tests.log').read_text(encoding='utf8')
    assert 'SC108_GEOMETRY311 city' in (HERE/'run.log').read_text(encoding='utf8')
    now=datetime.now(timezone.utc).isoformat()
    done=dict(status=report['status'],goal_complete=False,adopted=False,current_workers=[],
        previous_goal_turn='progress_city322_three_head_operand_diagnosis',
        this_goal_turn='progress_single_past_aggregate_candidate_5tests_two450_no_material_gain_improvement',
        closed_tool_session=12710,execution_exit_code=0,budget=report['budget'],
        delta_omega_veh_h=report['delta_omega_veh_h'],updated_utc=now,next_step=report['next_step'],
        source_pins={str(p):sha(p) for p in HERE.iterdir() if p.suffix in ('.py','.json','.log','.md')})
    out.write_text(json.dumps(done,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for path in (A/'plan.json',A.parent/'plan.json'):
        backup=path.with_name('plan.before323.json');assert not backup.exists();backup.write_bytes(path.read_bytes())
        d=json.loads(path.read_bytes());d.update(current_stage='sc16_323_level_improved_gain_still_limited_by_upstream_response',
            latest_stage=str(HERE/'README.md'),current_workers=[],goal_complete=False,updated_utc=now,next_step=done['next_step'],
            latest_goal_turn_audit=dict(previous=done['previous_goal_turn'],current=done['this_goal_turn']))
        d['sc16_aggregate323']=dict(status=done['status'],completion=str(out),sha256=sha(out),adopted=False)
        tmp=path.with_suffix('.tmp323.json');tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8');tmp.replace(path)
    print('RECORDED323: bounded aggregate candidate completed; no material gain qualification; goal active.')

if __name__=='__main__':main()
