<#
2026-09-04. 새 정본 제어 재기준선 — ctl_canon.

## 무제어는 다시 재지 않는다

무제어에서 어댑터는 37번 돌지만 출력이 VISSIM 에 가지 않는다(도시신호 COM 0종 = 진짜 네이티브).
이번에 바꾼 것 중 VISSIM 에 쓰는 것은 없다 — VBS 변경은 읽기 누적 + JSON 키 하나뿐이고,
beta_hat/regret/팔로워 far 는 무제어에서 애초에 안 탄다(리더가 안 돈다).
그래서 **nc_out_x18_20260902 = 7952.4 가 그대로 유효한 기준선**이다.

망 차이(_rampbn 대 _rampbn_qc)도 근거가 안 된다 — 읽기 전용 큐카운터 8개뿐이고,
qcread(_qc)가 arm_rampclean(_rampbn)의 8339.0 을 소수점까지 재현해 이미 증명됐다.

## 이 런이 재는 것

canon_default_20260904 그대로. head window 30 m 가 들어간 뒤의 값이다
(arm_qsplit 7946.2 는 head window **없이** 낸 값이라 기준선이 아니다).

  무제어 nc_out          7952.4
  제어 옛 기준선 qcread   8339.0   (삭제 전 코드)
  arm_qsplit            7946.2   (head window 없음)
  sigma                   50.7

## 읽을 것

  TTT                                    ctl - 7952.4 가 이번 세션의 성적표
  urban_queue_source_constant            0 이어야 한다
  urban_queue_contiguous_veh             head window 적용 후 값 (적용 전 walk/정지 0.820 -> 0.717)
  unrepresented_vehicle_count_veh        0 유지
  램프 미터 readback RED                  옛 84/296 -> arm_qsplit 14/296
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

for ($i=0; $i -lt 60; $i++) {
  $alive = @(Get-Process | Where-Object { $_.ProcessName -like "*VISSIM*" }).Count
  if ($alive -eq 0) { break }
  Write-Output ("[{0}] VISSIM {1}개 대기" -f (Get-Date -Format "HH:mm:ss"), $alive)
  Start-Sleep -Seconds 20
}

$name = "ctl_canon_x18_20260904"
Write-Output ("[{0}] {1} 시작 - 제어 재기준선 (canon_default_20260904, head window 포함)" -f (Get-Date -Format "HH:mm:ss"), $name)
& (Join-Path $repo "scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1") `
    -Name $name -OutDir (Join-Path $repo "evaluation/runs/$name") `
    -Adapter "evaluation/controllers/vissim_stackelberg_adapter.py" `
    -Tuning  "evaluation/configs/canon_default_20260904.json" `
    -Network "network/real_world_gaepo_modi/modi_eval_userfix_20260814e_fwsweep_x18_rampbn_qc.inpx" `
    -VbsConfig "evaluation/generated/real_world_modi_control_config_distributed_core17legs4f_20260826.vbs" `
    -Calibration "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json" `
    -Mapping "evaluation/real_world_modi_control_distributed_20260728/control_mapping_distributed_core17legs4b_20260819.json" `
    -Controller "wu-link" -SimPeriod 5400 -ControlIntervalSec 150 -StateLogIntervalSec 30 -Seed $Seed -StallSec 86400 -MaxAttempts 2
Write-Output ("[{0}] {1} 종료 (exit {2})" -f (Get-Date -Format "HH:mm:ss"), $name, $LASTEXITCODE)
Get-Process | Where-Object { $_.ProcessName -like "*VISSIM*" } | Stop-Process -Force -ErrorAction SilentlyContinue
