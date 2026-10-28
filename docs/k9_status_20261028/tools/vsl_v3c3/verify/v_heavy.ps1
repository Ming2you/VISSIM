# v_heavy.ps1 - VERIFY_VSL (2026-10-27 KST). Run heavy python jobs under the shared lock heavy.lock.
# Lock: CreateNew (exclusive), wait/retry every 30 s (max WaitMin minutes), delete at end only if our token is inside.
# Each job: python -B, PYTHONHASHSEED=0, BelowNormal. Windows PowerShell 5.1, ASCII only.
param(
  [Parameter(Mandatory=$true)][string]$JobsFile,
  [int]$WaitMin = 60
)
$ErrorActionPreference = 'Stop'
$LOCK = 'D:\VISSIM-merge\k8_gate_trees\heavy.lock'
$V = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\vsl_v3c3\verify'
$PY = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
$log = Join-Path $V 'logs\heavy.log'
New-Item -ItemType Directory -Force (Join-Path $V 'logs') | Out-Null
function Note([string]$m) { Add-Content -LiteralPath $log -Value ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' KST [pid=' + $PID + '] ' + $m) }
try { (Get-Process -Id $PID).PriorityClass = 'BelowNormal' } catch {}
$token = 'verify_vsl_' + [guid]::NewGuid().ToString()
$jobs = Get-Content -LiteralPath $JobsFile -Raw -Encoding UTF8 | ConvertFrom-Json
$deadline = (Get-Date).AddMinutes($WaitMin)
$have = $false
$waits = 0
while (-not $have) {
  try {
    $fs = [IO.File]::Open($LOCK, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    $b = [Text.Encoding]::ASCII.GetBytes("owner=verify_vsl token=$token pid=$PID time=" + (Get-Date -Format 'yyyy-MM-ddTHH:mm:ss') + "`r`n")
    $fs.Write($b, 0, $b.Length); $fs.Close(); $have = $true
  } catch {
    if ((Get-Date) -gt $deadline) { Note "lock wait timeout after $waits waits"; exit 9 }
    $waits++
    if ($waits -eq 1 -or ($waits % 10) -eq 0) { $who = ''; try { $who = (Get-Content -LiteralPath $LOCK -Raw) } catch {}; Note ("lock busy, waiting: " + $who.Trim()) }
    Start-Sleep -Seconds 30
  }
}
Note ("lock acquired token=$token waits=$waits jobs=" + $JobsFile)
$rc = 0
try {
  $env:PYTHONHASHSEED = '0'; $env:PYTHONDONTWRITEBYTECODE = '1'; $env:PYTHONUTF8 = '1'
  $env:OMP_NUM_THREADS = '1'; $env:OPENBLAS_NUM_THREADS = '1'; $env:MKL_NUM_THREADS = '1'
  foreach ($j in $jobs) {
    $argList = @('-B') + @($j.args)
    $quoted = @($argList | ForEach-Object { '"' + $_ + '"' }) -join ' '
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $p = Start-Process -FilePath $PY -ArgumentList $quoted -NoNewWindow -PassThru `
      -RedirectStandardOutput (Join-Path $V ('logs\' + $j.tag + '.stdout.txt')) -RedirectStandardError (Join-Path $V ('logs\' + $j.tag + '.stderr.txt'))
    $null = $p.Handle
    try { $p.PriorityClass = 'BelowNormal' } catch {}
    $p.WaitForExit()
    $sw.Stop()
    Note ("job {0} pid={1} exit={2} wall={3:N1}s" -f $j.tag, $p.Id, $p.ExitCode, $sw.Elapsed.TotalSeconds)
    if ($p.ExitCode -ne 0) { $rc = 3 }
  }
} finally {
  $c = ''
  try { $c = Get-Content -LiteralPath $LOCK -Raw } catch {}
  if ($c -like "*$token*") { Remove-Item -LiteralPath $LOCK -Force; Note 'lock released (own token)' } else { Note 'lock NOT ours at end; left untouched' }
}
Note "done rc=$rc"
exit $rc
