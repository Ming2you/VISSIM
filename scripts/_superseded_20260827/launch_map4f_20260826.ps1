<#
2026-08-26. 매핑 4f — 미관측 잔량 회수. map4e 에서 **detector mapping 만** 바뀐다.

무엇이 왜 바뀌나
  4e 에서 관측불가가 142대 남았다. 그중
    69   49.7대  CLAUDE.md sc1004-west-split-20260819 대로 무소유. **손대지 않는다**
    68   32.3대  아티팩트가 decision_log 로 오분류해 사용자 판정을 못 받았다
    31   25.0대  같은 오분류. link-78 항목 본문에 31 이 나온 것을 판정으로 오독했다
    109  10.3대  같은 오분류. 하류 0개 = 종단 링크
    78    8.4대  판정은 있었으나 observable_links 에 안 넣어 배선이 죽어 있었다

  사용자 판정 (2026-08-26): 68 -> 78처럼 FW_E/FW_W · 31 -> 78처럼 FW_E/FW_W · 109 -> SC2004_N_out
  실제 망(userfix_20260814e)에서 확인한 출구:
    68  -> 10646(R_F_W) · 10681(R_F_E) 둘뿐 = 100% 고속도로행 -> 0.5/0.5
    31  -> 10480(R_D_W) · 10484(R_D_E) · 10704->79(도시). relFlow 2:1 -> 0.667/0.333
    78  -> 10703->31 하나뿐 -> 31 과 동일
    109 -> 없음. 상류 셋이 전부 SC2004 로 향함 -> SC2004_N_out (용량 247.3)
  **68 은 R_F_* 이지 R_D_* 이 아니다** — 31/78 과 램프 쌍이 다르다.

  observable_links 626 -> 670. 이것이 핵심이다. 매핑 표에 넣어도 스캔 목록에 없으면
  러너가 안 훑어 state JSON 에 차량이 안 실린다. 4e 가 그래서 33.4대를 흘렸다.

판정 기준
  projection_unobservable_vehicle_count_veh 가 142 -> 60 근처로 떨어지는가
    (남는 60 중 49.7 이 설계상 link 69 다. 실질 잔량은 약 10대)
  모델 몫이 63.5% 보다 오르는가
  TTT 는 미지다. 4e 는 4d 대비 +58.5 악화했다(4746.9 대 4688.4).

기준선: 무제어 4808.1 · default 4723.9 · **tau_20260826 4688.4(현 최선)** · map4etau 4746.9
#>
param([int]$Seed = 13)

$ErrorActionPreference = "Continue"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runner = Join-Path $repo "scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1"
$name = "map4ftau_20260826"

$env:RW_MAINLINE_SG_ONLY = "1"
$env:RW_PYTHON_EXE = "C:/Users/TRLAB/AppData/Local/Programs/Python/Python312/python.exe"
foreach ($v in @("RW_OFFSET_WRITER","RW_MOVING_SPEED","RW_LANE_DELAY_CORRECTION","RW_NP_STATE_BAND",
                 "RW_STOPPED_SPLIT","RW_MAINLINE_PLAN","RW_MAINLINE_SHARE_SG","RW_ADAPTER_MODE")) {
  Remove-Item "env:$v" -ErrorAction SilentlyContinue
}

# 사전점검 하나 — sgplan 형제가 없으면 17개 신호가 전량 거부되고 무제어로 완주한다
$vbsCfg = Join-Path $repo "evaluation/generated/real_world_modi_control_config_distributed_core17legs4f_20260826.vbs"
$sgplan = $vbsCfg -replace "[.]vbs$", "_sgplan.vbs"
foreach ($f in @($vbsCfg, $sgplan)) {
  if (-not (Test-Path $f)) { Write-Output "!! 없음: $f"; exit 1 }
}
Write-Output ("사전점검 OK  config {0} B · sgplan {1} B" -f (Get-Item $vbsCfg).Length, (Get-Item $sgplan).Length)

# 사전점검 둘 — tuning 이 가리키는 경로. 백슬래시가 JSON 에서 CR 로 먹힌 전례가 있다
$tuningPath = Join-Path $repo "evaluation/configs/real_world_modi_pstack_distributed_core17legs4b_map4f_20260826.json"
& $env:RW_PYTHON_EXE (Join-Path $repo "scripts/preflight_tuning_paths.py") $tuningPath
if ($LASTEXITCODE -ne 0) { Write-Output "!! tuning 경로 사전점검 실패 - 런을 시작하지 않는다"; exit 1 }

$outDir = Join-Path $repo "evaluation/runs/$name"
Write-Output ("[{0}] {1} 시작  (스캔 링크 670)" -f (Get-Date -Format "HH:mm:ss"), $name)
& $runner -Name $name -OutDir $outDir `
    -Adapter "evaluation/controllers/vissim_stackelberg_adapter.py" `
    -Tuning  "evaluation/configs/real_world_modi_pstack_distributed_core17legs4b_map4f_20260826.json" `
    -Network "network/real_world_gaepo_modi/modi_eval_userfix_20260814e.inpx" `
    -VbsConfig "evaluation/generated/real_world_modi_control_config_distributed_core17legs4f_20260826.vbs" `
    -Calibration "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json" `
    -Mapping "evaluation/real_world_modi_control_distributed_20260728/control_mapping_distributed_core17legs4b_20260819.json" `
    -Controller "wu-link" -SimPeriod 5400 -ControlIntervalSec 150 -StateLogIntervalSec 30 -Seed $Seed
Write-Output ("[{0}] {1} 종료 (exit {2})" -f (Get-Date -Format "HH:mm:ss"), $name, $LASTEXITCODE)

Write-Output "=========================================================="
& $env:RW_PYTHON_EXE (Join-Path $repo "scripts/compare_runs_ttt.py") `
    nocontrol_s13_20260824 default_20260825 tau_20260826 map4etau_20260826 $name `
    --base nocontrol_s13_20260824
