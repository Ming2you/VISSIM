# VSL_OFFLINE: launch ONE PowerShell chain script detached via WMI (BELOW_NORMAL). Refuses if any c_port python runs.
param([Parameter(Mandatory = $true)][string]$Script, [Parameter(Mandatory = $true)][string]$Tag, [string]$ArgsLine = '')
$ErrorActionPreference = 'Stop'
$V  = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/c_port/vsl'
$busy = Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python' -and $_.CommandLine -and $_.CommandLine -match 'c_port' }
if ($busy) { throw ('another c_port python is running: ' + (($busy | ForEach-Object { $_.ProcessId }) -join ',')) }
if (-not (Test-Path -LiteralPath "$V/work/$Script")) { throw "missing $Script" }
$cmd = 'powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' + $V + '/work/' + $Script + '" ' + $ArgsLine
$si = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ PriorityClass = [uint32]16384 }
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = "$V/work"; ProcessStartupInformation = $si }
$stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
"$stamp TAG=$Tag RV=$($r.ReturnValue) PID=$($r.ProcessId) CMD=$cmd" | Out-File -Append -Encoding utf8 "$V/out/launch_receipt.log"
"RV=$($r.ReturnValue) PID=$($r.ProcessId)"
