"""Summarize the saved failure regression without another forecast."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
files={}
def read(path):
    raw=path.read_bytes();files[str(path)]=hashlib.sha256(raw).hexdigest()
    return json.loads(raw)
evidence=read(HERE/'held4050_80_ledger_hook.json')
failed=read(HERE/'held4050_80_typed_handle.json')
output=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926/closedloop_recorded4050_lever450_queuezero79_held4050_80_ledger_hook'
summary=read(output/'summary.json')
assert evidence['completed'] and evidence['new_rollouts']==1
assert not failed['completed'] and failed['new_rollouts']==1
assert summary['only_held_reference'] and set(summary['results'])=={'held_actual'}
assert summary['start_sec']==4050 and summary['duration_sec']==450
assert summary['optimizer_iterations']==0 and not summary['native_started'] and not summary['future_observation_inputs']
result=summary['results']['held_actual']
max_ramp_residual=max(abs(row['residual']) for row in result['ramps'].values())
assert len(result['ramps'])==8 and max_ramp_residual<1e-7
assert evidence['rollout_checks']['saved_states']==[
    dict(time_sec=4050.,initial_tag_veh=195.),dict(time_sec=4200.,initial_tag_veh=51.),
    dict(time_sec=4350.,initial_tag_veh=0),dict(time_sec=4500.,initial_tag_veh=0)]
for path,digest in evidence['source_sha256'].items():
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest
report=dict(status='SAVED4050_HELD450_CONSERVATION_PASS_NOT_GAIN_QUALIFIED',
    previous_goal_turn='PROGRESS: observed-zero fix and saved-state initialization verified; current turn extends to autonomous450.',
    start_sec=4050,horizon_sec=450,successful_rollout_compute_sec=result['wall_sec'],
    actual_rollouts_executed=2,successful_captured_rollouts=1,optimizer_calls=0,new_native_runs=0,
    failed_attempts=[dict(stage='before_prediction',reason='ctypes pseudo-handle default32bit conversion; typed HANDLE declaration fixed'),
                     dict(stage='after_prediction',reason='Diagnostic hook read the area response before runtime wrapper attached it; moved hook after runtime installation')],
    checks=evidence['rollout_checks'],max_ramp_mass_residual_veh=max_ramp_residual,
    predicted_omega_ttt_veh_h=result['ttt_omega_veh_h'],predicted_outside_tracked_veh_h=result['tracked_outside_residence_veh_h'],
    claim_limit='No actual4050..4500 data exists in the failed native run. This proves execution and conservation, not forecast accuracy or gain. No SDMPC optimization/native restart.',
    source_sha256=evidence['source_sha256'],input_sha256=files)
(HERE/'rollout_assessment80.json').write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ('source_sha256','input_sha256')}))
