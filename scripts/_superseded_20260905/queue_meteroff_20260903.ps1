<#
2026-09-03. 미터링 OFF 대조군 — arm_meteroff.

## 왜

램프 미터링의 순효과가 -42.3 veh.h 로 사실상 무승부인데, 그 안에 두 덩어리가 섞여 있다.

    고속 본선 이득            -496.1 veh.h   (직접 검산, 기존 권역분해 -494.8 과 0.3% 일치)
    램프 커넥터 8개            +220.5
    램프 상류 31/32/68/69/70   +233.2
    ------------------------------------
    램프 미터링 순효과          -42.3

그런데 같은 팔이 도시 신호 17개와 VSL 을 동시에 바꾼다. -496.1 중 얼마가 진짜
미터링 것인지 확인된 바 없다. 그리고 적자 +386.5 의 주범인 링크 420(+278.4)은
t~900s 에 막히는데 미터 클램프는 1800s 다 — 900초 먼저다. 420 통과차량의 74%가
램프를 아예 안 가고 R_D_W 이용자 중 420 경유는 1.8% 다. 신호 손상으로 보이지만
통제된 검증이 아니다.

이 한 런이 둘을 동시에 판정한다.

## 이 팔이 재는 것

도시 신호 17개와 VSL 은 **그대로 ON**. 램프만 물리적으로 못 조이게 두 겹으로 건다.

  (1) leader.N_UF_star_range = [7200, 7200]
      리더가 언제나 램프 물리용량 전체(1800 x 4)를 요청한다. 실런 진단에서
      leader_nuf_bound_upper 가 37결정 전부 7200.0 이라 상한과 충돌하지 않는다.
      종전 하한은 1440(용량의 20%)이고 25결정 중 14개가 정확히 거기 붙어 있었다.

  (2) actuation.real_world_ramp_metering.min_green_sec  2.0 -> 10.0 (= cycle)
      0 이 아닌 어떤 명령도 green_sec 10 = 900 vph 로 올린다.

잔여 탈출구는 adapter:7646 의 `if per_meter_rate <= 1.0e-9` 분기다. 그 분기는
**설정된 하한(min_green_sec=2.0 = 180 vph)을 명시적으로 우회**하며, 기준선 런에서
미터 명령 296건 중 84건(28%)이 그 경로로 green_sec 0 = readback RED 로 나갔다.
R_D_W 는 24구간 연속 폐쇄 = 3,600초로, 실측 만재한계 591초(저장 144대 / 도착 877 vph)의
6.1배다. 리더를 용량에 고정하면 개별 램프에 정확히 0 이 배분될 여지가 없어야 한다.
**사후에 action CSV 의 ramp_meter 296행이 전부 rate 900 / green 10 / GREEN 인지
검산한다.** 아니면 그 사실을 보고한다.

## 판정

기준선 (전부 시드 13 · x18_rampbn · 5400s):

    nc_out_x18_20260902      7952.4   무제어
    qcread_x18_20260903      8339.0   제어 (같은 tuning canon_outflow_d00)
    arm_rampclean_...        8339.0   비트 동일

  고속 본선 재차적분(is_freeway=1, 창 1800~5400) 무제어 대비:
    <= -370 유지  -> 이득의 75% 이상이 미터링과 무관 -> 미터링은 이 망에서 포기
    >= -150 이하  -> 미터링이 이득을 소유 -> 하한 + D3(ALINEA 사문) + D5(beta 비대칭) 수정 런으로

  링크 420 (제어 - 무제어):
    >= +250  -> 420/30 (+503.5, 도시 페널티의 85.8%) 은 신호 손상 확정

  TTT: |d| < 60 은 구별 불가 (무제어 5시드 sigma 50.7)

## 손대지 않은 것

leader.w_ramp_queue = 0.0 그대로. far 의 램프 항 q^2/(2*merge_rate) 가 그 역할이고
둘 다 켜면 이중계상이다(사용자 확인 2026-09-03, config 주석에도 명문화되어 있다).
코드는 한 줄도 고치지 않는다 — 어댑터는 결정마다 재기동되므로 런 중 편집은 금지다.
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
                 "RW_VALIDATION_FIXED_SIGNAL")) { Remove-Item "env:$v" -ErrorAction SilentlyContinue }

for ($i=0; $i -lt 60; $i++) {
  $alive = @(Get-Process | Where-Object { $_.ProcessName -like "*VISSIM*" }).Count
  if ($alive -eq 0) { break }
  Write-Output ("[{0}] VISSIM {1}개 대기" -f (Get-Date -Format "HH:mm:ss"), $alive)
  Start-Sleep -Seconds 20
}

$name = "arm_meteroff_x18_20260903"
Write-Output ("[{0}] {1} 시작 — 램프 미터링 OFF. 도시 신호·VSL 은 그대로. 기준선 8339.0" -f (Get-Date -Format "HH:mm:ss"), $name)
& (Join-Path $repo "scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1") `
    -Name $name -OutDir (Join-Path $repo "evaluation/runs/$name") `
    -Adapter "evaluation/controllers/vissim_stackelberg_adapter.py" `
    -Tuning  "evaluation/configs/arm_meteroff_d00_x18_20260903.json" `
    -Network "network/real_world_gaepo_modi/modi_eval_userfix_20260814e_fwsweep_x18_rampbn_qc.inpx" `
    -VbsConfig "evaluation/generated/real_world_modi_control_config_distributed_core17legs4f_20260826.vbs" `
    -Calibration "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json" `
    -Mapping "evaluation/real_world_modi_control_distributed_20260728/control_mapping_distributed_core17legs4b_20260819.json" `
    -Controller "wu-link" -SimPeriod 5400 -ControlIntervalSec 150 -StateLogIntervalSec 30 -Seed $Seed -StallSec 86400 -MaxAttempts 2
Write-Output ("[{0}] {1} 종료 (exit {2})" -f (Get-Date -Format "HH:mm:ss"), $name, $LASTEXITCODE)
Get-Process | Where-Object { $_.ProcessName -like "*VISSIM*" } | Stop-Process -Force -ErrorAction SilentlyContinue
