<#
2026-09-04. 도시 큐/접근 분리 재배선 0~4단계 묶음 — arm_qsplit.

## 기준선

  nc_out_x18_20260902    7952.4   무제어
  qcread_x18_20260903    8339.0   제어 (같은 tuning canon_outflow_d00 · 같은 망 x18_rampbn_qc · 시드 13)
  시드 sigma             50.7 veh.h

## 이 팔이 바꾸는 것

  0  link_to_origins +9        소실 161.32 -> 0.00 veh/결정
  1  urban.queue.contiguous    정지선 차로별 연속 walk (RW_QUEUE_BINS=1 필요)
  2  urban.arrival.seed_...    잔차를 도착 버퍼에 이봉 tau(15s/105s)로 예약
  3  warm_start 자동 억제      시더와 이중 예약 방지 (어댑터가 알아서 함)
  4  urban.tau.storage_lanes   저류 차로수 결손 75개 보충 (.fzp 유도)

1과 2는 반드시 함께 간다 — 현행 두 오차의 부호가 반대라 폐루프에서 부분 상쇄 중이다.

## 게이트 0 (VISSIM 없이 이미 통과)

  시더 OFF   movement_queue  s1..s90 전부 0.00
  시더 ON                    s6=565.89  s16=264.88  s31=628.94  s61=350.58  s90=315.12
  예약 1817 veh / 167 항목

## 판정

  TTT < 8237.6 (= 8339.0 - 2sigma)   실재 개선. 진짜 목표는 < 7952.4
  TTT > 8440.4                       되돌린다
  urban_arrival_buffer               > 1000 veh (현재 0.00)
  urban_queue_source_level_hist      constant 층 = 0 링크
  unrepresented                      < 5 veh/결정 (현재 161.32)

## 주의

러너 VBS 를 이번에 고쳤다(히스토그램 추가). 첫 결정에서 queue_bins 가 실제로 실리는지
먼저 확인해라 — 안 실리면 1단계가 조용히 stopped 층으로 폴백해 2단계만 잰 것이 된다.
#>

param([int]$Seed = 13)
$ErrorActionPreference = "Continue"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$env:RW_PYTHON_EXE = "C:/Users/TRLAB/AppData/Local/Programs/Python/Python312/python.exe"
$env:RW_MAINLINE_SG_ONLY = "1"
$env:RW_QUEUE_COUNTER = "1"
$env:RW_QUEUE_BINS = "1"
foreach ($v in @("RW_QUEUE_WINDOW","RW_QUEUE_WINDOW_STAT","RW_STATE_LOG","RW_FORCE_STEPWISE",
                 "RW_OFFSET_WRITER","RW_MOVING_SPEED","RW_LANE_DELAY_CORRECTION","RW_NP_STATE_BAND",
                 "RW_STOPPED_SPLIT","RW_MAINLINE_PLAN","RW_MAINLINE_SHARE_SG","RW_ADAPTER_MODE",
                 "RW_QUEUE_ORIGIN_BINDING","RW_TAU_LENGTH_CAP","RW_DEAD_PHASE_BETA_ZERO",
                 "RW_BOUNDARY_INFLOW_SEED","RW_MOVEMENT_PHASE_CORRECTION","RW_NARROW_AXIS_SG",
                 "RW_VALIDATION_FIXED_SIGNAL","RW_ARRIVAL_SEED","RW_QUEUE_CONTIGUOUS",
                 "RW_STORAGE_LANES_FZP","RW_RESTORE_RELEASE_BUFFERS","RW_WARMSTART_SEC")) {
  Remove-Item "env:$v" -ErrorAction SilentlyContinue }

for ($i=0; $i -lt 60; $i++) {
  $alive = @(Get-Process | Where-Object { $_.ProcessName -like "*VISSIM*" }).Count
  if ($alive -eq 0) { break }
  Write-Output ("[{0}] VISSIM {1}개 대기" -f (Get-Date -Format "HH:mm:ss"), $alive)
  Start-Sleep -Seconds 20
}

$name = "arm_qsplit_x18_20260904"
Write-Output ("[{0}] {1} 시작 - 큐/접근 분리 0~4단계. 기준선 8339.0" -f (Get-Date -Format "HH:mm:ss"), $name)
& (Join-Path $repo "scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1") `
    -Name $name -OutDir (Join-Path $repo "evaluation/runs/$name") `
    -Adapter "evaluation/controllers/vissim_stackelberg_adapter.py" `
    -Tuning  "evaluation/configs/arm_qsplit_d00_x18_20260904.json" `
    -Network "network/real_world_gaepo_modi/modi_eval_userfix_20260814e_fwsweep_x18_rampbn_qc.inpx" `
    -VbsConfig "evaluation/generated/real_world_modi_control_config_distributed_core17legs4f_20260826.vbs" `
    -Calibration "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json" `
    -Mapping "evaluation/real_world_modi_control_distributed_20260728/control_mapping_distributed_core17legs4b_20260819.json" `
    -Controller "wu-link" -SimPeriod 5400 -ControlIntervalSec 150 -StateLogIntervalSec 30 -Seed $Seed -StallSec 86400 -MaxAttempts 2
Write-Output ("[{0}] {1} 종료 (exit {2})" -f (Get-Date -Format "HH:mm:ss"), $name, $LASTEXITCODE)
Get-Process | Where-Object { $_.ProcessName -like "*VISSIM*" } | Stop-Process -Force -ErrorAction SilentlyContinue
