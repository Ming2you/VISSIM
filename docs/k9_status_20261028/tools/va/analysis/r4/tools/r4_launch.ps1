# Launch r4_driver.ps1 detached (WMI Win32_Process.Create, BELOW_NORMAL = 16384, hidden).  Prints ReturnValue and PID
# and appends the line to AV/r4/logs/wmi_lines.txt.
$ErrorActionPreference = 'Stop'
$tools = Split-Path -Parent $MyInvocation.MyCommand.Path
$logs = Join-Path (Split-Path -Parent $tools) 'logs'
New-Item -ItemType Directory -Force -Path $logs | Out-Null
$drv = Join-Path $tools 'r4_driver.ps1'
$cmd = 'powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File "{0}"' -f $drv
$startup = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ PriorityClass = [uint32]16384; ShowWindow = [uint16]0 }
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = $tools; ProcessStartupInformation = $startup }
$line = '{0} RV={1} PID={2} prio=BelowNormal | {3}' -f (Get-Date -Format o), $r.ReturnValue, $r.ProcessId, $cmd
Add-Content -LiteralPath (Join-Path $logs 'wmi_lines.txt') -Value $line -Encoding UTF8
Write-Output $line
