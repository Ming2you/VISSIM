# 본선(freeway) 수요만 올려 임계밀도 초과를 만드는 no-control 탐침.
#
# 배경: 새 기준선(#8)에서 freeway 가 한 번도 임계밀도를 넘지 않았다
#   (신 rho_crit = 16.354, 세그먼트 평균 최대 13.0, 초과 비율 1.6~3.4%).
#   본선 유입은 no=1098(link 74, feeder) / no=1099(link 26, mainline) 둘뿐이고
#   peak 4620 vph(4차로 = 1155 vph/lane)로 적합 용량 4914 veh/h 바로 아래다.
#   균일 스케일은 도시부까지 올려 램프를 막고 본선 유입을 오히려 줄이므로,
#   역할별 배수 프로파일로 본선만 올린다.
#
# FD 적합의 용량 미식별(rho>20 표본 1952점 중 12점) 해소도 겸한다.

param(
  [string]$OutDir = "evaluation\runs\freeway_congestion_probe_20260802",
  [int]$WarmupSec = 900,
  [int]$EvalSec = 3600,
  [int]$ControlIntervalSec = 60,
  [int]$StateLogIntervalSec = 60,
  [int]$Seed = 13,
  [int]$StallSec = 900,
  [int]$MaxAttempts = 2
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$runner = Join-Path $repo "scripts\run_real_world_single_watchdog.ps1"
$profiles = Join-Path $repo "evaluation\configs\demand_profiles"
$simPeriod = $WarmupSec + $EvalSec

# 본선 부하 오름차순. 도시부 배수를 함께 적어 교란 정도를 명시한다.
$cases = @(
  @{ Tag = "breakdown"; Profile = "real_world_freeway_breakdown_20260724.csv"; Note = "mainline 1.90 / feeder 2.10 / urban 1.20" },
  @{ Tag = "lowurban";  Profile = "real_world_freeway_stress_lowurban_20260725.csv"; Note = "mainline 2.20 / feeder 2.45 / urban 0.85" },
  @{ Tag = "extreme";   Profile = "real_world_freeway_stress_extreme_20260725.csv"; Note = "mainline 2.65 / feeder 3.00 / urban 0.90" }
)

foreach ($c in $cases) {
  $name = "no_control_fw_$($c.Tag)_warm${WarmupSec}_eval${EvalSec}_seed$Seed"
  Write-Host "=== $name  ($($c.Note))"
  & $runner `
    -Name $name `
    -OutDir $OutDir `
    -SimPeriod $simPeriod `
    -ControlIntervalSec $ControlIntervalSec `
    -StateLogIntervalSec $StateLogIntervalSec `
    -Seed $Seed `
    -Controller "no-control" `
    -WarmupController "no-control" `
    -ControlStartSec -1 `
    -DemandScale 1.00 `
    -DemandProfile (Join-Path $profiles $c.Profile) `
    -StallSec $StallSec `
    -MaxAttempts $MaxAttempts
}

Write-Host "DONE freeway congestion probe -> $OutDir"
