#Requires -Version 5.1
<#
N5 부모런 9개를 직렬로 돌린다 (pedovrx 격자).

**부모런은 no-control 이다.** 계획이 지정한 드라이버 run_plant_fidelity_matrix.ps1:123-124 가
Controller / WarmupController 를 둘 다 no-control 로 못 박고 이름도 fixed_nocontrol_ 로 붙인다.
부모런은 플랜트 기준선 궤적이고, anchor 는 거기서 갈라져 나가는 상태이며, N6 가 그 궤적에서
플랜트 파라미터를 적합한다. 제어를 켜면 궤적이 컨트롤러 모양으로 휘어 그 셋 다 무너진다.

**직렬인 이유.** 워치독의 Kill-Vissim 이 VISSIM200/VISSIM200CL/cscript 를 이름으로 전역 kill
한다. 병렬로 걸면 서로를 죽인다 - 2026-08-04 에 실제로 났던 사고다(context-notes.md:334).

**게이트맵을 반드시 명시로 넘긴다.** 비우면 러너가 urban_input_gate_map_20260811.csv 로
떨어지는데, 그 맵은 이 망의 도시 유입 3개(SC13 / SC1004 2개, 1,554 vph = 도시부의 13.8%)를
못 잡는다. 크래시도 경고도 없이 모델 쪽 유입만 0 이 되어 플랜트-모델 불일치가 조용히 생긴다.

**RW_ADAPTER_MODE 를 비운다.** pedovrx 워치독은 pedovr 에 있던 -AdapterMode 설정·원복을
잃었는데 러너는 아직 그 환경변수를 읽는다(run_real_world_stackelberg_controller.vbs:891).
호출 셸에 남아 있으면 9개 런의 재현성이 깨진다. no-control 이라 지금은 무해하지만 명시로 비운다.

이미 끝난 런은 건너뛴다 - 중간에 죽어도 다시 실행하면 이어서 간다.
#>
param(
  [string]$OutDir = "",
  [int]$SimPeriod = 3600,
  [int]$WarmupSec = 900,
  [int]$StateLogIntervalSec = 5,
  [string]$Tag = "n5parent_20260814",
  # 무진행 임계. 기본 300 초로는 **수요 스케일링 도중에 죽는다.**
  # 유입 34개 x 6구간 = 204회 COM 쓰기가 감시 파일을 하나도 안 건드리는데,
  # 러너 stdout 이 버퍼링돼 런로그 mtime 조차 안 움직이기 때문이다
  # (2026-08-15 실측: DEMAND_INTERVAL_SCHEDULE 직후 idle=306s 로 kill).
  [int]$StallSec = 1800,
  # 스모크: 첫 셀 하나만 짧게 돌려 수요 배율·게이트맵·처리량을 확인한다.
  [switch]$Smoke,
  [int]$SmokeSimPeriod = 300,
  [switch]$WhatIf
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ($OutDir -eq "") {
  $OutDir = if ($Smoke) {
    Join-Path $repo "evaluation\runs\n5_parent_smoke_20260814"
  } else {
    Join-Path $repo "evaluation\runs\n5_parent_20260814"
  }
}
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$watchdog = Join-Path $repo "scripts\run_real_world_single_watchdog_distributed_pedovrx.ps1"
$gateMap = "evaluation\real_world_modi_inventory\urban_input_gate_map_pedovr_20260814.csv"
$anchors = "900,1500,2100,2700"

# (role, demand, seed) - build_parent_run_spec.py 의 expand() 와 같은 순서다.
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

if ($Smoke) {
  # 배율이 1.0 이 아닌 셀을 고른다 - 검증하려는 것이 배율 적용이기 때문이다.
  $parents = @(@{ role = "smoke"; demand = 0.75; seed = 13 })
  $SimPeriod = $SmokeSimPeriod
  $WarmupSec = 0
}

function Get-RunName([hashtable]$p) {
  $d = [int]([math]::Round($p.demand * 100))
  return "{0}_{1}_d{2:d3}_s{3}" -f $Tag, $p.role, $d, $p.seed
}

# 완료 판정: 러너가 남기는 상태 CSV 가 있고 비어 있지 않으면 끝난 것으로 본다.
function Test-RunComplete([string]$name) {
  $state = Join-Path $OutDir "state_$name.csv"
  if (-not (Test-Path -LiteralPath $state -PathType Leaf)) { return $false }
  return (Get-Item -LiteralPath $state).Length -gt 0
}

$ledger = Join-Path $OutDir "n5_parent_ledger.csv"
if (-not (Test-Path -LiteralPath $ledger)) {
  "name,role,demand,seed,started_utc,finished_utc,exit_code,wall_min" |
    Out-File -FilePath $ledger -Encoding utf8
}

# 리더 탐색 폭이 호출 셸에서 새어 들어오지 않게 명시로 비운다.
$env:RW_ADAPTER_MODE = ""

$total = $parents.Count
$index = 0
foreach ($p in $parents) {
  $index += 1
  $name = Get-RunName $p
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
    "-Seed", $p.seed,
    "-StateLogIntervalSec", $StateLogIntervalSec,
    "-DemandScale", $p.demand,
    "-UrbanInputGateMap", $gateMap,
    "-AuditAnchorsSec", $anchors,
    "-StallSec", $StallSec,
    "-MaxAttempts", 3
  )

  if ($WhatIf) {
    Write-Output "[$index/$total] WOULD RUN: powershell $($wdArgs -join ' ')"
    continue
  }

  Write-Output "[$index/$total] START $name  demand=$($p.demand) seed=$($p.seed) sim=${SimPeriod}s  $(Get-Date -Format o)"
  $started = (Get-Date).ToUniversalTime().ToString("o")
  $sw = [System.Diagnostics.Stopwatch]::StartNew()
  $proc = Start-Process -FilePath "powershell.exe" -ArgumentList $wdArgs -NoNewWindow -Wait -PassThru
  $sw.Stop()
  $finished = (Get-Date).ToUniversalTime().ToString("o")
  $wall = [math]::Round($sw.Elapsed.TotalMinutes, 1)

  "{0},{1},{2},{3},{4},{5},{6},{7}" -f $name, $p.role, $p.demand, $p.seed, $started, $finished, $proc.ExitCode, $wall |
    Out-File -FilePath $ledger -Encoding utf8 -Append

  Write-Output "[$index/$total] DONE  $name exit=$($proc.ExitCode) wall=$wall min"
  if ($proc.ExitCode -ne 0) {
    Write-Output "[$index/$total] FAIL - 남은 런을 멈춘다. 로그: $(Join-Path $OutDir "runlog_$name.txt")"
    exit 1
  }
}

Write-Output "N5_PARENT_RUNS_COMPLETE ledger=$ledger"
