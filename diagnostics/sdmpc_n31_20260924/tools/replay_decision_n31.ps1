# Re-run one native obs150 (coupled-lane-plant/v2) decision offline (plan D2). PowerShell only. No VISSIM.
#
#   python -B <tools>\make_replay_state_v2.py prepare <run>\decisions_<Name> 900 <ReplayDir>
#   powershell -NoProfile -ExecutionPolicy Bypass -File <tools>\replay_decision_n31.ps1 -ReplayDir <ReplayDir>
#
# replay_decision.ps1 generalised to the v2 runner. Nothing is typed by hand; everything comes from the run:
#   Root       run_provenance.workspace_root (= the frozen tree FRZ the run used). Its FREEZE.json is re-verified.
#              -Root <W> replays a code change: every provenance path inside the run's root is rebased onto -Root
#              (same relative path), so code, tuning, mapping and pins all come from one tree.
#   Arguments  exactly the VBS call (run_real_world_stackelberg_controller.vbs:1114-1135): --state-json (the
#              isolated state), --mapping-json/--calibration-json/--tuning-json from provenance files, the
#              --detector-mapping-json the runner config declares (RW_DETECTOR_MAPPING_PATH, relative to Root),
#              --controller from launch_plan.json (warmup controller below control_start_sec, VBS:1110-1112),
#              --previous-action-json, --mode only if RW_ADAPTER_MODE was set.
#   Env        RW_* cleared, then exactly the provenance env; PYTHONPATH/threads as run_sdmpc_n31.ps1.
# The previous action is read from the RUN folder (its .applied receipt binds the absolute csv path, sdmpc.py:461-470);
# its bytes must still equal the hard links make_replay_state_v2.py kept in <ReplayDir>\previous.
# Outputs go to <ReplayDir>\replay\; derived_<T>.json lands in <ReplayDir>\obs150 (the state's obs150.directory).
# Then make_replay_state_v2.py compare. Exit: 0 identical, 1 adapter failed, 2 replay differs, 3 refused.
[CmdletBinding(PositionalBinding=$false)]
param(
  [Parameter(Mandatory=$true)][string]$ReplayDir,
  [string]$Root = '',
  [string]$Controller = '',
  [string]$ExtraPythonPath = '',
  [switch]$SkipFreezeVerify,
  [string]$DepRoot = 'C:\Users\TRLAB\Documents\ChatGPT\VISSIM\.review-deps'
)
$ErrorActionPreference = 'Continue'
$Tools = $PSScriptRoot
function Refuse([string]$Why) { Write-Output "REPLAY_REFUSED $Why"; exit 3 }
function Sha([string]$p) { (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() }
function Same([string]$a, [string]$b) { [IO.Path]::GetFullPath($a).TrimEnd('\').ToLowerInvariant() -eq [IO.Path]::GetFullPath($b).TrimEnd('\').ToLowerInvariant() }

$ReplayDir = [IO.Path]::GetFullPath($ReplayDir)
$manifestPath = Join-Path $ReplayDir 'replay_manifest.json'
if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) { Refuse "no replay_manifest.json in $ReplayDir (run make_replay_state_v2.py prepare)" }
$m = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($m.schema -ne 'sdmpc31-replay-state/v1') { Refuse "unsupported replay manifest schema $($m.schema)" }
$sec = [int]$m.sim_sec
$s = '{0:D6}' -f $sec
$dec = [string]$m.source_decisions
$runDir = Split-Path -Parent $dec
$runName = (Split-Path -Leaf $dec) -replace '^decisions_', ''
$provPath = Join-Path $runDir ("run_provenance_{0}.json" -f $runName)
if (-not (Test-Path -LiteralPath $provPath -PathType Leaf)) { Refuse "run provenance missing: $provPath" }
$prov = Get-Content -LiteralPath $provPath -Raw -Encoding UTF8 | ConvertFrom-Json
$runRoot = [string]$prov.workspace_root
if (-not $Root) { $Root = $runRoot }
$Root = [IO.Path]::GetFullPath($Root)
$rebase = -not (Same $Root $runRoot)
function Rebase([string]$p) {
  # A provenance path inside the run's root -> the same relative path under -Root.
  if (-not $rebase -or -not $p) { return $p }
  $full = [IO.Path]::GetFullPath($p); $base = [IO.Path]::GetFullPath($runRoot).TrimEnd('\') + '\'
  if ($full.ToLowerInvariant().StartsWith($base.ToLowerInvariant())) { return (Join-Path $Root $full.Substring($base.Length)) }
  return $p
}

# ------------------------------------------------------------------ code tree
$freeze = Join-Path $Root 'FREEZE.json'
if (Test-Path -LiteralPath $freeze -PathType Leaf) {
  if (-not $SkipFreezeVerify) {
    $lines = @(& $prov.env.RW_PYTHON -B (Join-Path $Root 'diagnostics\sdmpc_n31_20260924\tools\freeze_manifest.py') verify $Root 2>&1 | ForEach-Object { "$_" })
    $lines | ForEach-Object { Write-Output "FREEZE $_" }
    if ($LASTEXITCODE -ne 0) { Refuse "FREEZE.json verification failed for $Root" }
  } else { Write-Output "FREEZE verify skipped (-SkipFreezeVerify) root=$Root" }
} else { Write-Output "ROOT_NOT_FROZEN root=$Root (code-change replay)" }
if ($rebase) { Write-Output "REBASE provenance root $runRoot -> $Root" }

# ------------------------------------------------------------------ previous action (read from the run folder)
$prevArg = $null
if ($null -ne $m.previous_sec) {
  $p = '{0:D6}' -f [int]$m.previous_sec
  $prevArg = Join-Path $dec ("action_{0}.json" -f $p)
  foreach ($prop in $m.evidence.previous.PSObject.Properties) {
    $orig = [string]$prop.Value.source
    if (-not (Test-Path -LiteralPath $orig -PathType Leaf)) { Refuse "previous action file vanished: $orig" }
    if ((Sha $orig) -ne [string]$prop.Value.sha256) { Refuse "previous action file changed since prepare: $orig" }
  }
  if (-not (Test-Path -LiteralPath $prevArg -PathType Leaf)) { Refuse "previous action missing: $prevArg" }
}

# ------------------------------------------------------------------ controller (VBS:1109-1113)
if (-not $Controller) {
  $planPath = Join-Path $runDir 'launch_plan.json'
  if (-not (Test-Path -LiteralPath $planPath -PathType Leaf)) { Refuse "no launch_plan.json in $runDir; pass -Controller" }
  $plan = Get-Content -LiteralPath $planPath -Raw -Encoding UTF8 | ConvertFrom-Json
  $Controller = $(if ($sec -lt [int]$plan.control_start_sec) { [string]$plan.warmup_controller } else { [string]$plan.controller })
}

# ------------------------------------------------------------------ adapter arguments (VBS:1114-1135)
$files = $prov.files
$tuning = Rebase ([string]$files.tuning.path)
$mapping = Rebase ([string]$files.control_mapping.path)
$calibration = Rebase ([string]$files.calibration.path)
$runnerConfig = Rebase ([string]$files.generated_vbs_config.path)
$detMapping = ''
foreach ($line in [IO.File]::ReadAllLines($runnerConfig)) {
  $mm = [regex]::Match($line, '^\s*RW_DETECTOR_MAPPING_PATH\s*=\s*"(.*)"\s*$')
  if ($mm.Success) { $detMapping = $mm.Groups[1].Value }
}
$adapter = Join-Path $Root 'evaluation\controllers\vissim_stackelberg_adapter.py'
foreach ($f in @($tuning, $mapping, $calibration, $adapter)) {
  if (-not (Test-Path -LiteralPath $f -PathType Leaf)) { Refuse "missing input: $f" }
}
$out = Join-Path $ReplayDir 'replay'
if (Test-Path -LiteralPath (Join-Path $out ("action_{0}.json" -f $s))) { Refuse "replay output already exists in $out (prepare a new ReplayDir)" }
New-Item -ItemType Directory -Force -Path $out | Out-Null
$a = @($adapter, '--state-json', [string]$m.state.replay,
  '--out-action-json', (Join-Path $out ("action_{0}.json" -f $s)), '--out-action-csv', (Join-Path $out ("action_{0}.csv" -f $s)),
  '--mapping-json', $mapping, '--controller', $Controller)
if ($detMapping) { $a += @('--detector-mapping-json', $detMapping) }
$a += @('--calibration-json', $calibration, '--tuning-json', $tuning)
if ($prevArg) { $a += @('--previous-action-json', $prevArg) }
$mode = [string]$prov.env.RW_ADAPTER_MODE
if ($mode) { $a += @('--mode', $mode) }

# ------------------------------------------------------------------ environment: the run's RW_* and nothing else
Get-ChildItem Env: | Where-Object Name -like 'RW_*' | ForEach-Object { Remove-Item -LiteralPath ('Env:' + $_.Name) }
foreach ($prop in $prov.env.PSObject.Properties) { Set-Item -LiteralPath ('Env:' + $prop.Name) -Value ([string]$prop.Value) }
$env:PYTHONPATH = "$DepRoot\sdmpc;$DepRoot\sdmpc-numba"
if ($ExtraPythonPath) { $env:PYTHONPATH = "$ExtraPythonPath;$env:PYTHONPATH" }
$env:OMP_NUM_THREADS = '1'; $env:OPENBLAS_NUM_THREADS = '1'; $env:MKL_NUM_THREADS = '1'
$env:PYTHONUTF8 = '1'
$python = [string]$prov.env.RW_PYTHON
if (-not $python) { Refuse 'provenance env lacks RW_PYTHON' }

Set-Location -LiteralPath $Root
Write-Output ("REPLAY_START sim_sec={0} controller={1} root={2} previous={3}" -f $sec, $Controller, $Root, $(if ($prevArg) { $prevArg } else { '-' }))
Write-Output ("REPLAY_ARGS {0}" -f (($a | Select-Object -Skip 1) -join ' '))
$t0 = Get-Date
$stdout = Join-Path $out 'adapter_stdout.txt'; $stderr = Join-Path $out 'adapter_stderr.txt'
$proc = Start-Process -FilePath $python -ArgumentList (@('-B') + ($a | ForEach-Object { '"' + ($_ -replace '"', '\"') + '"' })) `
  -WorkingDirectory $Root -RedirectStandardOutput $stdout -RedirectStandardError $stderr -NoNewWindow -Wait -PassThru
$rc = $proc.ExitCode
$wall = [math]::Round(((Get-Date) - $t0).TotalSeconds, 1)
$record = [ordered]@{ schema = 'sdmpc31-replay-run/v1'; sim_sec = $sec; controller = $Controller; root = $Root; run_root = $runRoot
  rebased = $rebase; python = $python; arguments = $a; env = $prov.env; exit_code = $rc; wall_sec = $wall }
[IO.File]::WriteAllText((Join-Path $out 'replay_run.json'), ($record | ConvertTo-Json -Depth 6), [Text.UTF8Encoding]::new($false))
Write-Output "REPLAY_$s exit=$rc wall_sec=$wall"
if ($rc -ne 0) { Get-Content -LiteralPath $stderr -Tail 5 | ForEach-Object { Write-Output "STDERR $_" }; exit 1 }

& $python -B (Join-Path $Tools 'make_replay_state_v2.py') compare $ReplayDir --tuning $tuning 2>&1 | ForEach-Object { Write-Output "$_" }
if ($LASTEXITCODE -ne 0) { exit 2 }
exit 0
