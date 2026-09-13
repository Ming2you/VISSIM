"""Bounded recorded-state command-guard comparison; no model rollout or COM."""
import ast
import hashlib
import json
import os
from pathlib import Path
import pickle
import sys
import time
import traceback

D = Path(__file__).resolve().parent
ROOT = D.parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / 'vendor/NumSim-mine')]


def main():
    os.chdir(ROOT)
    os.environ['RW_OFFSET_WRITER'] = 'experiment'
    target = D / 'context_alias_recorded_benchmark_v1.json'
    if target.exists():
        raise FileExistsError(target)
    from diagnostics.probe_model_area_integration import build_projected
    from evaluation.controllers import vissim_stackelberg_adapter as a
    from evaluation.controllers import area_follower_objective as area, joint_owner_neighbors as neighbors
    from src.models.state import ControlAction, segment_vsl
    from src.models.demand import DemandStep
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    digest = lambda v: hashlib.sha256(pickle.dumps(v, protocol=5)).hexdigest()
    record = ROOT / 'evaluation/runs/codex_native_clock_fw080_u050_open_v2/decisions_codex_native_clock_fw080_u050_open_v2'
    config = D / 'joint_config_unlimited_prefetch_v1.json'
    paths = [Path(__file__), config, *(ROOT / 'evaluation/controllers').glob('*.py'),
             record / 'state_000900.json', record / 'action_000750.json',
             record / 'action_000900.json', record / 'action_000900.csv']
    pins = {str(p): sha(p) for p in paths}
    original = neighbors.make_joint_neighbor_callbacks
    report = {'completed': False, 'native_run': False, 'model_rollouts': 0, 'source_sha256': pins,
              'scope': 'ABBA same recorded900 state, unpriced callback context, same held command. Only duplicate identity-context checks change in memory; no production edit or whole-decision speed claim.', 'arms': {}}
    started = time.perf_counter()
    try:
        cfg, state, det, tuning, raw, mapping, meta = build_projected(
            config, record / 'state_000900.json', record / 'action_000750.json', fixture_inputs=False)
        cal = a.deep_update(dict(a.load_optional_json(str(ROOT / 'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'))), tuning.get('calibration_override', {}))
        forecast = a.demand_from_state(raw, cfg, DemandStep, 3, cal, det)
        historical = a.control_from_json(record / 'action_000900.json', cfg, ControlAction)
        historical, _ = area.expand_shared_vsl_action(historical, cfg, segment_vsl_func=segment_vsl)
        anchor = historical.copy()
        anchor.N_P_star = 2400.
        anchor.N_UF_star = 1887.525930614418
        follower = a.build_priced_wu_link_controller(cfg, tuning).nash_solver
        fixed = digest((follower, state, forecast, historical, anchor, mapping))
        manifest = json.loads((D / 'context_alias_guard_pending_v1.json').read_text())
        source = Path(neighbors.__file__)
        assert sha(source) == manifest['source_file_sha256']
        text = source.read_text(encoding='utf-8')
        for edit in manifest['replacements']:
            assert text.count(edit['before']) == 1
            text = text.replace(edit['before'], edit['after'])
        tree = ast.parse(text)
        function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'make_joint_neighbor_callbacks')
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), 'exec'), neighbors.__dict__)
        proposed = neighbors.make_joint_neighbor_callbacks
        report['setup_wall_sec'] = time.perf_counter() - started
        results = []
        for name, factory in (('old_a', original), ('new_a', proposed), ('new_b', proposed), ('old_b', original)):
            neighbors.make_joint_neighbor_callbacks = factory
            callbacks, context, _ = area._joint_runtime_callbacks(
                follower, state, forecast, historical, anchor, mapping, pins,
                reference=anchor, total_budget=None, directional={}, tolerance=40.)
            expected = callbacks['command_evidence'](anchor, context)
            before = callbacks['command_cache_stats']()
            tick, cpu = time.perf_counter(), time.process_time()
            for _ in range(20):
                actual = callbacks['command_evidence'](anchor, context)
                assert actual == expected
            row = {'wall_sec': time.perf_counter() - tick, 'cpu_sec': time.process_time() - cpu,
                   'evidence_sha256': digest(expected), 'repeats': 20,
                   'before': before, 'after': callbacks['command_cache_stats']()}
            assert row['after']['writer_checks'] == before['writer_checks']
            assert row['after']['hits'] - before['hits'] == 20
            assert digest((follower, state, forecast, historical, anchor, mapping)) == fixed
            report['arms'][name] = row
            results.append(expected)
            assert all(v == results[0] for v in results)
            print(json.dumps({'arm': name, 'wall_sec': row['wall_sec'], 'cpu_sec': row['cpu_sec']}), flush=True)
        report['all_evidence_values_exact'] = True
        report['all_evidence_pickle_exact'] = len({r['evidence_sha256'] for r in report['arms'].values()}) == 1
        assert report['all_evidence_pickle_exact']
        report['completed'] = True
    except Exception:
        report['error'] = traceback.format_exc()
    finally:
        neighbors.make_joint_neighbor_callbacks = original
        report['source_changes'] = [p for p, h in pins.items() if sha(p) != h]
        report['wall_sec'] = time.perf_counter() - started
        report['completed'] = report['completed'] and not report['source_changes']
        target.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k not in ('source_sha256', 'arms')}))
    return 0 if report['completed'] else 1


if __name__ == '__main__':
    sys.exit(main())
