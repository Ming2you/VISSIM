<#
2026-09-03. 협조 파괴의 순수 비용 — nc_off0.

## 왜

.fzp 권역 분해로 제어가 지는 곳이 도시 신호임을 확정했다:

                     제어권역   monitor   freeway    ramp     전체
  무제어              3029.6    900.9    3552.1   208.5    7960.7
  arm_rampclean      3599.0    916.5    3057.3   468.5    8344.0
  무제어 대비          +569.5    +15.7    -494.8            +383.3

monitor(+15.7)도 freeway(-494.8, 오히려 이김)도 아니고 제어권역 도시 신호(+569.5)다.

그런데 **무제어는 협조 신호다.** 제어 17 SC 의 실제 .sig(supplyFile2)에서:
    주기   16/17 이 150s (SC7 만 120s)
    offset 1~149s · 중앙 75 · **비영 17/17**
      SC1 131 · SC5 36 · SC6 137 · SC7 1 · SC11 95 · SC12 5 · SC16 149
      SC101 125 · SC105 35 · SC107 138 · SC108 112 · SC109 111 · SC1001~5 각 75
제어는 action JSON 의 offsets **629항목 전부 0** 이다.

주의: .inpx 의 signalController offset="0" 은 제어기 기본값이고 실제 협조는 .sig 안에 있다.
     그걸 보고 'offset 은 답이 아니다' 로 한 번 오독했다.

## 이 팔이 재는 것

제어 17 SC 의 native offset 만 0 으로 만든 망에서 **무제어**를 돌린다.
분할·주기·현시순서·monitor SC 는 전부 그대로다. 망 차이는 supplyFile2 참조 17줄뿐이고
검산으로 확인했다(제어 SC offset 비영 0개 · monitor 오염 0개).

    nc_off0 - nc_out = **협조 파괴의 순수 비용**

## 판정

  그 값이 +569.5 에 가까우면  -> 제어기 최적화는 사실상 중립이고 손실은 구조다.
                              그러면 다음은 제어기 튜닝이 아니라 offset 레버를 살리는 것이다.
  작으면(<150)               -> 협조는 부차적이고 제어기가 진짜로 나쁘다.
                              그러면 지금 도는 3팔(위상잠금·beta·정련)이 맞는 방향이다.
  |d| < 60 이면 구별 불가(무제어 5시드 sigma 50.7).

기준: nc_out_x18_20260902 = 7952.4 (제어권역 3029.6)
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
                 "RW_NARROW_AXIS_SG","RW_VALIDATION_FIXED_SIGNAL",
                 "RW_QUEUE_WINDOW","RW_QUEUE_WINDOW_STAT","RW_STATE_LOG")) {
  Remove-Item "env:$v" -ErrorAction SilentlyContinue }

for ($i = 0; $i -lt 60; $i++) {
  $alive = @(Get-Process | Where-Object { $_.ProcessName -like "*VISSIM*" }).Count
  if ($alive -eq 0) { break }
  Write-Output ("[{0}] VISSIM {1}개 대기" -f (Get-Date -Format "HH:mm:ss"), $alive)
  Start-Sleep -Seconds 20
}

$name = "nc_off0_x18_20260903"
Write-Output ("[{0}] {1} 시작 — 제어 17 SC 의 native offset 만 0. 무제어." -f (Get-Date -Format "HH:mm:ss"), $name)
& $runner -Name $name -OutDir (Join-Path $repo "evaluation/runs/$name") `
    -Adapter "evaluation/controllers/vissim_stackelberg_adapter.py" `
    -Tuning  "evaluation/configs/canon_nolencap_20260828.json" `
    -Network "network/real_world_gaepo_modi/modi_eval_userfix_20260814e_fwsweep_x18_rampbn_off0.inpx" `
    -VbsConfig "evaluation/generated/real_world_modi_control_config_distributed_core17legs4f_20260826.vbs" `
    -Calibration "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json" `
    -Mapping "evaluation/real_world_modi_control_distributed_20260728/control_mapping_distributed_core17legs4b_20260819.json" `
    -Controller "no-control" -SimPeriod 5400 -ControlIntervalSec 150 -StateLogIntervalSec 30 -Seed $Seed -StallSec 86400 -MaxAttempts 2 -ForceStepwise:$true
Write-Output ("[{0}] {1} 종료 (exit {2})" -f (Get-Date -Format "HH:mm:ss"), $name, $LASTEXITCODE)
Get-Process | Where-Object { $_.ProcessName -like "*VISSIM*" } | Stop-Process -Force -ErrorAction SilentlyContinue
