<#
2026-09-03. SC105 p1 오배분 — 정본 수정을 켠다.

## 무엇을 찾았나

.fzp 로 제어 적자 +386.5(무제어 7952.4 대 arm_rampclean 8339.0)를 링크 하나까지 좁혔다.
    권역   제어권역 +569.5 · monitor +15.7 · freeway -494.8
    SC     SC105 +303.3(53%) · SC1002 +172.6 · SC1001 +59.9 · SC108 -91.1
    링크   **420 하나 +278.6** = 전체 적자의 72% (속도 47.4 -> 4.5 kph)

SC105 결정24 현시별:  큐 227.6 인 p1 에 28.0s · 큐 6.6 인 p4 에 40.7s. native 는 p1 에 51s.
p1 은 네 팔(rampclean·window·nobeta·refine) 전부에서 **정확히 28.0** 이었다.

## 원인은 이미 진단·수정돼 있었다

  fee7419 (2026-08-23) 이 같은 증상을 적어 뒀다 —
    'SC5 p3 가 하한 22.7 에 묶인 결정 14/33, 그 14개 전부에서 p3 가격이 1위.
     시스템이 p3 에 녹색이 가장 필요하다고 정확히 판단하면서 p3 를 굶긴다.'
    원인: distribute_phase_green 의 자유도가 1차원이고 그 축이 늘 live[0](=p1).
    1차 수정 primary_by_price -> **순효과는 회귀**(그래서 폐기)

  ff45df0 (2026-08-27, **사용자 지시**) 이 정본 수정이다 —
    현시가격을 GNE **안**으로. LinkAgentWuFollower._solve_urban_agent_local 이
    p1 축 대신 현시 벡터를 좌표하강한다. 채점은 정련과 같은 함수(local + Σ price·Δg).

**그런데 기본 꺼짐이고 우리 config 에 키가 없다.** 실런 진단이 그대로 보여준다:
    phase_vector_green_enabled = 0.0   (37/37 결정)
즉 지금까지 모든 런이 옛 p1 축 경로였다.

## 배제된 것 (전부 실측)
  offset       nc_off0 = 8000.9, 무제어 대비 +48.5 (sigma 50.7 아래, 구별 불가)
  위상잠금     arm_window +671.3 악화
  리더 정련    arm_refine +728.9 악화 (정련은 37/37 정상 작동)
  동시현시     SC5 +15.9 · SC7 +40.7 로 작다
  관측 실패    아니다. link_counts[420] 243~273 · movement 큐 154.9 로 정확히 본다
  beta_hat     arm_nobeta -386.1 로 크게 이기지만 SC105 는 +304.0 불변(이득은 SC1001 -99.6)

## 두 팔

  1 arm_ingne   phase_price.in_gne = true    <- 정본 수정
     in_gne_rounds 는 명시하지 않는다. 어댑터가 refine_rounds(12)를 물려준다 —
     in_gne 를 켜면 정련이 꺼지므로 그 탐색량을 GNE 안으로 옮겨야 하고, 2 로 두면 6배 얕다.
     설치 검증: phase_vector_green_enabled 0.0 -> **1.0** · in_gne_rounds 12

  2 arm_gref    urban.green_reference = pressure   <- 대조
     옛 p1 축 경로를 그대로 두고 '나머지 현시 배분 기준'만 직전비율에서 큐비례로.
     in_gne 가 이기면 이 팔은 부차적이지만, 지면 자유도 구조가 아니라 기준값 문제였다는 뜻이다.

## 결정적 예측

기준선 arm_rampclean 8339.0 (제어권역 3599.0 · SC105 418.8 · 링크420 307.8 · p1 28.0).
고쳐졌다면 **SC105_p1 이 28.0 을 벗어나고** 링크 420 속도가 회복돼야 한다.
p1 이 여전히 28.0 이면 벡터 탐색이 발화하지 않은 것이니 진단
phase_vector_green_enabled 를 먼저 확인하라(1.0 이어야 한다).
무제어까지 남은 폭 386.5, 그중 링크 420 이 278.6.
#>
param([int]$Seed = 13)

$ErrorActionPreference = "Continue"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runner = Join-Path $repo "scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1"

$env:RW_PYTHON_EXE = "C:/Users/TRLAB/AppData/Local/Programs/Python/Python312/python.exe"

# 팔별 env 는 아래 루프가 세운다. 매 팔 시작 때 전부 지우고 그 팔 것만 세운다 —
# 누출 트랩(RW_QUEUE_WINDOW 이 다음 팔로 새면 단일변수가 깨진다)을 막는다.
$CLEAN = @("RW_OFFSET_WRITER","RW_MOVING_SPEED","RW_LANE_DELAY_CORRECTION","RW_NP_STATE_BAND",
           "RW_STOPPED_SPLIT","RW_MAINLINE_PLAN","RW_MAINLINE_SHARE_SG","RW_ADAPTER_MODE",
           "RW_QUEUE_ORIGIN_BINDING","RW_TAU_LENGTH_CAP","RW_DEAD_PHASE_BETA_ZERO",
           "RW_BOUNDARY_INFLOW_SEED","RW_FORCE_STEPWISE","RW_MOVEMENT_PHASE_CORRECTION",
           "RW_NARROW_AXIS_SG","RW_VALIDATION_FIXED_SIGNAL",
           "RW_QUEUE_WINDOW","RW_QUEUE_WINDOW_STAT","RW_STATE_LOG")

$arms = @(
  @{ name = "arm_ingne_x18_20260903"; tuning = "evaluation/configs/arm_ingne_d00_x18_20260903.json"; env = @{}; note = "정본 수정 — phase_price.in_gne (현시 벡터 좌표하강)" },
  @{ name = "arm_gref_x18_20260903"; tuning = "evaluation/configs/arm_gref_d00_x18_20260903.json"; env = @{}; note = "대조 — 옛 경로에 green_reference=pressure" }
)
foreach ($arm in $arms) {
  $name = $arm.name
  foreach ($v in $CLEAN) { Remove-Item "env:$v" -ErrorAction SilentlyContinue }
  $env:RW_MAINLINE_SG_ONLY = "1"
  foreach ($k in $arm.env.Keys) { Set-Item -Path "env:$k" -Value $arm.env[$k] }
  $envShow = ($arm.env.Keys | ForEach-Object { "$_=" + $arm.env[$_] }) -join " "

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

  Write-Output ("[{0}] {1} 시작 — {2}   env: {3}" -f (Get-Date -Format "HH:mm:ss"), $name, $arm.note, $envShow)
  & $runner -Name $name -OutDir (Join-Path $repo "evaluation/runs/$name") `
      -Adapter "evaluation/controllers/vissim_stackelberg_adapter.py" `
      -Tuning  $arm.tuning `
      -Network "network/real_world_gaepo_modi/modi_eval_userfix_20260814e_fwsweep_x18_rampbn.inpx" `
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
