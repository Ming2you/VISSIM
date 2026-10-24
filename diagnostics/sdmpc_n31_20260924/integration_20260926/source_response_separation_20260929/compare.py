"""Diagnose unequal future source realizations without calibrating the plant."""
from pathlib import Path
import hashlib
import json

HERE=Path(__file__).resolve().parent
I=HERE.parent
pins={}
def read(path):
    data=path.read_bytes(); pins[str(path)]=hashlib.sha256(data).hexdigest()
    return json.loads(data)

assert not (HERE/'comparison.json').exists()
normal=read(I/'closedloop_recorded2250_lever450_trace10484_head10119_s43_v2/summary.json')
common=read(I/'closedloop_recorded2250_lever450_source_common_nc_s43/summary.json')
varied=read(I/'closedloop_recorded2250_lever450_source_per_arm_s43/summary.json')
native=read(I/'seed43_fullplant_20260929/comparison.json')
protocol=read(HERE/'protocol.json')
assert normal['future_observation_inputs'] is False
for d in (common,varied):
    assert d['future_observation_inputs'] is True and d['autonomous_prediction'] is False
    assert d['optimizer_iterations']==0 and d['native_started'] is False
    assert d['prediction_conditioned_on_executed_commands'] is True
    assert set(d['results'])==set(normal['results'])=={'held_actual','rm','vsl','both'}
    for key,r in d['results'].items():
        assert r['commands']==normal['results'][key]['commands']
        source=r['diagnostic_future_source']
        assert abs(source['admitted_veh']-sum(source['rates_veh_h'])/24.)<1e-7
        assert abs(source['final_origin_queue_veh'])<1e-7
        assert all(abs(v['residual'])<1e-7 for v in r['ramps'].values())
baseline_equal={k:v for k,v in common['results']['held_actual'].items() if k!='wall_sec'} == {
    k:v for k,v in varied['results']['held_actual'].items() if k!='wall_sec'}
assert baseline_equal
rows=[]
for key in ('held_actual','rm','vsl','both'):
    arm='nc' if key=='held_actual' else key
    delta=lambda doc:doc['results'][key]['ttt_omega_veh_h']-doc['results']['held_actual']['ttt_omega_veh_h']
    rows.append(dict(case=arm,
        native_source_admissions_veh=protocol['native_sources'][key]['total'],
        native_delta_omega_veh_h=native['costs'][arm]['delta_vs_nc']['native_omega_veh_h'],
        causal_forecast_delta_omega_veh_h=delta(normal),
        common_future_nc_source_delta_omega_veh_h=delta(common),
        own_future_source_delta_omega_veh_h=delta(varied),
        model_source_realization_effect_veh_h=delta(varied)-delta(common),
        native_minus_conditional_veh_h=native['costs'][arm]['delta_vs_nc']['native_omega_veh_h']-delta(varied)))
report=dict(rows=rows,source_only_intervention=True,other_demands_and_commands_unchanged=True,
    model_admissions_match_supplied_native_counts=True,all_ramp_conservation_passed=True,
    common_baseline_non_timing_output_exact=baseline_equal,conditional_forecasts_completed=8,
    fitted_parameters=0,optimizer_iterations=0,new_native_runs=0,
    interpretation='Model sensitivity to unequal realized source inputs; not an identified causal decomposition of VISSIM treatment effect.',
    limitations=['Future source profiles are diagnostic inputs, not available to the controller.',
        'Admitted-input differences may include stochastic realization and endogenous admission effects; this test does not identify their source.',
        'Source profiles use150s mean rates; native30s totals determine those rates.',
        'Only FW_E source is replaced. Ramp/urban boundary arrivals, actual route choices and downstream response differences remain.',
        'Native450s totals and predicted450s totals differ by0.1s recording phase.',
        'Matching a conditional cost difference does not qualify autonomous control or remove the need to validate large gain/loss cases.'],
    source_pins=pins,goal_complete=False)
(HERE/'comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
print(json.dumps(rows))
