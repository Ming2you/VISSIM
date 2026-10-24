"""T9 (plan C11): AD smoke of the refined plant in an isolated instrumented process.

The work runs in n31_ad_smoke.py (forward tangent instrumentation must be the
first thing a fresh interpreter installs). This test asserts its record.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import n31_fixtures as fx

SCRIPT = fx.HERE / 'n31_ad_smoke.py'


class AdSmokeTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        handle, name = tempfile.mkstemp(prefix='_tmp_ad_', suffix='.json', dir=fx.HERE)
        os.close(handle)
        out = Path(name)
        try:
            env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUTF8': '1'}
            done = subprocess.run([sys.executable, '-B', str(SCRIPT), str(out)], cwd=fx.ROOT, env=env,
                                  capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=1800)
            if done.returncode:
                raise AssertionError('AD smoke failed:\n' + done.stdout[-3000:] + done.stderr[-6000:])
            cls.result = json.loads(out.read_text(encoding='utf-8'))
        finally:
            out.unlink(missing_ok=True)

    def test_instrumented(self):
        self.assertTrue(self.result['instrumented'])

    def test_merge_and_open_exit_branches(self):
        case = self.result['merge_open_exit']
        self.assertEqual(case['delta_merge'], 1.0)            # AFA:363-366 active on FW_E
        self.assertTrue(case['terminal_capacity_is_open'])     # AFA:285-288 open exit
        self.assertFalse(case['terminal_zero_gradient'])       # fw_e_terminal "component"
        self.assertTrue(case['source_capacity_is_admitted'])   # AFA:247-249
        self.assertTrue(case['finite'])

    def test_forward_ad_equals_central_fd(self):
        checks = self.result['merge_open_exit']['checks']
        self.assertEqual({(c['axis'], c['output']) for c in checks},
                         {(a, o) for a in ('source', 'ramp', 'cap') for o in ('ttt', 'vehicles')})
        for check in checks:
            self.assertGreater(abs(check['fd']), 1e-6, check)
            self.assertLessEqual(abs(check['ad'] - check['fd']), 1e-5 * abs(check['fd']) + 1e-9, check)

    def test_vsl_anchor_at_vsl_max_is_one_sided_not_zero(self):
        # Supersedes the zero column at 110 (branch VSL model, Carlson A0.5/E4 +
        # exposure transport on FW_E): the left derivative, value unchanged.
        case = self.result['vsl_anchor_max']
        self.assertEqual(case['vsl_max'], 110.0)
        self.assertTrue(case['finite'])
        self.assertGreater(case['max_abs_tangent'], 0.0)
        for check in case['checks']:
            self.assertEqual(check['primal'], check['plain_110'], check)
            self.assertGreater(abs(check['ad']), 1e-6, check)
            # O(h) left differences converge to AD; their Richardson value agrees to 1%.
            self.assertLess(abs(check['ad'] - check['left_h1']), abs(check['ad'] - check['left_h2']), check)
            self.assertLessEqual(abs(check['ad'] - check['richardson']), 1e-2 * abs(check['ad']), check)
        self.assertEqual(case['west_max_abs_tangent'], 0.0)   # FW_W: no fitted law, legacy cap

    def test_vsl_law_left_derivative_keeps_value(self):
        for row in self.result['vsl_unit']['law_left']:
            self.assertEqual(row['value'], row['target'], row)
            self.assertNotEqual(row['ad'], 0.0, row)
            self.assertLessEqual(abs(row['ad'] - row['left_fd']), 1e-4 * abs(row['ad']) + 1e-9, row)

    def test_vsl_cohort_merge_is_mass_weighted(self):
        unit = self.result['vsl_unit']
        self.assertEqual(unit['merge_keys'], [[110.0], [110.0]])
        self.assertEqual(unit['cohorts'], [{'110.0': 10.0}, {'110.0': 10.0}])
        first, second = unit['merge_first'], unit['merge_second']
        self.assertAlmostEqual(first[0]['110.0']['0'], 0.2)          # 2 of 10 tagged under axis 0
        self.assertEqual(first[1]['110.0'], {})
        self.assertAlmostEqual(second[0]['110.0']['0'], 0.16)        # 8 remain (0.2) + 2 new under axis 1
        self.assertAlmostEqual(second[0]['110.0']['1'], 0.2)
        self.assertAlmostEqual(second[1]['110.0']['0'], 0.04)        # 2 moved downstream carry 0.2

    def test_vsl_below_max_equals_central_fd(self):
        for check in self.result['vsl_below_max']['checks']:
            self.assertGreater(abs(check['fd']), 1e-6, check)
            self.assertLessEqual(abs(check['ad'] - check['fd']), 1e-4 * abs(check['fd']), check)

    def test_zone_axis_reaches_its_parent_cells(self):
        self.assertEqual(self.result['vsl_zone_reach']['cells_with_tangent'], list(range(15, 25)))


if __name__ == '__main__':
    unittest.main()
