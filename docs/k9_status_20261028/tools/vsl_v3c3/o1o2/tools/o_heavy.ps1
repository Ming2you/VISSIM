# o_heavy.ps1 - O1/O2 heavy job queue (vsl_v3c3, 2026-10-27 KST). Modeled on vsl_v3c3/tools/vsl_heavy.ps1 (479a7e69...),
# but the shared lock D:\VISSIM-merge\k8_gate_trees\heavy.lock is taken PER JOB (CreateNew; if present wait 30 s and
# retry; removed after the job only if it still carries this job's token), so another workflow can interleave.
# Job kinds: {"tag","kind":"py","args":[script, ...]}  -> python -B args (cwd = O)
#            {"tag","kind":"probe","label","source","T","spec","out"} -> child powershell o_run_probe.ps1 (clean env)
# Started detached by WMI with BELOW_NORMAL. Stop between jobs if <O>\STOP_O exists. A failed job is logged and the
# queue continues (each job is independent). Windows PowerShell 5.1, ASCII only.
param(
  [Parameter(Mandatory = $true)][string]$Jobs,
  [double]$WaitLockHours = 6
)
$ErrorActionPreference = 'Stop'
$O = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\vsl_v3c3\o1o2'
$PY = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
$PS = 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
$LOCK = 'D:\VISSIM-merge\k8_gate_trees\heavy.lock'
$UTF8 = New-Object System.Text.UTF8Encoding $false
$spec = Get-Content -LiteralPath $Jobs -Raw -Encoding UTF8 | ConvertFrom-Json
$logDir = Join-Path $O ('logs\' + $spec.name)
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$Log = Join-Path $logDir 'heavy.log'
function Note([string]$m) { [IO.File]::AppendAllText($Log, (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' KST [pid=' + $PID + '] ' + $m + "`r`n", $UTF8) }
$selfSha = (Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant()
$jobsSha = (Get-FileHash -LiteralPath $Jobs -Algorithm SHA256).Hash.ToLowerInvariant()
Note ('START o_heavy sha256=' + $selfSha + ' jobs=' + $Jobs + ' jobs_sha256=' + $jobsSha)
$fails = 0
foreach ($j in @($spec.jobs)) {
  if (Test-Path -LiteralPath (Join-Path $O 'STOP_O')) { Note 'STOP_O present: stop before next job'; break }
  $free = [math]::Round((Get-PSDrive C).Free / 1GB, 1); $freeD = [math]::Round((Get-PSDrive D).Free / 1GB, 1)
  if ($free -lt 8 -or $freeD -lt 8) { Note ('DISK_LOW C=' + $free + ' D=' + $freeD + ' GB: stop'); break }
  $token = [guid]::NewGuid().ToString('N')
  $deadline = (Get-Date).AddHours($WaitLockHours)
  $have = $false
  while (-not $have) {
    try {
      $fs = [IO.File]::Open($LOCK, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::Read)
      $b = $UTF8.GetBytes(('owner=vsl_v3c3_o1o2 ' + $spec.name + '/' + $j.tag + ' token=' + $token + ' pid=' + $PID + ' time=' + (Get-Date).ToString('o')))
      $fs.Write($b, 0, $b.Length); $fs.Dispose(); $have = $true
      Note ('LOCK_TAKEN ' + $j.tag)
    } catch {
      if ((Get-Date) -gt $deadline) { Note 'LOCK_WAIT_GIVE_UP'; exit 3 }
      $holder = ''; try { $holder = [IO.File]::ReadAllText($LOCK) } catch { }
      Note ('LOCK_BUSY wait 30 s; holder: ' + $holder)
      Start-Sleep -Seconds 30
    }
  }
  try {
    $out = Join-Path $logDir ($j.tag + '.out.txt'); $err = Join-Path $logDir ($j.tag + '.err.txt')
    $t0 = Get-Date
    if ($j.kind -eq 'probe') {
      $argl = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $O 'tools\o_run_probe.ps1'),
        '-Label', $j.label, '-Source', $j.source, '-T', [string]$j.T, '-SpecFile', $j.spec, '-OutJson', $j.out)
      Note ('JOB_BEGIN ' + $j.tag + ' probe ' + $j.label + ' ' + $j.source + ' T=' + $j.T)
      $p = Start-Process -FilePath $PS -ArgumentList ($argl | ForEach-Object { '"' + $_ + '"' }) -NoNewWindow -PassThru -RedirectStandardOutput $out -RedirectStandardError $err
    } else {
      $env:PYTHONHASHSEED = '0'; $env:PYTHONDONTWRITEBYTECODE = '1'; $env:PYTHONIOENCODING = 'utf-8'; $env:PYTHONUTF8 = '1'
      $env:OMP_NUM_THREADS = '1'; $env:OPENBLAS_NUM_THREADS = '1'; $env:MKL_NUM_THREADS = '1'
      $argl = @('-B') + @($j.args)
      Note ('JOB_BEGIN ' + $j.tag + ' : ' + ($argl -join ' '))
      $p = Start-Process -FilePath $PY -ArgumentList ($argl | ForEach-Object { '"' + $_ + '"' }) -WorkingDirectory $O -NoNewWindow -PassThru -RedirectStandardOutput $out -RedirectStandardError $err
    }
    $null = $p.Handle
    try { $p.PriorityClass = 'BelowNormal' } catch {}
    $p.WaitForExit()
    $sec = [math]::Round(((Get-Date) - $t0).TotalSeconds, 1)
    Note ('JOB_END ' + $j.tag + ' exit=' + $p.ExitCode + ' sec=' + $sec)
    if ($p.ExitCode -ne 0) { $fails += 1; Note ('JOB_FAILED ' + $j.tag) }
  } finally {
    try {
      $cur = [IO.File]::ReadAllText($LOCK)
      if ($cur.Contains('token=' + $token)) { Remove-Item -LiteralPath $LOCK -Force; Note 'LOCK_RELEASED' } else { Note ('LOCK_NOT_OURS left as is: ' + $cur) }
    } catch { Note ('LOCK_RELEASE_ERROR ' + $_.Exception.Message) }
  }
}
Note ('END fails=' + $fails)
exit $fails
