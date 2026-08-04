<#
2026-08-01 새 기준선 A/B 컨트롤러 arm 배치.

무제어 arm 은 별도로 SimPeriod 4500 으로 이미 돌렸고(FD 재적합 점군 겸용),
같은 시드/수요/네트워크의 결정론적 런이므로 그 산출물을 그대로 기준선으로 쓴다.
이 스크립트는 컨트롤러 arm 만 돌린다.
  기준선 경로: evaluation\runs\no_control_fd_refit_20260801\
  기준선 이름: no_control_scale{135|170}_warm900_eval3600_seed13

실행 모드 (2026-08-02 실측으로 확정).
  UseEventContinuousMode 는 "diagnostic-*" 와 "stackelberg" 만 매칭하므로
  pstack-flagship 은 STEPWISE 로 떨어진다. 이벤트 모드를 붙여 600 s 대조한 결과
  sim_sec 180 부터 궤적이 갈렸다(제어 인가/상태 표본이 1 초 밀린다). 그래서
  이벤트 모드 편입은 되돌렸고 모든 arm 을 STEPWISE 한 규약으로 통일한다.
  stackelberg 는 기본이 이벤트 모드라 -ForceStepwise 로 눌러 맞춘다.
  무제어 arm 의 CONTINUOUS_STATIC 은 STEPWISE 와 비트 동일이 확인돼(상태 CSV·
  세그먼트 CSV sha256 일치) 그대로 비교 가능하다. 근거 산출물은
  evaluation\runs\mode_probe_20260802\.

런 길이는 FD 재추출과 동일한 warm 900 + eval 3600 = SimPeriod 4500 이다.
600 s 실측 180 s(3.3 배속)이므로 arm 당 20 분대다 - 줄일 이유가 없다.
#>
param(
  [string]$OutDir = "evaluation\runs\new_baseline_ab_20260801",
  [double]$DemandScale = 1.35,
  [int]$WarmupSec = 900,
  [int]$EvalSec = 3600,
  [int]$ControlIntervalSec = 60,
  [int]$StateLogIntervalSec = 60,
  [int]$Seed = 13,
  [int]$StallSec = 900,
  [int]$MaxAttempts = 2,
  # 2026-08-02 FD 재적합 이후의 현행 체인 기본값.
  # leaf tuning 이 부모(adapter_v1)의 stale calibration_override(120/30/6900)를
  # 재적합값(119.505/16.354/4914)으로 덮는다. 캘리브레이션 파일만 갈면 도달하지 못한다.
  [string]$Tuning = "evaluation\configs\real_world_modi_pstack_flagship_segvsl_fdrefit_20260802.json",
  [string]$Calibration = "evaluation\calibration\real_world_modi_control_v2_fdrefit_20260802.json",
  [string[]]$Arms = @("pstack_flagship", "stackelberg")
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runner = Join-Path $repo "scripts\run_real_world_single_watchdog.ps1"
$mapping = Join-Path $repo "evaluation\real_world_modi_control\control_mapping.json"
$simPeriod = $WarmupSec + $EvalSec
$expectedStateRows = 2 + [int][Math]::Floor($simPeriod / $StateLogIntervalSec)
$scaleTag = ("{0:0}" -f ($DemandScale * 100))

if (-not [System.IO.Path]::IsPathRooted($OutDir)) { $OutDir = Join-Path $repo $OutDir }
if (-not [System.IO.Path]::IsPathRooted($Tuning)) { $Tuning = Join-Path $repo $Tuning }
if (-not [System.IO.Path]::IsPathRooted($Calibration)) { $Calibration = Join-Path $repo $Calibration }
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$caseDefs = @(
  [pscustomobject]@{
    Key = "pstack_flagship"
    Name = "pstack_flagship_scale${scaleTag}_warm${WarmupSec}_eval${EvalSec}_seed$Seed"
    Controller = "pstack-flagship"
  },
  [pscustomobject]@{
    Key = "stackelberg"
    Name = "stackelberg_scale${scaleTag}_warm${WarmupSec}_eval${EvalSec}_seed$Seed"
    Controller = "stackelberg"
  }
)

$selected = $caseDefs | Where-Object { $Arms -contains $_.Key }
if (-not $selected) { throw "No matching arms: $($Arms -join ',')" }

Write-Host "OUT_DIR=$OutDir"
Write-Host "SIM_PERIOD_SEC=$simPeriod"
Write-Host "ANALYSIS_WINDOW_SEC=$WarmupSec..$simPeriod"
Write-Host "DEMAND_SCALE=$DemandScale"
Write-Host "TUNING=$Tuning"
Write-Host "CALIBRATION=$Calibration"
Write-Host "EXPECTED_STATE_ROWS=$expectedStateRows"
Write-Host "RUN_MODE=STEPWISE (all arms, forced)"
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
    -ForceStepwise `
    -StallSec $StallSec `
    -MaxAttempts $MaxAttempts `
    -DoneRows $expectedStateRows
  if ($LASTEXITCODE -ne 0) { throw "Arm failed: $($case.Key)" }
  Write-Host "CASE_DONE key=$($case.Key) elapsed_sec=$([int]((Get-Date)-$t0).TotalSeconds)"
}

Write-Host "BATCH_DONE"
