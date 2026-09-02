<#
2026-09-02. 전량 되돌림 — 반증 검정.

## 왜 이 런인가

7팔이 승격 손해 +578.2 를 **하나도 설명하지 못했다.**
  perimeter 용량 배분      -104.083
  램프별 실측 상한          +92.933
  주기/예산 재산정          +150.412
  신규 현시보정 6건         -90.854
  램프큐 상한 절단           +0.000   <- 37결정 전부 제어출력 불변(green·N_P·meter·vsl)
  비존재 beta 0화           +21.438
  off_ramp 인덱스 재구축     -35.025
  ── 합                    +34.821   설명한 것 = -34.8. 필요한 것 = -578.2.

metadata 상수를 전수 대조해도(값 다른 것 15 · 신규 26 · 소멸 7) 남는 항목은 전부
이 7개 아니면 solver 내부 결과값(wall_sec·nuf_star)이다. 즉 **조각은 다 찾았는데
합이 안 맞는다.** 남은 설명은 둘뿐이다:
  (a) 강한 비가법성 — 조각들이 곱으로 작용한다
  (b) metadata 를 안 남기는 미측정 조각이 있다 (canon 어댑터 31ff447a 는 복원 불가)

## 두 팔이 그 둘을 가른다

  R2  arm_allrev_noout   7개 전량 되돌림 + 유출 스위치 OFF
      **반증 검정이다.** 우리 손잡이 7개가 승격 델타를 다 덮으면 이 팔은
      canon_farbn 8561.1 을 재현해야 한다(같은 config·같은 시드·같은 망).
        8561 근처   -> 손잡이가 델타를 다 덮는다. 손해는 전부 (a) 비가법성이다.
        8561 과 멀다 -> 그 차이가 곧 (b) 미측정 조각의 크기다. 정확히 얼마인지 나온다.
      R2 config 가 canon_farbn 런시점 config(12af100 판)와 되돌림 키로만 다른 것을
      flat diff 로 확인했다(차이 9개 = 램프상한 4 + 신규 키 5).

  R1  arm_allrev        7개 전량 되돌림 + 유출 스위치 ON
      기준선 ctl_outflow 8822.786 과 짝지은 비교.
        가법이면            8857.6  (+34.8)
        상호작용이 전부면    8244.6  (-578.2)
      두 예측이 613 벌어져 있어 어느 쪽인지 한 번에 갈린다.

## 부수 소득 — 파이프라인은 결정론적이다

rqclip 이 뜻하지 않게 위약 팔이 됐다. 내부 예측·진단은 바뀌었는데(diagnostics·prediction
필드가 37결정 다름) 제어 출력은 green_times·N_P_star·ramp_metering·vsl·offsets 이
**37결정 전부 동일**했고, TTT 가 소수 3자리까지 같았다(8822.786).
=> VISSIM+러너는 같은 액션에 같은 결과를 낸다. **팔 간 차이는 잡음이 아니라 실재한다.**
그리고 far 램프항의 q^2 재가중은 후보 판별력이 0 이다.

## 판정 후 할 일
  R2 가 8561 근처면  -> 조각 사냥을 그만두고 조합 효과를 본다(어느 쌍이 곱하는가).
  R2 가 멀면        -> 그 크기만큼의 미측정 조각을 찾는다. 다음 후보는
                       agent_topology.metering_in_gne(코드변경 0, config 키 하나).
#>
param([int]$Seed = 13)

$ErrorActionPreference = "Continue"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runner = Join-Path $repo "scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1"

$env:RW_MAINLINE_SG_ONLY = "1"
$env:RW_PYTHON_EXE = "C:/Users/TRLAB/AppData/Local/Programs/Python/Python312/python.exe"
foreach ($v in @("RW_OFFSET_WRITER","RW_MOVING_SPEED","RW_LANE_DELAY_CORRECTION","RW_NP_STATE_BAND",
                 "RW_STOPPED_SPLIT","RW_MAINLINE_PLAN","RW_MAINLINE_SHARE_SG","RW_ADAPTER_MODE",
                 "RW_QUEUE_ORIGIN_BINDING","RW_TAU_LENGTH_CAP","RW_DEAD_PHASE_BETA_ZERO",
                 "RW_BOUNDARY_INFLOW_SEED","RW_FORCE_STEPWISE","RW_MOVEMENT_PHASE_CORRECTION",
                 "RW_NARROW_AXIS_SG","RW_VALIDATION_FIXED_SIGNAL")) {
  Remove-Item "env:$v" -ErrorAction SilentlyContinue
}

$vbsCfg = Join-Path $repo "evaluation/generated/real_world_modi_control_config_distributed_core17legs4f_20260826.vbs"
$sgplan = $vbsCfg -replace "[.]vbs$", "_sgplan.vbs"
foreach ($f in @($vbsCfg, $sgplan)) {
  if (-not (Test-Path $f)) { Write-Output "!! 없음: $f"; exit 1 }
}

$arms = @(
  @{ name = "arm_allrev_noout_x18_20260902"; tuning = "evaluation/configs/arm_allrev_noout_d00_x18_20260902.json"; network = "network/real_world_gaepo_modi/modi_eval_userfix_20260814e_fwsweep_x18_rampbn.inpx"; controller = "wu-link"; note = "반증검정 R2 — 7개 전량 되돌림 + 유출 OFF. canon_farbn 8561.1 을 재현해야 한다" },
  @{ name = "arm_allrev_x18_20260902"; tuning = "evaluation/configs/arm_allrev_d00_x18_20260902.json"; network = "network/real_world_gaepo_modi/modi_eval_userfix_20260814e_fwsweep_x18_rampbn.inpx"; controller = "wu-link"; note = "R1 — 7개 전량 되돌림 + 유출 ON. 가법이면 8857.6" }
)
foreach ($arm in $arms) {
  $name = $arm.name
  $tuningAbs = Join-Path $repo $arm.tuning
    $ctrl = if ($arm.ContainsKey("controller")) { $arm.controller } else { "wu-link" }
    # 배열 splat 금지. PowerShell 은 `if` 출력의 1원소 배열을 String 으로 언롤하고,
    # 문자열 splat 은 그걸 **문자 단위 위치인자**로 쪼갠다 (2026-09-01 nc_rampbn_x18 사고:
    # "-ForceStepwise" -> 14개 인자, DemandScale=111 · 게이트맵=i · ForceStepwise 는 끝내 False).
    # 빈 배열 @() 도 $null 로 언롤돼 팬텀 위치인자 1개가 ControlStartSec 에 꽂힌다.
    # switch 는 -Name:$bool 로 넘긴다.
    $stepwise = ($ctrl -eq "no-control")
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

  $outDir = Join-Path $repo "evaluation/runs/$name"
  Write-Output ("[{0}] {1} 시작 — {2}" -f (Get-Date -Format "HH:mm:ss"), $name, $arm.note)
  & $runner -Name $name -OutDir $outDir `
      -Adapter "evaluation/controllers/vissim_stackelberg_adapter.py" `
      -Tuning  $arm.tuning `
      -Network $arm.network `
      -VbsConfig "evaluation/generated/real_world_modi_control_config_distributed_core17legs4f_20260826.vbs" `
      -Calibration "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json" `
      -Mapping "evaluation/real_world_modi_control_distributed_20260728/control_mapping_distributed_core17legs4b_20260819.json" `
      -Controller $ctrl -SimPeriod 5400 -ControlIntervalSec 150 -StateLogIntervalSec 30 -Seed $Seed -StallSec 86400 -MaxAttempts 2 -ForceStepwise:$stepwise
  Write-Output ("[{0}] {1} 종료 (exit {2})" -f (Get-Date -Format "HH:mm:ss"), $name, $LASTEXITCODE)

  Get-Process | Where-Object { $_.ProcessName -like "*VISSIM*" } | Stop-Process -Force -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 5
}
Write-Output "=========================================================="
Write-Output ("[{0}] 큐 종료" -f (Get-Date -Format "HH:mm:ss"))
