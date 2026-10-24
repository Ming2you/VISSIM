from pathlib import Path
from datetime import datetime,timezone
import hashlib
import json

HERE=Path(__file__).resolve().parent
A=HERE.parent


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    output=HERE/'completion.json'
    assert not output.exists()
    reports=[json.loads((HERE/n).read_bytes()) for n in ('audit.json','review.json')]
    for report in reports:
        for p,h in report['source_pins'].items():assert sha(p)==h,p
    assert 'Ran 3 tests' in (HERE/'tests.log').read_text(encoding='utf8')
    assert 'SOURCE318_DONE' in (HERE/'run.log').read_text(encoding='utf8')
    now=datetime.now(timezone.utc).isoformat()
    next_step=('Corrected source admissions differ by East46/West4 under the same schedule; future-boundary conditioning changes model city-minus-hold TTT from-0.7335 to+1.8715 versus native+5.2867. '
               'Do not fit this future information or claim autonomous gain qualification. Before further local coefficients, separate upstream platoon arrival timing from SC109 own discharge with existing closed SC108/SC109 head-time/position caches; retain source-forecast uncertainty in choice validation. '
               'No repeated unchanged optimization, coefficient grid or additional full native run. Keep FW5/U10, Omega701, horizon450 terminalOFF and immutable queue.')
    complete=dict(status=reports[1]['status'],goal_complete=False,production_adopted=False,
        previous_goal_turn='no progress: clock status explanation only; no blocker',
        this_goal_turn='progress: canonical source identity audit corrects admission counts;3tests and2conditional450s forecasts separate material source error from remaining urban exit timing',
        updated_utc=now,current_workers=[],closed_tool_session=44401,execution_exit_code=0,
        budget=reports[1]['budget'],next_step=next_step,
        source_pins={str(p):sha(p) for p in HERE.iterdir() if p.suffix in ('.py','.json','.md','.log')})
    output.write_text(json.dumps(complete,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for path in (A/'plan.json',A.parent/'plan.json'):
        backup=path.with_name('plan.before318.json')
        assert not backup.exists()
        backup.write_bytes(path.read_bytes())
        plan=json.loads(path.read_bytes())
        plan.update(current_stage='source318_boundary_conditioning_explains_wrong_sign_autonomous_gain_unqualified',
                    latest_stage=str(HERE/'README.md'),current_workers=[],goal_complete=False,
                    updated_utc=now,next_step=next_step,
                    latest_goal_turn_audit=dict(previous=complete['previous_goal_turn'],current=complete['this_goal_turn']))
        plan['source_boundary318']=dict(status=complete['status'],completion=str(output),sha256=sha(output),adopted=False)
        temp=path.with_suffix('.tmp318.json')
        temp.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        temp.replace(path)
    print('RECORDED318: source-count correction and conditional evidence saved; goal active incomplete; no active offline worker.')


if __name__=='__main__':main()
