# SDMPC-31 x obs150 launcher (plan D4, section 1.1). PowerShell only (run_in_background), never Git Bash.
#
#   Set-Location <FRZ>   # a tree made by freeze_worktree.ps1; launches run only from a frozen copy (NEW-14)
#   powershell -NoProfile -ExecutionPolicy Bypass -File D:\VISSIM-merge\tools\run_sdmpc_n31.ps1 `
#     -Tuning diagnostics\sdmpc_n31_20260924\config_n31_v2.json -Name sdmpc31_v2_s31 -SimPeriod 9000 -Seed 31
#   G1:  ... -Name sdmpc31_g1 -SimPeriod 1350 -Seed 31 -GroundTruthWindows 750:900,1050:1200
#   V4:  ... -Name sdmpc31_nc_s31 -SimPeriod 9000 -Seed 31 -Controller no-control [-AllowConcurrentDev]
#   Dry: ... -PreflightOnly   (plan + network copy + watchdog -PreflightOnly + provenance check; no VISSIM, no seat)
#   One step from the worktree:  Set-Location D:\VISSIM-merge\sim3-n31; ... -Freeze -Tuning diagnostics\...json ...
#        freezes the git worktree holding the tuning with freeze_worktree.ps1 (new FRZ under -FrozenRoot, printed
#        as FRZ=...) and launches the same relative tuning from that copy. Without -Freeze a tuning outside a frozen
#        tree is refused (code 3); with -Freeze a tuning already inside one is refused (code 2).
#
# The tuning file is the only configuration input: launch_plan.py derives the lane plant manifest (it must be
# coupled-lane-plant/v2), the runner config (-VbsConfig = execution.signal_vbs_config), the network pin, the
# detector table and the observation env from it, and checks every pinned byte inside FRZ. A relative -Tuning
# resolves against the current location; FRZ is the nearest folder above the tuning that holds FREEZE.json.
#
# Order: seat pre-check -> [-Freeze: freeze_worktree.ps1] -> FREEZE.json verify -> plan (claims
# D:\VISSIM_runs\20260924_sdmpc31\<Name>) ->
# network copy sdmpc31_<Name>.inpx + 42 .sig (prepare_sdmpc31_network.py, then verified here) -> clean env ->
# watchdog -PreflightOnly + provenance check -> seat re-check -> watchdog (VISSIM) -> provenance check -> EXIT.
#
# Seat rule (D:\VISSIM_runs\20260923_stage1\launch_reserved.ps1): the stage-1 queue keeps <= 3 VISSIMs and treats a
# VISSIM whose window title matches 'obs150|sdmpc|probe' as the dev seat. Launch only if total <= 3 and no dev
# VISSIM runs. -AllowConcurrentDev (V4 beside V5, D-A): at most one other dev VISSIM and total <= 2. With one dev
# VISSIM the queue's limit is 4 (SeatFree: min(4, 3 + min(1, dev))), so a second dev at total 3 would compete with
# the queue for its third seat (and a VISSIM counts as dev only once its title shows the network): total <= 2
# leaves that seat to the queue. Total stays <= 4. The title carries sdmpc31_<Name>.inpx: this run counts as dev.
#
# Exit codes: 0 ok, 1 watchdog failed, 2 arguments, 3 freeze/plan refused, 4 network, 5 no seat, 6 preflight,
# 7 the run's provenance differs from the launch plan.
# Every line also goes to <run folder>\launch_<Name>.log; watch_sdmpc.py ends on its 'EXIT ' line.
[CmdletBinding(PositionalBinding=$false)]
param(
  [Parameter(Mandatory=$true)][string]$Tuning,
  [Parameter(Mandatory=$true)][string]$Name,
  [Parameter(Mandatory=$true)][int]$SimPeriod,
  [Parameter(Mandatory=$true)][int]$Seed,
  [ValidateSet('wu-link','no-control')][string]$Controller = 'wu-link',
  [string]$GroundTruthWindows = '',
  [int]$StallSec = 2400,
  [int]$WaitSeatMinutes = 0,
  [switch]$AllowConcurrentDev,
  [switch]$PreflightOnly,
  [switch]$Freeze,
  [string]$FrozenRoot = 'D:\VISSIM-merge\frozen',
  [string]$FreezeTool = 'D:\VISSIM-merge\tools\freeze_worktree.ps1',
  [string]$RunsRoot = 'D:\VISSIM_runs\20260924_sdmpc31',
  [string]$PrepareNetworkTool = 'D:\VISSIM-merge\tools\prepare_sdmpc31_network.py',
  [string]$Python = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe',
  [string]$DepRoot = 'C:\Users\TRLAB\Documents\ChatGPT\VISSIM\.review-deps',
  [string]$SeatOverride = ''   # TEST ONLY: 'total,dev' replaces Get-Process; refused unless N31_LAUNCHER_TEST=1
)
$ErrorActionPreference = 'Continue'
$DevPattern = 'obs150|sdmpc|probe'
$ToolsRel = 'diagnostics\sdmpc_n31_20260924\tools'
$script:LogPath = $null
$script:Pending = @()

function Log([string]$Message) {
  # Straight to stdout, not the pipeline: helper functions below return values and must not carry log lines.
  $line = '{0}  {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message
  [Console]::Out.WriteLine($line)
  if ($script:LogPath) { [IO.File]::AppendAllText($script:LogPath, $line + "`r`n") } else { $script:Pending += $line }
}
function Stop-Launch([int]$Code, [string]$Why) {
  Log ("REFUSED code={0} {1}" -f $Code, $Why)
  Log ("EXIT {0} code={1}" -f $Name, $Code)
  exit $Code
}
function Get-SeatState {
  if ($SeatOverride) {
    $parts = $SeatOverride -split ','
    return [pscustomobject]@{ total = [int]$parts[0]; dev = [int]$parts[1]; list = @('override ' + $SeatOverride) }
  }
  $procs = @(Get-Process -Name 'VISSIM*' -ErrorAction SilentlyContinue)
  [pscustomobject]@{
    total = $procs.Count
    dev = @($procs | Where-Object { $_.MainWindowTitle -match $DevPattern }).Count
    list = @($procs | ForEach-Object { '{0} start={1:o} title={2}' -f $_.Id, $_.StartTime, $_.MainWindowTitle })
  }
}
function Test-SeatOk($Seat) {
  if ($AllowConcurrentDev) { return ($Seat.total -le 2 -and $Seat.dev -le 1) }
  return ($Seat.total -le 3 -and $Seat.dev -eq 0)
}
function Wait-Seat {
  $deadline = (Get-Date).AddMinutes($WaitSeatMinutes)
  while ($true) {
    $seat = Get-SeatState
    if (Test-SeatOk $seat) { return $seat }
    if ((Get-Date) -ge $deadline) { return $seat }
    Start-Sleep -Seconds 20
  }
}
function Invoke-Tool([string]$Label, [string[]]$Arguments) {
  # Native call; stderr lines are merged as text (Windows PowerShell 5.1 wraps them as ErrorRecords).
  $lines = @(& $Python -B @Arguments 2>&1 | ForEach-Object { "$_" })
  $code = $LASTEXITCODE
  foreach ($l in $lines) { if ($l.Trim()) { Log ("{0} {1}" -f $Label, $l) } }
  return [pscustomobject]@{ code = $code; lines = $lines }
}
function Invoke-Watchdog([string]$OutDir, [switch]$Preflight) {
  $a = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $plan.watchdog,
    '-Name', $Name, '-OutDir', $OutDir, '-Network', $plan.network_file,
    '-VbsConfig', $plan.runner_config.path, '-DemandProfile', $plan.runner_files.DemandProfile.path,
    '-Mapping', $plan.runner_files.Mapping.path, '-Calibration', $plan.runner_files.Calibration.path,
    '-Tuning', $plan.tuning.path, '-UrbanInputGateMap', $plan.runner_files.UrbanInputGateMap.path,
    '-VehicleInputRoles', $plan.runner_files.VehicleInputRoles.path,
    '-Controller', $plan.controller, '-WarmupController', $plan.warmup_controller,
    '-SimPeriod', [string]$plan.sim_period, '-ControlIntervalSec', [string]$plan.control_interval_sec,
    '-ControlStartSec', [string]$plan.control_start_sec, '-Seed', [string]$plan.seed,
    '-StateLogIntervalSec', [string]$plan.state_log_interval_sec, '-StallSec', [string]$plan.stall_sec,
    '-StartupStallSec', [string]$plan.startup_stall_sec, '-MaxAttempts', '1', '-NoGlobalKill')
  if ($plan.gt_text) { $a += @('-GroundTruthWindows', $plan.gt_text) }
  if ($Preflight) { $a += '-PreflightOnly' }
  Log ("WATCHDOG_ARGS {0}" -f ($a[4..($a.Count - 1)] -join ' '))
  & powershell @a 2>&1 | ForEach-Object { Log ("WD {0}" -f "$_") }
  return $LASTEXITCODE
}

# ------------------------------------------------------------------ arguments, FRZ
$tuningPath = $Tuning
if (-not [IO.Path]::IsPathRooted($tuningPath)) { $tuningPath = Join-Path (Get-Location).Path $tuningPath }
$tuningPath = [IO.Path]::GetFullPath($tuningPath)
Log ("LAUNCH name={0} tuning={1} sim_period={2} seed={3} controller={4} gt={5} preflight_only={6} vissim_now={7}" -f `
  $Name, $tuningPath, $SimPeriod, $Seed, $Controller, $(if ($GroundTruthWindows) { $GroundTruthWindows } else { '-' }),
  [bool]$PreflightOnly, (Get-SeatState).total)
if ($SeatOverride -and $env:N31_LAUNCHER_TEST -ne '1') { Stop-Launch 2 '-SeatOverride is for the launcher tests only (N31_LAUNCHER_TEST=1)' }
if (-not (Test-Path -LiteralPath $tuningPath -PathType Leaf)) { Stop-Launch 2 "tuning file missing: $tuningPath" }
function Find-FrozenRoot([string]$Path) {
  $dir = Split-Path -Parent $Path
  while ($dir) {
    if (Test-Path -LiteralPath (Join-Path $dir 'FREEZE.json') -PathType Leaf) { return $dir }
    $parent = Split-Path -Parent $dir
    if ($parent -eq $dir) { break }
    $dir = $parent
  }
  return $null
}
$frz = Find-FrozenRoot $tuningPath

# ------------------------------------------------------------------ seat pre-check (before freezing or claiming the name)
if (-not $PreflightOnly) {
  $seat = Wait-Seat
  Log ("SEAT total={0} dev={1} ok={2} allow_concurrent_dev={3}" -f $seat.total, $seat.dev, (Test-SeatOk $seat), [bool]$AllowConcurrentDev)
  if (-not (Test-SeatOk $seat)) { foreach ($p in $seat.list) { Log ("  VISSIM {0}" -f $p) }; Stop-Launch 5 'NO_SEAT' }
}

# ------------------------------------------------------------------ -Freeze: freeze the worktree, relaunch the tuning from the copy
if ($Freeze) {
  if ($frz) { Stop-Launch 2 "the tuning is already inside the frozen tree $frz; drop -Freeze" }
  $top = @(& git -C (Split-Path -Parent $tuningPath) rev-parse --show-toplevel 2>$null)
  if ($LASTEXITCODE -ne 0 -or $top.Count -ne 1) { Stop-Launch 3 "-Freeze: the tuning is not inside a git worktree: $tuningPath" }
  $top = [IO.Path]::GetFullPath($top[0]).TrimEnd('\')
  if (-not $tuningPath.StartsWith($top + '\', [StringComparison]::OrdinalIgnoreCase)) { Stop-Launch 3 "-Freeze: $tuningPath is not under $top" }
  $tuningRel = $tuningPath.Substring($top.Length + 1)
  if (-not (Test-Path -LiteralPath $FreezeTool -PathType Leaf)) { Stop-Launch 3 "-Freeze: freeze tool missing: $FreezeTool" }
  Log ("FREEZE_WORKTREE source={0} frozen_root={1}" -f $top, $FrozenRoot)
  $frozenLines = @(& powershell -NoProfile -ExecutionPolicy Bypass -File $FreezeTool -Source $top -FrozenRoot $FrozenRoot -Python $Python 2>&1 |
    ForEach-Object { "$_" })
  $freezeCode = $LASTEXITCODE
  foreach ($l in $frozenLines) { if ($l.Trim()) { Log ("FREEZE_TOOL {0}" -f $l) } }
  $frzLine = @($frozenLines | Where-Object { $_ -match '^FRZ=(.+)$' })
  if ($freezeCode -ne 0 -or $frzLine.Count -ne 1) { Stop-Launch 3 ("-Freeze: freeze_worktree.ps1 failed (exit={0})" -f $freezeCode) }
  $tuningPath = Join-Path ($frzLine[0].Substring(4).Trim()) $tuningRel
  if (-not (Test-Path -LiteralPath $tuningPath -PathType Leaf)) { Stop-Launch 3 "-Freeze: the frozen copy lacks the tuning: $tuningPath" }
  $frz = Find-FrozenRoot $tuningPath
  Log ("TUNING {0}" -f $tuningPath)
}
if (-not $frz) { Stop-Launch 3 'the tuning is not inside a frozen tree (no FREEZE.json above it); run freeze_worktree.ps1 and launch from FRZ, or pass -Freeze' }
Set-Location -LiteralPath $frz
$toolsDir = Join-Path $frz $ToolsRel
Log ("FRZ {0}" -f $frz)

# ------------------------------------------------------------------ freeze and plan
$r = Invoke-Tool 'FREEZE' @((Join-Path $toolsDir 'freeze_manifest.py'), 'verify', $frz)
if ($r.code -ne 0) { Stop-Launch 3 'FREEZE.json verification failed' }
$planArgs = @((Join-Path $toolsDir 'launch_plan.py'), 'plan', '--tuning', $tuningPath, '--name', $Name,
  '--sim-period', [string]$SimPeriod, '--seed', [string]$Seed, '--controller', $Controller,
  '--stall-sec', [string]$StallSec, '--runs-root', $RunsRoot)
# Windows PowerShell 5.1 drops an empty-string argument to a native command, so an empty
# '--gt-windows' value would swallow the next option. Pass it only when there is one.
if ($GroundTruthWindows) { $planArgs += @('--gt-windows', $GroundTruthWindows) }
if ($PreflightOnly) { $planArgs += '--preflight' }
$r = Invoke-Tool 'PLAN' $planArgs
$planLine = @($r.lines | Where-Object { $_ -match '^LAUNCH_PLAN_OK plan=(.+)$' })
if ($r.code -ne 0 -or $planLine.Count -ne 1) { Stop-Launch 3 'launch plan refused' }
$planPath = ([regex]::Match($planLine[0], '^LAUNCH_PLAN_OK plan=(.+)$')).Groups[1].Value.Trim()
$plan = Get-Content -LiteralPath $planPath -Raw -Encoding UTF8 | ConvertFrom-Json
$script:LogPath = Join-Path $plan.out_dir ("launch_{0}.log" -f $Name)
foreach ($line in $script:Pending) { [IO.File]::AppendAllText($script:LogPath, $line + "`r`n") }
$script:Pending = @()
Log ("RUN_DIR {0}" -f $plan.out_dir)

# ------------------------------------------------------------------ network copy (WP-E tool) + independent check
if (-not (Test-Path -LiteralPath $PrepareNetworkTool -PathType Leaf)) { Stop-Launch 4 "network copy tool missing: $PrepareNetworkTool" }
$r = Invoke-Tool 'NETCOPY' @($PrepareNetworkTool, '--name', $Name, '--out-dir', $plan.network_dir, '--root', $frz)
if ($r.code -ne 0) { Stop-Launch 4 ("network copy tool exit={0}" -f $r.code) }
$r = Invoke-Tool 'NETWORK' @((Join-Path $toolsDir 'launch_plan.py'), 'verify-network', '--plan', $planPath)
if ($r.code -ne 0) { Stop-Launch 4 'network copy differs from the manifest pins' }

# ------------------------------------------------------------------ environment: only what the plan names
Get-ChildItem Env: | Where-Object Name -like 'RW_*' | ForEach-Object { Remove-Item -LiteralPath ('Env:' + $_.Name) }
$env:PYTHONPATH = "$DepRoot\sdmpc;$DepRoot\sdmpc-numba"
$env:OMP_NUM_THREADS = '1'; $env:OPENBLAS_NUM_THREADS = '1'; $env:MKL_NUM_THREADS = '1'
$env:PYTHONUTF8 = '1'
# RW_PYTHON: python the runner calls. RW_OFFSET_WRITER: the config declares offset_writer=experiment and
# offset_promotion.validate_experiment_declaration also demands this env value. The watchdog sets the obs150 env.
$env:RW_PYTHON = $Python
$env:RW_OFFSET_WRITER = 'experiment'
Log ("ENV PYTHONPATH={0} RW_PYTHON={1} RW_OFFSET_WRITER=experiment" -f $env:PYTHONPATH, $env:RW_PYTHON)

# ------------------------------------------------------------------ preflight: the watchdog's provenance must equal the plan
$preDir = Join-Path $plan.out_dir 'preflight'
$rc = Invoke-Watchdog $preDir -Preflight
if ($rc -ne 0) { Stop-Launch 6 ("watchdog -PreflightOnly exit={0}" -f $rc) }
$r = Invoke-Tool 'PREFLIGHT' @((Join-Path $toolsDir 'launch_plan.py'), 'check-provenance', '--plan', $planPath,
  '--provenance', (Join-Path $preDir ("run_provenance_{0}.json" -f $Name)))
if ($r.code -ne 0) { Stop-Launch 6 'preflight provenance differs from the launch plan' }
if ($PreflightOnly) {
  Log 'PREFLIGHT_ONLY done; no VISSIM started'
  Log ("EXIT {0} code=0" -f $Name)
  exit 0
}

# ------------------------------------------------------------------ launch
$seat = Wait-Seat
Log ("SEAT total={0} dev={1} ok={2}" -f $seat.total, $seat.dev, (Test-SeatOk $seat))
if (-not (Test-SeatOk $seat)) {
  [IO.File]::WriteAllText((Join-Path $plan.out_dir 'NOT_LAUNCHED.txt'), "Seat taken after the plan; no VISSIM was started.`r`n")
  foreach ($p in $seat.list) { Log ("  VISSIM {0}" -f $p) }
  Stop-Launch 5 'NO_SEAT at launch (run folder claimed, nothing started; use a new -Name or remove the folder)'
}
$t0 = Get-Date
Log ("START {0} out_dir={1}" -f $Name, $plan.out_dir)
$rc = Invoke-Watchdog $plan.out_dir
Log ("WATCHDOG_EXIT code={0} wall_sec={1}" -f $rc, [math]::Round(((Get-Date) - $t0).TotalSeconds, 0))
$prov = Join-Path $plan.out_dir ("run_provenance_{0}.json" -f $Name)
$provOk = $false
if (Test-Path -LiteralPath $prov) {
  $r = Invoke-Tool 'PROVENANCE' @((Join-Path $toolsDir 'launch_plan.py'), 'check-provenance', '--plan', $planPath, '--provenance', $prov)
  $provOk = ($r.code -eq 0)
} else { Log 'PROVENANCE missing' }
# The run is only the planned run if its own provenance says so (exit 7 otherwise, even when VISSIM finished).
$code = $(if ($rc -ne 0) { 1 } elseif (-not $provOk) { 7 } else { 0 })
Log ("EXIT {0} code={1}" -f $Name, $code)
exit $code
