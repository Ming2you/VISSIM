"""Frozen331 model transfer to seed47; two already executed native RM sequences.

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
I = ROOT / 'diagnostics/sdmpc_n31_20260924/integration_20260926'
COMMANDS = I / 'native_rm_observation2700_writerfix_v3'
OUT = HERE / 'forecast2700_v2'
TUNING = HERE / 'config.json'
SOURCE = Path('D:/VISSIM_runs/20260928_rm_observation2700_s47_v3/hold/decisions_sdmpc31_g_2700_hold_s47')
read = lambda p: json.loads(Path(p).read_bytes())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf8')


def main():
    assert not OUT.exists(), 'Preserve previous attempts; no automatic retry'
    assert not any((p / 'STOP').exists() for p in (ROOT, HERE, HERE.parent, H))
    old = read(HERE / 'plan.json')
    assert all(sha(p) == digest for p, digest in old['source_pins'].items())
    pins = dict(old['source_pins'])
    for p in (Path(__file__), HERE / 'plan.json', COMMANDS / 'protocol.json', COMMANDS / 'analysis/summary.json'):
        pins[str(p)] = sha(p)
    sys.path[:0] = [str(HERE), str(ROOT), str(ROOT / 'vendor/NumSim-mine')]
    sys.argv = ['verify.py', '--at', '2700', '--out', str(OUT), '--no-prediction', '--cold-prices',
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
        # The native fixed-command run records raw obs150, not online derived files.
        # Reuse the existing verified native replay initializer; never write native files.
        from diagnostics.sdmpc_n31_20260924.integration_20260926 import probe_selected_arrival_path as probe
        from evaluation.controllers import obs150_contract as oc
        receipt = probe.prepare_fixed_replay_history(COMMANDS / 'analysis/summary.json', SOURCE, TUNING, OUT)
        derived = Path(receipt['derived_directory'])
        history_head, history_vsl = probe.replay_head_history, probe.replay_vsl_history
        probe.replay_head_history = lambda *a, **kw: history_head(*a, **dict(kw, derived_directory=derived))
        probe.replay_vsl_history = lambda *a, **kw: history_vsl(*a, **dict(kw, derived_directory=derived, compare_online=False))
        def readonly(raw, document):
            target = derived / f"derived_{document['sim_sec']:06d}.json"
            assert target.read_bytes() == oc.derived_bytes(document)
            return target
        oc.write_derived = readonly
        previous = probe.bind_fixed_replay_reference(receipt, SOURCE, OUT)
        sys.argv[sys.argv.index('--previous-action-json') + 1] = str(previous)
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
            assert state.time_sec == 2700 and cfg.simulation.T_f_sec == 5 and cfg.simulation.T_u_sec == 10
            from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.validation338.install import apply
            state = apply(cfg, state, SOURCE, save, pins, adapter)
            captured['state'] = state
            for module in tuple(sys.modules.values()):
                filename = getattr(module, '__file__', None)
                if filename and Path(filename).suffix == '.py' and Path(filename).is_relative_to(ROOT):
                    pins[str(Path(filename))] = sha(Path(filename))
            initial_stock = copy.deepcopy(get_ledger(state).stocks)
            native = read(COMMANDS / 'analysis/summary.json')
            assert native['counterfactual_valid'] and native['paired_prefix_exact']
            assert all(x['native_execution_passed'] for x in native['arms'].values())
            from evaluation.controllers.control_area_objective import physical_membership_from_ledger
            tuning = read(TUNING)
            physical = physical_membership_from_ledger(read(ROOT / tuning['control_area_objective']['membership_path']))
            raw = read(SOURCE / 'state_002700.json')
            observed = sum(physical[str(v['link_no'])] for v in raw['vehicle_records']['records'])
            seeded = sum(v['inside'] for v in initial_stock.values())
            assert abs(observed - seeded) < 1e-6, (observed, seeded)
            application = dict(model='frozen331 diagnostic model, FW5/U10; training29 coefficients unchanged on seed47', initial_omega_vehicles=seeded,
                native_omega_initial=observed, native_signals=True, all_vsl_kmh=110,
                old_native_whole_omega_scope_not_comparable=True)
            save('application.json', application)
            (OUT / 'initial.pickle').write_bytes(pickle.dumps((cfg, state, captured['forecast']), protocol=5))
            results = {}
            for arm in ('hold', 'release'):
                blocks = []
                for at in (2700, 2850, 3000):
                    path = COMMANDS / arm / 'commands' / f'action_{at:06}.json'
                    pins[str(path)] = sha(path)
                    command = seq.first_action(adapter.control_from_json(path, cfg, ControlAction))
                    from evaluation.controllers.area_follower_objective import expand_shared_vsl_action
                    segment_vsl = adapter.repo_imports(ROOT / 'vendor/NumSim-mine')[-1]
                    command, _ = expand_shared_vsl_action(command, cfg, segment_vsl_func=segment_vsl)
                    assert all(v == 110 for v in command.vsl.values())
                    signals.validate_writer(command, cfg, adapter.load_signal_group_actuation_plan(), 'experiment')
                    blocks.append(command)
                action = seq.pack(blocks)
                started = time.perf_counter()
                with seq.prediction_scope(action, cfg, 2700, 3) as visits:
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
                shared = constraints.shared_urban_quantities(follower, response, start_sec=2700, horizon_steps=3)
                feasibility = constraints.shared_quantity_constraints(follower, action, shared, start_sec=2700, horizon_steps=3,
                    np_mode='cap', target_np_veh=action.N_P_star, np_tolerance_veh=options['shared_tolerance'],
                    nuf_mode='cap', target_nuf_veh_h=action.N_UF_star, nuf_tolerance_veh_h=options['shared_tolerance'])
                results[arm] = dict(omega_ttt_veh_h=point.ttt, costs_by_stock=costs, shared_constraints=feasibility,
                    predicted_merge=point.control_area['predicted_ramp_merge'], resource_max_exceedance=exceed,
                    writer_three_blocks=True, conservation_states=4, wall_sec=wall)
                save(arm + '.json', results[arm])
                print('VALIDATION', arm, point.ttt, wall, flush=True)
            assert all(sha(p) == digest for p, digest in pins.items())
            save('summary.json', dict(status='complete', start_sec=2700, end_sec=3150,
                forecasts=2, optimizer_calls=0, native_runs=0, fits=0, future_observation_inputs=False,
                application=application, source_pins=pins, results=results))
            raise verifier.Done()
        sdmpc_pfo.solve = run
        return original_main()
    adapter.main = wrapped_main
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.sc12_phase305.candidate import hook
    from diagnostics.repin_v3c3_review_20261001.urban_rm269.aggregate270.validation338.install import frozen_services
    with frozen_services(), hook('source_path_current_physical_speed'):
        verifier.main()


if __name__ == '__main__':
    try:
        main()
    except BaseException as exc:
        if OUT.exists():
            save('failure.json', dict(type=type(exc).__name__, error=str(exc)))
        raise
