"""Reuse closed native metrics and four model responses; no new simulation."""
import csv
import gzip
import hashlib
import json
import pickle
from collections import defaultdict
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
H = HERE.parent.parent
read = lambda p: json.loads(Path(p).read_bytes())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def model_boundary(response, stocks, ttt, cfg):
    """Exact impulse accounting under this model's10s endpoint quadrature."""
    residence = response['residence']
    initial = sum(x['inside'] for x in stocks[0]['stocks'].values())
    routes = defaultdict(lambda: dict(entered=0., departed=0., generated_inside=0., entry_cost=0., departure_cost=0., generation_cost=0.))
    for row in response['transfers']:
        entry, departure = row['entered_veh'], row['ttd_veh']
        generated = 0.
        if row['source'] is None:
            # emit_input creates traffic on its physical side; this is NOT
            # an area-boundary crossing. Count its inventory addition separately.
            if row['route_key'] == 'input:gate_wait:' + cfg.network.physical_gate_travel['source']:
                # physical_ramp_branches.advance_gate explicitly generates
                # uninserted vehicles outsideOmega before admitting them.
                assert row['target'] == 'transit:gate_wait:' + cfg.network.physical_gate_travel['source']
            else:
                route = cfg.network.control_area_routes[row['route_key']]
                assert type(route.get('target_inside')) is bool, row['route_key']
                generated = row['vehicles'] if route['target_inside'] else 0.
        if not entry and not departure and not generated:
            continue
        weight = sum(x['dt_h'] for x in residence if x['end_sec'] >= row['end_sec'] - 1e-7)
        q = routes[row['route_key']]
        q['entered'] += entry
        q['departed'] += departure
        q['generated_inside'] += generated
        q['entry_cost'] += entry * weight
        q['departure_cost'] -= departure * weight
        q['generation_cost'] += generated * weight
    reconstructed = initial * sum(r['dt_h'] for r in residence) + sum(q['entry_cost'] + q['departure_cost'] + q['generation_cost'] for q in routes.values())
    assert abs(reconstructed - ttt) < 1e-7, ('TTT boundary identity', reconstructed, ttt)
    final = sum(x['inside'] for x in stocks[-1]['stocks'].values())
    assert abs(initial + sum(q['entered'] + q['generated_inside'] - q['departed'] for q in routes.values()) - final) < 1e-7
    return dict(initial_inside=initial, final_inside=final, routes=dict(routes), reconstructed_ttt=reconstructed)


def native_boundary():
    columns = ['observed_entry_events', 'appeared_inside_events', 'reappeared_inside_events',
               'observed_exit_events', 'terminal_exit_inferred_events', 'unresolved_inside_disappearances']
    totals, series = {}, {}
    for arm in ('hold', 'selected'):
        path = H / 'native2400_analysis' / arm / 'area_timeseries.csv'
        rows = list(csv.DictReader(path.open(encoding='utf8')))
        rows = [r for r in rows if float(r['sim_sec']) > 2400]
        values = {c: dict(vehicles=0., weighted_veh_h=0.) for c in columns}
        for row in rows:
            end, dt = float(row['sim_sec']), float(row['interval_sec'])
            assert abs(float(row['stock_closure_residual_veh'])) < 1e-7
            weight = (2850 - end + dt / 2) / 3600
            for i, key in enumerate(columns):
                n = float(row[key])
                values[key]['vehicles'] += n
                values[key]['weighted_veh_h'] += n * weight * (1 if i < 3 else -1)
        totals[arm] = values
        series[arm] = rows
    delta = {c: {k: totals['selected'][c][k] - totals['hold'][c][k] for k in totals['hold'][c]} for c in columns}
    actual = read(H / 'native2400_analysis/summary.json')['delta_TTT_veh_h']
    assert abs(sum(v['weighted_veh_h'] for v in delta.values()) - actual) < 1e-7
    return dict(delta=delta, totals=totals, final_inside_delta=float(series['selected'][-1]['inside_vehicles']) - float(series['hold'][-1]['inside_vehicles']),
                quadrature='Existing native5s trapezoidal samples; preserved4.9s censored hold tail, disappearance separate from counted exit.')


def main():
    target = HERE / 'review.json'
    assert not target.exists()
    sys.path.insert(0, str(H))
    root = HERE.parents[4]
    sys.path[:0] = [str(root), str(root / 'vendor/NumSim-mine')]
    from qualify_native2400 import validate_scope
    validate_scope(read(H / 'native2400_analysis/summary.json'), read(H / 'native2400_analysis/observed_input_qualification.json'))
    audit = read(H / 'native2400_analysis/component_audit.json')
    footprint = read(H / 'native2400_component_footprint.json')['groups']
    support = read(H / 'native2400_analysis/initial_support_cost_diagnostic.json')
    all_results, pins = {}, {}
    for variant in ('baseline', 'authority'):
        folder = HERE / variant
        summary = read(folder / 'summary.json')
        assert summary['status'] == 'complete' and summary['forecasts'] == 2
        assert summary['native_runs'] == summary['optimizer_calls'] == summary['fits'] == 0
        assert all(sha(p) == digest for p, digest in summary['source_pins'].items())
        pins[str(folder / 'summary.json')] = sha(folder / 'summary.json')
        results = summary['results']
        cfg, _, _ = pickle.loads((folder / 'initial.pickle').read_bytes())
        by_arm, boundary, counts = {}, {}, {}
        for arm, value in results.items():
            assert value['writer_three_blocks'] and value['conservation_states'] == 4
            assert value['resource_max_exceedance'] < 1e-7
            assert abs(sum(value['costs_by_stock'].values()) - value['omega_ttt_veh_h']) < 1e-7
            model_stocks = read(folder / (arm + '.stocks.json'))
            r = json.loads(gzip.decompress((folder / (arm + '.response.json.gz')).read_bytes()))
            boundary[arm] = model_boundary(r, model_stocks, value['omega_ttt_veh_h'], cfg)
            counts[arm] = []
            costs = value['costs_by_stock']
            keys = {g: set(v['initial_model_stock_keys']) for g, v in footprint.items()}
            keys['approach66'].add('transit:gate:in_SC1004_S')
            keys.update(ramp10681={'ramp:RM_C10681'}, ramp10646={'ramp:RM_C10646'})
            by_arm[arm] = {g: sum(costs.get(k, 0.) for k in members) for g, members in keys.items()}
            by_arm[arm]['mainline'] = sum(v for k, v in costs.items() if k.startswith('freeway:'))
            by_arm[arm]['remaining_omega'] = value['omega_ttt_veh_h'] - sum(by_arm[arm].values())
            by_arm[arm]['omega'] = value['omega_ttt_veh_h']
            for observed, modeled in zip(audit['arms'][arm]['physical_link_stocks'], model_stocks):
                assert observed['sim_sec'] == modeled['time_sec']
                forecast = {g: sum(modeled['stocks'].get(k, {}).get('inside', 0.) for k in keys[g]) for g in footprint}
                counts[arm].append(dict(sec=modeled['time_sec'], actual=observed['grouped_total_vehicles'], model_initial_support=forecast))
        delta = {k: by_arm['selected'][k] - by_arm['hold'][k] for k in by_arm['hold']}
        route_delta = {}
        for k in set(boundary['hold']['routes']) | set(boundary['selected']['routes']):
            a, b = boundary['hold']['routes'].get(k, {}), boundary['selected']['routes'].get(k, {})
            route_delta[k] = {field: b.get(field, 0.) - a.get(field, 0.) for field in ('entered', 'departed', 'generated_inside', 'entry_cost', 'departure_cost', 'generation_cost')}
        integrated = sum(v['entry_cost'] + v['departure_cost'] + v['generation_cost'] for v in route_delta.values())
        assert abs(integrated - delta['omega']) < 1e-7
        ranked = []
        for group in support['groups']:
            predicted = sum(results['selected']['costs_by_stock'].get(k, 0.) - results['hold']['costs_by_stock'].get(k, 0.) for k in group['stocks'])
            ranked.append(dict(stocks=group['stocks'], links=group['links'], native_joint_delta=group['native_delta'],
                               predicted_joint_delta=predicted, error=predicted-group['native_delta']))
        ranked.sort(key=lambda x: abs(x['error']), reverse=True)
        all_results[variant] = dict(delta_cost_veh_h=delta, absolute_omega={a:r['omega_ttt_veh_h'] for a,r in results.items()},
            extra_merge10681=results['selected']['predicted_merge']['accepted_vehicles_by_ramp']['RM_C10681'] - results['hold']['predicted_merge']['accepted_vehicles_by_ramp']['RM_C10681'],
            shared_feasible={a:r['shared_constraints']['feasible'] for a,r in results.items()}, stocks=counts,
            boundary=boundary, boundary_delta_by_route=route_delta, initial_support_ranked=ranked,
            wall_sec={a:r['wall_sec'] for a,r in results.items()})
    report = dict(status='matched_native_pair_cost_direction_still_wrong', new_scalar_forecasts=4,
        new_native_runs=0, new_full_selections=0, coefficient_fits=0,
        delta_definition='Actual jointcity+RMselected minus held, same2400state and450s window; not isolatedRM causal effect.',
        native_delta_cost_veh_h=audit['cost_comparison']['native_selected_minus_hold_veh_h'],
        actual_extra_merge10681=sum(w['merge'] for w in audit['arms']['selected']['ramps']['RM_C10681']) - sum(w['merge'] for w in audit['arms']['hold']['ramps']['RM_C10681']),
        native_boundary=native_boundary(), variants=all_results, source_pins=pins,
        limitations=['52+58 and ranked initial support groups are incomplete future geographic correspondence; mainline/wholeOmega scopes remain valid.',
            'Model10s endpoint versus native5s trapezoid/tail quadrature; boundary identities hold separately.',
            'Model ttd_veh is anOmega boundary departure count, not travelled distance or necessarily network termination.',
            'Native unresolved disappearance is kept separate, not promoted to normal discharge.',
            'Oneusedseed/state; not independentseed or closedloop performance validation.'])
    for p in (Path(__file__), H/'native2400_analysis/component_audit.json', H/'native2400_analysis/initial_support_cost_diagnostic.json'):
        pins[str(p)] = sha(p)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf8')
    print('NATIVE', report['native_delta_cost_veh_h'])
    print('NATIVE_BOUNDARY', report['native_boundary']['delta'])
    for name, r in all_results.items():
        print(name, r['delta_cost_veh_h'], 'extra10681', r['extra_merge10681'], 'feasible', r['shared_feasible'])
        print('ROUTES', sorted(r['boundary_delta_by_route'].items(), key=lambda kv: abs(kv[1]['entry_cost']+kv[1]['departure_cost']), reverse=True)[:8])
        print('STOCKS', r['stocks'])


if __name__ == '__main__':
    main()
