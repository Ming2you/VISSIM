# VERIFY_B: vb_scan.py 를 WMI 로 세션과 떨어져 BELOW_NORMAL 로 한 번 띄움 (읽기만 하는 스캔)
$ErrorActionPreference = 'Stop'
$V  = 'C:/Users/TRLAB/AppData/Local/Temp/claude/C--Users-TRLAB-Desktop----/491ef689-f002-4605-9dc5-e6d363495788/scratchpad/k8/codex_handoff/work/verify_b'
$py = 'C:/Users/TRLAB/AppData/Local/Programs/Python/Python312/python.exe'
if (Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.CommandLine -match 'vb_scan\.py' }) { throw 'vb_scan already running' }
$files = [ordered]@{
  'b43'  = 'D:/VISSIM_runs/20261026_codex_b_v3c3/s43/sdmpc/vissim_eval/sdmpc31_sdmpc9000_s43_001.fzp'
  'nc43' = 'D:/VISSIM_runs/20261001_v3c3/s43_v3c3nc/run/vissim_eval/baseline_s43_v3c3nc_001.fzp'
  'b31'  = 'D:/VISSIM_runs/20261026_codex_b_v3c3/s31/sdmpc/vissim_eval/sdmpc31_sdmpc9000_s31_001.fzp'
  'nc31' = 'D:/VISSIM_runs/20261001_v3c3/s31_v3c3nc/run/vissim_eval/baseline_s31_v3c3nc_001.fzp'
  'b41'  = 'D:/VISSIM_runs/20261026_codex_b_v3c3/s41/sdmpc/vissim_eval/sdmpc31_sdmpc9000_s41_001.fzp'
  'nc41' = 'D:/VISSIM_runs/20261001_v3c3/s41_v3c3nc/run/vissim_eval/baseline_s41_v3c3nc_001.fzp'
  'va31' = 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s31/vissim_eval/sdmpc31_sdmpc31_v3c3_k92va_s31_001.fzp'
  'va41' = 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s41/vissim_eval/sdmpc31_sdmpc31_v3c3_k92va_s41_001.fzp'
  'va43' = 'D:/VISSIM_runs/20261023_sdmpc31_k92/sdmpc31_v3c3_k92va_s43/vissim_eval/sdmpc31_sdmpc31_v3c3_k92va_s43_001.fzp'
}
foreach ($k in $files.Keys) { if (-not (Test-Path -LiteralPath $files[$k])) { throw "missing $k" } }
$argsList = ($files.Keys | ForEach-Object { '"' + $_ + '=' + $files[$_] + '"' }) -join ' '
New-Item -ItemType Directory -Force "$V/out" | Out-Null
$cmd = 'cmd.exe /c "set PYTHONHASHSEED=0&& set PYTHONDONTWRITEBYTECODE=1&& set OMP_NUM_THREADS=1&& set OPENBLAS_NUM_THREADS=1&& set MKL_NUM_THREADS=1&& "' + $py + '" -B "' + $V + '/vb_scan.py" ' + $argsList + ' > "' + $V + '/out/scan.log" 2>&1"'
$si = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ PriorityClass = [uint32]16384 }
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = $V; ProcessStartupInformation = $si }
$stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
"$stamp RV=$($r.ReturnValue) PID=$($r.ProcessId) CMD=$cmd" | Out-File -Append -Encoding utf8 "$V/out/launch_receipt.log"
"RV=$($r.ReturnValue) PID=$($r.ProcessId)"
