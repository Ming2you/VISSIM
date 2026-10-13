"""Persist reviewed finite work and its remaining scope; no new computation."""
import hashlib,json
from pathlib import Path
from datetime import datetime,timezone
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
read=lambda p:json.loads(p.read_bytes())
save=lambda p,v:p.write_text(json.dumps(v,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf8')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
response=read(HERE/'response_review.json');selection=read(HERE/'full_selection_review.json')
assert selection['status']=='complete_decision_reviewed'
assert all(sha(Path(p))==h for p,h in response['source_pins'].items())
previous=read(HERE.parent/'urban_clock276/plan.json');pins=dict(previous['source_pins'])
for backup in HERE.glob('*.py.before'):
    rel='evaluation/controllers/'+backup.name[:-7]
    if rel in pins:assert sha(backup)==pins[rel],rel
    pins[rel]=sha(ROOT/rel)
pins['evaluation/controllers/multirate_coupling.py']=sha(ROOT/'evaluation/controllers/multirate_coupling.py')
plan=dict(status='fw5_urban10_one_state_decision_verified',goal_status='active_not_complete',
    updated_utc=datetime.now(timezone.utc).isoformat(),prediction_clock=dict(freeway_sec=5,urban_sec=10),
    control_sec=150,horizon_sec=450,terminal_cost='OFF',area='Omega701',native_clock_changed=False,
    config='config_fw5_urban10.json',source_pins=pins,
    test_source_pins={p.relative_to(ROOT).as_posix():sha(p) for p in (ROOT/'tests').glob('test_multirate_*.py')},
    tests_passed=78,scalar_ad_max_error=max(response['scalar_ad_errors'].values()),
    default_urban1_max_error=max(response['default_urban1_errors'].values()),
    full_decision=dict(wall_sec=selection['measured_whole_check_wall_sec'],target_sec=600,
        target_met=True,iterations_each=2,converged=selection['converged'],
        best_observed_feasible=True,total_predictions=selection['query_stats']['total_rollouts']),
    evidence=['response_review.json','full_selection_review.json','tests.log'],
    diagnostic_failures_preserved=['interval_v1.json','hold_v1_prelaunch_failure.txt','hold_v2_execution.json'],
    superseded_predictions=['hold_v3','hold_v4','release_v1','release_v2'],
    final_prediction_labels=['hold_v5','release_v3','hold_ad_v1','default_v1'],
    full_decisions=1,native_runs=0,pushes=0,current_workers=[],
    native_defaults_changed=False,whole_model_qualification=False,
    next_step='Retain opted-in FW5/urban10 candidate. Reuse this timing/gain evidence. Check a different saved state and VSL action direction before native adoption; do not repeat unchanged full selection. Prior3300s urban52/58 stock-direction error remains a distinct dynamics issue. No new native or push in this work.',
    limitations=response['limitations']+selection['limits'])
save(HERE/'plan.json',plan)
previous['followup_plan']='../urban_clock277/plan.json';save(HERE.parent/'urban_clock276/plan.json',previous)
aggregate=read(HERE.parent/'plan.json');aggregate['latest_clock_plan']='urban_clock277/plan.json'
save(HERE.parent/'plan.json',aggregate)
print(json.dumps({k:plan[k] for k in ('status','goal_status','full_decision','current_workers','native_runs')}))
