"""Separate current RM-corridor response from the joint urban-signal cost error.

Reads only closed result summaries. Initial projection footprints cannot prove
the location of all future transit, so they are diagnostic attribution only.
"""
from pathlib import Path
import hashlib, importlib.util, json

HERE = Path(__file__).resolve().parent
H = HERE.parent
pins = {}


def read(path):
    pins[str(path.resolve())] = hashlib.sha256(path.read_bytes()).hexdigest()
    return json.loads(path.read_bytes())


def main():
    target = HERE / 'upstream_cost_split.json'
    assert not target.exists()
    loader = importlib.util.spec_from_file_location('qualification', H / 'qualify_native2400.py')
    qualification = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(qualification)
    scope = qualification.validate_scope(read(H / 'native2400_analysis/summary.json'),
        read(H / 'native2400_analysis/observed_input_qualification.json'))
    old = read(H / 'native2400_analysis/initial_support_cost_diagnostic.json')
    footprint = read(H / 'native2400_component_footprint.json')
    models = {a: read(H / 'spatial_receiving/forecast2400' / (a + '.json')) for a in ('hold', 'selected')}
    actual = {a: read(H / 'native2400_analysis' / a / 'area_metrics.json')['physical_link_residence'] for a in models}
    aggregate = read(H / 'spatial_receiving/assessment.json')
    history = read(H / 'native238_validation/assessment.json')
    used_links, used_stocks, rows = set(), set(), []
    for group in old['groups']:
        links, stocks = list(group['links']), list(group['stocks'])
        if stocks == ['storage:SC1004_W_out']:
            links.append('10772')  # downstream connector also belongs to this stock
        if 'storage:in_SC1004_S' in stocks and 'transit:gate:in_SC1004_S' not in stocks:
            stocks.append('transit:gate:in_SC1004_S')
        assert len(stocks) == len(set(stocks)) and len(links) == len(set(links))
        assert not (used_links & set(links)) and not (used_stocks & set(stocks))
        used_links.update(links)
        used_stocks.update(stocks)
        pred = {a: sum(models[a]['costs_by_stock'].get(k, 0.) for k in stocks) for a in models}
        observed = {a: sum(actual[a][k]['ttt_veh_h'] for k in links) for a in models}
        assert all(actual[a][k]['inside'] for a in models for k in links)
        native_delta, model_delta = observed['selected'] - observed['hold'], pred['selected'] - pred['hold']
        label = None
        for name, known in footprint['groups'].items():
            if set(known['initial_model_stock_keys']) <= set(stocks):
                label = name
        rows.append(dict(label=label, links=links, stocks=stocks,
            actual_delta_veh_h=native_delta, predicted_delta_veh_h=model_delta,
            delta_error_veh_h=model_delta - native_delta))
    rows.sort(key=lambda row: row['delta_error_veh_h'])
    assert abs(next(r for r in rows if r['label'] == 'shared_W_out')['actual_delta_veh_h']
               - aggregate['native_delta']['W_out']) < 1e-7
    report = dict(status='complete', paired_scope=scope, attribution_scope=old['scope'],
        observed_window=[2400, 2850], delta_definition='selected minus hold; positive means more TTT',
        controls='Joint urban green/offset and multiple RM changes, not isolated10681 effect',
        disjoint_cost_deltas=aggregate['disjoint_cost_deltas'], initial_support_groups=rows,
        known_upstream=[r for r in rows if r['label'] in ('approach52_with58', 'approach66')],
        historical_RM_only=dict(window=[4650,5100], actual_delta=history['native_delta_omega_veh_h'],
            mainline_delta=history['native_delta_components_veh_h']['mainline'],
            nonmainline_delta=history['native_delta_components_veh_h']['nonmainline'],
            usable_as_current_min2_choice=False,
            reason='Historical0s held command and inherited selectedNUF failure; small net sign is not a fitting target.'),
        causal_conclusions=[
            'Current whole-Omega disagreement must not be attributed solely to10681 ramp dynamics.',
            '52/58 model understates the native improvement;66 difference is small after counting gate transit.',
            'SC6/SC101 initial-support groups are large residual contributors; this is not exact future spatial assignment.',
            'SC101 old straight service cap still binds after verified SC1 supply correction. Test previously audited cap once.',
            'SC6 has a known supply shortfall; adding its fixed intermediate gate alone cannot recover missing arrivals.'
        ], source_pins=pins, new_predictions=0, new_fits=0, new_native=0, FZP_scans=0)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8')
    print(json.dumps(dict(known_upstream=report['known_upstream'], largest=rows[:5]), ensure_ascii=False))


if __name__ == '__main__':
    main()
