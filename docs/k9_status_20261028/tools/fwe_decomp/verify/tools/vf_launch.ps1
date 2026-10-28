param([Parameter(Mandatory=$true)][string]$JobsJson, [string]$Lock = 'D:/VISSIM-merge/k8_gate_trees/heavy.lock', [string]$Pause = '25')
# vf_launch.ps1 - VERIFY_FWE: start vf_runner.py detached (WMI Win32_Process.Create, BELOW_NORMAL = 16384, hidden).
# Env: PYTHONHASHSEED=0, no bytecode, thread vars 1. Writes a .cmd and a log under verify/logs only.
$VD = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\fwe_decomp\verify'
$PY = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$cmdFile = Join-Path $VD ("logs\launch_{0}.cmd" -f $stamp)
$logFile = Join-Path $VD ("logs\launch_{0}.log" -f $stamp)
$lines = @('@echo off', 'set PYTHONHASHSEED=0', 'set PYTHONDONTWRITEBYTECODE=1', 'set OMP_NUM_THREADS=1', 'set OPENBLAS_NUM_THREADS=1', 'set MKL_NUM_THREADS=1')
$lines += ('"' + $PY + '" -B "' + $VD + '\tools\vf_runner.py" "' + $JobsJson + '" "' + $Lock + '" ' + $Pause + ' > "' + $logFile + '" 2>&1')
Set-Content -Path $cmdFile -Value $lines -Encoding ascii
$si = ([wmiclass]'Win32_ProcessStartup').CreateInstance()
$si.PriorityClass = 16384
$si.ShowWindow = 0
$r = ([wmiclass]'Win32_Process').Create("cmd.exe /c `"$cmdFile`"", $VD, $si)
"ReturnValue=$($r.ReturnValue) PID=$($r.ProcessId) cmd=$cmdFile log=$logFile at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
