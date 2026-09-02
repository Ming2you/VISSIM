<#
2026-09-02. 승격 손해 분해 2라운드 — 4팔.

1라운드가 범인을 못 찾았다. 찾은 것은 **범인이 아닌 셋**이다 (기준선 ctl_outflow 8822.8):
  arm_perimoff  8718.7  -104.1   perimeter 용량 배분    -> 승격이 해로웠다
  arm_cap180    8915.7   +92.9   램프별 실측 상한       -> 승격이 이로웠다
  arm_natcyc    8973.2  +150.4   주기/예산 재산정       -> 승격이 이로웠다
셋의 순합은 -139.2 (이득). 그런데 승격 전체는 +578.2 손해였다.
=> 손해는 미검증 조각에 있고, 가법 가정 아래 **4팔의 합은 -717.4 여야 한다.**

## 전제 하나를 고쳤다

'승격 = 커밋 698e4d2 -> 35682c1' 이 **틀렸다.** canon_farbn 런의 어댑터 sha
31ff447a 는 어댑터를 건드린 54개 커밋 **어디에도 없다**(미커밋 작업트리에서 돌았다).
ctl_base 의 23567e95 는 8eae363 과 정확히 일치한다. 그래서 델타를 코드가 아니라
**런 산출물**로 봉인했다 — 두 런의 37결정 내내 상수인 metadata 키를 대조해
값이 다른 상수 13개 · ctl_base 에만 있는 상수 20개를 얻었다.

그 대조가 후보를 크게 줄였다. canon 에 **이미 켜져 있던 것**은 델타가 아니다:
  far 실측 배수율(far_measured_enabled=1.0 · far_measured_points=53) · far 램프용량 스왑 ·
  현시보정 11건(movement_phase_correction_applied=11.0) · metering_in_gne.
유출 3스위치는 양쪽 다 꺼져 있었고 기준선에서만 켜진다.

## 4팔 (각각 미검증 조각과 1:1)

  1 phase11  신규 현시보정 6건. **가장 유력하다.**
     5건의 declared phase 가 전부 SC107_p1 이고 SC107_p1 은 네 런 37결정 **전부 녹색 0.00**
     이다(실측 확인). SC16_W_to_N_SC12 도 SC16_p4 = 0.00. 즉 보정은 죽은 현시에 갇힌
     beta(SC107 1.5 + SC16 0.125)를 살아있는 현시로 옮긴다. 녹색에 그대로 찍힌다:
       SC107_p2  canon 20.16 -> ctl_outflow 43.14   SC16_p3  46.54 -> 65.16
     그리고 **상호작용의 흔적이 있다** — relabel 단독(arm_perimoff)은 SC107_p2 를
     24.70 까지만 올리는데 perimeter 를 얹으면 43.14 다. perimeter 의 해(-104.1)가
     이 relabel 을 통해 증폭됐을 수 있다.
     예측: 범인이면 TTT <= 8520. 녹색이 25s 로 안 돌아가면 설치 실패이니 런을 버려라.

  2 rqclip   관측 램프큐 상한 절단 복원.
     기준선 실측: **22/37 결정에서 상한 초과**, 누적 1812.9 veh, R_F_E 최대 248.0
     (상한 153.6 · q^2 2.60배), R_D_W 206.0(상한 153.2 · 1.81배).
     살아있는 소비처는 far 말단비용 하나다(stackelberg_mpc:180-204 의 q^2 항).
     후보 마진이 작다 — objective_spread 중앙 4.91 · gap 중앙 0.578.
     예측: 범인이면 TTT <= 8620 이고 spread 중앙값이 내려간다.
     주의: ramp_obs_*_occupancy 는 이 팔에서도 1.0 을 넘는다(관측은 무절단으로 심긴다).
     그건 실패 신호가 아니다.

  3 nxbeta   비존재 movement beta 0화.
     실효 2건이 SC7_E_SC16_to_N_SC11 · SC7_E_to_N_SC11 이고 둘 다 SC7_p3 =
     37결정 전부 0.00. 형제 _to_S_SC108 은 SC7_p4(평균 50.24s, 살아있음).
     팔 1과 **같은 기구**이고 범위가 좁다. 셋째는 install_measured_turn_beta 가 덮어 no-op.
     예측: 팔 1의 1/3~1/2, -60 ~ -250. |d| < 60 이면 설명에서 빠진다.

  4 offidx   병합 후 off_ramp 인덱스 재구축.
     되돌리면 죽은 이름 2건(SC1001_offE_to_W · SC1001_offW_to_W)이 부활하고 둘 다
     병합 후 spec 에 없어 beta 가 유실된다 -> OR_D_E·OR_D_W beta 합 1.0 -> 0.833.
     그 receiving_link 가 SC1001_W_out 이고, 유출 스위치가 램프행 이탈 게이트를 건
     바로 그 링크다. 기준선에서만 증폭된다.
     예측: -50 ~ -200. 잔차 후보다.

## 설치 검증 (발사 전 확인함 — 각 팔이 정확히 한 축만 바꾼다)

  팔        보정적용  건너뜀  nxbeta  재구축  clip
  기준선      17      0      1.0     1.0    False
  phase11     11      6      1.0     1.0    False
  rqclip      17      0      1.0     1.0    True
  nxbeta      17      0      0.0     1.0    False
  offidx      17      0      1.0     0.0    False

가드는 넷 다 **기본값이 현행 거동**이라 config 키가 없으면 비트 동일이다.

## 판정 척도 (무제어 5시드 sigma 50.7)
  범인 d<=-300 · 주요기여 -300<d<=-150 · 부수 -150<d<=-60 · 구별불가 |d|<60 · 역방향 d>=+60

## 남은 불확실성
  (1) 가법성이 이미 깨져 보인다(SC107_p2 상호작용). 합이 -717 을 안 맞춰도 실패가 아니다.
  (2) 31ff447a 를 복원 못 했다. 진단을 안 남기는 조각은 100% 배제 못 한다.
      네 팔이 전부 작으면 다음은 agent_topology.metering_in_gne:false 다.
  (3) +-100~150 이 잡음 바닥일 수 있다. 검증된 셋이 -104 +93 +150 이었다.
      부호가 갈리거나 전부 |d|<100 이면 다음은 조각 사냥이 아니라 위약 팔 + 2시드 재현이다.
#>
param([int]$Seed = 13)

$ErrorActionPreference = "Continue"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runner = Join-Path $repo "scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1"

$env:RW_MAINLINE_SG_ONLY = "1"
$env:RW_PYTHON_EXE = "C:/Users/TRLAB/AppData/Local/Programs/Python/Python312/python.exe"
foreach ($v in @("RW_OFFSET_WRITER","RW_MOVING_SPEED","RW_LANE_DELAY_CORRECTION","RW_NP_STATE_BAND",
                 "RW_STOPPED_SPLIT","RW_MAINLINE_PLAN","RW_MAINLINE_SHARE_SG","RW_ADAPTER_MODE",
                 "RW_QUEUE_ORIGIN_BINDING","RW_TAU_LENGTH_CAP","RW_DEAD_PHASE_BETA_ZERO",
                 "RW_BOUNDARY_INFLOW_SEED","RW_FORCE_STEPWISE","RW_MOVEMENT_PHASE_CORRECTION",
                 "RW_NARROW_AXIS_SG","RW_VALIDATION_FIXED_SIGNAL")) {
  Remove-Item "env:$v" -ErrorAction SilentlyContinue
}

$vbsCfg = Join-Path $repo "evaluation/generated/real_world_modi_control_config_distributed_core17legs4f_20260826.vbs"
$sgplan = $vbsCfg -replace "[.]vbs$", "_sgplan.vbs"
foreach ($f in @($vbsCfg, $sgplan)) {
  if (-not (Test-Path $f)) { Write-Output "!! 없음: $f"; exit 1 }
}

$arms = @(
  @{ name = "arm_phase11_x18_20260902"; tuning = "evaluation/configs/arm_phase11_d00_x18_20260902.json"; network = "network/real_world_gaepo_modi/modi_eval_userfix_20260814e_fwsweep_x18_rampbn.inpx"; controller = "wu-link"; note = "분해 2R — 신규 현시보정 6건만 건너뜀 — SC107 5건 p1->p2 · SC16 1건 p4->p3" },
  @{ name = "arm_rqclip_x18_20260902"; tuning = "evaluation/configs/arm_rqclip_d00_x18_20260902.json"; network = "network/real_world_gaepo_modi/modi_eval_userfix_20260814e_fwsweep_x18_rampbn.inpx"; controller = "wu-link"; note = "분해 2R — 관측 램프큐를 다시 상한으로 절단 — 승격 전 거동" },
  @{ name = "arm_nxbeta_x18_20260902"; tuning = "evaluation/configs/arm_nxbeta_d00_x18_20260902.json"; network = "network/real_world_gaepo_modi/modi_eval_userfix_20260814e_fwsweep_x18_rampbn.inpx"; controller = "wu-link"; note = "분해 2R — 비존재 movement 3건의 beta 0화를 끔 — SC7_p3 에 다시 가둠" },
  @{ name = "arm_offidx_x18_20260902"; tuning = "evaluation/configs/arm_offidx_d00_x18_20260902.json"; network = "network/real_world_gaepo_modi/modi_eval_userfix_20260814e_fwsweep_x18_rampbn.inpx"; controller = "wu-link"; note = "분해 2R — 병합 후 off_ramp 인덱스 재구축을 끔 — 죽은 이름 2건 부활" }
)
foreach ($arm in $arms) {
  $name = $arm.name
  $tuningAbs = Join-Path $repo $arm.tuning
    $ctrl = if ($arm.ContainsKey("controller")) { $arm.controller } else { "wu-link" }
    # 배열 splat 금지. PowerShell 은 `if` 출력의 1원소 배열을 String 으로 언롤하고,
    # 문자열 splat 은 그걸 **문자 단위 위치인자**로 쪼갠다 (2026-09-01 nc_rampbn_x18 사고:
    # "-ForceStepwise" -> 14개 인자, DemandScale=111 · 게이트맵=i · ForceStepwise 는 끝내 False).
    # 빈 배열 @() 도 $null 로 언롤돼 팬텀 위치인자 1개가 ControlStartSec 에 꽂힌다.
    # switch 는 -Name:$bool 로 넘긴다.
    $stepwise = ($ctrl -eq "no-control")
  & $env:RW_PYTHON_EXE (Join-Path $repo "scripts/preflight_tuning_paths.py") $tuningAbs --quiet
  if ($LASTEXITCODE -ne 0) { Write-Output ("!! {0} 사전점검 실패 — 건너뛴다" -f $name); continue }
  & $env:RW_PYTHON_EXE (Join-Path $repo "scripts/verify_parameters.py") $tuningAbs --quiet
  if ($LASTEXITCODE -ne 0) { Write-Output ("!! {0} 파라미터 검증 실패 — 건너뛴다" -f $name); continue }

  for ($i = 0; $i -lt 30; $i++) {
    $alive = @(Get-Process | Where-Object { $_.ProcessName -like "*VISSIM*" }).Count
    if ($alive -eq 0) { break }
    Write-Output ("[{0}] VISSIM {1}개 남아 있다. 대기." -f (Get-Date -Format "HH:mm:ss"), $alive)
    Start-Sleep -Seconds 10
  }

  $outDir = Join-Path $repo "evaluation/runs/$name"
  Write-Output ("[{0}] {1} 시작 — {2}" -f (Get-Date -Format "HH:mm:ss"), $name, $arm.note)
  & $runner -Name $name -OutDir $outDir `
      -Adapter "evaluation/controllers/vissim_stackelberg_adapter.py" `
      -Tuning  $arm.tuning `
      -Network $arm.network `
      -VbsConfig "evaluation/generated/real_world_modi_control_config_distributed_core17legs4f_20260826.vbs" `
      -Calibration "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json" `
      -Mapping "evaluation/real_world_modi_control_distributed_20260728/control_mapping_distributed_core17legs4b_20260819.json" `
      -Controller $ctrl -SimPeriod 5400 -ControlIntervalSec 150 -StateLogIntervalSec 30 -Seed $Seed -StallSec 86400 -MaxAttempts 2 -ForceStepwise:$stepwise
  Write-Output ("[{0}] {1} 종료 (exit {2})" -f (Get-Date -Format "HH:mm:ss"), $name, $LASTEXITCODE)

  Get-Process | Where-Object { $_.ProcessName -like "*VISSIM*" } | Stop-Process -Force -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 5
}
Write-Output "=========================================================="
Write-Output ("[{0}] 큐 종료" -f (Get-Date -Format "HH:mm:ss"))
