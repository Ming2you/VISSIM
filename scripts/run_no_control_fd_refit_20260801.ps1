<#
2026-08-01 플랜트(택시 class 70 VSL 편입) 재적합용 no-control FD/MFD 재추출 배치.

기존 관행(run_real_world_lever_authority_long_batch.ps1 의 no_control 케이스)을 그대로 따른다.
  - 900 s no-control warm-up + 3600 s 평가 = SimPeriod 4500
  - seed 13, ControlIntervalSec 60, StateLogIntervalSec 60
  - 기본 수요 스케일 1.35 (구 20260724 산출물과 동일 조건)
추가로 혼잡 branch 커버리지를 위해 상위 수요 스케일 런을 하나 더 돌린다.
새 플랜트는 자유류가 빨라져 1.35 만으로는 임계밀도 위쪽 표본이 부족할 수 있기 때문이다.
#>
param(
  [string]$OutDir = "evaluation\runs\no_control_fd_refit_20260801",
  [double[]]$DemandScales = @(1.35, 1.70),
  [int]$WarmupSec = 900,
  [int]$EvalSec = 3600,
  [int]$ControlIntervalSec = 60,
  [int]$StateLogIntervalSec = 60,
  [int]$Seed = 13,
  [int]$StallSec = 600,
  [int]$MaxAttempts = 2
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runner = Join-Path $repo "scripts\run_real_world_single_watchdog.ps1"
$calibration = Join-Path $repo "evaluation\calibration\real_world_modi_control_v0_20260719.json"
$tuning = Join-Path $repo "evaluation\configs\real_world_modi_pstack_adapter_v1_response_calibrated_20260721.json"
$mapping = Join-Path $repo "evaluation\real_world_modi_control\control_mapping.json"
$simPeriod = $WarmupSec + $EvalSec
$expectedStateRows = 2 + [int][Math]::Floor($simPeriod / $StateLogIntervalSec)

if (-not [System.IO.Path]::IsPathRooted($OutDir)) { $OutDir = Join-Path $repo $OutDir }
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

Write-Host "OUT_DIR=$OutDir"
Write-Host "SIM_PERIOD_SEC=$simPeriod"
Write-Host "FD_WINDOW_SEC=$WarmupSec..$simPeriod"
Write-Host "EXPECTED_STATE_ROWS=$expectedStateRows"

foreach ($scale in $DemandScales) {
  $tag = ("{0:0}" -f ($scale * 100))
  $name = "no_control_scale${tag}_warm900_eval3600_seed$Seed"
  Write-Host "CASE_START name=$name scale=$scale"
  & $runner `
    -Name $name `
    -OutDir $OutDir `
    -SimPeriod $simPeriod `
    -ControlIntervalSec $ControlIntervalSec `
    -Seed $Seed `
    -Controller "no-control" `
    -Tuning $tuning `
    -Calibration $calibration `
    -Mapping $mapping `
    -ControlStartSec -1 `
    -WarmupController "no-control" `
    -StateLogIntervalSec $StateLogIntervalSec `
    -DemandScale $scale `
    -StallSec $StallSec `
    -MaxAttempts $MaxAttempts `
    -DoneRows $expectedStateRows
  if ($LASTEXITCODE -ne 0) { throw "Case failed: $name" }
  Write-Host "CASE_DONE name=$name"
}

Write-Host "BATCH_DONE"
