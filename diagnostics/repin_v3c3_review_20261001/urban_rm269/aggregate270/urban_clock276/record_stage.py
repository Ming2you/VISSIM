import hashlib,json
from pathlib import Path
from datetime import datetime,timezone
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
save=lambda p,x:p.write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
check=json.loads((HERE/'default_execution.json').read_bytes())
assert check['status']=='complete_reviewed' and check['exit_code']==0
assert all(sha(ROOT/p)==h for p,h in check['source_pins'].items())
component=json.loads((HERE/'saved_local.json').read_bytes())
reverse=json.loads((HERE/'reverse_local.json').read_bytes())
assert component['canonical_stock_ledger_pass'] and reverse['derivative_error']<1e-5
plan=dict(status='local_ctm10_exchange_verified_whole_scheduler_pending',goal_status='active_not_complete',
    updated_utc=datetime.now(timezone.utc).isoformat(),previous_turn='status_only_revalidated275_before_current_changes',
    current_turn='progress_local_clock_endpoint_receipts_actual_saved_state_AD_and_default450_verified',
    source_pins=check['source_pins'],test_source_pins={'tests/test_multirate_local_clock.py':sha(ROOT/'tests/test_multirate_local_clock.py')},
    evidence=['saved_local.json','reverse_local.json','default_execution.json'],
    tests=dict(regression_suite_passed=56,final_local_suite_passed=5,unique_tests=58),
    prediction_clock=dict(freeway_sec=5,urban_sec=1),prepared_urban_tick_sec=10,
    local_numerical_sec=1,whole_urban_scheduler_qualified=False,
    full_rollouts=1,full_sdmpc_selections=0,native_runs=0,current_workers=[],
    next_step='Wire the actual5/10 scheduler, shared-head ordering, intermediate freeway landing and single accepted-flow budgets; explicitly integrate Omega residence across numerical substeps before full-state/gain testing.',
    targets=dict(urban_sec=10,whole_decision_sec=600,horizon_sec=450,terminal_cost='OFF',area='Omega701'))
save(HERE/'plan.json',plan)
previous=HERE.parent/'urban_clock275/plan.json';data=json.loads(previous.read_bytes())
data['followup_plan']='../urban_clock276/plan.json';save(previous,data)
aggregate=HERE.parent/'plan.json';data=json.loads(aggregate.read_bytes())
data['latest_clock_plan']='urban_clock276/plan.json';save(aggregate,data)
print(json.dumps({'status':plan['status'],'source_pins':len(plan['source_pins']),'goal':'active','current_workers':[]}))
