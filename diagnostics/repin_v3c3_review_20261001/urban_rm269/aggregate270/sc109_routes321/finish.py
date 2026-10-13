from pathlib import Path
from datetime import datetime,timezone
import hashlib,json

HERE=Path(__file__).resolve().parent;A=HERE.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    out=HERE/'completion.json';assert not out.exists()
    reports=[json.loads((HERE/n).read_bytes()) for n in ('review.json','unseen_initial3300.json')]
    for r in reports:
        for p,h in r['source_pins'].items():assert sha(p)==h,p
    assert 'Ran 5 tests' in (HERE/'tests.log').read_text(encoding='utf8')
    assert 'SC108_GEOMETRY311 city' in (HERE/'run.log').read_text(encoding='utf8')
    now=datetime.now(timezone.utc).isoformat()
    next_step='Stop SC109-only coefficient/ETA tuning: current known-route projection is corrected and its exit timing-cost direction is now loss(+0.1704 vs native+0.9734), but whole city response remains wrong(-0.3291 vs native+5.2867) and exit counts differ. Use retained native/head/arrival/phase records to separate missing city-loss response at SC6 south-through(1210018302->10205),SC101 south-through(1220011503->10538),SC16 north-left(1210012600->10250), keeping source-admission difference318 separate. Review Claude evidence first. Check current-route NULL and decision-position semantics before generalizing initial projection; unknown prior is still a limitation, not a new future decision. After a justified aggregate correction, qualify unused-state response, full AD and feasible whole SDMPC choice within600s. Keep FW5/U10,Omega701,horizon450,terminalOFF,conservation/current route-lane/finite receiving and immutable queue. No unchanged optimizer, coefficient grid, automatic whole native run or push.'
    done=dict(status=reports[0]['status'],goal_complete=False,production_adopted=False,updated_utc=now,
              previous_goal_turn='progress: timing320 and two autonomous forecasts; known current route loss confirmed',
              this_goal_turn='progress: current initial route projection implemented;5tests/two450 forecasts/unused3300 initialization; local exit loss direction corrected but whole city loss still missing',
              current_workers=[],closed_tool_session=31508,execution_exit_code=0,budget=reports[0]['budget'],
              unused_initialization_states=1,unused_response_forecasts=0,delta_omega_veh_h=reports[0]['delta_omega_veh_h'],
              next_step=next_step,source_pins={str(p):sha(p) for p in HERE.iterdir() if p.suffix in ('.py','.json','.log','.md')})
    out.write_text(json.dumps(done,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    for path in (A/'plan.json',A.parent/'plan.json'):
        backup=path.with_name('plan.before321.json');assert not backup.exists();backup.write_bytes(path.read_bytes())
        d=json.loads(path.read_bytes());d.update(current_stage='routes321_known_initial_turns_fixed_other_city_losses_unresolved',
            latest_stage=str(HERE/'README.md'),current_workers=[],goal_complete=False,updated_utc=now,next_step=next_step,
            latest_goal_turn_audit=dict(previous=done['previous_goal_turn'],current=done['this_goal_turn']))
        d['sc109_routes321']=dict(status=done['status'],completion=str(out),sha256=sha(out),adopted=False)
        temp=path.with_suffix('.tmp321.json');temp.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8');temp.replace(path)
    print('RECORDED321: initial route loss corrected; whole goal active incomplete; no owned offline worker.')

if __name__=='__main__':main()
