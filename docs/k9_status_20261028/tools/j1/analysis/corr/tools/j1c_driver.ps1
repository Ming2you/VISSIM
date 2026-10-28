# J1 correction driver (D-K9-89 7) = copy of r4_driver_v2.ps1 with: log name j1c_driver.log; guard = wait only
# while a heavy python of this workflow runs (Gate 1 replays, codex_handoff\work tools, r4 tools; never the B run
# itself or other sessions); steps = 9 scans + r4_firstobs.py + j1c_compare.py.  Original r4 v2 header follows.
# V-A r4 driver v2 (= r4_driver.ps1 + exit-code fix: the process handle is read right after Start-Process so that
# ExitCode is filled in Windows PowerShell 5.1; v1 logged an empty exit code and stopped after a successful step): runs the 9 FZP first-observation scans (one at a time) and then r4_firstobs.py.
# Started detached by r4_launch.ps1 (WMI Win32_Process.Create, BELOW_NORMAL); children inherit BELOW_NORMAL and are
# also set to BelowNormal explicitly.  Before every step it waits while (a) the A1 decision python
# (vissim_stackelberg_adapter.py under 20261025_codex_a1) is older than 1,500 s, or (b) another python.exe that is
# neither A1's nor an r4 step is running (one heavy job at a time).  Poll 60 s; gives up after 12 h (exit 3).
# Never kills anything.  Log: AV/r4/logs/r4_driver_v2.log; step stdout/stderr: AV/r4/logs/<step>.out.txt / .err.txt.
$ErrorActionPreference = 'Stop'
$py = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
$tools = Split-Path -Parent $MyInvocation.MyCommand.Path
$r4 = Split-Path -Parent $tools
$logs = Join-Path $r4 'logs'
$log = Join-Path $logs 'j1c_driver.log'
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
    $vis = @(Get-CimInstance Win32_Process -Filter "Name='VISSIM200.exe'")
    $other = @($ps | Where-Object { $_.CommandLine -match 'codexhandoff\\gate1|codex_handoff\\work\\|k92\\va\\analysis\\r4\\tools' })
    if ($other.Count -eq 0) { return ('vissim_pids={0} python_total={1}' -f (($vis | ForEach-Object { $_.ProcessId }) -join ','), $ps.Count) }
    L ('WAIT workflow_heavy_python={0}' -f (($other | ForEach-Object { $_.ProcessId }) -join ','))
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
$steps += , @('j1c_compare', @('-B', (Join-Path $tools 'j1c_compare.py')))
L ('START driver pid={0} steps={1}' -f $PID, $steps.Count)
foreach ($s in $steps) {
  $g = Guard
  $name = $s[0]
  $out = Join-Path $logs ($name + '.out.txt')
  $err = Join-Path $logs ($name + '.err.txt')
  $p = Start-Process -FilePath $py -ArgumentList $s[1] -WorkingDirectory $tools -RedirectStandardOutput $out -RedirectStandardError $err -PassThru -NoNewWindow
  $null = $p.Handle
  try { $p.PriorityClass = [System.Diagnostics.ProcessPriorityClass]::BelowNormal } catch { }
  L ('STEP {0} pid={1} start {2}' -f $name, $p.Id, $g)
  $p.WaitForExit()
  L ('STEP {0} exit={1}' -f $name, $p.ExitCode)
  if ($p.ExitCode -ne 0) { L ('ABORT at {0}' -f $name); exit 2 }
}
L 'ALL_STEPS_DONE'
exit 0
