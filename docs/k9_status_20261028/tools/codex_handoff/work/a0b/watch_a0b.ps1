# Read-only watcher for the A0b queue. Exits when the queue is done/stopped, when a replay's progress log has not
# changed for StallMin minutes, or after MaxMin minutes. Kills nothing.
param([int]$StallMin = 15, [int]$MaxMin = 200)
$W = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\work\a0b'
$A0 = 'D:\VISSIM-merge\k8_gate_trees\codexhandoff\a0'
$t0 = Get-Date
$lastLine = ''
while ($true) {
  if (Test-Path (Join-Path $W 'queue_a0b.done')) { 'DONE'; break }
  if (Test-Path (Join-Path $W 'a0b.stop')) { 'STOPPED'; break }
  $st = @(Get-Content (Join-Path $W 'queue_a0b.state.txt'))
  $cur = ($st | Where-Object { $_ -match 'T=(\d+) replay start' } | Select-Object -Last 1)
  if ($cur -match 'T=(\d+) replay start') {
    $T = [int]$Matches[1]; $t6 = '{0:D6}' -f $T
    $pf = Join-Path $A0 ("runs\T$t6\sdmpc\decisions_sdmpc31_sdmpc8100_s29\action_$t6.joint.progress.jsonl")
    $ended = $st | Where-Object { $_ -match "T=$T replay end" }
    if (-not $ended -and (Test-Path $pf)) {
      $age = ((Get-Date) - (Get-Item $pf).LastWriteTime).TotalMinutes
      if ($age -gt $StallMin) { "STALL T=$T progress age $([math]::Round($age,1)) min"; break }
    }
  }
  if (((Get-Date) - $t0).TotalMinutes -gt $MaxMin) { 'MAXTIME'; break }
  Start-Sleep -Seconds 60
}
Get-Content (Join-Path $W 'queue_a0b.state.txt') | Select-Object -Last 8
