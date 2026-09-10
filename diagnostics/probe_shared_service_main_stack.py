"""Read-only local phase-price replay from an explicit actual-main manifest."""
import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import pickle
import subprocess
import sys
import time
from unittest.mock import patch

from diagnostics.probe_model_area_integration import ROOT, adapter, build_projected, replay_provenance
from evaluation.controllers import local_signal_service as pool


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Choose a new output; historical evidence is immutable')
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    command = manifest['command']
    def source(option):
        return Path(command[command.index(option) + 1])
    config, raw_path, previous_path = map(source, ('--tuning-json', '--state-json', '--previous-action-json'))
    started = time.perf_counter()
    with patch.dict(os.environ, manifest['environment']):
        cfg, state, detectors, tuning, raw, mapping, metadata = build_projected(
            config, raw_path, previous_path, fixture_inputs=False)
        _, Demand, Control, _, _, _ = adapter.repo_imports(ROOT / 'vendor/NumSim-mine')
        calibration = adapter.load_optional_json(str(source('--calibration-json')))
        calibration = adapter.deep_update(dict(calibration), tuning.get('calibration_override', {}))
        forecast = adapter.demand_from_state(raw, cfg, Demand,
            cfg.mpc.horizon_steps + max(0, int(getattr(cfg.mpc, 'leader_value_depth', 0))), calibration, detectors)
        previous = adapter.control_from_json(previous_path, cfg, Control)
        controller = adapter.build_priced_wu_link_controller(cfg, tuning)
        adapter.install_vissim_terminal_cost_objective(controller, cfg, tuning)
        adapter.install_price_worker_bootstrap(controller, raw, detectors)
        before = pickle.dumps((state, previous, forecast))
        pins = replay_provenance(tuning, config, raw_path, previous_path, args.manifest)
        records, seeds, global_tasks = [], [], []
        follower = controller.nash_solver
        original_cost = follower._phase_local_cost_phased
        def cost(signal, phases, setup, ctx):
            value = original_cost(signal, phases, setup, ctx)
            records.append({'signal': signal, 'cost_veh_h': value,
                'shared': bool(setup.get('shared_ramp_service')), 'substeps': ctx['substeps']})
            if setup.get('shared_ramp_service'):
                assert pool._READY_CONTEXT.get() is None
                seeds.append(asdict(setup['ready_seed']))
            return value
        def global_values(state, previous, forecast, tasks):
            global_tasks.extend((signal, phase) for signal, phase, _ in tasks)
            return {(signal, phase): 0. for signal, phase, _ in tasks}
        with patch.object(controller, '_global_ttt_with_phases', return_value=0.), \
             patch.object(controller, '_phase_price_rollouts', side_effect=global_values), \
             patch.object(follower, '_phase_local_cost_phased', side_effect=cost):
            controller._refresh_phase_prices(state, forecast, previous)
        assert seeds and all(seed == seeds[0] for seed in seeds)
        assert before == pickle.dumps((state, previous, forecast))
        from diagnostics.test_shared_service_main_stack import local_result
        parent_local = local_result(controller, state, previous, forecast)
        code = '''import pickle,sys,json
from diagnostics.test_shared_service_main_stack import local_result
controller,state,previous,forecast=pickle.loads(sys.stdin.buffer.read())
print(json.dumps(local_result(controller,state,previous,forecast),sort_keys=True))
'''
        child = subprocess.run([sys.executable, '-X', 'utf8', '-c', code],
            input=pickle.dumps((controller, state, previous, forecast)),
            capture_output=True, cwd=ROOT, timeout=30)
        if child.returncode:
            raise RuntimeError(child.stderr.decode('utf-8', errors='replace'))
        worker_local = json.loads(child.stdout)
        assert worker_local == json.loads(json.dumps(parent_local))
        changes = [p for p, sha in pins.items() if hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != sha]
        assert not changes
        output = {'schema': 'shared-service-actual-main-phase-stack/v1', 'valid': True,
            'elapsed_sec': time.perf_counter() - started,
            'scope': 'actual configure_runtime + main builder + phase refresh local costs; global values stubbed to zero; no endpoint/MPC/VISSIM and no price validity claim',
            'manifest': str(args.manifest), 'source_sha256': pins, 'source_changes': changes,
            'input_objects_unchanged': True, 'local_calls': records,
            'shared_ready_seed': seeds[0], 'shared_local_calls': len(seeds),
            'global_tasks_not_executed': len(global_tasks),
            'fresh_controller_unpickle_bootstrap_equal': True, 'parent_and_worker_local': parent_local,
            'context_reset': pool._READY_CONTEXT.get() is None}
        args.output.write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({k: output[k] for k in ('valid', 'elapsed_sec', 'shared_local_calls', 'global_tasks_not_executed', 'fresh_controller_unpickle_bootstrap_equal')}))


if __name__ == '__main__':
    main()
