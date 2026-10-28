# FO prep: start one Windows PowerShell 5.1 script detached via WMI (Win32_Process.Create), BELOW_NORMAL (16384), hidden.
# Copy of work/b1/b1_launch_wmi.ps1 with the folder and the once-only state file changed. Refuses when the state file exists.
# usage: fo_launch_wmi.ps1 -Script <ps1> -StateName <state file name in this folder> [-ArgString "<args>"]
param([Parameter(Mandatory=$true)][string]$Script, [Parameter(Mandatory=$true)][string]$StateName, [string]$ArgString = '')
$W = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\fo\work\build'
if (Test-Path -LiteralPath (Join-Path (Split-Path -Parent $Script) $StateName)) { throw ($StateName + ' exists: the script was already started once') }
$cmd = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' + $Script + '" ' + $ArgString
$startup = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ PriorityClass = [uint32]16384; ShowWindow = [uint16]0 }
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = (Split-Path -Parent $Script); ProcessStartupInformation = $startup }
$line = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' KST ReturnValue=' + $r.ReturnValue + ' ProcessId=' + $r.ProcessId + ' Command=' + $cmd
$line | Add-Content -Encoding UTF8 -LiteralPath (Join-Path $W 'launch_receipts.log')
$line
