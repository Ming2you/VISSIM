"""Compare the configured first-exit route fraction with a served-flow proxy.

No new demand, capacity, future observation or benefit-fit parameter is added.
"""
from pathlib import Path
import sys
import hashlib
import json
import xml.etree.ElementTree as ET
import argparse
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e, H, MODEL, CASES, ARMS
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.fit_response import parts

HERE = Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--inventory',action='store_true')
    args=parser.parse_args()
    out = HERE/('upstream_exit_inventory_v1/replay' if args.inventory else 'configured_exit_ratio_v1')
    out.mkdir(exist_ok=False)
    network = HERE/'native_v1/none_s23/source/baseline.inpx'
    root = ET.parse(network).getroot()
    decision = next(n for n in root.findall('./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic') if n.get('no') == '1130')
    assert decision.get('link') == '74'
    routes = decision.findall('./vehRoutSta/vehicleRouteStatic')
    assert [r.get('relFlow') for r in routes] == ['2 0:2', '2 0:8', '2 0:2']
    weights = [float(r.get('relFlow').split(':')[1]) for r in routes]
    ratio = sum(w for w, r in zip(weights, routes) if r.get('destLink') == '10643') / sum(weights)
    base = HERE/'port_origin_split_v1/config.json'
    lane = HERE/'urban_boundary_rollout_lanes_v1/lane_config.json'
    parameter_file = HERE/'port_travel_fit_v1/selected_parameters.json'
    params = e.load(parameter_file)['parameters']
    profile = e.load(MODEL/'port_profile.json')
    configs={'reference':base,'configured_ratio':base,'configured_ratio_lanes':lane}
    if args.inventory:
        configs.pop('configured_ratio_lanes')
        for mode,source in [('upstream_inventory',base),('upstream_inventory_lanes',lane)]:
            cfg=e.load(source)
            cfg['freeway']['physical_upstream_exit_inventory']={'10643':ratio}
            configs[mode]=out/f'{mode}_config.json'
            e.save(configs[mode],cfg)
    pins = {str(p.relative_to(e.ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in
            [Path(__file__), network, base, lane, parameter_file, e.CAL/'canonical_harness.py',
             H/'evaluate_response.py', e.ROOT/'evaluation/controllers/physical_lane_groups.py',*configs.values()]}
    results = {}
    for seed, folder, bank, start in CASES:
        data = e.ObservationData(folder)
        lanes = e.load(H/'lane_group_response_20260919'/f'observations_v1/s{seed}.json')
        origins = e.load(HERE/f'port_positions_v1/s{seed}.json')
        protocol = e.load(bank/'protocol.json')
        modes, guards = {}, {}
        for mode,config in configs.items():
            model = e.load_base_model(data.geometry, config)
            off = model.offramps['10643']
            assert all(p['chain_pos_m'] > off['chain_pos_m'] for p in model.ramps.values() if p['road'] == 'FW_E')
            def window(t, command):
                w = e.window(data, model, t, 'history_forecast', profile, command, port_origin_counts=origins['counts'])
                w['lane_group_dynamics'] = {'FW_E': {**lanes['geometry'], **lanes['cutoffs'][str(t)],
                    'initial_ramp_origin': origins['counts'][str(t)],
                    'initial_off_eligible': origins['eligible_before_off'][str(t)]}}
                if mode != 'reference':
                    for step in w['boundary_steps']:
                        step['off_split_ratio']['10643'] = ratio
                return w
            guards[mode] = {}
            for t in (900, 1650, 2400, 3600):
                guards[mode][str(t)] = e.score_rollout(data, t, e.simulate(model, window(t, lambda _: ({}, {})), params), 'FW_E')
            modes[mode] = {}
            for arm in ARMS:
                seq = protocol['candidate_bank'].get(arm, {'green': [], 'vsl': []})
                def command(t):
                    i = int((t-start)//150)
                    return ({'RM_C10490': seq['green'][i]} if seq['green'] else {},
                            {d: seq['vsl'][i] for d in protocol.get('dsd_ids', [59,60,61,62])} if seq['vsl'] else {})
                pred = e.simulate(model, window(start, command), params)
                old = e.load(HERE/f'port_origin_split_qualification_v2/prediction_{seed}_{arm}.json')
                if mode == 'reference':
                    assert json.loads(json.dumps(pred)) == old
                if args.inventory and mode=='configured_ratio':
                    assert json.loads(json.dumps(pred))==e.load(HERE/f'configured_exit_ratio_v1/prediction_{seed}_{mode}_{arm}.json')
                for key in ('cells', 'flows'):
                    assert [r for r in pred[key] if r['road']=='FW_W'] == [r for r in old[key] if r['road']=='FW_W']
                for row in pred['ports']:
                    assert abs(row['conservation_residual_veh']) < 1e-7
                road=next(r for r in pred['diagnostics']['roads'] if r['road']=='FW_E')
                assert road['continuity_residual_max_veh']<1e-7
                assert road['lane_group_continuity_residual_max_veh']<1e-7
                if mode.startswith('upstream_'):
                    assert road['first_exit_inventory']['max_residual_veh']<1e-7
                modes[mode][arm] = parts(pred)
                e.save(out/f'prediction_{seed}_{mode}_{arm}.json', pred)
            modes[mode]['deltas'] = {a: {k: v-modes[mode]['none'][k] for k,v in modes[mode][a].items()} for a in ARMS[1:]}
            for d in modes[mode]['deltas'].values():
                d['total'] = sum(d.values())
            print(seed, mode, {a: round(d['total'],6) for a,d in modes[mode]['deltas'].items()}, flush=True)
        results[str(seed)] = {'modes': modes, 'state_guards': guards,
            'within_ten_percent': {mode: {t: row['objective'] <= 1.1*guards['reference'][t]['objective'] for t,row in guards[mode].items()} for mode in guards if mode!='reference'}}
        e.save(out/f'result_s{seed}.json', results[str(seed)])
    for path, pin in pins.items():
        assert hashlib.sha256((e.ROOT/path).read_bytes()).hexdigest() == pin
    e.save(out/'result.json', {'status': 'CAUSAL_DIAGNOSTIC_NOT_ADOPTED', 'configured_ratio': ratio,
        'interpretation': 'Known desired routing before the first off-ramp; not a ratio fitted to blocked exit counts.',
        'results': results, 'pins': pins, 'future_traffic_input': False, 'native_runs_started': 0})


if __name__ == '__main__':
    main()
