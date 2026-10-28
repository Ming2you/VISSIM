# B0: start one PowerShell 5.1 script detached via WMI (Win32_Process.Create), BELOW_NORMAL priority (16384), hidden.
# Writes a launch receipt line to work/b0/launch_receipts.log.  usage: launch_wmi_b0.ps1 -Script <ps1> -ArgString "<args>"
param([Parameter(Mandatory=$true)][string]$Script, [string]$ArgString = '')
$W = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\work\b0'
$cmd = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' + $Script + '" ' + $ArgString
$startup = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ PriorityClass = [uint32]16384; ShowWindow = [uint16]0 }
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = $W; ProcessStartupInformation = $startup }
$line = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' KST ReturnValue=' + $r.ReturnValue + ' ProcessId=' + $r.ProcessId + ' Command=' + $cmd
$line | Add-Content -Encoding UTF8 -LiteralPath (Join-Path $W 'launch_receipts.log')
$line
