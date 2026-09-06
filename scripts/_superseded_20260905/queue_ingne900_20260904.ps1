<#
2026-09-04. ctl_start900 + in_gne + lnChgDist 1000 복귀 (사용자 지시, 세 변경 묶음).

## 기준선

이 팔의 망은 lnChgDist **1000** + 증량수요다. 따라서 짝 무제어는

    nc_rampmax_x18_20260903 = 8082.3     <- 이 망의 무제어 (lcd1000 + 증량)
    nc_out_x18_20260902     = 7952.4     (lcd200 + 증량)
    ctl_canon_x18_20260904  = 7946.2     (lcd200 + 증량, 제어)  <- 망이 달라 참고만
    sigma 50.7

판정: TTT < 8082.3 이면 이 망에서 제어가 무제어를 이긴 것.

## 세 변경

  (1) -ControlStartSec 900   워밍업 무제어. t=1 빈 망 꼭짓점 락인 제거
  (2) phase_price.in_gne     GNE 를 현시 벡터 좌표하강으로. 신호당 자유도 1 -> 현시 수
  (3) 망 lnChgDist 1000 복귀  링크 2 pos 3400~3800 에서 107 -> 73~91 kph 열화 되돌림

세 개를 묶었으므로 개별 귀속은 안 된다(사용자 결정). 실패 시 (2)부터 빼고 재시도.

## 읽을 것

  wu_phase_refine_rounds_used            첫값 87 -> 하락해야 한다
  wu_phase_price_moved_sec_*             첫값 72.3 -> 이후 수준으로
  phase_vector_green_enabled             1.0 여야 한다 (아니면 (2)가 발화 안 한 것)
  녹색/큐 Spearman                        0.146 -> 상승
  max-pressure 일치율                     25.8% (우연 27.5%) -> 상승
  urban_queue_source_constant             0 유지
  VSL 분포 / 램프 readback RED             lcd1000 에서 레버가 다르게 움직이나
#>

param([int]$Seed = 13)
$ErrorActionPreference = "Continue"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$env:RW_PYTHON_EXE = "C:/Users/TRLAB/AppData/Local/Programs/Python/Python312/python.exe"
$env:RW_MAINLINE_SG_ONLY = "1"
$env:RW_QUEUE_COUNTER = "1"
foreach ($v in @("RW_QUEUE_WINDOW","RW_QUEUE_WINDOW_STAT","RW_STATE_LOG","RW_FORCE_STEPWISE",
                 "RW_OFFSET_WRITER","RW_MOVING_SPEED","RW_LANE_DELAY_CORRECTION","RW_NP_STATE_BAND",
                 "RW_STOPPED_SPLIT","RW_MAINLINE_PLAN","RW_MAINLINE_SHARE_SG","RW_ADAPTER_MODE",
                 "RW_QUEUE_ORIGIN_BINDING","RW_TAU_LENGTH_CAP","RW_DEAD_PHASE_BETA_ZERO",
                 "RW_BOUNDARY_INFLOW_SEED","RW_MOVEMENT_PHASE_CORRECTION","RW_NARROW_AXIS_SG",
                 "RW_VALIDATION_FIXED_SIGNAL","RW_ARRIVAL_SEED","RW_QUEUE_CONTIGUOUS",
                 "RW_STORAGE_LANES_FZP","RW_RESTORE_RELEASE_BUFFERS","RW_WARMSTART_SEC",
                 "RW_QUEUE_BINS")) {
  Remove-Item "env:$v" -ErrorAction SilentlyContinue }

for ($i=0; $i -lt 240; $i++) {
  $alive = @(Get-Process | Where-Object { $_.ProcessName -like "*VISSIM*" }).Count
  if ($alive -eq 0) { break }
  if ($i % 10 -eq 0) { Write-Output ("[{0}] 앞 런 대기 중 (VISSIM {1}개)" -f (Get-Date -Format "HH:mm:ss"), $alive) }
  Start-Sleep -Seconds 30
}

$name = "arm_ingne900_lcd1000_x18_20260904"
Write-Output ("[{0}] {1} 시작" -f (Get-Date -Format "HH:mm:ss"), $name)
& (Join-Path $repo "scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1") `
    -Name $name -OutDir (Join-Path $repo "evaluation/runs/$name") `
    -Adapter "evaluation/controllers/vissim_stackelberg_adapter.py" `
    -Tuning  "evaluation/configs/arm_ingne900_lcd1000_20260904.json" `
    -Network "network/real_world_gaepo_modi/modi_eval_userfix_20260814e_fwsweep_x18_rampbn_qc_lcd1000.inpx" `
    -VbsConfig "evaluation/generated/real_world_modi_control_config_distributed_core17legs4f_20260826.vbs" `
    -Calibration "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json" `
    -Mapping "evaluation/real_world_modi_control_distributed_20260728/control_mapping_distributed_core17legs4b_20260819.json" `
    -Controller "wu-link" -ControlStartSec 900 -WarmupController "no-control" `
    -SimPeriod 5400 -ControlIntervalSec 150 -StateLogIntervalSec 30 -Seed $Seed -StallSec 86400 -MaxAttempts 2
Write-Output ("[{0}] {1} 종료 (exit {2})" -f (Get-Date -Format "HH:mm:ss"), $name, $LASTEXITCODE)
Get-Process | Where-Object { $_.ProcessName -like "*VISSIM*" } | Stop-Process -Force -ErrorAction SilentlyContinue
