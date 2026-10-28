# FO final analysis plan under the shared heavy lock (Analyze step, 2026-10-28 KST; Windows PowerShell 5.1, ASCII).
# Holds D:\VISSIM-merge\k8_gate_trees\heavy.lock (exclusive create, retry 30 s, give up after 60 min -> exit 3) around ONE run
# of the declared plan "fo_ana.ps1 -Plan final" (unchanged; its steps are cache-only, so fo_ana itself takes no lock and the
# outer hold cannot deadlock). Deletes only its own token, then pauses 25 s. Started detached by fo_launch_wmi.ps1 at
# BELOW_NORMAL; the child inherits. Writes final_locked.state.txt next to this file. Does not read fo_ana's state file.
$ErrorActionPreference = 'Stop'
$FA = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\fo\work\ana'
$LOCK = 'D:\VISSIM-merge\k8_gate_trees\heavy.lock'
$stfile = Join-Path $FA 'final_locked.state.txt'
$TOKEN = 'fo_final-' + $PID + '-' + [guid]::NewGuid().ToString('N')
function W([string]$m) { ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' KST ' + $m) | Add-Content -Encoding UTF8 -LiteralPath $stfile }
W ('start pid=' + $PID + ' priority=' + (Get-Process -Id $PID).PriorityClass + ' token=' + $TOKEN)
$t0 = Get-Date
$got = $false
while (-not $got) {
  try {
    $fs = [IO.File]::Open($LOCK, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    $body = '{"owner": "fo_final_locked", "pid": ' + $PID + ', "token": "' + $TOKEN + '", "started_kst": "' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' KST", "job": "FO analysis final plan (cache-only steps)"}'
    $bytes = (New-Object System.Text.UTF8Encoding $false).GetBytes($body)
    $fs.Write($bytes, 0, $bytes.Length)
    $fs.Dispose()
    $got = $true
  } catch {
    if (((Get-Date) - $t0).TotalMinutes -gt 60) { W 'STOP heavy lock not acquired within 60 min'; exit 3 }
    Start-Sleep -Seconds 30
  }
}
W ('lock acquired after ' + [int]((Get-Date) - $t0).TotalSeconds + ' s')
$code = 99
try {
  $t1 = Get-Date
  $child = Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"' + (Join-Path $FA 'fo_ana.ps1') + '"'), '-Plan', 'final') -WorkingDirectory $FA -NoNewWindow -Wait -PassThru
  $code = $child.ExitCode
  W ('fo_ana -Plan final exit=' + $code + ' sec=' + [math]::Round(((Get-Date) - $t1).TotalSeconds, 1))
} catch {
  W ('fo_ana start error: ' + [string]$_)
} finally {
  try {
    $txt = [IO.File]::ReadAllText($LOCK)
    if ($txt -like ('*' + $TOKEN + '*')) { Remove-Item -LiteralPath $LOCK -Force; W 'lock released (own token)' } else { W 'lock NOT released: token differs' }
  } catch { W ('lock release error: ' + [string]$_) }
  Start-Sleep -Seconds 25
  W ('done exit=' + $code)
}
exit $code
