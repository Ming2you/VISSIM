from pathlib import Path
from datetime import datetime,timezone
import hashlib,json

HERE=Path(__file__).resolve().parent;A=HERE.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    out=HERE/'completion.json';assert not out.exists()
    reports=[json.loads((HERE/n).read_bytes()) for n in ('comparison.json','timing_diagnostic.json')]
    for r in reports:
        for p,h in r['source_pins'].items():assert sha(p)==h,p
    assert 'Ran 6 tests' in (HERE/'tests.log').read_text(encoding='utf8')
    now=datetime.now(timezone.utc).isoformat()
    complete=dict(status=reports[0]['status'],goal_complete=False,production_adopted=False,
        previous_goal_turn='no progress toward gain goal: user clock question answered from existing evidence; no blocker',
        current_goal_turn='progress: completed316 pair reviewed and independently reconciled downstream delayed arrivals; identifies transit-dependent travel distance for bounded geometry diagnosis',
        updated_utc=now,current_workers=[],closed_tool_session=29602,execution_exit_code=0,
        budget=reports[0]['budget'],next_step='One bounded source-path delay comparison; preserve initial calendars, flow receiving, no outcome-fitted coefficient.',
        source_pins={str(p):sha(p) for p in HERE.iterdir() if p.suffix in ('.py','.json','.md','.log')})
    out.write_text(json.dumps(complete,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for path in (A/'plan.json',A.parent/'plan.json'):
        backup=path.with_name('plan.before316.json');assert not backup.exists();backup.write_bytes(path.read_bytes())
        d=json.loads(path.read_bytes());d.update(current_stage='shared316_transport_timing_reconciled_gain_unqualified',latest_stage=str(HERE/'README.md'),
            current_workers=[],goal_complete=False,updated_utc=now,next_step=complete['next_step'],
            latest_goal_turn_audit=dict(previous=complete['previous_goal_turn'],current=complete['current_goal_turn']))
        d['sc107_shared316']=dict(status=complete['status'],completion=str(out),sha256=sha(out),adopted=False)
        temp=path.with_suffix('.tmp316.json');temp.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8');temp.replace(path)
    print('RECORDED316: shared flow improved, whole gain unqualified; no worker active.')

if __name__=='__main__':main()
