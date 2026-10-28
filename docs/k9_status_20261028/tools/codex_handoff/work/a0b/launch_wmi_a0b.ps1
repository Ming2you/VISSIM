# Launch run_queue_a0b.ps1 detached via WMI (Win32_Process.Create), BELOW_NORMAL priority (16384), hidden window.
$W = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\work\a0b'
$cmd = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' + (Join-Path $W 'run_queue_a0b.ps1') + '"'
$startup = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ PriorityClass = [uint32]16384; ShowWindow = [uint16]0 }
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = $W; ProcessStartupInformation = $startup }
"ReturnValue=$($r.ReturnValue) ProcessId=$($r.ProcessId)"
"Command=$cmd"
