<#
2026-08-26. **무제어 + 스텝별 상태 포착.** plant 롤아웃 검증 전용이다.

왜 필요한가
  지금 하네스는 map4etau 런(옛 어댑터·옛 config)을 새 config 로 재생한다. 경계저류 39개
  때문에 t=0 에 이미 +441대 차이가 나고, 먹이는 action 은 그 441대를 모르는 컨트롤러가
  고른 것이다 — off-policy 오염이다. 무제어로 돌리면 컨트롤러가 루프에서 빠져 plant
  충실도만 남는다.

  기존 nocontrol_s13_20260824 는 RUN_MODE=CONTINUOUS_STATIC 이라 state 파일이 **2개**뿐이다.
  RW_FORCE_STEPWISE=1 이 그 분기를 뒤집는다:
      UseContinuousStaticMode = (Not ForceStepwiseMode()) And (c = 'no-control' ...)
  이러면 150초마다 어댑터가 불려 state(local_observation + vehicle_records)를 쓰고,
  제어는 커밋되지 않아 VISSIM 네이티브 신호 프로그램이 그대로 돈다.

  스캔은 4f VBS(670 링크)를 쓴다 — 옛 무제어 런은 293 링크였다.

산출
  decisions_*/state_*.json  37개. 이걸로 다양한 부하 시점(혼잡/비혼잡)에 대해 6스텝
  개루프 롤아웃 정확도를 잰다. 롤아웃에 먹일 제어는 네이티브 현시 분할이다
  (outputs/signal_group_actuation_plan_v3.json 의 axis_green_sec).
#>
param([int]$Seed = 13)

$ErrorActionPreference = "Continue"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runner = Join-Path $repo "scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1"
$name = "nocontrolstep_20260826"

$env:RW_MAINLINE_SG_ONLY = "1"
# RW_FORCE_STEPWISE 를 여기서 세워봐야 소용없다 — 러너가 자기 -ForceStepwise 스위치로
# **덮어쓴다**(watchdog:335-339, 꺼져 있으면 $null 로 지운다). 러너 인자로 넘겨야 한다.
# 2026-08-26 에 env 로만 세웠다가 RUN_MODE=CONTINUOUS_STATIC 으로 돌아 state 가 1개만 나왔다.
$env:RW_PYTHON_EXE = "C:/Users/TRLAB/AppData/Local/Programs/Python/Python312/python.exe"
foreach ($v in @("RW_OFFSET_WRITER","RW_MOVING_SPEED","RW_LANE_DELAY_CORRECTION","RW_NP_STATE_BAND",
                 "RW_STOPPED_SPLIT","RW_MAINLINE_PLAN","RW_MAINLINE_SHARE_SG","RW_ADAPTER_MODE",
                 "RW_QUEUE_ORIGIN_BINDING","RW_TAU_LENGTH_CAP","RW_DEAD_PHASE_BETA_ZERO")) {
  Remove-Item "env:$v" -ErrorAction SilentlyContinue
}

$vbsCfg = Join-Path $repo "evaluation/generated/real_world_modi_control_config_distributed_core17legs4f_20260826.vbs"
$sgplan = $vbsCfg -replace "[.]vbs$", "_sgplan.vbs"
foreach ($f in @($vbsCfg, $sgplan)) {
  if (-not (Test-Path $f)) { Write-Output "!! 없음: $f"; exit 1 }
}
$tuningPath = Join-Path $repo "evaluation/configs/canon_bstoA_20260827.json"
& $env:RW_PYTHON_EXE (Join-Path $repo "scripts/preflight_tuning_paths.py") $tuningPath --quiet
if ($LASTEXITCODE -ne 0) { Write-Output "!! tuning 경로 사전점검 실패"; exit 1 }
# 경로만 맞아도 값이 안 들어갈 수 있다(2026-08-27 감사). 정본 파라미터가 실효값이
# 됐는지, 선언 없는 어긋남이 없는지 검사한다.
& $env:RW_PYTHON_EXE (Join-Path $repo "scripts/verify_parameters.py") $tuningPath --quiet
if ($LASTEXITCODE -ne 0) { Write-Output "!! 정본 파라미터 검증 실패"; exit 1 }
Write-Output "사전점검 OK · 러너에 -ForceStepwise 를 넘긴다"

$outDir = Join-Path $repo "evaluation/runs/$name"
Write-Output ("[{0}] {1} 시작 (무제어 · 스텝별 · 스캔 670)" -f (Get-Date -Format "HH:mm:ss"), $name)
& $runner -Name $name -OutDir $outDir `
    -Adapter "evaluation/controllers/vissim_stackelberg_adapter.py" `
    -Tuning  "evaluation/configs/canon_bstoA_20260827.json" `
    -Network "network/real_world_gaepo_modi/modi_eval_userfix_20260814e.inpx" `
    -VbsConfig "evaluation/generated/real_world_modi_control_config_distributed_core17legs4f_20260826.vbs" `
    -Calibration "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json" `
    -Mapping "evaluation/real_world_modi_control_distributed_20260728/control_mapping_distributed_core17legs4b_20260819.json" `
    -Controller "no-control" -ForceStepwise -SimPeriod 5400 -ControlIntervalSec 150 -StateLogIntervalSec 30 -Seed $Seed
Write-Output ("[{0}] {1} 종료 (exit {2})" -f (Get-Date -Format "HH:mm:ss"), $name, $LASTEXITCODE)
$n = (Get-ChildItem (Join-Path $outDir "decisions_$name") -Filter "state_*.json" -ErrorAction SilentlyContinue).Count
Write-Output ("state 파일 {0}개 (37 이어야 정상)" -f $n)
