"""Frozen direct10484 experiment, using the existing native runner and plant.

The purpose is to separate a directly actuated ramp's response from the
propagated10490 response. No parameter fitting, network editing or qualification.
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.probe import e, H, MODEL, CASES
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.gain_response_20260919.fit_response import parts
from diagnostics.demand_sweep.ramp_dsd_20260916_v2.cohort_dynamics_20260920.rm_attribution import native_ports, model_ports
from diagnostics.fast_fixed_profile import prepare
import argparse
import hashlib
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
SEED = 23
OUT = HERE/'direct10484_s23_v1'
NC = H/'controller_response_s23_v1/none'
BASE = HERE/'native_v1/none_s23'
START, END = 2400, 2850


def select_seed(seed):
    global SEED, OUT, NC, BASE
    if seed not in (23,33):raise ValueError('Only the two exact-prefix baseline recordings are prepared')
    SEED=seed;OUT=HERE/f'direct10484_s{seed}_v1'
    NC=next(row[1] for row in CASES if row[0]==seed)
    BASE=HERE/f'native_v1/none_s{seed}'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def check_pins():
    protocol = e.load(OUT/'protocol.json')
    for name, digest in protocol['pins'].items():
        assert sha(e.ROOT/name) == digest, ('Source changed', name)
    return protocol


def setup():
    OUT.mkdir(exist_ok=False)
    folder = OUT/'rm10484'; folder.mkdir()
    network = BASE/'source/baseline.inpx'
    source_pin = sha(network)
    data = e.ObservationData(NC)
    mapping = e.load(Path(data.geometry['mapping']['path']))
    ramp = next(r for r in mapping['ramp_meters'] if r['connector'] == 10484)
    sc = int(ramp['sc_no'])
    tree = ET.parse(network)
    heads = tree.findall(f"./signalHeads/signalHead[@sg='{sc} 1']")
    assert heads and all(h.get('lane').split()[0] == '10484' for h in heads)
    profile = e.load(BASE/'profile.json')
    profile.update(network_sha256=source_pin, meter_commands=[
        dict(time_s=t, sc_no=sc, green_sec=g)
        for t, g in zip([2400,2550,2700,2850], [8,6,4,4])])
    e.save(folder/'profile.json', profile)
    prepare(network, folder/'profile.json', folder/'prepared')
    assert sha(folder/'prepared/network/baseline.inpx') == sha(BASE/'prepared/network/baseline.inpx')
    files = [Path(__file__), network, BASE/'prepared/network/baseline.inpx',
             folder/'profile.json', folder/'prepared/prepared.json',
             e.ROOT/'diagnostics/fast_fixed_profile.py', e.ROOT/'diagnostics/fast_nc_run.ps1',
             e.ROOT/'diagnostics/fast_nc_runner.vbs', e.ROOT/'diagnostics/fast_fixed_profile_verify.py',
             H/'extract_response.py', H/'evaluate_response.py', e.CAL/'canonical_harness.py',
             e.ROOT/'evaluation/controllers/physical_lane_groups.py',
             MODEL/'config.json', MODEL/'selected_parameters.json', MODEL/'port_profile.json',
             HERE/'port_origin_split_v1/config.json', HERE/'port_travel_fit_v1/selected_parameters.json',
             HERE/f'port_positions_v1/s{SEED}.json', H/f'lane_group_response_20260919/observations_v1/s{SEED}.json',
             HERE/f'rm_boundary_cohorts_v1/s{SEED}_none.json']
    protocol = dict(seed=SEED, start_s=START, end_s=END, run_end_s=3000,
        meter_id='RM_C10484', sc_no=sc, command_times=[2400,2550,2700,2850],
        candidate_bank={'rm10484':dict(green=[8,6,4,4], vsl=[])},
        baseline_run=str(BASE/'run'), baseline_observations=str(NC),
        hypothesis='Direct10484 tests its own actuator/head/merge/wait response separately from indirect10490 effects.',
        scope='FW_E mainline and its four on/four off connectors; not Omega, independent validation or full GNE.',
        unchanged='Exact same prepared network, seed, demand, routing, urban signals, other meters, DSD and1s FZP.',
        expected_discrimination='Separate unchanged physical discharge, head-service error, merge/wait error and downstream mainline response. Do not fit a benefit bonus.',
        trust_region='OFF anchor10 then8,6,4 at150s; RED/GREEN only, existing absolute10s cycle and post-frame writes.',
        parameters_frozen_before_native_run=True, qualified=False,
        pins={str(p.relative_to(e.ROOT)):sha(p) for p in files})
    e.save(OUT/'protocol.json', protocol)
    print('PREPARED', sc, {h.get('lane'):h.get('pos') for h in heads}, flush=True)
    predict()


def predict():
    protocol = check_pins(); data = e.ObservationData(NC)
    lane = e.load(H/f'lane_group_response_20260919/observations_v1/s{SEED}.json')
    origin = e.load(HERE/f'port_positions_v1/s{SEED}.json')
    profile = e.load(MODEL/'port_profile.json')
    results = {}
    for name in ['established', 'open_candidate']:
        config = MODEL/'config.json' if name == 'established' else HERE/'port_origin_split_v1/config.json'
        param_path = MODEL/'selected_parameters.json' if name == 'established' else HERE/'port_travel_fit_v1/selected_parameters.json'
        params = e.load(param_path)['parameters']; model = e.load_base_model(data.geometry, config)
        if name == 'open_candidate':
            original = model._config
            def configured(road, override):
                cfg = original(road, override)
                if road == 'FW_E': cfg.network.terminal_zero_gradient = True
                return cfg
            model._config = configured
        rows = {}
        for arm in ['none', 'rm10484']:
            def command(t):
                return ({'RM_C10484':[8,6,4,4][int((t-START)//150)]} if arm == 'rm10484' else {}, {})
            w = e.window(data, model, START, 'history_forecast', profile, command, port_origin_counts=origin['counts'])
            if model.lane_groups_enabled:
                w['lane_group_dynamics'] = {'FW_E':{**lane['geometry'], **lane['cutoffs'][str(START)],
                    'initial_ramp_origin':origin['counts'][str(START)],
                    'initial_off_eligible':origin['eligible_before_off'][str(START)]}}
            pred = e.simulate(model, w, params)
            for r in pred['diagnostics']['roads']:
                assert r['continuity_residual_max_veh'] < 1e-7 and r['negative_density_count'] == r['jam_density_exceedance_count'] == 0
            e.save(OUT/f'prediction_{name}_{arm}.json', pred)
            rows[arm] = dict(parts=parts(pred), ports=model_ports(pred))
        delta = {k:rows['rm10484']['parts'][k]-rows['none']['parts'][k] for k in rows['none']['parts']}
        delta['total'] = sum(delta.values())
        results[name] = dict(arms=rows, delta=delta)
        print('FROZEN_PREDICTION', name, delta, flush=True)
    check_pins()
    e.save(OUT/'frozen_predictions.json', results)


def review():
    protocol = check_pins(); run = OUT/'rm10484/run'
    receipt = e.load(run/'run.json'); validation = e.load(OUT/'paired_validation.json')
    assert receipt['completed'] and receipt['terminal_sec'] == 3000 and not receipt['owned_native_alive']
    assert validation['passed'] and validation['paired_comparison_end_sec'] == START
    folder = OUT/'observations/rm10484'
    control = e.ObservationData(folder)
    actual = {}; port_results = {}; checks = 0
    for arm, path in [('none', NC), ('rm10484', folder)]:
        ports, n = native_ports(path); checks += n; port_results[arm] = ports
        on = sum(r['ttt_veh_h'] for r in ports.values() if r['kind'] == 'ramp')
        off = sum(r['ttt_veh_h'] for r in ports.values() if r['kind'] == 'offramp')
        if arm == 'none':
            ledger = e.load(HERE/f'rm_boundary_cohorts_v1/s{SEED}_none.json')
            assert not ledger['unexplained_events'] and abs(ledger['residence_identity_residual']) < 1e-7
            main = ledger['ttt_veh_h']-on-off
        else:
            stocks = [r for r in e.rows(path/'component_stocks_1s.csv') if START < int(r['time_s']) <= END]
            assert len(stocks) == 450
            assert abs(sum(int(r['FW_E_on']) for r in stocks)/3600-on) < 1e-7
            assert abs(sum(int(r['FW_E_off']) for r in stocks)/3600-off) < 1e-7
            main = sum(int(r['FW_E_mainline']) for r in stocks)/3600
            for r in stocks:
                t = int(r['time_s'])
                if t%30 == 0: assert int(r['FW_E_mainline']) == sum(x['n_veh'] for x in control.cells[t] if x['road'] == 'FW_E')
        actual[arm] = dict(mainline=main, on=on, off=off, total=main+on+off)
    delta = {k:actual['rm10484'][k]-actual['none'][k] for k in actual['none']}
    windows = {}
    for arm, path in [('none', NC), ('rm10484', folder)]:
        heads = e.rows(path/'head_crossings.csv'); stocks = e.rows(path/'head_stock_1s.csv'); events = e.rows(path/'port_events.csv')
        rows = []
        for start in [2400,2550,2700]:
            selected = [r for r in stocks if int(r['ramp']) == 10484 and start < int(float(r['time_s'])) <= start+150]
            assert len(selected) == 150
            counts = {kind:sum(r['connector']=='10484' and r['kind']==kind and start<float(r['time_s'])<=start+150 for r in events) for kind in ['arrival','departure']}
            rows.append(dict(start_s=start, arrivals=counts['arrival'], merges=counts['departure'],
                head_passes=sum(int(r['ramp'])==10484 and start<float(r['time_s'])<=start+150 for r in heads),
                prehead_ttt_veh_h=sum(int(r['prehead_n']) for r in selected)/3600,
                posthead_ttt_veh_h=sum(int(r['posthead_n']) for r in selected)/3600,
                end_prehead=int(selected[-1]['prehead_n']), end_posthead=int(selected[-1]['posthead_n'])))
        windows[arm] = rows
    component_links = {int(k) for k,v in control.geometry['addresses'].items() if v[0]=='FW_E'}
    component_links.update(int(b['connector']) for b in control.geometry['boundaries'] if b['road']=='FW_E' and b['kind'] in ('ramp','offramp'))
    manifest = e.load(folder/'manifest.json')
    losses = [r for r in manifest['removals'] if START<float(r['time_sec'])<=END and int(r['link']) in component_links]
    forecasts = e.load(OUT/'frozen_predictions.json')
    e.save(OUT/'review.json', dict(qualified=False, scope=protocol['scope'], actual=actual, actual_delta=delta,
        forecasts=forecasts, ports=port_results, windows_150s=windows, native_port_stock_checks=checks,
        component_removals=losses, extraction_exclusions=[r for r in manifest['exclusions'] if START<r['upper_sec']<=END],
        prediction_errors={m:{k:v['delta'][k]-delta[k] for k in delta} for m,v in forecasts.items()},
        native_validation=validation, source_pins_verified=True,
        note='Native1s end-frame stock vs canonical10s mainline/local1s ramp/event off integration. No fitting to this result.'))
    check_pins()
    print('ACTUAL_DELTA', delta, flush=True)
    print('DIRECT10484_WINDOWS', windows, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('phase', choices=['prepare','review'])
    parser.add_argument('--seed',type=int,choices=[23,33],default=23)
    args = parser.parse_args();select_seed(args.seed)
    setup() if args.phase == 'prepare' else review()
