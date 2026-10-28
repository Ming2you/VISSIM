# vsl_heavy.ps1 - run a list of heavy read-only Python jobs (FZP scans) one after another under the shared lock
# D:\VISSIM-merge\k8_gate_trees\heavy.lock (created with FileMode.CreateNew; if present, wait and retry; removed at the end
# only if it still carries this run's token). Windows PowerShell 5.1, ASCII only. Started detached by WMI with
# PriorityClass BELOW_NORMAL (child python processes inherit it). Env: PYTHONHASHSEED=0, PYTHONDONTWRITEBYTECODE=1,
# OMP/OPENBLAS/MKL threads 1, python -B. Stop between jobs if <VS>\STOP_HEAVY exists. 2026-10-27 KST, vsl_v3c3.
# Jobs file (JSON): {"name": "...", "jobs": [{"tag": "...", "args": ["<script.py>", "arg1", ...]}, ...]}
param(
  [Parameter(Mandatory = $true)][string]$Jobs,
  [double]$WaitLockHours = 6
)
$ErrorActionPreference = 'Stop'
$VS = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\vsl_v3c3'
$PY = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
$LOCK = 'D:\VISSIM-merge\k8_gate_trees\heavy.lock'
$UTF8 = New-Object System.Text.UTF8Encoding $false
$spec = Get-Content -LiteralPath $Jobs -Raw -Encoding UTF8 | ConvertFrom-Json
$logDir = Join-Path $VS ('logs\' + $spec.name)
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$Log = Join-Path $logDir 'heavy.log'
function Note([string]$m) { [IO.File]::AppendAllText($Log, (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' KST [pid=' + $PID + '] ' + $m + "`r`n", $UTF8) }
$token = [guid]::NewGuid().ToString('N')
$selfSha = (Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant()
$jobsSha = (Get-FileHash -LiteralPath $Jobs -Algorithm SHA256).Hash.ToLowerInvariant()
Note ('START heavy runner sha256=' + $selfSha + ' jobs=' + $Jobs + ' jobs_sha256=' + $jobsSha + ' token=' + $token)
$deadline = (Get-Date).AddHours($WaitLockHours)
$have = $false
while (-not $have) {
  try {
    $fs = [IO.File]::Open($LOCK, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::Read)
    $b = $UTF8.GetBytes(('owner=vsl_v3c3 ' + $spec.name + ' token=' + $token + ' pid=' + $PID + ' time=' + (Get-Date).ToString('o')))
    $fs.Write($b, 0, $b.Length); $fs.Dispose(); $have = $true
    Note ('LOCK_TAKEN ' + $LOCK)
  } catch {
    if ((Get-Date) -gt $deadline) { Note 'LOCK_WAIT_GIVE_UP'; exit 3 }
    $holder = ''; try { $holder = [IO.File]::ReadAllText($LOCK) } catch { }
    Note ('LOCK_BUSY wait 30 s; holder: ' + $holder)
    Start-Sleep -Seconds 30
  }
}
$rc = 0
try {
  $env:PYTHONHASHSEED = '0'; $env:PYTHONDONTWRITEBYTECODE = '1'; $env:PYTHONIOENCODING = 'utf-8'
  $env:OMP_NUM_THREADS = '1'; $env:OPENBLAS_NUM_THREADS = '1'; $env:MKL_NUM_THREADS = '1'
  foreach ($j in @($spec.jobs)) {
    if (Test-Path -LiteralPath (Join-Path $VS 'STOP_HEAVY')) { Note 'STOP_HEAVY present: stop before next job'; $rc = 4; break }
    $out = Join-Path $logDir ($j.tag + '.out.txt'); $err = Join-Path $logDir ($j.tag + '.err.txt')
    $argl = @('-B') + @($j.args)
    Note ('JOB_BEGIN ' + $j.tag + ' : ' + ($argl -join ' '))
    $t0 = Get-Date
    $p = Start-Process -FilePath $PY -ArgumentList ($argl | ForEach-Object { '"' + $_ + '"' }) -NoNewWindow -PassThru -RedirectStandardOutput $out -RedirectStandardError $err
    $null = $p.Handle   # keep the OS handle so ExitCode survives (PS 5.1)
    $p.WaitForExit()
    $sec = [math]::Round(((Get-Date) - $t0).TotalSeconds, 1)
    Note ('JOB_END ' + $j.tag + ' exit=' + $p.ExitCode + ' sec=' + $sec)
    if ($p.ExitCode -ne 0) { $rc = 1; Note 'JOB_FAILED: stop the list'; break }
  }
} finally {
  try {
    $cur = [IO.File]::ReadAllText($LOCK)
    if ($cur.Contains('token=' + $token)) { Remove-Item -LiteralPath $LOCK -Force; Note 'LOCK_RELEASED' } else { Note ('LOCK_NOT_OURS left as is: ' + $cur) }
  } catch { Note ('LOCK_RELEASE_ERROR ' + $_.Exception.Message) }
}
Note ('END rc=' + $rc)
exit $rc
