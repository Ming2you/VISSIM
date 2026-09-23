param([string]$Name = 'sdmpc_verify_v1', [int]$SimPeriod = 1500, [int]$Seed = 23)
$ErrorActionPreference = 'Continue'
$dep = "C:\Users\TRLAB\Documents\ChatGPT\VISSIM\.review-deps"
$env:PYTHONPATH = "$dep\sdmpc;$dep\sdmpc-numba"
$env:OMP_NUM_THREADS = '1'; $env:OPENBLAS_NUM_THREADS = '1'; $env:MKL_NUM_THREADS = '1'
$env:PYTHONUTF8 = '1'
Set-Location D:\VISSIM-merge\sim3
$py = (Get-Command python).Source
Write-Output "LAUNCH $Name sim=$SimPeriod seed=$Seed python=$py vissim_now=$(@(Get-Process -Name 'VISSIM*' -ErrorAction SilentlyContinue).Count) $(Get-Date -Format o)"
& powershell -NoProfile -ExecutionPolicy Bypass -File 'diagnostics\run_selected_control_trial.ps1' `
  -SelectedPrepared 'D:\VISSIM_runs\20260922_both_off_half\fw080_urban090_nc9000\prepared' `
  -Tuning 'diagnostics\sdmpc_pfo_caps_20260922\config_candidate.json' `
  -Name $Name -Controller 'wu-link' -SimPeriod $SimPeriod -ControlStartSec 900 -Seed $Seed -Python $py
Write-Output "EXIT $Name code=$LASTEXITCODE $(Get-Date -Format o)"
