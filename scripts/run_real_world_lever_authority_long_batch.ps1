<#
Run long real-world Gaepo lever-authority diagnostics.

Default setup:
  - 900 s no-control warm-up
  - 3600 s evaluation window
  - demand scale 1.35
  - large, isolated actuator moves where possible

The underlying single-case watchdog is restartable through DoneRows; rerunning
this batch skips cases whose state CSV already contains the expected rows.
#>
param(
  [string]$OutDir = "evaluation\runs\real_world_modi_lever_authority_warm900_eval3600_20260722",
  [double]$DemandScale = 1.35,
  [int]$WarmupSec = 900,
  [int]$EvalSec = 3600,
  [int]$ControlIntervalSec = 60,
  [int]$StateLogIntervalSec = 60,
  [int]$Seed = 13,
  [int]$StallSec = 600,
  [int]$MaxAttempts = 2,
  [string[]]$Cases = @(
    "no_control",
    "vsl60_all",
    "vsl60_bnmask",
    "ramp_all360",
    "signal_major90",
    "signal_minor90",
    "signal_offset60",
    "combined_extreme",
    "pstack_bnmask"
  )
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runner = Join-Path $repo "scripts\run_real_world_single_watchdog.ps1"
$baseTuning = Join-Path $repo "evaluation\configs\real_world_modi_pstack_adapter_v1_response_calibrated_20260721.json"
$maskTuning = Join-Path $repo "evaluation\configs\real_world_modi_pstack_bottleneck_mask_scale135_20260722.json"
$calibration = Join-Path $repo "evaluation\calibration\real_world_modi_control_v0_20260719.json"
$mapping = Join-Path $repo "evaluation\real_world_modi_control\control_mapping.json"
$simPeriod = $WarmupSec + $EvalSec
$expectedStateRows = 2 + [int][Math]::Floor($simPeriod / $StateLogIntervalSec)

if (-not [System.IO.Path]::IsPathRooted($OutDir)) {
  $OutDir = Join-Path $repo $OutDir
}
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$caseDefs = @(
  [pscustomobject]@{
    Key = "no_control"
    Name = "no_control_scale135_warm900_eval3600_seed13"
    Controller = "no-control"
    Tuning = $baseTuning
    ControlStartSec = -1
  },
  [pscustomobject]@{
    Key = "vsl60_all"
    Name = "vsl60_all_scale135_warm900_eval3600_seed13"
    Controller = "diagnostic-vsl60-only"
    Tuning = $baseTuning
    ControlStartSec = $WarmupSec
  },
  [pscustomobject]@{
    Key = "vsl60_bnmask"
    Name = "vsl60_bnmask_scale135_warm900_eval3600_seed13"
    Controller = "diagnostic-vsl60-only"
    Tuning = $maskTuning
    ControlStartSec = $WarmupSec
  },
  [pscustomobject]@{
    Key = "ramp_all360"
    Name = "ramp_all360_scale135_warm900_eval3600_seed13"
    Controller = "diagnostic-ramp-all360-original"
    Tuning = $baseTuning
    ControlStartSec = $WarmupSec
  },
  [pscustomobject]@{
    Key = "signal_major90"
    Name = "signal_major90_scale135_warm900_eval3600_seed13"
    Controller = "diagnostic-signal-major90-only"
    Tuning = $baseTuning
    ControlStartSec = $WarmupSec
  },
  [pscustomobject]@{
    Key = "signal_minor90"
    Name = "signal_minor90_scale135_warm900_eval3600_seed13"
    Controller = "diagnostic-signal-minor90-only"
    Tuning = $baseTuning
    ControlStartSec = $WarmupSec
  },
  [pscustomobject]@{
    Key = "signal_offset60"
    Name = "signal_offset60_scale135_warm900_eval3600_seed13"
    Controller = "diagnostic-signal-offset60-only"
    Tuning = $baseTuning
    ControlStartSec = $WarmupSec
  },
  [pscustomobject]@{
    Key = "combined_extreme"
    Name = "combined_extreme_scale135_warm900_eval3600_seed13"
    Controller = "diagnostic-combined-extreme"
    Tuning = $baseTuning
    ControlStartSec = $WarmupSec
  },
  [pscustomobject]@{
    Key = "pstack_bnmask"
    Name = "pstack_bnmask_scale135_warm900_eval3600_seed13"
    Controller = "stackelberg"
    Tuning = $maskTuning
    ControlStartSec = $WarmupSec
  }
)

$caseKeys = @(
  foreach ($caseKey in $Cases) {
    foreach ($part in ($caseKey -split ",")) {
      $trimmed = $part.Trim()
      if ($trimmed -ne "") {
        $trimmed
      }
    }
  }
)

$selected = $caseDefs | Where-Object { $caseKeys -contains $_.Key }
if (-not $selected) {
  throw "No matching cases selected. Requested: $($caseKeys -join ',')"
}

Write-Host "OUT_DIR=$OutDir"
Write-Host "SIM_PERIOD_SEC=$simPeriod"
Write-Host "EVAL_WINDOW_SEC=$WarmupSec..$simPeriod"
Write-Host "EXPECTED_STATE_ROWS=$expectedStateRows"
Write-Host "CASES=$($selected.Key -join ',')"

foreach ($case in $selected) {
  Write-Host "CASE_START key=$($case.Key) name=$($case.Name) controller=$($case.Controller)"
  & $runner `
    -Name $case.Name `
    -OutDir $OutDir `
    -SimPeriod $simPeriod `
    -ControlIntervalSec $ControlIntervalSec `
    -Seed $Seed `
    -Controller $case.Controller `
    -Tuning $case.Tuning `
    -Calibration $calibration `
    -Mapping $mapping `
    -ControlStartSec $case.ControlStartSec `
    -WarmupController "no-control" `
    -StateLogIntervalSec $StateLogIntervalSec `
    -DemandScale $DemandScale `
    -StallSec $StallSec `
    -MaxAttempts $MaxAttempts `
    -DoneRows $expectedStateRows
  if ($LASTEXITCODE -ne 0) {
    throw "Case failed: $($case.Key)"
  }
  Write-Host "CASE_DONE key=$($case.Key) name=$($case.Name)"
}

Write-Host "BATCH_DONE"
