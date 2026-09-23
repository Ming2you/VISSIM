param([string]$Name = 'sdmpc_verify_v1', [int]$SimPeriod = 1500, [int]$Seed = 23)
$ErrorActionPreference = 'Continue'
$dep = "C:\Users\TRLAB\Documents\ChatGPT\VISSIM\.review-deps"
$env:PYTHONPATH = "$dep\sdmpc;$dep\sdmpc-numba"
$env:OMP_NUM_THREADS = '1'; $env:OPENBLAS_NUM_THREADS = '1'; $env:MKL_NUM_THREADS = '1'
$env:PYTHONUTF8 = '1'
# The launcher clears RW_* before any Python starts; do the same so a stale
# RW_MAINLINE_SG_ONLY / RW_ADAPTER_MODE from an earlier shell cannot leak in.
Get-ChildItem Env: | Where-Object Name -like 'RW_*' | ForEach-Object { Remove-Item -LiteralPath ('Env:' + $_.Name) }
Set-Location D:\VISSIM-merge\sim3
$net = 'D:\VISSIM_runs\20260922_both_off_half\fw080_urban090_nc9000\prepared\network\baseline.inpx'
Write-Output "LAUNCH $Name sim=$SimPeriod seed=$Seed vissim_now=$(@(Get-Process -Name 'VISSIM*' -ErrorAction SilentlyContinue).Count) $(Get-Date -Format o)"
& powershell -NoProfile -ExecutionPolicy Bypass -File 'scripts\run_real_world_single_watchdog_distributed_core17legs4b.ps1' `
  -Name $Name -Network $net -OutDir "D:\VISSIM_runs\20260923_sdmpc\$Name" `
  -Tuning      'diagnostics\sdmpc_pfo_caps_20260922\config_candidate.json' `
  -Calibration 'evaluation\calibration\real_world_prediction_calibration_core17legs4b_20260820.json' `
  -Mapping     'evaluation\real_world_modi_control_ver2n21_20260907\control_mapping_ver2n21.json' `
  -VbsConfig   'evaluation\real_world_modi_control_ver2n21_20260907\real_world_modi_control_config_ver2n21.vbs' `
  -Controller 'wu-link' -WarmupController 'no-control' `
  -SimPeriod $SimPeriod -ControlIntervalSec 150 -ControlStartSec 900 -Seed $Seed `
  -StateLogIntervalSec 5 -StallSec 2400 -StartupStallSec 300 -MaxAttempts 1 -NoGlobalKill
Write-Output "EXIT $Name code=$LASTEXITCODE $(Get-Date -Format o)"
