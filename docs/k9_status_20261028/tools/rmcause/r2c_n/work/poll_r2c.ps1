# Read-only poll of the two R2c runs. Exits on: both completed, any stall > 300 s, any own PID gone before completion, or MaxSec.
param([int]$MaxSec = 520)
$t0 = Get-Date
$pids = @{ 31 = @(41832, 5456, 54900); 41 = @(48156, 21932, 36928) }
while ($true) {
  $lines = @(); $done = 0; $alarm = $false
  foreach ($s in 31, 41) {
    $r = "D:/VISSIM_runs/20261001_v3c3/s${s}_v3c3rm10681/run"
    $pg = Get-Item "$r/progress.csv" -EA SilentlyContinue
    $last = (Get-Content "$r/progress.csv" -Tail 1 -EA SilentlyContinue)
    $age = if ($pg) { [int]((Get-Date) - $pg.LastWriteTime).TotalSeconds } else { -1 }
    $comp = $false
    try { $j = Get-Content "$r/run.json" -Raw -EA Stop | ConvertFrom-Json; $comp = ($j.completed -eq $true) } catch {}
    $fv = Test-Path "$r/fixed_validation.json"
    $nd = @(Get-ChildItem $r -Filter 'decision_*.json' -EA SilentlyContinue | Where { $_.Name -notlike 'decision_failure*' }).Count
    $nf = @(Get-ChildItem $r -Filter 'decision_failure*' -EA SilentlyContinue).Count
    $alive = @($pids[$s] | Where { Get-Process -Id $_ -EA SilentlyContinue }).Count
    if ($comp) { $done++ }
    if (-not $comp -and ($age -gt 300)) { $alarm = $true }
    if (-not $comp -and $alive -lt 3 -and -not $fv) { $alarm = $true }
    if ($nf -gt 0) { $alarm = $true }
    $lines += "s$s last=[$last] age=${age}s dec=$nd fail=$nf alive=$alive/3 completed=$comp fv=$fv"
  }
  $el = [int]((Get-Date) - $t0).TotalSeconds
  if ($done -eq 2 -or $alarm -or $el -ge $MaxSec) {
    $tag = if ($done -eq 2) { 'BOTH_DONE' } elseif ($alarm) { 'ALARM' } else { 'TICK' }
    Write-Output ("{0} {1} vissim_pc={2}" -f (Get-Date -Format 'HH:mm:ss'), $tag, @(Get-Process -Name 'VISSIM*' -EA SilentlyContinue).Count)
    $lines | ForEach-Object { Write-Output $_ }
    break
  }
  Start-Sleep -Seconds 30
}
