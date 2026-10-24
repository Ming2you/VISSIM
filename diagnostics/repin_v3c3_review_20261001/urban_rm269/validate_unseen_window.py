"""One frozen-parameter450s replay in a previously unused native window.

Executed controls are given, not future traffic. This is response validation,
not a same-initial-state counterfactual or evidence of native controller gain.
"""
import os
for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[name] = '1'
import copy
from collections import defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PAIR = HERE/'runtime_pair2400_numericfix'
OUT = HERE/'unseen_window3300'
F = Path('E:/VISSIM_runs/20261008_coupling268_window_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29')
TUNING = HERE/'isolated10681/canonical_port/config.json'
AT = 3300
read = lambda p: json.loads(Path(p).read_bytes())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(name, value):
    (OUT/name).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n', encoding='utf8')


def main():
    import argparse
    global OUT, TUNING
    parser = argparse.ArgumentParser()
    parser.add_argument('--aggregate10', action='store_true', help='One opt-in aggregate270 response; retain the old response as baseline')
    parser.add_argument('--lane-offer', action='store_true', help='Use the pinned independently receiving lane revision')
    parser.add_argument('--route-interval', action='store_true', help='One fixed-route10s aggregate response, reusing the closed3300 window')
    parser.add_argument('--freeway5', action='store_true', help='One coupled freeway5s response; urban physical update remains1s')
    parser.add_argument('--urban10', action='store_true', help='One source-pinned freeway5/urban10 response, no parameter refit')
    args = parser.parse_args()
    if args.lane_offer or args.route_interval or args.freeway5 or args.urban10:
        args.aggregate10 = True
    if sum((args.route_interval, args.lane_offer, args.freeway5, args.urban10)) > 1:
        raise ValueError('Select one saved revision')
    pins = {}
    if args.aggregate10:
        a = HERE/'aggregate270'
        OUT, TUNING = a/'unseen3300_dt10', a/'config_dt10.json'
        plan = read(a/'plan.json')
        assert read(a/'clock_comparison.json')['status'] == 'one_state_clock_direction_and_feasibility_passed'
        for path, digest in plan['coupled_bridge_source_sha256'].items():
            source = ROOT/path if path.startswith('evaluation') else a/path
            if not (args.lane_offer or args.route_interval or args.freeway5 or args.urban10):
                assert sha(source) == digest, source
                pins[str(source)] = digest
        if args.lane_offer:
            revision = read(a/'lane_offer_plan.json')
            OUT = a/'unseen3300_lane_offer'
            assert revision['status'] == 'prepared' and revision['new_predictions_max'] == 1
            for path,digest in revision['source_pins'].items():
                assert sha(path) == digest, path
                pins[path] = digest
        if args.route_interval:
            revision = read(a/'route_interval/plan.json')
            assert revision['status'] == 'completed_single_state_response_and_ad_reviewed'
            assert read(a/'route_interval/ad_review.json')['source_pins_pass']
            OUT, TUNING = a/'unseen3300_routes', a/'config_dt10_routes.json'
            for path, digest in revision['source_pins'].items():
                assert sha(path) == digest, path
                pins[path] = digest
        if args.freeway5:
            m = a/'multirate271'
            revision = read(m/'plan.json')
            assert revision['status'] == 'single_state_fw5_coupled_scalar_ad_pass'
            OUT, TUNING = m/'unseen3300_fw5_joint2', m/'config_fw5_urban1.json'
            for path, digest in revision['source_pins'].items():
                source = ROOT/path
                assert sha(source) == digest, source
                pins[str(source)] = digest
            assert not (m/'STOP').exists()
            for source in (ROOT/'evaluation/controllers').glob('*.py'):
                pins[str(source)] = sha(source)
        if args.urban10:
            revision = read(a/'urban_clock277/plan.json')
            assert revision['status'] == 'fw5_urban10_one_state_decision_verified'
            OUT, TUNING = a/'validation278/unseen3300_fw5_urban10', a/'urban_clock277/config_fw5_urban10.json'
            for path, digest in revision['source_pins'].items():
                source = ROOT/path
                assert sha(source) == digest, source
                pins[str(source)] = digest
            assert not (a/'urban_clock277/STOP').exists() and not (OUT.parent/'STOP').exists()
            for source in (ROOT/'evaluation/controllers').glob('*.py'):
                pins[str(source)] = sha(source)
        assert not (a/'STOP').exists()
    assert not OUT.exists(), 'Preserve prior validation attempt'
    if not args.aggregate10:
        pair = read(PAIR/'plan.json')
        assert pair['status'] in ('both_complete_equivalence_pending', 'complete_equivalent')
        for mode in ('cache_off', 'cache_on'):
            assert read(PAIR/(mode+'.execution.json'))['status'] == 'complete_uncompared'
        for path, digest in pair['source_pins'].items():
            assert sha(path) == digest, path
            pins[path] = digest
    queue = read('E:/VISSIM_runtime/20261008_coupling268_vsl_three/queue_state.json')
    closed = queue['conditions']['window']
    assert closed['normal_sim_done'] == 8100 and closed['owners_closed'] and closed['native_exit_code'] == 0
    assert not (ROOT/'STOP').exists() and not (HERE/'STOP').exists() and not (PAIR/'STOP').exists()
    pins[str(Path(__file__).resolve())] = sha(__file__)
    pins[str(TUNING)] = sha(TUNING)
    pins[str(HERE.parent/'urban260/verify.py')] = sha(HERE.parent/'urban260/verify.py')
    sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine')]
    sys.argv = ['verify.py', '--at', str(AT), '--out', str(OUT), '--no-prediction',
                '--tuning', str(TUNING), '--decisions', str(F), '--cold-prices']
    loader = importlib.util.spec_from_file_location('unseen_window_verifier', HERE.parent/'urban260/verify.py')
    v = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(v)
    from evaluation.controllers import vissim_stackelberg_adapter as adapter, sdmpc_pfo
    from evaluation.controllers import physical_ramp_branches as ramps, sdmpc_sequence as seq
    from evaluation.controllers import signal_actuation_contract as signals, obs150_contract as oc
    from evaluation.controllers.obs150_observation import check_rule_crosscheck
    from evaluation.controllers.control_area_objective import get_ledger
    from evaluation.controllers.area_runtime import model_inventory
    from src.controllers import rollout_endpoint as endpoint
    from src.models.state import ControlAction
    original_main = adapter.main

    def wrapped_main():
        capture = {}
        bound, forecast = ramps.configure_operating_bounds, adapter.demand_from_state
        def capture_bound(state, cfg, reference):
            capture.update(state=state, cfg=cfg)
            return bound(state, cfg, reference)
        def capture_forecast(*a, **kw):
            result = forecast(*a, **kw)
            capture['forecast'] = result
            return result
        ramps.configure_operating_bounds = capture_bound
        adapter.demand_from_state = capture_forecast

        def audit(reference, coord, policy, options, evaluate, derivative, quantities, check_budget, emit):
            state, cfg = capture['state'], capture['cfg']
            assert state.time_sec == AT and len(capture['forecast']) == 3
            if args.freeway5:
                assert cfg.simulation.T_f_sec == 5 and cfg.simulation.T_u_sec == 1
            if args.urban10:
                assert cfg.simulation.T_f_sec == 5 and cfg.simulation.T_u_sec == 10
                assert cfg.network.multirate_joint_clock_enabled
            assert all(getattr(b, '_causal_receiving_enabled', False)
                       for b in state.lane_ramp_runtime.buffers['RM_C10681']._lane_buffers)
            footprint = read(HERE/'native2400_component_footprint.json')['groups']
            links = {k:set(row['links']) for k,row in footprint.items()}
            links['shared_W_out'].add(10772)
            links['ramp10681'] = {10681}
            keys = {k:set(row['initial_model_stock_keys']) for k,row in footprint.items()}
            keys['approach66'].add('transit:gate:in_SC1004_S')
            keys['ramp10681'] = {'ramp:RM_C10681'}
            blocks, command_pins = [], {}
            for t in (AT, AT+150, AT+300):
                path = F/f'action_{t:06}.json'
                assert path.with_suffix('.json.applied').is_file()
                action = seq.first_action(adapter.control_from_json(path, cfg, ControlAction))
                signals.validate_writer(action, cfg, adapter.load_signal_group_actuation_plan(), 'experiment')
                blocks.append(action)
                command_pins[str(path)] = sha(path)
            action = seq.pack(blocks)
            started = time.perf_counter()
            with seq.prediction_scope(action, cfg, AT, 3) as visits:
                point = endpoint.evaluate_price_point(state, action, copy.deepcopy(capture['forecast']), (),
                    endpoint.ObjectiveSpec(cfg, depth_override=3, box_walk=False, score_mode='raw'), capture_response=True)
            assert not point.aborted and len(point.states) == 3 and visits == [0,1,2]
            response = point.control_area_response
            assert response['model_constraint_coverage']['complete'] and response['conditional_model_feasibility_witness']
            max_excess = max((r['exceedance_veh'] for r in response['resource_allocations']), default=0.)
            assert max_excess < 1e-7
            predicted = []
            aggregate_states = []
            for s in (state, *point.states):
                ledger = get_ledger(s)
                ledger.assert_stocks(model_inventory(s, cfg))
                predicted.append({k:sum(ledger.stocks.get(key, {}).get('inside', 0.) for key in group)
                                  for k,group in keys.items()})
                if args.aggregate10:
                    obj = s.known_legsplit_route_state['aggregate_transport']
                    obj.bins.verify()
                    obj.check_capacity(cfg)
                    aggregate_states.append(dict(time_sec=s.time_sec, stock=obj.stock(), updates=obj.updates,
                        fixed_array_shape=list(obj.bins.future.shape), road68_by_lane={lane:obj.stock('68',lane) for lane in obj.road_lanes},
                        stage_ready_by_lane_turn={str(key):float(obj.bins.waiting[j]) for key,j in obj.bins.index.items()},
                        stage_pending_by_lane_turn={str(key):float(obj.bins.pending[j]) for key,j in obj.bins.index.items()}))
            if args.aggregate10:
                assert aggregate_states[-1]['updates'] == 45
            route_aggregate_states = []
            if args.route_interval or args.freeway5 or args.urban10:
                for s in (state, *point.states):
                    obj = s.route_choice_corridor_state['aggregate_routes']
                    obj.bins.verify()
                    route_aggregate_states.append(dict(time_sec=s.time_sec, updates=obj.updates,
                        classes=len(obj.bins.labels), stock_by_storage={k:float(obj.stock(k)) for k in obj.by_storage}))
                assert route_aggregate_states[-1]['updates'] == 45
            if args.urban10:
                # Physical group budgets, not Omega-only weights. Internal
                # transfers and the temporary ramp staging round trip cancel.
                group_flux = {}
                for label, group in keys.items():
                    incoming, outgoing = defaultdict(float), defaultdict(float)
                    for row in response['transfers']:
                        source_in, target_in = row['source'] in group, row['target'] in group
                        if source_in == target_in:
                            continue
                        table = incoming if target_in else outgoing
                        table[row['route_key']] += float(row['vehicles'])
                    physical = [sum(sum(get_ledger(s).stocks.get(key, {}).values()) for key in group)
                                for s in (state, *point.states)]
                    residual = physical[-1]-physical[0]-sum(incoming.values())+sum(outgoing.values())
                    assert abs(residual) < 1e-6, (label, residual)
                    group_flux[label] = dict(physical_stocks=physical, model_stock_keys=sorted(group),
                        inflow=dict(incoming), outflow=dict(outgoing), conservation_residual_veh=residual)
                save('group_flux.json', group_flux)
            # Forecast is finished before any future traffic is opened.
            observed, native_windows, target_pins = [], [], {}
            previous = None
            for t in (AT, AT+150, AT+300, AT+450):
                path = F/f'state_{t:06}.json'
                raw = read(path)
                target_pins[str(path)] = sha(path)
                assert raw['sim_sec'] == t
                bundle = oc.load_bundle(raw)
                assert bundle.frame_end['complete']
                vehicles = bundle.frame_end['vehicles']
                stocks = {k:sum(row[1] in ids for row in vehicles) for k,ids in links.items()}
                observed.append(stocks)
                if previous is not None:
                    obs = bundle.obs
                    ds,_ = oc.read_detector_csv(obs['detector_config']['path'], obs['detector_config']['sha256'])
                    oc.validate_raw(obs, ds, expected_simres=10)
                    check_rule_crosscheck(obs, ds)
                    crossings = oc.evaluate_boundaries(obs, ds, bundle.frame_end, bundle.frame_start, bundle.err_rows)
                    removed = sum(int(row['link']) == 10681 for row in oc.window_removals(bundle.err_rows, t-150, t))
                    arrival = crossings['ramp_arrival:RM_C10681'].cross
                    merged = previous+arrival-stocks['ramp10681']-removed
                    assert merged >= 0
                    native_windows.append(dict(end=t, arrival=arrival, merge=merged, removed=removed))
                previous = stocks['ramp10681']
            initial_error = {k:predicted[0][k]-observed[0][k] for k in keys}
            changes = {k:dict(native=observed[-1][k]-observed[0][k],
                              predicted=predicted[-1][k]-predicted[0][k]) for k in keys}
            protocol = read(OUT/'protocol.json')
            protocol.update(max_predictions=1, prediction_horizon_sec=450, actual_fixed_predictions=1,
                            future_traffic_used_as_input=False, supplied_actual_command_blocks=3)
            save('protocol.json', protocol)
            save('response_validation.json', dict(status='one_frozen_parameter_response_complete',
                times=[AT,AT+150,AT+300,AT+450], predicted_stocks=predicted, native_stocks=observed,
                initial_group_errors=initial_error, stock_changes=changes, native_windows=native_windows,
                predicted_merge10681=point.control_area['predicted_ramp_merge']['accepted_vehicles_by_ramp']['RM_C10681'],
                predicted_arrival10681=sum(r['vehicles'] for r in response['transfers']
                    if r['target']=='ramp:RM_C10681' and not r['source'].startswith('transit:exchange:ramp:')),
                predicted_omega_ttt_veh_h=point.ttt, resource_max_exceedance_veh=max_excess,
                wall_sec=time.perf_counter()-started, command_pins=command_pins, target_pins=target_pins,
                tuning_sha256=sha(TUNING), source_pins=pins, aggregate_states=aggregate_states,
                route_aggregate_states=route_aggregate_states,
                clocks=dict(freeway_sec=cfg.simulation.T_f_sec, urban_sec=cfg.simulation.T_u_sec),
                new_fits=0, new_native_runs=0, optimizer_calls=0,
                limits=['Actual controls supplied: response validation, not native causal RM gain or autonomous SDMPC choice.',
                        'Same seed29, distinct previously unused3300 native state; not independent-seed evidence.',
                        'No native TTT estimate from sparse snapshots. Physical stock is not stopped queue length.',
                        'Applied command markers and closed-run receipt reused; no new LDP actuation audit or FZP scan.']))
            for path,digest in pins.items():
                assert sha(path) == digest, path
            print('UNSEEN_RESPONSE_COMPLETE', changes, flush=True)
            raise v.Done()
        sdmpc_pfo.solve = audit
        return original_main()
    adapter.main = wrapped_main
    v.main()


if __name__ == '__main__':
    main()
