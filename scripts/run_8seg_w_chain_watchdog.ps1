<#
run_8seg_w_chain_watchdog.ps1 — 8-seg _w suite chain with a hang watchdog (2026-07-15).

User policy: VISSIM COM runs must be monitored; if no progress for 5 minutes wall
(StallSec=300), force-kill cscript+VISSIM and restart that run from scratch, up to
MaxAttempts. Progress signal = newest mtime among decisions\action_*.json and the
run's state csv. RESUMABLE: runs whose state csv already has >= DoneRows lines are
skipped, so the chain can be relaunched safely after any interruption.

Job list is embedded (edit the $jobs array). Modeled on run_controller_with_watchdog.ps1.
#>
param(
  [int]$StallSec = 300,
  [int]$MaxAttempts = 3,
  [int]$DoneRows = 2100
)

$ErrorActionPreference = "Continue"
$adp = "C:\Users\TRLAB\Documents\Codex\2026-06-25\ming2you-numerical-sim-https-github-com"
$nw = "C:\Users\TRLAB\Desktop\찐찐막\Network_Vissim_Work"
$runs = "$adp\evaluation\runs\8seg_sweet_w_20260714"
$runner = "$adp\scripts\run_stackelberg_vissim_controller_8seg.vbs"
$net = "$nw\modi_eval_vsl_8seg.inpx"
$adapter = "$adp\evaluation\controllers\vissim_stackelberg_adapter.py"
$calib = "$adp\evaluation\calibration\vissim_network_calibration_v2_8seg_20260714.json"
$tuning = "$adp\evaluation\configs\tuning_turning_ratios_route_manifest_v2_20260715.json"
$pulse = "0.5:3600:300:3600:300"

$jobs = @(
    @{name="pfo_190w_v2";    u=1235; fw=3213; seed=13; ctrl="pfo";                    tun=$tuning},
    @{name="pstack_190w_v2"; u=1235; fw=3213; seed=13; ctrl="stackelberg-wu-metered"; tun=$tuning}
)
# NOTE: pfo_155w_tr must use $tuning too — fixed below (kept the array literal simple).
foreach ($j in $jobs) { if ($j.name -like "*_tr*" -and $j.tun -eq "") { $j.tun = $tuning } }

$progress = Join-Path $runs "WATCHDOG_PROGRESS.txt"
New-Item -ItemType Directory -Force -Path $runs | Out-Null
function Log($m) {
  $line = ("{0}  {1}" -f (Get-Date -Format "MM-dd HH:mm:ss"), $m)
  for ($r = 0; $r -lt 5; $r++) {
    try { [System.IO.File]::AppendAllText($progress, $line + "`r`n"); break }
    catch { Start-Sleep -Milliseconds 200 }
  }
}

function Kill-Vissim {
  Get-Process -Name "VISSIM200","VISSIM200CL","cscript" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 3
}

function Q($s) { '"' + $s + '"' }

function Run-One($j) {
  $n = $j.name
  $stateCsv = Join-Path $runs "state_$n.csv"
  $actionCsv = Join-Path $runs "action_$n.csv"
  $dec = Join-Path $runs "decisions_$n"
  $log = Join-Path $runs "runlog_$n.txt"
  if (Test-Path $stateCsv) {
    $rows = (Get-Content $stateCsv | Measure-Object -Line).Lines
    if ($rows -ge $DoneRows) { Log "SKIP $n (rows=$rows)"; return $true }
  }
  New-Item -ItemType Directory -Force -Path $dec | Out-Null
  for ($att = 1; $att -le $MaxAttempts; $att++) {
    Kill-Vissim
    $tunTok = if ($j.tun -ne "") { Q $j.tun } else { '""' }
    $argline = "//nologo " + (Q $runner) + " " + (Q $net) + " " + (Q $stateCsv) + " " + (Q $actionCsv) + " " + (Q $dec) +
      " 10800 $($j.u) $($j.fw) 180 $($j.seed) " + (Q $adapter) + " " + (Q $calib) +
      " $tunTok sym $($j.ctrl) " + (Q $pulse)
    $t0 = Get-Date
    $proc = Start-Process -FilePath "cscript" -ArgumentList $argline -RedirectStandardOutput $log `
            -RedirectStandardError "$log.err" -PassThru -WindowStyle Hidden
    Log "START $n attempt $att pid $($proc.Id)"
    while ($true) {
      Start-Sleep -Seconds 20
      if ($proc.HasExited) {
        $done = Select-String -Path $log -Pattern "SIM_DONE" -Quiet -ErrorAction SilentlyContinue
        if ($done) { Log "OK $n attempt $att elapsed $([int]((Get-Date)-$t0).TotalSeconds)s"; return $true }
        Log "EXIT-NO-DONE $n attempt $att (retry)"; break
      }
      $lastT = $proc.StartTime
      $sig = @()
      $sig += Get-ChildItem (Join-Path $dec "action_*.json") -ErrorAction SilentlyContinue |
              Sort-Object LastWriteTime -Descending | Select-Object -First 1
      $sig += Get-Item $stateCsv -ErrorAction SilentlyContinue
      foreach ($s in $sig) { if ($s -and $s.LastWriteTime -gt $lastT) { $lastT = $s.LastWriteTime } }
      $idle = [int]((Get-Date) - $lastT).TotalSeconds
      if ($idle -gt $StallSec) {
        Log "WATCHDOG_KILL $n attempt $att (idle ${idle}s > ${StallSec}s)"
        try { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue } catch {}
        Kill-Vissim
        break
      }
    }
  }
  Log "FAIL $n after $MaxAttempts attempts"
  return $false
}

Log "CHAIN START stall=${StallSec}s maxAtt=${MaxAttempts} jobs=$($jobs.Count)"
$failed = @()
foreach ($j in $jobs) {
  $ok = Run-One $j
  if (-not $ok) { $failed += $j.name }
}
Kill-Vissim
if ($failed.Count -gt 0) { Log "CHAIN DONE with FAILURES: $($failed -join ', ')" } else { Log "CHAIN DONE all OK" }
