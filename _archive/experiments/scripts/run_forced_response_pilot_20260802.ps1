# 강제응답 그리드 사전 파일럿 - 파생 수요 네트워크 2종에서 무제어로 혼잡 발생 여부와 런타임을 잰다.
# 목적: (i) 분석창 900~4500 s 에서 rho_crit=16.354 초과가 지속되는지,
#       (ii) StateLogIntervalSec=10 의 런타임 비용이 얼마인지.
param(
  [string]$OutDir = "evaluation\runs\forced_response_pilot_20260802",
  [int]$WarmupSec = 900,
  [int]$EvalSec = 3600,
  [int]$StateLogIntervalSec = 10,
  [int]$Seed = 13,
  [int]$StallSec = 900
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$runner = Join-Path $repo "scripts\run_real_world_single_watchdog.ps1"
$netDir = Join-Path $repo "network\real_world_gaepo_modi"
$tuning = Join-Path $repo "evaluation\configs\real_world_modi_pstack_flagship_segvsl_fdrefit_20260802.json"
$calib = Join-Path $repo "evaluation\calibration\real_world_modi_control_v2_fdrefit_20260802.json"
$simPeriod = $WarmupSec + $EvalSec

$cases = @(
  @{ Tag = "fw100"; Net = "modi_eval_rw_fr_fw100_20260802.inpx" },
  @{ Tag = "fw125"; Net = "modi_eval_rw_fr_fw125_20260802.inpx" }
)

foreach ($c in $cases) {
  $name = "no_control_$($c.Tag)_warm${WarmupSec}_eval${EvalSec}_seed$Seed"
  Write-Host "=== $name net=$($c.Net)"
  & $runner `
    -Name $name `
    -Network (Join-Path $netDir $c.Net) `
    -OutDir $OutDir `
    -SimPeriod $simPeriod `
    -ControlIntervalSec 60 `
    -StateLogIntervalSec $StateLogIntervalSec `
    -Seed $Seed `
    -Controller "no-control" `
    -WarmupController "no-control" `
    -ControlStartSec -1 `
    -Tuning $tuning `
    -Calibration $calib `
    -DemandScale 1.00 `
    -StallSec $StallSec `
    -MaxAttempts 2
}

Write-Host "PILOT_DONE"
