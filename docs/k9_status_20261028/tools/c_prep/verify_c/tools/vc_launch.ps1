# vc_launch.ps1 -- start one verify_c python job detached via WMI, BELOW_NORMAL, env_hsw, PYTHONHASHSEED=0, python -B, threads 1.
# Usage: vc_launch.ps1 <tool.py> <arg1> <logname>. Refuses if any c_port python job (vc_/w1099_/rb_/v1_..v4_) is already running.
param([string]$Tool, [string]$Arg1, [string]$LogName)
$ErrorActionPreference = 'Stop'
$V  = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/c_port/verify_c'
$py = 'C:/Users/TRLAB/AppData/Local/Programs/Python/Python312/python.exe'
$busy = Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python' -and $_.CommandLine -and $_.CommandLine -match 'c_port' }
if ($busy) { throw ('c_port python already running: ' + (($busy | ForEach-Object { $_.ProcessId }) -join ',')) }
$envs = 'set PYTHONHASHSEED=0&& set PYTHONDONTWRITEBYTECODE=1&& set OPENBLAS_CORETYPE=Haswell&& set NPY_DISABLE_CPU_FEATURES=AVX512F AVX512CD AVX512_SKX AVX512_CLX&& set NUMBA_CPU_NAME=haswell&& set OMP_NUM_THREADS=1&& set OPENBLAS_NUM_THREADS=1&& set MKL_NUM_THREADS=1&& '
$cmd = 'cmd.exe /c "' + $envs + '"' + $py + '" -B "' + $V + '/tools/' + $Tool + '" "' + $Arg1 + '" > "' + $V + '/logs/' + $LogName + '" 2>&1"'
$si = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ PriorityClass = [uint32]16384 }
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = $V; ProcessStartupInformation = $si }
$stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
"$stamp RV=$($r.ReturnValue) PID=$($r.ProcessId) TOOL=$Tool" | Out-File -Append -Encoding utf8 "$V/logs/launch_receipt.log"
"RV=$($r.ReturnValue) PID=$($r.ProcessId)"
