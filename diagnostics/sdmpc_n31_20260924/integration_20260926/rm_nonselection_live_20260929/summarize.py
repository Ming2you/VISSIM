"""Summarize existing predictions; no simulation, calibration or optimizer."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
PROBE = BASE/'closedloop_recorded3600_lever450_live29_rm_diagnosis_v1'
read = lambda p: json.loads(p.read_bytes())
held = read(PROBE/'held_actual.json')
trace = read(HERE/'held_resource_trace.json')
saved = read(HERE/'saved_solver_evidence.json')
record = next(r for r in saved['records'] if r['sim_sec']==3600)
catalog = trace['quantities']['movement_catalog']
signs = dict(boundary_in=1, off_ramp=1, boundary_out=-1, on_ramp=-1, internal=0)
caps = {key:record['constraints'][key]['target'] for key in ('np','nuf')}
assert trace['quantities']['movement_flow_counts_match']
assert abs(trace['ttt_omega_veh_h']-held['ttt_omega_veh_h'])<1e-9


def np_value(case):
    return sum(signs[s['kind']]*case['control_area']['flow_counts'].get('movement:'+m,0.)
               for m,s in catalog.items())


assert abs(np_value(held)-trace['quantities']['np_veh'])<1e-7
results = {}
for path in [PROBE/'held_actual.json', *sorted(PROBE.glob('meter_*.json'))]:
    case = read(path)
    stock_delta = {k:v-held['cost_by_stock'].get(k,0.) for k,v in case['cost_by_stock'].items()}
    groups = dict(freeway=sum(v for k,v in stock_delta.items() if k.startswith('freeway:')),
                  ramp=sum(v for k,v in stock_delta.items() if k.startswith('ramp:')))
    groups['other_omega'] = sum(stock_delta.values())-sum(groups.values())
    delta = case['ttt_omega_veh_h']-held['ttt_omega_veh_h']
    assert abs(sum(groups.values())-delta)<1e-7
    ramps = {}
    for ramp,row in case['ramps'].items():
        assert abs(row['residual'])<1e-7
        ramps[ramp] = dict(**row, initial_stock_veh=held['ramps'][ramp]['merge']+
            held['ramps'][ramp]['final_stock']-held['ramps'][ramp]['arrival'],
            merge_delta_veh=row['merge']-held['ramps'][ramp]['merge'],
            greens=[c['meters'][ramp] for c in case['commands']])
    np = np_value(case)
    nuf = sum(r['merge'] for r in case['ramps'].values())/(450/3600)
    results[path.stem] = dict(omega_ttt_veh_h=case['ttt_omega_veh_h'],delta_omega_veh_h=delta,
        delta_omega_percent=100*delta/held['ttt_omega_veh_h'],delta_by_stock_group=groups,
        tracked_outside_delta_veh_h=case['tracked_outside_residence_veh_h']-held['tracked_outside_residence_veh_h'],
        ramps=ramps, np_veh=np,nuf_veh_h=nuf,
        quantity_caps_satisfied=np<=caps['np']+1e-7 and nuf<=caps['nuf']+1e-7,
        actuator_and_step_constraints=case['validation'])

resources = {}
for ramp in held['ramps']:
    resource = {}
    for kind in sorted({r['kind'] for r in trace['resources']}):
        rows = [r for r in trace['resources'] if r['kind']==kind and r['resource'].split(':')[0]==ramp]
        resource[kind] = dict(rows=len(rows),
            positive_limit_binding_rows=sum(r['available_veh']>1e-8 and abs(r['available_veh']-r['accepted_total_veh'])<1e-8 for r in rows),
            zero_limit_rows=sum(r['available_veh']<1e-8 for r in rows),
            sum_interval_availability_veh=sum(r['available_veh'] for r in rows),
            sum_accepted_veh=sum(r['accepted_total_veh'] for r in rows),
            max_exceedance_veh=max(r['exceedance_veh'] for r in rows))
    resources[ramp] = resource

inputs = [PROBE/'held_actual.json', *sorted(PROBE.glob('meter_*.json')),
          HERE/'saved_solver_evidence.json', HERE/'held_resource_trace.json']
output = dict(start_sec=3600,duration_sec=450,seed=29,
    purpose='Saved-state RM nonselection diagnosis; no native counterfactual',
    prediction_rollouts=10, city_vsl_held_at_last_actual_command=True,
    future_observations_used=False, production_code_changed=False, new_native_runs=0,
    caps=caps, np_reconstruction='17-owner accepted movement signs; checked against full response transfers',
    all_candidate_quantity_caps_satisfied=all(r['quantity_caps_satisfied'] for r in results.values()),
    results=results,held_resources=resources,
    resource_caveat='Summed stock/eligibility availability repeats inventory and is NOT demand. Two-lane head rows are per lane. Aggregate physical receiving does not certify lane-level binding.',
    remaining_unknowns=['Native counterfactual for these live29 states',
        'Benefit of stronger RM beyond the legal 450s reachable sequence',
        'Whether future high-queue states have a materially beneficial feasible candidate missed by search'],
    source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs})
(HERE/'comparison.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(all_quantity_caps_satisfied=output['all_candidate_quantity_caps_satisfied'],
    np_range=[min(r['np_veh'] for r in results.values()),max(r['np_veh'] for r in results.values())],
    nuf_range=[min(r['nuf_veh_h'] for r in results.values()),max(r['nuf_veh_h'] for r in results.values())],
    rows=[dict(case=k,delta=v['delta_omega_veh_h'],cost=v['delta_by_stock_group']) for k,v in results.items()]),indent=2))
