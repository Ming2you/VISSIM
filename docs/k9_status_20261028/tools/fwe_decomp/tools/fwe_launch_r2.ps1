param([Parameter(Mandatory=$true)][string]$Jobs, [string]$Name = 'r2heavy', [string]$ExtraEnv = '')
# fwe_launch_r2.ps1 - D-K9-106 R2: start fwe_heavy_r2.py detached from this session (WMI Win32_Process.Create,
# PriorityClass BELOW_NORMAL = 16384, hidden). $Jobs = space separated job names (e.g. "H6 H7"). $ExtraEnv = "K=V;K=V"
# (self-test only). Env for the queue and its children: PYTHONHASHSEED=0, bytecode off, thread vars 1.
$FD = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\fwe_decomp'
$PY = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$cmdFile = Join-Path $FD ("logs\launch_{0}_{1}.cmd" -f $Name, $stamp)
$logFile = Join-Path $FD ("logs\launch_{0}_{1}.log" -f $Name, $stamp)
$lines = @('@echo off', 'set PYTHONHASHSEED=0', 'set PYTHONDONTWRITEBYTECODE=1', 'set OMP_NUM_THREADS=1', 'set OPENBLAS_NUM_THREADS=1', 'set MKL_NUM_THREADS=1')
if ($ExtraEnv -ne '') { foreach ($kv in $ExtraEnv.Split(';')) { if ($kv -ne '') { $lines += ('set "' + $kv + '"') } } }
$lines += ('"' + $PY + '" -B "' + $FD + '\tools\fwe_heavy_r2.py" ' + $Jobs + ' > "' + $logFile + '" 2>&1')
Set-Content -Path $cmdFile -Value $lines -Encoding ascii
$si = ([wmiclass]'Win32_ProcessStartup').CreateInstance()
$si.PriorityClass = 16384
$si.ShowWindow = 0
$r = ([wmiclass]'Win32_Process').Create("cmd.exe /c `"$cmdFile`"", $FD, $si)
"ReturnValue=$($r.ReturnValue) PID=$($r.ProcessId) cmd=$cmdFile log=$logFile at $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
