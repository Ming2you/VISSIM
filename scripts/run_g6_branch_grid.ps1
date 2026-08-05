# 계약 §11 G6 순위 정합 측정용 VISSIM 분기 리플레이 배치.
#
# 상태 복원 방식 — VISSIM 에는 스냅샷 저장/복원 API 를 쓰지 않는다. 대신
# **공통 접두 리플레이(common-prefix seed replay)** 를 쓴다.
#
#   같은 .inpx + 같은 시드 + t < ControlStartSec 구간을 전부 WarmupController(no-control)
#   로 돌리면, 모든 arm 의 t0 상태가 바이트 단위로 같아진다. t0 에서만 후보 액션이 갈린다.
#
# 이 성질은 이미 실측으로 확인했다. evaluation/runs/forced_response_grid_20260802 의
# decisions_*/state_000900.json 은 6개 arm 전부 SHA-256 이 동일하고, 10 s state CSV 는
# sim_sec=910 에서 처음 갈라진다(수요 fw100/fw125 × 시드 13/29 네 셀 모두).
# 하네스(run_g6_shadow.py)도 셀마다 이 해시 동일성을 다시 검증하고 어긋나면 셀을 버린다.
#
# 기존 forced_response_grid 와 다른 점 하나 — **-ForceStepwise 를 켠다.**
# 이벤트 연속 모드는 diagnostic arm 에서 t0 에 단 한 번만 결정하므로
# state_XXXXXX.json 이 t0 에만 남는다. G6 는 t0+T_c ... t0+H·T_c 의 관측 궤적이
# 필요하므로 매 control interval 마다 결정이 일어나야 한다. stepwise 모드는
# `stepNo Mod controlInterval = 0` 마다 RunControllerDecision 을 호출하고
# 그 안에서 WriteStateJson 이 돈다(run_real_world_stackelberg_controller.vbs:354, 657).
# diagnostic 컨트롤러는 상태와 무관한 상수 액션이므로 매 구간 재결정해도 액션은
# 동일하다 = 계약이 요구한 "fixed action" open-loop 비교가 그대로 성립한다.

param(
  [string]$OutDir = "evaluation\runs\g6_branch_grid_20260802",
  [int]$WarmupSec = 900,
  [int]$HorizonSteps = 5,
  [int]$ControlIntervalSec = 60,
  [int]$StateLogIntervalSec = 10,
  [int[]]$Seeds = @(13, 29),
  [string[]]$Demands = @("fw100", "fw125"),
  # candidate_id -> 어댑터 controller variant. harness/g6/g6_core.py CANDIDATE_SET_V1 과
  # 1:1 로 맞춰야 한다(하네스가 디렉터리 이름의 candidate_id 로 후보를 되찾는다).
  # V2 후보집합 (2026-08-03 재설계). 근거는 harness/g6/g6_core.py CANDIDATE_SET_V2 주석 참조.
  #   - VSL 을 [100,90,80,70,60,50] 6 단계로. 기존 110/120 은 실측 속도 분포상 구속하지 않아
  #     c01_vsl110 과 c02_vsl100 의 관측 목적함수가 정확히 같았다.
  #   - 신호 중복 제거. c22_major62 / c23_minor62 도 관측이 같아서 뺐다.
  [string[]]$Candidates = @(
    "c00_anchor",
    "c01_vsl100", "c02_vsl90", "c03_vsl80", "c04_vsl70", "c05_vsl60", "c06_vsl50",
    "c10_rampd1364", "c11_rampd1253", "c12_rampd691",
    "c13_rampall500", "c14_rampall400", "c15_rampall300",
    "c20_major75", "c21_minor75",
    "c30_offset30", "c40_combined_strong", "c41_combined_extreme"
  ),
  [int]$StallSec = 900,
  [int]$MaxAttempts = 2,
  # 혼잡 초기상태 셀용. 비어 있지 않으면 $Demands 의 네트워크 표를 무시하고
  # 이 네트워크 + 수요 프로파일 조합을 쓴다(셀 이름은 $Demands 원소를 태그로 쓴다).
  # 자유류 t0 에서는 램프 축 목적함수 폭이 0.014% 로 사실상 평평해 순위가 노이즈 지배다.
  [string]$NetworkOverride = "",
  [string]$DemandProfile = "",
  # 2026-08-04 추가. 이전에는 튜닝/캘리브레이션/매핑이 아래에 하드코딩돼 있어
  # 새 캘리브레이션으로 측정할 방법이 없었다. 실제로 수리 후 재캘리브레이션(v3_postrepair)을
  # 만들어 두고도 그리드는 구 v2_fdrefit 으로 액션을 생성하고 있었다.
  #
  # Mapping 이 특히 중요하다. 기본 control_mapping.json 은 신호제어기가 **1 개**뿐이고
  # (SC 1, freeway_interface_signal_controller) 나머지 36 개 도시부 신호가 들어 있지 않다.
  # 그래서 green/offset 후보가 교차로 하나만 건드렸고 관측 응답이 전 지평에서 0 이었다.
  # 도시부 축을 재려면 distributed 매핑(15core/19sc)을 넘겨야 한다.
  [string]$TuningOverride = "",
  [string]$CalibrationOverride = "",
  [string]$MappingOverride = "",
  # 2026-08-04 추가. MappingOverride 만 넘기고 이걸 빼면 **플랜트 관측이 base 로 남는다.**
  # 러너가 evaluation\generated\real_world_modi_control_config.vbs 를 하드코딩하고 있었고,
  # 그 파일이 RW_LOCAL_OBSERVABLE_LINKS(22개)와 RW_DETECTOR_MAPPING_PATH(base)를 정한다.
  # 즉 state_*.json 의 local_observation 이 22 링크만 담긴 채 기록되고, 채점은 분산
  # 175 링크 매핑으로 투영하므로 153 링크에 데이터가 없다. 실측 결과 관측 목적함수가
  # 도시부 차량의 1.4 %만 잡았고(플랜트 69,495 대 투영 987), green/ramp 축 부호가 뒤집혔다.
  # Mapping 을 분산으로 줄 때는 이것도 반드시 짝으로 분산 config 를 줘야 한다.
  [string]$VbsConfigOverride = ""
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$runner = Join-Path $repo "scripts\run_real_world_single_watchdog.ps1"
$netDir = Join-Path $repo "network\real_world_gaepo_modi"
$tuning = if ($TuningOverride -ne "") { $TuningOverride } else {
  Join-Path $repo "evaluation\configs\real_world_modi_pstack_flagship_segvsl_fdrefit_20260802.json" }
$calib = if ($CalibrationOverride -ne "") { $CalibrationOverride } else {
  Join-Path $repo "evaluation\calibration\real_world_modi_control_v2_fdrefit_20260802.json" }
foreach ($f in @($tuning, $calib)) {
  if (-not (Test-Path $f)) { throw "not found: $f" }
}
Write-Host "TUNING=$tuning"
Write-Host "CALIBRATION=$calib"
if ($MappingOverride -ne "") {
  if (-not (Test-Path $MappingOverride)) { throw "not found: $MappingOverride" }
  Write-Host "MAPPING=$MappingOverride"
}

$simPeriod = $WarmupSec + $ControlIntervalSec * $HorizonSteps
$expectedStateRows = 2 + [int][Math]::Floor($simPeriod / $StateLogIntervalSec)

if (-not [System.IO.Path]::IsPathRooted($OutDir)) { $OutDir = Join-Path $repo $OutDir }
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$netByDemand = @{
  "fw100" = "modi_eval_rw_fr_fw100_20260802.inpx"
  "fw125" = "modi_eval_rw_fr_fw125_20260802.inpx"
}

# candidate_id -> --controller. 이름에 -original / -only 가 붙은 변형은 어댑터가
# suppress_signal_rows=1 을 찍어 VISSIM 신호를 원래 프로그램에 맡기는데, 모델 쪽
# ControlAction 은 green 57/57 을 그대로 들고 있다. 모델과 플랜트의 액션이 어긋나므로
# G6 후보로 쓰면 안 된다 - 아래 표에서 제외했다.
# 이 표는 harness/g6/g6_core.py 의 Candidate.variant 와 1:1 로 유지해야 한다.
# V1/V2 양쪽 id 를 모두 담아 두어 -Candidates 로 어느 쪽을 골라도 돌아가게 한다.
$controllerByCandidate = @{
  "c00_anchor"           = "diagnostic-fixed57"
  # --- V2 VSL 6 단계 (2026-08-03)
  "c01_vsl100"           = "diagnostic-vsl100"
  "c02_vsl90"            = "diagnostic-vsl90"
  "c04_vsl70"            = "diagnostic-vsl70"
  "c05_vsl60"            = "diagnostic-vsl60"
  "c06_vsl50"            = "diagnostic-vsl50"
  # --- V1 잔존 id (G6_CANDIDATE_SET=v1 로 되돌릴 때 쓴다)
  "c01_vsl110"           = "diagnostic-vsl110"
  "c02_vsl100"           = "diagnostic-vsl100"
  "c22_major62"          = "diagnostic-signal-major62"
  "c23_minor62"          = "diagnostic-signal-minor62"
  # --- 공통
  "c03_vsl80"            = "diagnostic-vsl80"
  "c10_rampd1364"        = "diagnostic-ramp-d1364"
  "c11_rampd1253"        = "diagnostic-ramp-d1253"
  "c12_rampd691"         = "diagnostic-ramp-hold"
  # 네 그룹 전부 구동 + 구속 수준 미터율 (2026-08-04)
  "c13_rampall500"       = "diagnostic-ramp-all500"
  "c14_rampall400"       = "diagnostic-ramp-all400"
  "c15_rampall300"       = "diagnostic-ramp-all300"
  "c20_major75"          = "diagnostic-signal-major"
  "c21_minor75"          = "diagnostic-signal-minor"
  "c30_offset30"         = "diagnostic-signal-offset30"
  "c40_combined_strong"  = "diagnostic-combined-strong"
  "c41_combined_extreme" = "diagnostic-combined-extreme"
}

Write-Host "OUT_DIR=$OutDir"
Write-Host "SIM_PERIOD_SEC=$simPeriod  WARMUP_SEC=$WarmupSec  HORIZON_STEPS=$HorizonSteps"
Write-Host ("TOTAL_RUNS=" + ($Demands.Count * $Seeds.Count * $Candidates.Count))

$batchT0 = Get-Date
foreach ($dem in $Demands) {
  if ($NetworkOverride -ne "") {
    $net = $NetworkOverride
  } else {
    if (-not $netByDemand.ContainsKey($dem)) { throw "Unknown demand: $dem" }
    $net = Join-Path $netDir $netByDemand[$dem]
  }
  if (-not (Test-Path $net)) { throw "Missing network: $net" }
  foreach ($seed in $Seeds) {
    foreach ($cand in $Candidates) {
      if (-not $controllerByCandidate.ContainsKey($cand)) { throw "Unknown candidate: $cand" }
      $controller = $controllerByCandidate[$cand]
      $name = "${dem}_${cand}_seed${seed}"
      # 재개(resume) — 마지막 state json 이 이미 있으면 그 케이스는 끝난 것이다.
      # 배치가 중간에 끊겨도 처음부터 다시 돌리지 않는다.
      $lastState = Join-Path $OutDir ("decisions_" + $name + "\state_" + $simPeriod.ToString("000000") + ".json")
      if (Test-Path $lastState) {
        Write-Host "CASE_SKIP name=$name reason=already_complete"
        continue
      }
      Write-Host "CASE_START name=$name controller=$controller"
      $t0 = Get-Date
      $extra = @{}
      if ($DemandProfile -ne "") { $extra["DemandProfile"] = $DemandProfile }
      if ($MappingOverride -ne "") { $extra["Mapping"] = $MappingOverride }
      if ($VbsConfigOverride -ne "") { $extra["VbsConfig"] = $VbsConfigOverride }
      & $runner @extra `
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
        -ForceStepwise `
        -StallSec $StallSec `
        -MaxAttempts $MaxAttempts `
        -DoneRows $expectedStateRows
      if ($LASTEXITCODE -ne 0) { Write-Host "CASE_FAIL name=$name" }
      Write-Host "CASE_DONE name=$name elapsed_sec=$([int]((Get-Date)-$t0).TotalSeconds)"
    }
  }
}
Write-Host "GRID_DONE elapsed_sec=$([int]((Get-Date)-$batchT0).TotalSeconds)"
Write-Host ""
Write-Host "NEXT:"
Write-Host "  C:/Users/alsrj/anaconda3/python.exe -B harness/g6/run_g6_shadow.py \"
Write-Host "      --run-dir $OutDir --out-dir outputs/g6_20260802 --t0 $WarmupSec --horizons 1,3,5"
