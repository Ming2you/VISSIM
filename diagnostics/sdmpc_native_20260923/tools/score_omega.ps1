param([Parameter(Mandatory=$true)][string]$Arm)
# Canonical Omega accounting for one seed-sweep arm: one FZP pass through
# diagnostics/summarize_fast_nc.py, which integrates per-link vehicle counts and
# keeps the 635 links the membership document marks inside Omega.
$ErrorActionPreference = 'Continue'
$dep = "C:\Users\TRLAB\Documents\ChatGPT\VISSIM\.review-deps"
$env:PYTHONPATH = "$dep\sdmpc;$dep\sdmpc-numba"
$env:PYTHONUTF8 = '1'; $env:RW_OFFSET_WRITER = 'experiment'
$env:OMP_NUM_THREADS = '1'; $env:OPENBLAS_NUM_THREADS = '1'; $env:MKL_NUM_THREADS = '1'
Set-Location D:\VISSIM-merge\sim3
$t0 = Get-Date
# --run is the run subdirectory: completion_inputs() wants run.json, stdout.txt and
# the *.err files beside each other, not the arm directory that also holds prepared/.
# --geometry-vbs supplies the fixed chain declarations directly; the REFERENCE run the
# script would otherwise read them from lives under the gitignored evaluation/runs/.
python -B diagnostics/summarize_fast_nc.py `
  --run "D:/VISSIM_runs/20260922_seedvar/$Arm/run" `
  --out "D:/VISSIM-merge/sim3/diagnostics/omega_seedvar_20260923/$Arm" `
  --geometry-vbs "D:/VISSIM-merge/sim3/evaluation/real_world_modi_control_ver2n21_20260907/real_world_modi_control_config_ver2n21.vbs"
Write-Output "SCORED $Arm exit=$LASTEXITCODE wall_sec=$([math]::Round(((Get-Date)-$t0).TotalSeconds,1))"
