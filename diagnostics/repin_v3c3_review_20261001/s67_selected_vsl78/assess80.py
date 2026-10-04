"""Use completed native metrics and obs150; never rescan FZP or rerun a forecast."""
import bisect
import hashlib
import json
from pathlib import Path
from evaluation.controllers import lane_plant_runtime, obs150_observation

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
I=ROOT/'diagnostics/sdmpc_n31_20260924/integration_20260926'
RUNS=Path('D:/VISSIM_runs/20261003_s67_selected_vsl78')
pins={}
def read(path):
    data=path.read_bytes();pins[str(path)]=hashlib.sha256(data).hexdigest();return json.loads(data)
def save(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf-8')

assert not (HERE/'response_assessment80.json').exists()
assert read(HERE/'analysis_run80_cli.json')['stage']=='complete'
native=read(HERE/'analysis/summary.json')
assert native['counterfactual_valid'] and native['original_initial_history_exact']
assert all(row['native_execution_passed'] for row in native['arms'].values())
protocol=read(I/'closedloop_recorded2700_native_selected_s67_selected_vsl78/protocol.json')
prediction=read(Path(protocol['prediction_source']))
assert pins[protocol['prediction_source']]==protocol['prediction_sha256']
ramps=read(HERE/'analysis/ramp_response_audit.json')
prior=read(HERE.parent/'s67_full_observation/response_assessment76.json')
prior_native=read(HERE.parent/'s67_full_observation/analysis/summary.json')
assert native['prefixes']['selected']==prior_native['prefixes']['release']
g=read(I/'selected/port_gain/geometry.json')
assert g['network']['sha256']==protocol['network_sha256']
chains={road:{int(v['link']):v for v in chain} for road,chain in g['chains'].items()}
ramp_links={int(b['connector']) for b in g['boundaries'] if b['kind']=='ramp'}
tuning=read(HERE.parent/'rm47_service66_response/candidate_config.json')
context=lane_plant_runtime.load_sources(tuning['freeway']['lane_plant'])
rows={};snapshots=[]
for arm in ('selected','vsl90'):
    metric=read(HERE/f'analysis/{arm}/area_metrics.json')
    components=dict(FW_E=0.,FW_W=0.,ramps=0.,other_omega=0.)
    for link,value in metric['physical_link_residence'].items():
        if not value['inside']:continue
        key=next((r for r,links in chains.items() if int(link) in links),None)
        key=key or ('ramps' if int(link) in ramp_links else 'other_omega')
        components[key]+=value['ttt_veh_h']
    assert abs(sum(components.values())-metric['ttt_veh_h'])<1e-7
    totals={};stocks={}
    folder=RUNS/arm/f'decisions_sdmpc31_g_2700_{arm}_s67'
    for sec in (2700,2850,3000,3150):
        raw=read(folder/f'state_{sec:06d}.json')
        assert raw['sim_sec']==sec and raw['vehicle_records']['complete']
        observed=raw['vehicle_records']['records']
        stocks[sec]={r:sum(int(v['link_no']) in links for v in observed) for r,links in chains.items()}
        cells=sorted((c for c in g['cells'] if c['road']=='FW_E'),key=lambda c:c['cell'])
        ends=[c['end_m'] for c in cells];bins=[[] for _ in cells]
        for vehicle in observed:
            link=int(vehicle['link_no'])
            if link in chains['FW_E']:
                pos=chains['FW_E'][link]['offset_m']+float(vehicle['position_m'])
                bins[min(bisect.bisect_right(ends,pos),30)].append(float(vehicle['speed_kph']))
        snapshots.append(dict(arm=arm,time_sec=sec,east_cells=[dict(cell=i,n=len(v),
            speed_kmh=sum(v)/len(v) if v else None) for i,v in enumerate(bins)]))
        if sec==2700:continue
        d=obs150_observation.derive(raw,context['obs150'])
        assert d['window']==dict(start_s=sec-150,end_s=sec)
        for ref,value in d['boundaries'].items():
            if ref.startswith(('source:','chain_end:','off_entry:')):
                totals[ref]=totals.get(ref,0)+value['cross']
    mainline={}
    for road in chains:
        ports=[b for b in g['boundaries'] if b['road']==road]
        rm=[b['id'] for b in ports if b['kind']=='ramp']
        off=[b['connector'] for b in ports if b['kind']=='offramp']
        flow=dict(source=totals['source:'+road],merge=sum(ramps['arms'][arm][r]['actual']['merge'] for r in rm),
            off=sum(totals['off_entry:'+str(c)] for c in off),terminal=totals['chain_end:'+road],
            initial_stock=stocks[2700][road],final_stock=stocks[3150][road])
        flow['balance_residual']=flow['initial_stock']+flow['source']+flow['merge']-flow['off']-flow['terminal']-flow['final_stock']
        assert abs(flow['balance_residual'])<1e-7
        mainline[road]=flow
    rows[arm]=dict(native_full_run_component_veh_h=components,mainline450=mainline)
delta={key:rows['vsl90']['native_full_run_component_veh_h'][key]-rows['selected']['native_full_run_component_veh_h'][key]
       for key in components}
assert abs(sum(delta.values())-native['delta_TTT_veh_h'])<1e-7
pred=prediction['results'];pred_delta=pred['vsl90']['execution']['ttt_omega_veh_h']-pred['selected']['execution']['ttt_omega_veh_h']
assert abs(pred_delta-native['predicted_delta_omega_veh_h'])<1e-9
result=dict(status='SELECTED_POLICY_VSL_LOSS_DIRECTION_MATCHES_PRIOR_GAIN_UNDERRESPONSE_REMAINS',
    actual_delta_omega_veh_h=native['delta_TTT_veh_h'],predicted_delta_omega_veh_h=pred_delta,
    prediction_error_veh_h=pred_delta-native['delta_TTT_veh_h'],actual_component_delta_veh_h=delta,
    outside_observed_delta_veh_h=native['delta_outside_Omega_residence_veh_h'],
    native_uninserted_delay_delta_veh_h=native['delta_native_uninserted_delay_veh_h'],
    native_total_time_including_uninserted_delta_veh_h=native['delta_native_total_time_including_uninserted_veh_h'],
    earlier_joint_policy=dict(actual_vsl_delta=prior['actual_delta_omega_veh_h'],predicted_vsl_delta=prior['predicted_delta_omega_veh_h']),
    change_in_marginal_vsl_effect=dict(actual=native['delta_TTT_veh_h']-prior['actual_delta_omega_veh_h'],
        predicted=pred_delta-prior['predicted_delta_omega_veh_h'],
        interpretation='Same observed initial state, different joint city/RM schedules. This is a policy interaction contrast, not isolated attribution to RM versus city signals.'),
    arms=rows,source_snapshots='Evaluation after frozen predictions and completed native runs; never forecast inputs.',
    new_forecasts=0,new_native_runs=0,extra_fzp_scans=0,new_calibration=0,gain_qualified=False,
    limitations=['Small one-state effect; seed67 already used, not a new independent holdout.',
        'Native component levels include0..3150; compare deltas only because the prefix is exact.',
        '5s trajectory sampling and4.9s tail hold. LSA still incomplete; authorized LDP execution validation passed.',
        '64 native removals and276 unresolved Omega disappearances in each arm are not normal exits. Equal counts do not assert identical vehicle identities.',
        'Current selected-neighbor report stores total costs and ramp totals, not all cell state predictions; observed snapshots cannot by themselves prove a recovery mechanism.'],
    input_sha256=pins)
save(HERE/'observed_snapshots80.json',snapshots);save(HERE/'response_assessment80.json',result)
print(json.dumps({k:v for k,v in result.items() if k not in ('input_sha256','limitations')}))
