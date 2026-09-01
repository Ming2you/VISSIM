<#
Run one 8-seg VISSIM controller case with a no-progress watchdog.

Progress is the newest mtime among the run log, state CSV, action CSV, and
decision action JSONs. If nothing moves for StallSec seconds, cscript/VISSIM are
killed and the case is retried up to MaxAttempts.
#>
param(
  [Parameter(Mandatory=$true)][string]$Name,
  [string]$OutDir = "",
  [int]$SimPeriod = 10800,
  [double]$UrbanVph = 1235,
  [double]$FreewayVph = 3213,
  [int]$ControlIntervalSec = 180,
  [int]$Seed = 13,
  [string]$DemandProfile = "sym",
  [double]$UrbanWestEastRatio = 1.0,
  [string]$Controller = "pfo",
  [string]$Tuning = "",
  [string]$Pulse = "0.5:3600:300:3600:300",
  [int]$ControlStartSec = -1,
  [string]$WarmupController = "diagnostic-fixed57",
  [int]$StallSec = 300,
  [int]$MaxAttempts = 3,
  [int]$DoneRows = 0
)

$ErrorActionPreference = "Continue"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ($OutDir -eq "") {
  $OutDir = Join-Path $repo "evaluation\runs\8seg_single_watchdog_20260715"
}
if ($Tuning -eq "") {
  $Tuning = Join-Path $repo "evaluation\configs\tuning_turning_ratios_route_manifest_v2_20260715.json"
}
if ($Pulse -in @("none", "off", "false", "0")) {
  $Pulse = ""
}

$runner = Join-Path $repo "scripts\run_stackelberg_vissim_controller_8seg.vbs"
$net = Join-Path $repo "network\modi_eval_vsl_8seg.inpx"
$adapter = Join-Path $repo "evaluation\controllers\vissim_stackelberg_adapter.py"
$calib = Join-Path $repo "evaluation\calibration\vissim_network_calibration_v2_8seg_20260714.json"

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

function Q($s) { '"' + $s + '"' }

$stateCsv = Join-Path $OutDir "state_$Name.csv"
$actionCsv = Join-Path $OutDir "action_$Name.csv"
$decisionDir = Join-Path $OutDir "decisions_$Name"
$log = Join-Path $OutDir "runlog_$Name.txt"
New-Item -ItemType Directory -Force -Path $decisionDir | Out-Null

if ($DoneRows -gt 0 -and (Test-Path $stateCsv)) {
  $rows = (Get-Content $stateCsv | Measure-Object -Line).Lines
  if ($rows -ge $DoneRows) {
    Log "SKIP $Name rows=$rows"
    exit 0
  }
}

for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
  Kill-Vissim
  $argline = "//nologo " + (Q $runner) + " " + (Q $net) + " " + (Q $stateCsv) + " " + (Q $actionCsv) + " " + (Q $decisionDir) +
    " $SimPeriod $UrbanVph $FreewayVph $ControlIntervalSec $Seed " + (Q $adapter) + " " + (Q $calib) + " " + (Q $Tuning) +
    " $DemandProfile $Controller"
  if ($Pulse -ne "") {
    $argline = $argline + " " + (Q $Pulse)
  } else {
    $argline = $argline + " " + (Q "")
  }
  $argline = $argline + " $UrbanWestEastRatio"
  $argline = $argline + " $ControlStartSec " + (Q $WarmupController)

  $t0 = Get-Date
  $proc = Start-Process -FilePath "cscript.exe" -ArgumentList $argline -RedirectStandardOutput $log `
    -RedirectStandardError "$log.err" -PassThru -WindowStyle Hidden
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
      break
    }

    $lastT = $proc.StartTime
    $signals = @()
    $signals += Get-Item $log -ErrorAction SilentlyContinue
    $signals += Get-Item $stateCsv -ErrorAction SilentlyContinue
    $signals += Get-Item $actionCsv -ErrorAction SilentlyContinue
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
      break
    }
  }
}

Log "FAIL $Name after $MaxAttempts attempts"
exit 1
