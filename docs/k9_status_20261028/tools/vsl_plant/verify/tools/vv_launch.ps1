# vv_launch.ps1 - start vv_queue.py for one jobs file, detached via WMI Win32_Process.Create (BELOW_NORMAL,
# PYTHONHASHSEED=0, python -B, NUMBA_NUM_THREADS removed). Same form as tools/vp_launch.ps1. ASCII only.
# powershell -NoProfile -ExecutionPolicy Bypass -File vv_launch.ps1 -Jobs <jobs.json> -Tag <tag>
param([Parameter(Mandatory=$true)][string]$Jobs, [Parameter(Mandatory=$true)][string]$Tag)
$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
$py = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
$logDir = Join-Path (Split-Path $here -Parent) 'logs'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir ("launch_{0}.txt" -f $Tag)
if (Test-Path -LiteralPath $log) { throw "log exists (never reused): $log" }
$cmd = 'cmd.exe /c set "PYTHONHASHSEED=0" && set "PYTHONDONTWRITEBYTECODE=1" && set "NUMBA_NUM_THREADS=" && "{0}" -B "{1}" "{2}" > "{3}" 2>&1' -f $py, (Join-Path $here 'vv_queue.py'), $Jobs, $log
$startup = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ PriorityClass = [uint32]16384 }
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = $here; ProcessStartupInformation = $startup }
$line = '{0} tag={1} ReturnValue={2} PID={3} priority=BelowNormal(16384) cmd={4}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Tag, $r.ReturnValue, $r.ProcessId, $cmd
Add-Content -LiteralPath (Join-Path $logDir 'wmi_launch_lines.txt') -Value $line -Encoding UTF8
Write-Output $line
