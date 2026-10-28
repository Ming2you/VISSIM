# Launch run_replay.ps1 detached via WMI (Win32_Process.Create), BELOW_NORMAL priority.
param([Parameter(Mandatory=$true)][string]$ArgLine)
$WORK = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\work\a0'
$cmd = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' + (Join-Path $WORK 'run_replay.ps1') + '" ' + $ArgLine
$startup = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ PriorityClass = [uint32]16384; ShowWindow = [uint16]0 }
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = $WORK; ProcessStartupInformation = $startup }
"ReturnValue=$($r.ReturnValue) ProcessId=$($r.ProcessId)"
"Command=$cmd"
