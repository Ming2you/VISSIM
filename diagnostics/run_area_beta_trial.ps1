param(
  [Parameter(Mandatory=$true)][ValidateSet(0,60,150,300)][int]$BetaSeconds,
  [int]$Seed = 13,
  [Parameter(Mandatory=$true)][ValidatePattern('^[A-Za-z0-9_-]+$')][string]$Name,
  [string]$Python = 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
)
$ErrorActionPreference = 'Stop'
$areaRepo = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $areaRepo
$areaConfig = "diagnostics/area_candidate_configs/n7_area_beta$BetaSeconds.json"
$areaOutput = Join-Path 'evaluation/runs' $Name
if (Test-Path -LiteralPath $areaOutput) { throw "Run output already exists: $areaOutput" }
$areaManifestPath = Join-Path $PSScriptRoot 'area_candidate_configs/manifest.json'
$areaManifestBytes = [IO.File]::ReadAllBytes($areaManifestPath)
$areaManifest = [Text.Encoding]::UTF8.GetString($areaManifestBytes) | ConvertFrom-Json
function Assert-AreaSources {
  foreach ($entry in $areaManifest.source_sha256.PSObject.Properties) {
    $sourcePath = Join-Path $areaRepo $entry.Name
    if ((Get-FileHash -Algorithm SHA256 -LiteralPath $sourcePath).Hash -ne $entry.Value) {
      throw "Candidate source changed since manifest generation: $($entry.Name)"
    }
  }
  $selected = $areaManifest.outputs.PSObject.Properties[[string]$BetaSeconds].Value
  if ((Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $areaRepo $areaConfig)).Hash -ne $selected.sha256) {
    throw 'Selected candidate config changed since manifest generation'
  }
}
Assert-AreaSources
$env:PYTHONUTF8 = '1'
$env:RW_PYTHON = $Python
$env:RW_OFFSET_WRITER = 'experiment'
$env:RW_QUEUE_COUNTER = '1'
$env:RW_QUEUE_WINDOW = '1'
$env:RW_SIGNAL_READBACK_SEC = '1'
$env:RW_SIGNAL_WRITE_ON_CHANGE = '0'
$env:RW_VEHREC_RESOLUTION = '1'
Remove-Item Env:RW_ADAPTER_MODE -ErrorAction SilentlyContinue
& $Python -X utf8 scripts/verify_parameters.py $areaConfig
if ($LASTEXITCODE -ne 0) { throw 'Parameter verification failed' }
New-Item -ItemType Directory -Path $areaOutput | Out-Null
[IO.File]::WriteAllBytes((Join-Path $areaRepo "$areaOutput/area_candidate_source_manifest.json"), $areaManifestBytes)
& scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1 `
  -Name $Name -Controller wu-link `
  -Network 'network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx' `
  -OutDir $areaOutput -Tuning $areaConfig `
  -Calibration 'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json' `
  -Mapping 'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json' `
  -VbsConfig 'evaluation/real_world_modi_control_ver2n21_20260907/real_world_modi_control_config_ver2n21.vbs' `
  -UrbanInputGateMap 'evaluation/real_world_modi_inventory/urban_input_gate_map_ver2_20260907.csv' `
  -VehicleInputRoles 'evaluation/real_world_modi_inventory/vehicle_input_roles.csv' `
  -DemandProfile 'evaluation/configs/demand_profiles/ver2_fdsweep_x15_20260907.csv' `
  -DemandScale 1 -SimPeriod 5400 -ControlIntervalSec 150 -ControlStartSec 900 `
  -WarmupController no-control -Seed $Seed -StateLogIntervalSec 30 `
  -StartupStallSec 300 -StallSec 2400 -MaxAttempts 1 -NoGlobalKill `
  -AuditAnchorsSec '900,1500,1800,2100,2700,3600,4500,5400'
$areaExitCode = $LASTEXITCODE
Assert-AreaSources
exit $areaExitCode
