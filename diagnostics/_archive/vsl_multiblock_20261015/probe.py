"""Bounded saved-state VSL schedules in the exact adopted355 plant; no native run."""
import os
for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
import argparse, copy, hashlib, importlib.util, json, sys, time
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = Path('D:/VISSIM_runtime/20261012_adopted355_vsl_three/frozen/sdmpc31_ca181e84_202610121132')
DEC = Path('E:/VISSIM_runs/20261012_adopted355_optimized_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29')
TUNING = ROOT/'diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/native413_adopted355/optimized_config.json'
VERIFY = ROOT/'diagnostics/repin_v3c3_review_20261001/urban260/verify.py'
read = lambda p: json.loads(Path(p).read_bytes())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--at', type=int, choices=(1800, 2250, 3300), required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    args.out = args.out.resolve()
    assert not args.out.exists(), 'Preserve existing attempt'
    assert sha(TUNING) == 'c90882628ddc75c0c75c9a82771c96a50614b297839ec32c506859a969dc1df3'
    sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine'), str(HERE)]
    os.environ['NUMSIM_REPO_ROOT'] = str(ROOT/'vendor/NumSim-mine')
    sys.argv = [str(VERIFY), '--at', str(args.at), '--out', str(args.out),
                '--tuning', str(TUNING), '--decisions', str(DEC), '--full-selection']
    spec = importlib.util.spec_from_file_location('saved_vsl_verifier', VERIFY)
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)
    from evaluation.controllers import runtime_setup, sdmpc_pfo, sdmpc_sequence as seq
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from evaluation.controllers import signal_actuation_contract as signals
    from evaluation.controllers.area_runtime import model_inventory
    from evaluation.controllers.control_area_objective import get_ledger
    from evaluation.controllers.area_freeway_accounting import continuity_vehicle_counts
    from src.models.state import ControlAction
    from src.controllers import rollout_endpoint as endpoint
    from vsl_schedule_neighbors import schedules
    captured = {}
    original_setup = runtime_setup.configure_runtime
    original_forecast = adapter.demand_from_state
    def setup(*a, **kw):
        result = original_setup(*a, **kw)
        captured.update(state=result[0], cfg=a[1])
        return result
    def forecast(*a, **kw):
        result = original_forecast(*a, **kw)
        captured['forecast'] = result
        return result
    runtime_setup.configure_runtime = setup
    adapter.demand_from_state = forecast
    def save(name, data):
        (args.out/name).write_text(json.dumps(data, indent=2, allow_nan=False)+'\n', encoding='utf8')
    def run(reference, coord, policy, options, evaluate, derivative, quantities, check_budget, emit):
        # The canonical verifier has completed initialization and writer checks.
        # Replacing this callback prevents PFO and the full optimizer from running.
        state, cfg = captured['state'], captured['cfg']
        assert state.time_sec == args.at
        assert (cfg.simulation.T_f_sec, cfg.simulation.T_u_sec, cfg.mpc.horizon_steps) == (5, 10, 3)
        path = DEC/f'action_{args.at:06d}.json'
        assert Path(str(path)+'.applied').exists()
        anchor = adapter.control_from_json(path, cfg, ControlAction)
        coord.validate(anchor)
        candidates, skipped = schedules(coord, anchor)
        assert len(candidates) <= 25
        # Also separate the one-block effect at the bottleneck from persistence.
        z = coord.encode(anchor)
        for j, axis in enumerate(coord.axes):
            if axis['kind'] == 'vsl' and axis['key'] == 'FW_E__seg13' and axis['block'] == 0:
                z[j] = (90-axis['reference_value'])/axis['scale']
        one = coord.decode(z, anchor)
        coord.validate(one)
        candidates = [('baseline', anchor), ('FW_E__seg13:90x1', one), *candidates]
        before = copy.deepcopy(get_ledger(state).stocks)
        pins = {str(p): sha(p) for p in (TUNING, VERIFY, Path(__file__), HERE/'vsl_schedule_neighbors.py', path, DEC/f'state_{args.at:06d}.json')}
        save('protocol.json', dict(at=args.at, horizon=450, frozen_tree=str(ROOT), pins=pins,
            names=[name for name, _ in candidates], skipped=skipped, native_runs=0,
            future_observations_used=False, fixed_non_vsl_controls=True,
            scope='Saved selected three-block city/RM/caps; finite VSL profiles, exact execution model'))
        results = []
        for name, action in candidates:
            coord.validate(action)
            for block, original in zip(seq.actions(action, 3), seq.actions(anchor, 3)):
                for field in ('green_times', 'offsets', 'ramp_metering', 'N_P_star', 'N_UF_star'):
                    assert getattr(block, field) == getattr(original, field), (name, field)
                assert {k:v for k,v in block.diagnostics.items() if k.startswith('rw_meter_green_')} == {k:v for k,v in original.diagnostics.items() if k.startswith('rw_meter_green_')}
                signals.validate_writer(block, cfg, adapter.load_signal_group_actuation_plan(), 'experiment')
            tick = time.perf_counter()
            with seq.prediction_scope(action, cfg, args.at, 3) as visits:
                point = endpoint.evaluate_price_point(state, action, copy.deepcopy(captured['forecast'][:3]), (),
                    endpoint.ObjectiveSpec(cfg, depth_override=3, box_walk=False, score_mode='raw'), capture_response=True)
            assert visits == [0, 1, 2] and not point.aborted and len(point.states) == 3
            response = point.control_area_response
            assert response['model_constraint_coverage']['complete'] and response['conditional_model_feasibility_witness']
            costs = {}
            outside = {}
            for row in response['residence']:
                for key, value in row['inside_veh'].items():
                    costs[key] = costs.get(key, 0.) + value*row['dt_h']
                    outside[key] = outside.get(key, 0.) + (row['model_stock_veh'][key]-value)*row['dt_h']
            assert abs(sum(costs.values()) - point.ttt) < 1e-7
            snapshots = []
            for current in (state, *point.states):
                get_ledger(current).assert_stocks(model_inventory(current, cfg))
                snapshots.append(dict(time_sec=current.time_sec, stocks=get_ledger(current).stocks,
                    n=continuity_vehicle_counts(current, cfg), speed=current.freeway_speed,
                    ramp_queue=current.ramp_queue))
            assert before == get_ledger(state).stocks
            result = dict(name=name, ttt=point.ttt, seconds=time.perf_counter()-tick,
                delta_veh_h=point.ttt-(results[0]['ttt'] if results else point.ttt),
                costs=costs, outside_costs=outside, physical_constraints=True, writer=True,
                control_area=point.control_area, snapshots=snapshots)
            results.append(result)
            save('progress.json', dict(status='running', at=args.at, results=results))
            print(name, result['delta_veh_h'], result['seconds'], flush=True)
        save('summary.json', dict(status='complete', at=args.at, results=results, native_runs=0,
            full_optimizer_runs=0, fitted_coefficients=0, skipped=skipped))
        raise verifier.Done()
    sdmpc_pfo.solve = run
    try:
        verifier.main()
        assert (args.out/'summary.json').exists()
    except BaseException as exc:
        import traceback
        if args.out.exists():
            save('failure_preserved.json', dict(error=repr(exc), traceback=traceback.format_exc(), native_runs=0))
        raise


if __name__ == '__main__':
    main()
