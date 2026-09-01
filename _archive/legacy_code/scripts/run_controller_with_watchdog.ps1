<#
run_controller_with_watchdog.ps1 — VISSIM controller runs with a hang watchdog + auto-restart.

VISSIM COM occasionally hangs (e.g. stuck at COM_CREATED). This wrapper monitors run progress via
the newest decisions\action_*.json mtime (written directly by the python adapter, so it is not
affected by cscript stdout buffering). If no progress for -StallSec seconds, it force-kills the
cscript + VISSIM processes and restarts that run from the beginning, up to -MaxAttempts times.
It is RESUMABLE: runs whose state.csv already has >= -DoneRows lines are skipped.

Usage example:
  powershell -File run_controller_with_watchdog.ps1 -Base <dir> -Net <inpx> -Adapter <py> -Calib <json> `
    -SimPeriod 1800 -UrbanVol 1800 -FreewayVol 3000 -CtrlInterval 60 `
    -Seeds 11,13,47 -Controllers no-control,wu,pfo,stackelberg-wu-metered
#>
param(
  [Parameter(Mandatory=$true)][string]$Base,
  [Parameter(Mandatory=$true)][string]$Net,
  [Parameter(Mandatory=$true)][string]$Adapter,
  [Parameter(Mandatory=$true)][string]$Calib,
  [int]$SimPeriod = 1800,
  [int]$UrbanVol = 1800,
  [int]$FreewayVol = 3000,
  [int]$CtrlInterval = 60,
  [string]$Profile = "sym",
  [string]$Tuning = "",
  [int[]]$Seeds = @(11,13,47),
  [string[]]$Controllers = @("no-control","wu","pfo","stackelberg-wu-metered"),
  [int]$StallSec = 180,
  [int]$MaxAttempts = 3,
  [int]$DoneRows = 360
)

$ErrorActionPreference = "Continue"
$runner = Join-Path $PSScriptRoot "run_stackelberg_vissim_controller.vbs"
New-Item -ItemType Directory -Force -Path $Base | Out-Null
$progress = Join-Path $Base "PROGRESS.txt"
function Log($m) { Add-Content -Path $progress -Value ("{0}  {1}" -f (Get-Date -Format HH:mm:ss), $m) }
Log "WATCHDOG START stall=${StallSec}s maxAtt=${MaxAttempts}"

function Kill-Vissim {
  Get-Process -Name "VISSIM200","VISSIM200CL","cscript" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 3
}

function Run-One($ctrl, $seed) {
  $name = ($ctrl -replace '-','_') + "_seed$seed"
  $dir = Join-Path $Base $name
  $dec = Join-Path $dir "decisions"
  $stateCsv = Join-Path $dir "state.csv"
  $log = Join-Path $dir "run_log.txt"
  # resumable: skip if already complete
  if (Test-Path $stateCsv) {
    $rows = (Get-Content $stateCsv | Measure-Object -Line).Lines
    if ($rows -ge $DoneRows) { Log "SKIP $name (already complete, rows=$rows)"; return $true }
  }
  New-Item -ItemType Directory -Force -Path $dec | Out-Null
  for ($att = 1; $att -le $MaxAttempts; $att++) {
    Kill-Vissim
    # Build a single quoted argument string so the empty tuning arg ("") is preserved
    # (Start-Process drops empty array elements, which would shift positional args).
    $actionCsv = Join-Path $dir "action.csv"
    function Q($s) { '"' + $s + '"' }
    $tunTok = if ($Tuning -ne "") { Q $Tuning } else { '""' }
    $argline = "//nologo " + (Q $runner) + " " + (Q $Net) + " " + (Q $stateCsv) + " " + (Q $actionCsv) + " " + (Q $dec) +
      " $SimPeriod $UrbanVol $FreewayVol $CtrlInterval $seed " + (Q $Adapter) + " " + (Q $Calib) +
      " $tunTok " + (Q $Profile) + " " + (Q $ctrl)
    $t0 = Get-Date
    $proc = Start-Process -FilePath "cscript" -ArgumentList $argline -RedirectStandardOutput $log `
            -RedirectStandardError "$log.err" -PassThru -WindowStyle Hidden
    Log "START $name attempt $att pid $($proc.Id)"
    while ($true) {
      Start-Sleep -Seconds 15
      if ($proc.HasExited) {
        $done = Select-String -Path $log -Pattern "SIM_DONE" -Quiet -ErrorAction SilentlyContinue
        if ($done) { Log "OK $name attempt $att elapsed $([int]((Get-Date)-$t0).TotalSeconds)s"; return $true }
        Log "EXIT-NO-DONE $name attempt $att (will retry)"; break
      }
      # progress signal: newest decision json mtime, floored at process start
      $lastT = $proc.StartTime
      $newest = Get-ChildItem (Join-Path $dec "action_*.json") -ErrorAction SilentlyContinue |
                Sort-Object LastWriteTime -Descending | Select-Object -First 1
      if ($newest -and $newest.LastWriteTime -gt $lastT) { $lastT = $newest.LastWriteTime }
      $idle = [int]((Get-Date) - $lastT).TotalSeconds
      if ($idle -gt $StallSec) {
        Log "WATCHDOG_KILL $name attempt $att (idle ${idle}s > ${StallSec}s)"
        try { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue } catch {}
        Kill-Vissim
        break
      }
    }
  }
  Log "FAIL $name after $MaxAttempts attempts"; return $false
}

foreach ($seed in $Seeds) {
  foreach ($ctrl in $Controllers) {
    Run-One $ctrl $seed | Out-Null
  }
  Log "--- seed $seed complete ---"
}
Kill-Vissim
Log "ALL_DONE"
