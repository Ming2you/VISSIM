<#
Run a seed-paired 8-seg P-Stack sweep through the single-case VISSIM watchdog.

Each case uses scripts/run_8seg_single_watchdog.ps1, so no-progress detection,
VISSIM/cscript termination, and retry behavior stay in one place. The wrapper
writes a batch_manifest.json compatible with analyze_vissim_controller_stress_sweep.py.
#>
param(
  [string]$Cell = "155w",
  [string[]]$Seeds = @("11","13","29","47"),
  [string[]]$Controllers = @("no-control","stackelberg-wu-metered"),
  [string]$OutDir = "",
  [int]$SimPeriod = 10800,
  [int]$ControlIntervalSec = 180,
  [string]$DemandProfile = "sym",
  [double]$UrbanWestEastRatio = 1.0,
  [double]$UrbanVph = 0.0,
  [double]$FreewayVph = 0.0,
  [string]$Tuning = "",
  [string]$Pulse = "0.5:3600:300:3600:300",
  [int]$WarmupSec = 3600,
  [int]$StallSec = 300,
  [int]$MaxAttempts = 3,
  [int]$DoneRows = 2100
)

$ErrorActionPreference = "Continue"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$single = Join-Path $repo "scripts\run_8seg_single_watchdog.ps1"
$analyzer = Join-Path $repo "scripts\analyze_vissim_controller_stress_sweep.py"
$diagnoser = Join-Path $repo "scripts\diagnose_controller_seed_batch.py"
$canary = Join-Path $repo "scripts\component_canary.py"

if ($OutDir -eq "") {
  $safeCell = $Cell.ToLower().Replace("_", "")
  $OutDir = Join-Path $repo "evaluation\runs\8seg_pstack_${safeCell}_4seed_pair_20260715"
}
if ($Tuning -eq "") {
  $Tuning = Join-Path $repo "evaluation\configs\tuning_turning_ratios_route_manifest_v2_20260715.json"
}

switch ($Cell.ToLower().Replace("_", "")) {
  "155w" {
    if ($UrbanVph -le 0.0) { $UrbanVph = 1008.0 }
    if ($FreewayVph -le 0.0) { $FreewayVph = 2621.0 }
  }
  "190w" {
    if ($UrbanVph -le 0.0) { $UrbanVph = 1235.0 }
    if ($FreewayVph -le 0.0) { $FreewayVph = 3213.0 }
  }
  default {
    if ($UrbanVph -le 0.0 -or $FreewayVph -le 0.0) {
      throw "Unknown Cell '$Cell'. Pass -UrbanVph and -FreewayVph, or use 155w/190w."
    }
  }
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$manifestPath = Join-Path $OutDir "batch_manifest.json"
$manifest = @()
if (Test-Path $manifestPath) {
  $existing = Get-Content $manifestPath -Raw | ConvertFrom-Json
  if ($existing) {
    foreach ($item in @($existing)) { $manifest += $item }
  }
}

function Controller-ShortName([string]$Controller) {
  if ($Controller -eq "stackelberg-wu-metered") { return "pstack" }
  return $Controller.Replace("-", "_")
}

function Write-Manifest {
  $manifest | ConvertTo-Json -Depth 8 | Set-Content -Path $manifestPath -Encoding UTF8
}

function Existing-Manifest-Item([string]$CaseId) {
  foreach ($item in $manifest) {
    if ([string]$item.case_id -eq $CaseId) { return $item }
  }
  return $null
}

function Parse-Seeds([string[]]$RawSeeds) {
  $values = @()
  foreach ($token in $RawSeeds) {
    foreach ($part in ([string]$token -split ",")) {
      $trimmed = $part.Trim()
      if ($trimmed -ne "") {
        $values += [int]$trimmed
      }
    }
  }
  return $values
}

$SeedList = Parse-Seeds $Seeds

foreach ($seed in $SeedList) {
  foreach ($controller in $Controllers) {
    $short = Controller-ShortName $controller
    $caseId = "${short}_${Cell}_seed${seed}"
    $stateCsv = Join-Path $OutDir "state_$caseId.csv"
    $actionCsv = Join-Path $OutDir "action_$caseId.csv"
    $decisionDir = Join-Path $OutDir "decisions_$caseId"
    $stdout = Join-Path $OutDir "runlog_$caseId.txt"
    $stderr = Join-Path $OutDir "runlog_$caseId.txt.err"

    $started = Get-Date
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $single `
      -Name $caseId `
      -OutDir $OutDir `
      -SimPeriod $SimPeriod `
      -UrbanVph $UrbanVph `
      -FreewayVph $FreewayVph `
      -ControlIntervalSec $ControlIntervalSec `
      -Seed $seed `
      -DemandProfile $DemandProfile `
      -UrbanWestEastRatio $UrbanWestEastRatio `
      -Controller $controller `
      -Tuning $Tuning `
      -Pulse $Pulse `
      -StallSec $StallSec `
      -MaxAttempts $MaxAttempts `
      -DoneRows $DoneRows
    $returnCode = $LASTEXITCODE
    $elapsed = [int]((Get-Date) - $started).TotalSeconds

    $item = [ordered]@{
      case_id = $caseId
      controller = $controller
      scenario_id = $Cell
      category = "pstack_seed_pair"
      demand_profile = $DemandProfile
      returncode = $returnCode
      elapsed_sec = $elapsed
      timed_out = $false
      timeout_reason = ""
      case_timeout_sec = 0
      startup_timeout_sec = $StallSec
      first_progress_sec = 0
      last_progress_sec = 0
      progress_marker_count = 0
      sim_period_sec = $SimPeriod
      urban_volume_vph = $UrbanVph
      freeway_volume_vph = $FreewayVph
      urban_west_east_ratio = $UrbanWestEastRatio
      control_interval_sec = $ControlIntervalSec
      rand_seed = $seed
      state_csv = $stateCsv
      action_csv = $actionCsv
      decision_dir = $decisionDir
      stdout = $stdout
      stderr = $stderr
      tuning_json = $Tuning
    }

    $prev = Existing-Manifest-Item $caseId
    if ($prev) {
      $manifest = @($manifest | Where-Object { [string]$_.case_id -ne $caseId })
    }
    $manifest += [pscustomobject]$item
    Write-Manifest

    if ($returnCode -ne 0) {
      Write-Host "FAIL $caseId returncode=$returnCode"
      exit $returnCode
    }
  }
}

python $analyzer --out-dir $OutDir --warmup-sec $WarmupSec
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python $diagnoser --out-dir $OutDir --calibration-md (Join-Path $repo "evaluation\calibration\prediction_audit_bayes_update_8seg_pfo_green_frozen_smoke_20260715.md")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$pstackDirs = @()
foreach ($seed in $SeedList) {
  $dir = Join-Path $OutDir "decisions_pstack_${Cell}_seed${seed}"
  if (Test-Path $dir) {
    $pstackDirs += $dir
  }
}
if ($pstackDirs.Count -gt 0) {
  python $canary @pstackDirs --active-start-sec $WarmupSec --out-json (Join-Path $OutDir "component_canary_pstack_${Cell}_4seed.json") --out-md (Join-Path $OutDir "component_canary_pstack_${Cell}_4seed.md")
  exit $LASTEXITCODE
}
exit 0
