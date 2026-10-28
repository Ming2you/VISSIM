# Launch run_a1_analysis.ps1 detached via WMI (Win32_Process.Create), BELOW_NORMAL priority (16384), hidden window.
param([switch]$Smoke, [string]$Steps = 'scan,metrics,first,unins,ours,table,fzpdiff,trace')
$F = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\work\a1\full'
$cmd = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' + (Join-Path $F 'run_a1_analysis.ps1') + '" -Steps ' + $Steps + $(if ($Smoke) { ' -Smoke' } else { '' })
$startup = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ PriorityClass = [uint32]16384; ShowWindow = [uint16]0 }
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = $F; ProcessStartupInformation = $startup }
"ReturnValue=$($r.ReturnValue) ProcessId=$($r.ProcessId)"
"Command=$cmd"
