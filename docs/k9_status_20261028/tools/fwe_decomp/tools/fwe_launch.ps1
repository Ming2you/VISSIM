# fwe_launch.ps1 (fwe_decomp, D-K9-106, 2026-10-27 KST): start tools/fwe_heavy.py <jobs.json> detached via WMI
# (Win32_Process.Create), PriorityClass BELOW_NORMAL (16384), python -B, PYTHONHASHSEED=0, PYTHONDONTWRITEBYTECODE=1,
# OMP/OPENBLAS/MKL threads 1. Writes a receipt line (PID) to logs/heavy/launch_receipt.log. ASCII only.
param([Parameter(Mandatory = $true)][string]$Jobs, [string]$Tag = 'heavy')
$ErrorActionPreference = 'Stop'
$FD = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/fwe_decomp'
$py = 'C:/Users/TRLAB/AppData/Local/Programs/Python/Python312/python.exe'
if (-not (Test-Path -LiteralPath $Jobs)) { throw "missing $Jobs" }
New-Item -ItemType Directory -Force -Path "$FD/logs/heavy" | Out-Null
$envs = 'set PYTHONHASHSEED=0&& set PYTHONDONTWRITEBYTECODE=1&& set PYTHONIOENCODING=utf-8&& set OMP_NUM_THREADS=1&& set OPENBLAS_NUM_THREADS=1&& set MKL_NUM_THREADS=1&& '
$cmd = 'cmd.exe /c "' + $envs + '"' + $py + '" -B "' + $FD + '/tools/fwe_heavy.py" "' + $Jobs + '" > "' + $FD + '/logs/heavy/' + $Tag + '.runner.txt" 2>&1"'
$si = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ PriorityClass = [uint32]16384 }
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = $FD; ProcessStartupInformation = $si }
$stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
"$stamp KST RV=$($r.ReturnValue) PID=$($r.ProcessId) CMD=$cmd" | Out-File -Append -Encoding utf8 "$FD/logs/heavy/launch_receipt.log"
"RV=$($r.ReturnValue) PID=$($r.ProcessId)"
