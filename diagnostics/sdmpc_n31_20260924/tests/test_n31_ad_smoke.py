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

    def test_vsl_anchor_at_vsl_max_is_a_zero_column(self):
        case = self.result['vsl_anchor_max']
        self.assertEqual(case['vsl_max'], 110.0)
        self.assertEqual(case['max_abs_tangent'], 0.0)
        self.assertTrue(case['finite'])

    def test_zone_axis_reaches_its_parent_cells(self):
        self.assertEqual(self.result['vsl_zone_reach']['cells_with_tangent'], list(range(15, 25)))


if __name__ == '__main__':
    unittest.main()
