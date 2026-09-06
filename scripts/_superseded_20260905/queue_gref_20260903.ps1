<#
2026-09-03. SC105 p1 오배분 — green_reference · primary_by_price.

## 무엇을 찾았나

.fzp 로 제어 적자 +386.5(무제어 7952.4 대 arm_rampclean 8339.0)를 끝까지 좁혔다.

  권역        제어권역 +569.5 · monitor +15.7 · freeway -494.8
  SC 별       SC105 +303.3(53%) · SC1002 +172.6 · SC1001 +59.9 · SC108 -91.1
  링크 별     **링크 420 하나 +278.6** (속도 47.4 -> 4.5 kph, 29.2 -> 307.8 veh·h)
              = SC105 손실의 92% · 제어권역 손실의 49% · **전체 적자의 72%**

링크 420(N_SC1002 접근로)의 현시별 실태 (결정 24):

    현시        큐      용량       녹색    처리     판정
    p1       227.6   1,652/h    28.0s   12.9   **부족 215**
    p2        66.4     413/h    28.7s    3.3   **부족 63**
    p3        14.4   1,859/h    40.7s   21.0   충분
    p4         6.6     620/h    40.7s    7.0   충분

큐 227.6 인 현시에 28초, 큐 6.6 인 현시에 40.7초다. native 는 p1(=SG4)에 51초를 준다.

## 배제된 것 (전부 실측)

  관측 실패    아니다. link_counts[420] 243~273 · movement 큐 154.9 로 정확히 본다.
  위상잠금     아니다. SC105 는 SG 8개가 결정시점 전부 녹색 0.00 이라 균일 편향이고,
               arm_window 는 오히려 +671.3 악화.
  offset       아니다. nc_off0(제어 17 SC 의 native offset 만 0) = 8000.9, 무제어 대비
               **+48.5 로 sigma 50.7 아래** — 구별 불가.
  동시현시     아니다. SC5 +15.9 · SC7 +40.7 로 작다.
  리더 정련    아니다. arm_refine 은 정련이 37/37 정상 작동했는데 +728.9 악화.
  beta_hat     무관하다. arm_nobeta 는 -386.1 로 크게 이기지만 SC105 는 +304.0 로 불변
               (이득은 SC1001 -99.6 에서 왔다).

p1 은 네 팔(rampclean·window·nobeta·refine) 전부에서 **정확히 28.0** 이다.

## 가설 — 배분기의 자유도가 1차원이고 나머지가 직전값에 고착

  priced_wu_link_controller.py:209-211
    green_reference_mode: str = "previous"   # 나머지 현시 배분의 기준
                                              # "pressure" = 현시별 큐 비례
  어댑터:5192 primary_by_price 주석
    "distribute_phase_green 의 자유도가 1차원이라 그 축이 p1 에 고정돼 있으면
     다른 현시를 못 올린다(실측: SC5 p3 가 가격 1위인 결정 14개 전부에서 하한에 묶임)"

둘 다 config 로 켤 수 있는데 우리 config 에 없어 기본값이다. 그러면 자유도가 p1 하나이고
나머지는 직전 비율 그대로이므로, p3/p4 가 큐 14.4/6.6 인데도 40.7s 를 계속 받는다.

  A arm_gref     urban.green_reference = "pressure"
  B arm_primary  phase_price.primary_by_price = true
  C arm_grefpri  A + B  (이 세션에서 비가법성이 컸으므로 조합도 잰다. 의심 커서 먼저 돌린다)

설치 검증 (발사 전 확인):
    팔          green_reference_mode   primary_by_price
    기준선      previous               False
    gref        pressure               False
    primary     previous               True
    grefpri     pressure               True

## 결정적 예측

기준선 arm_rampclean 8339.0 (제어권역 3599.0 · SC105 418.8 · 링크420 307.8).
고쳐졌다면 **SC105_p1 이 28.0 을 벗어나 40s 이상**으로 올라가고 링크 420 속도가 회복돼야 한다.
p1 이 여전히 28.0 이면 가설이 죽고, 자유도 구조가 아니라 다른 곳을 봐야 한다.
무제어까지 남은 폭이 386.5 이고 링크 420 이 그중 278.6 이다.
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
  @{ name = "arm_grefpri_x18_20260903"; tuning = "evaluation/configs/arm_grefpri_d00_x18_20260903.json"; env = @{}; note = "C — green_reference=pressure + primary_by_price" },
  @{ name = "arm_gref_x18_20260903"; tuning = "evaluation/configs/arm_gref_d00_x18_20260903.json"; env = @{}; note = "A — green_reference=pressure" },
  @{ name = "arm_primary_x18_20260903"; tuning = "evaluation/configs/arm_primary_d00_x18_20260903.json"; env = @{}; note = "B — primary_by_price=true" }
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
