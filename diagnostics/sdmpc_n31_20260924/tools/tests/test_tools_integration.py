"""WP-D against the real neighbours, on the live worktree W (no VISSIM, nothing written inside W).

- WP-E prepare_sdmpc31_network.py copies the pinned v2 network + 42 .sig into a temporary run folder;
  launch_plan.verify_network must accept exactly that folder (name sdmpc31_<Name>.inpx, receipt .json).
- WP-A watchdog -PreflightOnly, called with the arguments run_sdmpc_n31.ps1 passes, must write a
  run_provenance that launch_plan.check_provenance accepts for the plan built from the real tuning.
  W has no FREEZE.json, so the plan's freeze pin is None and the watchdog records freeze null
  (CONTRACT 1.4); every other field is checked as in a launch.
Skipped when a neighbour's file is missing.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import launch_plan as lp  # noqa: E402
from n31_common import PYTHON, ROOT, read_json  # noqa: E402

POWERSHELL = shutil.which('powershell') or r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
PREPARE = Path(r'D:\VISSIM-merge\tools\prepare_sdmpc31_network.py')
TUNING = ROOT / 'diagnostics' / 'sdmpc_n31_20260924' / 'config_n31_v2.json'
SIG_MANIFEST = ROOT / 'diagnostics' / 'sdmpc_n31_20260924' / 'network' / 'sig_manifest.json'
WATCHDOG = ROOT / Path(*lp.WATCHDOG_REL.split('/'))
NAME = 'sdmpc31_itest'


def unfrozen_plan(runs):
    """build_plan on W itself: the tree root is W and there is no freeze pin."""
    args = argparse.Namespace(tuning=str(TUNING), name=NAME, sim_period=1350, seed=31, controller='wu-link',
                              gt_windows='', stall_sec=2400, runs_root=str(runs), preflight=False)
    with mock.patch.object(lp, 'find_freeze_root', lambda _: ROOT), mock.patch.object(lp, 'freeze_pin', lambda _: None):
        return lp.build_plan(args)


def watchdog_args(plan, out_dir):
    """The argument list of run_sdmpc_n31.ps1 Invoke-Watchdog, with -PreflightOnly."""
    files = plan['runner_files']
    return ['-Name', plan['name'], '-OutDir', str(out_dir), '-Network', plan['network_file'],
            '-VbsConfig', plan['runner_config']['path'], '-DemandProfile', files['DemandProfile']['path'],
            '-Mapping', files['Mapping']['path'], '-Calibration', files['Calibration']['path'],
            '-Tuning', plan['tuning']['path'], '-UrbanInputGateMap', files['UrbanInputGateMap']['path'],
            '-VehicleInputRoles', files['VehicleInputRoles']['path'],
            '-Controller', plan['controller'], '-WarmupController', plan['warmup_controller'],
            '-SimPeriod', str(plan['sim_period']), '-ControlIntervalSec', str(plan['control_interval_sec']),
            '-ControlStartSec', str(plan['control_start_sec']), '-Seed', str(plan['seed']),
            '-StateLogIntervalSec', str(plan['state_log_interval_sec']), '-StallSec', str(plan['stall_sec']),
            '-StartupStallSec', str(plan['startup_stall_sec']), '-MaxAttempts', '1', '-NoGlobalKill', '-PreflightOnly']


@unittest.skipUnless(PREPARE.is_file() and SIG_MANIFEST.is_file() and TUNING.is_file(),
                     'WP-E network copy tool, N31D network or the v2 tuning missing')
class RealNeighbours(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix='n31_itest_'))
        cls.plan = unfrozen_plan(cls.tmp / 'runs')
        Path(cls.plan['out_dir']).mkdir(parents=True)
        cls.copy = subprocess.run([str(PYTHON), '-B', str(PREPARE), '--name', NAME, '--out-dir', cls.plan['network_dir'],
                                   '--root', str(ROOT)], capture_output=True, text=True, timeout=600,
                                  env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_real_network_copy_is_what_the_plan_verifies(self):
        self.assertEqual(self.copy.returncode, 0, self.copy.stdout + self.copy.stderr)
        lines = [l for l in self.copy.stdout.splitlines() if l.strip()]
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith('NETWORK_COPY_OK '), lines[0])
        lp.verify_network(self.plan)
        network = Path(self.plan['network_dir'])
        self.assertEqual(sorted(p.name for p in network.glob('*.inpx')), [f'sdmpc31_{NAME}.inpx'])
        self.assertEqual(len(list(network.glob('*.sig'))), lp.SIG_COUNT)
        stale = network / f'sdmpc31_{NAME}_001.err'
        stale.write_text('stale', encoding='utf-8')
        try:
            with self.assertRaises(lp.ToolError):
                lp.verify_network(self.plan)
        finally:
            stale.unlink()

    @unittest.skipUnless(WATCHDOG.is_file() and 'PreflightOnly' in WATCHDOG.read_text(encoding='utf-8-sig'),
                         'WP-A watchdog without -PreflightOnly')
    def test_real_watchdog_preflight_provenance_matches_the_plan(self):
        self.assertEqual(self.copy.returncode, 0, self.copy.stdout + self.copy.stderr)
        out_dir = Path(self.plan['out_dir']) / 'preflight'
        env = {k: v for k, v in os.environ.items() if not k.upper().startswith('RW_')}
        env.update({'RW_PYTHON': str(PYTHON), 'RW_OFFSET_WRITER': 'experiment', 'PYTHONUTF8': '1',
                    'PYTHONDONTWRITEBYTECODE': '1'})
        done = subprocess.run([POWERSHELL, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(WATCHDOG),
                               *watchdog_args(self.plan, out_dir)], capture_output=True, text=True, timeout=900,
                              env=env, cwd=str(ROOT))
        self.assertEqual(done.returncode, 0, done.stdout[-3000:] + done.stderr[-3000:])
        self.assertIn('PREFLIGHT_ONLY', done.stdout)
        provenance = out_dir / f'run_provenance_{NAME}.json'
        lp.check_provenance(self.plan, provenance, require_freeze=False)
        doc = read_json(provenance)
        self.assertIsNone(doc['observation']['freeze'])
        self.assertEqual(doc['observation']['ground_truth_windows'], [])
        with self.assertRaises(lp.ToolError):          # a launch always requires the freeze pin
            lp.check_provenance({**self.plan, 'freeze': {'path': 'x', 'sha256': '0' * 64}}, provenance)


if __name__ == '__main__':
    unittest.main()
