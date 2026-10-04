"""Check saved onset factorial and prior native decision evidence only."""
import ast
import csv
import hashlib
import json
from pathlib import Path

O = Path(__file__).resolve().parent
I = O.parents[2]
read = lambda p: json.loads(Path(p).read_bytes())
out = Path(read(O/'output.json')['output'])
summary = read(out/'summary.json')
results = summary['results']
base = results['held_actual']
prior = read(I/'closedloop_recorded2250_lever450_RM_C10484_city2250_after/held_actual.json')
for k in prior:
    if k != 'wall_sec':
        assert base[k] == prior[k], k
assert len(results) == 4 and summary['future_observation_inputs'] is False
caps = {r['case']:r['resource'] for r in read(O/'quantities.json')}
conditions = read(O/'protocol.json')['conditions']


def group(cost):
    east = cost['freeway:FW_E']
    west = cost['freeway:FW_W']
    ramps = sum(v for k,v in cost.items() if k.startswith('ramp:'))
    return dict(east=east,west=west,ramps=ramps,other_omega=sum(cost.values())-east-west-ramps)


def flux(x):
    flows = x['control_area']['flow_counts'] if 'control_area' in x else {
        r['route_key']:r['vehicles'] for r in x['transfers']}
    return dict(source=flows['origin:FW_E->freeway:FW_E'],
                terminal=flows['freeway:FW_E->external:terminal:FW_E'],
                offramp=sum(v for k,v in flows.items() if k.startswith('freeway:FW_E->storage:')),
                merge=sum(v for k,v in flows.items() if k.startswith('merge_pending:') and k.endswith('->freeway:FW_E')))


rows = []
cell_rows = []
mass_rows = []
for name,x in results.items():
    assert x['validation']['all_actuator_and_step_constraints_checked']
    for j,c in enumerate(x['commands']):
        b = base['commands'][j]
        assert c['green_times'] == b['green_times'] and c['offsets'] == b['offsets']
        assert c['meters']['RM_C10484'] == conditions[name]['meter'][j]
        assert all(c['meters'][k] == b['meters'][k] for k in c['meters'] if k!='RM_C10484')
        assert c['vsl']['FW_E__seg13'] == conditions[name]['vsl'][j]
        assert set(c['vsl']) == set(b['vsl'])
        assert all(c['vsl'][k] == b['vsl'][k] for k in c['vsl']
                   if k not in ('FW_E','FW_E__seg13','FW_E__seg14'))
    assert x['first_interval']['physical_cell_states'][0] == base['first_interval']['physical_cell_states'][0]
    assert all(abs(r['residual'])<1e-7 for r in x['ramps'].values())
    first = x['first_interval']
    initial, final = first['physical_cell_states']
    stock_delta = sum(final['vehicle_count']['FW_E'])-sum(initial['vehicle_count']['FW_E'])
    net_flow = sum(r['vehicles'] for r in first['transfers'] if r['target']=='freeway:FW_E')
    net_flow -= sum(r['vehicles'] for r in first['transfers'] if r['source']=='freeway:FW_E')
    assert abs(stock_delta-net_flow) < 1e-7
    mass_rows.append(dict(case=name,residual=stock_delta-net_flow))
    for h in (150,450):
        a = x['first_interval'] if h==150 else x
        b = base['first_interval'] if h==150 else base
        ga,gb = group(a['cost_by_stock']),group(b['cost_by_stock'])
        fa,fb = flux(a),flux(b)
        delta = a['ttt_omega_veh_h']-b['ttt_omega_veh_h']
        parts = {k:ga[k]-gb[k] for k in ga}
        assert abs(delta-sum(parts.values()))<1e-8
        rows.append(dict(case=name,horizon_sec=h,delta_omega=delta,
            **{'delta_'+k:v for k,v in parts.items()},
            delta_outside=(a.get('tracked_outside_veh_h',a.get('tracked_outside_residence_veh_h'))
                           -b.get('tracked_outside_veh_h',b.get('tracked_outside_residence_veh_h'))),
            ramp10484_arrival=a['ramps']['RM_C10484']['arrival'],
            ramp10484_merge=a['ramps']['RM_C10484']['merge'],
            ramp10484_final_stock=a['ramps']['RM_C10484']['final_stock'],
            **{'delta_east_'+k:fa[k]-fb[k] for k in fa},
            np_actual=caps[name]['np']['actual'],nuf_actual=caps[name]['nuf']['actual'],
            fixed_caps_pass=caps[name]['feasible']))
    for s,b in zip(x['first_interval']['physical_cell_states'],base['first_interval']['physical_cell_states']):
        for j in range(31):
            cell_rows.append(dict(case=name,time_sec=s['time_sec'],cell=j,
                n=s['vehicle_count']['FW_E'][j],delta_n=s['vehicle_count']['FW_E'][j]-b['vehicle_count']['FW_E'][j],
                speed=s['speed_kmh']['FW_E'][j],delta_speed=s['speed_kmh']['FW_E'][j]-b['speed_kmh']['FW_E'][j]))


def csvout(name,rows):
    with (O/name).open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


csvout('cost_and_flow.csv',rows)
csvout('cells_first150.csv',cell_rows)
D = Path('D:/VISSIM_runs/20260930_expanded036_s29_9000_r2/sdmpc/decisions_sdmpc31_sdmpc9000_s29')
history = []
pins = read(O/'execution_pins.json')
for t in range(1500,3301,150):
    p=D/f'action_{t:06d}.joint.json';a=D/f'action_{t:06d}.json'
    pins[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
    pins[str(a)] = hashlib.sha256(a.read_bytes()).hexdigest()
    s=read(p)['selection'];action=read(a)
    grads=[r for r in s['gradient_rows'] if r['key']=='RM_C10484']
    assert len(grads)>=3
    assert all(r['resolved'] and r['derivative_method']=='compiled_reverse_active_path' for r in grads)
    c=s['candidates'][0]
    history.append(dict(sec=t,vsl13=action['vsl']['FW_E__seg13'],
        rm10484=action['diagnostics']['rw_meter_green_RM_C10484'],
        gradient_evaluations=len(grads),rm_total_grad_max=max(abs(r['total']) for r in grads),
        finite_neighbor_audit=s['finite_neighbor_audit_performed'],
        execution_model_evaluated=s['execution_model_evaluated'],
        held_surrogate=s['held_objective'],selected_surrogate=s['selected_objective'],
        selected_gain=s['prediction_ttt_reduction'],accepted=c['accepted_steps'],
        outer_iterations=c['executed_iterations'],max_outer_iterations=c['max_iterations'],
        converged=s['converged'],status=c['status']))
csvout('saved_decision_history.csv',history)
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in pins.items())
(O/'source_pins.json').write_text(json.dumps(pins,indent=2),encoding='utf8')
verification = dict(status='completed_model_diagnostic_not_gain_qualification',
    baseline_matches_saved_corrected_baseline_exact=True,baseline_excluded_fields=['wall_sec'],
    common_state_city_other_meters_writer_mass=True,
    east_first150_mass=mass_rows,unrelated_vsl_commands_unchanged=True,
    future_native_inputs=False,new_native=0,coefficient_fits=0,optimizer=0,
    successful_forecasts=4,failed_baseline_comparison_forecasts=1,
    forecast_compute_sec=sum(x['wall_sec'] for x in results.values()),
    caps=dict(np_target=caps['held_actual']['np']['target'],nuf_target=caps['held_actual']['nuf']['target']),
    rows=rows,saved_decisions=history,
    all_tested_caps_pass=all(v['feasible'] for v in caps.values()),
    rm_gradients_zero_all_saved=all(v['rm_total_grad_max']==0 for v in history),
    interaction_omega450=results['both']['ttt_omega_veh_h']-results['rm_only']['ttt_omega_veh_h']
        -results['vsl_release']['ttt_omega_veh_h']+base['ttt_omega_veh_h'],
    limitations=['Actual2250-2400 commands match held; no native counterfactual for modified commands.',
                 'After2400 native city commands change: fixed450 versus native450 not matched.',
                 'Current model includes two documented core binding fixes relative to original9000.',
                 'Old surrogate gradient and current physical finite difference are not identical models.',
                 'Small predicted differences are not evidence of actual gain or general lever ineffectiveness.'])
(O/'verification.json').write_text(json.dumps(verification,indent=2)+'\n',encoding='utf8')
print(json.dumps(dict(rows=rows,compute_sec=verification['forecast_compute_sec'],interaction=verification['interaction_omega450']),indent=2))
