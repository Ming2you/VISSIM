param([string]$Tag)
$ErrorActionPreference = "Continue"
$dep = "C:\Users\TRLAB\Documents\ChatGPT\VISSIM\.review-deps"
$env:PYTHONPATH = "$dep\sdmpc;$dep\sdmpc-numba"
$env:OMP_NUM_THREADS = "1"; $env:OPENBLAS_NUM_THREADS = "1"; $env:MKL_NUM_THREADS = "1"
$env:PYTHONUTF8 = "1"; $env:RW_OFFSET_WRITER = "experiment"
Set-Location D:\VISSIM-merge\sim3
$t0 = Get-Date
python -B -m unittest `
  diagnostics.test_sdmpc_pfo_caps diagnostics.test_sdmpc_central diagnostics.test_sdmpc_tangent `
  diagnostics.test_sdmpc_reverse diagnostics.test_sdmpc_sequence diagnostics.test_sdmpc_surrogate_reuse `
  diagnostics.test_sdmpc_initial_shared diagnostics.test_sdmpc_hotpath `
  diagnostics.test_shared_joint_price_quantity diagnostics.test_validated_decision_hold 2>&1
Write-Output "TESTS_$Tag exit=$LASTEXITCODE wall_sec=$([math]::Round(((Get-Date)-$t0).TotalSeconds,2))"
