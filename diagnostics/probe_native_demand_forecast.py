"""Actual complete raw state -> configured timetable -> fresh worker forecast."""
from copy import deepcopy
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import pickle
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine')]


def forecast(payload):
    from evaluation.controllers import vissim_stackelberg_adapter as adapter
    from src.models.demand import DemandStep
    return [vars(row) for row in adapter.demand_from_state(payload['raw'], payload['cfg'], DemandStep,
        4, payload['calibration'], payload['detectors'])]


def main():
    if len(sys.argv) == 4 and sys.argv[1] == '--worker':
        from evaluation.controllers import vissim_stackelberg_adapter as adapter, runtime_setup
        payload = pickle.loads(Path(sys.argv[2]).read_bytes())
        adapter.install_config_switches(payload['tuning'])
        os.environ['RW_OFFSET_WRITER'] = 'experiment'
        runtime_setup.install_worker_runtime(adapter, payload['cfg'], payload['raw'], payload['detectors'])
        with Path(sys.argv[3]).open('x', encoding='utf-8') as file:
            json.dump(forecast(payload), file)
        return
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): raise FileExistsError(args.output)
    from diagnostics.probe_model_area_integration import build_projected, adapter
    original = ROOT/'diagnostics/area_candidate_configs/n7_area_beta0.json'
    run = 'codex_area_observed_nc_s13_20260910'
    folder = ROOT/'evaluation/runs'/run/('decisions_'+run)
    raw_path, previous = folder/'anchor_001500.json', folder/'action_000001.json'
    sources = [original, raw_path, previous, Path(__file__),
               *sorted((ROOT/'evaluation/controllers').glob('*.py'))]
    before = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    tuning = json.loads(original.read_text(encoding='utf-8'))
    tuning.setdefault('prediction', {})['native_input_schedule'] = True
    os.environ['RW_OFFSET_WRITER'] = 'experiment'
    with tempfile.TemporaryDirectory(prefix='native-timetable-', dir=ROOT/'diagnostics') as directory:
        directory = Path(directory)
        config = directory/'config.json'
        config.write_text(json.dumps(tuning), encoding='utf-8')
        cfg, state, detectors, tuned, raw, mapping, metadata = build_projected(config, raw_path, previous, fixture_inputs=False)
        calibration = adapter.load_optional_json(str(ROOT/'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))
        calibration = adapter.deep_update(calibration, tuned.get('calibration_override', {}))
        payload = {'cfg': cfg, 'raw': raw, 'detectors': detectors, 'tuning': tuned, 'calibration': calibration}
        frozen = pickle.dumps(payload, protocol=5)
        actual = forecast(payload)
        baseline = deepcopy(payload)
        del baseline['cfg'].network.native_input_schedule
        persistence = forecast(baseline)
        differences = {group: {key: value-persistence[0][group][key]
            for key, value in actual[0][group].items() if value != persistence[0][group][key]}
            for group in ('freeway_mainline', 'urban_boundary', 'ramp_arrival')}
        assert all(abs(value) <= 1e-5 for group in differences.values() for value in group.values()), differences
        assert all(math.isclose(r['freeway_mainline']['FW_E'], expected, rel_tol=0, abs_tol=1e-6)
                   for r, expected in zip(actual, [6599.736, 6599.736, 6929.7228, 6929.7228]))
        assert all(r['ramp_arrival'] == actual[0]['ramp_arrival'] for r in actual)
        internal_targets = {r['target_storage'] for r in cfg.network.native_internal_inputs['inputs'].values()}
        assert all(r['urban_boundary'].get(target, 0.) == 0 for r in actual for target in internal_targets)
        input_path, result_path = directory/'input.pkl', directory/'result.json'
        input_path.write_bytes(frozen)
        result = subprocess.run([sys.executable, '-X', 'utf8', '-m', 'diagnostics.probe_native_demand_forecast',
            '--worker', str(input_path), str(result_path)], cwd=ROOT, capture_output=True, text=True,
            encoding='utf-8', timeout=60)
        if result.returncode: raise RuntimeError(result.stderr[-6000:])
        assert json.loads(result_path.read_text(encoding='utf-8')) == actual
        assert pickle.dumps(payload, protocol=5) == frozen
        summary = {'schema': 'native-timetable-integration/v1', 'raw_state_sec': raw['sim_sec'],
            'overlay': {'prediction': {'native_input_schedule': True}},
            'forecast': actual, 'persistence': persistence,
            'source_schedule_inputs': len(cfg.network.native_input_schedule['inputs']),
            'native_internal_inputs': list(cfg.network.native_internal_inputs['inputs']),
            'first_interval_matches_raw_within_1e_5_vph': True, 'first_interval_rounding_differences': differences,
            'fresh_worker_equal': True, 'input_objects_unchanged': True,
            'scope': 'Actual1500 snapshot, installed configure_runtime and demand_from_state; known1800 input transition. No endpoint/search/VISSIM and no future traffic data.'}
    after = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    assert before == after, 'Source/input changed during forecast validation'
    summary.update(source_sha256=after, source_unchanged=True)
    with args.output.open('x', encoding='utf-8') as file:
        json.dump(summary, file, indent=2); file.write('\n')
    print(json.dumps({'output': str(args.output), 'fresh_worker_equal': True, 'source_unchanged': True}))


if __name__ == '__main__': main()
