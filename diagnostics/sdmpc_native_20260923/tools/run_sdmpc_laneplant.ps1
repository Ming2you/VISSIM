param([string]$Name = 'sdmpc_lp_v1', [int]$SimPeriod = 1500, [int]$Seed = 13)
# Closed-loop SDMPC on the network its lane plant is pinned to.
#
# The pin is checked as snapshot_network_sha256(state) == plant.json sources.network,
# and network_provenance returns the PHYSICAL source sha when a recording proof is
# present -- so -Network is the recording copy (4bad9195) and -NetworkRecordingProof
# is what makes it resolve to the pinned fcb349d3. Passing the recording network
# without the proof fails the guard.
#
# Every other input is the lane_native_nc2850_s13_v3 provenance's, not a default:
# the gate map is ver2, NOT legs4b, and the VBS config is the lane_native scenario.
$ErrorActionPreference = 'Continue'
$dep = "C:\Users\TRLAB\Documents\ChatGPT\VISSIM\.review-deps"
$env:PYTHONPATH = "$dep\sdmpc;$dep\sdmpc-numba"
$env:OMP_NUM_THREADS = '1'; $env:OPENBLAS_NUM_THREADS = '1'; $env:MKL_NUM_THREADS = '1'
$env:PYTHONUTF8 = '1'
Get-ChildItem Env: | Where-Object Name -like 'RW_*' | ForEach-Object { Remove-Item -LiteralPath ('Env:' + $_.Name) }
# Cleared above so a stale RW_ADAPTER_MODE / RW_MAINLINE_SG_ONLY cannot leak in, then
# set back the two this run genuinely requires. The watchdog only RECORDS RW_* -- it
# inherits them from this shell and sets none of them itself.
#   RW_PYTHON        verifying the recording proof shells out to Python.
#   RW_OFFSET_WRITER the config declares offset_writer=experiment, and
#                    offset_promotion.validate_experiment_declaration demands BOTH the
#                    config value and this env var. The VBS only knows intent_only and
#                    test_only, so 'experiment' can only come from here.
$env:RW_PYTHON = (Get-Command python).Source
$env:RW_OFFSET_WRITER = 'experiment'
Set-Location D:\VISSIM-merge\sim3
# The recording proof asserts Path(proof.recorded_network.path) == Path(-Network),
# an absolute-path identity, not a hash comparison -- so the network and its proof
# must be the originals the proof names, even though sim3's copies are byte-identical.
# Code, mapping, calibration and tuning still come from sim3; only this data does not.
# plant.json's own `network` pin still resolves under sim3 and was verified there.
$lp = 'C:\Users\TRLAB\Documents\ChatGPT\VISSIM\.worktrees\sdmpc-lane-plant-20260921\diagnostics\lane_plant_20260921'
Write-Output "LAUNCH $Name sim=$SimPeriod seed=$Seed vissim_now=$(@(Get-Process -Name 'VISSIM*' -ErrorAction SilentlyContinue).Count) $(Get-Date -Format o)"
& powershell -NoProfile -ExecutionPolicy Bypass -File 'scripts\run_real_world_single_watchdog_distributed_core17legs4b.ps1' `
  -Name $Name -OutDir "D:\VISSIM_runs\20260923_sdmpc\$Name" `
  -Network               "$lp\native\native_recording\baseline.inpx" `
  -NetworkRecordingProof "$lp\native\network_recording.json" `
  -VbsConfig             "$lp\scenario\lane_native.vbs" `
  -DemandProfile         "$lp\scenario\profile.csv" `
  -Mapping     'evaluation\real_world_modi_control_ver2n21_20260907\control_mapping_ver2n21.json' `
  -Calibration 'evaluation\calibration\real_world_prediction_calibration_core17legs4b_20260820.json' `
  -Tuning      'diagnostics\sdmpc_pfo_caps_20260922\config_candidate_obs1.json' `
  -UrbanInputGateMap 'evaluation\real_world_modi_inventory\urban_input_gate_map_ver2_20260907.csv' `
  -VehicleInputRoles 'evaluation\real_world_modi_inventory\vehicle_input_roles.csv' `
  -Controller 'wu-link' -WarmupController 'no-control' `
  -SimPeriod $SimPeriod -ControlIntervalSec 150 -ControlStartSec 900 -Seed $Seed `
  -StateLogIntervalSec 30 -StallSec 2400 -StartupStallSec 300 -MaxAttempts 1 -NoGlobalKill
Write-Output "EXIT $Name code=$LASTEXITCODE $(Get-Date -Format o)"
