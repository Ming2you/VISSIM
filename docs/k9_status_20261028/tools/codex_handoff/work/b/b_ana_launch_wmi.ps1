# Start b_ana.ps1 detached via WMI (Win32_Process.Create) under Windows PowerShell 5.1, BELOW_NORMAL (16384), hidden.
# Refuses when another b_ana.ps1 is running (one heavy job at a time). Appends a receipt line to work/b/launch_receipts.log.
param([Parameter(Mandatory = $true)][ValidateSet('prescan', 's31stage')][string]$Plan)
$ErrorActionPreference = 'Stop'
$W = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\work\b'
$busy = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(powershell|pwsh)\.exe$' -and $_.CommandLine -match '-File "[^"]*\\b_ana\.ps1"' -and $_.ProcessId -ne $PID })
if ($busy.Count) { throw ('b_ana already running: ' + (($busy | ForEach-Object { $_.ProcessId }) -join ',')) }
$cmd = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' + (Join-Path $W 'b_ana.ps1') + '" -Plan ' + $Plan
$startup = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ PriorityClass = [uint32]16384; ShowWindow = [uint16]0 }
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = $W; ProcessStartupInformation = $startup }
$line = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' KST ana plan=' + $Plan + ' ReturnValue=' + $r.ReturnValue + ' ProcessId=' + $r.ProcessId + ' Priority=16384 Command=' + $cmd
$line | Add-Content -Encoding UTF8 -LiteralPath (Join-Path $W 'launch_receipts.log')
$line
