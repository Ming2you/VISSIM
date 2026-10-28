# FO monitor wait (2026-10-27 KST; copy of work/b/b_poll_wait.ps1 with b_status.ps1 -> fo_status.ps1 only). Read-only: starts nothing, stops nothing, writes nothing.
# Calls fo_status.ps1 every -PollSec seconds for at most -MaxSec seconds (<= 540) and returns early when a watched flag changes:
#   launcher process present, launch stopped / stop files, disk below 8 GB, PC VISSIM count above 4,
#   per seed: tries list, wrapper alive, first control decision T=900 done, non-zero decision exits, hold attempts,
#   held-previous count, IDLE_OVER_499, sim_done, wrapper end/exit text, native_status stage.
# Prints the reason and the last fo_status output.
param([int]$MaxSec = 520, [int]$PollSec = 30)
$ErrorActionPreference = 'Continue'
if ($MaxSec -gt 540) { $MaxSec = 540 }
$ST = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\fo\fo_status.ps1'
function Flags([string[]]$lines) {
  $f = New-Object System.Collections.ArrayList
  $seed = ''
  foreach ($l in $lines) {
    if ($l -match '^launcher processes=\[([^\]]*)\]') { [void]$f.Add('launcher=' + $(if ($Matches[1]) { 'yes' } else { 'NONE' })) }
    elseif ($l -match '^launch stopped=(.*) stop_files=\[([^\]]*)\]') { [void]$f.Add('stopped=' + $Matches[1] + ' files=' + $Matches[2]) }
    elseif ($l -match '^disk ') { [void]$f.Add('disklow=' + ($l -match 'DISK_BELOW_8GB')) }
    elseif ($l -match '^PC VISSIM count=(\d+)') { [void]$f.Add('vissim_over4=' + ([int]$Matches[1] -gt 4)) }
    elseif ($l -match '^(s\d+) launched=(\S+)(?: tries=\[([^\]]*)\])?') { $seed = $Matches[1]; [void]$f.Add($seed + ' launched=' + $Matches[2] + ' tries=' + $Matches[3]) }
    elseif ($seed -and $l -match '^\s+wrapper=\d+\((\w+ ?\w*)\).* decisions=(\d+) .*nonzero=(\d+)') {
      $n = [int]$Matches[2]
      [void]$f.Add($seed + ' wrapper=' + $Matches[1] + ' t900done=' + ($n -ge 7) + ' nonzero=' + $Matches[3]) }
    elseif ($seed -and $l -match '^\s+in_progress=.*attempts=(\d+).*held_previous=(\d+)') { [void]$f.Add($seed + ' holds=' + $Matches[1] + '/' + $Matches[2]) }
    elseif ($seed -and $l -match '^\s+last_progress_age=') { [void]$f.Add($seed + ' idle_over=' + ($l -match 'IDLE_OVER_')) }
    elseif ($seed -and $l -match '^\s+stage=.* sim_done=(\S+) SIM_SEC=(\S+) exit=\[([^\]]*)\] native_status=(\S+)') { [void]$f.Add($seed + ' done=' + $Matches[1] + ' simsec=' + $Matches[2] + ' exit=' + $Matches[3] + ' ns=' + $Matches[4]) }
  }
  return ($f -join ' | ')
}
$t0 = Get-Date
$first = @(& $ST)
$f0 = Flags $first
$last = $first; $reason = 'max_wait'
while (((Get-Date) - $t0).TotalSeconds + $PollSec -le $MaxSec) {
  Start-Sleep -Seconds $PollSec
  $last = @(& $ST)
  $f1 = Flags $last
  if ($f1 -ne $f0) {
    $a = $f0 -split ' \| '; $b = $f1 -split ' \| '
    $reason = 'flag_change: ' + ((@($b | Where-Object { $a -notcontains $_ })) -join ' ; ')
    break
  }
}
'WAIT_END ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' waited=' + [int]((Get-Date) - $t0).TotalSeconds + 's reason=' + $reason
'FLAGS0 ' + $f0
$last
