"""T3/T3b (plan C11, N31 review B12): parent primal == fresh-worker primal.

Two fresh interpreters (n31_parity_roles.py): the parent installs the
reference-config hooks and the full-cfg hooks in the adapter's order and pickles
what a worker receives; the worker reinstalls only the worker freeway hooks
from the pickled full cfg. 450 s of both roads must agree to <= 1e-12 (bit
equality is expected), every refined cell must read the same parent-zone VSL,
and the A1 blocks re-derived from the pickled cfg must equal the DemandStep
data the worker received.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import n31_fixtures as fx

ROLES = fx.HERE / 'n31_parity_roles.py'


def run_role(role, folder):
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUTF8': '1'}
    done = subprocess.run([sys.executable, '-B', str(ROLES), role, str(folder)], cwd=fx.ROOT, env=env,
                          capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=1800)
    if done.returncode:
        raise AssertionError(role + ' role failed:\n' + done.stdout[-3000:] + done.stderr[-6000:])
    return json.loads((folder / (role + '.json')).read_text(encoding='utf-8'))


class ParentWorkerParityTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.dir = Path(tempfile.mkdtemp(prefix='_tmp_', dir=fx.HERE))
        try:
            cls.parent = run_role('parent', cls.dir)
            cls.worker = run_role('worker', cls.dir)
        except BaseException:
            shutil.rmtree(cls.dir, ignore_errors=True)
            raise

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.dir, ignore_errors=True)

    def test_primal_parity(self):
        worst = 0.0
        for road in ('FW_E', 'FW_W'):
            a, b = self.parent['rollout'][road], self.worker['rollout'][road]
            self.assertEqual(len(a), 450)
            self.assertEqual(len(a), len(b))
            for row_a, row_b in zip(a, b):
                self.assertEqual(len(row_a), len(row_b))
                worst = max(worst, max(abs(x - y) for x, y in zip(row_a, row_b)))
        self.assertLessEqual(worst, 1e-12)

    def test_rollout_is_not_trivial(self):
        """The compared run must actually move traffic and bind VSL (not a frozen state)."""
        for road in ('FW_E', 'FW_W'):
            first, last = self.parent['rollout'][road][0], self.parent['rollout'][road][-1]
            self.assertNotEqual(first[1:32], last[1:32])
            self.assertGreater(sum(r[0] for r in self.parent['rollout'][road]), 0.0)

    def test_zone_tables_and_reads(self):
        self.assertEqual(self.parent['binding_head_of_cell'], fx.EXPECTED_HEAD_OF_CELL)
        self.assertEqual(self.worker['head_of_cell'], self.parent['head_of_cell'])
        self.assertEqual(self.worker['head_of_cell'], fx.EXPECTED_HEAD_OF_CELL)
        self.assertEqual(self.worker['vsl_reads'], self.parent['vsl_reads'])
        self.assertNotIn(33.0, self.worker['vsl_reads']['FW_E'] + self.worker['vsl_reads']['FW_W'])

    def test_full_cfg_fd_rows(self):
        """T6 record: full cfg FD is the 21-row b110 copy before LPR:436, 31 after, 31 in the worker."""
        self.assertEqual(self.parent['full_cfg_fd_rows_before_bind'], {'FW_E': 21, 'FW_W': 21})
        self.assertEqual(self.parent['full_cfg_fd_rows_after_bind'], {'FW_E': 31, 'FW_W': 31})
        self.assertEqual(self.worker['full_cfg_fd_rows'], {'FW_E': 31, 'FW_W': 31})

    def test_a1_reaches_the_worker(self):
        blocks = self.parent['a1_blocks']
        self.assertEqual(self.worker['a1_blocks'], blocks)
        for index, step in enumerate(self.worker['demand_received']):
            self.assertEqual(step, {road: blocks[road][index] for road in ('FW_E', 'FW_W')})
        self.assertGreater(min(blocks['FW_E']), 0.0)


if __name__ == '__main__':
    unittest.main()
