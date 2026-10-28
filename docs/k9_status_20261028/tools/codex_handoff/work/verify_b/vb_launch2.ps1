# VERIFY_B: 읽기만 하는 파이썬 도구 하나를 WMI 로 세션과 떨어져 BELOW_NORMAL 로 띄움. 우리 vb_* 가 돌면 거부.
param([Parameter(Mandatory = $true)][string]$Script, [string]$Tag = 'job')
$ErrorActionPreference = 'Stop'
$V  = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work/verify_b'
$py = 'C:/Users/TRLAB/AppData/Local/Programs/Python/Python312/python.exe'
if (Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine -match 'verify_b/vb_[a-z0-9_]+\.py' -and $_.Name -match 'python' }) { throw 'another vb_* python is running' }
if (-not (Test-Path -LiteralPath "$V/$Script")) { throw "missing $Script" }
$cmd = 'cmd.exe /c "set PYTHONHASHSEED=0&& set PYTHONDONTWRITEBYTECODE=1&& set OMP_NUM_THREADS=1&& set OPENBLAS_NUM_THREADS=1&& set MKL_NUM_THREADS=1&& "' + $py + '" -B "' + $V + '/' + $Script + '" > "' + $V + '/out/' + $Tag + '.log" 2>&1"'
$si = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ PriorityClass = [uint32]16384 }
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = $V; ProcessStartupInformation = $si }
$stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
"$stamp RV=$($r.ReturnValue) PID=$($r.ProcessId) CMD=$cmd" | Out-File -Append -Encoding utf8 "$V/out/launch_receipt.log"
"RV=$($r.ReturnValue) PID=$($r.ProcessId)"
