"""Verify completed selection/ablation artifacts; no model or native execution."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
LABEL = 'rm_pair_s47_cell23_v2'
pins = {}

def load(path):
    data = path.read_bytes()
    pins[str(path)] = hashlib.sha256(data).hexdigest()
    return json.loads(data)

selection_dir = BASE / ('closedloop_recorded2700_select_' + LABEL)
selection_receipt = load(selection_dir / 'summary.json')
joint = load(selection_dir / 'unused_action.joint.json')
selected = joint['selection']
old = load(BASE / ('closedloop_recorded2700_select_check_' + LABEL) / 'summary.json')
vsl = load(BASE / ('closedloop_recorded2700_budget_check_selected_vsl13_' + LABEL) / 'summary.json')
parts = load(BASE / ('closedloop_recorded2700_budget_check_selected_components_' + LABEL) / 'summary.json')
native = load(HERE / 'analysis/summary.json')
assert native['counterfactual_valid'] and native['paired_prefix_exact']
assert joint['completed'] and selected['feasible']
assert not selection_receipt['native_started'] and not selection_receipt['gain_qualified']
assert old['future_observation_inputs'] is False

# Resolve the exact harness used for selection, without pretending newer code
# was used historically. All non-harness pins must still match their originals.
selection_pins = {}
for name, digest in selection_receipt['files'].items():
    path = Path(name)
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        assert path.name == 'probe_selected_arrival_path.py', name
        path = BASE / 'executed_sources' / (path.stem + '_' + digest + path.suffix)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest, path
    selection_pins[name] = dict(verified_path=str(path), sha256=digest)

held, applied = old['results']['held_actual'], old['results']['selected']
assert abs(applied['ttt_omega_veh_h'] - vsl['results']['selected']['execution']['ttt_omega_veh_h']) < 1e-7
rows = {}
for label, audit in (('vsl', vsl), ('components', parts)):
    assert audit['selected_surrogate_and_execution_reproduced']
    assert audit['selected_budget_caps_frozen']
    assert audit['optimizer_iterations'] == 0 and not audit['native_started']
    for name, result in audit['results'].items():
        execution = result['execution']
        assert execution['conditional_model_feasibility_witness']
        assert execution['model_constraint_coverage']['complete']
        assert execution['resource_max_exceedance'] < 1e-7
        assert max(abs(r['residual']) for r in execution['ramps'].values()) < 1e-7
        for q in ('np', 'nuf'):
            assert execution['quantities'][q]['target'] == selected['final_constraints'][q]['target']
        rows[label + '/' + name] = dict(
            omega_ttt=execution['ttt_omega_veh_h'],
            delta_omega_vs_held=execution['ttt_omega_veh_h']-held['ttt_omega_veh_h'],
            delta_outside_vs_held=execution['tracked_outside_veh_h']-held['tracked_outside_residence_veh_h'],
            np_nuf_feasible=execution['quantities']['feasible'],
            np=execution['quantities']['np'], nuf=execution['quantities']['nuf'],
            merge10490=execution['ramps']['RM_C10490']['merges'],
            merge10484=execution['ramps']['RM_C10484']['merges'])
        rows[label + '/' + name]['delta_with_tracked_outside'] = (
            rows[label + '/' + name]['delta_omega_vs_held'] + rows[label + '/' + name]['delta_outside_vs_held'])

stop = Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP')
stop_hash = hashlib.sha256(stop.read_bytes()).hexdigest()
assert stop_hash == '91b2163b02b01447242909dee8e7f773d18e76a6594bd9db8de64d2a48246fc3'
cache = joint['physical_response_cache']
report = dict(
    start_sec=2700, horizon_sec=450, seed=47,
    selected_plan=parts['results']['selected']['commands'],
    held_omega_ttt=held['ttt_omega_veh_h'],
    held_tracked_outside=held['tracked_outside_residence_veh_h'],
    surrogate_delta=selected['selected_objective']-selected['held_objective'],
    execution_delta=applied['ttt_omega_veh_h']-held['ttt_omega_veh_h'],
    rows=rows, component_attribution=parts['components'],
    controller_wall_sec=selection_receipt['controller_wall_sec'],
    pfo={k:selected['pfo_warm_start'][k] for k in ('max_iterations','executed_iterations','accepted_iterations','converged')},
    sdmpc=dict(max_iterations=selected['policy']['max_iterations'],
               executed_iterations=len(selected['iteration_dual_updates']),converged=selected['converged']),
    selection_rollouts={k:cache[k] for k in ('scalar_rollouts','tangent_rollouts','total_rollouts','cache_hits')},
    saved_selection_pins=selection_pins, files=pins, stop_sha256=stop_hash,
    new_rollouts_in_verifier=0, new_native_runs=0, coefficients_changed=False,
    selected_native_gain_validated=False, goal_qualified=False,
    limitations=[
        'Selected city/RM command has model validation only; native pair tested10484 hold/release, not this selection.',
        'Two PFO and two SDMPC iterations are not convergence or global optimality.',
        'VSL100/90 results cover FW_E__seg13 with three constant blocks at one saved state only.',
        'Tracked external residence excludes unrepresented external queues and is not added to the objective.',
        'Seed47 has been inspected before and is not a pristine held-out calibration test.',
        'Finite ablations are conditional on the chosen other levers, not independent physical causal components.'])
target = HERE / 'controller_comparison.json'
assert not target.exists(), 'Preserve prior completed comparisons'
target.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
print(json.dumps(dict(controller_wall_sec=report['controller_wall_sec'],
                     components=parts['components'],rows=rows), ensure_ascii=False))
