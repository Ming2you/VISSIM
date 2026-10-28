# VSL_OFFLINE: launch ONE read-only python job detached via WMI (BELOW_NORMAL, PYTHONHASHSEED=0, python -B, threads 1).
# Refuses if any c_port python job (vsl/w1099/readback) is already running, so heavy jobs never overlap.
param([Parameter(Mandatory = $true)][string]$Script, [Parameter(Mandatory = $true)][string]$Tag, [string]$ArgsLine = '')
$ErrorActionPreference = 'Stop'
$V  = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/c_port/vsl'
$py = 'C:/Users/TRLAB/AppData/Local/Programs/Python/Python312/python.exe'
$busy = Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python' -and $_.CommandLine -and $_.CommandLine -match 'c_port' }
if ($busy) { throw ('another c_port python is running: ' + (($busy | ForEach-Object { $_.ProcessId }) -join ',')) }
if (-not (Test-Path -LiteralPath "$V/work/$Script")) { throw "missing $Script" }
$cmd = 'cmd.exe /c "set PYTHONHASHSEED=0&& set PYTHONDONTWRITEBYTECODE=1&& set OMP_NUM_THREADS=1&& set OPENBLAS_NUM_THREADS=1&& set MKL_NUM_THREADS=1&& "' + $py + '" -B "' + $V + '/work/' + $Script + '" ' + $ArgsLine + ' > "' + $V + '/out/' + $Tag + '.log" 2>&1"'
$si = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ PriorityClass = [uint32]16384 }
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = "$V/work"; ProcessStartupInformation = $si }
$stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
"$stamp TAG=$Tag RV=$($r.ReturnValue) PID=$($r.ProcessId) CMD=$cmd" | Out-File -Append -Encoding utf8 "$V/out/launch_receipt.log"
"RV=$($r.ReturnValue) PID=$($r.ProcessId)"
