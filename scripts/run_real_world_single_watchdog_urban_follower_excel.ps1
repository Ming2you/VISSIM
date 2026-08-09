<#
Run one real-world Gaepo modi VISSIM controller case with a no-progress watchdog.

Progress is the newest mtime among the run log, state CSV, action CSV, and
decision action JSONs. If nothing moves for StallSec seconds, cscript/VISSIM are
killed and the case is retried up to MaxAttempts.
#>
param(
  [Parameter(Mandatory=$true)][string]$Name,
  [string]$Network = "",
  [string]$OutDir = "",
  [int]$SimPeriod = 1800,
  [int]$ControlIntervalSec = 60,
  [int]$Seed = 13,
  [string]$Controller = "pstack-flagship",
  [string]$Tuning = "",
  [string]$Calibration = "",
  [string]$Mapping = "",
  [int]$ControlStartSec = -1,
  [string]$WarmupController = "no-control",
  [int]$StateLogIntervalSec = 5,
  [double]$DemandScale = 1.0,
  [string]$DemandProfile = "",
  [string]$VehicleInputRoles = "",
  [int]$IncidentLink = 0,
  [int]$IncidentLane = 0,
  [double]$IncidentPos = -1.0,
  [int]$IncidentStartSec = -1,
  [int]$IncidentEndSec = -1,
  [string]$IncidentName = "",
  [string]$NumericalSimRepoRoot = $env:STRICT_NUMERICAL_SIM_REPO,
  [switch]$ForceStepwise,
  [int]$StallSec = 300,
  [int]$MaxAttempts = 3,
  [int]$DoneRows = 0
)

$ErrorActionPreference = "Continue"
$trustedG6Hash = $env:RW_TRUSTED_G6_REPORT_SHA256
$trustedG8Hash = $env:RW_TRUSTED_G8_REPORT_SHA256
$trustedG8Path = $env:RW_TRUSTED_G8_REPORT_PATH
$actionHmacKey = $env:RW_ACTION_HMAC_KEY
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
function Resolve-RepoPath([string]$PathValue) {
  if ($PathValue -eq "") { return "" }
  if ([System.IO.Path]::IsPathRooted($PathValue)) {
    return [System.IO.Path]::GetFullPath($PathValue)
  }
  return [System.IO.Path]::GetFullPath((Join-Path $repo $PathValue))
}

if ($OutDir -eq "") {
  $OutDir = Join-Path $repo "evaluation\runs\real_world_modi_watchdog"
}
$OutDir = Resolve-RepoPath $OutDir
if ($Tuning -eq "") {
  $Tuning = Join-Path $repo "evaluation\configs\real_world_modi_pstack_flagship_20260731.json"
}
$Tuning = Resolve-RepoPath $Tuning
if ($Calibration -eq "") {
  $Calibration = Join-Path $repo "evaluation\calibration\real_world_modi_control_v0_20260719.json"
}
$Calibration = Resolve-RepoPath $Calibration
if ($Mapping -eq "") {
  $Mapping = Join-Path $repo "evaluation\real_world_modi_control_urban_follower_excel_20260731\control_mapping_urban_follower_excel_20260731.json"
}
$Mapping = Resolve-RepoPath $Mapping
if ($VehicleInputRoles -eq "") {
  $VehicleInputRoles = Join-Path $repo "evaluation\real_world_modi_inventory\vehicle_input_roles.csv"
}
$VehicleInputRoles = Resolve-RepoPath $VehicleInputRoles
if ($DemandProfile -ne "") {
  $DemandProfile = Resolve-RepoPath $DemandProfile
}
if ($ControlIntervalSec -le 0 -or ($ControlIntervalSec % 10) -ne 0) {
  throw "ControlIntervalSec must be a positive multiple of the 10s ramp-meter cycle. Got $ControlIntervalSec."
}
if ($StateLogIntervalSec -le 0) {
  throw "StateLogIntervalSec must be positive. Got $StateLogIntervalSec."
}

$runner = Join-Path $repo "scripts\run_real_world_stackelberg_controller.vbs"
if ($Network -eq "") {
  $Network = Join-Path $repo "network\real_world_gaepo_modi\modi.inpx"
}
$net = Resolve-RepoPath $Network
$adapter = Join-Path $repo "evaluation\controllers\vissim_stackelberg_adapter.py"
$vbsConfig = Join-Path $repo "evaluation\generated\real_world_modi_control_config_urban_follower_excel_20260731.vbs"

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$progress = Join-Path $OutDir "WATCHDOG_PROGRESS.txt"

function Log($m) {
  $line = ("{0}  {1}" -f (Get-Date -Format "MM-dd HH:mm:ss"), $m)
  for ($r = 0; $r -lt 5; $r++) {
    try { [System.IO.File]::AppendAllText($progress, $line + "`r`n"); break }
    catch { Start-Sleep -Milliseconds 200 }
  }
  Write-Host $line
}

function Kill-Vissim {
  Get-Process -Name "VISSIM200","VISSIM200CL","cscript" -ErrorAction SilentlyContinue |
    Stop-Process -Force -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 3
}

function Clear-DecisionDir([string]$Dir) {
  if (-not (Test-Path $Dir)) {
    New-Item -ItemType Directory -Force -Path $Dir | Out-Null
    return
  }
  Get-ChildItem -LiteralPath $Dir -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like "action_*.json" -or $_.Name -like "action_*.csv" -or $_.Name -like "state_*.json" } |
    Remove-Item -Force -ErrorAction SilentlyContinue
}

function Normalize-ProcessPathEnv {
  $pathValue = [Environment]::GetEnvironmentVariable("Path", "Process")
  if ([string]::IsNullOrWhiteSpace($pathValue)) {
    $pathValue = [Environment]::GetEnvironmentVariable("PATH", "Process")
  }
  [Environment]::SetEnvironmentVariable("PATH", $null, "Process")
  [Environment]::SetEnvironmentVariable("Path", $null, "Process")
  if (-not [string]::IsNullOrWhiteSpace($pathValue)) {
    [Environment]::SetEnvironmentVariable("Path", $pathValue, "Process")
  }
}

function Q($s) { '"' + $s + '"' }

$stateCsv = Join-Path $OutDir "state_$Name.csv"
$actionCsv = Join-Path $OutDir "action_$Name.csv"
$bottleneckLinkCsv = Join-Path $OutDir "bottleneck_links_$Name.csv"
$bottleneckSegmentCsv = Join-Path $OutDir "bottleneck_segments_$Name.csv"
$decisionDir = Join-Path $OutDir "decisions_$Name"
$log = Join-Path $OutDir "runlog_$Name.txt"
New-Item -ItemType Directory -Force -Path $decisionDir | Out-Null

function Archive-AttemptOutputs([int]$Attempt) {
  $archive = Join-Path $OutDir ("attempt_{0:00}_{1}" -f $Attempt, $Name)
  New-Item -ItemType Directory -Force -Path $archive | Out-Null
  foreach ($path in @($stateCsv, $actionCsv, $bottleneckLinkCsv, $bottleneckSegmentCsv, $log, "$log.err")) {
    if (Test-Path $path) {
      Copy-Item -LiteralPath $path -Destination (Join-Path $archive ([System.IO.Path]::GetFileName($path))) -Force -ErrorAction SilentlyContinue
    }
  }
  if (Test-Path $decisionDir) {
    $decisionArchive = Join-Path $archive ([System.IO.Path]::GetFileName($decisionDir))
    Copy-Item -LiteralPath $decisionDir -Destination $decisionArchive -Recurse -Force -ErrorAction SilentlyContinue
  }
}

if ($DoneRows -gt 0 -and (Test-Path $stateCsv)) {
  $rows = (Get-Content $stateCsv | Measure-Object -Line).Lines
  if ($rows -ge $DoneRows) {
    Log "SKIP $Name rows=$rows"
    exit 0
  }
}

for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
  Kill-Vissim
  Clear-DecisionDir $decisionDir
  $argline = "//nologo " + (Q $runner) + " " + (Q $net) + " " + (Q $stateCsv) + " " + (Q $actionCsv) + " " + (Q $decisionDir) +
    " $SimPeriod $ControlIntervalSec $Seed " + (Q $adapter) + " " + (Q $Calibration) + " " + (Q $Tuning) + " " + (Q $Mapping) +
    " " + (Q $Controller) + " $ControlStartSec " + (Q $WarmupController) + " " + (Q $vbsConfig)
  $argline = $argline + " $StateLogIntervalSec"
  $argline = $argline + " $DemandScale"
  $argline = $argline + " " + (Q $DemandProfile) + " " + (Q $VehicleInputRoles)
  $argline = $argline + " $IncidentLink $IncidentLane $IncidentPos $IncidentStartSec $IncidentEndSec " + (Q $IncidentName)
  $argline = $argline + " " + (Q $NumericalSimRepoRoot)

  $t0 = Get-Date
  Normalize-ProcessPathEnv
  $oldForceStepwise = [Environment]::GetEnvironmentVariable("RW_FORCE_STEPWISE", "Process")
  if ($ForceStepwise) {
    [Environment]::SetEnvironmentVariable("RW_FORCE_STEPWISE", "1", "Process")
  } else {
    [Environment]::SetEnvironmentVariable("RW_FORCE_STEPWISE", $null, "Process")
  }
  $cscriptExe = Join-Path $env:SystemRoot "System32\cscript.exe"
  if (-not (Test-Path $cscriptExe)) { $cscriptExe = "cscript.exe" }
  $proc = Start-Process -FilePath $cscriptExe -ArgumentList $argline -RedirectStandardOutput $log `
    -RedirectStandardError "$log.err" -WorkingDirectory $repo -PassThru -WindowStyle Hidden
  [Environment]::SetEnvironmentVariable("RW_FORCE_STEPWISE", $oldForceStepwise, "Process")
  if (-not $proc -or -not $proc.Id) {
    throw "Failed to start cscript for $Name attempt=$attempt"
  }
  Log "START $Name attempt=$attempt pid=$($proc.Id)"

  while ($true) {
    Start-Sleep -Seconds 20
    if ($proc.HasExited) {
      $done = Select-String -Path $log -Pattern "STAGE=SIM_DONE" -Quiet -ErrorAction SilentlyContinue
      if ($done) {
        Log "OK $Name attempt=$attempt elapsed=$([int]((Get-Date)-$t0).TotalSeconds)s"
        exit 0
      }
      Log "EXIT_NO_DONE $Name attempt=$attempt"
      Archive-AttemptOutputs $attempt
      break
    }

    $lastT = $proc.StartTime
    $signals = @()
    $signals += Get-Item $log -ErrorAction SilentlyContinue
    $signals += Get-Item $stateCsv -ErrorAction SilentlyContinue
    $signals += Get-Item $actionCsv -ErrorAction SilentlyContinue
    $signals += Get-Item $bottleneckLinkCsv -ErrorAction SilentlyContinue
    $signals += Get-Item $bottleneckSegmentCsv -ErrorAction SilentlyContinue
    $signals += Get-ChildItem (Join-Path $decisionDir "action_*.json") -ErrorAction SilentlyContinue |
      Sort-Object LastWriteTime -Descending | Select-Object -First 1
    foreach ($signal in $signals) {
      if ($signal -and $signal.LastWriteTime -gt $lastT) {
        $lastT = $signal.LastWriteTime
      }
    }
    $idle = [int]((Get-Date) - $lastT).TotalSeconds
    if ($idle -gt $StallSec) {
      Log "WATCHDOG_KILL $Name attempt=$attempt idle=${idle}s"
      try { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue } catch {}
      Kill-Vissim
      Archive-AttemptOutputs $attempt
      break
    }
  }
}

Log "FAIL $Name after $MaxAttempts attempts"
exit 1
