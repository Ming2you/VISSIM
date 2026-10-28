$ErrorActionPreference = 'Continue'
$W = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\work\vfy_a1b0'
$O = Join-Path $W 'out'
$PY = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
$state = Join-Path $W 'run_vfy.state.txt'
$env:PYTHONHASHSEED = '0'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
$env:PYTHONIOENCODING = 'utf-8'
"START $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') pid=$PID" | Out-File -FilePath $state -Encoding utf8
function Step($name, $argList) {
  $t0 = Get-Date
  $p = Start-Process -FilePath $PY -ArgumentList $argList -NoNewWindow -PassThru -RedirectStandardOutput (Join-Path $O ($name + '.out.txt')) -RedirectStandardError (Join-Path $O ($name + '.err.txt'))
  try { $p.PriorityClass = 'BelowNormal' } catch {}
  $p.WaitForExit()
  $p.Refresh()
  $code = $p.ExitCode
  if ($null -eq $code) { $code = 'null' }
  "$name exit=$code sec=$([math]::Round(((Get-Date) - $t0).TotalSeconds,1)) at $(Get-Date -Format 'HH:mm:ss')" | Out-File -FilePath $state -Append -Encoding utf8
}
$scans = @(
  @('a1', 'D:\VISSIM_runs\20261025_codex_a1_s29\sdmpc\vissim_eval\sdmpc31_sdmpc8100_s29_001.fzp', '--tmax 8100'),
  @('joint', 'D:\VISSIM_handoff\20261024\raw\joint\sdmpc\vissim_eval\sdmpc31_sdmpc8100_s29_001.fzp', '--tmax 8100'),
  @('nc', 'D:\VISSIM_handoff\20261024\raw\nc\vissim_eval\sdmpc31_nc9000_s29_001.fzp', '--tmax 8100'),
  @('lnc', 'D:\VISSIM_runs\vsl_repro_s29\none\run\vissim_eval\vsl_seed29_none_001.fzp', '--tmax 8100'),
  @('va_s31', 'D:\VISSIM_runs\20261023_sdmpc31_k92\sdmpc31_v3c3_k92va_s31\vissim_eval\sdmpc31_sdmpc31_v3c3_k92va_s31_001.fzp', '--skip010 --tmax 8995.1'),
  @('va_s41', 'D:\VISSIM_runs\20261023_sdmpc31_k92\sdmpc31_v3c3_k92va_s41\vissim_eval\sdmpc31_sdmpc31_v3c3_k92va_s41_001.fzp', '--skip010 --tmax 8995.1'),
  @('va_s43', 'D:\VISSIM_runs\20261023_sdmpc31_k92\sdmpc31_v3c3_k92va_s43\vissim_eval\sdmpc31_sdmpc31_v3c3_k92va_s43_001.fzp', '--skip010 --tmax 8995.1'),
  @('j1_s31', 'D:\VISSIM_runs\20261004_sdmpc31_k8\sdmpc31_v3c3_k8j1r_s31\vissim_eval\sdmpc31_sdmpc31_v3c3_k8j1r_s31_001.fzp', '--skip010 --tmax 8995.1'),
  @('j1_s41', 'D:\VISSIM_runs\20261004_sdmpc31_k8\sdmpc31_v3c3_k8j1_s41\vissim_eval\sdmpc31_sdmpc31_v3c3_k8j1_s41_001.fzp', '--skip010 --tmax 8995.1'),
  @('j1_s43', 'D:\VISSIM_runs\20261004_sdmpc31_k8\sdmpc31_v3c3_k8j1_s43\vissim_eval\sdmpc31_sdmpc31_v3c3_k8j1_s43_001.fzp', '--skip010 --tmax 8995.1'),
  @('nc3_s31', 'D:\VISSIM_runs\20261001_v3c3\s31_v3c3nc\run\vissim_eval\baseline_s31_v3c3nc_001.fzp', '--skip010 --tmax 8995.1'),
  @('nc3_s41', 'D:\VISSIM_runs\20261001_v3c3\s41_v3c3nc\run\vissim_eval\baseline_s41_v3c3nc_001.fzp', '--skip010 --tmax 8995.1'),
  @('nc3_s43', 'D:\VISSIM_runs\20261001_v3c3\s43_v3c3nc\run\vissim_eval\baseline_s43_v3c3nc_001.fzp', '--skip010 --tmax 8995.1')
)
foreach ($s in $scans) {
  $out = Join-Path $O ('scan_' + $s[0] + '.json.gz')
  Step ('scan_' + $s[0]) ('-B "' + (Join-Path $W 'vfy_fzp_scan.py') + '" "' + $s[1] + '" "' + $out + '" ' + $s[2])
}
Step 'a1_table' ('-B "' + (Join-Path $W 'vfy_a1_table.py') + '" "' + (Join-Path $O 'a1_table.json') + '"')
Step 'trace' ('-B "' + (Join-Path $W 'vfy_trace.py') + '" "' + (Join-Path $O 'trace.json') + '"')
Step 'b0' ('-B "' + (Join-Path $W 'vfy_b0.py') + '" "' + (Join-Path $O 'b0.json') + '"')
Step 'r4' ('-B "' + (Join-Path $W 'vfy_r4.py') + '" "' + (Join-Path $O 'r4.json') + '"')
"DONE $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Out-File -FilePath $state -Append -Encoding utf8
