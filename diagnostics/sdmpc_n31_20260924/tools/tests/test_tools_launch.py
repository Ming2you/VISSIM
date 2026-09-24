"""WP-D D4/D5: freeze_worktree.ps1 + freeze_manifest.py, launch_plan.py, run_sdmpc_n31.ps1 (test doubles, no VISSIM)."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import launch_world as lw  # noqa: E402
import freeze_manifest as fm  # noqa: E402
import launch_plan as lp  # noqa: E402
from n31_common import ToolError, oc, read_json  # noqa: E402


def plan_args(tuning, name, runs, **kw):
    base = dict(tuning=str(tuning), name=name, sim_period=1350, seed=31, controller='wu-link', gt_windows='',
                stall_sec=2400, runs_root=str(runs), preflight=False)
    base.update(kw)
    return argparse.Namespace(**base)


class Freeze(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix='n31_freeze_'))
        cls.world = lw.World(cls.tmp)
        cls.frz, cls.stdout = cls.world.freeze()

    @classmethod
    def tearDownClass(cls):
        lw.rmtree(cls.tmp)

    def test_freeze_copies_hashes_and_records_git(self):
        doc = read_json(self.frz / 'FREEZE.json')
        self.assertEqual(doc['schema'], 'sdmpc31-freeze/v1')
        self.assertTrue(self.frz.name.startswith('sdmpc31_' + doc['git']['head'][:8] + '_'))
        files = doc['files']
        self.assertIn('diagnostics/sdmpc_n31_20260924/b110/boundary_fit/freeze.json', files)   # nested input kept
        self.assertNotIn('.git', files)
        self.assertFalse(any('__pycache__' in k or k.endswith('.pyc') for k in files))
        self.assertGreater(doc['git']['status_entries'], 0)                  # untracked scenario files
        self.assertEqual(doc['tree_sha256'], fm.tree_sha256(files))
        self.assertIn('FREEZE_OK', self.stdout)
        fm.verify(self.frz)

    def test_verify_detects_changed_extra_and_edited_table(self):
        target = self.frz / 'README.txt'
        original = target.read_bytes()
        try:
            target.write_bytes(original + b'x')
            with self.assertRaises(ToolError):
                fm.verify(self.frz)
        finally:
            target.write_bytes(original)
        extra = self.frz / 'evaluation' / 'new.py'
        extra.write_text('x', encoding='utf-8')
        try:
            with self.assertRaises(ToolError):
                fm.verify(self.frz)
        finally:
            extra.unlink()
        freeze = self.frz / 'FREEZE.json'
        original = freeze.read_bytes()
        try:
            doc = json.loads(original)
            doc['files']['README.txt'] = '0' * 64
            freeze.write_text(json.dumps(doc), encoding='utf-8')
            with self.assertRaises(ToolError):
                fm.verify(self.frz)
        finally:
            freeze.write_bytes(original)
        fm.verify(self.frz)

    def test_verify_switch_of_the_script(self):
        import subprocess
        done = subprocess.run([lw.POWERSHELL, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(lw.FREEZER),
                               '-Verify', str(self.frz), '-Python', sys.executable], capture_output=True, text=True, timeout=300)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn('FREEZE_VERIFIED', done.stdout)

    def test_build_refuses_a_moving_worktree(self):
        state = self.tmp / 'state.json'
        fm.write_json(state, fm.git_state(self.world.w))
        copy = self.tmp / 'copy_moving'
        shutil.copytree(self.world.w, copy, ignore=shutil.ignore_patterns('.git', '__pycache__', '*.pyc'))
        (self.world.w / 'late.txt').write_text('edited during the copy', encoding='utf-8')
        try:
            with self.assertRaises(ToolError):
                fm.build(self.world.w, copy, state)
        finally:
            (self.world.w / 'late.txt').unlink()


class LaunchPlanUnit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix='n31_plan_'))
        cls.world = lw.World(cls.tmp)
        cls.frz, _ = cls.world.freeze()
        cls.tuning = cls.frz / Path(*cls.world.tuning_rel.split('/'))

    @classmethod
    def tearDownClass(cls):
        lw.rmtree(cls.tmp)

    def test_plan_derives_everything_from_the_tuning(self):
        plan = lp.build_plan(plan_args(self.tuning, 'sdmpc31_g1', self.tmp / 'runs', gt_windows='750:900,1050:1200'))
        self.assertEqual(Path(plan['root']), self.frz)
        self.assertEqual(plan['manifest']['mode'], 'v2')
        self.assertEqual(Path(plan['runner_config']['path']),
                         self.frz / 'diagnostics' / 'sdmpc_n31_20260924' / 'scenario' / 'lane_native_b110.vbs')
        self.assertEqual(Path(plan['network_file']).name, 'sdmpc31_sdmpc31_g1.inpx')
        self.assertEqual(plan['detectors']['rows'], len(lw.cf.detector_rows()))
        self.assertEqual(len(plan['sig_files']), lp.SIG_COUNT)
        env = plan['expected_env']
        self.assertEqual(env['RW_OBSERVATION_CADENCE'], 'decision150')
        self.assertEqual(env['RW_OBS150_GT'], '750:900,1050:1200')
        self.assertEqual(Path(env['RW_OBS150_DETECTORS']), Path(plan['detectors']['path']))
        self.assertEqual(plan['ground_truth_windows'], [[750, 900], [1050, 1200]])
        self.assertEqual((plan['control_start_sec'], plan['warmup_controller'], plan['state_log_interval_sec']),
                         (900, 'no-control', 150))

    def test_refusals(self):
        runs = self.tmp / 'runs_refuse'
        bad = {
            'gt on a non-dev name': plan_args(self.tuning, 'sdmpc31_v2_s31', runs, gt_windows='750:900'),
            'sim period off the clock': plan_args(self.tuning, 'sdmpc31_g1', runs, sim_period=1000),
            'stall below 2400': plan_args(self.tuning, 'sdmpc31_g1', runs, stall_sec=600),
            'bad name': plan_args(self.tuning, '../x', runs),
            'unfrozen tuning': plan_args(self.world.w / Path(*self.world.tuning_rel.split('/')), 'sdmpc31_g1', runs),
        }
        for why, args in bad.items():
            with self.assertRaises((ToolError, oc.ObsContractError), msg=why):
                lp.build_plan(args)

    def test_pin_and_tuning_refusals_on_a_mutated_copy(self):
        copy = self.tmp / 'mut'
        shutil.copytree(self.frz, copy)
        tuning = copy / Path(*self.world.tuning_rel.split('/'))
        doc = json.loads(tuning.read_text(encoding='utf-8'))
        doc['urban']['capacity']['head_observation']['sample_interval_sec'] = 1
        tuning.write_text(json.dumps(doc), encoding='utf-8')
        with self.assertRaises(oc.ObsContractError):
            lp.build_plan(plan_args(tuning, 'sdmpc31_g1', self.tmp / 'r1'))
        doc['urban']['capacity']['head_observation'].pop('sample_interval_sec')
        tuning.write_text(json.dumps(doc), encoding='utf-8')
        sig = copy / 'diagnostics' / 'sdmpc_n31_20260924' / 'network' / '1000.sig'
        sig.write_text('changed', encoding='utf-8')
        with self.assertRaises(ToolError):
            lp.build_plan(plan_args(tuning, 'sdmpc31_g1', self.tmp / 'r2'))

    def test_signal_group_plan_is_required_and_pinned(self):
        """Review optional 3: the runner finds <config>_sgplan.vbs by name only; without it the plan is off."""
        plan = lp.build_plan(plan_args(self.tuning, 'sdmpc31_g3', self.tmp / 'runs_sg'))
        self.assertEqual(Path(plan['signal_group_plan']['path']),
                         self.frz / 'diagnostics' / 'sdmpc_n31_20260924' / 'scenario' / 'lane_native_b110_sgplan.vbs')
        copy = self.tmp / 'mut_sg'
        shutil.copytree(self.frz, copy)
        (copy / 'diagnostics' / 'sdmpc_n31_20260924' / 'scenario' / 'lane_native_b110_sgplan.vbs').unlink()
        with self.assertRaisesRegex(ToolError, 'Signal-group plan missing'):
            lp.build_plan(plan_args(copy / Path(*self.world.tuning_rel.split('/')), 'sdmpc31_g3', self.tmp / 'runs_sg2'))

    def test_verify_network_and_provenance(self):
        plan = lp.build_plan(plan_args(self.tuning, 'sdmpc31_g2', self.tmp / 'runs_net'))
        net = Path(plan['network_dir'])
        src = self.frz / 'diagnostics' / 'sdmpc_n31_20260924' / 'network'
        net.mkdir(parents=True)
        shutil.copyfile(src / 'baseline_s31_v2nc.inpx', plan['network_file'])
        for sig in src.glob('*.sig'):
            shutil.copyfile(sig, net / sig.name)
        lp.verify_network(plan)
        (net / 'sdmpc31_sdmpc31_g2_001.err').write_text('stale', encoding='utf-8')
        with self.assertRaises(ToolError):
            lp.verify_network(plan)


class Launcher(unittest.TestCase):
    """run_sdmpc_n31.ps1 end to end with the watchdog and network-copy test doubles."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix='n31_launch_'))
        cls.world = lw.World(cls.tmp)
        cls.frz, _ = cls.world.freeze()

    @classmethod
    def tearDownClass(cls):
        lw.rmtree(cls.tmp)

    def assertExit(self, done, code):
        self.assertEqual(done.returncode, code, done.stdout[-4000:] + done.stderr[-2000:])

    def test_g1_launch_with_ground_truth(self):
        done = self.world.launch(self.frz, 'sdmpc31_g1', '-GroundTruthWindows', '750:900,1050:1200')
        self.assertExit(done, 0)
        run = self.world.runs / 'sdmpc31_g1'
        self.assertIn('PROVENANCE_OK', done.stdout)
        self.assertIn('EXIT sdmpc31_g1 code=0', (run / 'launch_sdmpc31_g1.log').read_text(encoding='utf-8'))
        pre = read_json(run / 'preflight' / 'watchdog_preflight.json')
        real = read_json(run / 'watchdog_launch.json')
        for record in (pre, real):
            args = record['args']
            self.assertEqual(args['GroundTruthWindows'], '750:900,1050:1200')
            self.assertEqual(Path(args['Network']).name, 'sdmpc31_sdmpc31_g1.inpx')
            self.assertEqual(Path(args['VbsConfig']), self.frz / 'diagnostics' / 'sdmpc_n31_20260924' / 'scenario' /
                             'lane_native_b110.vbs')
            self.assertEqual((args['ControlIntervalSec'], args['StateLogIntervalSec'], args['ControlStartSec']),
                             (150, 150, 900))
            self.assertEqual((args['Controller'], args['WarmupController'], args['MaxAttempts']), ('wu-link', 'no-control', 1))
            self.assertIsNone(record['rw_leak'])
        self.assertIn('PreflightOnly', pre['bound'])
        self.assertNotIn('PreflightOnly', real['bound'])
        self.assertTrue((run / 'network' / 'sdmpc31_sdmpc31_g1.inpx').is_file())
        plan = read_json(run / 'launch_plan.json')
        self.assertEqual(plan['gt_text'], '750:900,1050:1200')

    def test_v5_style_launch_without_windows_and_name_is_claimed(self):
        done = self.world.launch(self.frz, 'sdmpc31_v2_s31')
        self.assertExit(done, 0)
        real = read_json(self.world.runs / 'sdmpc31_v2_s31' / 'watchdog_launch.json')
        self.assertNotIn('GroundTruthWindows', real['bound'])
        again = self.world.launch(self.frz, 'sdmpc31_v2_s31')
        self.assertExit(again, 3)                              # a used run name is never reused

    def test_preflight_only(self):
        done = self.world.launch(self.frz, 'sdmpc31_pf', '-PreflightOnly', seat='4,2')   # no seat needed
        self.assertExit(done, 0)
        self.assertIn('PREFLIGHT_ONLY done', done.stdout)
        runs = list((self.world.runs / '_preflight').glob('sdmpc31_pf_*'))
        self.assertEqual(len(runs), 1)
        self.assertFalse((runs[0] / 'watchdog_launch.json').exists())

    def test_refusals(self):
        self.assertExit(self.world.launch(self.frz, 'sdmpc31_v2_x', '-GroundTruthWindows', '750:900'), 3)
        self.assertExit(self.world.launch(self.frz, 'sdmpc31_seat1', seat='4,0'), 5)
        self.assertExit(self.world.launch(self.frz, 'sdmpc31_seat2', seat='3,1'), 5)
        self.assertExit(self.world.launch(self.frz, 'sdmpc31_seat3', seat='2,1'), 5)     # a dev VISSIM already runs
        unfrozen = self.world.w / Path(*self.world.tuning_rel.split('/'))
        self.assertExit(self.world.launch(self.frz, 'sdmpc31_unfrozen', tuning=unfrozen), 3)
        self.assertExit(self.world.launch(self.frz, 'sdmpc31_badnet', env={'N31_TEST_NET_EXTRA': 'x_001.err'}), 4)

    def test_run_provenance_differing_from_plan_is_exit_7(self):
        done = self.world.launch(self.frz, 'sdmpc31_badprov', env={'N31_TEST_BAD_PROV': '1'})
        self.assertExit(done, 7)
        self.assertIn('seed/sim_period', done.stdout)

    def test_concurrent_dev_seat_for_v4(self):
        # Review optional 1: beside V5 (dev 1) and two queue runs (total 3) the queue owns the next seat.
        self.assertExit(self.world.launch(self.frz, 'sdmpc31_nc_busy', '-Controller', 'no-control', '-AllowConcurrentDev',
                                          seat='3,1'), 5)
        self.assertExit(self.world.launch(self.frz, 'sdmpc31_nc_2dev', '-Controller', 'no-control', '-AllowConcurrentDev',
                                          seat='2,2'), 5)
        done = self.world.launch(self.frz, 'sdmpc31_nc_s31', '-Controller', 'no-control', '-AllowConcurrentDev', seat='2,1')
        self.assertExit(done, 0)
        real = read_json(self.world.runs / 'sdmpc31_nc_s31' / 'watchdog_launch.json')
        self.assertEqual(real['args']['Controller'], 'no-control')

    def test_seat_override_is_refused_outside_the_tests(self):
        done = self.world.launch(self.frz, 'sdmpc31_override', env={'N31_LAUNCHER_TEST': ''})
        self.assertExit(done, 2)
        self.assertIn('-SeatOverride is for the launcher tests only', done.stdout)
        self.assertFalse((self.world.runs / 'sdmpc31_override').exists())

    def test_leaked_adapter_mode_is_exit_7(self):
        done = self.world.launch(self.frz, 'sdmpc31_leak', env={'N31_TEST_LEAK_ADAPTER_MODE': '1'})
        self.assertExit(done, 7)
        self.assertIn('RW_ADAPTER_MODE', done.stdout)

    def test_freeze_switch_freezes_the_worktree_then_launches_from_the_copy(self):
        unfrozen = self.world.w / Path(*self.world.tuning_rel.split('/'))
        frozen_root = self.tmp / 'frozen_by_launcher'
        done = self.world.launch(self.frz, 'sdmpc31_frz', '-Freeze', '-FrozenRoot', str(frozen_root), tuning=unfrozen)
        self.assertExit(done, 0)
        made = [p for p in frozen_root.iterdir() if p.is_dir()]
        self.assertEqual(len(made), 1)
        self.assertTrue((made[0] / 'FREEZE.json').is_file())
        plan = read_json(self.world.runs / 'sdmpc31_frz' / 'launch_plan.json')
        self.assertEqual(Path(plan['root']), made[0])
        self.assertEqual(Path(plan['tuning']['path']), made[0] / Path(*self.world.tuning_rel.split('/')))
        self.assertIn('FREEZE_TOOL FREEZE_OK', done.stdout)
        self.assertIn('PROVENANCE_OK', done.stdout)
        # an already frozen tuning with -Freeze is an argument error: nothing is frozen or claimed
        again = self.world.launch(self.frz, 'sdmpc31_frz2', '-Freeze', '-FrozenRoot', str(frozen_root))
        self.assertExit(again, 2)
        self.assertFalse((self.world.runs / 'sdmpc31_frz2').exists())
        self.assertEqual(len([p for p in frozen_root.iterdir() if p.is_dir()]), 1)

    def test_frozen_tree_edited_after_freeze(self):
        target = self.frz / 'README.txt'
        original = target.read_bytes()
        try:
            target.write_text('edited', encoding='utf-8')
            done = self.world.launch(self.frz, 'sdmpc31_edited')
            self.assertExit(done, 3)
            self.assertIn('FREEZE.json verification failed', done.stdout)
        finally:
            target.write_bytes(original)


if __name__ == '__main__':
    unittest.main()
