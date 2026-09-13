"""Normal benchmark counters must not install per-call hooks or lose children."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ResourceTests(unittest.TestCase):
    def test_spawn_exact_output_without_function_hooks(self):
        with tempfile.TemporaryDirectory(prefix='resource_test_', dir=ROOT / 'diagnostics') as folder:
            target = Path(folder)
            script = target / 'exercise.py'
            script.write_text('''import multiprocessing, sys
def work():
    assert sys.getprofile() is None and sys.gettrace() is None
    assert all(sys.monitoring.get_tool(i) is None for i in range(6))
    print(sum(i*i for i in range(4000)), flush=True)
if __name__ == '__main__':
    work()
    child=multiprocessing.get_context('spawn').Process(target=work)
    child.start(); child.join(); assert child.exitcode == 0
''', encoding='utf-8')
            env = dict(os.environ)
            env.pop('RW_DECISION_RESOURCE_DIR', None)
            plain = subprocess.run([sys.executable, '-X', 'utf8', str(script)], env=env,
                                   capture_output=True, check=True, timeout=30)
            env['PYTHONPATH'] = os.pathsep.join([str(ROOT), str(ROOT / 'diagnostics/decision_resource_bootstrap')])
            env['RW_DECISION_RESOURCE_DIR'] = str(target / 'resources')
            counted = subprocess.run([sys.executable, '-X', 'utf8', str(script)], env=env,
                                     capture_output=True, check=True, timeout=30)
            self.assertEqual((plain.stdout, plain.stderr), (counted.stdout, counted.stderr))
            markers = list((target / 'resources').glob('*.started.json'))
            self.assertEqual(len(markers), 2)
            reports = [json.loads(p.with_name(p.name.replace('.started', '')).read_text()) for p in markers]
            self.assertEqual(sum(row['parent_pid'] in {r['pid'] for r in reports} for row in reports), 1)
            for row in reports:
                self.assertTrue(row['completed'])
                self.assertFalse(row['function_instrumentation'])
                self.assertGreaterEqual(row['observed_process_cpu_sec'], 0.)
                self.assertTrue(row['memory']['available'])


if __name__ == '__main__':
    unittest.main()
