"""Assess two completed fixed-command forecasts; no simulator or model calls."""
import hashlib
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
INTEGRATION = ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926'
RESULTS = INTEGRATION / 'closedloop_recorded2700_lever450_service66rm47_after_rm47'
PINS = {}


def read(path):
    raw = path.read_bytes()
    PINS[str(path)] = hashlib.sha256(raw).hexdigest()
    return json.loads(raw)


def main():
    protocol = read(HERE / 'protocol.json')
    for name, expected in protocol['source_pins'].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == expected, name
    prior = read(HERE.parent / 'sc1001_route_inventory_s47/assessment.json')
    native = read(INTEGRATION / 'native_rm_observation2700_writerfix_v3/analysis/summary.json')
    assert native['paired_prefix_exact']
    assert all(row['native_execution_passed'] for row in native['arms'].values())
    local = read(HERE / 'after_rm47_local.json')
    summary = read(RESULTS / 'summary.json')
    assert summary['optimizer_iterations'] == 0 and not summary['future_observation_inputs']
    assert len(local) == 2
    assert local[0]['full_stock_witness'][0] == local[1]['full_stock_witness'][0]
    cases = {}
    balance_max = resource_max = compute_sec = 0.
    for name, label, trace in zip(('held_actual', 'release_actual'), ('hold', 'release'), local):
        point = read(RESULTS / (name + '.json'))
        old = read(INTEGRATION / 'closedloop_recorded2700_lever450_sc1001_causal_history_routes' / (name + '.json'))
        assert point['commands'] == old['commands'], name
        assert point['validation']['all_actuator_and_step_constraints_checked']
        compute_sec += point['wall_sec']
        transfers = trace['all_transfers_aggregated']
        first, last = (trace['full_stock_witness'][j]['stock'] for j in (0, -1))
        residuals = {}
        for stock in first.keys() | last.keys():
            incoming = math.fsum(t['vehicles'] for t in transfers if t['target'] == stock)
            outgoing = math.fsum(t['vehicles'] for t in transfers if t['source'] == stock)
            residuals[stock] = last.get(stock, 0.) - first.get(stock, 0.) - incoming + outgoing
        error = max(map(abs, residuals.values()))
        assert error < 1e-7, (name, sorted(residuals.items(), key=lambda p: abs(p[1]))[-3:])
        balance_max = max(balance_max, error)
        resource_max = max(resource_max, trace['resource_max'])
        assert resource_max < 1e-7
        flow = {'source': 0., 'merge': 0., 'off': 0., 'terminal': 0.}
        for event in transfers:
            s, t, n = event['source'], event['target'], event['vehicles']
            if t == 'freeway:FW_E':
                category = 'source' if s == 'origin:FW_E' else 'merge'
                assert category == 'source' or s.startswith('merge_pending:')
                flow[category] += n
            elif s == 'freeway:FW_E':
                category = 'terminal' if t == 'external:terminal:FW_E' else 'off'
                assert category == 'terminal' or t.startswith('storage:')
                flow[category] += n
        c = point['cost_by_stock']
        cases[label] = dict(omega=point['ttt_omega_veh_h'], east=c['freeway:FW_E'],
            west=c['freeway:FW_W'], ramps=sum(v for k, v in c.items() if k.startswith('ramp:')),
            outside=point['tracked_outside_residence_veh_h'],
            tracked_total=point['ttt_with_tracked_outside_veh_h'], **flow,
            end_east_vehicles=last['freeway:FW_E'],
            ramp10484=point['ramps']['RM_C10484'], max_stock_balance_error=error)
    fields = ('omega', 'east', 'west', 'ramps', 'outside', 'tracked_total',
              'source', 'merge', 'off', 'terminal', 'end_east_vehicles')
    delta = {k: cases['release'][k] - cases['hold'][k] for k in fields}
    assert delta['omega'] > 0 and delta['east'] > 0 and delta['ramps'] < 0
    doc = dict(status='STRONG_RM_DIRECTION_RETAINED_NOT_FULL_GAIN_QUALIFICATION',
        cases=cases, release_minus_hold=dict(current=delta,
            old_routed=prior['release_minus_hold']['after'], native=prior['release_minus_hold']['native']),
        same_executed_commands=True, same_initial_model_stocks=True,
        max_full_stock_balance_error=balance_max, max_resource_exceedance=resource_max,
        forecasts=2, forecast_compute_sec=compute_sec, fit=0, new_native=0, new_fzp=0,
        controller_constraint_scope='Physical/writer checks passed; no fresh PFO or SDMPC solve. Old fixed cap473.589 is not a fresh decision cap.',
        limitations=['Existing seed47 strong-RM case, not a new heldout state.',
            'Native5s Omega includes held final4.9s, unresolved disappearances and network removals retained from original receipt.',
            'Model tracked outside residence differs from native whole-network and uninserted delay scope.',
            'Seed43 VSL sign failure remains; source-admission confounding not absorbed into model coefficients.',
            'Current PFO-cap solver regenerates budgets from its current warm prediction; no target was changed here.'],
        source_pins=PINS)
    (HERE / 'assessment.json').write_text(json.dumps(doc, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(delta=delta, native=doc['release_minus_hold']['native'],
        balance=balance_max, resource=resource_max, seconds=compute_sec), ensure_ascii=False))


def selection():
    chosen = INTEGRATION / 'closedloop_recorded2700_select_service66_current'
    check = INTEGRATION / 'closedloop_recorded2700_select_check_service66_current'
    component = INTEGRATION / 'closedloop_recorded2700_budget_check_selected_components_service66_current'
    report = read(chosen / 'unused_action.joint.json')['selection']
    receipt = read(chosen / 'summary.json')
    timing = read(chosen / 'unused_action.decision_budget.json')
    points = {name: read(check / (name+'.json')) for name in ('held_actual', 'selected')}
    assert points['held_actual']['ttt_omega_veh_h'] == read(RESULTS / 'held_actual.json')['ttt_omega_veh_h']
    assert all(p['canonical_quantity_constraints']['feasible'] for p in points.values())
    assert points['selected']['validation']['written_command_binding_passed']
    assert points['selected']['validation']['prewrite_binding_passed']
    for p in points.values():
        assert p['saved_state_stock_witness']['passed']
        for resource in ('np', 'nuf'):
            assert p['canonical_quantity_constraints'][resource]['target'] == report['final_constraints'][resource]['target']
    def costs(p):
        c = p['cost_by_stock']
        return dict(omega=p['ttt_omega_veh_h'], outside=p['tracked_outside_residence_veh_h'],
                    east=c['freeway:FW_E'], west=c['freeway:FW_W'],
                    ramps=sum(v for k, v in c.items() if k.startswith('ramp:')),
                    tracked_total=p['ttt_with_tracked_outside_veh_h'])
    before, after = (costs(points[k]) for k in ('held_actual', 'selected'))
    delta = {k: after[k]-before[k] for k in before}
    commands = []
    for block, (old, new) in enumerate(zip(points['held_actual']['commands'], points['selected']['commands'])):
        commands.append(dict(block=block, changed={field: {k: [v, new[field][k]] for k, v in old[field].items()
                            if v != new[field][k]} for field in ('vsl', 'meters', 'green_times', 'offsets')}))
    comp = read(component / 'summary.json')
    assert comp['selected_surrogate_and_execution_reproduced']
    variants = {}
    for name, result in comp['results'].items():
        e = result['execution']
        assert e['quantities']['feasible']
        variants[name] = dict(omega=e['ttt_omega_veh_h'],
            delta_versus_held=e['ttt_omega_veh_h']-before['omega'],
            delta_versus_selected=e['ttt_omega_veh_h']-after['omega'],
            outside=e['tracked_outside_veh_h'], surrogate=result['surrogate']['ttt_omega_veh_h'],
            np=e['quantities']['np']['actual'], nuf=e['quantities']['nuf']['actual'])
    doc = dict(status='CURRENT_OFFLINE_SELECTION_AND_EXECUTION_REPLAY_COMPLETE_NOT_NATIVE_VALIDATED',
        surrogate_delta=report['selected_objective']-report['held_objective'],
        exact_delta=delta, exact_costs=dict(held=before, selected=after), commands=commands,
        all_fixed_cap_checks_passed=True, quantities={k:p['canonical_quantity_constraints'] for k,p in points.items()},
        fresh_cap_initialization=report['budget_initialization'],
        pfo={k:report['pfo_warm_start'][k] for k in ('executed_iterations', 'accepted_iterations', 'converged')},
        sdmpc_candidates=report['candidates'], converged=report['converged'],
        controller_wall_sec=receipt['controller_wall_sec'], inclusive_budget_wall_sec=timing['wall_sec'],
        selection_prediction_counts={k:report['surrogate_query'][k] for k in ('scalar_rollouts','tangent_rollouts','total_rollouts')},
        exact_check_forecasts=2, exact_check_compute_sec=sum(p['wall_sec'] for p in points.values()),
        components=variants, component_surrogate_forecasts=comp['surrogate_rollouts'],
        component_exact_forecasts=comp['execution_rollouts'],
        component_exact_compute_sec=sum(x['execution']['wall_sec'] for x in comp['results'].values()),
        native_started=False, fitting=0, source_pins=PINS)
    (HERE / 'selection_assessment.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(delta=delta,components=variants,commands=commands,converged=doc['converged']),ensure_ascii=False))


if __name__ == '__main__':
    selection() if '--selection' in sys.argv else main()
