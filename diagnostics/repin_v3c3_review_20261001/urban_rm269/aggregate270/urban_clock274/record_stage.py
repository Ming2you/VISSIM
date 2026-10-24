"""Record completed evidence; do not dispatch any prediction or native run."""
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
load=lambda p:json.loads(p.read_bytes())
save=lambda p,x:p.write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
evidence=load(HERE/'saved_calendar.json')
assert evidence['status']=='complete_reviewed'
assert all(sha(ROOT/p)==h for p,h in evidence['source_pins'].items())
plan=dict(status='urban_calendar10_rebase_verified_whole_scheduler_pending',goal_status='active_not_complete',
    updated_utc=datetime.now(timezone.utc).isoformat(),source_pins=evidence['source_pins'],
    evidence=['saved_calendar.json'],tests=dict(passed=45,seconds=.90,
        files=['test_multirate_urban_clock.py','test_multirate_shared_approach.py','test_aggregate_wout.py','test_aggregate_route_corridors.py'],
        regression_failures_before_fix=2),prediction_clock=dict(freeway_sec=5,urban_sec=1),
    prepared_urban_tick_sec=10,whole_urban_scheduler_qualified=False,current_workers=[],
    native_runs=0,full_rollouts=0,full_sdmpc_selections=0,
    next_step='Connect ordinary off-ramp/local CTM drainage and a real5/10coupled scheduler with a single accepted-flow budget and physical residence cost. Do not enable rebase alone in the old nested scheduler.',
    targets=dict(urban_sec=10,whole_decision_sec=600,horizon_sec=450,terminal_cost='OFF',area='Omega701'))
plan['test_source_pins']={f'tests/{p}':sha(ROOT/'tests'/p) for p in plan['tests']['files']}
plan['prior_sources']={p:sha(HERE/p) for p in ('aggregate_wout_before.py','aggregate_route_corridors_before.py')}
save(HERE/'plan.json',plan)
previous_path=HERE.parent/'urban_clock273/plan.json'
previous=load(previous_path);previous['followup_plan']='../urban_clock274/plan.json';save(previous_path,previous)
parent_path=HERE.parent/'plan.json';parent=load(parent_path)
parent.update(status='fw5_retained_urban10_calendar_prepared_whole_scheduler_pending',
    latest_clock_plan='urban_clock274/plan.json',
    current_prediction_clock=dict(freeway_sec=5,urban_sec=1,urban10_prepared_not_activated=True),
    last_goal_turn=dict(status='progress_completed_calendar_rebase_and_physical_clock_tests',
        record='urban_clock274/plan.json',native_runs=0,full_rollouts=0,full_sdmpc_selections=0))
save(parent_path,parent)
print(json.dumps(dict(status=plan['status'],pins_verified=len(plan['source_pins']),tests=45),ensure_ascii=False))
