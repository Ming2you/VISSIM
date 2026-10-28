param([Parameter(Mandatory=$true)][string]$CmdFile, [string]$WorkDir)
# fresh WMI detached launcher for VERIFY_HANDOFF_RESULTS (BELOW_NORMAL = 16384)
$si = ([wmiclass]'Win32_ProcessStartup').CreateInstance()
$si.PriorityClass = 16384
$si.ShowWindow = 0
$r = ([wmiclass]'Win32_Process').Create("cmd.exe /c `"$CmdFile`"", $WorkDir, $si)
"ReturnValue=$($r.ReturnValue) PID=$($r.ProcessId) at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
