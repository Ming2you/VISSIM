#Requires -Version 5.1
<#
N5 의 base replay 를 돌린다.

## base replay 가 무엇인가

**같은 것을 그대로 다시 돌리는 것**이다 - 같은 .inpx, 같은 시드, 같은 수요 배율, 같은
no-control 설정. 시드를 바꾸지 않는다. eps_J_vissim 은 수요 실현 분산이 아니라 VISSIM
**재현성**의 잡음 바닥이고, 하한이 1e-6 veh·h 인 것이 그 증거다(J 는 수천 veh·h 규모다).
자세한 근거는 scripts/measure_eps_j_vissim.py 의 모듈 주석에 있다.

계획 N9-1 이 스냅샷 복원을 금지하고 모든 branch 를 t=0 부터 재실행하도록 못 박았다.
그래서 여기도 anchor 에서 재개하지 않고 t=0 부터 통째로 다시 돈다 - 러너에 상태를
읽어 들이는 경로 자체가 없다(anchor_<sec>.json 은 쓰기 전용이다).

## 왜 부모-anchor 당이 아니라 부모당 20회인가

한 번의 replay 가 anchor 4개의 J 를 전부 준다. J 는 [anchor, 런 끝] 구간의 TTT 적분이라
같은 상태 시계열에서 창만 다르게 잘라내면 된다. 그래서 9 x 4 x 20 = 720 회가 아니라
9 x 20 = 180 회다. 표본 수는 계획이 요구한 그대로 부모-anchor 당 20 개다.

**부모런 자체가 replay 1 번이다.** 무섭동 no-control 이라 정의상 base arm 이다.
그래서 부모당 19 회만 추가로 돈다.

## 쓰는 법

    # 파일럿 - 한 셀만 3회(부모 포함) 재현성 확인
    scripts\run_n5_base_replays.ps1 -Only training_d075_s13 -Replays 3

    # 본작업 - 9셀 x 20회
    scripts\run_n5_base_replays.ps1 -Replays 20

VISSIM 은 한 번에 하나만 돈다(Kill-Vissim 이 전역 kill). 이미 끝난 replay 는 건너뛴다.
#>
param(
  [string]$OutDir = "",
  [int]$SimPeriod = 3600,
  [int]$WarmupSec = 900,
  [int]$StateLogIntervalSec = 5,
  [string]$Tag = "n5parent_20260814",
  [int]$Replays = 20,
  # 특정 셀만 돌린다. 예: training_d075_s13. 비우면 9셀 전부.
  [string]$Only = "",
  [int]$StallSec = 1800,
  [switch]$WhatIf
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ($OutDir -eq "") { $OutDir = Join-Path $repo "evaluation\runs\n5_parent_20260814" }
if (-not (Test-Path -LiteralPath $OutDir -PathType Container)) {
  throw "OutDir 가 없다: $OutDir  (부모런을 먼저 돌려라)"
}

$watchdog = Join-Path $repo "scripts\run_real_world_single_watchdog_distributed_pedovrx.ps1"
$gateMap = "evaluation\real_world_modi_inventory\urban_input_gate_map_pedovr_20260814.csv"
$anchors = "900,1500,2100,2700"

$parents = @(
  @{ role = "training";  demand = 0.75; seed = 13 },
  @{ role = "training";  demand = 0.75; seed = 29 },
  @{ role = "training";  demand = 1.00; seed = 13 },
  @{ role = "training";  demand = 1.00; seed = 29 },
  @{ role = "congested"; demand = 1.25; seed = 13 },
  @{ role = "congested"; demand = 1.25; seed = 29 },
  @{ role = "holdout";   demand = 0.75; seed = 47 },
  @{ role = "holdout";   demand = 1.00; seed = 47 },
  @{ role = "holdout";   demand = 1.25; seed = 47 }
)

function Get-ParentName([hashtable]$p) {
  $d = [int]([math]::Round($p.demand * 100))
  return "{0}_{1}_d{2:d3}_s{3}" -f $Tag, $p.role, $d, $p.seed
}

function Test-RunComplete([string]$name) {
  $state = Join-Path $OutDir "state_$name.csv"
  if (-not (Test-Path -LiteralPath $state -PathType Leaf)) { return $false }
  return (Get-Item -LiteralPath $state).Length -gt 0
}

if ($Only -ne "") {
  $parents = @($parents | Where-Object { (Get-ParentName $_) -like "*$Only*" })
  if ($parents.Count -eq 0) { throw "-Only '$Only' 에 맞는 셀이 없다" }
}

$ledger = Join-Path $OutDir "n5_base_replay_ledger.csv"
if (-not (Test-Path -LiteralPath $ledger)) {
  "name,parent,replay_index,demand,seed,started_utc,finished_utc,exit_code,wall_min" |
    Out-File -FilePath $ledger -Encoding utf8
}

$env:RW_ADAPTER_MODE = ""

# 부모런이 replay 1 이므로 2..N 만 돈다.
$plan = @()
foreach ($p in $parents) {
  $parent = Get-ParentName $p
  if (-not (Test-RunComplete $parent)) {
    Write-Output "SKIP-CELL $parent (부모런이 아직 없다)"
    continue
  }
  for ($k = 2; $k -le $Replays; $k++) {
    $plan += @{ parent = $parent; index = $k; demand = $p.demand; seed = $p.seed }
  }
}

$total = $plan.Count
Write-Output "base replay 계획: $total 회 (셀 $($parents.Count)개 x $($Replays - 1)회, 부모런이 1번)"

$index = 0
foreach ($job in $plan) {
  $index += 1
  $name = "{0}_r{1:d2}" -f $job.parent, $job.index
  if (Test-RunComplete $name) {
    Write-Output "[$index/$total] SKIP $name (이미 끝남)"
    continue
  }

  $wdArgs = @(
    "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $watchdog,
    "-Name", $name,
    "-OutDir", $OutDir,
    "-SimPeriod", $SimPeriod,
    "-ControlIntervalSec", 60,
    "-ControlStartSec", $WarmupSec,
    "-Controller", "no-control",
    "-WarmupController", "no-control",
    "-Seed", $job.seed,
    "-StateLogIntervalSec", $StateLogIntervalSec,
    "-DemandScale", $job.demand,
    "-UrbanInputGateMap", $gateMap,
    "-AuditAnchorsSec", $anchors,
    "-StallSec", $StallSec,
    "-MaxAttempts", 3
  )

  if ($WhatIf) {
    Write-Output "[$index/$total] WOULD RUN $name"
    continue
  }

  Write-Output "[$index/$total] START $name  $(Get-Date -Format o)"
  $started = (Get-Date).ToUniversalTime().ToString("o")
  $sw = [System.Diagnostics.Stopwatch]::StartNew()
  $proc = Start-Process -FilePath "powershell.exe" -ArgumentList $wdArgs -NoNewWindow -Wait -PassThru
  $sw.Stop()
  $finished = (Get-Date).ToUniversalTime().ToString("o")
  $wall = [math]::Round($sw.Elapsed.TotalMinutes, 1)

  "{0},{1},{2},{3},{4},{5},{6},{7},{8}" -f $name, $job.parent, $job.index, $job.demand, $job.seed, $started, $finished, $proc.ExitCode, $wall |
    Out-File -FilePath $ledger -Encoding utf8 -Append

  Write-Output "[$index/$total] DONE  $name exit=$($proc.ExitCode) wall=$wall min"
  if ($proc.ExitCode -ne 0) {
    Write-Output "[$index/$total] FAIL - 멈춘다. 로그: $(Join-Path $OutDir "runlog_$name.txt")"
    exit 1
  }
}

Write-Output "N5_BASE_REPLAYS_COMPLETE ledger=$ledger"
