"""Bounded current-main preparation, projection and150-second worker replays."""
from datetime import datetime, timezone
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT/'diagnostics/fixtures/area_baseline_before_route_choice_beta0.json'
DECISIONS = ROOT/'evaluation/runs/codex_n7_pure_s13_20260910/decisions_codex_n7_pure_s13_20260910'


class RemainingProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not all(path.is_file() for path in (CONFIG, DECISIONS/'state_001200.json', DECISIONS/'action_001050.json')):
            raise unittest.SkipTest('Explicit historical replay inputs are unavailable')
        cls.temporary = tempfile.TemporaryDirectory(prefix='remaining-probe-migration-', dir=ROOT/'diagnostics')
        cls.directory = Path(cls.temporary.name).resolve()
        if not cls.directory.is_relative_to((ROOT/'diagnostics').resolve()):
            raise ValueError('Temporary output escaped diagnostics')
        manifest = json.loads((ROOT/'diagnostics/area_candidate_configs/manifest.json').read_text(encoding='utf-8-sig'))
        cls.frozen = [ROOT/path for path in manifest['source_sha256']]
        cls.frozen += [CONFIG, ROOT/'diagnostics/area_main_preflight/first_ramp_clip_50548.pkl']
        cls.before = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in cls.frozen}
        cls.results = []

    @classmethod
    def tearDownClass(cls):
        after = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in cls.frozen}
        if after != cls.before:
            raise AssertionError('A live pinned file or historical fixture changed')
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        path = ROOT/f'diagnostics/remaining_probe_migration_validation_{stamp}.json'
        with path.open('x', encoding='utf-8') as stream:
            json.dump({'results': cls.results, 'frozen_sha256': after,
                       'scope': 'Historical pure-n7 input with immutable area baseline before route-choice/native-input additions; current production main preparation and one150-second endpoint/repeat/fresh worker. Not validation of the new complete-route live model; no VISSIM or full optimizer.'}, stream, indent=2)
            stream.write('\n')
        print('MIGRATION_REPORT='+str(path))
        cls.temporary.cleanup()

    def invoke(self, name, extra=()):
        importlib.import_module('diagnostics.'+name)
        output = self.directory/(name+'.json')
        command = [sys.executable, '-X', 'utf8', '-m', 'diagnostics.'+name,
                   '--config', str(CONFIG), '--snapshot', str(DECISIONS/'state_001200.json'),
                   '--previous', str(DECISIONS/'action_001050.json'), '--output', str(output), *extra]
        started = time.monotonic()
        result = subprocess.run(command, cwd=ROOT, text=True, encoding='utf-8', capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr[-9000:]+result.stdout[-1000:])
        completed = output.read_bytes()
        payload = json.loads(completed)
        repeated = subprocess.run(command, cwd=ROOT, text=True, encoding='utf-8', capture_output=True, timeout=10)
        self.assertNotEqual(repeated.returncode, 0)
        self.assertEqual(output.read_bytes(), completed)
        missing = subprocess.run([sys.executable, '-X', 'utf8', '-m', 'diagnostics.'+name], cwd=ROOT,
                                 text=True, encoding='utf-8', capture_output=True, timeout=10)
        self.assertNotEqual(missing.returncode, 0)
        self.results.append({'module': name, 'command': command, 'wall_sec': time.monotonic()-started,
                             'output_sha256': hashlib.sha256(completed).hexdigest(),
                             'explicit_inputs_required': True, 'existing_output_rejected': True,
                             'result': payload})
        return payload

    def test_main_prepares_actual_controller_and_keeps_production_bootstrap(self):
        result = self.invoke('probe_area_full_decide', ['--prepare-only'])
        self.assertTrue(result['reached_actual_main_decide'])
        self.assertFalse(result['decide_executed'])
        self.assertEqual(result['worker_bootstrap'], {
            'module': 'evaluation.controllers.vissim_stackelberg_adapter',
            'func': 'install_price_worker_runtime_patches'})

    def test_package_main_repeat_and_fresh_worker_same_point(self):
        result = self.invoke('probe_area_package_runtime', ['--action', str(DECISIONS/'action_001200.json')])
        self.assertEqual(result['horizon_sec'], 150)
        self.assertTrue(result['fresh_worker_equal'] and result['main_worker_equal'])
        self.assertTrue(result['all_stock_closures_pass'] and result['original_inputs_unchanged'])

    def test_initial_actual_projection_without_new_entries(self):
        result = self.invoke('probe_all_area_initial')
        row = result['records'][0]
        self.assertAlmostEqual(row['raw_omega_veh'], row['model_omega_veh'])
        self.assertEqual(row['initial_area_entries'], 0)
        self.assertTrue(row['physical_vehicle_counts_enabled'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
