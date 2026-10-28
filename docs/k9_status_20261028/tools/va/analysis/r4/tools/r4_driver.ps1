# V-A r4 driver: runs the 9 FZP first-observation scans (one at a time) and then r4_firstobs.py.
# Started detached by r4_launch.ps1 (WMI Win32_Process.Create, BELOW_NORMAL); children inherit BELOW_NORMAL and are
# also set to BelowNormal explicitly.  Before every step it waits while (a) the A1 decision python
# (vissim_stackelberg_adapter.py under 20261025_codex_a1) is older than 1,500 s, or (b) another python.exe that is
# neither A1's nor an r4 step is running (one heavy job at a time).  Poll 60 s; gives up after 12 h (exit 3).
# Never kills anything.  Log: AV/r4/logs/r4_driver.log; step stdout/stderr: AV/r4/logs/<step>.out.txt / .err.txt.
$ErrorActionPreference = 'Stop'
$py = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
$tools = Split-Path -Parent $MyInvocation.MyCommand.Path
$r4 = Split-Path -Parent $tools
$logs = Join-Path $r4 'logs'
$log = Join-Path $logs 'r4_driver.log'
New-Item -ItemType Directory -Force -Path $logs | Out-Null
function L([string]$m) { Add-Content -LiteralPath $log -Value ('{0} {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $m) -Encoding UTF8 }
$env:PYTHONHASHSEED = '0'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
function Guard {
  $waited = 0
  while ($true) {
    $now = Get-Date
    $ps = @(Get-CimInstance Win32_Process -Filter "Name='python.exe'")
    $a1 = @($ps | Where-Object { $_.CommandLine -match 'vissim_stackelberg_adapter\.py' -and $_.CommandLine -match '20261025_codex_a1' })
    $age = 0.0
    foreach ($p in $a1) { $x = ($now - $p.CreationDate).TotalSeconds; if ($x -gt $age) { $age = $x } }
    $other = @($ps | Where-Object { $_.CommandLine -notmatch '20261025_codex_a1' -and $_.CommandLine -notmatch 'r4_(fzp_first|firstobs)\.py' })
    if ($age -le 1500 -and $other.Count -eq 0) { return ('a1_decision_age={0:N0}s' -f $age) }
    L ('WAIT a1_decision_age={0:N0}s other_python={1}' -f $age, (($other | ForEach-Object { $_.ProcessId }) -join ','))
    if ($waited -ge 43200) { L 'STOP waited 12 h'; exit 3 }
    Start-Sleep -Seconds 60
    $waited += 60
  }
}
$steps = @()
foreach ($t in 'va_s31', 'j1_s31', 'nc3_s31', 'va_s41', 'j1_s41', 'nc3_s41', 'va_s43', 'j1_s43', 'nc3_s43') {
  $steps += , @("fzp_$t", @('-B', (Join-Path $tools 'r4_fzp_first.py'), $t))
}
$steps += , @('firstobs', @('-B', (Join-Path $tools 'r4_firstobs.py')))
L ('START driver pid={0} steps={1}' -f $PID, $steps.Count)
foreach ($s in $steps) {
  $g = Guard
  $name = $s[0]
  $out = Join-Path $logs ($name + '.out.txt')
  $err = Join-Path $logs ($name + '.err.txt')
  $p = Start-Process -FilePath $py -ArgumentList $s[1] -WorkingDirectory $tools -RedirectStandardOutput $out -RedirectStandardError $err -PassThru -NoNewWindow
  try { $p.PriorityClass = [System.Diagnostics.ProcessPriorityClass]::BelowNormal } catch { }
  L ('STEP {0} pid={1} start {2}' -f $name, $p.Id, $g)
  $p.WaitForExit()
  L ('STEP {0} exit={1}' -f $name, $p.ExitCode)
  if ($p.ExitCode -ne 0) { L ('ABORT at {0}' -f $name); exit 2 }
}
L 'ALL_STEPS_DONE'
exit 0
