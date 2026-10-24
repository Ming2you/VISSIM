"""Verify the explicit local candidate and its saved coupled runtime receipt."""
import copy
import datetime
import gzip
import hashlib
import json
import sys
from pathlib import Path

D=Path(__file__).resolve().parent;A=D.parent;I=A.parent
ROOT=I.parents[2];sys.path[:0]=[str(ROOT),str(ROOT/'vendor/NumSim-mine')]
from evaluation.controllers import lane_plant_runtime as lpr
from diagnostics.sdmpc_n31_20260924.integration_20260926.replay_congested_component import read_primitive_capture

load=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
summary=load(D/'summary.json');selection=load(D/'frozen_selection.json')['selected']
ctx=lpr.load_sources(D/'candidate_manifest.json');model=ctx['component']
cfg=model._config('FW_E',ctx['parameters']['by_direction']['FW_E'])
assert cfg.network.freeway_state_response['FW_E']['cell_overrides']['23']=={
    'anticipation':{'downstream_ge_local':18.375,'downstream_lt_local':4.59375},'delta_merge':2.}
base=load(I/'heldout53_response_v2/candidate_config.json');candidate=load(D/'candidate_reference_config.json')
restored=copy.deepcopy(candidate)
restored['freeway']['state_response']['FW_E']['cell_overrides']['23']=base['freeway']['state_response']['FW_E']['cell_overrides']['23']
assert restored==base
r=next(r for r in load(I/'decision_response/capture.json')['records'] if r['case']=='s47_late' and r['arm']=='release_10484')
args,kwargs=read_primitive_capture(r['input'],r['sha256'])
assert args[2]==ctx['parameters']
prediction=model.rollout(*args,**kwargs)
with gzip.open(D/selection/'s47_late_release_10484.json.gz','rt',encoding='utf-8') as f:previous=json.load(f)
# Persisted traces are JSON: lane_arrival_shares tuples are serialized as
# arrays. Compare the same representation, without tolerances or rounding.
serialized_prediction=json.loads(json.dumps(prediction,allow_nan=False))
exact={k:serialized_prediction[k]==previous[k] for k in ('cells','flows','ports','ramps')}
if not all(exact.values()):
    differences=[]
    def compare(a,b,path):
        if a==b or len(differences)>=30:return
        if isinstance(a,dict) and isinstance(b,dict) and a.keys()==b.keys():
            for key in a:compare(a[key],b[key],path+'.'+str(key))
        elif isinstance(a,list) and isinstance(b,list) and len(a)==len(b):
            for index,(aa,bb) in enumerate(zip(a,b)):compare(aa,bb,path+f'[{index}]')
        else:differences.append(dict(path=path,candidate=a,previous=b))
    compare(prediction['ramps'],previous['ramps'],'ramps')
    (D/'manifest_parity_failure.json').write_text(json.dumps(dict(exact=exact,differences=differences),indent=2),encoding='utf-8')
    print(json.dumps(differences[:5]),flush=True)
assert all(exact.values()),exact
coupled_path=I/'closedloop_recorded6000_trace_local_cell23_v1/summary.json';coupled=load(coupled_path)
assert coupled['simulation_started'] is False and coupled['start_sec']==6000 and coupled['duration_sec']==150
full_path=D/'candidate_full_config.json'
assert sha(full_path) in coupled['inputs'].values()
residual=max(abs(v['stock_conservation_residual_veh']) for v in coupled['ramps'].values());assert residual<1e-7
assert len(coupled['physical_ramps'])==8
assert sha(I/'selected/config_n31_v2.json')=='b86534bab6e9360abf5d79c5b7a0edcc9867242af4eb50b009280978150a9347'
assert sha(I/'selected/network/native_seed29.inpx')=='64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc'
assert Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP').exists()
quality=load(D/'native_boundary_quality.json')
valid={(r['case'],r['arm']) for r in quality if r['clean_component_boundary']}
choices=[]
for variant in ('baseline',selection):
    for case in sorted({r['case'] for r in summary['rows']}):
        rows=[r for r in summary['rows'] if r['variant']==variant and r['case']==case and (case,r['arm']) in valid]
        best=min(rows,key=lambda r:r['costs']['predicted']['total']);actual=min(rows,key=lambda r:r['costs']['actual']['total'])
        choices.append(dict(variant=variant,case=case,selected=best['arm'],actual_best=actual['arm'],
            regret=best['costs']['actual']['total']-actual['costs']['actual']['total']))
result=dict(status='PARTIAL_LOCAL_RESPONSE_IMPROVEMENT_NOT_GENERAL_GAIN_QUALIFIED',
    only_physical_east_cell23_changed=True,manifest_prediction_arrays_exact=exact,
    baseline_arrays_exact_cases=len(load(D/'baseline_parity.json')),
    physical_model_sources_changed=False,selected_config_unchanged=True,STOP_preserved=True,
    offline450_rollouts=summary['rollouts']+3,offline150_rollouts=1,optimizer_iterations=0,native_runs=0,
    manifest_check_replays=3,initial_manifest_check_failure='Tuple versus saved JSON list in lane_arrival_shares; exact serialized arrays all verified, no numeric tolerance.',
    local_term_evaluations=560,full_coupled150_complete=True,ramp_conservation_max=residual,
    coupled_ttt_omega_prediction_veh_h=coupled['cases']['recorded']['ttt_omega_veh_h'],
    clean_boundary_choices=choices,excluded_native_arm='s47_late hold_vsl90: four unexplained losses',
    provenance_limitation='s43_early none manifest pins raw FZP, not table; table hash captured now, not retrospectively verified.',
    proof_sha256={str(p):sha(p) for p in (D/'protocol.json',D/'frozen_selection.json',D/'summary.json',D/'candidate_reference_config.json',D/'candidate_manifest.json',full_path,coupled_path)},
    adopted=False,gain_qualified=False)
(D/'validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
status_path=A/'user_stop_analysis_status.json';status=load(status_path)
status.update(diagnostic_stage='cell23_local_calibration_partial_response_improvement',
    diagnostic_completed_at=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),
    diagnostic_report='local_merge_cell23/README.md',diagnostic_results='local_merge_cell23/summary.json',
    active_owned_calculations=[],calibration_adopted=False,
    next_diagnostic='Retain the frozen cell23 candidate. Check remaining10490 release and RM+VSL interaction errors in conserved discharge/arrival responses; do not chase exact trajectories. Existing STOP remains; no native restart.')
status_path.write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ('proof_sha256','clean_boundary_choices')}),flush=True)
