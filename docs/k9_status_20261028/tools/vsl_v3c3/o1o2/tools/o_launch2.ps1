# o_launch2.ps1 - start o_heavy2.ps1 for a jobs file, detached via WMI Win32_Process.Create, BELOW_NORMAL (vsl_v3c3 o1o2).
param([Parameter(Mandatory=$true)][string]$Jobs, [Parameter(Mandatory=$true)][string]$Tag)
$O = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\vsl_v3c3\o1o2'
$cmd = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' + (Join-Path $O 'tools\o_heavy2.ps1') + '" -Jobs "' + $Jobs + '"'
$si = ([wmiclass]'Win32_ProcessStartup').CreateInstance()
$si.PriorityClass = 16384
$si.ShowWindow = 0
$r = ([wmiclass]'Win32_Process').Create($cmd, $O, $si)
$line = (Get-Date).ToString('o') + '  ' + $Tag + '  RV=' + $r.ReturnValue + ' PID=' + $r.ProcessId + ' prio=BelowNormal | ' + $cmd
Add-Content -LiteralPath (Join-Path $O 'logs\wmi_launch_lines.txt') -Value $line
$line
