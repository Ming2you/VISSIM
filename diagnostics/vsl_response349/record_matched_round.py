"""Record completed evidence; never execute a forecast or native launch."""
import csv,json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
OUT=Path('E:/VISSIM_analysis/20261011_vsl_response349')
read=lambda p:json.loads(p.read_bytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plan=read(HERE/'plan.json')
assert plan['progress']['completed_predictions']==6
results=[]
for seed in (67,71):
    path=OUT/f'matched_seed{seed}_v3';summary=read(path/'summary.json');audit=read(path/'matched_assessment.json')
    assert summary['new_predictions']==2 and summary['status']=='complete_conditional_pair'
    results.append(dict(seed=seed,start=summary['start'],path=str(path),native_delta=audit['native_delta'],model_delta=audit['model_delta'],
        same_city_rm=True,omega_links=701,known_seed_not_blind=True,latest_full_native348_validation=False))
startup=[];rows=[]
for arm in ('window','optimized','off'):
    path=OUT/f'startup_{arm}_v1';proof=read(path/'verification.json')
    assert proof['status']=='canonical_startup_replay_passed_not_native_run'
    startup.append(proof)
    with (path/'action.csv').open(encoding='utf8',newline='') as f:rows.append(list(csv.DictReader(f)))
assert rows[0]==rows[1]==rows[2]
queue=Path('E:/VISSIM_runtime/20261011_native348_vsl_three/queue_state.json');q=read(queue)
assert q['stage']=='failed_no_retry' and q['native_launches']==1
pins={str(ROOT/'evaluation/controllers'/name):sha(ROOT/'evaluation/controllers'/name)
    for name in ('runtime_setup.py','vissim_stackelberg_adapter.py')}
progress=plan['progress'];progress.update(completed_predictions=10,
    candidate_fits=0,production_edits=2,matched_pairs=results,
    matched_driver_attempts_failed_before_rollout=4,
    matched_driver_failures='Path conversion then legacy VSL alias normalization; all preserved in v1/v2, no prediction consumed.',
    native348_queue_observation={'status':q['stage'],'native_launches':q['native_launches'],'last_actual_sec':1,
        'owned_processes_closed':True,'reason':'Initial1s no-control command requested aligned FW5/urban10 prediction initialization',
        'source':str(queue),'queue_sha256':sha(queue),'queue_and_frozen_inputs_unchanged':True},
    startup_fix=dict(status='offline_verified_not_relaunched',proofs=startup,regression_tests_passed=35,
        command_rows_equal_across_conditions=74,production_source_pins=pins,
        aligned_prediction_clock_guard_retained=True,new_native_launches=0))
plan['next_step']='Resolve remaining native348 current-state projection coverage and validate regular no-control/control initialization before preparing a corrected immutable queue; preserve failed queue and original outputs, no blind retry. VSL calibration remains open: paired67 benefit nearzero, paired71 harm direction but weak. Do not repeat rejected FD24/25 or Carlson A/E grid; remaining first-round forecast budget3, fit0, selection0.'
(HERE/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
(OUT/'round_matched_summary.json').write_text(json.dumps(dict(matched=results,startup=progress['startup_fix'],queue=progress['native348_queue_observation']),ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('Recorded10 completed forecasts,0fits,0selection,0new native; startup35tests/3saved replays passed; original queue failure preserved.')
