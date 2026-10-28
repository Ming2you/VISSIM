# B1 prep: start one Windows PowerShell 5.1 script detached via WMI (Win32_Process.Create), BELOW_NORMAL (16384), hidden.
# Same as work/gate1/g1_launch_wmi.ps1 except the priority and the receipt folder. Refuses when chain_b1.state.txt exists.
# usage: b1_launch_wmi.ps1 -Script <ps1> [-ArgString "<args>"]
param([Parameter(Mandatory=$true)][string]$Script, [string]$ArgString = '')
$W = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\work\b1'
if (Test-Path -LiteralPath (Join-Path $W 'chain_b1.state.txt')) { throw 'chain_b1.state.txt exists: the chain was already started once' }
$cmd = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' + $Script + '" ' + $ArgString
$startup = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ PriorityClass = [uint32]16384; ShowWindow = [uint16]0 }
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = $W; ProcessStartupInformation = $startup }
$line = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' KST ReturnValue=' + $r.ReturnValue + ' ProcessId=' + $r.ProcessId + ' Command=' + $cmd
$line | Add-Content -Encoding UTF8 -LiteralPath (Join-Path $W 'launch_receipts.log')
$line
