<#
2026-08-28. 녹색 신뢰영역 폭 팔. canon_gne_far 와 단일변수 대조.

  canon_gne_t15   trust 6.0 -> 15.0. 나머지 208개 컨트롤러/cfg 속성 전부 동일(실측 확인).

왜. canon_gne_far(5232.3)·canon_gne_nofar(5215.4)가 canon_plantfix(4823.2)보다 +392~409
나빴다. far 효과는 -16.9 (시드 sigma 50.7 의 0.33배)라 판정 불가 — 벽은 far 가 아니다.
남은 차이는 탐색 폭이다. 정련은 12라운드 x step 6 = 결정당 최대 72초를 움직였고,
GNE 벡터는 trust 6 에 묶였다. 실측 결정간 녹색 L1 이 368.0 -> 87.1 로 4배 줄었다.

**유효 도달폭은 15 가 아니라 12 다.** exchange_steps_sec 가 [6.0] 하나뿐이라 좌표하강이
6초 단위로 걷고, 앵커에서 2걸음(12)까지만 15 안에 들어온다. step 은 이 팔에서 안 건드린다.

사다리: 무제어 4819.4 · tau 4699.1 · bstoA 4704.1 · canon_plantfix 4823.2
        canon_gne_nofar 5215.4 · canon_gne_far 5232.3
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
                 "RW_BOUNDARY_INFLOW_SEED","RW_FORCE_STEPWISE")) {
  Remove-Item "env:$v" -ErrorAction SilentlyContinue
}

$vbsCfg = Join-Path $repo "evaluation/generated/real_world_modi_control_config_distributed_core17legs4f_20260826.vbs"
$sgplan = $vbsCfg -replace "[.]vbs$", "_sgplan.vbs"
foreach ($f in @($vbsCfg, $sgplan)) {
  if (-not (Test-Path $f)) { Write-Output "!! 없음: $f"; exit 1 }
}

$arms = @(
  @{ name = "canon_gne_t15_20260828"; tuning = "evaluation/configs/canon_gne_t15_20260828.json"; note = "trust 15초 (유효 도달 12) · 정련 OFF · 현시가격 GNE 안 · far ON" }
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
      -Network "network/real_world_gaepo_modi/modi_eval_userfix_20260814e.inpx" `
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
