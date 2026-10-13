"""One past-supported SC101 capacity candidate, two actual450s command sequences.

Fresh canonical initialization; no optimization, fitting, native run or future input.
"""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import copy, gzip, hashlib, importlib.util, json, pickle, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
H = HERE.parent.parent
PREV = HERE.parent / 'matched280/authority'
OUT = HERE / 'forecast2400'
TUNING = HERE.parent / 'flow279/config_10686_free.json'
SOURCE = Path('D:/VISSIM_runs/20261007_goal8_prevention_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29')
read = lambda p: json.loads(Path(p).read_bytes())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8')


def main():
    assert not OUT.exists(), 'Preserve previous attempts; no automatic retry'
    assert not any((p / 'STOP').exists() for p in (ROOT, HERE, HERE.parent, H))
    old = read(PREV / 'summary.json')
    assert all(sha(p) == digest for p, digest in old['source_pins'].items())
    pins = dict(old['source_pins'])
    for p in (Path(__file__), HERE / 'audit.py', HERE / 'audit.json', PREV / 'initial.pickle', PREV / 'summary.json'):
        pins[str(p)] = sha(p)
    sys.path[:0] = [str(HERE), str(ROOT), str(ROOT / 'vendor/NumSim-mine')]
    import audit as candidate
    sys.argv = ['verify.py', '--at', '2400', '--out', str(OUT), '--no-prediction', '--cold-prices',
                '--tuning', str(TUNING), '--decisions', str(SOURCE)]
    loader = importlib.util.spec_from_file_location('head281_verifier', H.parent / 'urban260/verify.py')
    verifier = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(verifier)
    from evaluation.controllers import vissim_stackelberg_adapter as adapter, sdmpc_pfo, sdmpc_sequence as seq
    from evaluation.controllers import physical_ramp_branches as ramps, signal_actuation_contract as signals
    from evaluation.controllers import area_leader_objective as constraints
    from evaluation.controllers.control_area_objective import get_ledger
    from evaluation.controllers.area_runtime import model_inventory
    from src.controllers import rollout_endpoint as endpoint
    from src.models.state import ControlAction
    original_main = adapter.main

    def wrapped_main():
        captured = {}
        bound, forecast = ramps.configure_operating_bounds, adapter.demand_from_state
        def capture_bound(state, cfg, reference):
            captured.update(state=state, cfg=cfg)
            return bound(state, cfg, reference)
        def capture_forecast(*a, **kw):
            result = forecast(*a, **kw)
            captured['forecast'] = result
            return result
        ramps.configure_operating_bounds = capture_bound
        adapter.demand_from_state = capture_forecast

        def run(reference, coord, policy, options, evaluate, derivative, quantities, check_budget, emit):
            state, cfg = captured['state'], captured['cfg']
            old_cfg, old_state, old_forecast = pickle.loads((PREV / 'initial.pickle').read_bytes())
            assert state.time_sec == 2400 and cfg.simulation.T_f_sec == 5 and cfg.simulation.T_u_sec == 10
            initial_stock = copy.deepcopy(get_ledger(state).stocks)
            assert initial_stock == get_ledger(old_state).stocks
            assert cfg.network.urban_movements == old_cfg.network.urban_movements
            assert cfg.network.movement_capacity_by_movement_veh_h == old_cfg.network.movement_capacity_by_movement_veh_h
            assert pickle.dumps(captured['forecast'], protocol=5) == pickle.dumps(old_forecast, protocol=5)
            application = candidate.install(cfg)
            save('application.json', application)
            (OUT / 'initial.pickle').write_bytes(pickle.dumps((cfg, state, captured['forecast']), protocol=5))
            results = {}
            for arm in ('hold', 'selected'):
                blocks = []
                for at in (2400, 2550, 2700):
                    path = H / 'selection2400_discrete' / arm / f'action_{at:06}.json'
                    pins[str(path)] = sha(path)
                    command = seq.first_action(adapter.control_from_json(path, cfg, ControlAction))
                    signals.validate_writer(command, cfg, adapter.load_signal_group_actuation_plan(), 'experiment')
                    blocks.append(command)
                action = seq.pack(blocks)
                started = time.perf_counter()
                with seq.prediction_scope(action, cfg, 2400, 3) as visits:
                    point = endpoint.evaluate_price_point(state, action, copy.deepcopy(captured['forecast'][:3]), (),
                        endpoint.ObjectiveSpec(cfg, depth_override=3, box_walk=False, score_mode='raw'), capture_response=True)
                wall = time.perf_counter() - started
                assert not point.aborted and len(point.states) == 3 and visits == [0, 1, 2]
                response = point.control_area_response
                assert response['model_constraint_coverage']['complete'] and response['conditional_model_feasibility_witness']
                exceed = max((r['exceedance_veh'] for r in response['resource_allocations']), default=0.)
                assert exceed < 1e-7
                stocks = []
                for current in (state, *point.states):
                    ledger = get_ledger(current)
                    ledger.assert_stocks(model_inventory(current, cfg))
                    stocks.append(dict(time_sec=current.time_sec, stocks=ledger.stocks))
                assert get_ledger(state).stocks == initial_stock
                save(arm + '.stocks.json', stocks)
                (OUT / (arm + '.response.json.gz')).write_bytes(gzip.compress(json.dumps(response, allow_nan=False).encode('utf8')))
                costs = {}
                for row in response['residence']:
                    for key, value in row['inside_veh'].items():
                        costs[key] = costs.get(key, 0.) + value * row['dt_h']
                assert abs(sum(costs.values()) - point.ttt) < 1e-7
                follower = adapter._PHASE_VECTOR_FOLLOWER['ref']
                shared = constraints.shared_urban_quantities(follower, response, start_sec=2400, horizon_steps=3)
                feasibility = constraints.shared_quantity_constraints(follower, action, shared, start_sec=2400, horizon_steps=3,
                    np_mode='cap', target_np_veh=action.N_P_star, np_tolerance_veh=options['shared_tolerance'],
                    nuf_mode='cap', target_nuf_veh_h=action.N_UF_star, nuf_tolerance_veh_h=options['shared_tolerance'])
                results[arm] = dict(omega_ttt_veh_h=point.ttt, costs_by_stock=costs, shared_constraints=feasibility,
                    predicted_merge=point.control_area['predicted_ramp_merge'], resource_max_exceedance=exceed,
                    writer_three_blocks=True, conservation_states=4, wall_sec=wall)
                save(arm + '.json', results[arm])
                print('CANDIDATE', arm, point.ttt, wall, flush=True)
            assert all(sha(p) == digest for p, digest in pins.items())
            save('summary.json', dict(status='complete', start_sec=2400, end_sec=2850,
                forecasts=2, optimizer_calls=0, native_runs=0, fits=0, future_observation_inputs=False,
                application=application, source_pins=pins, results=results))
            raise verifier.Done()
        sdmpc_pfo.solve = run
        return original_main()
    adapter.main = wrapped_main
    verifier.main()


if __name__ == '__main__':
    main()
