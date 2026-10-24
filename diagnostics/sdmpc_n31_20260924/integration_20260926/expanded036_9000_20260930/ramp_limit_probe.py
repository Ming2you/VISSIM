"""Observe the existing 3600 s physical ramp constraints; no model changes."""
import copy
import ctypes
import gzip
import hashlib
import json
from pathlib import Path
import sys
import time

from diagnostics.sdmpc_n31_20260924.integration_20260926 import probe_selected_arrival_path as probe
from evaluation.controllers import runtime_setup, obs150_contract as oc
from evaluation.controllers import vissim_stackelberg_adapter as adapter
from evaluation.controllers import lane_ramp_runtime, physical_ramp_branches as branches
from evaluation.controllers import sdmpc_sequence as sequence
from src.models.state import ControlAction
from src.controllers import rollout_endpoint as endpoint


def main():
    kernel = ctypes.windll.kernel32
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    kernel.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    assert kernel.SetPriorityClass(kernel.GetCurrentProcess(), 0x4000)
    arm = sys.argv[1]
    assert arm in ('selected', 'progressive')
    base = probe.HERE/'expanded036_9000_20260930'
    output = base/('ramp_limit3600_'+arm)
    output.mkdir(exist_ok=False)
    folder = Path('D:/VISSIM_runs/20260930_expanded036_s29_9000_r2/sdmpc/decisions_sdmpc31_sdmpc9000_s29')
    tuning = probe.HERE/'baseline_reproduction_20260929/cellwise_calibration/coupled_expanded_joint/candidate_config.json'
    source = probe.HERE/'closedloop_recorded3600_budget_check_selected_meter_e036_10681_r2'/ (arm+'.json')
    load = lambda p: json.loads(p.read_bytes())
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    pins = {str(p): sha(p) for p in (Path(__file__), tuning, source,
        folder/'state_003600.json', folder/'action_003600.json',
        Path('D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP'))}
    frozen = Path('D:/VISSIM_runs/20260930_expanded036_runtime_r2/frozen/sdmpc31_886a014a_202609301259')
    for rel in ('evaluation/controllers/lane_ramp_runtime.py',
                'evaluation/controllers/physical_ramp_boundary.py',
                'evaluation/controllers/area_freeway_accounting.py',
                'evaluation/controllers/vissim_stackelberg_adapter.py'):
        p = probe.ROOT/rel
        assert sha(p) == sha(frozen/rel), rel
        pins[str(p)] = sha(p)
    # The new terminal option is absent in this original experiment. Verify its
    # reviewed source rather than expecting the pre-terminal file's byte hash.
    terminal_check = load(base/'cost_to_go_v1/implementation_verification.json')
    for name, digest in terminal_check['sources'].items():
        p = probe.ROOT/'evaluation/controllers'/name
        assert sha(p) == digest, name
        pins[str(p)] = digest
    payload = {}
    configure, forecast_fn, write = runtime_setup.configure_runtime, adapter.demand_from_state, oc.write_derived
    def capture(*args, **kwargs):
        result = configure(*args, **kwargs)
        payload.update(state=result[0], cfg=args[1])
        return result
    def forecast(*args, **kwargs):
        result = forecast_fn(*args, **kwargs)
        payload['forecast'] = result
        return result
    def verify_existing(raw, derived):
        obs = raw[oc.RAW_STATE_KEY]
        p = oc.resolve(obs, oc.derived_path(obs['sim_sec']))
        assert p.is_file() and p.read_bytes() == oc.derived_bytes(derived)
        pins[str(p)] = sha(p)
        return p
    runtime_setup.configure_runtime, adapter.demand_from_state, oc.write_derived = capture, forecast, verify_existing
    try:
        sys.argv = [str(Path(probe.__file__)), '--closedloop-recorded', '--at=3600',
            '--initialize-only', '--warm-head-history', '--replay-vsl-history',
            '--recording-dir='+str(folder), '--tuning-json='+str(tuning),
            '--probe-label=ramp_limits_'+arm]
        probe.main()
    finally:
        runtime_setup.configure_runtime, adapter.demand_from_state, oc.write_derived = configure, forecast_fn, write
    state, cfg = payload['state'], payload['cfg']
    assert state.time_sec == 3600 and cfg.mpc.horizon_steps == 3
    assert getattr(cfg.network, 'sdmpc_terminal_cost', None) is None
    saved = load(source)
    reference = sequence.first_action(adapter.control_from_json(folder/'action_003600.json', cfg, ControlAction))
    controls, previous = [], reference
    for command in saved['commands']:
        action = branches.candidate_from_greens(previous, previous, cfg, command['meters'])
        assert action.green_times == command['green_times']
        assert action.offsets == command['offsets'] and action.vsl == command['vsl']
        controls.append(action)
        previous = action
    action = sequence.pack(controls)
    rows = []
    original = lane_ramp_runtime.LaneRampRuntime.advance
    def traced(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        for ramp, receipt in result[2].items():
            assert receipt['duration_sec'] == 1
            rows.append(dict(ramp=ramp, **copy.deepcopy(receipt)))
        return result
    lane_ramp_runtime.LaneRampRuntime.advance = traced
    started = time.perf_counter()
    try:
        with sequence.prediction_scope(action, cfg, state.time_sec, 3) as visits:
            point = endpoint.evaluate_price_point(state, action, payload['forecast'][:3], (),
                endpoint.ObjectiveSpec(cfg, depth_override=3, box_walk=False, score_mode='raw'),
                capture_response=True)
        assert visits == [0, 1, 2] and not point.aborted
    finally:
        lane_ramp_runtime.LaneRampRuntime.advance = original
    assert len(rows) == 450*8
    assert abs(point.ttt-saved['execution']['ttt_omega_veh_h']) < 1e-7
    assert point.objective == point.ttt and point.far == 0.
    response = point.control_area_response
    resources = [r for r in response['resource_allocations'] if r['kind'].startswith('physical_ramp_')]
    ramps = {}
    for ramp in cfg.network.ramps:
        selected = [r for r in rows if r['ramp'] == ramp]
        assert len(selected) == 450 and len({r['start_sec'] for r in selected}) == 450
        merges = sum(r['accepted_merge_veh'] for r in selected)
        arrivals = sum(r['vehicles'] for r in response['transfers'] if r['target'] == 'ramp:'+ramp)
        final = point.states[-1].ramp_queue[ramp]
        expected = saved['execution']['ramps'][ramp]
        for actual, key in ((merges, 'merges'), (arrivals, 'arrivals'), (final, 'final_stock')):
            assert abs(actual-expected[key]) < 1e-7, (ramp, key)
        ramps[ramp] = dict(arrivals=arrivals, merges=merges, initial_stock=state.ramp_queue[ramp],
            final_stock=final, head_crossings=sum(r['head_service_veh'] for r in selected),
            conservation_residual=state.ramp_queue[ramp]+arrivals-merges-final)
        assert abs(ramps[ramp]['conservation_residual']) < 1e-7
    for path, digest in pins.items():
        assert sha(Path(path)) == digest, path
    data = dict(rows=rows, resources=resources)
    (output/'trace.json.gz').write_bytes(gzip.compress(json.dumps(data, allow_nan=False).encode()))
    summary = dict(arm=arm, start=3600, end=4050, ttt_omega_veh_h=point.ttt, ramps=ramps,
        same_existing_cost_and_all8_flows=True, wall_sec=time.perf_counter()-started,
        pins=pins, physical_rollouts=1, native_runs=0, model_changes=0,
        scope='Constraint attribution only. Baseline model response, not a new control-benefit test.')
    (output/'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(dict(output=str(output), cost=point.ttt, ramp10681=ramps['RM_C10681'])), flush=True)


if __name__ == '__main__':
    main()
