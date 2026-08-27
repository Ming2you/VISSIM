<#
2026-08-26. 경계 유입 저류 39개 신설. map4f 에서 **config 한 항목만** 바뀐다.

무엇이 왜
  모델 저류 187개 중 in_* 가 0개였다. _link_storage_split_fraction 이 저류를 못 찾으면
  0.0 을 반환하고, 경계 유입 링크는 전량 movement 큐로 간다. movement 큐는 한 스텝에
  방류되므로 매 결정 증발한다.
    실측 경계 접근로 재고 651.8대  대  모델 표현 154.9대

  용량 = 링크 길이 x 차로수 / 6m (modi_eval_userfix_20260814e.inpx 폴리라인). 합 10,094대.
  tau 가 available x 6m 를 거리로 쓰므로 용량이 곧 정지선까지의 거리다 — 빈 링크면 멀고
  꽉 차면 꼬리가 입구라 즉시 도달하는 설계다(urban_queue_model.py:627-636).

오프라인 검증 (VISSIM 없이 map4etau 결정 30개 재예측, origin 단위 규칙불변 지표)
    변형              절대오차   상대오차   in_ 오차
    기준               1478.4    55.7%     555.5
    A 길이x차로/6       1099.2    41.9%     161.1   <- 채택
    B 길이/6           1120.4    42.4%     185.1
  in_ 예측 154.9 -> 677.6 (실측 651.8). _to_ 와 _out 은 거의 불변 — 수술이 정확하다.

판정 기준
  프로젝션의 in_ 관련 표현량이 오르는가
  TTT 는 미지. 예측 개선이 폐루프로 번역된다는 보장은 없다(리더 argmin 이 축퇴돼 있다).

기준선: 무제어 4808.1 · default 4723.9 · tau 4688.4(최선) · map4etau 4746.9 · map4ftau(대조)
#>
param([int]$Seed = 13)

$ErrorActionPreference = "Continue"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runner = Join-Path $repo "scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1"
$name = "bstoAtau_20260826"

$env:RW_MAINLINE_SG_ONLY = "1"
$env:RW_PYTHON_EXE = "C:/Users/TRLAB/AppData/Local/Programs/Python/Python312/python.exe"
foreach ($v in @("RW_OFFSET_WRITER","RW_MOVING_SPEED","RW_LANE_DELAY_CORRECTION","RW_NP_STATE_BAND",
                 "RW_STOPPED_SPLIT","RW_MAINLINE_PLAN","RW_MAINLINE_SHARE_SG","RW_ADAPTER_MODE",
                 "RW_QUEUE_ORIGIN_BINDING")) {
  Remove-Item "env:$v" -ErrorAction SilentlyContinue
}

$vbsCfg = Join-Path $repo "evaluation/generated/real_world_modi_control_config_distributed_core17legs4f_20260826.vbs"
$sgplan = $vbsCfg -replace "[.]vbs$", "_sgplan.vbs"
foreach ($f in @($vbsCfg, $sgplan)) {
  if (-not (Test-Path $f)) { Write-Output "!! 없음: $f"; exit 1 }
}
Write-Output ("사전점검 OK  config {0} B · sgplan {1} B" -f (Get-Item $vbsCfg).Length, (Get-Item $sgplan).Length)
$tuningPath = Join-Path $repo "evaluation/configs/canon_bstoA_20260827.json"
& $env:RW_PYTHON_EXE (Join-Path $repo "scripts/preflight_tuning_paths.py") $tuningPath
if ($LASTEXITCODE -ne 0) { Write-Output "!! tuning 경로 사전점검 실패"; exit 1 }
# 경로만 맞아도 값이 안 들어갈 수 있다(2026-08-27 감사). 정본 파라미터가 실효값이
# 됐는지, 선언 없는 어긋남이 없는지 검사한다.
& $env:RW_PYTHON_EXE (Join-Path $repo "scripts/verify_parameters.py") $tuningPath --quiet
if ($LASTEXITCODE -ne 0) { Write-Output "!! 정본 파라미터 검증 실패"; exit 1 }

$outDir = Join-Path $repo "evaluation/runs/$name"
Write-Output ("[{0}] {1} 시작  (경계저류 39개 · 스캔 670)" -f (Get-Date -Format "HH:mm:ss"), $name)
& $runner -Name $name -OutDir $outDir `
    -Adapter "evaluation/controllers/vissim_stackelberg_adapter.py" `
    -Tuning  "evaluation/configs/canon_bstoA_20260827.json" `
    -Network "network/real_world_gaepo_modi/modi_eval_userfix_20260814e.inpx" `
    -VbsConfig "evaluation/generated/real_world_modi_control_config_distributed_core17legs4f_20260826.vbs" `
    -Calibration "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json" `
    -Mapping "evaluation/real_world_modi_control_distributed_20260728/control_mapping_distributed_core17legs4b_20260819.json" `
    -Controller "wu-link" -SimPeriod 5400 -ControlIntervalSec 150 -StateLogIntervalSec 30 -Seed $Seed
Write-Output ("[{0}] {1} 종료 (exit {2})" -f (Get-Date -Format "HH:mm:ss"), $name, $LASTEXITCODE)
Write-Output "=========================================================="
& $env:RW_PYTHON_EXE (Join-Path $repo "scripts/compare_runs_ttt.py") `
    nocontrol_s13_20260824 tau_20260826 map4etau_20260826 map4ftau_20260826 $name `
    --base nocontrol_s13_20260824
