<#
2026-08-28. freeway 레버 활성화. 순차(VISSIM 동시 둘 불가).

  1  canon_fdfit2   FD 실측 재적합만 (원본 망) — canon_nolencap 대비 단일변수
  2  canon_fdfw14   위 + fw14_ramp2 망 (고속도로 x1.4 · 온램프 2배)

왜. 수요를 x1.4 로 올린 무제어 프로브에서도 최대 밀도 32.66 으로 현행 임계 33.5 를
**0.0%** 초과했다. 막혀서가 아니라 임계가 높아서다 — 실측 재적합 21.70 이면
무제어 0.7% · fw12 1.9% · fw14 4.3% 가 초과한다. 그래서 VSL 이 5400초 내내 120.0
고정이었고 leader_density_excess 가 37/37 에서 0.000 이었다.

  1 - canon_nolencap    = FD 효과 (원본 망 사다리에 바로 붙는다)
  2 - nc_fw14_ramp2     = 고속도로가 실제로 일할 때 제어가 이기는가
  **2 는 망이 달라 원본 사다리에 붙이지 마라.**

평가는 보호망 분해로 한다 — scripts/protected_ttt_from_fzp_20260828.py
(전체 TTT 는 제어 불가 monitor 9개 SC 를 17~20% 섞는다).

**바이트 단위로 만들었다.** 텍스트 왕복은 CRLF 를 겹쳐 백틱 줄이음을 깬다.

  1  canon_dpoff      canon_plantfix 에서 dead_phase_beta_zero 만 끈다        <- 과제 1
  2  canon_phasefix   위 + 선언 phase 보정 11건                              <- 과제 3

**순서가 뒤집힌 이유.** 요청은 3->1 이었으나 둘이 상호작용한다 — phase 보정이 dead_phase
판정을 바꾼다(죽이는 movement 13 -> 9). dead_phase 를 끈 팔이 base 여야 보정이 단일변수가
된다. 그래서 dpoff 를 먼저 돌린다. 최종 판정은 두 팔이 다 끝나야 나오므로 순서는
답을 바꾸지 않고, 어느 쪽이 먼저 보이느냐만 바꾼다.

  canon_phasefix - canon_dpoff      = phase 보정 효과 (단일변수)
  canon_dpoff    - canon_plantfix   = dead_phase 효과 (단일변수)

사다리: tau 4699.1 · bstoA 4704.1 · default 4735.0 · 무제어(s13) 4819.4
        canon_plantfix 4823.2 · canon_gne_nofar 5215.4 · canon_gne_t15 5225.7 · canon_gne_far 5232.3
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
  @{ name = "canon_fdfit2_20260828"; tuning = "evaluation/configs/canon_fdfit2_20260828.json"; network = "network/real_world_gaepo_modi/modi_eval_userfix_20260814e.inpx"; note = "FD 실측 재적합 113.0/21.70/2.28/6325.8 (원본 망, nolencap 대비 단일변수)" },
  @{ name = "canon_fdfw14_20260828"; tuning = "evaluation/configs/canon_fdfw14_20260828.json"; network = "network/real_world_gaepo_modi/modi_eval_userfix_20260814e_fw14_ramp2.inpx"; note = "위 + fw14_ramp2 망 (고속도로 x1.4, 온램프 2배) — 대조군은 nc_fw14_ramp2 5394.1" }
)

foreach ($arm in $arms) {
  $name = $arm.name
  $tuningAbs = Join-Path $repo $arm.tuning
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
      -Controller "wu-link" -SimPeriod 5400 -ControlIntervalSec 150 -StateLogIntervalSec 30 -Seed $Seed
  Write-Output ("[{0}] {1} 종료 (exit {2})" -f (Get-Date -Format "HH:mm:ss"), $name, $LASTEXITCODE)

  Get-Process | Where-Object { $_.ProcessName -like "*VISSIM*" } | Stop-Process -Force -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 5
}
Write-Output "=========================================================="
Write-Output ("[{0}] 큐 종료" -f (Get-Date -Format "HH:mm:ss"))
