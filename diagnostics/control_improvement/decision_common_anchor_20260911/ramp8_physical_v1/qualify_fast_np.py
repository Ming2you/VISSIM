"""Qualify pending canonical edits in memory while an older decision is pinned."""
import ast
import hashlib
import importlib
import json
from pathlib import Path
import sys
import time
import unittest

D = Path(__file__).resolve().parent
ROOT = D.parents[3]
sys.path[:0] = [str(ROOT), str(ROOT/'vendor/NumSim-mine')]


def install_pending():
    names = ('recorded_targets_replay_pending_v1', 'context_alias_guard_pending_v1',
        'fixed_context_token_pending_v1', 'fast_np_runtime_pending_v2',
        'fast_np_restoration_pending_v2', 'fast_np_follower_pending_v2')
    composed, pins = {}, {}
    for name in names:
        m = json.loads((D/(name+'.json')).read_text(encoding='utf-8'))
        pins[str(D/(name+'.json'))] = hashlib.sha256((D/(name+'.json')).read_bytes()).hexdigest()
        path = ROOT/m['path']
        raw = path.read_bytes()
        h = hashlib.sha256(raw).hexdigest()
        if h != m['source_file_sha256']:
            raise ValueError('Pinned source changed: '+str(path))
        pins[str(path)] = h
        text = composed.get(path, raw.decode('utf-8').replace('\r\n','\n'))
        for edit in m.get('replacements', [{'before':m.get('before'), 'after':m.get('after')}]):
            if text.count(edit['before']) != 1:
                raise ValueError((name, edit['before'][:100]))
            text = text.replace(edit['before'], edit['after'])
        composed[path] = text
    for path, text in composed.items():
        module = importlib.import_module('.'.join(path.relative_to(ROOT).with_suffix('').parts))
        old = {n.name:ast.dump(n) for n in ast.parse(path.read_text(encoding='utf-8')).body if isinstance(n, ast.FunctionDef)}
        changed = [n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and ast.dump(n) != old.get(n.name)]
        exec(compile(ast.Module(body=changed,type_ignores=[]), str(path), 'exec'), module.__dict__)
    return pins


def main():
    pins = install_pending()
    modules = ('test_fast_np_initialization', 'test_joint_decision_anchor', 'test_fixed_shared_game',
        'test_physical_ramp_branches', 'test_runtime_joint_prices', 'test_runtime_joint_leader',
        'test_joint_owner_game_candidate', 'test_joint_owner_game_round_robin', 'test_joint_leader_result',
        'test_joint_final_output_budget', 'test_signal_profile_experiments', 'test_selected_shared_profile',
        'test_joint_main_integration', 'test_decision_shared_response_cache', 'test_joint_neighbor_callbacks')
    suite = unittest.defaultTestLoader.loadTestsFromNames(['diagnostics.'+m for m in modules])
    started = time.perf_counter()
    with (D/'fast_np_pending_tests_v2.txt').open('w', encoding='utf-8') as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    report = {'completed':result.wasSuccessful(), 'tests_run':result.testsRun,
        'failures':len(result.failures), 'errors':len(result.errors), 'wall_sec':time.perf_counter()-started,
        'sources_sha256':pins,
        'source_changes':[p for p,h in pins.items() if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h],
        'scope':'Pending function bodies only in this process; canonical files unedited; no native run.'}
    (D/'fast_np_pending_tests_v2.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report))
    return 0 if report['completed'] and not report['source_changes'] else 1


if __name__ == '__main__': sys.exit(main())
