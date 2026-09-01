<#
2026-08-26. τ 신기록의 **짝지은 시드 재현**.

    tau_20260826  4688.4  vs  default_20260825  4723.9   ->  -35.5

시드 sigma 가 50.7(5시드 무제어 실측)이라 이 차이는 **비짝지음으로는 판정 불가**다.
같은 시드 짝지음만 유효하고, 지금은 시드 13 하나뿐이다. 논문 인용 전 필수 숙제다.

시드마다 **default 와 tau 를 둘 다** 돌려야 짝이 된다 — 무제어 s14~s17 은 있지만
default 는 s13 밖에 없다. 그래서 한 시드당 2런(약 3.2시간)이다.

시드 14 부터 채운다. 시간이 남으면 15, 16, 17 로 이어간다.

전부 default_20260825 / tau_20260825 config 그대로이고 **-Seed 만 다르다.**
#>
param(
  [int[]]$Seeds = @(14),
  [string[]]$Only = @()
)

$ErrorActionPreference = "Continue"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runner = Join-Path $repo "scripts\run_real_world_single_watchdog_distributed_core17legs4b.ps1"

$common = @{
  Network            = "network\real_world_gaepo_modi\modi_eval_userfix_20260814e.inpx"
  VbsConfig          = "evaluation\generated\real_world_modi_control_config_distributed_core17legs4b_mainline_20260825.vbs"
  Calibration        = "evaluation\calibration\real_world_prediction_calibration_core17legs4b_20260820.json"
  Mapping            = "evaluation\real_world_modi_control_distributed_20260728\control_mapping_distributed_core17legs4b_20260819.json"
  Controller         = "wu-link"
  SimPeriod          = 5400
  ControlIntervalSec = 150
  StateLogIntervalSec= 30
}

# 짝의 두 쪽. 같은 시드에서 둘 다 있어야 한 점이 생긴다.
$pair = @(
  @{ Key = "default"
     Adapter = "evaluation\controllers\vissim_stackelberg_adapter.py"
     Tuning  = "evaluation\configs\real_world_modi_pstack_distributed_core17legs4b_default_20260825.json" }
  @{ Key = "tau"
     Adapter = "evaluation\controllers\vissim_stackelberg_adapter.py"
     Tuning  = "evaluation\configs\canon_tau_20260827.json" }
)

$env:RW_MAINLINE_SG_ONLY = "1"
$env:RW_PYTHON_EXE = "C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe"
foreach ($v in @("RW_OFFSET_WRITER","RW_MOVING_SPEED","RW_LANE_DELAY_CORRECTION","RW_NP_STATE_BAND",
                 "RW_STOPPED_SPLIT","RW_MAINLINE_PLAN","RW_MAINLINE_SHARE_SG","RW_ADAPTER_MODE")) {
  Remove-Item "env:$v" -ErrorAction SilentlyContinue
}

$done = @()
foreach ($seed in $Seeds) {
  foreach ($side in $pair) {
    $name = "{0}_s{1}_20260826" -f $side.Key, $seed
    if ($Only.Count -gt 0 -and -not ($Only -contains $name)) { continue }
    $outDir = Join-Path $repo "evaluation\runs\$name"
    if (Test-Path (Join-Path $outDir ("state_{0}.csv" -f $name))) {
      Write-Output "이미 있음, 건너뜀: $name"; $done += $name; continue
    }
    Write-Output "=========================================================="
    Write-Output ("[{0}] {1} 시작  seed={2}" -f (Get-Date -Format "HH:mm:ss"), $name, $seed)
    & $runner -Name $name -OutDir $outDir -Adapter $side.Adapter -Tuning $side.Tuning `
        -Network $common.Network -VbsConfig $common.VbsConfig `
        -Calibration $common.Calibration -Mapping $common.Mapping `
        -Controller $common.Controller -SimPeriod $common.SimPeriod `
        -ControlIntervalSec $common.ControlIntervalSec `
        -StateLogIntervalSec $common.StateLogIntervalSec -Seed $seed
    Write-Output ("[{0}] {1} 종료 (exit {2})" -f (Get-Date -Format "HH:mm:ss"), $name, $LASTEXITCODE)
    $done += $name
  }
}

Write-Output "=========================================================="
Write-Output "짝지은 시드 TTT (같은 시드끼리만 비교해라):"
& $env:RW_PYTHON_EXE (Join-Path $repo "scripts\compare_runs_ttt.py") `
    nocontrol_s13_20260824 default_20260825 tau_20260826 $done `
    --base nocontrol_s13_20260824
