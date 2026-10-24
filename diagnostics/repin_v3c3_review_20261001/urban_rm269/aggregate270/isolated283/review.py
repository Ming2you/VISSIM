"""Compare one new current-clock forecast to the exact reusable hold and native pair."""
import gzip, hashlib, importlib.util, json, pickle, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
H = HERE.parent.parent
read = lambda p: json.loads(Path(p).read_bytes())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    assert not (HERE / 'review.json').exists()
    sys.path[:0] = [str(ROOT), str(ROOT / 'vendor/NumSim-mine')]
    spec = importlib.util.spec_from_file_location('boundary280', HERE.parent / 'matched280/review.py')
    boundary = importlib.util.module_from_spec(spec); spec.loader.exec_module(boundary)
    folders = {'hold': HERE.parent / 'matched280/authority', 'selected': HERE / 'selected2400'}
    results, identities, pins = {}, {}, {}
    for arm, folder in folders.items():
        s = read(folder / 'summary.json')
        assert s['status'] == 'complete'
        assert all(sha(p) == digest for p, digest in s['source_pins'].items())
        cfg, _, _ = pickle.loads((folder / 'initial.pickle').read_bytes())
        value = s['results'][arm]
        assert value['shared_constraints']['feasible'] and value['writer_three_blocks']
        assert value['resource_max_exceedance'] < 1e-7
        response = json.loads(gzip.decompress((folder / (arm + '.response.json.gz')).read_bytes()))
        stocks = read(folder / (arm + '.stocks.json'))
        identities[arm] = boundary.model_boundary(response, stocks, value['omega_ttt_veh_h'], cfg)
        results[arm] = value
        pins[str(folder / 'summary.json')] = sha(folder / 'summary.json')
    current = read(HERE / 'selected2400/summary.json')
    assert current['forecasts'] == 1 and current['reused_forecasts'] == 1
    assert current['application']['state_error'] == 0
    for name in ('np','nuf'):
        assert results['hold']['shared_constraints'][name]['target'] == results['selected']['shared_constraints'][name]['target']
    native = read(H / 'isolated10681/practical_calibration_assessment.json')
    native_execution = read(H / 'isolated10681/native_analysis/summary.json')
    assert native_execution['counterfactual_valid'] and native_execution['common_start_vehicle_records_exact']
    footprint = read(H / 'native2400_component_footprint.json')['groups']
    costs = {k:results['selected']['costs_by_stock'].get(k,0) - results['hold']['costs_by_stock'].get(k,0)
             for k in set(results['selected']['costs_by_stock']) | set(results['hold']['costs_by_stock'])}
    groups = {g: sum(costs.get(k,0) for k in value['initial_model_stock_keys']) +
                  (costs.get('transit:gate:in_SC1004_S',0) if g=='approach66' else 0)
              for g,value in footprint.items()}
    groups.update(ramp10681=costs['ramp:RM_C10681'],ramp10646=costs['ramp:RM_C10646'],
                  mainline=sum(v for k,v in costs.items() if k.startswith('freeway:')))
    groups['other_Omega'] = sum(costs.values()) - sum(groups.values())
    groups['Omega'] = sum(costs.values())
    assert abs(groups['Omega'] - (results['selected']['omega_ttt_veh_h']-results['hold']['omega_ttt_veh_h'])) < 1e-7
    material = ('approach52_with58','shared_W_out','ramp10681','mainline')
    signs = {k: groups[k]*native['native_cost_delta_veh_h'][k]>0 for k in material}
    extra = results['selected']['predicted_merge']['accepted_vehicles_by_ramp']['RM_C10681'] - results['hold']['predicted_merge']['accepted_vehicles_by_ramp']['RM_C10681']
    for p in (Path(__file__), H / 'isolated10681/practical_calibration_assessment.json', H / 'isolated10681/native_analysis/summary.json', H / 'native2400_component_footprint.json'):
        pins[str(p)] = sha(p)
    result = dict(status='current_fw5_u10_isolated10681_macro_checked', native_cost_delta_veh_h=native['native_cost_delta_veh_h'],
        predicted_cost_delta_veh_h=groups, native_added_merge_veh=native['native_added_merge'], predicted_added_merge_veh=extra,
        material_sign_checks=signs, material_directions_pass=all(signs.values()),
        same_initial_state_error=current['application']['state_error'],same_forecast=True, same_physical_controls_except10681=True,
        same_np_nuf_caps_feasible=True, conservation_and_boundary_cost_identity=True,
        new_forecasts=1,reused_forecasts=1,scalar_compute_sec=results['selected']['wall_sec'],
        optimizer_calls=0,native_runs=0,fits=0,fzp_rescans=0,source_pins=pins,
        limitations=['WholeOmega actual+0.213 versus model negative is near cancellation, not proof of a material net benefit or a target for fitting.',
            '52+58/sharedWout stock groups use initial support, not exact future physical road ownership; do not call sharedWout link68 alone.',
            'Same seed29/state2400 development case. Seed47 validation282 is a separate10484 comparison.',
            'Native5s sampled/trapezoid versus model10s end-stock integration; each ledger closes separately.',
            'This fixed-action pair is not an SDMPC selection. Final current-config selection remains separate.'])
    for name,value in [('boundary_identity.json',identities),('review.json',result)]:
        (HERE/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps({k:result[k] for k in ('material_directions_pass','native_added_merge_veh','predicted_added_merge_veh','predicted_cost_delta_veh_h','same_np_nuf_caps_feasible')},ensure_ascii=False))

if __name__ == '__main__':main()
