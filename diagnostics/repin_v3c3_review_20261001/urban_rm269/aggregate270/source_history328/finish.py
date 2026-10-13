from pathlib import Path
from datetime import datetime,timezone
import hashlib,json

HERE=Path(__file__).resolve().parent;A=HERE.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    out=HERE/'completion.json';assert not out.exists()
    r=json.loads((HERE/'assessment.json').read_bytes())
    for p,h in r['source_pins'].items():assert sha(p)==h,p
    t=(HERE/'tests.log').read_text(encoding='utf8');assert 'Ran 5 tests' in t and 'OK' in t
    now=datetime.now(timezone.utc).isoformat()
    next_step='Do not search more source averaging windows or transplant Claude4189. Review accepted future urban traffic route composition and arrival scheduling against current native static routing and Claude U7; distinguish initial current-route preservation from future source-conditioned routing. Identify an actual route/time contract mismatch before one aggregate correction. SameFW5/urban10/horizon450/terminalOFF/Omega; no unchanged optimizer or native repeat.'
    done=dict(status='complete_source_history328_partial_MAE_improvement_not_adopted',
        previous_goal_turn='progress327_exact_cost_and_initial_roster_decomposition',
        this_goal_turn='progress328_one_causal_source_estimator_five_tests_six_walk_forward_origins',
        goal_complete=False,production_adopted=False,current_workers=[],execution_exit_code=0,
        metrics=r['metrics'],budget=r['budget'],tests=5,next_step=next_step,updated_utc=now,
        source_pins={str(p):sha(p) for p in HERE.iterdir() if p.suffix in ('.py','.json','.log','.md')})
    out.write_text(json.dumps(done,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for path in (A/'plan.json',A.parent/'plan.json'):
        backup=path.with_name('plan.before328.json');assert not backup.exists();backup.write_bytes(path.read_bytes())
        d=json.loads(path.read_bytes());d.update(current_stage='source_history328_partial_improvement_not_adopted_future_urban_routes_next',
            latest_stage=str(HERE/'README.md'),current_workers=[],goal_complete=False,updated_utc=now,next_step=next_step,
            latest_goal_turn_audit=dict(previous=done['previous_goal_turn'],current=done['this_goal_turn']))
        d['source_history328']=dict(status=done['status'],completion=str(out),sha256=sha(out),adopted=False)
        tmp=path.with_suffix('.tmp328.json');tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8');tmp.replace(path)
    print('RECORDED328: one source estimator,5 tests,6 forward origins; not adopted; goal active/incomplete.')

if __name__=='__main__':main()
