<#
2026-08-01 새 기준선 A/B 컨트롤러 arm 배치.

무제어 arm 은 별도로 SimPeriod 4500 으로 이미 돌렸고(FD 재적합 점군 겸용),
같은 시드/수요/네트워크의 결정론적 런이므로 분석창 900..2700 을 잘라 쓴다.
이 스크립트는 컨트롤러 arm 만 돌린다.

런 길이 축소 근거(조용히 줄이지 않는다).
  관행은 warm 900 + eval 3600 = SimPeriod 4500 이다. 그런데
  run_real_world_stackelberg_controller.vbs 의 UseEventContinuousMode 가
  "diagnostic-*" 와 "stackelberg" 만 매칭하므로 pstack-flagship 은 STEPWISE 모드로
  떨어진다(매 sim-sec RunSingleStep + ApplyRuntimeSignals/RampMeters).
  실측 처리율이 no-control 연속 모드 대비 한 자릿수 배 느려서 4500 sim-sec 는
  한 arm 당 3 시간을 넘긴다. 임무의 arm 당 2 시간 상한을 지키기 위해
  eval 을 3600 -> 1800 으로 줄였다. 시드·수요·네트워크·제어주기는 그대로다.
#>
param(
  [string]$OutDir = "evaluation\runs\new_baseline_ab_20260801",
  [double]$DemandScale = 1.35,
  [int]$WarmupSec = 900,
  [int]$EvalSec = 1800,
  [int]$ControlIntervalSec = 60,
  [int]$StateLogIntervalSec = 60,
  [int]$Seed = 13,
  [int]$StallSec = 600,
  [int]$MaxAttempts = 2,
  [Parameter(Mandatory=$true)][string]$Tuning,
  [Parameter(Mandatory=$true)][string]$Calibration,
  [string[]]$Arms = @("pstack_flagship", "stackelberg")
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runner = Join-Path $repo "scripts\run_real_world_single_watchdog.ps1"
$mapping = Join-Path $repo "evaluation\real_world_modi_control\control_mapping.json"
$simPeriod = $WarmupSec + $EvalSec
$expectedStateRows = 2 + [int][Math]::Floor($simPeriod / $StateLogIntervalSec)

if (-not [System.IO.Path]::IsPathRooted($OutDir)) { $OutDir = Join-Path $repo $OutDir }
if (-not [System.IO.Path]::IsPathRooted($Tuning)) { $Tuning = Join-Path $repo $Tuning }
if (-not [System.IO.Path]::IsPathRooted($Calibration)) { $Calibration = Join-Path $repo $Calibration }
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$caseDefs = @(
  [pscustomobject]@{
    Key = "pstack_flagship"
    Name = "pstack_flagship_scale135_warm900_eval1800_seed$Seed"
    Controller = "pstack-flagship"
  },
  [pscustomobject]@{
    Key = "stackelberg"
    Name = "stackelberg_scale135_warm900_eval1800_seed$Seed"
    Controller = "stackelberg"
  }
)

$selected = $caseDefs | Where-Object { $Arms -contains $_.Key }
if (-not $selected) { throw "No matching arms: $($Arms -join ',')" }

Write-Host "OUT_DIR=$OutDir"
Write-Host "SIM_PERIOD_SEC=$simPeriod"
Write-Host "ANALYSIS_WINDOW_SEC=$WarmupSec..$simPeriod"
Write-Host "TUNING=$Tuning"
Write-Host "CALIBRATION=$Calibration"
Write-Host "EXPECTED_STATE_ROWS=$expectedStateRows"
Write-Host "ARMS=$($selected.Key -join ',')"

foreach ($case in $selected) {
  Write-Host "CASE_START key=$($case.Key) name=$($case.Name) controller=$($case.Controller)"
  $t0 = Get-Date
  & $runner `
    -Name $case.Name `
    -OutDir $OutDir `
    -SimPeriod $simPeriod `
    -ControlIntervalSec $ControlIntervalSec `
    -Seed $Seed `
    -Controller $case.Controller `
    -Tuning $Tuning `
    -Calibration $Calibration `
    -Mapping $mapping `
    -ControlStartSec $WarmupSec `
    -WarmupController "no-control" `
    -StateLogIntervalSec $StateLogIntervalSec `
    -DemandScale $DemandScale `
    -StallSec $StallSec `
    -MaxAttempts $MaxAttempts `
    -DoneRows $expectedStateRows
  if ($LASTEXITCODE -ne 0) { throw "Arm failed: $($case.Key)" }
  Write-Host "CASE_DONE key=$($case.Key) elapsed_sec=$([int]((Get-Date)-$t0).TotalSeconds)"
}

Write-Host "BATCH_DONE"
