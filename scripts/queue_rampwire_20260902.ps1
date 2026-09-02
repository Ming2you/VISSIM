<#
2026-09-02. 램프 배선 복원 — 2팔.

## 무엇을 고치나

결함: 롤아웃에서 램프 저수지에 유입 경로가 하나도 없다. w_r 은 순수 sink 다.
  urban_queue_model.py:1134 `if arrival <= 0.0 or not movements: continue` 가
  on_ramp_to_movement 공집합에서 걸리고, metanet.py:391 경로는 coupling.py:214
  update_ramp_queues=False 로 죽어 있다. 37결정 5,393.5 veh 가 조용히 소멸.
  검정: demand.ramp_arrival 을 0 으로 두든 3976 vph 로 채우든 궤적이 비트 동일.

## 고치는 방법 — 사용자가 2026-08-17 에 이미 만든 수정

commit 2eb0287 `scripts/derive_ramp_coupling_movements.py`. 그런데 그 스크립트는
현행 config 에서 깨진다(KeyError 'W') — 당시엔 램프 leg 자체가 없어 새 leg 를 심었는데
지금은 W_RAMP 가 이미 있어 충돌한다. 현행에서는 **on 만 채우면 된다**:
  SC1001.W_RAMP.on = {W: R_D_W, E: R_D_E}
  SC1004.W_RAMP.on = {W: R_F_W, E: R_F_E}
(60개 config 전부에서 on 이 한 번도 채워진 적이 없다 — '껐다' 가 아니라 '켠 적 없다'.)

재현 검증(8/17 것이 지금도 성립): 생산 474 = 재현 474 이름 단위 완전 일치.
on 채우면 +18(on_ramp 12 · boundary_in 6) · 제거 0 · 변경 17(전부 SC1001/SC1004 안).
config 에 urban_movements 가 명시돼 있어 grid_node_legs 만 고치면 안 읽힌다 — movement 를 주입해야 한다.

## 두 팔

  A arm_rampwire   movement 주입만. 관측 매핑 현행 유지.
     8/17 에 '예측이 안 좋아졌다' 로 기각된 그 조건이다. **폐루프 TTT 는 그때도 지금도 미측정.**
     오프라인 램프 예측오차 27.5 -> 34.6 veh (악화). 왜 악화하는지는 B 가 답한다.

  B arm_rampconn   A + 램프 큐 관측을 미터 커넥터 8개로 축소
     ramp_link_to_queues 12개 중 4개(31·68·78·10703)가 도시 피더 링크인데 100% 램프로 센다.
     어제 만든 boundary_out_ramp_split 은 같은 링크 31 을 free 0.25/R_D_E 0.25/R_D_W 0.50 으로
     쪼갠다 — 두 표가 모순이다.
       전체 링크: R_D_W 중앙 183.3 상한초과 22/37 · R_F_E 중앙 129.5 초과 12/37
       커넥터만 : R_D_W 중앙 138.0 초과 0/37 · R_F_E 중앙 87.0 초과 0/37
     상한(111~175)이 틀린 게 아니라 관측이 과대였다.
     오프라인 램프 예측오차 **27.5 -> 9.6 veh (65% 감소)**, 편향 9% -> 27%(무편향 50%).

## 오프라인 실측 (37결정 1스텝 예측−관측, veh)

  팔                R_D_E     R_D_W     R_F_E     R_F_W   전체|중앙|  과대%
  현행              -30/30     -6/9     -15/18    -54/54     27.5      9%
  A 주입만          -25/25    -40/40    -28/28    -41/41     34.6      6%
  B 주입+커넥터만     -9/9     +9/10      -0/7     -26/26      9.6     27%
  (표기: 중앙편차/|중앙|오차)

  유입 복구 확인: onramp_arrivals_veh 0.00 -> 165.67 (= 관측 도착 3976 vph x 150s/3600)

## 결정적 예측

  기준선 ctl_outflow_x18_20260902 = 8822.786 (시드 13, 같은 망)
  B 가 범인 하나를 제대로 고친 것이면 TTT 가 내려가야 한다. 안 내려가면 —
  '램프 예측이 3배 정확해져도 폐루프가 안 움직인다' 가 결론이고, 그건 far 램프항의
  후보 판별력이 0 이라는 기존 측정(rqclip 팔: 후보 폭 변화 0.000)과 정합한다.
  A 가 B 보다 나쁘면 오프라인 순서가 폐루프에서도 성립한다는 뜻이다.

## 알려진 한계

  B 는 제거된 4링크가 link_to_movements·link_to_origins 에도 없어 도시 저류로도 안 간다 —
  모델 관측에서 83~295 veh 가 빠진다. 그 차량이 '안 보이게' 되는 게 아니라 '잘못 보이던 걸
  멈추는' 것이고, TTT 는 VISSIM total_vehicles 로 재므로 지표는 무편향이다.
  제대로 된 자리는 SC1001_W_out/SC1004_W_out 저류인데 매핑을 새로 짜야 해서 이번 범위 밖이다.

  주입하면 죽어 있던 코드가 여럿 살아난다(urban_queue_model.py:1173-1200 램프 방류 블록 등).
  그중 상한 절단 min(_cap_r, ...) 이 A 에서 R_D_W 206 -> 153.2 로 52.8 veh 를 지운다.
  B 에서는 관측이 상한 아래라 그 절단이 안 걸린다.
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
  @{ name = "arm_rampconn_x18_20260902"; tuning = "evaluation/configs/arm_rampconn_d00_x18_20260902.json"; network = "network/real_world_gaepo_modi/modi_eval_userfix_20260814e_fwsweep_x18_rampbn.inpx"; controller = "wu-link"; note = "B — movement 주입 + 램프관측 커넥터 8개만. 오프라인 램프 예측 27.5->9.6" },
  @{ name = "arm_rampwire_x18_20260902"; tuning = "evaluation/configs/arm_rampwire_d00_x18_20260902.json"; network = "network/real_world_gaepo_modi/modi_eval_userfix_20260814e_fwsweep_x18_rampbn.inpx"; controller = "wu-link"; note = "A — movement 주입만. 2026-08-17 사용자 수정의 첫 폐루프 측정" }
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
