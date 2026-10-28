# vf_queue2.ps1 - VERIFY_FO second queue (Windows PowerShell 5.1, detached via vf_launch2.ps1, BELOW_NORMAL).
# Steps: pin check (PINS_VF2.sha256) -> vf_prefix under one heavy.lock hold -> vf_extra -> vf_check.
# Lock rules as vf_queue.ps1. Never starts or stops VISSIM; never touches other processes.
param([Parameter(Mandatory=$true)][string]$QueueName)
$ErrorActionPreference = 'Stop'
$VFDIR = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\fo\verify'
$FODIR = Split-Path -Parent $VFDIR
$PYEXE = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
$LOCKPATH = 'D:\VISSIM-merge\k8_gate_trees\heavy.lock'
$OUTDIR = Join-Path $VFDIR 'out'
$LOGDIR = Join-Path $OUTDIR 'logs'
$STATEFILE = Join-Path $OUTDIR ($QueueName + '.state.txt')
$LISTFILE = Join-Path $VFDIR 'vf_fzp_list.txt'
$PINFILE = Join-Path $VFDIR 'PINS_VF2.sha256'

function Write-State([string]$msg) {
  $txt = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' ' + $msg + "`r`n"
  for ($k = 0; $k -lt 20; $k++) {
    try { [System.IO.File]::AppendAllText($STATEFILE, $txt, (New-Object System.Text.UTF8Encoding($false))); return } catch { Start-Sleep -Milliseconds 500 }
  }
}

function Get-HeavyLock([string]$what) {
  $tokenText = 'VERIFY_FO pid=' + $PID + ' guid=' + [guid]::NewGuid().ToString() + ' what=' + $what + ' at=' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
  $deadline = (Get-Date).AddMinutes(60)
  while ((Get-Date) -lt $deadline) {
    $handle = $null
    try {
      $handle = [System.IO.File]::Open($LOCKPATH, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
      $bytes = [System.Text.Encoding]::ASCII.GetBytes($tokenText)
      $handle.Write($bytes, 0, $bytes.Length)
      $handle.Close()
      Write-State ('LOCK_ACQUIRED ' + $tokenText)
      return $tokenText
    } catch {
      if ($handle -ne $null) { try { $handle.Close() } catch {} }
      Write-State ('LOCK_BUSY ' + $what + ' retry_in_30s')
      Start-Sleep -Seconds 30
    }
  }
  return $null
}

function Release-HeavyLock([string]$tokenText) {
  $cur = $null
  try { $cur = [System.IO.File]::ReadAllText($LOCKPATH) } catch { $cur = $null }
  if ($cur -eq $tokenText) { Remove-Item -LiteralPath $LOCKPATH -Force; Write-State 'LOCK_RELEASED own_token' }
  else { Write-State 'LOCK_NOT_OURS_NOT_DELETED' }
  Start-Sleep -Seconds 25
}

function Invoke-Py([string]$stepName, [string]$argLine) {
  $env:PYTHONHASHSEED = '0'
  $env:PYTHONDONTWRITEBYTECODE = '1'
  $env:OMP_NUM_THREADS = '1'
  $env:OPENBLAS_NUM_THREADS = '1'
  $env:MKL_NUM_THREADS = '1'
  $env:NUMEXPR_NUM_THREADS = '1'
  $env:PYTHONIOENCODING = 'utf-8'
  $so = Join-Path $LOGDIR ($stepName + '.out.txt')
  $se = Join-Path $LOGDIR ($stepName + '.err.txt')
  $proc = Start-Process -FilePath $PYEXE -ArgumentList ('-B ' + $argLine) -NoNewWindow -PassThru -RedirectStandardOutput $so -RedirectStandardError $se
  $null = $proc.Handle
  $proc.WaitForExit()
  return $proc.ExitCode
}

New-Item -ItemType Directory -Force $LOGDIR | Out-Null
Write-State ('QUEUE_START name=' + $QueueName + ' pid=' + $PID)
foreach ($pinLine in (Get-Content -LiteralPath $PINFILE)) {
  if ($pinLine.Trim() -eq '') { continue }
  $parts = $pinLine -split '\s+\*?', 2
  $want = $parts[0].Trim().ToLower()
  $rel = $parts[1].Trim().TrimStart('*')
  $have = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $VFDIR $rel)).Hash.ToLower()
  if ($have -ne $want) { Write-State ('STOP PIN_MISMATCH ' + $rel + ' have=' + $have + ' want=' + $want); exit 5 }
}
Write-State 'PINS_OK'

$tok = Get-HeavyLock 'vf_prefix'
if ($tok -eq $null) { Write-State 'STOP LOCK_60MIN'; exit 2 }
$codePre = -1
try {
  $codePre = Invoke-Py 'prefix' ('"' + (Join-Path $VFDIR 'vf_prefix.py') + '" "' + $LISTFILE + '" "' + (Join-Path $OUTDIR 'prefix.json') + '"')
} finally {
  Release-HeavyLock $tok
}
Write-State ('STEP_END prefix exit=' + $codePre)
if ($codePre -ne 0) { Write-State 'STOP PREFIX_FAILED'; exit 3 }

$codeExtra = Invoke-Py 'extra' ('"' + (Join-Path $VFDIR 'vf_extra.py') + '" "' + (Join-Path $OUTDIR 'extra.json') + '"')
Write-State ('STEP_END extra exit=' + $codeExtra)
if ($codeExtra -ne 0) { Write-State 'STOP EXTRA_FAILED'; exit 3 }

$codeChk = Invoke-Py 'check' ('"' + (Join-Path $VFDIR 'vf_check.py') + '" "' + $OUTDIR + '" "' + (Join-Path $FODIR 'FO_REPORT.json') + '" "' + (Join-Path $FODIR 'FO_REPORT.md') + '" "' + (Join-Path $OUTDIR 'check.json') + '"')
Write-State ('STEP_END check exit=' + $codeChk)
if ($codeChk -ne 0) { Write-State 'STOP CHECK_FAILED'; exit 3 }
Write-State 'QUEUE_DONE'
exit 0
