from pathlib import Path
from datetime import datetime,timezone
import hashlib,json

HERE=Path(__file__).resolve().parent;A=HERE.parent;ROOT=HERE.parents[4]


def sha(p):
    p=Path(p)
    return hashlib.sha256((p if p.is_absolute() else ROOT/p).read_bytes()).hexdigest()


def main():
    report=json.loads((HERE/'comparison.json').read_bytes())
    heads=json.loads((HERE/'head_service_diagnostic.json').read_bytes())
    for d in (report,heads):
        for p,h in d['source_pins'].items():assert sha(p)==h,p
    assert 'Ran 5 tests' in (HERE/'tests.log').read_text(encoding='utf8')
    assert 'SC108_GEOMETRY311 city' in (HERE/'run.log').read_text(encoding='utf8')
    assert not report['adopted'] and not report['results']['new']['hold']['shared_constraints']['feasible']
    now=datetime.now(timezone.utc).isoformat()
    complete=dict(status=report['status'],goal_complete=False,production_adopted=False,
        previous_goal_turn='progress: branch service bound disproved by past flow and binding in two retained responses',
        this_goal_turn='progress: two bounded autonomous forecasts show larger supply mostly accumulates before SC107; shared physical head and unused origin-specific service independently evidenced',
        updated_utc=now,current_workers=[],owned_tool_sessions_closed=[94061],execution_exit_code=0,
        tests_passed=5,budget=report['budget'],delta_omega_veh_h=report['delta_omega_veh_h'],
        next_step=report['next_action'],source_pins={str(p):sha(p) for p in HERE.iterdir() if p.suffix in ('.py','.json','.md','.log')})
    out=HERE/'completion.json';assert not out.exists()
    out.write_text(json.dumps(complete,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for path in (A/'plan.json',A.parent/'plan.json'):
        backup=path.with_name('plan.before315.json');assert not backup.exists();backup.write_bytes(path.read_bytes())
        d=json.loads(path.read_bytes())
        d.update(current_stage='branch315_increase_stalls_at_sc107_source_partition',latest_stage=str(HERE/'README.md'),
                 current_workers=[],goal_complete=False,updated_utc=now,next_step=report['next_action'],
                 latest_goal_turn_audit=dict(previous=complete['previous_goal_turn'],current=complete['this_goal_turn']))
        d['branch_service315']=dict(status=report['status'],completion=str(out),sha256=sha(out),adopted=False)
        temporary=path.with_suffix('.tmp315.json');temporary.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8');temporary.replace(path)
    print('RECORDED315: active goal incomplete; two forecasts finished; candidate not adopted; no active offline worker.')


if __name__=='__main__':main()
