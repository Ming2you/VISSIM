# rb_launch.ps1 (c_port/readback, 2026-10-27 KST): run one read-only python tool detached via WMI, BELOW_NORMAL (16384),
# python -B, PYTHONHASHSEED=0, env_hsw (OPENBLAS_CORETYPE=Haswell, NPY_DISABLE_CPU_FEATURES=AVX512F AVX512CD AVX512_SKX AVX512_CLX,
# NUMBA_CPU_NAME=haswell), threads 1. Refuses if any python with 'c_port' in its command line is running (one heavy job at a time).
param([Parameter(Mandatory = $true)][string]$Script, [string]$ArgLine = '', [string]$Tag = 'job')
$ErrorActionPreference = 'Stop'
$RB = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/c_port/readback'
$py = 'C:/Users/TRLAB/AppData/Local/Programs/Python/Python312/python.exe'
$busy = Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python' -and $_.CommandLine -and $_.CommandLine -match 'c_port' }
if ($busy) { throw ('another c_port python is running: ' + (($busy | ForEach-Object { $_.ProcessId }) -join ',')) }
if (-not (Test-Path -LiteralPath "$RB/tools/$Script")) { throw "missing $Script" }
$envs = 'set PYTHONHASHSEED=0&& set PYTHONDONTWRITEBYTECODE=1&& set OMP_NUM_THREADS=1&& set OPENBLAS_NUM_THREADS=1&& set MKL_NUM_THREADS=1&& set NUMBA_NUM_THREADS=1&& set OPENBLAS_CORETYPE=Haswell&& set NPY_DISABLE_CPU_FEATURES=AVX512F AVX512CD AVX512_SKX AVX512_CLX&& set NUMBA_CPU_NAME=haswell&& '
$cmd = 'cmd.exe /c "' + $envs + '"' + $py + '" -B "' + $RB + '/tools/' + $Script + '" ' + $ArgLine + ' > "' + $RB + '/logs/' + $Tag + '.log" 2>&1"'
$si = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ PriorityClass = [uint32]16384 }
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = $RB; ProcessStartupInformation = $si }
$stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
"$stamp RV=$($r.ReturnValue) PID=$($r.ProcessId) CMD=$cmd" | Out-File -Append -Encoding utf8 "$RB/logs/launch_receipt.log"
"RV=$($r.ReturnValue) PID=$($r.ProcessId)"
