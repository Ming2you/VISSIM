"""One bounded real endpoint per migrated CLI; no proposal installation."""
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
CONFIG = ROOT/'diagnostics/area_candidate_configs/n7_area_beta0.json'
RUN = ROOT/'evaluation/runs/codex_n7_pure_s13_20260910'
DECISIONS = RUN/('decisions_'+RUN.name)


class MigratedProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='probe-migration-', dir=ROOT/'diagnostics')
        cls.directory = Path(cls.temp.name)
        if not cls.directory.resolve().is_relative_to((ROOT/'diagnostics').resolve()):
            raise ValueError('Diagnostic temporary directory escaped its intended workspace')
        cls.results = []
        cls.frozen = [ROOT/'diagnostics/physical_projection_support_635_proposal.json',
            ROOT/'diagnostics/direct_branch_order_audit.json', ROOT/'diagnostics/offramp_feedback_trace.json',
            ROOT/'diagnostics/corrected_prediction_fidelity_two_states.json']
        cls.before = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in cls.frozen}

    @classmethod
    def tearDownClass(cls):
        after = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in cls.frozen}
        if after != cls.before:
            raise AssertionError('Migration tests changed frozen inputs or historical outputs')
        (ROOT/'diagnostics/probe_production_migration_validation.json').write_text(json.dumps({
            'tests': cls.results, 'frozen_historical_and_input_sha256': after,
            'scope': 'Five standalone CLI invocations, one1200 snapshot each, 150-second installed endpoint. No fullgrid/search or VISSIM.'}, indent=2)+'\n', encoding='utf-8')
        cls.temp.cleanup()

    def run_probe(self, name, extra):
        # Import must not install or rebind any proposal body on its own.
        importlib.import_module('diagnostics.'+name)
        output = self.directory/(name+'_production.json')
        command = [sys.executable, '-X', 'utf8', '-m', 'diagnostics.'+name,
            '--config', str(CONFIG), '--snapshot', str(DECISIONS/'state_001200.json'),
            '--previous', str(DECISIONS/'action_001050.json'), '--output', str(output)]+extra
        started = time.monotonic()
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=45)
        self.assertEqual(result.returncode, 0, result.stderr[-8000:]+result.stdout[-2000:])
        payload = json.loads(output.read_text(encoding='utf-8'))
        completed_bytes = output.read_bytes()
        repeated = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=10)
        self.assertNotEqual(repeated.returncode, 0, 'The probe overwrote a completed result')
        self.assertEqual(output.read_bytes(), completed_bytes)
        self.results.append({'module': name, 'command': command, 'wall_sec': time.monotonic()-started,
            'successful': True, 'existing_output_rejected': True,
            'output_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
            'source_sha256': payload.get('source_sha256') or payload['model_input_traces'][0]['source_sha256'],
            'result_summary': {key: payload[key] for key in ('implementation', 'horizon_sec',
                'all_stock_closures_pass', 'candidate_copy_independence', 'raw_initial_omega_veh',
                'model_initial_omega_veh') if key in payload},
            'record_count': len(payload.get('records', [])),
            'trace_step_counts': [len(row.get('steps', row.get('rows', []))) for row in
                payload.get('traces', payload.get('model_input_traces', []))]})
        return payload

    def test_grid_one_candidate_one_interval(self):
        result = self.run_probe('probe_all_area_snapshots', ['--depth', '1', '--candidate', 'previous', '--beta', '0'])
        self.assertEqual(result['horizon_sec'], 150)
        self.assertTrue(result['all_stock_closures_pass'])

    def test_legacy_grid_cli_has_same_installed_driver(self):
        result = self.run_probe('probe_single_transfer_grid', ['--depth', '1', '--candidate', 'previous', '--beta', '0'])
        self.assertTrue(result['candidate_copy_independence'])

    def test_prediction_uses_explicit_actual_action_and_comparison_csv(self):
        result = self.run_probe('probe_corrected_prediction_fidelity', ['--action', str(DECISIONS/'action_001200.json'),
            '--segments', str(RUN/('bottleneck_segments_'+RUN.name+'.csv'))])
        self.assertEqual(len(result['records']), 42)
        self.assertTrue(result['all_stock_closures_pass'])

    def test_physical_order_traces_current_endpoint(self):
        result = self.run_probe('probe_direct_branch_order', ['--action', str(DECISIONS/'action_001200.json')])
        self.assertEqual(len(result['model_input_traces'][0]['rows']), 30)
        self.assertTrue(result['model_input_traces'][0]['mass_closure'])

    def test_receiving_trace_observes_current_endpoint(self):
        result = self.run_probe('probe_offramp_feedback_trace', ['--action', str(DECISIONS/'action_001200.json'),
            '--physical', str(RUN/('bottleneck_links_'+RUN.name+'.csv'))])
        self.assertEqual(len(result['traces'][0]['steps']), 15)
        self.assertIn('actual_R_F_E_release_veh_h', result['traces'][0]['steps'][0])


if __name__ == '__main__':
    unittest.main(verbosity=2)
