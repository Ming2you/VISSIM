<#
2026-08-27. canon_plantfix 가 끝나면 canon_fdfit 을 이어서 돌린다.

canon_fdfit = canon_plantfix + freeway FD 실측적합. 단일 변수(FD 넷).
  v_free 100 -> 113.0 · rho_crit 33.5 -> 21.7 · a 1.867 -> 2.28 · capacity 4000 -> 6325.8
  용량은 나머지 셋의 파생값이라 따로 둘 수 없다. q = rho_crit*v_free*exp(-1/a)*4.

왜. 현행은 실측과 두 방향으로 어긋난다 — 자유류를 15 kph 과소, 혼잡을 14~17 kph 과대.
그리고 4차로에서 FD 가 함의하는 용량 7843 과 저장값 4000 이 1.96배 어긋나 있다.
rho_crit 33.5 가 실측 21.7 보다 12 높아 실측 밀도 최대 32.7 이 임계를 0.0% 초과했고,
그래서 VSL 이 켜질 물리적 근거가 없었다.

판정 기준은 예측오차가 아니라 **폐루프 TTT** 다. 이 프로젝트에서 예측 개선이 폐루프
악화로 간 전례가 둘 있다(차로수 보정, plantfix).

기준선: 무제어 4819.4 · tau 4699.1 · bstoA 4704.1 · plantfix(구) 4859.3
#>
param([int]$Seed = 13, [int]$PollSec = 60, [int]$MaxWaitMin = 180)

$ErrorActionPreference = "Continue"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runner = Join-Path $repo "scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1"

# --- 앞 런이 끝나기를 기다린다. 병렬 실행은 2026-08-27 에 실패·좀비를 냈다. ---
$prev = Join-Path $repo "evaluation/runs/canon_plantfix_20260827"
$deadline = (Get-Date).AddMinutes($MaxWaitMin)
while ((Get-Date) -lt $deadline) {
  $n = 0
  if (Test-Path $prev) { $n = @(Get-ChildItem -Path $prev -Recurse -Filter "state_*.json" -ErrorAction SilentlyContinue).Count }
  $alive = @(Get-Process | Where-Object { $_.ProcessName -like "*VISSIM*" }).Count
  if ($n -ge 37 -and $alive -eq 0) { Write-Output ("[{0}] 앞 런 완주 ({1}/37). 이어서 시작." -f (Get-Date -Format "HH:mm:ss"), $n); break }
  Write-Output ("[{0}] 대기 — canon_plantfix {1}/37 · VISSIM {2}개" -f (Get-Date -Format "HH:mm:ss"), $n, $alive)
  Start-Sleep -Seconds $PollSec
}
if ((Get-Date) -ge $deadline) { Write-Output "!! 대기 시간 초과. 시작하지 않는다."; exit 1 }

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

$name = "canon_fdfit_20260827"
$tuningPath = Join-Path $repo "evaluation/configs/canon_fdfit_20260827.json"
& $env:RW_PYTHON_EXE (Join-Path $repo "scripts/preflight_tuning_paths.py") $tuningPath --quiet
if ($LASTEXITCODE -ne 0) { Write-Output "!! tuning 경로 사전점검 실패"; exit 1 }
# 경로만 맞아도 값이 안 들어갈 수 있다(2026-08-27 감사). 정본 파라미터가 실효값이
# 됐는지, 선언 없는 어긋남이 없는지 검사한다.
& $env:RW_PYTHON_EXE (Join-Path $repo "scripts/verify_parameters.py") $tuningPath --quiet
if ($LASTEXITCODE -ne 0) { Write-Output "!! 정본 파라미터 검증 실패"; exit 1 }
Write-Output "사전점검 OK"

$outDir = Join-Path $repo "evaluation/runs/$name"
Write-Output ("[{0}] {1} 시작 (FD 실측적합 113.0/21.7/2.28/6325.8)" -f (Get-Date -Format "HH:mm:ss"), $name)
& $runner -Name $name -OutDir $outDir `
    -Adapter "evaluation/controllers/vissim_stackelberg_adapter.py" `
    -Tuning  "evaluation/configs/canon_fdfit_20260827.json" `
    -Network "network/real_world_gaepo_modi/modi_eval_userfix_20260814e.inpx" `
    -VbsConfig "evaluation/generated/real_world_modi_control_config_distributed_core17legs4f_20260826.vbs" `
    -Calibration "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json" `
    -Mapping "evaluation/real_world_modi_control_distributed_20260728/control_mapping_distributed_core17legs4b_20260819.json" `
    -Controller "wu-link" -SimPeriod 5400 -ControlIntervalSec 150 -StateLogIntervalSec 30 -Seed $Seed
Write-Output ("[{0}] {1} 종료 (exit {2})" -f (Get-Date -Format "HH:mm:ss"), $name, $LASTEXITCODE)
