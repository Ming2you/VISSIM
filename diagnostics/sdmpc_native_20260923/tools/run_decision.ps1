param([string]$OutName, [string]$Config = "diagnostics/sdmpc_pfo_caps_20260922/config_candidate.json")
$ErrorActionPreference = "Continue"
$dep = "C:\Users\TRLAB\Documents\ChatGPT\VISSIM\.review-deps"
$env:PYTHONPATH = "$dep\sdmpc;$dep\sdmpc-numba"
$env:OMP_NUM_THREADS = "1"; $env:OPENBLAS_NUM_THREADS = "1"; $env:MKL_NUM_THREADS = "1"
$env:PYTHONUTF8 = "1"
$env:RW_OFFSET_WRITER = "experiment"
Set-Location D:\VISSIM-merge\sim3
$vis = @(Get-Process -Name 'VISSIM*' -ErrorAction SilentlyContinue).Count
Write-Output "START $OutName vissim_concurrent=$vis $(Get-Date -Format o)"
$t0 = Get-Date
python -B diagnostics/measure_sdmpc_pfo_decision.py `
  diagnostics/sdmpc_stream_summary_20260922/hotpath_h3_v1 `
  "diagnostics/sdmpc_pfo_caps_20260922/$OutName" `
  $Config
$code = $LASTEXITCODE
Write-Output "DONE $OutName exit=$code wall_sec=$([math]::Round(((Get-Date)-$t0).TotalSeconds,3)) vissim_end=$(@(Get-Process -Name 'VISSIM*' -ErrorAction SilentlyContinue).Count)"
