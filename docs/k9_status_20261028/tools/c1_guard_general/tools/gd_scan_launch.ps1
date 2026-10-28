# gd_scan_launch.ps1 — gd_scan.py run (read-only FZP scans, 12 files, one at a time) detached via WMI, BELOW_NORMAL.
# The python script takes/releases the shared heavy lock per FZP (exclusive create, retry 2 s, deletes only its own),
# then pauses 25 s before the next. env: PYTHONHASHSEED=0, python -B, single thread. Refuses if gd_scan is already running.
$ErrorActionPreference = 'Stop'
$G   = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/c_port/c1/guard/general'
$OUT = 'D:/VISSIM-merge/k8_gate_trees/c1/guard_general/data'
$py  = 'C:/Users/TRLAB/AppData/Local/Programs/Python/Python312/python.exe'
if (Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine -match 'gd_scan.py' -and $_.Name -match 'python' }) { throw 'gd_scan already running' }
New-Item -ItemType Directory -Force $OUT | Out-Null
$envs = 'set PYTHONHASHSEED=0&& set PYTHONDONTWRITEBYTECODE=1&& set OMP_NUM_THREADS=1&& set OPENBLAS_NUM_THREADS=1&& set MKL_NUM_THREADS=1&& set GD_SELFTEST_LOCK=&& '
$cmd = 'cmd.exe /c "' + $envs + '"' + $py + '" -B "' + $G + '/tools/gd_scan.py" run "' + $G + '/inventory.json" "' + $OUT + '" >> "' + $OUT + '/gd_scan.log" 2>&1"'
$si = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ PriorityClass = [uint32]16384 }
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = $G; ProcessStartupInformation = $si }
$stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
"$stamp KST RV=$($r.ReturnValue) PID=$($r.ProcessId) CMD=$cmd" | Out-File -Append -Encoding utf8 "$OUT/launch_receipt.log"
"RV=$($r.ReturnValue) PID=$($r.ProcessId)"
