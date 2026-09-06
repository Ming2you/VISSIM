<#
2026-09-04. 새 기본으로 재기준선 — nc_canon / ctl_canon.

## 왜 재기준선이 필요한가

옛 기준선(무제어 7952.4 / 제어 8339.0)은 **삭제 전 코드**의 값이다. 그 뒤로 바뀐 것:

  삭제  beta_hat 가드 보정 · beta 추정기 · trailing-regret · 리더 되먹임 carry · 팔로워 far
        (벤더 테스트 HEAD 대조 회귀 0: 양쪽 34 failed / 442 passed / 1873 subtests, 실패집합 동일)
  승격  0 link_to_origins +9 · 1 정지선 연속 walk + head window 30m ·
        2 arrival buffer 시더(이봉 tau 15/105s) · 3 warm_start 자동 억제 ·
        4 저류 차로보정 149->204

arm_qsplit_x18_20260904 = 7946.2 는 그중 head window **없이** 낸 값이라 이것도 기준선이 아니다.
이 두 런이 이후 모든 비교의 기준이 된다.

## 두 팔

  nc_canon    무제어. 도시신호 COM 0종 = 진짜 네이티브. -ForceStepwise 는 러너 인자여야 한다
              (env 는 덮인다).
  ctl_canon   제어. canon_default_20260904 그대로.

같은 시드 13 · 같은 망 x18_rampbn_qc · 5400s. 짝지은 비교만 유효(무제어 5시드 sigma 50.7 은
수준의 분산이지 짝지은 차이의 분산이 아니다).

## 읽을 것

  TTT                                   ctl - nc 가 이번 세션의 진짜 성적표
  urban_queue_source_contiguous/stopped/constant   constant = 0 이어야 한다
  urban_queue_contiguous_veh            head window 적용 후 값
  unrepresented_vehicle_count_veh       0 유지
  램프 미터 readback RED 비율            기준선 84/296 -> arm_qsplit 14/296
#>

param([int]$Seed = 13)
$ErrorActionPreference = "Continue"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runner = Join-Path $repo "scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1"
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

$net  = "network/real_world_gaepo_modi/modi_eval_userfix_20260814e_fwsweep_x18_rampbn_qc.inpx"
$tun  = "evaluation/configs/canon_default_20260904.json"
$vbs  = "evaluation/generated/real_world_modi_control_config_distributed_core17legs4f_20260826.vbs"
$cal  = "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json"
$map  = "evaluation/real_world_modi_control_distributed_20260728/control_mapping_distributed_core17legs4b_20260819.json"
$adp  = "evaluation/controllers/vissim_stackelberg_adapter.py"

function Wait-Vissim {
  for ($i=0; $i -lt 60; $i++) {
    $alive = @(Get-Process | Where-Object { $_.ProcessName -like "*VISSIM*" }).Count
    if ($alive -eq 0) { return }
    Write-Output ("[{0}] VISSIM {1}개 대기" -f (Get-Date -Format "HH:mm:ss"), $alive)
    Start-Sleep -Seconds 20
  }
}

Wait-Vissim
$name = "nc_canon_x18_20260904"
Write-Output ("[{0}] {1} 시작 - 무제어 재기준선" -f (Get-Date -Format "HH:mm:ss"), $name)
& $runner -Name $name -OutDir (Join-Path $repo "evaluation/runs/$name") `
    -Adapter $adp -Tuning $tun -Network $net -VbsConfig $vbs -Calibration $cal -Mapping $map `
    -Controller "no-control" -SimPeriod 5400 -ControlIntervalSec 150 -StateLogIntervalSec 30 `
    -Seed $Seed -StallSec 86400 -MaxAttempts 2 -ForceStepwise:$true
Write-Output ("[{0}] {1} 종료 (exit {2})" -f (Get-Date -Format "HH:mm:ss"), $name, $LASTEXITCODE)
Get-Process | Where-Object { $_.ProcessName -like "*VISSIM*" } | Stop-Process -Force -ErrorAction SilentlyContinue

Wait-Vissim
$name = "ctl_canon_x18_20260904"
Write-Output ("[{0}] {1} 시작 - 제어 재기준선 (canon_default_20260904)" -f (Get-Date -Format "HH:mm:ss"), $name)
& $runner -Name $name -OutDir (Join-Path $repo "evaluation/runs/$name") `
    -Adapter $adp -Tuning $tun -Network $net -VbsConfig $vbs -Calibration $cal -Mapping $map `
    -Controller "wu-link" -SimPeriod 5400 -ControlIntervalSec 150 -StateLogIntervalSec 30 `
    -Seed $Seed -StallSec 86400 -MaxAttempts 2
Write-Output ("[{0}] {1} 종료 (exit {2})" -f (Get-Date -Format "HH:mm:ss"), $name, $LASTEXITCODE)
Get-Process | Where-Object { $_.ProcessName -like "*VISSIM*" } | Stop-Process -Force -ErrorAction SilentlyContinue
Write-Output ("[{0}] 재기준선 2팔 완료" -f (Get-Date -Format "HH:mm:ss"))
