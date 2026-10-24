"""Assess the completed bounded check without fitting to its small net sign."""
import hashlib
import json
from pathlib import Path
from collections import defaultdict

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
D = HERE/'native238_validation'
read = lambda p: json.loads(p.read_bytes())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
plan = read(D/'plan.json')
for path, expected in plan['source_pins'].items():
    assert sha(Path(path)) == expected, path
native = read(D/'native_omega701.json')
mapping_path = ROOT/'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json'
mapping = read(mapping_path)['freeway_model_links']
fw_links = {str(k) for row in mapping.values() for k in row['chain_links']}
native_parts = dict(mainline=sum(v for k,v in native['delta_by_link_veh_h'].items() if k in fw_links),
    nonmainline=sum(v for k,v in native['delta_by_link_veh_h'].items() if k not in fw_links))
ramp_path = HERE.parent/'rm_restart219/native238/analysis/ramp_response_audit.json'
ramps = read(ramp_path)
native_flows = {arm:{r:ramps['arms'][arm][r]['actual'] for r in ('RM_C10681','RM_C10646')}
                for arm in ('hold','selected')}
results = {}
pins = {str(p):sha(p) for p in (D/'native_omega701.json', mapping_path, ramp_path)}
for model in ('baseline','candidate'):
    folder = D/(model+'_native_command')
    assert read(folder/'completion.json')['status'] == 'complete'
    summary = read(folder/'summary.json'); pins[str(folder/'summary.json')] = sha(folder/'summary.json')
    part = defaultdict(float)
    hold, selected = summary['results']['hold'], summary['results']['selected']
    for k in set(hold['costs_by_stock'])|set(selected['costs_by_stock']):
        part[k.split(':')[0]] += selected['costs_by_stock'].get(k,0)-hold['costs_by_stock'].get(k,0)
    assert abs(sum(part.values())-summary['delta_omega_ttt_veh_h']) < 1e-7
    for item in (hold,selected):
        assert item['resource_max_exceedance'] <= 1e-7 and item['conservation_checks'] == 4
    predicted = {arm:{r:summary['results'][arm]['predicted_ramp_merge']['accepted_vehicles_by_ramp'][r]
                     for r in ('RM_C10681','RM_C10646')} for arm in ('hold','selected')}
    results[model] = dict(delta_omega_veh_h=summary['delta_omega_ttt_veh_h'],delta_by_stock_class_veh_h=dict(part),
        delta_mainline_veh_h=part['freeway'], delta_nonmainline_veh_h=sum(v for k,v in part.items() if k!='freeway'),
        predicted_merges=predicted, native_merge_errors={a:{r:predicted[a][r]-native_flows[a][r]['merge']
            for r in predicted[a]} for a in predicted},
        inherited_cap_feasible={a:summary['results'][a]['inherited_cap_check']['feasible'] for a in ('hold','selected')},
        completion=read(folder/'completion.json'), resource_and_conservation_pass=True)
output = dict(status='structural_response_improved_but_gain_calibration_not_complete',
    scope='4650–5100 same initial state and physically executed RM-only command changes; current Omega701, no new native data',
    native_delta_omega_veh_h=native['delta_4650_5100_veh_h'], native_delta_components_veh_h=native_parts,
    native_flows=native_flows, models=results, source_pins=pins,
    conclusions=[
        'The local68 queue fixes blocked10646 leakage: held merge22.34->4.00 vs actual4, reopened50.83->43.55 vs29.',
        'Both models preserve the mainline-loss/nonmainline-benefit direction, but exaggerate both magnitudes.',
        '10681 reopening merge remains172.77 vs actual111; observed138 head crossings are distinct from111 merges.',
        'Net gain is not improved: actual+0.407, baseline-0.666, candidate-1.134 vehh. Do not call calibration complete or tune a bonus to this small sign.',
        'Historical hold0s is outside current minimum2s, and reopening violates the inherited NUF cap; this is not a newly feasible SDMPC solution.',
        'Retain bounded structural correction as a candidate. Diagnose admitted ramp flow/head-to-merge response using existing histories before any new coefficient search.',
        'Do not start end-to-end runtime optimization until the bounded calibration/control gate is resolved; completed exact-cache proofs remain reusable.'
    ],
    native_runs=0, FZP_scans=0, forecasts_completed=4, fit_parameters=0,
    historical_limitations=['Same seed29 unused state, not independent-seed validation',
        'Final4.9sec last-stock extrapolation; exact common prefix cancels in reclassified difference',
        'Approved LDP execution proof retained; LSA coverage missing',
        'No terminal-exit inference was used to recompute normal departures'])
(D/'assessment.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
plan['status'] = output['status'];plan['consumed'] = dict(predictions=4, native_runs=0, full_selections=0)
plan['assessment'] = 'assessment.json'
(D/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({'status':output['status'],'native_delta':output['native_delta_omega_veh_h'],
    'baseline_delta':results['baseline']['delta_omega_veh_h'],'candidate_delta':results['candidate']['delta_omega_veh_h']}))
