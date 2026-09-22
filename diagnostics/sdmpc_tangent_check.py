"""Offline derivative preflight. Never starts VISSIM or writes native controls."""
from pathlib import Path
import hashlib
import json
import pickle
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine')]


def prepare(out, horizon):
    from evaluation.controllers import vissim_stackelberg_adapter as a, sdmpc, sdmpc_tangent, lane_plant_runtime
    from evaluation.controllers import area_follower_objective as joint, area_meter_finalization as meters
    from scripts.offline_harness_20260904 import build
    from src.models.state import TrafficState, ControlAction, segment_vsl
    from src.models.demand import DemandStep
    old = ROOT.parent/'sdmpc-lane-plant-20260921/evaluation/runs/lane_native_nc2850_s13_v3/decisions_lane_native_nc2850_s13_v3'
    statepath, previouspath = old/'state_000900.json', old/'action_000750.json'
    config = json.loads((ROOT/'diagnostics/lane_storage_recovery_20260921/config_candidate.json').read_text())
    config['adapter']['sdmpc_derivatives'] = 'tangent-v1'
    configpath = out/'config.json'
    configpath.write_text(json.dumps(config, indent=2)+'\n')
    observe = lane_plant_runtime.observe_live
    lane_plant_runtime.observe_live = lambda c, r: observe(c, r, use_checkpoint=False)
    cfg, state, raw, metadata, det, cal, tuning = build(a, TrafficState, configpath, statepath, previouspath)
    options = a.joint_owner_game_settings(tuning, cfg, 'wu-link')
    sdmpc.configure(tuning, cfg)
    sdmpc.install_cost_ownership(cfg, det)
    controller = a.build_priced_wu_link_controller(cfg, tuning)
    a.install_vissim_terminal_cost_objective(controller, cfg, tuning)
    a.install_price_worker_bootstrap(controller, raw, det)
    previous = a.control_from_json(previouspath, cfg, ControlAction)
    forecast = a.demand_from_state(raw, cfg, DemandStep, cfg.mpc.horizon_steps, cal, det)
    historical = meters.prepare_held_actual_reference(previous, cfg)
    historical, _ = joint.expand_shared_vsl_action(historical, cfg, segment_vsl_func=segment_vsl)
    follower = controller.nash_solver
    reference = meters.prepare_held_actual_reference(historical, cfg)
    mapping = a.load_optional_json(str(ROOT/tuning['mapping_json']))
    sources = {str(configpath.resolve()): hashlib.sha256(configpath.read_bytes()).hexdigest()}
    bootstrap = dict(state_json={'network_path': str(Path(raw['network_path']).resolve())},
        detector_mapping=det, runtime_sources=sources)
    with joint.shared_query_runtime_scope():
        a._PHASE_VECTOR_FOLLOWER['ref'] = follower
        callbacks, context, fingerprint = joint._joint_runtime_callbacks(follower, state, forecast,
            historical, reference, mapping, sources, reference=reference, total_budget=None,
            directional={}, tolerance=options['nuf_tolerance_veh_h'], price_probe=False)
        coord = sdmpc.Coordinates(cfg, reference, callbacks['move_box'], dict(cfg.network.sdmpc_options))
        request = sdmpc_tangent.prepare_request(follower, state, forecast, reference, reference, coord, bootstrap)
        request['horizon'] = horizon
        request['diagnostic_checkpoint'] = str(out/'prediction_checkpoint.pickle')
        (out/'request.pickle').write_bytes(pickle.dumps(request, protocol=5))
    print(json.dumps(dict(prepared=True, axes=len(coord.axes), horizon=horizon)), flush=True)


def main():
    import subprocess
    out = ROOT/'diagnostics'/sys.argv[1]
    out.mkdir(exist_ok=True)
    if sys.argv[2] == 'prepare':
        prepare(out, int(sys.argv[3]))
        return 0
    data = (out/'request.pickle').read_bytes()
    result = out/('result_'+sys.argv[2]+'.pickle')
    started = time.perf_counter()
    process = subprocess.run([sys.executable, '-B', str(ROOT/'evaluation/controllers/sdmpc_tangent_worker.py'),
        str(out/'request.pickle'), str(result), hashlib.sha256(data).hexdigest()])
    receipt = pickle.loads(result.read_bytes())
    receipt['wall_sec_including_spawn'] = time.perf_counter()-started
    (result.with_suffix('.json')).write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items()
        if k in ('error', 'scalar_sec', 'tangent_sec', 'wall_sec_including_spawn', 'ad_axes', 'max_primal_state_error')}), flush=True)
    return process.returncode


if __name__ == '__main__':
    raise SystemExit(main())
