<#
2026-08-26. 듀얼 λ_P **가격-반응 곡선**. dual_20260826(cap 0.02)을 기준점으로 양옆을 채운다.

  dualc0p005   cap 0.005   거래구간 바닥
  (dual_20260826  cap 0.02   이미 돌았다 — 거래구간 상단)
  dualc0p1     cap 0.1     포화 시작
  dualc0p5     cap 0.5
  dualc2       cap 2.0     현행(10)에 가까운 포화

gain 은 cap 에 비례해 같이 내린다(gain = cap x 1e-3). 안 그러면 어느 팔이든 잔차 한 번에
cap 으로 튀어 축이 하나로 뭉갠다.

왜 이 축인가 — 실런 33결정에서 λ 는 {0: 18, 10: 14, 7.2: 1} 로 순수 bang-bang 이고
gain_pd = 0.01 x np_pd_gain_mult(25) = 0.25 라 잔차 131.8 이면 λ=32.9 -> cap 클립이다.
**cap 이 곧 발화 가격**이다. 오프라인 스윕에서 내부해가 나오는 구간은 0.005~0.02 였고
0.05 이상은 상자 꼭짓점으로 포화했다. 그 예측이 플랜트에서도 맞는지가 이 런의 판정 대상이다.

전부 default_20260825 에서 독립 분기이고 어댑터는 dual 사본 하나를 공유한다(스위치는 config).
#>
param(
  [string[]]$Only = @(),
  [int]$Seed = 13
)

$ErrorActionPreference = "Continue"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runner = Join-Path $repo "scripts\run_real_world_single_watchdog_distributed_core17legs4b.ps1"
$adapter = "evaluation\controllers\vissim_stackelberg_adapter.py"

$common = @{
  Network            = "network\real_world_gaepo_modi\modi_eval_userfix_20260814e.inpx"
  VbsConfig          = "evaluation\generated\real_world_modi_control_config_distributed_core17legs4b_mainline_20260825.vbs"
  Calibration        = "evaluation\calibration\real_world_prediction_calibration_core17legs4b_20260820.json"
  Mapping            = "evaluation\real_world_modi_control_distributed_20260728\control_mapping_distributed_core17legs4b_20260819.json"
  Controller         = "wu-link"
  SimPeriod          = 5400
  ControlIntervalSec = 150
  StateLogIntervalSec= 30
  Seed               = $Seed
}

# 곡선의 양 끝부터 채운다 — 도중에 시간이 모자라도 바깥 점이 먼저 확보되게.
# npin 을 먼저 돌린다 — 축이 다르고(발화 빈도) 메커니즘을 직접 겨냥하므로 정보가 가장 크다.
$arms = @("npin_20260826","dualc2_20260826","dualc0p005_20260826","dualc0p1_20260826","dualc0p5_20260826")
if ($Only.Count -gt 0) { $arms = $arms | Where-Object { $Only -contains $_ } }

$env:RW_MAINLINE_SG_ONLY = "1"
$env:RW_PYTHON_EXE = "C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe"
foreach ($v in @("RW_OFFSET_WRITER","RW_MOVING_SPEED","RW_LANE_DELAY_CORRECTION",
                 "RW_STOPPED_SPLIT","RW_MAINLINE_PLAN","RW_MAINLINE_SHARE_SG","RW_ADAPTER_MODE")) {
  Remove-Item "env:$v" -ErrorAction SilentlyContinue
}

foreach ($name in $arms) {
  $tuning = "evaluation\configs\real_world_modi_pstack_distributed_core17legs4b_$name.json"
  if (-not (Test-Path (Join-Path $repo $tuning))) {
    Write-Output "!! config 없음, 건너뜀: $tuning"; continue
  }
  # npin 은 urban.dual 스위치를 안 쓴다(리더 상자만 바꾼다). 그래서 **정본 어댑터**로 돌린다 —
  # 사본 차이가 결과로 새지 않게 한다. 나머지는 dual 사본을 공유한다(스위치는 config).
  if ($name -eq "npin_20260826") {
    $useAdapter = "evaluation\controllers\vissim_stackelberg_adapter.py"
  } else {
    $useAdapter = $adapter
  }
  $outDir = Join-Path $repo "evaluation\runs\$name"
  Write-Output "=========================================================="
  Write-Output ("[{0}] {1} 시작  adapter={2}" -f (Get-Date -Format "HH:mm:ss"), $name, (Split-Path $useAdapter -Leaf))
  & $runner -Name $name -OutDir $outDir -Adapter $useAdapter -Tuning $tuning `
      -Network $common.Network -VbsConfig $common.VbsConfig `
      -Calibration $common.Calibration -Mapping $common.Mapping `
      -Controller $common.Controller -SimPeriod $common.SimPeriod `
      -ControlIntervalSec $common.ControlIntervalSec `
      -StateLogIntervalSec $common.StateLogIntervalSec -Seed $common.Seed
  Write-Output ("[{0}] {1} 종료 (exit {2})" -f (Get-Date -Format "HH:mm:ss"), $name, $LASTEXITCODE)
}

Write-Output "=========================================================="
Write-Output "듀얼 가격-반응 곡선 TTT:"
& $env:RW_PYTHON_EXE (Join-Path $repo "scripts\compare_runs_ttt.py") `
    nocontrol_s13_20260824 default_20260825 dual_20260826 `
    dualc0p005_20260826 dualc0p1_20260826 dualc0p5_20260826 dualc2_20260826 npin_20260826 `
    --base nocontrol_s13_20260824
