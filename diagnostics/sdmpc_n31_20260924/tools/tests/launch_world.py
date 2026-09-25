"""A temporary git worktree W holding a complete, pinned SDMPC-31 v2 scenario for launcher tests.

Nothing here starts VISSIM: the watchdog is a PowerShell test double that records its arguments,
writes the run provenance the real PS1 (WP-A) is specified to write (CONTRACT 1.3/1.4, emulating
Set-HeadObservationTransport from the launch plan) and exits. The network copy tool is a Python
test double of prepare_sdmpc31_network.py (WP-E).
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
REAL_ROOT = TOOLS.parents[2]
for p in (str(REAL_ROOT), str(TOOLS), str(REAL_ROOT / 'diagnostics' / 'obs150_20260924' / 'tests')):
    if p not in sys.path:
        sys.path.insert(0, p)

from evaluation.controllers import obs150_contract as oc  # noqa: E402
import contract_fixtures as cf  # noqa: E402
import launch_plan  # noqa: E402

N31D = 'diagnostics/sdmpc_n31_20260924'
POWERSHELL = shutil.which('powershell') or r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
LAUNCHER = Path(r'D:\VISSIM-merge\tools\run_sdmpc_n31.ps1')
FREEZER = Path(r'D:\VISSIM-merge\tools\freeze_worktree.ps1')

FAKE_WATCHDOG = textwrap.dedent(r'''
    # Test double of run_real_world_single_watchdog_distributed_core17legs4b.ps1 (WP-A contract): no VISSIM.
    [CmdletBinding(PositionalBinding=$false)]
    param([string]$Name, [string]$OutDir, [string]$Network, [string]$VbsConfig, [string]$DemandProfile,
      [string]$Mapping, [string]$Calibration, [string]$Tuning, [string]$UrbanInputGateMap, [string]$VehicleInputRoles,
      [string]$Controller, [string]$WarmupController, [int]$SimPeriod, [int]$ControlIntervalSec, [int]$ControlStartSec,
      [int]$Seed, [int]$StateLogIntervalSec, [int]$StallSec, [int]$StartupStallSec, [int]$MaxAttempts,
      [switch]$NoGlobalKill, [string]$GroundTruthWindows = '', [switch]$PreflightOnly)
    $ErrorActionPreference = 'Stop'
    $repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
    function Ev([string]$p) { [ordered]@{ path = $p; sha256 = (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() } }
    New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
    $planPath = Join-Path $OutDir 'launch_plan.json'
    if (-not (Test-Path $planPath)) { $planPath = Join-Path (Split-Path -Parent $OutDir) 'launch_plan.json' }
    $plan = Get-Content -LiteralPath $planPath -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($p in $plan.expected_env.PSObject.Properties) { Set-Item -LiteralPath ('Env:' + $p.Name) -Value ([string]$p.Value) }
    $env:RW_DECISION_FAIL_FAST = '1'
    $rw = [ordered]@{}
    foreach ($e in (Get-ChildItem Env: | Where-Object { $_.Name -like 'RW_*' } | Sort-Object Name)) { $rw[$e.Name] = [string]$e.Value }
    $gt = @()
    if ($GroundTruthWindows) { foreach ($w in $GroundTruthWindows.Split(',')) { $a = $w.Split(':'); $gt += ,@([int]$a[0], [int]$a[1]) } }
    $freeze = Join-Path $repo 'FREEZE.json'
    $prov = [ordered]@{
      run_id = 'run-test'; name = $Name; workspace_root = $repo; seed = $Seed; sim_period_sec = $SimPeriod
      control_interval_sec = $ControlIntervalSec; state_log_interval_sec = $StateLogIntervalSec; controller = $Controller
      env = $rw
      files = [ordered]@{ network = (Ev $Network); tuning = (Ev $Tuning); generated_vbs_config = (Ev $VbsConfig)
        demand_profile = (Ev $DemandProfile); control_mapping = (Ev $Mapping); calibration = (Ev $Calibration)
        urban_input_gate_map = (Ev $UrbanInputGateMap); vehicle_input_roles = (Ev $VehicleInputRoles) }
      signal_programs = @(Get-ChildItem -LiteralPath (Split-Path -Parent $Network) -Filter '*.sig' -File | Sort-Object Name |
        ForEach-Object { Ev $_.FullName })
      observation = [ordered]@{ schema = 'obs150-provenance/v1'; cadence = 'decision150'
        plant_manifest = [ordered]@{ path = $plan.manifest.path; sha256 = $plan.manifest.sha256 }
        detectors = [ordered]@{ path = $plan.detectors.path; sha256 = $plan.detectors.sha256; rows = $plan.detectors.rows }
        expected_simres = 10; vehrec_interval_sec = 5; ground_truth_windows = $gt; freeze = (Ev $freeze) }
    }
    # The real PS1 records the runner's sibling <config>_sgplan.vbs only when it exists (WD:696-697).
    $sgplan = Join-Path (Split-Path -Parent $VbsConfig) ([IO.Path]::GetFileNameWithoutExtension($VbsConfig) + '_sgplan.vbs')
    if (Test-Path -LiteralPath $sgplan -PathType Leaf) { $prov.files.signal_group_plan = (Ev $sgplan) }
    if ($env:N31_TEST_BAD_PROV -and -not $PreflightOnly) { $prov.seed = 999 }
    if ($env:N31_TEST_LEAK_ADAPTER_MODE -and -not $PreflightOnly) { $prov.env['RW_ADAPTER_MODE'] = 'leaked' }
    $json = $prov | ConvertTo-Json -Depth 8
    if ($gt.Count -eq 0) { $json = $json -replace '"ground_truth_windows":\s*\{\s*\}', '"ground_truth_windows": []' -replace '"ground_truth_windows":\s*null', '"ground_truth_windows": []' }
    [IO.File]::WriteAllText((Join-Path $OutDir "run_provenance_$Name.json"), $json, [Text.UTF8Encoding]::new($false))
    $mode = $(if ($PreflightOnly) { 'preflight' } else { 'launch' })
    $record = [ordered]@{ mode = $mode; bound = $PSBoundParameters.Keys; args = $PSBoundParameters; rw_leak = $env:RW_LEAK }
    [IO.File]::WriteAllText((Join-Path $OutDir "watchdog_$mode.json"), ($record | ConvertTo-Json -Depth 5), [Text.UTF8Encoding]::new($false))
    Write-Output "FAKE_WATCHDOG $mode $Name"
    exit 0
''')

FAKE_PREPARE = textwrap.dedent(r'''
    """Test double of prepare_sdmpc31_network.py: copy the pinned .inpx and the 42 .sig files."""
    import argparse, os, shutil
    from pathlib import Path
    p = argparse.ArgumentParser()
    p.add_argument('--name', required=True)
    p.add_argument('--out-dir', required=True)
    p.add_argument('--root', required=True)
    a = p.parse_args()
    assert Path(a.root, 'FREEZE.json').is_file(), 'the launcher passes the frozen tree as --root'
    src = Path(os.environ['N31_TEST_NET_SRC'])
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(src / 'baseline_s31_v3bnc.inpx', out / f'sdmpc31_{a.name}.inpx')
    for sig in src.glob('*.sig'):
        shutil.copyfile(sig, out / sig.name)
    if os.environ.get('N31_TEST_NET_EXTRA'):
        (out / os.environ['N31_TEST_NET_EXTRA']).write_text('stale', encoding='utf-8')
    print('NETWORK_COPIED', out)
''')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rmtree(path):
    """Remove a test tree including git's read-only object files (Windows)."""
    import os
    import stat

    def writable(func, target, _):
        os.chmod(target, stat.S_IWRITE)
        func(target)
    shutil.rmtree(path, onexc=writable) if sys.version_info >= (3, 12) else shutil.rmtree(path, onerror=writable)


def git(cwd, *args):
    done = subprocess.run(['git', '-C', str(cwd), *args], capture_output=True, text=True)
    if done.returncode:
        raise RuntimeError(f'git {args}: {done.stderr}')
    return done.stdout


def write(root, rel, data):
    path = Path(root, *rel.split('/'))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data if isinstance(data, bytes) else data.encode('utf-8'))
    return path


class World:
    def __init__(self, base):
        self.base = Path(base)
        self.main = self.base / 'main'
        self.w = self.base / 'w'
        self.frozen_root = self.base / 'frozen'
        self.runs = self.base / 'runs'
        self.main.mkdir(parents=True)
        git(self.main, 'init', '-q')
        git(self.main, 'config', 'core.autocrlf', 'false')
        git(self.main, 'config', 'user.email', 'test@example.invalid')
        git(self.main, 'config', 'user.name', 'test')
        write(self.main, 'README.txt', 'tracked\n')
        git(self.main, 'add', 'README.txt')
        git(self.main, 'commit', '-q', '-m', 'base')
        git(self.main, 'worktree', 'add', '-q', str(self.w))
        self.populate()

    def populate(self):
        w = self.w
        for name in ('n31_common.py', 'freeze_manifest.py', 'launch_plan.py'):
            write(w, f'{N31D}/tools/{name}', (TOOLS / name).read_bytes())
        write(w, 'evaluation/controllers/obs150_contract.py',
              (REAL_ROOT / 'evaluation' / 'controllers' / 'obs150_contract.py').read_bytes())
        write(w, launch_plan.WATCHDOG_REL, FAKE_WATCHDOG)
        net = f'{N31D}/network'
        write(w, f'{net}/baseline_s31_v3bnc.inpx', '<network/>\n')
        sigs = {}
        for i in range(launch_plan.SIG_COUNT):
            sigs[f'{1000 + i}.sig'] = sha(write(w, f'{net}/{1000 + i}.sig', f'<sc no="{1000 + i}"/>\n'))
        write(w, f'{net}/sig_manifest.json', json.dumps({'files': sigs}, indent=1))
        write(w, f'{N31D}/scenario/lane_native_b110.vbs',
              'RW_FW_W_CHAIN_LINKS = "26,10771,120"\r\nRW_DETECTOR_MAPPING_PATH = "evaluation\\x\\det.json"\r\n')
        write(w, f'{N31D}/scenario/lane_native_b110_sgplan.vbs', "' signal-group plan\r\n")
        for rel in launch_plan.RUNNER_FILES.values():
            write(w, rel, f'{rel}\n')
        write(w, f'{N31D}/obs150/obs150_detectors_v2.csv', oc.format_detector_csv(cf.detector_rows()))
        document = cf.manifest_v2()
        for key in ('geometry', 'refined_partition', 'reference_config', 'parameters', 'port_profile', 'reference_protocol'):
            write(w, document['sources'][key]['path'], json.dumps({'k': key}))
        write(w, document['membership']['path'], '{"membership": 1}')
        write(w, document['off_groups'], '{"off": 1}')
        for key, pin in document['sources'].items():
            pin['sha256'] = sha(Path(w, *pin['path'].split('/')))
        document['membership']['sha256'] = sha(Path(w, *document['membership']['path'].split('/')))
        document['observation']['detectors']['sha256'] = sha(Path(w, *document['observation']['detectors']['path'].split('/')))
        self.manifest_rel = f'{N31D}/plant_n31_v2.json'
        write(w, self.manifest_rel, json.dumps(document, indent=1))
        tuning = cf.tuning_v2(document)
        tuning['freeway']['lane_plant'] = self.manifest_rel
        tuning['mapping_json'] = launch_plan.RUNNER_FILES['Mapping']
        tuning['detector_mapping_json'] = 'evaluation/x/det.json'
        tuning['config_overrides'] = {'freeway_follower': {'vsl_set': [60.0, 80.0, 110.0]}}
        self.tuning_rel = f'{N31D}/config_n31_v2.json'
        write(w, self.tuning_rel, json.dumps(tuning, indent=1))
        # untracked noise the freeze must copy or skip exactly
        write(w, f'{N31D}/b110/boundary_fit/freeze.json', '{"nested": "input"}')
        write(w, 'evaluation/controllers/__pycache__/x.cpython-312.pyc', b'\x00')
        self.prepare_tool = write(self.base, 'fake_prepare.py', FAKE_PREPARE)

    def freeze(self):
        done = subprocess.run([POWERSHELL, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(FREEZER),
                               '-Source', str(self.w), '-FrozenRoot', str(self.frozen_root), '-Python', sys.executable],
                              capture_output=True, text=True, timeout=600)
        if done.returncode:
            raise RuntimeError(done.stdout + done.stderr)
        frz = [l for l in done.stdout.splitlines() if l.startswith('FRZ=')]
        return Path(frz[-1][4:]), done.stdout

    def launch(self, frz, name, *extra, seat='0,0', tuning=None, env=None):
        import os
        environment = {**os.environ, 'N31_TEST_NET_SRC': str(Path(frz, *f'{N31D}/network'.split('/'))),
                       'RW_LEAK': 'must-not-survive', 'PYTHONDONTWRITEBYTECODE': '1', 'N31_LAUNCHER_TEST': '1',
                       **(env or {})}
        args = [POWERSHELL, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(LAUNCHER),
                '-Tuning', str(tuning or Path(frz, *self.tuning_rel.split('/'))), '-Name', name,
                '-SimPeriod', '1350', '-Seed', '31', '-RunsRoot', str(self.runs),
                '-PrepareNetworkTool', str(self.prepare_tool), '-Python', sys.executable, *extra]
        if seat is not None:
            args += ['-SeatOverride', seat]
        return subprocess.run(args, capture_output=True, text=True, timeout=900, env=environment)
