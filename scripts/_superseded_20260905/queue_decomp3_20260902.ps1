<#
2026-09-02. 승격 묶음 분해 3팔.

왜. A/B 가 두 가지를 동시에 말했다 (시드 13 · rampbn 망 · 무제어 7952.4):
  ctl_base     9139.3  +14.92%   승격 묶음 O · 유출 스위치 X
  ctl_outflow  8822.8  +10.94%   승격 묶음 O · 유출 스위치 O
  canon_farbn  8561.1   +7.65%   승격 묶음 X · 유출 스위치 X
-> 유출 스위치는 -316.5 (-3.46%) 로 **효과가 있다**.
-> 승격 묶음은 +578.2 (+6.75%) 로 **해가 된다**. 그 안에 뭐가 범인인지 모른다.

기준선은 ctl_outflow (8822.8) 다. 각 팔은 승격 조각 **하나만** 되돌린다.
TTT 가 8822.8 보다 내려가면 그 조각이 범인이다.

  A  arm_perimoff   perimeter movement 184개 용량
     승격: 차로수 배분 (중앙 206.5 · 범위 207~826)
     되돌림: vendor 전역 스칼라 1400
     의심 이유 — 206.5 는 internal 실측 중앙에서 왔지 **경계 실측이 아니다**.
     경계 이탈을 6.8배 조인 셈이라 유출이 과소평가됐을 수 있다.

  B  arm_cap180     램프 큐 상한
     승격: 램프별 실측 111.2/153.2/153.6/174.5
     되돌림: vendor 격자 스칼라 180
     의심 이유 — 무제어 램프큐 최대 32~70 인데 제어에서 267/248 이다.
     상한이 물리적으로 맞더라도, 걸리는 순간 도시 게이트가 닫혀 접근로가 역류한다.
     **상한을 올리자는 게 아니다** — 이 팔은 그 초과가 벌점의 원인인지만 잰다.

  C  arm_natcyc     주기/예산 재산정
     승격: 구동주기 150 기준 (SC7 150/141 · SC16 150/141)
     되돌림: 실측 native 프로그램 (SC7 120/114)
     의심 이유 — 재산정이 SC7·SC16 두 신호의 예산을 각각 +27·+34 늘린다.
     녹색을 더 주는 게 맞는 방향이라 보였는데, 배분기가 그 여유를 어디에 쓰는지는
     검증한 적이 없다.

스위치는 셋 다 config 키다(승격 원칙 유지 — 어댑터에 분기를 남기지 않는다):
  A  urban.capacity.perimeter 키 제거
  B  config_overrides.network.ramp_queue_max_veh_by_ramp 를 180 으로
  C  urban.native_signal.drive_cycle_recompute = 0

설치 결과를 발사 전에 확인했다 — 각 팔이 정확히 한 가지만 바꾼다:
  팔            perimeter                 램프상한  SC7 주기/예산
  ctl_outflow   n=184 중앙 206.5           153.2    150/141
  A perimoff    n=184 중앙 1400.0          153.2    150/141
  B cap180      n=184 중앙 206.5           180.0    150/141
  C natcyc      n=184 중앙 206.5           153.2    120/114

주의. 무제어 시드 분산 sigma 50.7 (1.06%) 이다. 여기 차이는 +578 규모라 그 위지만,
개별 팔이 100 미만으로 움직이면 '구별 안 된다' 까지만 말할 수 있다.
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
  @{ name = "arm_perimoff_x18_20260902"; tuning = "evaluation/configs/arm_perimoff_d00_x18_20260902.json"; network = "network/real_world_gaepo_modi/modi_eval_userfix_20260814e_fwsweep_x18_rampbn.inpx"; controller = "wu-link"; note = "분해 A — perimeter 용량만 되돌림(184개가 스칼라 1400 로)" },
  @{ name = "arm_cap180_x18_20260902"; tuning = "evaluation/configs/arm_cap180_d00_x18_20260902.json"; network = "network/real_world_gaepo_modi/modi_eval_userfix_20260814e_fwsweep_x18_rampbn.inpx"; controller = "wu-link"; note = "분해 B — 램프 상한만 vendor 격자 180 으로 되돌림" },
  @{ name = "arm_natcyc_x18_20260902"; tuning = "evaluation/configs/arm_natcyc_d00_x18_20260902.json"; network = "network/real_world_gaepo_modi/modi_eval_userfix_20260814e_fwsweep_x18_rampbn.inpx"; controller = "wu-link"; note = "분해 C — 주기/예산 재산정만 끔(SC7 150/141 -> 120/114)" }
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
