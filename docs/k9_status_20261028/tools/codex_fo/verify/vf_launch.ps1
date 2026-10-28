# vf_launch.ps1 - VERIFY_FO: start vf_queue.ps1 once, detached from the session via WMI Win32_Process.Create,
# BELOW_NORMAL (16384), hidden. Refuses if the queue state file already exists (once-only).
param([Parameter(Mandatory=$true)][string]$QueueName)
$VFDIR = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\fo\verify'
$stateFile = Join-Path $VFDIR ('out\' + $QueueName + '.state.txt')
if (Test-Path -LiteralPath $stateFile) { throw ($stateFile + ' exists: queue already started once') }
$queue = Join-Path $VFDIR 'vf_queue.ps1'
$cmdLine = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' + $queue + '" -QueueName ' + $QueueName
$startup = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ PriorityClass = [uint32]16384; ShowWindow = [uint16]0 }
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmdLine; CurrentDirectory = $VFDIR; ProcessStartupInformation = $startup }
$receipt = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' KST ReturnValue=' + $r.ReturnValue + ' ProcessId=' + $r.ProcessId + ' Command=' + $cmdLine
$receipt | Out-File -Append -Encoding utf8 -LiteralPath (Join-Path $VFDIR 'out\launch_receipts.log')
$receipt
