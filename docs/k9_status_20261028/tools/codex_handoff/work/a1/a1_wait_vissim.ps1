# Wait for "no VISSIM process on this PC" (read-only; never touches another process).
# Polls every 30 s for at most -MaxSec seconds; writes one log line at start, at every change of the VISSIM PID set,
# at least every 270 s, and at the end. Prints CLEAR when no VISSIM was seen in two polls 60 s apart, else BUSY.
param([int]$MaxSec = 540, [string]$Log = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\work\a1\vissim_wait.log')
function Note([string]$m) { ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' KST ' + $m) | Add-Content -Encoding UTF8 -LiteralPath $Log }
function Pids { @(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^Vissim' } | ForEach-Object { [int]$_.ProcessId } | Sort-Object) -join ',' }
function OtherProgress {
  try {
    $f = 'D:\VISSIM_runs\20261023_rolling_cea\ttt_only_s29_8100_v4\sdmpc\runlog_sdmpc31_sdmpc8100_s29.txt'
    $m = Select-String -LiteralPath $f -Pattern '^CONTROLLER_DECISION sim_sec=(\d+)' | Select-Object -Last 1
    if ($m) { return 'other_run_last_decision_sim_sec=' + $m.Matches[0].Groups[1].Value } } catch {}
  return 'other_run_last_decision_sim_sec=?'
}
$t0 = Get-Date; $last = Pids; $lastLog = Get-Date; $clearSince = $null
Note ("poll start vissim=[" + $last + "] " + (OtherProgress))
while ($true) {
  $p = Pids
  if ($p -eq '') { if (-not $clearSince) { $clearSince = Get-Date } } else { $clearSince = $null }
  if ($p -ne $last) { Note ("vissim set changed [" + $last + "] -> [" + $p + "] " + (OtherProgress)); $last = $p; $lastLog = Get-Date }
  if ($clearSince -and ((Get-Date) - $clearSince).TotalSeconds -ge 60) { Note 'CLEAR (no VISSIM in polls >= 60 s apart)'; 'CLEAR'; break }
  if (((Get-Date) - $lastLog).TotalSeconds -ge 270) { Note ("still vissim=[" + $p + "] " + (OtherProgress)); $lastLog = Get-Date }
  if (((Get-Date) - $t0).TotalSeconds -ge $MaxSec) { Note ("poll end BUSY vissim=[" + $p + "] " + (OtherProgress)); 'BUSY vissim=[' + $p + '] ' + (OtherProgress); break }
  Start-Sleep -Seconds 30
}
