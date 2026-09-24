"""WP-A watchdog (plan A8): the obs150 switch, env, provenance block and -PreflightOnly.

Every run uses -PreflightOnly or is refused before the attempt loop, and every v1 run also has
-NoGlobalKill -MaxAttempts 0, so no VISSIM and no cscript runner is ever started and Kill-Vissim
is never reached (the static KillPolicyTests pin that the v2 path cannot reach it at all).
v2 cases run a byte-exact copy of the watchdog
from a throw-away repository root holding a synthetic v2 manifest, tuning and detector table
(the watchdog resolves every relative path against its own ..\\). The v1 case compares the
modified watchdog with the one of the plan's base commit (BASE_COMMIT, never HEAD: once the
integrator commits, HEAD is the modified watchdog itself) on the real OBS1 tuning: the env and the
observation evidence must be identical (plan A8 "v1 env diff 0"). ProcessStopTests run only the
watchdog's PID-based stop helpers, cut out of it, on processes the test itself starts.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import runner_harness as rh  # noqa: E402
from contract_fixtures import SHA_A, detector_rows  # noqa: E402
from evaluation.controllers import obs150_contract as oc  # noqa: E402

WATCHDOG_NAME = rh.PS1_PATH.name
OBS1 = 'diagnostics/sdmpc_pfo_caps_20260922/config_candidate_obs1.json'
# The plan's base commit (SDMPC31_OBS150_PLAN_20260924): the v1 reference watchdog. Not HEAD, which is the
# modified watchdog as soon as the integrator commits, so the comparison would pass against itself.
BASE_COMMIT = 'f34b8961605c1e2f3b90e878b443fe15c2127060'
RUNNER_CONFIG_BYTES = b"RW_SCHEMA_VERSION = 3\r\n"


def pin(path):
    return {'path': path, 'sha256': SHA_A}


def v2_manifest(csv_rel, csv_sha, runner_sha=SHA_A):
    sources = {key: pin(f'plant/{key}.json') for key in oc.V2_SOURCE_KEYS}
    sources['runner_config'] = {'path': 'scenario/runner.vbs', 'sha256': runner_sha}
    return {'schema': oc.PLANT_SCHEMA_V2, 'sources': sources, 'membership': pin('plant/membership.json'),
            'off_groups': 'plant/off_groups.json',
            'observation': {'detectors': {'path': csv_rel, 'sha256': csv_sha}, 'expected_simres': 10,
                            'vehrec_interval_sec': 5},
            'source_boundary': dict(oc.SOURCE_BOUNDARY_BLOCK), 'lane_groups': False, 'fw_e_terminal': 'component',
            'vsl_command_space': 'parent_21', 'future_observations': False,
            'qualification': 'synthetic manifest of the WP-A watchdog test'}


def tuning(lane_plant, head_extra=None):
    head = {'enabled': True, 'min_green_sec': 30, 'min_crossings': 5}
    head.update(head_extra or {})
    return {'freeway': {'lane_plant': lane_plant},
            'urban': {'capacity': {'measured': True, 'head_observation': head}},
            'execution': {'native_signal_record': False, 'signal_vbs_config': 'scenario/runner.vbs'}}


def clean_env(extra=None):
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith('RW_')}
    env.update(extra or {})
    return env


def run_watchdog(script, args, *, cwd, env=None, timeout=300):
    return subprocess.run([rh.POWERSHELL, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(script), *args],
                          cwd=str(cwd), env=clean_env(env), capture_output=True, text=True, errors='replace',
                          timeout=timeout)


class FakeRepoCase(unittest.TestCase):
    """A throw-away root: scripts\\<watchdog>, a v2 (or v1) manifest, tuning, table, runner config."""

    def setUp(self):
        if not rh.POWERSHELL:
            self.skipTest('Windows PowerShell is required')
        self._tmp = tempfile.TemporaryDirectory(prefix='wpa_ps1_')
        self.root = Path(self._tmp.name) / 'repo'
        (self.root / 'scripts').mkdir(parents=True)
        (self.root / 'evaluation' / 'controllers').mkdir(parents=True)
        for folder in ('plant', 'tuning', 'obs150', 'scenario', 'network'):
            (self.root / folder).mkdir()
        shutil.copyfile(rh.PS1_PATH, self.root / 'scripts' / WATCHDOG_NAME)
        self.script = self.root / 'scripts' / WATCHDOG_NAME
        (self.root / 'scenario' / 'runner.vbs').write_bytes(RUNNER_CONFIG_BYTES)
        self.runner_sha = hashlib.sha256(RUNNER_CONFIG_BYTES).hexdigest()
        (self.root / 'network' / 'net.inpx').write_bytes(b'<network/>')
        self.rows = detector_rows()
        self.csv = self.root / 'obs150' / 'detectors.csv'
        self.csv.write_bytes(oc.format_detector_csv(self.rows))
        self.csv_sha = hashlib.sha256(self.csv.read_bytes()).hexdigest()
        self.manifest_doc = v2_manifest('obs150/detectors.csv', self.csv_sha, self.runner_sha)
        self.write_json('plant/plant_v2.json', self.manifest_doc)
        self.write_json('plant/plant_v1.json', {'schema': oc.PLANT_SCHEMA_V1})
        self.write_json('tuning/v2.json', tuning('plant/plant_v2.json'))
        self.write_json('tuning/v1.json', tuning('plant/plant_v1.json'))
        self.out = Path(self._tmp.name) / 'out'

    def tearDown(self):
        self._tmp.cleanup()

    def write_json(self, rel, document):
        (self.root / rel).write_text(json.dumps(document, indent=1), encoding='utf-8')

    def args(self, *, name='sdmpc31_g1', tuning_rel='tuning/v2.json', extra=(), preflight=True):
        args = ['-Name', name, '-OutDir', str(self.out), '-Network', 'network\\net.inpx',
                '-VbsConfig', 'scenario\\runner.vbs', '-Tuning', tuning_rel, '-Controller', 'wu-link',
                '-WarmupController', 'no-control', '-SimPeriod', '1350', '-ControlIntervalSec', '150',
                '-StateLogIntervalSec', '150', '-ControlStartSec', '900', '-Seed', '31', '-NoGlobalKill',
                '-MaxAttempts', '0', *extra]
        return args + (['-PreflightOnly'] if preflight else [])

    def watchdog(self, args, env=None):
        return run_watchdog(self.script, args, cwd=self.root, env=env)

    def provenance(self, name='sdmpc31_g1'):
        return json.loads((self.out / f'run_provenance_{name}.json').read_text(encoding='utf-8-sig'))

    def refused(self, args, text, env=None):
        result = self.watchdog(args, env=env)
        output = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0, output)
        self.assertIn(text, output)
        self.assertFalse(list(self.out.glob('run_provenance_*.json')), 'a refused launch wrote provenance')
        return result


class V2WatchdogTests(FakeRepoCase):
    def test_v2_preflight_exports_the_contract_env_and_block(self):
        result = self.watchdog(self.args(extra=['-GroundTruthWindows', '750:900,1050:1200']))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('PREFLIGHT_ONLY provenance=', result.stdout)
        document = self.provenance()
        block = document['observation']
        oc.validate_provenance_observation(block)
        manifest = self.root / 'plant' / 'plant_v2.json'
        self.assertEqual(block['plant_manifest'], {'path': str(manifest),
                                                   'sha256': hashlib.sha256(manifest.read_bytes()).hexdigest()})
        self.assertEqual(block['detectors'], {'path': str(self.csv), 'sha256': self.csv_sha, 'rows': len(self.rows)})
        self.assertEqual(block['ground_truth_windows'], [[750, 900], [1050, 1200]])
        self.assertIsNone(block['freeze'])
        env = document['env']
        expected = oc.expected_runner_env(self.manifest_doc, str(self.csv))
        self.assertEqual({k: env.get(k) for k in expected}, expected)
        self.assertEqual(env['RW_OBS150_GT'], oc.format_gt_windows(block['ground_truth_windows']))
        self.assertEqual(document['signal_observation']['obs150']['runner_config'],
                         {'path': str(self.root / 'scenario' / 'runner.vbs'), 'sha256': self.runner_sha})
        # The RW_QUEUE_WINDOW=1 line of the measured-capacity tuning is overridden, and says so.
        self.assertIn('OBS150 RW_QUEUE_WINDOW=0 (decision150 overrides', result.stdout)
        self.assertEqual(env['RW_QUEUE_WINDOW'], '0')
        self.assertEqual(env['RW_SIGNAL_OBSERVATION_CONFIG_SHA256'],
                         document['signal_observation']['config_chain'][0]['sha256'])
        self.assertEqual(document['signal_observation']['lane_plant']['sha256'], block['plant_manifest']['sha256'])
        # Nothing else was started or written: no run log, no watchdog progress file.
        self.assertEqual(sorted(p.name for p in self.out.iterdir()),
                         ['decisions_sdmpc31_g1', 'run_provenance_sdmpc31_g1.json'])

    def test_v2_without_ground_truth_clears_it(self):
        result = self.watchdog(self.args(name='sdmpc31_v2_s31'), env={'RW_OBS150_GT': '750:900'})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        document = self.provenance('sdmpc31_v2_s31')
        self.assertNotIn('RW_OBS150_GT', document['env'])
        self.assertEqual(document['observation']['ground_truth_windows'], [])

    def test_frozen_tree_pins_freeze_json(self):
        freeze = self.root / 'FREEZE.json'
        freeze.write_text('{"schema": "test"}', encoding='ascii')
        result = self.watchdog(self.args())
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        block = self.provenance()['observation']
        oc.validate_provenance_observation(block, require_freeze=True)
        self.assertEqual(block['freeze'], {'path': str(freeze), 'sha256': hashlib.sha256(freeze.read_bytes()).hexdigest()})

    def test_launch_outside_a_frozen_tree_is_refused(self):
        self.refused(self.args(preflight=False), 'runs only from a frozen tree')

    def test_v2_forces_no_global_kill_without_the_switch(self):
        # -PreflightOnly exits before the attempt loop; this only shows the forced switch takes.
        args = [a for a in self.args() if a != '-NoGlobalKill']
        args[args.index('-MaxAttempts') + 1] = '1'
        result = self.watchdog(args)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('OBS150 kill_policy=pid_only no_global_kill=True max_attempts=1', result.stdout)
        self.assertIn('PREFLIGHT_ONLY provenance=', result.stdout)

    def test_more_than_one_attempt_is_refused(self):
        args = self.args()
        args[args.index('-MaxAttempts') + 1] = '2'
        self.refused(args, 'obs150 runs one attempt; got -MaxAttempts 2')

    def test_force_stepwise_is_refused(self):
        self.refused(self.args(extra=['-ForceStepwise']), 'rejects -ForceStepwise')

    def test_state_log_interval_is_refused(self):
        args = self.args()
        args[args.index('-StateLogIntervalSec') + 1] = '30'
        self.refused(args, 'StateLogIntervalSec equal to -ControlIntervalSec')

    def test_control_interval_is_refused(self):
        args = self.args()
        args[args.index('-ControlIntervalSec') + 1] = '60'
        args[args.index('-StateLogIntervalSec') + 1] = '60'
        self.refused(args, 'decides every 150 s')

    def test_sim_period_is_refused(self):
        args = self.args()
        args[args.index('-SimPeriod') + 1] = '1000'
        self.refused(args, 'positive multiple of 150')

    def test_audit_anchors_are_refused(self):
        self.refused(self.args(extra=['-AuditAnchorsSec', '900']), 'rejects -AuditAnchorsSec')

    def test_ground_truth_on_a_production_name_is_refused(self):
        self.refused(self.args(name='sdmpc31_v2_s31', extra=['-GroundTruthWindows', '750:900']),
                     'only on dev runs named sdmpc31_g*')

    def test_malformed_ground_truth_is_refused(self):
        self.refused(self.args(extra=['-GroundTruthWindows', '750:800']), '150 s aligned')
        self.refused(self.args(extra=['-GroundTruthWindows', '0:150']), 'start:end seconds')

    def test_adjacent_ground_truth_is_refused(self):
        # The runner would write the 900 start row of the second window twice (VBS Obs150GtStepTo).
        self.refused(self.args(extra=['-GroundTruthWindows', '750:900,900:1050']), 'merge adjacent ones')

    def test_detector_table_sha_mismatch_is_refused(self):
        self.csv.write_bytes(self.csv.read_bytes() + b'\n')
        self.refused(self.args(), 'differs from the manifest pin')

    def test_detector_path_outside_the_repo_is_refused(self):
        # CONTRACT _repo_pin: no '..' segment, no ':' (the file itself exists and matches its pin).
        outside = self.root.parent / 'detectors.csv'
        outside.write_bytes(self.csv.read_bytes())
        for path in ('obs150/../../detectors.csv', 'C:detectors.csv'):
            with self.subTest(path=path):
                self.write_json('plant/plant_v2.json', v2_manifest(path, self.csv_sha, self.runner_sha))
                self.refused(self.args(), 'observation.detectors.path must be a repo-relative forward-slash path')

    def test_runner_config_pin_mismatch_is_refused(self):
        (self.root / 'scenario' / 'runner.vbs').write_bytes(RUNNER_CONFIG_BYTES + b"' edited\r\n")
        self.refused(self.args(), 'sources.runner_config')

    def test_vbs_config_other_than_the_pinned_runner_config_is_refused(self):
        (self.root / 'scenario' / 'other.vbs').write_bytes(RUNNER_CONFIG_BYTES)
        args = self.args()
        args[args.index('-VbsConfig') + 1] = 'scenario\\other.vbs'
        self.refused(args, 'is not the manifest runner_config')

    def test_sample_interval_is_refused(self):
        self.write_json('tuning/v2.json', tuning('plant/plant_v2.json', {'sample_interval_sec': 1}))
        self.refused(self.args(), 'rejects head_observation.sample_interval_sec')

    def test_unknown_manifest_schema_is_refused(self):
        self.write_json('plant/plant_v2.json', {**self.manifest_doc, 'schema': 'coupled-lane-plant/v3'})
        self.refused(self.args(), 'Unsupported lane plant manifest schema')


class V1WatchdogTests(FakeRepoCase):
    def test_v1_preflight_has_no_obs150_env_even_when_inherited(self):
        inherited = {'RW_OBSERVATION_CADENCE': 'decision150', 'RW_OBS150_GT': '750:900',
                     'RW_OBS150_DETECTORS': 'x', 'RW_OBS150_DETECTORS_SHA256': 'y',
                     'RW_OBS150_EXPECTED_SIMRES': '10', 'RW_OBS150_VEHREC_SEC': '5'}
        result = self.watchdog(self.args(tuning_rel='tuning/v1.json'), env=inherited)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn('OBS150', result.stdout)
        document = self.provenance()
        self.assertNotIn('observation', document)
        self.assertFalse({k for k in document['env'] if k.startswith('RW_OBS150') or k == 'RW_OBSERVATION_CADENCE'})
        self.assertEqual(document['env']['RW_SIGNAL_OBSERVATION'], '1')
        self.assertEqual(document['env']['RW_QUEUE_WINDOW'], '1')

    def test_v1_ground_truth_is_refused(self):
        self.refused(self.args(tuning_rel='tuning/v1.json', extra=['-GroundTruthWindows', '750:900']),
                     'needs a coupled-lane-plant/v2 manifest')


class V1RegressionTests(unittest.TestCase):
    """Plan A8: with OBS1 the modified watchdog writes the provenance the committed one writes."""

    def test_obs1_provenance_equals_the_base_commit_watchdog(self):
        if not rh.POWERSHELL:
            self.skipTest('Windows PowerShell is required')
        # A missing reference fails: a skipped v1 regression would read as a pass.
        self.assertTrue((rh.ROOT / OBS1).is_file(), f'OBS1 tuning missing: {OBS1}')
        present = subprocess.run(['git', '-C', str(rh.ROOT), 'cat-file', '-e', BASE_COMMIT + '^{commit}'],
                                 capture_output=True)
        self.assertEqual(present.returncode, 0, f'plan base commit {BASE_COMMIT} is not in this repository')
        committed = subprocess.run(['git', '-C', str(rh.ROOT), 'show', f'{BASE_COMMIT}:scripts/{WATCHDOG_NAME}'],
                                   capture_output=True)
        self.assertEqual(committed.returncode, 0, committed.stderr.decode('utf-8', 'replace'))
        text = committed.stdout.decode('utf-8-sig')
        self.assertNotIn('Obs150', text, 'the reference must be the watchdog before WP-A')
        repo_line = '$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path'
        write_end = '  [System.Text.UTF8Encoding]::new($false)\r\n)\r\n'
        self.assertEqual(text.count(repo_line), 1)
        self.assertEqual(text.count(write_end), 1)
        # The committed watchdog, rooted at this tree and stopped right after its provenance write.
        text = text.replace(repo_line, "$repo = '" + str(rh.ROOT) + "'")
        text = text.replace(write_end, write_end + 'exit 0\r\n')
        with tempfile.TemporaryDirectory(prefix='wpa_v1_') as temp:
            temp = Path(temp)
            old_script = temp / 'committed_watchdog.ps1'
            old_script.write_bytes(b'\xef\xbb\xbf' + text.encode('utf-8'))
            common = ['-Name', 'obs1_preflight', '-VbsConfig', 'diagnostics\\lane_plant_20260921\\scenario\\lane_native.vbs',
                      '-Mapping', 'evaluation\\real_world_modi_control_ver2n21_20260907\\control_mapping_ver2n21.json',
                      '-Calibration', 'evaluation\\calibration\\real_world_prediction_calibration_core17legs4b_20260820.json',
                      '-Tuning', OBS1.replace('/', '\\'), '-Controller', 'wu-link', '-WarmupController', 'no-control',
                      '-SimPeriod', '1350', '-ControlIntervalSec', '150', '-ControlStartSec', '900', '-Seed', '31',
                      '-StateLogIntervalSec', '30', '-NoGlobalKill', '-MaxAttempts', '0']
            old = run_watchdog(old_script, common + ['-OutDir', str(temp / 'old')], cwd=rh.ROOT)
            new = run_watchdog(rh.PS1_PATH, common + ['-OutDir', str(temp / 'new'), '-PreflightOnly'], cwd=rh.ROOT)
            self.assertEqual(old.returncode, 0, old.stdout + old.stderr)
            self.assertEqual(new.returncode, 0, new.stdout + new.stderr)
            before = json.loads((temp / 'old' / 'run_provenance_obs1_preflight.json').read_text(encoding='utf-8-sig'))
            after = json.loads((temp / 'new' / 'run_provenance_obs1_preflight.json').read_text(encoding='utf-8-sig'))
        self.assertEqual(after['env'], before['env'])
        self.assertEqual(after['signal_observation'], before['signal_observation'])
        self.assertEqual(after['ramp_meter_timing'], before['ramp_meter_timing'])
        self.assertNotIn('observation', after)
        for key in ('run_id', 'created_at'):
            before.pop(key)
            after.pop(key)
        before['files'].pop('watchdog_wrapper')
        after['files'].pop('watchdog_wrapper')
        self.assertEqual(after, before)


PS_HELPERS = r'''
param([string]$Path, [string]$Case, [int]$RootId = 0, [int]$BystanderId = 0)
$ErrorActionPreference = 'Stop'
$tokens = $null; $errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($Path, [ref]$tokens, [ref]$errors)
if ($errors.Count -gt 0) { throw 'watchdog does not parse' }
# Only the named helpers are defined here; the watchdog itself never runs.
foreach ($name in @('Test-RunVissimTitle', 'Get-RunDescendantIdentities', 'Stop-RunProcesses')) {
  $definition = @($ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq $name }, $true))
  if ($definition.Count -ne 1) { throw "helper $name not found once" }
  if ($definition[0].Extent.Text -match '-Name\b') { throw "helper $name looks processes up by name" }
  . ([scriptblock]::Create($definition[0].Extent.Text))
}
if ($Case -eq 'title') {
  $rows = [Console]::In.ReadToEnd() | ConvertFrom-Json
  $out = @($rows | ForEach-Object { [bool](Test-RunVissimTitle $_.title $_.name) })
  [Console]::Out.Write((ConvertTo-Json @($out) -Compress))
  exit 0
}
$p = Get-Process -Id $RootId
$runnerIdentity = [pscustomobject]@{ Id = $p.Id; StartTime = $p.StartTime }
$runVissimIdentity = $null
$b = Get-Process -Id $BystanderId
# A bystander whose recorded start time does not match: the recheck must keep it alive.
$stale = [pscustomobject]@{ Id = $b.Id; StartTime = $b.StartTime.AddSeconds(-5) }
$staleRoot = [pscustomobject]@{ Id = $p.Id; StartTime = $p.StartTime.AddSeconds(-5) }
$staleFound = Get-RunDescendantIdentities $staleRoot
$none = @($staleFound).Count
$script:Obs150Run = $true
# The exact statements of the watchdog's STARTUP_TIMEOUT / WATCHDOG_KILL branches.
$runDescendants = $(if ($script:Obs150Run) { Get-RunDescendantIdentities $runnerIdentity } else { @() })
$found = @($runDescendants | ForEach-Object { $_.Id })
Stop-RunProcesses $runnerIdentity $runVissimIdentity $runDescendants
Stop-RunProcesses $null $stale
$script:Obs150Run = $false
$v1Descendants = $(if ($script:Obs150Run) { Get-RunDescendantIdentities $runnerIdentity } else { @() })
[Console]::Out.Write((ConvertTo-Json @{ found = @($found); stale_root = $none; v1 = @($v1Descendants).Count } -Compress))
'''

SLEEPER = 'import time; time.sleep(300)'
PARENT = ('import subprocess, sys, time; child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(300)"]); '
          'print(child.pid, flush=True); time.sleep(300)')


def run_helpers(case, *, stdin=None, root=0, bystander=0):
    with tempfile.TemporaryDirectory(prefix='wpa_stop_') as temp:
        script = Path(temp) / 'helpers.ps1'
        script.write_text(PS_HELPERS, encoding='utf-8-sig')
        return subprocess.run([rh.POWERSHELL, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(script),
                               '-Path', str(rh.PS1_PATH), '-Case', case, '-RootId', str(root),
                               '-BystanderId', str(bystander)],
                              input=stdin, capture_output=True, text=True, errors='replace', timeout=180)


def alive(pid):
    probe = subprocess.run(['tasklist', '/FI', f'PID eq {pid}', '/NH', '/FO', 'CSV'], capture_output=True, text=True,
                           errors='replace', timeout=60)
    return f'"{pid}"' in probe.stdout


class ProcessStopTests(unittest.TestCase):
    """The v2 stop path: the VISSIM title match and the PID + start-time stop of the runner's descendants.

    The helpers are cut out of the watchdog by the PowerShell parser and run alone; the processes
    stopped are python sleepers this test starts. Nothing is looked up or stopped by name.
    """

    def setUp(self):
        if not rh.POWERSHELL:
            self.skipTest('Windows PowerShell is required')

    def test_title_matches_the_network_file_as_a_whole_component(self):
        name = 'sdmpc31_g1.inpx'
        cases = [
            ('PTV Vissim 2020 (SP 14) - D:\\VISSIM_runs\\g1\\network\\sdmpc31_g1.inpx', name, True),
            ('sdmpc31_g1.inpx - PTV Vissim 2020', name, True),
            ('PTV Vissim - [D:\\runs\\SDMPC31_G1.INPX]', name, True),
            ('PTV Vissim - D:/runs/sdmpc31_g1.inpx*', name, True),
            ('PTV Vissim - D:\\runs\\sdmpc31_a_sdmpc31_g1.inpx', name, False),
            ('PTV Vissim - D:\\runs\\xsdmpc31_g1.inpx', name, False),
            ('PTV Vissim - D:\\runs\\sdmpc31_g1.inpx.bak', name, False),
            ('PTV Vissim - D:\\runs\\sdmpc31_g10.inpx', name, False),
            ('', name, False),
            ('PTV Vissim - D:\\runs\\sdmpc31_g1.inpx', '', False),
        ]
        rows = json.dumps([{'title': t, 'name': n} for t, n, _ in cases])
        result = run_helpers('title', stdin=rows)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout), [want for _, _, want in cases])

    def test_descendants_are_stopped_by_pid_and_start_time_only(self):
        bystander = subprocess.Popen([sys.executable, '-c', SLEEPER])
        parent = subprocess.Popen([sys.executable, '-c', PARENT], stdout=subprocess.PIPE, text=True)
        started = [bystander, parent]
        child_pid = None
        try:
            child_pid = int(parent.stdout.readline())
            result = run_helpers('stop', root=parent.pid, bystander=bystander.pid)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(result.stdout)
            self.assertIn(child_pid, report['found'])
            self.assertNotIn(bystander.pid, report['found'])
            self.assertEqual(report['stale_root'], 0)       # a recycled root PID adopts nothing
            self.assertEqual(report['v1'], 0)               # v1 keeps the runner + VISSIM stop only
            parent.wait(timeout=60)
            for _ in range(60):
                if not alive(child_pid):
                    break
                time.sleep(0.5)
            self.assertFalse(alive(child_pid), 'the runner child survived')
            self.assertIsNone(bystander.poll(), 'a process outside the tree was stopped')
        finally:
            for process in started:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=60)
            # A surviving child is left to end its own 300 s sleep: no stop by a PID that may be reused.
            if parent.stdout:
                parent.stdout.close()


if __name__ == '__main__':
    unittest.main()
