"""Assess one saved-state decision and two finite VSL neighbors; no simulation."""
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
I = ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926'
LABEL = 's67_service66_selection77_access'
SELECT = I / ('closedloop_recorded2700_select_' + LABEL)
CHECK = I / ('closedloop_recorded2700_select_check_' + LABEL)
NEIGHBORS = I / ('closedloop_recorded2700_budget_check_selected_vsl13_' + LABEL)
PAIR = I / 'closedloop_recorded2700_lever450_s67_service66_20261003_actuator_equivalent'
pins = {}
def read(path):
    data = path.read_bytes()
    pins[str(path)] = hashlib.sha256(data).hexdigest()
    return json.loads(data)
def groups(result):
    costs = result['cost_by_stock']
    row = {road: costs['freeway:' + road] for road in ('FW_E', 'FW_W')}
    row['ramps'] = math.fsum(v for k, v in costs.items() if k.startswith('ramp:'))
    row['other_omega'] = result['ttt_omega_veh_h'] - math.fsum(row.values())
    return row
def main():
    for name in ('exit_access.json', 'execution_exit.json', 'vsl_exit.json'):
        assert read(HERE/name)['exit_code'] == 0
    protocol = read(HERE/'protocol.json')
    for path, expected in protocol['source_pins'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == expected, path
    stop = Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP')
    assert hashlib.sha256(stop.read_bytes()).hexdigest() == '91b2163b02b01447242909dee8e7f773d18e76a6594bd9db8de64d2a48246fc3'
    selection_receipt = read(SELECT/'summary.json')
    report = read(SELECT/'unused_action.joint.json')
    selection = report['selection']
    binding = read(SELECT/'unused_action.joint_written.json')
    assert report['completed'] and selection['feasible'] and binding['written_command_binding_passed']
    assert not selection_receipt['native_started'] and not selection_receipt['gain_qualified']
    for path, expected in selection_receipt['files'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == expected
    execution = read(CHECK/'summary.json')
    held, chosen = (execution['results'][k] for k in ('held_actual', 'selected'))
    caps = selection['budget_initialization']
    for result in (held, chosen):
        q = result['canonical_quantity_constraints']
        assert q['feasible'] and q['np']['target'] == caps['np_cap_veh']
        assert q['nuf']['target'] == caps['nuf_cap_veh_h']
        assert result['saved_state_stock_witness']['passed']
        assert result['max_resource_exceedance_veh'] < 1e-7
    changes = []
    for b, (before, after) in enumerate(zip(held['commands'], chosen['commands'])):
        assert before['vsl'] == after['vsl'] and set(after['vsl'].values()) == {110.}
        changes.append(dict(block=b, changes={kind: {k:[value,after[kind][k]]
            for k,value in before[kind].items() if value != after[kind][k]}
            for kind in ('vsl','meters','green_times','offsets')}))
    neighbor_report = read(NEIGHBORS/'summary.json')
    neighbors = {}
    for name, result in neighbor_report['results'].items():
        for mode in ('surrogate','execution'):
            q = result[mode]['quantities']
            assert q['feasible'] and q['np']['target'] == caps['np_cap_veh']
            assert q['nuf']['target'] == caps['nuf_cap_veh_h']
        neighbors[name] = dict(
            surrogate_ttt=result['surrogate']['ttt_omega_veh_h'],
            execution_ttt=result['execution']['ttt_omega_veh_h'],
            delta_execution=result['execution']['ttt_omega_veh_h']-chosen['ttt_omega_veh_h'],
            np=result['execution']['quantities']['np'],
            nuf=result['execution']['quantities']['nuf'])
    assert neighbors['selected']['delta_execution'] == 0
    pair = read(PAIR/'summary.json')
    fixed_release = {}
    for name, result in pair['results'].items():
        merge = result['control_area']['predicted_ramp_merge']
        assert merge['schema'] == 'predicted-physical-ramp-merge/v1'
        assert merge['start_sec'] == 2700 and merge['end_sec'] == 3150
        rate = merge['total_rate_veh_h']
        assert abs(rate - math.fsum(r['merge'] for r in result['ramps'].values())*8) < 1e-8
        fixed_release[name] = dict(nuf=rate, cap=caps['nuf_cap_veh_h'],
            excess_veh_h=rate-caps['nuf_cap_veh_h'],
            excess_vehicles450=(rate-caps['nuf_cap_veh_h'])/8,
            passes_this_decision_nuf_cap=rate <= caps['nuf_cap_veh_h']+1e-7,
            scope='Constraint-only comparison against this decision cap; no change to experiment or claim that physical commands are illegal')
    delta = dict(omega=chosen['ttt_omega_veh_h']-held['ttt_omega_veh_h'],
        tracked_outside=chosen['tracked_outside_residence_veh_h']-held['tracked_outside_residence_veh_h'],
        **{k:groups(chosen)[k]-v for k,v in groups(held).items()})
    delta['tracked_total'] = delta['omega']+delta['tracked_outside']
    query = selection['surrogate_query']
    secants = [r for r in selection['gradient_rows'] if r['kind']=='vsl' and r['key']=='FW_E__seg13']
    assert len(secants)==6 and all(r['derivative_method']=='executable_secant_fallback' for r in secants)
    out = dict(status='OFFLINE_SELECTION_AND_FINITE_VSL_CHECK_COMPLETE_PHYSICAL_GAIN_NOT_QUALIFIED',
        previous_goal_turn='NO_PROGRESS: explanation only; current PROGRESS: actual selection, exact execution and finite candidates',
        seed=67,start_sec=2700,duration_sec=450,blind_holdout=False,
        controller_calls=1,selection_converged=selection['converged'],
        selection_status=selection['selection_status'],
        controller_wall_sec=selection_receipt['controller_wall_sec'],
        solver_elapsed_sec=report['elapsed_sec'],
        selection_prediction_counts={k:query[k] for k in ('scalar_rollouts','tangent_rollouts','total_rollouts','failed_batches')},
        exact_check_forecasts=2,neighbor_surrogate_forecasts=3,neighbor_exact_forecasts=3,
        exact_check_compute_sec=sum(r['wall_sec'] for r in execution['results'].values()),
        fresh_caps=caps,commands=changes,exact_delta_veh_h=delta,
        exact_quantity_checks={k:v['canonical_quantity_constraints'] for k,v in execution['results'].items()},
        finite_vsl_neighbors=neighbors,activation_secants=secants,
        prior_fixed_release_under_current_cap=fixed_release,
        native_runs=0,fzp_scans=0,coefficient_fit=0,production_source_changes=0,
        source_pins_verified=len(protocol['source_pins']),
        old_STOP_unchanged=True,concurrent_DATA9000_untouched=True,
        limitations=[
            'No actual native outcome for this selected command or its VSL neighbors; not a native gain validation.',
            'The earlier measured VSL gain is conditional on stronger RM release with native city signals; selected city/RM is another control.',
            'Infeasible strong RM release does not prove VSL alone is constrained. Both tested VSL neighbors are feasible but costlier in the model.',
            'Two VSL neighbors and local secants do not prove global optimality, all combinations or all states.',
            'Other-Omega cost reduction is not an RM causal attribution. No city-only/RM-only factorial rerun here.',
            'Tracked outside residence omits unobserved native uninserted delay; do not call it complete total-system cost.',
            'Execution summary generic quantity_constraints text is stale; per-result canonical_quantity_constraints contain the actual checked fixed caps.',
            'First attempt failed at scipy import under sandbox before prediction; preserved separately. No optimizer or native automatic retry loop.',
            'Production off-entry/recovery/gain errors from REVIEW76 remain; no physical calibration adoption.'],
        input_sha256=pins,goal='ACTIVE / NOT_QUALIFIED')
    target = HERE/'assessment.json'
    assert not target.exists()
    target.write_text(json.dumps(out,indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps({k:out[k] for k in ('status','exact_delta_veh_h','finite_vsl_neighbors','prior_fixed_release_under_current_cap')}))
if __name__ == '__main__':
    main()

