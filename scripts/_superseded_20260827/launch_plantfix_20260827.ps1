<#
2026-08-27. plant 수정 (B) — 단독 1시드.

무엇이 바뀌나 (tau_20260826 대비)
  VBS   4f  스캔 293 -> 670 링크 · detector mapping 4f
  plant urban.tau.length_cap          tau 이동거리를 저류 물리 길이로 상한
        urban.movements.dead_phase_beta_zero  녹색이 구조적으로 0 인 현시 5개의 movement 17개 beta=0
  어댑터 qbind  위 둘 + 가격 워커 부트스트랩(부모/워커 tau 불일치 차단)

오프라인 근거 (무제어 네이티브 런, 출발점 30 x 6스텝, off-policy 오염 없음)
    스텝3(MPC horizon)  70.3% -> 53.8%   (-16.5pt)
    스텝6(리더 끝)       91.6% -> 73.2%   (-18.4pt)

해석 한계 — 짝지음 null 산포 대용치가 sd 40.7 veh*h 다. 차이가 ±80 안이면
시드 반복 없이는 판정할 수 없다. 그건 미리 알고 돌린다.

기준선: 무제어 4808.1 · default 4723.9 · **tau_20260826 4688.4(현 최선)**
#>
param([int]$Seed = 13)

$ErrorActionPreference = "Continue"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runner = Join-Path $repo "scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1"
$name = "plantfix_20260827"

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
$tuningPath = Join-Path $repo "evaluation/configs/canon_plantfix_20260827.json"
& $env:RW_PYTHON_EXE (Join-Path $repo "scripts/preflight_tuning_paths.py") $tuningPath --quiet
if ($LASTEXITCODE -ne 0) { Write-Output "!! tuning 경로 사전점검 실패"; exit 1 }
# 경로만 맞아도 값이 안 들어갈 수 있다(2026-08-27 감사). 정본 파라미터가 실효값이
# 됐는지, 선언 없는 어긋남이 없는지 검사한다.
& $env:RW_PYTHON_EXE (Join-Path $repo "scripts/verify_parameters.py") $tuningPath --quiet
if ($LASTEXITCODE -ne 0) { Write-Output "!! 정본 파라미터 검증 실패"; exit 1 }
Write-Output "사전점검 OK"

$outDir = Join-Path $repo "evaluation/runs/$name"
Write-Output ("[{0}] {1} 시작 (plantfix · 4f 670링크)" -f (Get-Date -Format "HH:mm:ss"), $name)
& $runner -Name $name -OutDir $outDir `
    -Adapter "evaluation/controllers/vissim_stackelberg_adapter.py" `
    -Tuning  "evaluation/configs/canon_plantfix_20260827.json" `
    -Network "network/real_world_gaepo_modi/modi_eval_userfix_20260814e.inpx" `
    -VbsConfig "evaluation/generated/real_world_modi_control_config_distributed_core17legs4f_20260826.vbs" `
    -Calibration "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json" `
    -Mapping "evaluation/real_world_modi_control_distributed_20260728/control_mapping_distributed_core17legs4b_20260819.json" `
    -Controller "wu-link" -SimPeriod 5400 -ControlIntervalSec 150 -StateLogIntervalSec 30 -Seed $Seed
Write-Output ("[{0}] {1} 종료 (exit {2})" -f (Get-Date -Format "HH:mm:ss"), $name, $LASTEXITCODE)
Write-Output "=========================================================="
& $env:RW_PYTHON_EXE (Join-Path $repo "scripts/compare_runs_ttt.py") `
    nocontrol_s13_20260824 default_20260825 tau_20260826 $name `
    --base nocontrol_s13_20260824
