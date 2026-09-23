param([string]$Out = 'D:\VISSIM_runs\20260923_sdmpc\sdmpc_lp_v2\offline_900')
# Re-run the native run's 900 s SDMPC decision offline, with the exact arguments the
# VBS built (scripts/run_real_world_stackelberg_controller.vbs:1113-1125) and the exact
# RW_* environment the watchdog recorded in run_provenance_sdmpc_lp_v2.json. No VISSIM:
# the adapter reads the saved state_000900.json and previous action_000750.json.
#
# Purpose: exercise every output writer on the SDMPC path -- the joint decision report,
# the action JSON, the action CSV and .joint_written.json -- in one ~10 minute pass,
# instead of a 60+ minute native run that fails at the first writer it reaches.
$ErrorActionPreference = 'Continue'
$dep = 'C:\Users\TRLAB\Documents\ChatGPT\VISSIM\.review-deps'
$env:PYTHONPATH = "$dep\sdmpc;$dep\sdmpc-numba"
$env:OMP_NUM_THREADS = '1'; $env:OPENBLAS_NUM_THREADS = '1'; $env:MKL_NUM_THREADS = '1'
$env:PYTHONUTF8 = '1'
Get-ChildItem Env: | Where-Object Name -like 'RW_*' | ForEach-Object { Remove-Item -LiteralPath ('Env:' + $_.Name) }
$env:RW_DECISION_FAIL_FAST = '1'
$env:RW_LANE_PLANT_OBSERVATION = '1'
$env:RW_MAINLINE_SG_ONLY = '1'
$env:RW_OFFSET_WRITER = 'experiment'
$env:RW_PYTHON = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
$env:RW_QUEUE_COUNTER = '1'
$env:RW_QUEUE_WINDOW = '1'
$env:RW_RAMP_AMBER_SEC = '0'
$env:RW_SIGNAL_OBSERVATION = '1'
$env:RW_SIGNAL_OBSERVATION_CONFIG_SHA256 = '1c1dc201df2ef9183751fdb10607aeb06443e668e77ae391026bfd00f69a903e'
$env:RW_VEHICLE_OBSERVATION_INTERVAL_SEC = '1'
Set-Location 'D:\VISSIM-merge\sim3'
New-Item -ItemType Directory -Force $Out | Out-Null
$dec = 'D:\VISSIM_runs\20260923_sdmpc\sdmpc_lp_v2\decisions_sdmpc_lp_v2'
$t0 = Get-Date
& $env:RW_PYTHON 'evaluation\controllers\vissim_stackelberg_adapter.py' `
  --state-json "$dec\state_000900.json" `
  --previous-action-json "$dec\action_000750.json" `
  --out-action-json "$Out\action_000900.json" `
  --out-action-csv "$Out\action_000900.csv" `
  --mapping-json 'evaluation\real_world_modi_control_ver2n21_20260907\control_mapping_ver2n21.json' `
  --controller 'wu-link' `
  --detector-mapping-json 'evaluation\real_world_modi_control_ver2_20260907\detector_local_mapping_ver2_20260907.json' `
  --calibration-json 'evaluation\calibration\real_world_prediction_calibration_core17legs4b_20260820.json' `
  --tuning-json 'diagnostics\sdmpc_pfo_caps_20260922\config_candidate_obs1.json'
Write-Output "OFFLINE_900 exit=$LASTEXITCODE wall_sec=$([math]::Round(((Get-Date)-$t0).TotalSeconds,1))"
