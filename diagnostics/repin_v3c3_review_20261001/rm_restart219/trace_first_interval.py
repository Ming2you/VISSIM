"""One passive native900 replay; endpoint parity precedes ramp diagnosis."""
import copy
import ctypes
import ctypes.wintypes
import gzip
import hashlib
import json
import math
import sys
from pathlib import Path
from unittest.mock import patch
from contextlib import nullcontext

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SPEED_PAIR = '--physical-speed-pair' in sys.argv
NORTH_PAIR = '--north-prior-pair' in sys.argv
PROJECTION_AUDIT = '--north-projection-audit' in sys.argv
ROUTE_REPLAY = '--native-route-replay' in sys.argv
ROUTE_BASELINE = '--baseline' in sys.argv
PAIR = SPEED_PAIR or NORTH_PAIR
assert not (SPEED_PAIR and NORTH_PAIR)
UPSTREAM = '--upstream-response' in sys.argv or PAIR or ROUTE_REPLAY
OUT = HERE / ('native_routes222/baseline_v2' if ROUTE_REPLAY and ROUTE_BASELINE else 'native_routes222/candidate' if ROUTE_REPLAY else 'projection222v2' if PROJECTION_AUDIT else 'north_prior221' if NORTH_PAIR else 'physical_speed220v2' if SPEED_PAIR else 'upstream220v2' if UPSTREAM else 'trace150v3')
TUNING = HERE / ('native_routes222/candidate_config.json' if ROUTE_REPLAY and not ROUTE_BASELINE else 'config.json')
DEC = Path('D:/VISSIM_runs/20261005_rm219_fixed90_s29_9000/sdmpc/decisions_sdmpc31_sdmpc9000_s29')
FROZEN = Path('E:/VISSIM_runtime/20261005_rm219_fixed90/frozen/sdmpc31_26569d54_202610050246')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(name, value):
    raw = json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2).encode('utf-8')
    (OUT / name).write_bytes(gzip.compress(raw) if name.endswith('.gz') else raw)

def compare(actual, expected, path='root'):
    """Check every saved field, with an explicit numerical error list."""
    if isinstance(expected, dict):
        assert actual.keys() == expected.keys(), path
        return [row for k in expected for row in compare(actual[k], expected[k], path+'.'+k)]
    if isinstance(expected, list):
        assert len(actual) == len(expected), path
        return [row for i, (a, b) in enumerate(zip(actual, expected)) for row in compare(a, b, path+f'[{i}]')]
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        return [dict(path=path, actual=actual, expected=expected, error=actual-expected)]
    assert actual == expected, path
    return []

def trace(captured, reference, coord, options, evaluate, selected_path, output, *, parity_required=True, **unused):
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from evaluation.controllers.lane_ramp_runtime import LaneRampRuntime
    from src.models.state import ControlAction
    from src.controllers import rollout_endpoint as endpoint

    state, cfg = captured['state'], captured['cfg']
    assert state.time_sec == 900
    action = adapter.control_from_json(selected_path, cfg, ControlAction)
    native = json.loads(selected_path.read_bytes())['prediction']
    assert native['status'] == 'ok' and native['target_sim_sec'] == 1050
    names = sorted(state.lane_ramp_runtime.buffers)
    assert len(names) == 8
    initial = {r: copy.deepcopy(state.lane_ramp_runtime.buffers[r].snapshot()) for r in names}
    captured_point = []
    evaluate_point = endpoint.evaluate_price_point
    def capture_point(*args, **kwargs):
        kwargs['capture_response'] = True
        point = evaluate_point(*args, **kwargs)
        captured_point.append(point)
        return point
    if UPSTREAM:
        upstream = 'SC1004_W_out'
        incoming = {m:s for m,s in cfg.network.urban_movements.items() if s.get('receiving_link') == upstream}
        origins = {s['origin'] for s in incoming.values() if s['origin'] in cfg.network.urban_link_storage_veh}
        head_contract = getattr(cfg.network, 'head_service_resources', {})
        heads = {k:v for k,v in head_contract.get('resources', {}).items() if set(v['members']).intersection(incoming)}
        save('initial_upstream.json', dict(known_routes=cfg.network.known_legsplit_routes,
            known_cohorts=state.known_legsplit_route_state, incoming_movements=incoming,
            queues={m:state.urban_movement_queue.get(m, 0.) for m in incoming},
            capacities={m:cfg.network.movement_capacity_by_movement_veh_h.get(m) for m in incoming},
            origins={o:dict(stock=cfg.network.urban_link_storage_veh[o]-state.urban_link_storage[o],
                           speed=state.urban_link_speed_kph.get(o),
                           arrivals=state.urban_arrival_buffer.get(o,{}),
                           releases=state.urban_storage_release_buffer.get(o,{})) for o in origins},
            heads={k:dict(spec=v, observation=head_contract['observations'].get(k),
                          installed_pool=head_contract['extra_pool_groups'].get(k)) for k,v in heads.items()}))
    advance, finish = LaneRampRuntime.advance, LaneRampRuntime.finish
    rows, pending = [], {}

    def observed_advance(runtime, *args, **kwargs):
        assert not pending
        before = {r: copy.deepcopy(runtime.buffers[r].snapshot()) for r in names}
        result = advance(runtime, *args, **kwargs)
        for r in names:
            pending[r] = dict(ramp=r, before=before[r], receipt=copy.deepcopy(result[2][r]),
                              after_advance=copy.deepcopy(runtime.buffers[r].snapshot()))
        return result

    def observed_finish(runtime, current):
        assert set(pending) == set(names)
        finish(runtime, current)
        for r in names:
            row = pending.pop(r)
            row['after_finish'] = copy.deepcopy(runtime.buffers[r].snapshot())
            rows.append(row)

    endpoint_scope = patch.object(endpoint, 'evaluate_price_point', capture_point) if UPSTREAM else nullcontext()
    with patch.object(LaneRampRuntime, 'advance', observed_advance), patch.object(LaneRampRuntime, 'finish', observed_finish), endpoint_scope:
        replay = adapter.build_one_step_prediction(state, action, captured['forecast'], cfg, captured['calibration'])
    save('replayed_prediction.json', replay)
    save('receipts.json.gz', rows)
    assert replay['status'] == 'ok', replay
    assert not pending and len(rows) == 150*8
    parity = compare(replay['state_summary'], native['state_summary'])
    parity += compare(replay['terminal_features'], native['terminal_features'], 'terminal_features')
    maximum = max(abs(r['error']) for r in parity)
    save('endpoint_parity.json', dict(maximum_error=maximum, exact=maximum == 0, fields=parity))
    if parity_required:
        assert maximum < 1e-9, ('Native endpoint NOT reproduced; do not interpret flows', maximum)
    else:
        assert (SPEED_PAIR and cfg.network.known_legsplit_routes['physical_travel']['speed_source'] == 'physical_observation'
                or (NORTH_PAIR or ROUTE_REPLAY) and cfg.network.urban_movements['SC1004_N_SC1003_to_W']['beta'] == .75)
    if UPSTREAM:
        assert len(captured_point) == 1
        point = captured_point[0]
        save('response.json.gz', point.control_area_response)
        end = point.states[-1]
        save('end_upstream.json', dict(known_cohorts=end.known_legsplit_route_state,
            queues={m:end.urban_movement_queue.get(m, 0.) for m in incoming},
            origins={o:dict(stock=cfg.network.urban_link_storage_veh[o]-end.urban_link_storage[o],
                           speed=end.urban_link_speed_kph.get(o),arrivals=end.urban_arrival_buffer.get(o,{})) for o in origins}))

    actual = json.loads((HERE/'first_interval_ramps.json').read_bytes())['arms']['current']
    report = {}
    worst = 0.
    for r in names:
        selected = [row for row in rows if row['ramp'] == r]
        assert [x['receipt']['start_sec'] for x in selected] == list(range(900, 1050))
        assert all(x['receipt']['duration_sec'] == 1 for x in selected)
        start, end = initial[r], selected[-1]['after_finish']
        arrivals = math.fsum(x['after_finish']['connector_veh']-x['after_advance']['connector_veh'] for x in selected)
        head = math.fsum(x['receipt']['head_service_veh'] for x in selected)
        merge = math.fsum(x['receipt']['accepted_merge_veh'] for x in selected)
        for i, x in enumerate(selected):
            b, a, f = x['before'], x['after_advance'], x['after_finish']
            m = x['receipt']['accepted_merge_veh']
            h = x['receipt']['head_service_veh']
            incoming = f['connector_veh']-a['connector_veh']
            pre = lambda s: s['upstream_travelling_veh']+s['head_ready_veh']
            post = lambda s: s['downstream_travelling_veh']+s['merge_ready_veh']
            errors = [b['connector_veh']-m-a['connector_veh'],
                      pre(b)+incoming-h-pre(f), post(b)+h-m-post(f)]
            if i:
                errors += [b[k]-selected[i-1]['after_finish'][k] for k in ('connector_veh','cumulative_admitted_veh','cumulative_head_service_veh','cumulative_merge_veh')]
            worst = max(worst, *(abs(v) for v in errors))
            assert incoming >= -1e-9
        assert abs(start['connector_veh']-actual[r]['initial_veh']) < 1e-9
        assert abs(pre(start)-actual[r]['prehead_initial_veh']) < 1e-9
        assert abs(post(start)-actual[r]['posthead_initial_veh']) < 1e-9
        assert abs(arrivals-(end['cumulative_admitted_veh']-start['cumulative_admitted_veh'])) < 1e-8
        assert abs(head-(end['cumulative_head_service_veh']-start['cumulative_head_service_veh'])) < 1e-8
        assert abs(merge-(end['cumulative_merge_veh']-start['cumulative_merge_veh'])) < 1e-8
        obs = actual[r]
        error = dict(arrival=arrivals-obs['arrivals_at_boundary'],
                     head=head-obs['head_passages'], merge=merge-obs['merge_from_inventory_balance'],
                     end=end['connector_veh']-obs['end_veh'],
                     prehead=pre(end)-obs['prehead_end_veh'], posthead=post(end)-obs['posthead_end_veh'])
        assert abs(error['end']-(error['arrival']-error['merge'])) < 1e-8
        assert abs(error['prehead']-(error['arrival']-error['head'])) < 1e-8
        assert abs(error['posthead']-(error['head']-error['merge'])) < 1e-8
        report[r] = dict(initial=start, end=end, predicted=dict(arrivals=arrivals, head=head, merge=merge,
                            prehead_end=pre(end), posthead_end=post(end)), native=obs, errors=error)
    assert worst < 1e-8
    save('summary.json', dict(status='PASS', window=[900,1050], endpoint_exact=maximum==0,
        endpoint_maximum_error=maximum, max_mass_error=worst, ramps=report,
        predictions150=1, optimizer=0, fits=0, VISSIM=0, FZP=0, future_observations_used=False,
        scope='One autonomous actual-command replay. Native merge is inventory-derived; error accounting is not a causal decomposition or capacity calibration.'))
    print(json.dumps(dict(status='PASS', exact=maximum==0, seconds=replay['wall_sec'],
        ramps={r: dict(predicted=x['predicted'], errors=x['errors']) for r,x in report.items()})), flush=True)

def main():
    global OUT
    OUT.mkdir(exist_ok=False)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetCurrentProcess.restype = ctypes.wintypes.HANDLE
    kernel.SetPriorityClass.argtypes = [ctypes.wintypes.HANDLE, ctypes.wintypes.DWORD]
    assert kernel.SetPriorityClass(kernel.GetCurrentProcess(), 0x4000)
    prior = json.loads((HERE.parent/'rm_flow218/protocol.json').read_bytes())
    paths = set(prior['source_sha256']) | {'evaluation/controllers/runtime_setup.py', 'evaluation/controllers/lane_plant_runtime.py', 'evaluation/controllers/sdmpc.py'}
    pins = {p: sha(ROOT/p) for p in sorted(paths)}
    changed = sorted({Path(p).as_posix() for p,value in pins.items() if sha(FROZEN/p)!=value})
    expected_changed = ['evaluation/controllers/observation_projection.py','evaluation/controllers/route_choice_corridor.py','evaluation/controllers/runtime_setup.py'] if ROUTE_REPLAY else ['evaluation/controllers/route_choice_corridor.py'] if PAIR or PROJECTION_AUDIT else []
    assert changed == expected_changed, changed
    if PAIR:
        assert sha(HERE/'upstream220v2/route_choice_corridor.before.py.txt') == sha(FROZEN/'evaluation/controllers/route_choice_corridor.py')
    stop = prior['STOP']
    assert sha(Path(stop['path'])) == stop['sha256']
    inputs = [HERE/'config.json', TUNING, HERE/'first_interval_ramps.json', DEC/'action_000900.json', DEC/'state_000900.json', DEC/'action_000750.json']
    if ROUTE_REPLAY:
        inputs += [HERE/'native_routes222'/name for name in ('contract.json','physical_routes.json')]
    input_pins = {str(p):sha(p) for p in inputs}
    save('protocol.json', dict(budget=dict(predictions150=0 if PROJECTION_AUDIT else 2 if PAIR else 1, fit=0, optimization=0, native=0, FZP=0),
         priority='BelowNormal', source_sha256=pins, native_frozen=str(FROZEN), inputs=input_pins,
         STOP=stop, driver_sha256=sha(Path(__file__)), changed_from_frozen=changed,
         candidate_change='Known W_out future physical travel speed from unscaled observation' if SPEED_PAIR else
                          'One native1125 conditional future prior; common projected initial inventory unchanged' if NORTH_PAIR else None))
    # Reuse check_first.py's actual first-control initialization. Warmup has
    # native signals and intentionally no applied COM-action receipt, so the
    # later-state probe's previous-applied requirement is inapplicable here.
    from evaluation.controllers import vissim_stackelberg_adapter as adapter, obs150_contract as oc
    from evaluation.controllers import runtime_setup, sdmpc_pfo
    captured = {}
    configure, forecast = runtime_setup.configure_runtime, adapter.demand_from_state
    class Ready(BaseException):
        pass
    def capture_runtime(*args, **kwargs):
        result = configure(*args, **kwargs)
        captured['state'], captured['cfg'] = result[0], args[1]
        captured['calibration'] = args[7]
        if PROJECTION_AUDIT or ROUTE_REPLAY:
            captured['detectors'], captured['metadata'] = result[1:]
        return result
    def capture_forecast(*args, **kwargs):
        result = forecast(*args, **kwargs)
        captured['forecast'] = result
        return result
    def read_only(raw, derived):
        path = oc.resolve(raw[oc.RAW_STATE_KEY], oc.derived_path(derived['sim_sec']))
        assert path.read_bytes() == oc.derived_bytes(derived)
        return path
    def at_pfo(reference, coord, policy, options, evaluate, *args, **kwargs):
        global OUT
        if ROUTE_REPLAY:
            import pickle
            initial = pickle.dumps(captured['state'])
            save('runtime_metadata.json', captured['metadata'])
            state=captured['state'];origin='SC1003_to_SC1004'
            save('route_initial.json', dict(queue={m:n for m,n in state.urban_movement_queue.items() if m.startswith('SC1004_N_SC1003')},
                tags=getattr(state,'gate_initial_route_tags',{}).get(origin,{}),
                arrivals=state.urban_arrival_buffer[origin],releases=state.urban_storage_release_buffer[origin],
                source_stock=captured['cfg'].network.urban_link_storage_veh[origin]-state.urban_link_storage[origin],
                physical_support=state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']['46']))
            trace(captured, reference, coord, options, evaluate, DEC/'action_000900.json', OUT, parity_required=ROUTE_BASELINE)
            assert pickle.dumps(captured['state']) == initial
            raise Ready()
        if PROJECTION_AUDIT:
            state, cfg = captured['state'], captured['cfg']
            origin = 'SC1003_to_SC1004'
            movements = {m:s for m,s in cfg.network.urban_movements.items() if s.get('origin')==origin}
            support = state.local_observation_summary['projection_diagnostics']['physical_stock_assignment_by_link']
            detector = captured['detectors']
            save('projection.json', dict(movements=movements,
                queue={m:state.urban_movement_queue.get(m) for m in movements},
                source_stock=cfg.network.urban_link_storage_veh[origin]-state.urban_link_storage[origin],
                arrivals=state.urban_arrival_buffer.get(origin),
                releases=state.urban_storage_release_buffer.get(origin),
                supports={k:v for k,v in support.items() if 'storage:'+origin in v or any('movement:'+m in v for m in movements)},
                detectors={k:detector.get(k) for k in ('link_to_origins','link_to_movements')},
                metadata=captured['metadata']))
            raise Ready()
        if PAIR:
            root_out = OUT
            cfg = captured['cfg']
            import pickle
            prior_override = {}
            if NORTH_PAIR:
                import xml.etree.ElementTree as ET
                from evaluation.controllers.offramp_routing import _weight
                raw_net = Path(provenance['files']['network']['path']).read_bytes()
                assert hashlib.sha256(raw_net).hexdigest() == provenance['files']['network']['sha256']
                tree = ET.fromstring(raw_net)
                intervals=tree.findall(".//timeIntervalSet[@no='VEHICLEROUTESTATIC']/timeInts/timeInterval")
                assert [float(x.get('start')) for x in intervals] == [0.]
                dec = tree.find("./vehicleRoutingDecisionsStatic/vehicleRoutingDecisionStatic[@no='1125']")
                assert dec.get('link')=='46' and dec.get('allVehTypes')=='true' and dec.get('routeChoiceMeth')=='STATIC'
                expected = {'1':('W','10625','68','SC1004_W_out'),
                            '2':('S','10626','67','SC1004_S_out'),
                            '3':('E_SC1005','10627','56','SC1004_E_choice')}
                routes = dec.findall('./vehRoutSta/vehicleRouteStatic')
                assert {r.get('no') for r in routes} == set(expected)
                evidence = {}
                for row in routes:
                    suffix, connector, link, receiver = expected[row.get('no')]
                    key = 'SC1004_N_SC1003_to_'+suffix
                    path = ['46']+[x.get('key') for x in row.findall('./linkSeq/intObjectRef')]+[row.get('destLink')]
                    assert not row.get('formula') and path == ['46',connector,link]
                    spec = cfg.network.urban_movements[key]
                    assert spec['origin']=='SC1003_to_SC1004' and spec['receiving_link']==receiver
                    prior_override[key] = _weight(row)
                    evidence[key] = dict(path=path, weight=_weight(row), old_beta=spec['beta'])
                total = math.fsum(prior_override.values())
                prior_override = {k:v/total for k,v in prior_override.items()}
                same_origin = {k:v for k,v in cfg.network.urban_movements.items() if v.get('origin')=='SC1003_to_SC1004'}
                assert all(v['beta']==0. for k,v in same_origin.items() if k not in prior_override)
                save('north_prior.json', dict(network_sha256=hashlib.sha256(raw_net).hexdigest(), evidence=evidence,
                    replacement_beta=prior_override, scope='Diagnostic response only; generic initial transit is not individual observed route preservation.'))
            initial = pickle.dumps(captured['state'])
            for name in ('baseline','native_prior' if NORTH_PAIR else 'physical_speed'):
                OUT = root_out/name; OUT.mkdir()
                if name == 'physical_speed':
                    cfg.network.known_legsplit_routes['physical_travel']['speed_source'] = 'physical_observation'
                elif name == 'native_prior':
                    for key,value in prior_override.items():cfg.network.urban_movements[key]['beta'] = value
                trace(captured, reference, coord, options, evaluate, DEC/'action_000900.json', OUT,
                      parity_required=name=='baseline')
                assert pickle.dumps(captured['state']) == initial, 'Forecast mutated its initial state'
            OUT = root_out
        else:
            trace(captured, reference, coord, options, evaluate, DEC/'action_000900.json', OUT)
        raise Ready()
    provenance = json.loads(next(DEC.parent.glob('run_provenance_*.json')).read_bytes())
    assert sha(HERE/'config.json') == provenance['files']['tuning']['sha256']
    assert (DEC/'action_000900.json.applied').is_file()
    sys.argv = [str(Path(adapter.__file__)), '--state-json', str(DEC/'state_000900.json'),
        '--previous-action-json', str(DEC/'action_000750.json'),
        '--out-action-json', str(OUT/'unused_action.json'), '--out-action-csv', str(OUT/'unused_action.csv'),
        '--mapping-json', str(ROOT/'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json'),
        '--calibration-json', str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'),
        '--tuning-json', str(TUNING), '--controller', 'wu-link']
    with patch.object(runtime_setup, 'configure_runtime', capture_runtime), patch.object(adapter, 'demand_from_state', capture_forecast), patch.object(sdmpc_pfo, 'solve', at_pfo), patch.object(oc, 'write_derived', read_only):
        try:
            adapter.main()
        except Ready:
            pass
        else:
            raise AssertionError('Expected first-control PFO entry was not reached')
    assert all(sha(ROOT/p)==value for p,value in pins.items())
    assert all(sha(Path(p))==value for p,value in input_pins.items())
    assert sha(Path(stop['path'])) == stop['sha256']
    save('completion.json', dict(status='COMPLETE', source_and_inputs_unchanged=True, STOP_unchanged=True))

if __name__ == '__main__':
    main()
