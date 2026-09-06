<#
2026-09-03. 승격 정본 위의 3팔 — 위상잠금 · beta끄기 · 리더정련.

기준선 = arm_rampclean_x18_20260902 **8339.0** (승격된 canon_outflow 와 설치 비트 동일).
직전 기준선 8822.786 이 아니다 — on-ramp 결합 승격(-483.8)이 들어갔다.

  1 arm_window   ② 위상잠금.  env RW_QUEUE_WINDOW=1 + RW_QUEUE_WINDOW_STAT=mean 만.
     제어주기 150s = 신호주기 150s 라 관측 순간이 늘 같은 위상에 떨어진다. 실측:
     SG 144개 중 **115개(79.9%)가 결정시점에 한 번도 녹색이 아니다**. 전체표본에서 항상
     적색인 건 14개(9.7%)뿐이니 그 115개도 실제론 정상 작동한다(녹색비율 중앙 0.246).
     결정시점 녹색비율 중앙 0.000 대 전체 0.253, |차이| 중앙 0.238 · 최대 0.474.
     리더/팔로워가 쓰는 건 현시 간 **상대** 큐라 그대로 배분 왜곡이 된다.
     완화 코드는 VBS·어댑터 양쪽에 이미 있는데 RW_QUEUE_WINDOW 를 **대입하는 코드가 0곳**이다.
     주의: mean 만 쓴다. max 는 link_counts 가 mean 을 쓰는데 stopped 만 max 라 내부 모순이다.
     주의: RW_STATE_LOG 은 설정하지 않는다(decision 이면 누적이 조기반환 뒤라 창이 조용히 빈다).
     한계: StateLogIntervalSec 30 이라 창 표본이 5개다(2026-08-23 win4c 는 30개였다).
     과거 실측 win4c: 4860.7 -> 4855.2 (-5.5). 단 그때는 x1.0 망·다른 기준선이고,
     당시 결론('매핑 버그의 종속 증상')은 지금 성립하지 않는다 — 그때 죽어 있던
     link_stopped_counts 가 지금은 링크별 저류분율을 직접 정해 창이 두 번째 채널을 탄다.

  2 arm_nobeta   ⑥ beta 끄기.  config_overrides.mpc.fallback_guard_beta = false
     가드가 리더/폴백 TTT 를 비교할 때 **리더 쪽에만** beta_hat 을 곱한다. 실측:
       beta 이동량 |leader_ttt - leader_ttt_beta| 중앙 74.29 (최대 111.27)
       비교 신호   |leader_ttt - fallback_ttt|      중앙  0.3302 (최대 2.74)
       비율 중앙 **142배** · beta_hat 중앙 0.9096 · 1 미만 35/37
     주석은 '낙관을 beta>1 로 벌한다' 인데 실제론 리더 TTT 를 9% **깎아준다**(할인).
     그래서 TTT 게이트가 2/37 로 무력해지고, 기각 18/37 은 전부 PFO 비교가 만든다.
     (그 16건은 동률이 아니라 leader-pfo 중앙 +1.067 로 리더가 진짜로 진 것이다.)

  3 arm_refine   ④ 리더 정련.  adapter.flagship = {opt12: false}
     config 에 adapter.flagship 절이 없어 flagship_settings()가 {} 를 내고,
     settings.get('opt12', True) 가 기본 True 로 leader_skip_local_refinement 를 켠다.
     실측: refinement_active 4/37 · **selected_stage_refined 0/37** · coarse 중앙 9.
     같은 config 가 leader_refinement_candidate_count=5 를 명시하는데 무효 손잡이였다.
     후보 폭 중앙 4.91(목적함수 수준의 0.19%)인 지형에서 정련은 남은 유일한 해상도원이다.
     opt12 를 끄면 leader_rollout_early_stop 도 같이 꺼지는데, 그건 incumbent 초과 후보를
     조기 abort 하는 가지치기이고 TTT 가 누적량이라 답은 보존된다 — **속도만 느려진다.**
     그래서 이 팔은 다른 둘보다 오래 걸릴 수 있다(StallSec 86400 이라 kill 되지는 않는다).

## 판정
  무제어 7952.4 · 기준선 8339.0. 무제어까지 남은 폭이 386.6 이다.
  |d| < 60 이면 구별 불가로 읽는다(무제어 5시드 sigma 50.7).
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
  @{ name = "arm_window_x18_20260903"; tuning = "evaluation/configs/arm_window_d00_x18_20260903.json"; env = @{ RW_QUEUE_WINDOW = "1"; RW_QUEUE_WINDOW_STAT = "mean" }; note = "② 위상잠금 창 관측(mean)" },
  @{ name = "arm_nobeta_x18_20260903"; tuning = "evaluation/configs/arm_nobeta_d00_x18_20260903.json"; env = @{}; note = "⑥ fallback_guard_beta 끄기" },
  @{ name = "arm_refine_x18_20260903"; tuning = "evaluation/configs/arm_refine_d00_x18_20260903.json"; env = @{}; note = "④ 리더 정련 되살리기(opt12 false)" }
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
