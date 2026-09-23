param(
  [Parameter(Mandatory = $true)][string]$Dec,
  [Parameter(Mandatory = $true)][int]$Sec,
  [Parameter(Mandatory = $true)][int]$PrevSec,
  [Parameter(Mandatory = $true)][string]$Out,
  # Code tree to run. Default is the tree the native runs use; pass a worktree to
  # replay a code change without touching the tree a live run re-reads.
  [string]$Root = 'D:\VISSIM-merge\sim3',
  # Optional tuning config, relative to $Root.
  [string]$Tuning = 'diagnostics\sdmpc_pfo_caps_20260922\config_candidate_obs1.json',
  # State JSON prepared by make_replay_state.py (isolated frame folder). Default: the run's own.
  [string]$StateJson = '',
  # Prepended to PYTHONPATH (e.g. a folder holding a tracing sitecustomize.py).
  [string]$ExtraPythonPath = ''
)
# Re-run one native SDMPC decision offline from a run's saved state, generalising
# replay_900.ps1 to any decision time. Same adapter arguments as the VBS
# (scripts/run_real_world_stackelberg_controller.vbs:1113-1125) and the RW_* env the
# watchdog recorded in run_provenance_sdmpc_lp_9000.json. No VISSIM.
#
# The previous action is read from the run's own decisions folder, so its
# .applied / .sdmpc_pending markers -- the applied-price receipt a consecutive
# SDMPC decision inherits -- are the ones the native run wrote.
$ErrorActionPreference = 'Continue'
$dep = 'C:\Users\TRLAB\Documents\ChatGPT\VISSIM\.review-deps'
$env:PYTHONPATH = "$dep\sdmpc;$dep\sdmpc-numba"
if ($ExtraPythonPath) { $env:PYTHONPATH = "$ExtraPythonPath;$env:PYTHONPATH" }
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
Set-Location $Root
New-Item -ItemType Directory -Force $Out | Out-Null
$s = '{0:D6}' -f $Sec
$p = '{0:D6}' -f $PrevSec
$t0 = Get-Date
& $env:RW_PYTHON 'evaluation\controllers\vissim_stackelberg_adapter.py' `
  --state-json $(if ($StateJson) { $StateJson } else { "$Dec\state_$s.json" }) `
  --previous-action-json "$Dec\action_$p.json" `
  --out-action-json "$Out\action_$s.json" `
  --out-action-csv "$Out\action_$s.csv" `
  --mapping-json 'evaluation\real_world_modi_control_ver2n21_20260907\control_mapping_ver2n21.json' `
  --controller 'wu-link' `
  --detector-mapping-json 'evaluation\real_world_modi_control_ver2_20260907\detector_local_mapping_ver2_20260907.json' `
  --calibration-json 'evaluation\calibration\real_world_prediction_calibration_core17legs4b_20260820.json' `
  --tuning-json $Tuning
Write-Output "REPLAY_$s exit=$LASTEXITCODE wall_sec=$([math]::Round(((Get-Date)-$t0).TotalSeconds,1))"
