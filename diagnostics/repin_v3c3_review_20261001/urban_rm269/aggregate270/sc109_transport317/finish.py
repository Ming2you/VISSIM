from pathlib import Path
from datetime import datetime,timezone
import hashlib,json

HERE=Path(__file__).resolve().parent;A=HERE.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    out=HERE/'completion.json';assert not out.exists()
    reports=[json.loads((HERE/n).read_bytes()) for n in ('comparison.json','past_head_bound.json','residual_budget.json')]
    for report in reports:
        for p,h in report['source_pins'].items():assert sha(p)==h,p
    assert 'Ran 6 tests' in (HERE/'tests.log').read_text(encoding='utf8')
    assert 'SC108_GEOMETRY311 city' in (HERE/'run.log').read_text(encoding='utf8')
    now=datetime.now(timezone.utc).isoformat()
    next_step='Before further cell/service fitting, distinguish actual freeway insertion variation from receiving/observation errors using saved native input records; retain corrected transport diagnosis and focus on material exit-timing residuals. No unchanged optimization, full native rerun, or coefficient grid.'
    complete=dict(status=reports[0]['status'],goal_complete=False,production_adopted=False,
        previous_goal_turn='no progress: clock explanation only; no blocker',
        this_goal_turn='progress:316 recorded; geometry-based transport implemented and6tests+two450s forecasts completed; exact whole boundary budget changes next diagnostic priority',
        updated_utc=now,current_workers=[],closed_tool_session=28283,execution_exit_code=0,
        budget=reports[0]['budget'],delta_omega_veh_h=reports[0]['delta_omega_veh_h'],next_step=next_step,
        source_pins={str(p):sha(p) for p in HERE.iterdir() if p.suffix in ('.py','.json','.md','.log')})
    out.write_text(json.dumps(complete,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for path in (A/'plan.json',A.parent/'plan.json'):
        backup=path.with_name('plan.before317.json');assert not backup.exists();backup.write_bytes(path.read_bytes())
        d=json.loads(path.read_bytes());d.update(current_stage='transport317_local_improvement_whole_boundary_budget_pending',latest_stage=str(HERE/'README.md'),
            current_workers=[],goal_complete=False,updated_utc=now,next_step=next_step,
            latest_goal_turn_audit=dict(previous=complete['previous_goal_turn'],current=complete['this_goal_turn']))
        d['sc109_transport317']=dict(status=complete['status'],completion=str(out),sha256=sha(out),adopted=False)
        temp=path.with_suffix('.tmp317.json');temp.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8');temp.replace(path)
    print('RECORDED317: goal active incomplete;2forecasts completed; no active owned offline worker; native unchanged.')

if __name__=='__main__':main()
