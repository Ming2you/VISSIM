"""Prepare a distinct finite queue after evidenced startup/projection repairs.

No native launch here. Preserve the failed native348 queue and its frozen tree.
"""
from pathlib import Path
import copy,hashlib,json,shutil
HERE=Path(__file__).resolve().parent;NEW=HERE.parent;ROOT=NEW.parents[1]
BASE=Path('E:/VISSIM_analysis/20261011_vsl_response349')
OLD=Path('E:/VISSIM_runtime/20261011_native348_vsl_three')
RUNTIME=Path('E:/VISSIM_runtime/20261011_native349_fixed_vsl_three')
read=lambda p:json.loads(Path(p).read_bytes())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert not RUNTIME.exists() and not (NEW/'STOP').exists()
assert not (OLD/'STOP').exists()
old_state=read(OLD/'queue_state.json')
assert old_state['stage']=='failed_no_retry' and old_state['native_launches']==1
assert old_state['conditions']['window']['last_observed_sim_sec']==1
plan=read(OLD/'plan.json');plan=copy.deepcopy(plan)
expected={'evaluation/controllers/runtime_setup.py','evaluation/controllers/vissim_stackelberg_adapter.py',
 'evaluation/controllers/calibrated_urban_runtime.py',
 'diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/sc12_initial306/candidate.py',
 'diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/corridor339/project.py',
 'diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/sc105_initial340/candidate.py'}
changed={p for p,h in plan['source_pins'].items() if sha(ROOT/p)!=h}
assert changed <= expected,('Unreviewed source changes',sorted(changed-expected))
plan.update(revision='native349_projection_repair',runtime_root=str(RUNTIME),
 status='prepared_not_dispatched',replaces_failed_queue=str(OLD),
 failed_queue_sha256=sha(OLD/'queue_state.json'),reviewed_changed_sources=sorted(changed))
proofs={}
for folder in ('window2250_full_v1','window4500_full_v1','optimized3300_full_v2'):
    result=read(BASE/folder/'summary.json');assessment=read(BASE/folder/'assessment.json')
    assert result['status']=='complete_conditional_response' and result['latest_full_plant_validation']
    assert result['initial_cell_stock_max_error']<1e-7 and len(result['rows'])==1
    assert result['rows'][0]['physical_model_constraints_passed']
    proofs[folder]=dict(summary=str(BASE/folder/'summary.json'),sha256=sha(BASE/folder/'summary.json'),
        native_omega_ttt_veh_h=assessment['native_omega_ttt_cached_interpolated_veh_h'],
        predicted_omega_ttt_veh_h=assessment['predicted_omega_ttt_veh_h'],
        prediction_sec=450,autonomous_controller_validation=False)
startup=read(BASE/'startup_window_v2/verification.json')
assert startup['status']=='canonical_startup_replay_passed_not_native_run'
assert startup['rows_by_kind']=={'vsl':66,'ramp_meter':8} and startup['new_predictions']==0
assert '54 passed' in (HERE/'tests_final_v2.log').read_text()
plan['validation']['projection_repair349']=dict(conditional_forecasts=proofs,regression_tests=54,
    startup=startup,sc12_same_saved_single_parent_exact=True,sc12_moving_stopped_calendar_consumed_once=True,
    sc105_saved_physical_vehicles=30,sc105_retained_source_stock=29.5,
    sc109_saved_source_stock=48,old_harness_rejected_stale_adapter_pin=True,
    full_optimizer_repeated=False,coefficient_fits=0,new_native_runs=0)
plan['validation_note']='New current-state/startup repairs:54 tests, three conditional450s predictions, current ledger and writer checks. Earlier full selection/AD records are reused with their original scope; no new full selection or VSL dynamics gain validation is claimed.'
plan['limitations'] += ['Post-head SC109/SC105 stock retains its previous aggregate owner and reservation; no downstream reownership model is claimed.',
    'The VSL gain calibration goal remains open. Projection repairs do not establish native TTT improvement.',
    'Two window forecasts precede only the SC105 zero-roundoff replacement repair; the optimized forecast includes it.']
for arm,row in plan['conditions'].items():
    output=Path('E:/VISSIM_runs')/f'20261011_native349_{arm}_s29_8100'
    assert not output.exists(),output
    assert sha(ROOT/row['config'])==row['sha256']
    row.update(results_root=str(output),status='prepared',launches_consumed=0)
for p in list(plan['source_pins']):plan['source_pins'][p]=sha(ROOT/p)
for p in [ROOT/'tests/test_calibrated_projection_coverage.py',ROOT/'tests/test_native_multirate_startup.py',
          NEW/'forecast.py',NEW/'startup/replay.py',Path(__file__)]:
    plan['source_pins'][p.relative_to(ROOT).as_posix()]=sha(p)
assert sha(OLD/'run_queue.ps1')==plan['queue_script_sha256']=='7fcdb7d3ef8deb48b7108cf670d122e74c4760711cece7d15e12823e0de0c896'
RUNTIME.mkdir();shutil.copyfile(OLD/'run_queue.ps1',RUNTIME/'run_queue.ps1')
blob=json.dumps(plan,ensure_ascii=False,indent=2)+'\n'
(RUNTIME/'plan.json').write_text(blob,encoding='utf8')
(HERE/'corrected_queue_plan.json').write_text(blob,encoding='utf8')
progress=read(NEW/'plan.json');assert progress['progress']['completed_predictions']==10
progress['progress'].update(completed_predictions=13,production_edits=6,
    full_native348_conditional_forecasts=proofs,
    projection_repair=dict(status='offline_verified',regression_tests=54,
        affected=['SC12/SC16 observed zero readiness and paired arrival tags',
          'SC109 lane heads, both post-head connectors and float ownership',
          'SC10 intermediate fixed-gate stock',
          'SC105 both lane connectors and nonnegative physical cohort replacement'],
        coefficients_changed=False,remaining='VSL response gain/ranking and downstream post-head ownership dynamics'),
    startup_current_source_recheck=startup,
    corrected_queue=dict(runtime=str(RUNTIME),status='prepared_not_dispatched',native_launches=0,max_native_runs=3))
progress['next_step']='Dispatch the distinct corrected finite window/optimized/off queue after ownership/STOP checks. During canonical freeze keep source unchanged. VSL first-round13 forecasts finished, no fit/full selection yet; reuse saved response/flow balances to choose one mechanistic candidate before assigning a small next prediction budget. Preserve failed native348 and all diagnostic failures.'
progress['history_reviewed'] += ['Claude U7/U8 current queue/arrival ownership records',
 'aggregate270/sc12_initial306/README.md','aggregate270/sc105_initial340/README.md','aggregate270/corridor339/README.md']
(NEW/'plan.json').write_text(json.dumps(progress,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(dict(status='prepared_not_dispatched',runtime=str(RUNTIME),changed_sources=sorted(changed),
    conditional_forecasts=3,total_forecasts=13,regression_tests=54,new_native_runs=0),ensure_ascii=False))
