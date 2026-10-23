"""Two conditional scalar forecasts, one unfitted hypothesis, no native dispatch."""
import os
for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[key] = '1'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
import copy
import datetime
import gzip
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path
from cdf_congestion_cap import CDFCongestionCap

A = Path(__file__).resolve().parent
H = A.parent
O = A / 'cdf_cap_candidate'
ROOT = Path('D:/VISSIM_packages/vsl_multizone355_20261015')
CONFIG = ROOT / 'diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/vsl_schedules_20261015/config.json'
F = Path('E:/VISSIM_runs/20261011_vsl349_off2250_s29/hold/decisions_sdmpc31_g_2250_hold_s29')
OBS = Path('E:/VISSIM_runs/20261008_coupling268_off_s29_8100/sdmpc/decisions_sdmpc31_sdmpc8100_s29')
read = lambda p: json.loads(Path(p).read_bytes())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(p, doc):
    p.write_text(json.dumps(doc, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf8')


def main():
    protocol = read(O / 'protocol.json')
    assert protocol['budget'] == {'forecasts': 2, 'fits': 0, 'native': 0, 'full_optimizations': 0}
    assert not (O / 'launch.json').exists() and not (O / 'STOP').exists() and not (A / 'STOP').exists()
    for p, h in protocol['source_pins'].items():
        assert sha(p) == h, p
    with (O / 'launch.json').open('x', encoding='utf8') as f:
        json.dump(dict(pid=os.getpid(), started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                       command=sys.argv, forecasts_authorized=2, retry=0, native=0), f, indent=2)
    sys.path[:0] = [str(ROOT), str(ROOT / 'vendor/NumSim-mine')]
    os.environ['NUMSIM_REPO_ROOT'] = str(ROOT / 'vendor/NumSim-mine')
    verify = ROOT / 'diagnostics/repin_v3c3_review_20261001/urban260/verify.py'
    sys.argv = [str(verify), '--at', '2250', '--out', str(O / 'capture'), '--tuning', str(CONFIG), '--decisions', str(OBS), '--full-selection']
    spec = importlib.util.spec_from_file_location('cdf_cap_verify', verify)
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)
    from evaluation.controllers import vissim_stackelberg_adapter as adapter, sdmpc_pfo, sdmpc_sequence as seq, runtime_setup, sdmpc, freeway_fd as fd
    from evaluation.controllers import physical_ramp_branches as ramps, signal_actuation_contract as signals, area_freeway_accounting as area
    from evaluation.controllers.control_hold import fixed_vsl_values
    from evaluation.controllers.area_runtime import model_inventory
    from evaluation.controllers.control_area_objective import get_ledger
    from src.models.state import ControlAction
    from src.controllers import rollout_endpoint as endpoint
    import numpy as np
    sdmpc.load_prices = lambda *a, **kw: (np.zeros(2), {'source': 'offline_conditional_replay_cold_prices', 'committed': False})
    base = {r['name']: r for r in read(H / 'matched_off2250_v3/summary.json')['results']}
    assert base['hold']['snapshots'][0] == base['selected']['snapshots'][0]
    paths = [Path(__file__), A / 'cdf_congestion_cap.py', O / 'protocol.json', CONFIG, verify,
             H / 'matched_off2250_v3/summary.json', A / 'distribution_contract.json',
             Path(fd.__file__), Path(area.__file__), Path(adapter.__file__),
             ROOT / 'evaluation/controllers/physical_lane_groups.py']
    paths += [F / f'action_{sec:06d}.json' for sec in (2250, 2400, 2550)]
    pins = {str(p): sha(p) for p in paths}
    captured = {}
    configure, bounds, demand = runtime_setup.configure_runtime, ramps.configure_operating_bounds, adapter.demand_from_state
    def capture_runtime(*a, **kw):
        value = configure(*a, **kw)
        captured.update(mapping=a[3], calibration=a[7], tuning=a[2])
        return value
    def capture_bounds(state, cfg, reference):
        value = bounds(state, cfg, reference)
        captured.update(state=state, cfg=cfg)
        return value
    def capture_demand(*a, **kw):
        value = demand(*a, **kw)
        captured['forecast'] = value
        return value
    runtime_setup.configure_runtime, ramps.configure_operating_bounds, adapter.demand_from_state = capture_runtime, capture_bounds, capture_demand
    completed = []

    def audit(reference, coord, policy, options, evaluate, derivative, quantities, check_budget, emit):
        state, cfg = captured['state'], captured['cfg']
        assert state.time_sec == 2250 and (cfg.simulation.T_f_sec, cfg.simulation.T_u_sec, cfg.mpc.horizon_steps) == (5, 10, 3)
        n = area.continuity_vehicle_counts(state, cfg)
        initial = base['hold']['snapshots'][0]
        assert max(abs(x-y) for road in n for x,y in zip(n[road], initial['n'][road])) < 1e-7
        assert max(abs(x-y) for road in state.freeway_speed for x,y in zip(state.freeway_speed[road], initial['speed'][road])) < 1e-7
        for name, zones in [('single90', {'FW_E__seg13': 90}), ('selected', {'FW_E__seg10': 90, 'FW_E__seg13': 90})]:
            actions = []
            for sec in (2250, 2400, 2550):
                original = seq.first_action(adapter.control_from_json(F / f'action_{sec:06d}.json', cfg, ControlAction))
                action = copy.deepcopy(original)
                action.vsl = fixed_vsl_values(action.vsl, dict(start_sec=2250, base_kmh=110, zone_kmh=zones), cfg.network.freeway_vsl_zone_heads, sec)
                for field in ('green_times', 'offsets', 'ramp_metering', 'N_P_star', 'N_UF_star', 'inflow_outflow_allocation'):
                    assert getattr(action, field) == getattr(original, field)
                signals.validate_writer(action, cfg, adapter.load_signal_group_actuation_plan(), 'experiment')
                actions.append(action)
            action = seq.pack(actions)
            candidate = CDFCongestionCap(read(A / 'distribution_contract.json')['distributions'])
            candidate.install(fd, area)
            started = time.perf_counter()
            try:
                with seq.prediction_scope(action, cfg, 2250, 3) as visits:
                    point = endpoint.evaluate_price_point(copy.deepcopy(state), action, copy.deepcopy(captured['forecast'][:3]), (),
                        endpoint.ObjectiveSpec(cfg, depth_override=3, box_walk=False, score_mode='raw'), capture_response=True)
            finally:
                candidate.restore()
            seconds = time.perf_counter() - started
            assert visits == [0, 1, 2] and not point.aborted and len(point.states) == 3 and candidate.calls > 0
            response = point.control_area_response
            assert response['model_constraint_coverage']['complete'] and response['conditional_model_feasibility_witness']
            costs, outside, snapshots = {}, {}, []
            for r in response['residence']:
                for k, count in r['inside_veh'].items():
                    costs[k] = costs.get(k, 0.) + count * r['dt_h']
                    outside[k] = outside.get(k, 0.) + (r['model_stock_veh'][k] - count) * r['dt_h']
            assert abs(sum(costs.values()) - point.ttt) < 1e-7
            for s in (state, *point.states):
                get_ledger(s).assert_stocks(model_inventory(s, cfg))
                snapshots.append(dict(time_sec=s.time_sec, stocks=get_ledger(s).stocks, n=area.continuity_vehicle_counts(s, cfg), speed=s.freeway_speed, ramp_queue=s.ramp_queue))
            with gzip.open(O / f'{name}_response.json.gz', 'wt', encoding='utf8') as f:
                json.dump(response, f, allow_nan=False)
            result = dict(name=name, ttt_veh_h=point.ttt, delta_veh_h=point.ttt - base['hold']['ttt_veh_h'], seconds=seconds,
                costs=costs, outside_costs=outside, snapshots=snapshots, physical_constraints=True,
                hook_calls=candidate.calls, native_validated=False, new_law='unfitted_native_cdf_common_congestion_cap')
            save(O / f'{name}_result.json', result)
            completed.append(result)
            print('FORECAST_DONE', name, result['delta_veh_h'], seconds, flush=True)
        raise verifier.Done()

    sdmpc_pfo.solve = audit
    verifier.main()
    assert len(completed) == 2
    for p, h in pins.items():
        assert sha(p) == h, p
    save(O / 'completion.json', dict(status='complete_pending_assessment', pid=os.getpid(),
        new_forecasts=2, new_native=0, new_optimizer_runs=0, parameter_fits=0, production_edits=0,
        source_pins=pins, future_observations_used=False, initial_stock_speed_parity=True,
        commands_fixed=True, baseline_reused=True, goal_complete=False))


if __name__ == '__main__':
    try:
        main()
    except BaseException as error:
        import traceback
        save(O / 'failure.json', dict(error=repr(error), traceback=traceback.format_exc()))
        raise
