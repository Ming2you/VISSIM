# R2c launch (D-K9-79): the two rows of D:\VISSIM_runs\20261001_v3c3\launch_lines_rm10681.txt, detached via WMI
# (Win32_Process.Create, CurrentDirectory = the v3c3 folder), 20 s apart, like the rm arms.
# Checks before each row: VISSIM count < 4 PC-wide (others are counted, never touched), run\ and launch.log absent,
# C: and D: >= 8 GB free, the rule python exists.  Each launch is appended to wmi_launch_lines_rm10681.txt.
# Nothing is killed here.
$ErrorActionPreference = 'Stop'
$root = 'D:\VISSIM_runs\20261001_v3c3'
$rec = Join-Path $root 'wmi_launch_lines_rm10681.txt'
$rows = @(Get-Content -LiteralPath (Join-Path $root 'launch_lines_rm10681.txt') -Encoding ASCII | Where-Object { $_ -and -not $_.StartsWith('#') })
if ($rows.Count -ne 2) { throw 'expected 2 launch rows' }
if (-not (Test-Path -LiteralPath 'C:\Users\TRLAB\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe')) { throw 'rule python missing' }
$head = (& git --no-optional-locks -C 'D:\VISSIM-merge\sim3' rev-parse --short=8 HEAD)
$i = 0
foreach ($row in $rows) {
  $parts = $row -split '  ', 2
  $tag = $parts[0]; $cmd = $parts[1]
  if ($tag -notmatch '^s(31|41)_v3c3rm10681$') { throw "unexpected label $tag" }
  $arm = Join-Path $root $tag
  if (Test-Path -LiteralPath (Join-Path $arm 'run')) { throw "run folder exists: $tag" }
  if (Test-Path -LiteralPath (Join-Path $arm 'launch.log')) { throw "launch.log exists: $tag" }
  if ($i -gt 0) { Start-Sleep -Seconds 20 }
  $freeD = (New-Object System.IO.DriveInfo 'D:\').AvailableFreeSpace
  $freeC = (New-Object System.IO.DriveInfo 'C:\').AvailableFreeSpace
  if ($freeD -lt 8GB -or $freeC -lt 8GB) { throw ('disk below 8 GB: C {0} D {1}' -f $freeC, $freeD) }
  $vis = @(Get-Process -Name 'VISSIM*' -ErrorAction SilentlyContinue).Count
  if ($vis -ge 4) { throw "seats full: $vis VISSIM running" }
  $t = Get-Date
  $r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine = $cmd; CurrentDirectory = $root}
  $line = '{0}  {1}  RV={2} PID={3} VISSIM_before={4} cwd={5} sim3_head={6} freeC_GB={7:N1} freeD_GB={8:N1} | {9}' -f `
    $t.ToString('o'), $tag, $r.ReturnValue, $r.ProcessId, $vis, $root, $head, ($freeC / 1GB), ($freeD / 1GB), $cmd
  Add-Content -LiteralPath $rec -Value $line -Encoding UTF8
  Write-Output $line
  if ($r.ReturnValue -ne 0) { throw "WMI create failed for $tag (RV=$($r.ReturnValue))" }
  $i++
}
