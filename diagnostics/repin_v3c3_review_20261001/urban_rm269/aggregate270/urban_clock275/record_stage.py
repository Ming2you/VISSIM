"""Record completed boundary evidence without launching calculations."""
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
load=lambda p:json.loads(p.read_bytes())
save=lambda p,x:p.write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
e=load(HERE/'saved_drain_batched.json');ad=load(HERE/'reverse_boundary.json')
assert e['status']=='complete_reviewed' and ad['status']=='passed_three_transformed_boundary_cases'
assert all(sha(ROOT/p)==h for p,h in e['source_pins'].items())
tests=['test_multirate_offramp_drain.py','test_multirate_urban_clock.py',
       'test_multirate_shared_approach.py','test_aggregate_wout.py','test_aggregate_route_corridors.py']
plan=dict(status='ordinary_offramp10_boundary_verified_whole_scheduler_pending',goal_status='active_not_complete',
    updated_utc=datetime.now(timezone.utc).isoformat(),previous_goal_turn='progress_calendar_rebase_and_physical_clock_tests_completed',
    source_pins=e['source_pins'],test_source_pins={f'tests/{p}':sha(ROOT/'tests'/p) for p in tests},
    evidence=['saved_drain_batched.json','reverse_boundary.json'],
    previous_boundary_experiment='saved_drain.json',tests=dict(passed=53,seconds=1.09),
    prediction_clock=dict(freeway_sec=5,urban_sec=1),prepared_urban_tick_sec=10,
    prepared_offramp_count=7,whole_urban_scheduler_qualified=False,
    native_runs=0,full_rollouts=0,full_sdmpc_selections=0,current_workers=[],
    next_step='Connect local CTM numerical substeps, canonical shared-head ordering, and the actual5/10scheduler with one finite accepted-flow budget, endpoint arrivals and Omega residence. Current runtime clock remains5/1.',
    targets=dict(urban_sec=10,whole_decision_sec=600,horizon_sec=450,terminal_cost='OFF',area='Omega701'))
save(HERE/'plan.json',plan)
p=HERE.parent/'urban_clock274/plan.json';before=load(p);before['followup_plan']='../urban_clock275/plan.json';save(p,before)
p=HERE.parent/'plan.json';parent=load(p)
parent.update(status='fw5_retained_urban10_ordinary_offramp_verified_whole_scheduler_pending',
    latest_clock_plan='urban_clock275/plan.json',
    current_prediction_clock=dict(freeway_sec=5,urban_sec=1,urban10_prepared_not_activated=True),
    last_goal_turn=dict(status='progress_completed_ordinary_offramp10_boundary_and_AD_validation',
        record='urban_clock275/plan.json',native_runs=0,full_rollouts=0,full_sdmpc_selections=0))
save(p,parent)
print(json.dumps(dict(status=plan['status'],pins_verified=len(plan['source_pins']),tests=53),ensure_ascii=False))
