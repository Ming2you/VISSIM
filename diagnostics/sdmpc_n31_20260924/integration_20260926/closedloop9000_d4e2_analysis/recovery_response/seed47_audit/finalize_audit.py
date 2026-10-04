"""Finalize saved-data diagnostics only; no rollout or native execution."""
import csv
import datetime
import hashlib
import json
from pathlib import Path

D=Path(__file__).resolve().parent
A=D.parents[1]
I=A.parent
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
x=load(D/'tau4_decomposition_v2.json');base=load(D/'baseline_decomposition_v2.json')
assert all(x['results'][a]['main_ttt']['native']==base['results'][a]['main_ttt']['native'] for a in x['results'])
rs={r['arm']:r for r in load(I/'decision_response/capture.json')['records'] if r['case']=='s47_late'}
cmd={a:load(Path(rs[a]['truth']).parent.parent/(a+'_commands.json')) for a in ('hold','release_10484')}
pins={}
for a in cmd:
    p=Path(rs[a]['truth']).parent.parent/(a+'_commands.json')
    # Capture pins a canonical JSON representation with integer time keys,
    # not the raw command file bytes. Verify both representations explicitly.
    normalized={int(t):v for t,v in cmd[a].items()}
    digest=hashlib.sha256(json.dumps(normalized,sort_keys=True).encode()).hexdigest()
    assert digest==rs[a]['commands_sha256']
    pins[str(p)]={'raw_sha256':sha(p),'capture_canonical_sha256':digest}
for t in cmd['hold']:
    if float(t)<2700:assert cmd['hold'][t]==cmd['release_10484'][t]
changes=[]
for t in ('2700','2850','3000'):
    h=cmd['hold'][t];r=cmd['release_10484'][t]
    assert h['vsl']==r['vsl']
    assert {k:v for k,v in h['greens'].items() if k!='RM_C10484'}=={k:v for k,v in r['greens'].items() if k!='RM_C10484'}
    changes.append({'time_sec':int(t),'hold_green_sec':h['greens']['RM_C10484'],'release_green_sec':r['greens']['RM_C10484']})
assert [z['release_green_sec'] for z in changes]==[4,6,8]
counts={}
for arm in cmd:
    p=Path(rs[arm]['truth'])/'flows_30s.csv'
    assert sha(p)==x['pins'][str(p)]
    with p.open(encoding='utf-8-sig') as f:
        fs=[z for z in csv.DictReader(f) if z['road']=='FW_E' and z['cell']=='20' and 2670.10001<float(z['window_end_s'])<3120.10001]
    off=sum(float(z['off_departures']) for z in fs);through=sum(float(z['downstream_crossings']) for z in fs)
    counts[arm]={'off_veh':off,'through_veh':through,'total_out_veh':off+through,'realized_off_share':off/(off+through)}
h=counts['hold'];r=counts['release_10484']
flow_effect=h['realized_off_share']*(r['total_out_veh']-h['total_out_veh'])
mix_effect=r['total_out_veh']*(r['realized_off_share']-h['realized_off_share'])
assert abs(flow_effect+mix_effect-(r['off_veh']-h['off_veh']))<1e-9
assert sha(I/'selected/config_n31_v2.json')=='b86534bab6e9360abf5d79c5b7a0edcc9867242af4eb50b009280978150a9347'
assert sha(I/'selected/network/native_seed29.inpx')=='64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc'
assert Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP').exists()
code=A/'posthead_receiving/decompose_existing_response.py'
compile(code.read_text(encoding='utf-8'),str(code),'exec')
summary=dict(status='DIAGNOSIS_COMPLETE_NOT_GAIN_QUALIFIED',window_sec=[2670.1,3120.1],
    scope='FW_E31+eight east connector ports; not whole Omega',objective_changed=False,
    command_changes=changes,commands_sha256=pins,common_initial_state_exact=True,
    cache_sha_verified=True,cost_conservation_verified=True,
    baseline_delta=base['results']['release_10484']['delta_component_ttt'],
    tau4_delta=x['results']['release_10484']['delta_component_ttt'],
    tau4_component_boundary=x['results']['release_10484']['delta_component_boundary'],
    off10483_posthoc_split=dict(counts=counts,flow_volume_effect_veh=flow_effect,
        realized_composition_effect_veh=mix_effect,order_dependent_decomposition=True,used_for_forecast=False),
    failed_checks=[dict(stage='initial_all_arm_flow_stock_reconciliation',arm='hold_vsl90',
        unexplained_mainline_losses_veh=4,resolution='No reinterpretation as exits. This audit only covers hold and release_10484, both zero loss. VSL exact decomposition remains unqualified.'),
        dict(stage='raw_command_hash_compared_to_canonical_hash',resolution='Capture source documents integer-key sorted JSON hashing; correct canonical hash now matches, raw bytes separately pinned.')],
    native_runs=0,new_rollouts=0,optimizer_iterations=0,model_or_parameter_changes=False,
    selected_network_config_unchanged=True,stop_preserved=True,source_sha256=sha(code),
    saved_data_sha256={str(D/name):sha(D/name) for name in ('baseline_decomposition_v2.json','tau4_decomposition_v2.json')},
    next_step='Audit canonical local METANET speed-term balance at common native states and merge perturbations; separate state/mean-speed closure from receiving limits before another fit. No new native restart.')
(D/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
status=load(A/'user_stop_analysis_status.json')
status.update(diagnostic_stage='seed47_rm10484_discharge_response_error_isolated',
    diagnostic_completed_at=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),
    diagnostic_report='recovery_response/seed47_audit/README.md',diagnostic_results='recovery_response/seed47_audit/summary.json',
    next_diagnostic=summary['next_step'],active_owned_calculations=[])
(A/'user_stop_analysis_status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(off10483=summary['off10483_posthoc_split'],commands=changes,selected_unchanged=True,STOP=True)))
