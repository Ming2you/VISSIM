<#
Run no-control real-world Gaepo demand profiles to find a clearer,
controller-relevant congestion regime before spending time on full P-Stack runs.

Default setup:
  - 900 s no-control warm-up
  - 1200 s evaluation window
  - role-specific demand profiles for freeway, urban, and mixed stress
#>
param(
  [string]$OutDir = "evaluation\runs\real_world_modi_congestion_ladder_20260724",
  [int]$WarmupSec = 900,
  [int]$EvalSec = 1200,
  [int]$ControlIntervalSec = 60,
  [int]$StateLogIntervalSec = 60,
  [int]$Seed = 13,
  [int]$StallSec = 600,
  [int]$MaxAttempts = 2,
  [string[]]$Cases = @(
    "uniform170",
    "mixed_critical",
    "freeway_breakdown",
    "urban_storage"
  )
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runner = Join-Path $repo "scripts\run_real_world_single_watchdog.ps1"
$baseTuning = Join-Path $repo "evaluation\configs\real_world_modi_pstack_adapter_v1_response_calibrated_20260721.json"
$calibration = Join-Path $repo "evaluation\calibration\real_world_modi_control_v0_20260719.json"
$mapping = Join-Path $repo "evaluation\real_world_modi_control\control_mapping.json"
$profiles = Join-Path $repo "evaluation\configs\demand_profiles"
$simPeriod = $WarmupSec + $EvalSec
$expectedStateRows = 2 + [int][Math]::Floor($simPeriod / $StateLogIntervalSec)

if (-not [System.IO.Path]::IsPathRooted($OutDir)) {
  $OutDir = Join-Path $repo $OutDir
}
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$caseDefs = @(
  [pscustomobject]@{
    Key = "uniform150"
    Name = "no_control_uniform150_warm${WarmupSec}_eval${EvalSec}_seed${Seed}"
    DemandScale = 1.50
    DemandProfile = ""
  },
  [pscustomobject]@{
    Key = "uniform170"
    Name = "no_control_uniform170_warm${WarmupSec}_eval${EvalSec}_seed${Seed}"
    DemandScale = 1.70
    DemandProfile = ""
  },
  [pscustomobject]@{
    Key = "uniform190"
    Name = "no_control_uniform190_warm${WarmupSec}_eval${EvalSec}_seed${Seed}"
    DemandScale = 1.90
    DemandProfile = ""
  },
  [pscustomobject]@{
    Key = "mixed_critical"
    Name = "no_control_mixed_critical_warm${WarmupSec}_eval${EvalSec}_seed${Seed}"
    DemandScale = 1.00
    DemandProfile = Join-Path $profiles "real_world_mixed_critical_20260724.csv"
  },
  [pscustomobject]@{
    Key = "freeway_breakdown"
    Name = "no_control_freeway_breakdown_warm${WarmupSec}_eval${EvalSec}_seed${Seed}"
    DemandScale = 1.00
    DemandProfile = Join-Path $profiles "real_world_freeway_breakdown_20260724.csv"
  },
  [pscustomobject]@{
    Key = "urban_storage"
    Name = "no_control_urban_storage_warm${WarmupSec}_eval${EvalSec}_seed${Seed}"
    DemandScale = 1.00
    DemandProfile = Join-Path $profiles "real_world_urban_storage_20260724.csv"
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
  Write-Host "CASE_START key=$($case.Key) name=$($case.Name) demand_scale=$($case.DemandScale) profile=$($case.DemandProfile)"
  & $runner `
    -Name $case.Name `
    -OutDir $OutDir `
    -SimPeriod $simPeriod `
    -ControlIntervalSec $ControlIntervalSec `
    -Seed $Seed `
    -Controller "no-control" `
    -Tuning $baseTuning `
    -Calibration $calibration `
    -Mapping $mapping `
    -ControlStartSec -1 `
    -WarmupController "no-control" `
    -StateLogIntervalSec $StateLogIntervalSec `
    -DemandScale $case.DemandScale `
    -DemandProfile $case.DemandProfile `
    -StallSec $StallSec `
    -MaxAttempts $MaxAttempts `
    -DoneRows $expectedStateRows
  if ($LASTEXITCODE -ne 0) {
    throw "Case failed: $($case.Key)"
  }
  Write-Host "CASE_DONE key=$($case.Key) name=$($case.Name)"
}

Write-Host "BATCH_DONE"
