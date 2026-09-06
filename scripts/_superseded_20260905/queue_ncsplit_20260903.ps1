<#
2026-09-03. rampbn 망 편집의 책임 분해 — nc_base / nc_lcd200 / nc_rampmax.

## 왜

같은 시드 13 · 같은 수요 · **둘 다 무제어**인데:

    원본  x18        6675.7 veh.h   (ncsweep_x18_20260828)
    rampbn x18       7952.4 veh.h   (nc_out_x18_20260902)   +1276.7  (+19.1%)

제어 적자(+386.5)의 3.3배를 망 편집 하나가 이미 만들어놨다. 링크 분해상 증가분의
84%가 고속 본선(링크 2 72.3->15.2 kph, 74 67.0->13.0, 26 75.0->39.9)이고
램프 미터 커넥터 8개는 무제어에서 정지차량 0 . 41 kph 로 자유류다.
즉 증량은 램프를 막은 게 아니라 **본선을 무너뜨렸다.**

## 속성 전수 대조 결과 rampbn = 원본 + 정확히 셋

    (1) 링크 8개(10480,10482,10484,10490,10639,10644,10646,10681) lnChgDist 1000 -> 200
    (2) 경로 17개 relFlow 상향 (변경분 몫 574.5% -> 826.7%, 평균 1.44배)
    (3) 평가 간격 6개 160 -> 150s  (계측만, 물리 아님)

그 외 요소 26,822개 전부 동일. 한쪽에만 있는 요소 0개.

(1)만 든 망 _lcd200 과 (2)만 든 망 _rampmax 가 이미 있고 런은 없다.

## 이 팔들이 재는 것

    nc_lcd200  - nc_base   = 차선변경거리 축소의 순수 비용   <- 거동 파라미터
    nc_rampmax - nc_base   = 수요 증량의 순수 비용           <- 진짜 '차량 대수'
    nc_out     - (합)      = 교호작용

nc_base 를 08-28 ncsweep 재사용 대신 다시 도는 이유: 08-28 런의 러너 인자
(-ForceStepwise 등)가 09-02 레시피와 같다는 보장이 없다. 4개를 같은 레시피로
돌려야 뺄셈이 성립한다.

## 판정

  lcd200 이 지배적이면 -> 수요 증량은 무죄. 범인은 차선변경거리 200m 이고
                        이건 수요가 아니라 모형 파라미터다. 되돌리면 된다.
  rampmax 가 지배적이면 -> 증량 자체가 본선을 무너뜨렸다. 배수를 낮춰야 한다.
  |d| < 60 은 구별 불가 (무제어 5시드 sigma 50.7).

기준: nc_out_x18_20260902 = 7952.4 / ncsweep_x18_20260828 = 6675.7
#>

param([int]$Seed = 13)
$ErrorActionPreference = "Continue"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runner = Join-Path $repo "scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1"
$env:RW_PYTHON_EXE = "C:/Users/TRLAB/AppData/Local/Programs/Python/Python312/python.exe"
$env:RW_MAINLINE_SG_ONLY = "1"
foreach ($v in @("RW_OFFSET_WRITER","RW_MOVING_SPEED","RW_LANE_DELAY_CORRECTION","RW_NP_STATE_BAND",
                 "RW_STOPPED_SPLIT","RW_MAINLINE_PLAN","RW_MAINLINE_SHARE_SG","RW_ADAPTER_MODE",
                 "RW_QUEUE_ORIGIN_BINDING","RW_TAU_LENGTH_CAP","RW_DEAD_PHASE_BETA_ZERO",
                 "RW_BOUNDARY_INFLOW_SEED","RW_FORCE_STEPWISE","RW_MOVEMENT_PHASE_CORRECTION",
                 "RW_NARROW_AXIS_SG","RW_VALIDATION_FIXED_SIGNAL","RW_QUEUE_COUNTER",
                 "RW_QUEUE_WINDOW","RW_QUEUE_WINDOW_STAT","RW_STATE_LOG")) {
  Remove-Item "env:$v" -ErrorAction SilentlyContinue }

$arms = @(
  @{ Name = "nc_base_x18_20260903";    Net = "modi_eval_userfix_20260814e_fwsweep_x18.inpx" },
  @{ Name = "nc_lcd200_x18_20260903";  Net = "modi_eval_userfix_20260814e_fwsweep_x18_lcd200.inpx" },
  @{ Name = "nc_rampmax_x18_20260903"; Net = "modi_eval_userfix_20260814e_fwsweep_x18_rampmax.inpx" }
)

foreach ($arm in $arms) {
  for ($i = 0; $i -lt 60; $i++) {
    $alive = @(Get-Process | Where-Object { $_.ProcessName -like "*VISSIM*" }).Count
    if ($alive -eq 0) { break }
    Write-Output ("[{0}] VISSIM {1}개 대기" -f (Get-Date -Format "HH:mm:ss"), $alive)
    Start-Sleep -Seconds 20
  }
  $name = $arm.Name
  Write-Output ("[{0}] {1} 시작 — {2}" -f (Get-Date -Format "HH:mm:ss"), $name, $arm.Net)
  & $runner -Name $name -OutDir (Join-Path $repo "evaluation/runs/$name") `
      -Adapter "evaluation/controllers/vissim_stackelberg_adapter.py" `
      -Tuning  "evaluation/configs/canon_nolencap_20260828.json" `
      -Network ("network/real_world_gaepo_modi/" + $arm.Net) `
      -VbsConfig "evaluation/generated/real_world_modi_control_config_distributed_core17legs4f_20260826.vbs" `
      -Calibration "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json" `
      -Mapping "evaluation/real_world_modi_control_distributed_20260728/control_mapping_distributed_core17legs4b_20260819.json" `
      -Controller "no-control" -SimPeriod 5400 -ControlIntervalSec 150 -StateLogIntervalSec 30 -Seed $Seed -StallSec 86400 -MaxAttempts 2 -ForceStepwise:$true
  Write-Output ("[{0}] {1} 종료 (exit {2})" -f (Get-Date -Format "HH:mm:ss"), $name, $LASTEXITCODE)
  Get-Process | Where-Object { $_.ProcessName -like "*VISSIM*" } | Stop-Process -Force -ErrorAction SilentlyContinue
}
Write-Output ("[{0}] 3팔 완료" -f (Get-Date -Format "HH:mm:ss"))
