<#
2026-08-27. 증량 망의 **무제어 기준선 + FD 자료 수집**.

왜 제어보다 먼저인가
  (1) 증량 수요에서 무제어 TTT 를 모르면 제어 효과를 못 잰다. 기존 4808.1 은 원본 수요 값이다.
  (2) 지금 FD 재적합(rho_crit 16.354)은 혼잡이 거의 없던 자료로 적합했다 —
      파일 스스로 rho_p95=15.03 · frac_rho_gt_rho_crit=1.6% 이고
      'WARN: 관측 유량이 상단에서 잘려 최대 bin 이 절단점일 수 있다' 고 적는다.
      임계 근처 자료 없이 임계를 추정한 값으로 증량 실험을 판정하면 순환이다.
      증량 무제어 런이 임계 영역 자료를 만들어 준다.

무제어는 도시신호를 COM 제어하지 않아 .inpx 네이티브 프로그램이 돈다(되읽기 도시신호 0종).
-ForceStepwise 는 러너 인자로 넘겨야 한다 — 환경변수는 러너가 덮어쓴다.
#>
param(
  [Parameter(Mandatory=$true)][string]$Net,
  [Parameter(Mandatory=$true)][string]$Tag,
  [int]$Seed = 13
)
$ErrorActionPreference = "Continue"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runner = Join-Path $repo "scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1"
$name = "nc_" + $Tag + "_20260827"

$env:RW_MAINLINE_SG_ONLY = "1"
$env:RW_PYTHON_EXE = "C:/Users/TRLAB/AppData/Local/Programs/Python/Python312/python.exe"
foreach ($v in @("RW_OFFSET_WRITER","RW_MOVING_SPEED","RW_LANE_DELAY_CORRECTION","RW_NP_STATE_BAND",
                 "RW_STOPPED_SPLIT","RW_MAINLINE_PLAN","RW_MAINLINE_SHARE_SG","RW_ADAPTER_MODE",
                 "RW_QUEUE_ORIGIN_BINDING","RW_TAU_LENGTH_CAP","RW_DEAD_PHASE_BETA_ZERO",
                 "RW_BOUNDARY_INFLOW_SEED","RW_FORCE_STEPWISE")) {
  Remove-Item "env:$v" -ErrorAction SilentlyContinue
}
$netPath = Join-Path $repo $Net
if (-not (Test-Path $netPath)) { Write-Output ("!! 망 없음: " + $netPath); exit 1 }
$vbsCfg = Join-Path $repo "evaluation/generated/real_world_modi_control_config_distributed_core17legs4f_20260826.vbs"
$sgplan = $vbsCfg -replace "[.]vbs$", "_sgplan.vbs"
foreach ($f in @($vbsCfg, $sgplan)) {
  if (-not (Test-Path $f)) { Write-Output ("!! 없음: " + $f); exit 1 }
}
$outDir = Join-Path $repo ("evaluation/runs/" + $name)
Write-Output ("[{0}] {1} 시작  net={2}" -f (Get-Date -Format "HH:mm:ss"), $name, $Tag)
& $runner -Name $name -OutDir $outDir `
    -Adapter "evaluation/controllers/vissim_stackelberg_adapter.py" `
    -Tuning  "evaluation/configs/canon_plantfix_20260827.json" `
    -Network $Net `
    -VbsConfig "evaluation/generated/real_world_modi_control_config_distributed_core17legs4f_20260826.vbs" `
    -Calibration "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json" `
    -Mapping "evaluation/real_world_modi_control_distributed_20260728/control_mapping_distributed_core17legs4b_20260819.json" `
    -Controller "no-control" -ForceStepwise -SimPeriod 5400 -ControlIntervalSec 150 -StateLogIntervalSec 30 -Seed $Seed
Write-Output ("[{0}] {1} 종료 (exit {2})" -f (Get-Date -Format "HH:mm:ss"), $name, $LASTEXITCODE)
$n = (Get-ChildItem (Join-Path $outDir ("decisions_" + $name)) -Filter "state_*.json" -ErrorAction SilentlyContinue).Count
Write-Output ("state 파일 {0}개 (37 이어야 정상)" -f $n)
