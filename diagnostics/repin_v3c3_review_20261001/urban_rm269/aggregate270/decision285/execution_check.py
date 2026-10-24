"""Two scalar execution-model responses for the one completed current SDMPC choice.

Fresh canonical initialization; no optimization, fitting, native run or future input.
"""
import os
for key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
import copy, gzip, hashlib, importlib.util, json, pickle, re, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
H = HERE.parent.parent
PREV = HERE.parent / 'matched280/authority'
OUT = HERE / 'execution3300'
TUNING = HERE.parent / 'flow279/config_10686_free.json'
SOURCE = Path(json.loads((HERE/'full_decision_execution.json').read_bytes())['decisions'])
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
    for p in (Path(__file__), HERE/'full_decision_execution.json', HERE/'full3300_current/unused.json', HERE/'full3300_current/reference.json', HERE/'full3300_current/state.json', HERE/'full3300_current/network.json', SOURCE/'state_003300.json', SOURCE/'action_003150.json'):
        pins[str(p)] = sha(p)
    sys.path[:0] = [str(HERE), str(ROOT), str(ROOT / 'vendor/NumSim-mine')]
    sys.argv = ['verify.py', '--at', '3300', '--out', str(OUT), '--no-prediction',
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
            assert state.time_sec == 3300 and cfg.simulation.T_f_sec == 5 and cfg.simulation.T_u_sec == 10
            initial_stock = copy.deepcopy(get_ledger(state).stocks)
            def clean(x):
                if isinstance(x,dict): return {str(k):clean(v) for k,v in x.items()}
                if isinstance(x,(tuple,list)): return [clean(v) for v in x]
                if isinstance(x,(str,int,float,bool)) or x is None: return x
                if hasattr(x,'tolist'): return x.tolist()
                return repr(x)[:600]
            state_now=clean(vars(state)); net_now=clean(vars(cfg.network))
            save('state.json',state_now)
            request_path=HERE.parent/'flow279/candidate3300/initial.pickle'
            old_request=pickle.loads(request_path.read_bytes())
            from evaluation.controllers.sdmpc_tangent_worker import state_error
            exact_state_error=state_error(state,old_request[1])
            assert exact_state_error==0,exact_state_error
            pins[str(request_path)]=sha(request_path)
            state_saved=read(HERE/'full3300_current/state.json')
            net_saved=read(HERE/'full3300_current/network.json')
            def strip_object_addresses(x):
                if isinstance(x,dict): return {k:strip_object_addresses(v) for k,v in x.items()}
                if isinstance(x,list): return [strip_object_addresses(v) for v in x]
                if isinstance(x,str) and x.startswith('<evaluation.controllers.') and ' object at 0x' in x:
                    return re.sub(r' object at 0x[0-9A-Fa-f]+>', ' object>',x)
                return x
            state_now=strip_object_addresses(state_now);state_saved=strip_object_addresses(state_saved)
            init_compare={'exact_saved_physical_state_max_error':exact_state_error,'runtime_addresses_excluded_from_text_comparison':True,'state_equal':state_now==state_saved,'network_equal':net_now==net_saved,
                'state_differences':[k for k in set(state_now)|set(state_saved) if state_now.get(k)!=state_saved.get(k)],
                'network_differences':[k for k in set(net_now)|set(net_saved) if net_now.get(k)!=net_saved.get(k)],
                'source':str(SOURCE),'reason':'Canonical source and actual historical action are identical to completed3300 full selection.'}
            save('initial_comparison.json',init_compare)
            assert init_compare['state_equal'] and init_compare['network_equal'],init_compare
            initial_error=0
            proof = read(HERE/'full_selection_review.json')
            assert proof['physical_and_shared_feasible']
            old_reference = read(HERE/'full3300_current/reference.json')
            fields = ('green_times','offsets','vsl','ramp_metering','inflow_outflow_allocation')
            ref_compare = {k: {'equal': getattr(reference,k) == old_reference[k], 'fresh': getattr(reference,k), 'saved': old_reference[k]} for k in fields}
            save('reference_comparison.json', ref_compare)
            assert all(v['equal'] for v in ref_compare.values()), [k for k,v in ref_compare.items() if not v['equal']]
            selected = adapter.control_from_json(HERE/'full3300_current/unused.json',cfg,ControlAction)
            held = reference.copy(); held.N_P_star=selected.N_P_star; held.N_UF_star=selected.N_UF_star
            coord.validate(held); coord.validate(selected)
            application = dict(no_source_change=True,state_error=initial_error,same_full_selection_reference=True,optimizer_calls=0,reason='Final SDMPC continuous/cycle-mean selection requires discrete scalar response check')
            save('application.json', application)
            (OUT / 'initial.pickle').write_bytes(pickle.dumps((cfg, state, captured['forecast']), protocol=5))
            results = {}
            for arm in ('hold', 'selected'):
                action = held if arm == 'hold' else selected
                for block in seq.actions(action,3):
                    signals.validate_writer(block,cfg,adapter.load_signal_group_actuation_plan(),'experiment')
                started = time.perf_counter()
                with seq.prediction_scope(action, cfg, 3300, 3) as visits:
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
                shared = constraints.shared_urban_quantities(follower, response, start_sec=3300, horizon_steps=3)
                feasibility = constraints.shared_quantity_constraints(follower, action, shared, start_sec=3300, horizon_steps=3,
                    np_mode='cap', target_np_veh=action.N_P_star, np_tolerance_veh=options['shared_tolerance'],
                    nuf_mode='cap', target_nuf_veh_h=action.N_UF_star, nuf_tolerance_veh_h=options['shared_tolerance'])
                results[arm] = dict(omega_ttt_veh_h=point.ttt, costs_by_stock=costs, shared_constraints=feasibility,
                    predicted_merge=point.control_area['predicted_ramp_merge'], resource_max_exceedance=exceed,
                    writer_three_blocks=True, conservation_states=4, wall_sec=wall)
                save(arm + '.json', results[arm])
                print('EXECUTION', arm, point.ttt, wall, flush=True)
            assert all(sha(p) == digest for p, digest in pins.items())
            save('summary.json', dict(status='complete', start_sec=3300, end_sec=3750,
                forecasts=2, optimizer_calls=0, native_runs=0, fits=0, future_observation_inputs=False,
                application=application, source_pins=pins, results=results))
            raise verifier.Done()
        sdmpc_pfo.solve = run
        return original_main()
    adapter.main = wrapped_main
    verifier.main()


if __name__ == '__main__':
    main()
