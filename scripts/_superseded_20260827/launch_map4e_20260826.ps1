<#
2026-08-26. 매핑 누수 판정을 적용한 첫 실런. **default_20260825 에서 매핑만** 바뀐다.

바뀌는 것 넷 (그 외 전부 default 와 동일)
  detector mapping  ..._core17legs4e_20260826.json   경계 큐 21건 배선 · 종단 배정 36건 · 램프 가중
  **베이스는 tau_20260825** — τ(이동차 속도 + 차로 보정)가 켜져 있다. 짝은 tau_20260826(4688.4)이고
  그 차이가 곧 매핑 효과다. 처음엔 default 를 extends 했다가 사용자 지적으로 바꿨다 —
  캘리브레이션 재적합은 최종 plant 위에서 해야 하고, τ 를 맞춘 대조가 더 깨끗하다.
  VBS config        ..._core17legs4e_20260826.vbs    RW_LOCAL_OBSERVABLE_LINKS 293 -> **626**
  config            ..._map4e_20260826.json          저류 160 -> 162 (SC107_E_out · SC109_W_out)
  adapter           ..._map4e_20260826.py            ramp_link_to_queues 가중 dict 지원

## 왜 실런이 필요한가

리플레이로 같은 state 를 4d/4e 로 재보면 모델 몫이 **62.5% -> 66.6%**(+109 veh) 오른다.
그런데 **관측불가 583(22.3%)은 리플레이로 안 준다** — 러너의 스캔 목록이 정하고
기록된 state JSON 에 그 차량이 애초에 없기 때문이다. 스캔 링크를 626 으로 넓힌 이 런에서만
회수된다.

## 판정 기준

  projection_unobservable_vehicle_count_veh 가 583 보다 크게 줄어드는가
  모델 몫이 66.6% 보다 오르는가
  TTT 는 미지 — 캘리브레이션이 옛 누수 위에서 적합됐으므로 악화할 수도 있다.
  (그 경우 예측 보정 재적합이 다음 수순이지 매핑을 되돌릴 일은 아니다.)

기준선: 무제어 4808.1 · default_20260825 4723.9 · **tau_20260826 4688.4(현 최선)**
#>
param([int]$Seed = 13)

$ErrorActionPreference = "Continue"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runner = Join-Path $repo "scripts\run_real_world_single_watchdog_distributed_core17legs4b.ps1"
# 이름에 tau 를 넣는다 — 이 팔은 tau_20260825 위에 매핑 4e 를 얹은 것이고,
# 짝은 tau_20260826 이다. (첫 시도 map4e_20260826 은 sgplan 형제가 없어 무제어로 돌아 폐기했다.)
$name = "map4etau_20260826"

$env:RW_MAINLINE_SG_ONLY = "1"
$env:RW_PYTHON_EXE = "C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe"
foreach ($v in @("RW_OFFSET_WRITER","RW_MOVING_SPEED","RW_LANE_DELAY_CORRECTION","RW_NP_STATE_BAND",
                 "RW_STOPPED_SPLIT","RW_MAINLINE_PLAN","RW_MAINLINE_SHARE_SG","RW_ADAPTER_MODE")) {
  Remove-Item "env:$v" -ErrorAction SilentlyContinue
}

# ── 사전점검 ──────────────────────────────────────────────────────────────
# 러너는 신호 계획을 VBS config 의 **형제**(<config>_sgplan.vbs)로 찾는다
# (run_real_world_stackelberg_controller.vbs:1797). config 만 복사하고 형제를 안 만들면
# 17개 신호가 전량 거부되고(ACTION_CSV_SIGNAL_WITHOUT_PLAN_CONFIG) **무제어로 완주한다** —
# 2026-08-26 에 그렇게 92분을 버렸다. 조용히 실패하므로 여기서 못박는다.
$vbsCfg = Join-Path $repo "evaluation\generated\real_world_modi_control_config_distributed_core17legs4e_20260826.vbs"
$sgplan = $vbsCfg -replace '\.vbs$', '_sgplan.vbs'
foreach ($f in @($vbsCfg, $sgplan)) {
  if (-not (Test-Path $f)) { Write-Output "!! 없음: $f"; exit 1 }
}
Write-Output ("사전점검 OK  config {0} B · sgplan {1} B" -f (Get-Item $vbsCfg).Length, (Get-Item $sgplan).Length)

# tuning 이 가리키는 경로를 발사 전에 검사한다. 2026-08-26 에 config 의 백슬래시 경로가
# JSON 에서 캐리지리턴으로 해석돼 detector mapping 이 사라졌고, load_optional_json 이
# 조용히 빈 dict 를 내서 이 런이 관측 없이 92분을 완주했다 (TTT 4806.7 = 무제어 수준).
# 러너는 결정 실패를 세면서도 완주하므로 어댑터 안의 가드로는 시간을 못 아낀다.
$tuningPath = Join-Path $repo "evaluation/configs/real_world_modi_pstack_distributed_core17legs4b_map4e_20260826.json"
& $env:RW_PYTHON_EXE (Join-Path $repo "scripts/preflight_tuning_paths.py") $tuningPath
if ($LASTEXITCODE -ne 0) { Write-Output "!! tuning 경로 사전점검 실패 - 런을 시작하지 않는다"; exit 1 }

$outDir = Join-Path $repo "evaluation\runs\$name"
Write-Output ("[{0}] {1} 시작  (스캔 링크 626)" -f (Get-Date -Format "HH:mm:ss"), $name)
& $runner -Name $name -OutDir $outDir `
    -Adapter "evaluation\controllers\vissim_stackelberg_adapter.py" `
    -Tuning  "evaluation\configs\real_world_modi_pstack_distributed_core17legs4b_map4e_20260826.json" `
    -Network "network\real_world_gaepo_modi\modi_eval_userfix_20260814e.inpx" `
    -VbsConfig "evaluation\generated\real_world_modi_control_config_distributed_core17legs4e_20260826.vbs" `
    -Calibration "evaluation\calibration\real_world_prediction_calibration_core17legs4b_20260820.json" `
    -Mapping "evaluation\real_world_modi_control_distributed_20260728\control_mapping_distributed_core17legs4b_20260819.json" `
    -Controller "wu-link" -SimPeriod 5400 -ControlIntervalSec 150 -StateLogIntervalSec 30 -Seed $Seed
Write-Output ("[{0}] {1} 종료 (exit {2})" -f (Get-Date -Format "HH:mm:ss"), $name, $LASTEXITCODE)

Write-Output "=========================================================="
& $env:RW_PYTHON_EXE (Join-Path $repo "scripts\compare_runs_ttt.py") `
    nocontrol_s13_20260824 default_20260825 tau_20260826 $name `
    --base nocontrol_s13_20260824
