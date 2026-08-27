<#
2026-08-26. 세 팔을 default_20260825 에서 **각각 독립으로** 분기해 순차 실행한다.

  dual_20260826    lambda_np_cap 10 -> 0.02 · gain 0.01 -> 2e-5      (듀얼이 포화 대신 거래하게)
  tau_20260826     이동차 기준 속도 + 차로 차원 보정                  (tau 만, offset 은 꺼둠)
  tauoff_20260826  위 + offset 실시간 150s                           (tau 가 offset 을 살리는가)

셋 다 어댑터 **사본**이고 스위치는 config 에 있다. OFF 로 두면 default 와 비트 동일이
리플레이로 확인돼 있다(각 91/91).

기준선: 무제어 4808.1 (시드 13, sigma 50.7) · default_20260825 4723.9 (-84.2, 현 최선)

**tauoff 만 RW_OFFSET_WRITER=test_only 가 필요하다.** 러너 관문은 config 로 못 연다 —
안 세우면 plan_reject=OFFSET_NOT_PROMOTED 로 CSV 가 전량 거부되고 그 구간이 무제어로 돈다
(2026-08-25 에 한 번 당했다). 팔마다 세우고 지운다 — 다른 팔로 새면 대조가 깨진다.
#>
param(
  [string[]]$Only = @(),
  [int]$Seed = 13
)

$ErrorActionPreference = "Continue"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runner = Join-Path $repo "scripts\run_real_world_single_watchdog_distributed_core17legs4b.ps1"

# default_20260825 의 run_provenance 에서 그대로 가져온 값들이다. 하나라도 다르면 대조가 깨진다.
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

$arms = @(
  @{ Name = "dual_20260826"
     Adapter = "evaluation\controllers\vissim_stackelberg_adapter.py"
     Tuning  = "evaluation\configs\real_world_modi_pstack_distributed_core17legs4b_dual_20260826.json"
     Offset  = $false }
  @{ Name = "tau_20260826"
     Adapter = "evaluation\controllers\vissim_stackelberg_adapter.py"
     Tuning  = "evaluation\configs\canon_tau_20260827.json"
     Offset  = $false }
  @{ Name = "tauoff_20260826"
     Adapter = "evaluation\controllers\vissim_stackelberg_adapter.py"
     Tuning  = "evaluation\configs\real_world_modi_pstack_distributed_core17legs4b_tauoff_20260825.json"
     Offset  = $true }
)
if ($Only.Count -gt 0) { $arms = $arms | Where-Object { $Only -contains $_.Name } }

# default 런의 env 를 그대로 재현한다.
$env:RW_MAINLINE_SG_ONLY = "1"
$env:RW_PYTHON_EXE = "C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe"
# 이전 팔의 잔재가 새지 않게 비운다.
foreach ($v in @("RW_OFFSET_WRITER","RW_MOVING_SPEED","RW_LANE_DELAY_CORRECTION",
                 "RW_STOPPED_SPLIT","RW_MAINLINE_PLAN","RW_MAINLINE_SHARE_SG","RW_ADAPTER_MODE")) {
  Remove-Item "env:$v" -ErrorAction SilentlyContinue
}

foreach ($arm in $arms) {
  $name = $arm.Name
  $outDir = Join-Path $repo "evaluation\runs\$name"
  Write-Output "=========================================================="
  Write-Output ("[{0}] {1} 시작  offset_writer={2}" -f (Get-Date -Format "HH:mm:ss"), $name, $(if ($arm.Offset) { "test_only" } else { "(없음)" }))
  Write-Output "  adapter $($arm.Adapter)"
  Write-Output "  tuning  $($arm.Tuning)"

  if ($arm.Offset) { $env:RW_OFFSET_WRITER = "test_only" }
  else { Remove-Item "env:RW_OFFSET_WRITER" -ErrorAction SilentlyContinue }

  & $runner -Name $name -OutDir $outDir `
      -Adapter $arm.Adapter -Tuning $arm.Tuning `
      -Network $common.Network -VbsConfig $common.VbsConfig `
      -Calibration $common.Calibration -Mapping $common.Mapping `
      -Controller $common.Controller -SimPeriod $common.SimPeriod `
      -ControlIntervalSec $common.ControlIntervalSec `
      -StateLogIntervalSec $common.StateLogIntervalSec -Seed $common.Seed

  Remove-Item "env:RW_OFFSET_WRITER" -ErrorAction SilentlyContinue
  Write-Output ("[{0}] {1} 종료 (exit {2})" -f (Get-Date -Format "HH:mm:ss"), $name, $LASTEXITCODE)
}

Write-Output "=========================================================="
Write-Output "전 팔 종료. TTT:"
& $env:RW_PYTHON_EXE (Join-Path $repo "scripts\compare_runs_ttt.py") `
    default_20260825 nocontrol_s13_20260824 ($arms | ForEach-Object { $_.Name }) `
    --base nocontrol_s13_20260824
