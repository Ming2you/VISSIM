<#
2026-08-27. 정본 팔 순차 큐.

  1  canon_gne_far     dead_phase OFF + 현시가격 GNE 안 + 후보채점 far ON
  2  canon_gne_nofar   위와 동일 · far OFF          <- 1 과 단일변수 대조(far 효과)
  3  canon_fdfit       FD 실측적합 113.0/21.7/2.28/6325.8

**순차인 이유.** VISSIM 인스턴스가 동시에 둘 뜨지 못한다. 2026-08-27 병렬 시도에서
앞 런이 16분 만에 EXIT_NO_DONE, 재시도 2·3차가 20초 만에 죽었다(어댑터는 정상이었다).

대조군: canon_plantfix_20260827 = 4823.2 (+3.8)
기준선: 무제어 4819.4 · tau 4699.1 · bstoA 4704.1 · plantfix(구,지평6) 4859.3
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
  @{ name = "canon_gne_far_20260827";   tuning = "evaluation/configs/canon_gne_far_20260827.json";   note = "dead_phase OFF + 현시가격 GNE 안 + 후보채점 far ON" },
  @{ name = "canon_gne_nofar_20260827"; tuning = "evaluation/configs/canon_gne_nofar_20260827.json"; note = "위와 동일 · 후보채점 far OFF (단일변수 대조)" },
  @{ name = "canon_fdfit_20260827";     tuning = "evaluation/configs/canon_fdfit_20260827.json";     note = "FD 실측적합 113.0/21.7/2.28/6325.8" }
)

foreach ($arm in $arms) {
  $name = $arm.name
  $tuningAbs = Join-Path $repo $arm.tuning
  & $env:RW_PYTHON_EXE (Join-Path $repo "scripts/preflight_tuning_paths.py") $tuningAbs --quiet
  if ($LASTEXITCODE -ne 0) { Write-Output ("!! {0} 사전점검 실패 — 건너뛴다" -f $name); continue }
  & $env:RW_PYTHON_EXE (Join-Path $repo "scripts/verify_parameters.py") $tuningAbs --quiet
  if ($LASTEXITCODE -ne 0) { Write-Output ("!! {0} 파라미터 검증 실패 — 건너뛴다" -f $name); continue }

  # 앞 팔의 VISSIM 이 확실히 없어진 뒤에 시작한다.
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
