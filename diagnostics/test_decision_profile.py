"""Verify inherited parent/worker profiling and read-only result behavior."""
import json
import os
from pathlib import Path
import pstats
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ProcessProfileTests(unittest.TestCase):
    def test_spawned_process_flushes_profile_and_same_result(self):
        with tempfile.TemporaryDirectory(prefix='profile_test_', dir=ROOT/'diagnostics') as folder:
            directory = Path(folder)
            script = directory/'exercise.py'
            script.write_text('''import multiprocessing
def marker_work():
    value = sum(i*i for i in range(40000))
    print(value, flush=True)
if __name__ == '__main__':
    marker_work()
    child = multiprocessing.get_context('spawn').Process(target=marker_work)
    child.start()
    child.join()
    assert child.exitcode == 0
''', encoding='utf-8')
            env = dict(os.environ)
            env.pop('RW_DECISION_PROFILE_DIR', None)
            plain = subprocess.run([sys.executable, '-X', 'utf8', str(script)],
                                   env=env, capture_output=True, check=True, timeout=30)
            env['PYTHONPATH'] = os.pathsep.join([str(ROOT), str(ROOT/'diagnostics/decision_profile_bootstrap')])
            env['RW_DECISION_PROFILE_DIR'] = str(directory/'profile')
            profiled = subprocess.run([sys.executable, '-X', 'utf8', str(script)],
                                      env=env, capture_output=True, check=True, timeout=30)
            self.assertEqual(profiled.stdout, plain.stdout)
            self.assertEqual(profiled.stderr, plain.stderr)
            started = list((directory/'profile').glob('*.started.json'))
            self.assertEqual(len(started), 2)
            reports = [json.loads(p.with_name(p.name.replace('.started', '')).read_text(encoding='utf-8'))
                       for p in started]
            pids = {r['pid'] for r in reports}
            self.assertEqual(sum(r['parent_pid'] in pids for r in reports), 1)
            for row in reports:
                self.assertTrue(row['completed'])
                self.assertGreater(row['profiled_lifetime_wall_sec'], 0)
                self.assertGreaterEqual(row['process_cpu_sec'], 0)
                stats = pstats.Stats(str(ROOT/row['pstats']))
                marker = [v for k, v in stats.stats.items() if k[2] == 'marker_work']
                self.assertEqual(len(marker), 1)
                self.assertEqual(marker[0][1], 1)

    def test_refuses_to_replace_an_existing_profile_hook(self):
        from diagnostics.decision_profile import install
        with tempfile.TemporaryDirectory(prefix='profile_test_', dir=ROOT/'diagnostics') as folder:
            previous = sys.getprofile()
            sys.setprofile(lambda frame, event, arg: None)
            try:
                with self.assertRaisesRegex(ValueError, 'another Python profiling hook'):
                    install(folder)
            finally:
                sys.setprofile(previous)

    def test_refuses_existing_monitoring_profiler(self):
        import cProfile
        from diagnostics.decision_profile import install
        with tempfile.TemporaryDirectory(prefix='profile_test_', dir=ROOT/'diagnostics') as folder:
            profiler = cProfile.Profile()
            profiler.enable()
            try:
                with self.assertRaisesRegex(ValueError, 'another trace/monitoring tool'):
                    install(folder)
            finally:
                profiler.disable()


if __name__ == '__main__':
    unittest.main()
