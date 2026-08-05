# METANET 동역학(tau/nu/kappa/delta_merge) 식별용 강제응답 그리드 실행기.
#
# 설계 근거는 outputs\forced_response_grid_20260802.md 에 적었다. 요약하면
#   - 레버 arm 은 전부 fixed57 계열(diagnostic-fixed57 / vsl100 / vsl80 /
#     ramp-all735-original / ramp-all360-original)로 통일한다. 같은 계열이라
#     도시부 신호(57/57)와 미적용 레버가 arm 간 동일하고, diagnostic-fixed57 이
#     계열 내 기준(VSL 120 = 비구속, 램프 = 용량 1800)이 된다.
#   - ControlStartSec=900 이므로 diagnostic arm 은 t=900 에서 단 한 번 결정한다
#     (VBS UseSingleDecisionEventMode). 즉 런마다 t=900 에 깨끗한 계단 입력이
#     하나 들어가고 그 뒤 램프 미터링/신호는 매 사이클 계속 인가된다.
#   - 수요는 파생 .inpx 2종으로 준다. [2026-08-02 정정] 예전 주석은 런너의
#     -DemandScale/-DemandProfile 이 Volume(1)(=0~900 s)만 써서 분석창 수요를
#     못 바꾼다고 적었는데, 그 버그는 고쳐졌고 지금은 전 시간구간에 적용된다.
#     파생망을 계속 쓰는 이유는 배수가 아니라 평탄화다. 런너는 .inpx 의 시간
#     프로파일 모양을 유지하므로 분석창 동안 수요가 계속 변하고, tau/nu 식별에는
#     900 s 이후 peak 평탄화가 필요하다.
#   - StateLogIntervalSec=10. tau 가 O(10~30 s)라 60 s 표본으로는 완화 과도가
#     1~2 점밖에 안 잡힌다.
param(
  [string]$OutDir = "evaluation\runs\forced_response_grid_20260802",
  [int]$WarmupSec = 900,
  [int]$EvalSec = 3600,
  [int]$ControlIntervalSec = 60,
  [int]$StateLogIntervalSec = 10,
  [int[]]$Seeds = @(13, 29),
  [string[]]$Demands = @("fw100", "fw125"),
  [string[]]$Arms = @("nc", "fixed57", "vsl100", "vsl80", "rm735", "rm360", "incf57"),
  # 사고(차선폐쇄) arm 은 자유류 수요(fw100)에서만 돌린다. 자유류에서 시작해야
  # 폐쇄 onset/해제 offset 이 깨끗한 충격파 한 쌍으로 잡힌다.
  [string]$IncidentDemand = "fw100",
  [int]$IncidentLink = 24,
  [int]$IncidentLane = 1,
  [double]$IncidentPosM = 500.0,
  [int]$IncidentStartSec = 1800,
  [int]$IncidentEndSec = 2700,
  [int]$StallSec = 900,
  [int]$MaxAttempts = 2
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$runner = Join-Path $repo "scripts\run_real_world_single_watchdog.ps1"
$netDir = Join-Path $repo "network\real_world_gaepo_modi"
$tuning = Join-Path $repo "evaluation\configs\real_world_modi_pstack_flagship_segvsl_fdrefit_20260802.json"
$calib = Join-Path $repo "evaluation\calibration\real_world_modi_control_v2_fdrefit_20260802.json"
$simPeriod = $WarmupSec + $EvalSec
$expectedStateRows = 2 + [int][Math]::Floor($simPeriod / $StateLogIntervalSec)

if (-not [System.IO.Path]::IsPathRooted($OutDir)) { $OutDir = Join-Path $repo $OutDir }
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$netByDemand = @{
  "fw100" = "modi_eval_rw_fr_fw100_20260802.inpx"
  "fw125" = "modi_eval_rw_fr_fw125_20260802.inpx"
}

# Arm -> 어댑터 컨트롤러 이름. nc 만 계열 밖(외부 기준 + #8 기준선 연결고리).
$armController = @{
  "nc"      = "no-control"
  "fixed57" = "diagnostic-fixed57"
  "vsl100"  = "diagnostic-vsl100"
  "vsl80"   = "diagnostic-vsl80"
  "rm735"   = "diagnostic-ramp-all735-original"
  "rm360"   = "diagnostic-ramp-all360-original"
  "incf57"  = "diagnostic-fixed57"
}

Write-Host "OUT_DIR=$OutDir"
Write-Host "SIM_PERIOD_SEC=$simPeriod  STATE_LOG_SEC=$StateLogIntervalSec  EXPECTED_STATE_ROWS=$expectedStateRows"
Write-Host "DEMANDS=$($Demands -join ',')  ARMS=$($Arms -join ',')  SEEDS=$($Seeds -join ',')"
Write-Host ("TOTAL_RUNS=" + ($Demands.Count * $Arms.Count * $Seeds.Count))

$batchT0 = Get-Date
foreach ($dem in $Demands) {
  if (-not $netByDemand.ContainsKey($dem)) { throw "Unknown demand: $dem" }
  $net = Join-Path $netDir $netByDemand[$dem]
  if (-not (Test-Path $net)) { throw "Missing network: $net" }
  foreach ($seed in $Seeds) {
    foreach ($arm in $Arms) {
      if (-not $armController.ContainsKey($arm)) { throw "Unknown arm: $arm" }
      $controller = $armController[$arm]
      $name = "${dem}_${arm}_seed${seed}"
      $isIncident = ($arm -eq "incf57")
      if ($isIncident -and $dem -ne $IncidentDemand) {
        Write-Host "CASE_SKIP name=$name reason=incident_arm_only_on_$IncidentDemand"
        continue
      }
      $incArgs = @{}
      if ($isIncident) {
        $incArgs = @{
          IncidentLink     = $IncidentLink
          IncidentLane     = $IncidentLane
          IncidentPos      = $IncidentPosM
          IncidentStartSec = $IncidentStartSec
          IncidentEndSec   = $IncidentEndSec
          IncidentName     = "FR_LANECLOSE"
        }
      }
      Write-Host "CASE_START name=$name controller=$controller net=$($netByDemand[$dem]) incident=$isIncident"
      $t0 = Get-Date
      & $runner `
        -Name $name `
        -Network $net `
        -OutDir $OutDir `
        -SimPeriod $simPeriod `
        -ControlIntervalSec $ControlIntervalSec `
        -StateLogIntervalSec $StateLogIntervalSec `
        -Seed $seed `
        -Controller $controller `
        -WarmupController "no-control" `
        -ControlStartSec $WarmupSec `
        -Tuning $tuning `
        -Calibration $calib `
        -DemandScale 1.00 `
        -StallSec $StallSec `
        -MaxAttempts $MaxAttempts `
        -DoneRows $expectedStateRows `
        @incArgs
      if ($LASTEXITCODE -ne 0) { Write-Host "CASE_FAIL name=$name" }
      Write-Host "CASE_DONE name=$name elapsed_sec=$([int]((Get-Date)-$t0).TotalSeconds)"
    }
  }
}
Write-Host "GRID_DONE elapsed_sec=$([int]((Get-Date)-$batchT0).TotalSeconds)"
