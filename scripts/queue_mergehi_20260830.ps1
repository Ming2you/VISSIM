<#
2026-08-30. 합류셀 보정 + 동역학 4항을 **붕괴 구간**에서 검정한다 (x1.8 · x2.2).

왜 원본 망이 아니라 여기인가. 원본(x1.0) 실측:
   canon_fdfit3   4657.8 / canon_mergedyn 4662.3 / canon_mergefix 4685.5
   freeway TTT 가 셋 다 1057~1062 로 무제어(1064.5)와 7 안. VSL 은 전 결정 120.0 고정,
   leader_density_excess 0/37. 본선이 용량의 58% 라 **제어할 일이 없다.**
   차이 4.5~27.7 은 무제어 5시드 sigma 50.7 안이라 구별이 안 된다.

이 배율에서는 VSL 이 39~49% 발동하고 density_excess 가 26~30/37 이다.

그리고 delta_merge=17.3 이 VSL 에 **새 이득 경로**를 연다 —
   dv_merge = -delta * dt * q_ramp * v / (L * lanes * (rho+kappa))
가 본선 속도 v 에 비례하므로 VSL 로 상류를 늦추면 합류 교란이 줄어든다.
지금까지는 alpha_vsl 0 · capacity_drop False · two_branch 없음으로 전부 닫혀 있었다.

  배율   무제어    기존 제어   VSL!=120   density_excess
  x1.8  6692.0   6699.3     39.2%      26/37
  x2.2  6958.9   7035.7     48.6%      30/37

  1  canon_mergefix   R_F_W 4->5 만                      단일변수 (대조 fdfit3 4657.8)
  2  canon_mergedyn   + tau7 / nu48 / kappa25 / delta17.3  단일변수 (대조 mergefix)

merge 보정: R_F_W 커넥터가 둘인데 체인 6072.6 m · 6774.3 m 로 서로 다른 셀에 붙는다
(셀 5 시작 = 6736.06 m). 생성기가 용량 가중 다수결인데 넷 다 900 vph 라 동률 -> 상류 4.
실측 유량은 431 대 781 로 하류가 64%. 오프라인 A/B 로 FW_W|4 밀도 MAPE 49.9% -> 16.8%,
전체 예측점수 +5.44% (동역학 4항 전체 적합 +4.9% 보다 크다).

동역학: 무제어 5런 150쌍으로 한-스텝-앞 적합. 홀드아웃(x1.6·x2.0) 점수 +15.7%.
delta 17.3 은 문헌값의 1400배지만 최적점이 실재하고(25 넘으면 악화, 40 부터 붕괴),
상류 셀은 안 움직이며(물리적 인과), 혼잡영역에서 속도·밀도 편의가 동시에 준다
(속도 +13.18 -> +7.78 · 밀도 -5.12 -> -3.58). 미터링 판단이 걸리는 자리가 그 영역이다.

VSL 격자도 10 단위로 넓혔다([80,100,120] -> [70..120]). 러너 VBS 허용값 115 -> 110.
**원본 망에서는 무효다** — fdfit3 실측이 전 37결정 VSL=120.0 하나뿐이다. 고수요 팔에서 산다.

현행은 queue_drain_horizon_sec=120.0 스칼라 하나를 램프 넷에 다 쓴다. 실측 통과시간은
6.5s ~ 77.4s 로 12배 벌어진다. 그래서 arrival 이 실측의 39% 로 나온다.

  램프      실측 통과시간   현행 arrival   교정 후   실측 유량
  R_D_W       33.4 s          210         754       752
  R_F_W       77.4 s          720        1116      1212
  R_D_E       30.7 s          240         938       938
  R_F_E        6.5 s          120         554       555
  합                         1350        3204      3457

모형 검정: 통과시간이 수요 x1.0~x2.2 에 걸쳐 상수다(변동계수 0.006~0.114). 기하량이라
상수여야 하고 실제로 그렇다. 처리량은 .fzp 고유 차량 직접 계수.
근거 scripts/calibrate_ramp_arrival_20260830.py · outputs/ramp_arrival_calibration_20260830.json

고칠 자리(queue_drain_horizon_sec_by_ramp)는 2026-08-04 에 이미 만들어져 있었고
값만 안 들어가 있었다. cap 도 같이 고친다 — 스칼라 900 이 R_F_W 실측 1212 를 자른다.

왜 중요한가. 어댑터 주석(:5960): '모델 ramp_arrival 이 플랜트의 3.5분의 1로 나왔고,
모델 세계에서만 미터가 수요를 구속하지 않아 dTTT/d(meter) 가 정의상 0 이 됐다.'
실측: x2.2 에서 미터링이 도착을 구속한 결정 0/37.

상류는 미터링을 루프 **밖에서 1회만** 푼다(wu_faithful_follower.py:4308).
그래서 되먹임이 한 방향이다 — 도시 agent 는 자기 녹색이 만들 미터링을 못 보고,
미터링이 정해질 때는 녹색이 이미 확정이다. VSL 은 원래 루프 안이고 결합변수
(off-ramp 유출)로도 실린다.

  배율   urban    freeway     합      VSL 끔 freeway
  x1.8  -158.8   +165.1    +7.3     +154.2
  x2.0  -206.6   +266.9   +59.8       -
  x2.2  -159.9   +238.5   +76.8     +167.3

VSL 을 끄고 미터링을 무제어와 같은 7200 으로 열어둬도 freeway 가 +167.3 남는다.
레버 값이 아니라 **구조**가 남는 설명이다.

구현: LinkAgentWuFollower 가 `_solve_freeway_segment_agents` 를 링크 단위 metered
solve 로 재정의한다. 상류가 그 분기를 `segment_agents` 로만 여니 그 플래그를 켜지만
**세그먼트 분해는 없다** — 이 클래스에서 그 플래그는 '미터링을 루프 안에서 푼다' 다.
빌더는 SEG13 키를 비운 **뒤에** 켠다(먼저 켜면 그 키 가드가 즉사시킨다).

  1-2  x1.8 · x2.2  VSL 끔(vsl_set=[120])         손해가 VSL 단독인가
  3-6  x1.6~x2.2    용량강하 ON + alpha_vsl 0.1    이길 기구를 주면 이기는가

실측 (기본 FD · VSL 켬):
  배율   무제어   제어      효과    freeway    urban   VSL!=120
  x1.4  5394.1  5198.7  -195.4     -2.1  -194.9     4.1%
  x1.6  6001.1  6264.6  +263.4  +221.7   +38.6    21.6%
  x1.8  6692.0  6699.3    +7.3  +165.1  -158.8    39.2%
  x2.0  6869.4  6929.2   +59.8  +266.9  -206.6    43.2%
  x2.2  6958.9  7035.7   +76.8  +238.5  -159.9    48.6%

VSL 발동률과 freeway 손해가 같이 움직인다. VSL 이 거의 안 켜지는 x1.4 에서만 이긴다.

왜. VSL 이 x1.8·x2.2 에서 39~49% 결정에 발동했는데 제어가 졌다(+7.3 · +76.8).
freeway +165 · +238 이 도시부 -159 를 덮었다. 그런데 모델에 VSL 이 이길 기구가
없었다 — capacity_drop_anticipation=False 라 nu 가 65 고정이고, V(rho) 가 단일값
단조면 감속이 처리량을 못 늘린다. **이길 방법이 없는 플랜트에서 지고 있었다.**

켜면 rho>rho_crit 에서 nu 65 -> 250 으로 전환된다(용량강하). 그러면 VSL 이 상류를
늦춰 병목 도착유량을 줄이고 병목을 subcritical 로 지키는 고전 경로가 열린다.
select_anticipation_nu 가 plant(metanet.py:615)와 follower 예측
(local_freeway_plant.py:308) 양쪽에서 불리므로 정합한다.

alpha_vsl 은 V_eff = min(FD, (1+alpha)*VSL) 의 계수다 — **클수록 VSL 이 약해진다**.
0.1 이면 VSL 80 의 실효 상한이 88 이다.

  배율   무제어    용량강하 없는 제어
  x1.6  6001.1    (미실행)
  x1.8  6692.0    6699.3  (+7.3)
  x2.0  6869.4    (미실행)
  x2.2  6958.9    7035.7  (+76.8)

  canon_fd3sw18_novsl   x1.8 · vsl_set [80,100,120] -> [120.0]
  canon_fd3sw22_novsl   x2.2 · 〃

실측 (VSL 켠 판):
  x1.8  제어 6699.3 대 무제어 6692.0  = +7.3   freeway +165.0 · urban -158.8
  x2.2  제어 7035.7 대 무제어 6958.9  = +76.8  freeway +238.4 · urban -159.8
  VSL 이 39.2% · 48.6% 결정에서 120 이 아니었다.

모델에서 VSL 이 이득을 낼 경로가 전부 꺼져 있다 — alpha_vsl 0.0 ·
capacity_drop_anticipation False · vsl_fd_two_branch 없음.
metanet.py 주석이 그 셋을 'VSL 의 교과서 이득' 이라 부른다. 없으면 V(rho) 가
단일값 단조라 감속이 처리량을 못 늘리고 VSL 은 구조적 순손실이다.

레버 배선은 안 건드리고 **선택지만** 자유류 하나로 묶는다 — 가격·오라클·롤아웃
경로가 그대로라 다른 변수가 안 섞인다.

queue_fd3_20260828.ps1 (fdfit3 · sw18 · sw22) 이 끝난 뒤에 돌린다.
넷을 모으면 배율에 따른 제어 이득 곡선이 된다.

  배율   초과%(27.0)  무제어 대조
  x1.6      8.1%       6001.1     붕괴 시작
  x1.8     23.6%       6692.0     붕괴
  x2.0     28.4%       6869.4     포화 진입
  x2.2     31.2%       6958.9     포화

  1  canon_fdfit3    원본 망 · FD 120.0/27.00/1.60/6937.0   <- canon_fdfit2(4660.9) 와 FD 만 다름
  2  canon_fd3sw18   x1.8 망 (초과 23.6%) 대조 6692.0
  3  canon_fd3sw22   x2.2 망 (초과 31.2%) 대조 6958.9

2단계 재적합: 14런 6944점, 혼잡부 43점(1.7%) -> 1459점(21.0%), 밀도 32.7 -> 65.3.
같은 자료 RMSE  새 10.509 · 직전(21.70) 12.234 · 현행 parameters 13.733.

**x1.8·x2.2 는 망이 달라 원본 사다리에 붙이지 마라.** 각자 같은 망 무제어와만 비교한다.

x1.6 ~ x2.4 를 0.1 단위로. 본선 진입 둘(link 26 경부_NB · 74 경부_EB)의 volume 만
곱한 망이고 램프 relFlow 는 원본 그대로다 — 기존 fw12/fw14 는 둘을 같이 바꿔서
두 변수였다. 망 생성·검증: scripts/make_freeway_demand_sweep_20260828.py

왜. x1.4 에서도 본선이 용량의 78% 라(밀도 중앙 12.25, 임계 21.25) 붕괴가 없다.
적합 FD 의 4차로 용량은 6218 veh/h 인데 x1.6 부터 첨두가 7392 로 그것을 넘는다.

다음 단계. 이 9런 + 기존 5런으로 FD 재적합(scripts/refit_freeway_fd_20260828.py)
-> 그 값으로 제어 런. 지금 FD 혼잡부 표본은 43점(1.7%)뿐이라 rho_crit 이 그 43점에
달려 있다. sweep 이 그 구간을 채운다.

tuning 은 canon_nolencap 을 쓰지만 -Controller no-control 이라 제어는 안 걸린다.
StallSec 86400 · MaxAttempts 2 유지.

**-ForceStepwise 가 필수다.** 없으면 결정 시점 상태 JSON 이 1개만 나오고(2026-08-28 실측)
FD 적합에 쓸 freeway_segments 가 안 남는다. env RW_FORCE_STEPWISE 는 러너가 덮으므로
반드시 러너 **인자**로 줘야 한다.

**바이트 단위로 만들었다.** 텍스트 왕복은 CRLF 를 겹쳐 백틱 줄이음을 깬다.

왜. fw14_ramp2 망에서 attempt 1 이 기동 중 idle 311s 로 워치독에 killed 됐다
(첫 결정 전, VISSIM 이 망을 여는 단계). 결정 자체는 중앙 92.7초로 문턱 300 아래다.
사용자 지시로 StallSec 을 86400 으로 올려 사실상 끈다 — 오래 걸려도 좋다.

  **StallSec 0 은 쓰지 마라.** 러너가 `if ($idle -gt $StallSec)` 로 판정하므로
  0 이면 첫 폴링에서 즉시 kill 된다. 끄려면 큰 값을 줘야 한다.

  MaxAttempts 도 2 로 줄였다 — kill 이 없으면 재시도의 의미가 EXIT_NO_DONE 뿐이다.

대조군: nc_fw14_ramp2_20260827 (무제어, 같은 망) 전체 TTT 5394.1 · freeway 1535.4
짝: canon_fdfit2_20260828 (같은 FD·제어, 원본 망) 4660.9 — 신기록

**바이트 단위로 만들었다.** 텍스트 왕복은 CRLF 를 겹쳐 백틱 줄이음을 깬다.

  1  canon_fdfit2   FD 실측 재적합만 (원본 망) — canon_nolencap 대비 단일변수
  2  canon_fdfw14   위 + fw14_ramp2 망 (고속도로 x1.4 · 온램프 2배)

왜. 수요를 x1.4 로 올린 무제어 프로브에서도 최대 밀도 32.66 으로 현행 임계 33.5 를
**0.0%** 초과했다. 막혀서가 아니라 임계가 높아서다 — 실측 재적합 21.70 이면
무제어 0.7% · fw12 1.9% · fw14 4.3% 가 초과한다. 그래서 VSL 이 5400초 내내 120.0
고정이었고 leader_density_excess 가 37/37 에서 0.000 이었다.

  1 - canon_nolencap    = FD 효과 (원본 망 사다리에 바로 붙는다)
  2 - nc_fw14_ramp2     = 고속도로가 실제로 일할 때 제어가 이기는가
  **2 는 망이 달라 원본 사다리에 붙이지 마라.**

평가는 보호망 분해로 한다 — scripts/protected_ttt_from_fzp_20260828.py
(전체 TTT 는 제어 불가 monitor 9개 SC 를 17~20% 섞는다).

**바이트 단위로 만들었다.** 텍스트 왕복은 CRLF 를 겹쳐 백틱 줄이음을 깬다.

  1  canon_dpoff      canon_plantfix 에서 dead_phase_beta_zero 만 끈다        <- 과제 1
  2  canon_phasefix   위 + 선언 phase 보정 11건                              <- 과제 3

**순서가 뒤집힌 이유.** 요청은 3->1 이었으나 둘이 상호작용한다 — phase 보정이 dead_phase
판정을 바꾼다(죽이는 movement 13 -> 9). dead_phase 를 끈 팔이 base 여야 보정이 단일변수가
된다. 그래서 dpoff 를 먼저 돌린다. 최종 판정은 두 팔이 다 끝나야 나오므로 순서는
답을 바꾸지 않고, 어느 쪽이 먼저 보이느냐만 바꾼다.

  canon_phasefix - canon_dpoff      = phase 보정 효과 (단일변수)
  canon_dpoff    - canon_plantfix   = dead_phase 효과 (단일변수)

사다리: tau 4699.1 · bstoA 4704.1 · default 4735.0 · 무제어(s13) 4819.4
        canon_plantfix 4823.2 · canon_gne_nofar 5215.4 · canon_gne_t15 5225.7 · canon_gne_far 5232.3
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
  @{ name = "canon_mergefix_x18_20260830"; tuning = "evaluation/configs/canon_mergefix_x18_20260830.json"; network = "network/real_world_gaepo_modi/modi_eval_userfix_20260814e_fwsweep_x18.inpx"; note = "x1.8 · 합류셀 보정 R_F_W 4->5 (+VSL 10단위) — 무제어 6692.0 / 기존제어 6699.3" },
  @{ name = "canon_mergedyn_x18_20260830"; tuning = "evaluation/configs/canon_mergedyn_x18_20260830.json"; network = "network/real_world_gaepo_modi/modi_eval_userfix_20260814e_fwsweep_x18.inpx"; note = "x1.8 · 위 + 동역학 4항 tau7/nu48/kappa25/delta17.3 — 무제어 6692.0 / 기존제어 6699.3" },
  @{ name = "canon_mergefix_x22_20260830"; tuning = "evaluation/configs/canon_mergefix_x22_20260830.json"; network = "network/real_world_gaepo_modi/modi_eval_userfix_20260814e_fwsweep_x22.inpx"; note = "x2.2 · 합류셀 보정 R_F_W 4->5 (+VSL 10단위) — 무제어 6958.9 / 기존제어 7035.7" },
  @{ name = "canon_mergedyn_x22_20260830"; tuning = "evaluation/configs/canon_mergedyn_x22_20260830.json"; network = "network/real_world_gaepo_modi/modi_eval_userfix_20260814e_fwsweep_x22.inpx"; note = "x2.2 · 위 + 동역학 4항 tau7/nu48/kappa25/delta17.3 — 무제어 6958.9 / 기존제어 7035.7" }
)

foreach ($arm in $arms) {
  $name = $arm.name
  $tuningAbs = Join-Path $repo $arm.tuning
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
      -Controller "wu-link" -SimPeriod 5400 -ControlIntervalSec 150 -StateLogIntervalSec 30 -Seed $Seed -StallSec 86400 -MaxAttempts 2
  Write-Output ("[{0}] {1} 종료 (exit {2})" -f (Get-Date -Format "HH:mm:ss"), $name, $LASTEXITCODE)

  Get-Process | Where-Object { $_.ProcessName -like "*VISSIM*" } | Stop-Process -Force -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 5
}
Write-Output "=========================================================="
Write-Output ("[{0}] 큐 종료" -f (Get-Date -Format "HH:mm:ss"))
