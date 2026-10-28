# Wait for "no VISSIM process on this PC" (read-only; never touches another process). Same logic as A1 a1_wait_vissim.ps1.
# Polls every 30 s for at most -MaxSec seconds; writes one log line at start, at every change of the VISSIM PID set,
# at least every 270 s, and at the end. Prints CLEAR when no VISSIM was seen in polls >= 60 s apart, else BUSY.
# Other-run progress: newest runlog_*.txt under the run folders named in live cscript command lines (read-only).
param([int]$MaxSec = 540, [string]$Log = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\work\b\vissim_wait.log')
function Note([string]$m) { ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' KST ' + $m) | Add-Content -Encoding UTF8 -LiteralPath $Log }
function Pids { @(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^Vissim' } | ForEach-Object { [int]$_.ProcessId } | Sort-Object) -join ',' }
function OtherProgress {
  $parts = @()
  try {
    foreach ($cs in @(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'cscript.exe' })) {
      $m = [regex]::Match([string]$cs.CommandLine, '"([^"]+\\decisions_[^"\\]+)"')
      if (-not $m.Success) { continue }
      $out = Split-Path -Parent $m.Groups[1].Value
      $rl = Get-ChildItem -LiteralPath $out -Filter 'runlog_*.txt' -ErrorAction SilentlyContinue | Select-Object -First 1
      $last = '?'
      if ($rl) { $x = Select-String -LiteralPath $rl.FullName -Pattern '^CONTROLLER_DECISION sim_sec=(\d+)' | Select-Object -Last 1; if ($x) { $last = $x.Matches[0].Groups[1].Value } }
      $parts += ('cscript=' + $cs.ProcessId + ' out=' + $out + ' last_decision_sim_sec=' + $last)
    }
  } catch {}
  if (-not $parts.Count) { return 'other_run=?' }
  return ($parts -join ' | ')
}
$t0 = Get-Date; $last = Pids; $lastLog = Get-Date; $clearSince = $null
Note ("poll start vissim=[" + $last + "] " + (OtherProgress))
while ($true) {
  $p = Pids
  if ($p -eq '') { if (-not $clearSince) { $clearSince = Get-Date } } else { $clearSince = $null }
  if ($p -ne $last) { Note ("vissim set changed [" + $last + "] -> [" + $p + "] " + (OtherProgress)); $last = $p; $lastLog = Get-Date }
  if ($clearSince -and ((Get-Date) - $clearSince).TotalSeconds -ge 60) { Note 'CLEAR (no VISSIM in polls >= 60 s apart)'; 'CLEAR'; break }
  if (((Get-Date) - $lastLog).TotalSeconds -ge 270) { Note ("still vissim=[" + $p + "] " + (OtherProgress)); $lastLog = Get-Date }
  if (((Get-Date) - $t0).TotalSeconds -ge $MaxSec) { $o = OtherProgress; Note ("poll end BUSY vissim=[" + $p + "] " + $o); 'BUSY vissim=[' + $p + '] ' + $o; break }
  Start-Sleep -Seconds 30
}
