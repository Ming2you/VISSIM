# Detached launch of one Gates-stage job (WMI Win32_Process.Create, BELOW_NORMAL, PYTHONHASHSEED=0, python -B).
# V-A copy of SP/j1/fix/gates/launch.ps1 (f0ae4042...): log folder = OUTVA\logs (amendment 34 5.0 R4 item 1).
# powershell -NoProfile -File launch.ps1 -Tag <tag> -Script <script.py> [-ArgLine "<args>"]
param([Parameter(Mandatory=$true)][string]$Tag, [Parameter(Mandatory=$true)][string]$Script, [string]$ArgLine = '')
$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
$py = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
$logDir = 'D:\VISSIM_runs\20261001_v3c3\reports\k8\k92_va\offline_gates\logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir ("{0}.txt" -f $Tag)
if (Test-Path -LiteralPath $log) { throw "log exists (never reused): $log" }
$vissimNow = @(Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -like 'VISSIM*' }).Count
$pythonNow = @(Get-Process -Name python -ErrorAction SilentlyContinue).Count
$cmd = 'cmd.exe /c set "PYTHONHASHSEED=0" && set "PYTHONDONTWRITEBYTECODE=1" && "{0}" -B "{1}" {2} > "{3}" 2>&1' -f $py, (Join-Path $here $Script), $ArgLine, $log
$startup = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ PriorityClass = [uint32]16384 }
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = $here; ProcessStartupInformation = $startup }
$line = '{0} tag={1} ReturnValue={2} PID={3} vissim_now={4} python_now={5} priority=BelowNormal(16384) cwd={6} cmd={7}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Tag, $r.ReturnValue, $r.ProcessId, $vissimNow, $pythonNow, $here, $cmd
Add-Content -LiteralPath (Join-Path $here 'wmi_launch_lines.txt') -Value $line -Encoding UTF8
Write-Output $line
