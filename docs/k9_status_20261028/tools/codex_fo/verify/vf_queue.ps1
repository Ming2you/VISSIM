# vf_queue.ps1 - VERIFY_FO queue (Windows PowerShell 5.1, started detached by vf_launch.ps1 via WMI, BELOW_NORMAL).
# Steps: pin check -> vf_seedcheck -> vf_scan per FZP (one heavy.lock hold per FZP) -> vf_runfiles (one lock hold) -> vf_pairs.
# Lock: exclusive create of the shared heavy.lock, retry every 30 s up to 60 min, delete only our own token, 25 s pause after release.
# Never starts or stops VISSIM; never touches other processes.
param([Parameter(Mandatory=$true)][string]$QueueName)
$ErrorActionPreference = 'Stop'
$VFDIR = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\fo\verify'
$PYEXE = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
$LOCKPATH = 'D:\VISSIM-merge\k8_gate_trees\heavy.lock'
$OUTDIR = Join-Path $VFDIR 'out'
$LOGDIR = Join-Path $OUTDIR 'logs'
$STATEFILE = Join-Path $OUTDIR ($QueueName + '.state.txt')
$INPX = 'D:\VISSIM_runs\20261028_codex_fo_v3c3\s31\sdmpc\network\sdmpc31_sdmpc9000_s31.inpx'
$LISTFILE = Join-Path $VFDIR 'vf_fzp_list.txt'
$PINFILE = Join-Path $VFDIR 'PINS_VF.sha256'

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
  $so = Join-Path $LOGDIR ($stepName + '.out.txt')
  $se = Join-Path $LOGDIR ($stepName + '.err.txt')
  $proc = Start-Process -FilePath $PYEXE -ArgumentList ('-B ' + $argLine) -NoNewWindow -PassThru -RedirectStandardOutput $so -RedirectStandardError $se
  $null = $proc.Handle
  $proc.WaitForExit()
  return $proc.ExitCode
}

New-Item -ItemType Directory -Force $LOGDIR | Out-Null
Write-State ('QUEUE_START name=' + $QueueName + ' pid=' + $PID)
# pin check: every tool line in PINS_VF.sha256 must match
foreach ($pinLine in (Get-Content -LiteralPath $PINFILE)) {
  if ($pinLine.Trim() -eq '') { continue }
  $parts = $pinLine -split '\s+\*?', 2
  $want = $parts[0].Trim().ToLower()
  $rel = $parts[1].Trim().TrimStart('*')
  $have = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $VFDIR $rel)).Hash.ToLower()
  if ($have -ne $want) { Write-State ('STOP PIN_MISMATCH ' + $rel + ' have=' + $have + ' want=' + $want); exit 5 }
}
Write-State 'PINS_OK'

$codeSeed = Invoke-Py 'seedcheck' ('"' + (Join-Path $VFDIR 'vf_seedcheck.py') + '" "' + $LISTFILE + '" "' + (Join-Path $OUTDIR 'seedcheck.json') + '"')
Write-State ('STEP_END seedcheck exit=' + $codeSeed)
if ($codeSeed -ne 0) { Write-State 'STOP SEEDCHECK'; exit 4 }

$entries = Get-Content -LiteralPath $LISTFILE | Where-Object { $_.Trim() -ne '' -and -not $_.StartsWith('#') }
foreach ($ent in $entries) {
  $lab = ($ent -split '\|', 2)[0].Trim()
  $fzpPath = ($ent -split '\|', 2)[1].Trim()
  $outJson = Join-Path $OUTDIR ('scan_' + $lab + '.json')
  if (Test-Path -LiteralPath $outJson) { Write-State ('SKIP_EXISTS scan_' + $lab); continue }
  $tok = Get-HeavyLock ('vf_scan ' + $lab)
  if ($tok -eq $null) { Write-State 'STOP LOCK_60MIN'; exit 2 }
  $codeScan = -1
  try {
    $codeScan = Invoke-Py ('scan_' + $lab) ('"' + (Join-Path $VFDIR 'vf_scan.py') + '" ' + $lab + ' "' + $fzpPath + '" "' + $INPX + '" "' + $outJson + '"')
  } finally {
    Release-HeavyLock $tok
  }
  Write-State ('STEP_END scan_' + $lab + ' exit=' + $codeScan)
  if ($codeScan -ne 0) { Write-State ('STOP SCAN_FAILED ' + $lab); exit 3 }
}

$tok2 = Get-HeavyLock 'vf_runfiles'
if ($tok2 -eq $null) { Write-State 'STOP LOCK_60MIN'; exit 2 }
$codeRun = -1
try {
  $codeRun = Invoke-Py 'runfiles' ('"' + (Join-Path $VFDIR 'vf_runfiles.py') + '" "' + (Join-Path $OUTDIR 'runfiles.json') + '"')
} finally {
  Release-HeavyLock $tok2
}
Write-State ('STEP_END runfiles exit=' + $codeRun)
if ($codeRun -ne 0) { Write-State 'STOP RUNFILES_FAILED'; exit 3 }

$codePairs = Invoke-Py 'pairs' ('"' + (Join-Path $VFDIR 'vf_pairs.py') + '" "' + $OUTDIR + '" "' + (Join-Path $OUTDIR 'pairs.json') + '"')
Write-State ('STEP_END pairs exit=' + $codePairs)
if ($codePairs -ne 0) { Write-State 'STOP PAIRS_FAILED'; exit 3 }
Write-State 'QUEUE_DONE'
exit 0
