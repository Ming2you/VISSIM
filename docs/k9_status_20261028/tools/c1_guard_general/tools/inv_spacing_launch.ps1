# inv_spacing_launch.ps1 — inv_spacing.py (read-only FZP scan, one file) detached via WMI, BELOW_NORMAL.
# The python script itself takes/releases the shared heavy lock (exclusive create, retry 15 s, deletes only its own).
# env: PYTHONHASHSEED=0, python -B, single thread. Refuses if our inv_spacing is already running.
$ErrorActionPreference = 'Stop'
$G   = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/c_port/c1/guard/general'
$OUT = 'D:/VISSIM-merge/k8_gate_trees/c1/guard_general'
$py  = 'C:/Users/TRLAB/AppData/Local/Programs/Python/Python312/python.exe'
$fzp = 'D:/VISSIM_runs/20261001_v3c3/s31_v3c3nc/run/vissim_eval/baseline_s31_v3c3nc_001.fzp'
if (Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine -match 'inv_spacing.py' -and $_.Name -match 'python' }) { throw 'inv_spacing already running' }
if (-not (Test-Path -LiteralPath $fzp)) { throw 'missing fzp' }
New-Item -ItemType Directory -Force $OUT | Out-Null
$envs = 'set PYTHONHASHSEED=0&& set PYTHONDONTWRITEBYTECODE=1&& set OMP_NUM_THREADS=1&& set OPENBLAS_NUM_THREADS=1&& set MKL_NUM_THREADS=1&& set INV_SELFTEST_LOCK=&& '
$cmd = 'cmd.exe /c "' + $envs + '"' + $py + '" -B "' + $G + '/tools/inv_spacing.py" "' + $fzp + '" "' + $G + '/work/net_facts.json" "' + $OUT + '/spacing_nc3_s31.json" > "' + $OUT + '/spacing_nc3_s31.log" 2>&1"'
$si = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ PriorityClass = [uint32]16384 }
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = $G; ProcessStartupInformation = $si }
$stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
"$stamp KST RV=$($r.ReturnValue) PID=$($r.ProcessId) CMD=$cmd" | Out-File -Append -Encoding utf8 "$OUT/launch_receipt.log"
"RV=$($r.ReturnValue) PID=$($r.ProcessId)"
