<#
2026-08-26. offset **슬루 제한** 실런.

  slew15_20260826    결정당 offset 변경을 +-15 s (주기의 10%, 실무 short-way 한계)로
  slew7p5_20260826   +-7.5 s (5%, 보수적)

## 왜 — 신뢰영역은 이미 켜져 있었고, 틀린 기준점에 걸려 있었다

리더가 매 결정 `offset_marginal_price_trust_sec = cycle/8 = 18.75s` 를 세우고 후보 필터도
돈다(wu_faithful_follower.py:1815). 커밋 점프의 **중앙값도 정확히 18.75**(318회 중 177회)다.
그런데 43%가 그 정수배로 초과한다 — 37.5(77회) · 56.25(47회) · 75.0(11회).

원인: 기준점 `op_offset[s] = previous.offsets[s]`(stackelberg_wu_metered.py:1356)인데 리더가
**ADMM 반복마다 가격을 다시 계산해서**(:1365 `refresh = force or ...`) 기준점이 그 반복의
현재 iterate 로 갱신된다. 실측으로 리더 ref 와 직전 커밋이 **540 표본 중 207회(38%)**
어긋나고 최대 56.25s 차이다. 신뢰영역이 움직이는 기준점에 걸려 실효가 없다.

이 팔은 **커밋값을 직전 커밋 기준**으로 묶는다(short-way, 신호별 플랜 주기에서 원형).
자르는 자리는 action JSON 쓰기 직전의 `control.offsets` 다 — JSON 이 CSV 보다 **먼저**
써지므로 거기서 잘라야 JSON·CSV·다음 결정의 previous 가 전부 같은 값을 본다.
(첫 판은 CSV 쓰기 시점에 잘라서 JSON 이 안 잘렸고 레버 diff 가 0 으로 나왔다.)

## 리플레이 검증 (tauoff 실런 3결정)

    사본 OFF   레버 0/91 x 3                                   비트 동일
    slew15     clamped 9/11/9 · raw_max 56.25/75/56.25
               커밋 점프가 **전 신호에서 자기 주기 기준 정확히 15.00**
               (150 으로 재면 SC7 이 42 로 보이는데 그건 주기 123 을 150 으로 잰 측정 아티팩트다)

기준선: 무제어 4808.1 · default 4723.9 · **tau 4688.4(현 최선)** · tauoff 4778.7
판정: tauoff(4778.7)보다 좋아지면 전이비용이 범인. tau(4688.4)를 넘으면 offset 첫 순이득.

**RW_OFFSET_WRITER=test_only 가 필수다** — 러너 관문은 config 로 못 연다. 안 세우면
plan_reject=OFFSET_NOT_PROMOTED 로 CSV 전량 거부되고 그 구간이 무제어로 돈다.
#>
param(
  [string[]]$Only = @(),
  [int]$Seed = 13
)

$ErrorActionPreference = "Continue"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runner = Join-Path $repo "scripts\run_real_world_single_watchdog_distributed_core17legs4b.ps1"
$adapter = "evaluation\controllers\vissim_stackelberg_adapter.py"

# default_20260825 provenance 그대로. 하나라도 다르면 대조가 깨진다.
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

$arms = @("slew15_20260826","slew7p5_20260826")
if ($Only.Count -gt 0) { $arms = $arms | Where-Object { $Only -contains $_ } }

$env:RW_MAINLINE_SG_ONLY = "1"
$env:RW_PYTHON_EXE = "C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe"
foreach ($v in @("RW_MOVING_SPEED","RW_LANE_DELAY_CORRECTION","RW_NP_STATE_BAND",
                 "RW_STOPPED_SPLIT","RW_MAINLINE_PLAN","RW_MAINLINE_SHARE_SG","RW_ADAPTER_MODE")) {
  Remove-Item "env:$v" -ErrorAction SilentlyContinue
}

foreach ($name in $arms) {
  $tuning = "evaluation\configs\real_world_modi_pstack_distributed_core17legs4b_$name.json"
  if (-not (Test-Path (Join-Path $repo $tuning))) {
    Write-Output "!! config 없음, 건너뜀: $tuning"; continue
  }
  $outDir = Join-Path $repo "evaluation\runs\$name"
  Write-Output "=========================================================="
  Write-Output ("[{0}] {1} 시작  offset_writer=test_only" -f (Get-Date -Format "HH:mm:ss"), $name)
  $env:RW_OFFSET_WRITER = "test_only"
  & $runner -Name $name -OutDir $outDir -Adapter $adapter -Tuning $tuning `
      -Network $common.Network -VbsConfig $common.VbsConfig `
      -Calibration $common.Calibration -Mapping $common.Mapping `
      -Controller $common.Controller -SimPeriod $common.SimPeriod `
      -ControlIntervalSec $common.ControlIntervalSec `
      -StateLogIntervalSec $common.StateLogIntervalSec -Seed $common.Seed
  Remove-Item "env:RW_OFFSET_WRITER" -ErrorAction SilentlyContinue
  Write-Output ("[{0}] {1} 종료 (exit {2})" -f (Get-Date -Format "HH:mm:ss"), $name, $LASTEXITCODE)
}

Write-Output "=========================================================="
Write-Output "슬루 제한 TTT:"
& $env:RW_PYTHON_EXE (Join-Path $repo "scripts\compare_runs_ttt.py") `
    nocontrol_s13_20260824 default_20260825 tau_20260826 tauoff_20260826 `
    slew15_20260826 slew7p5_20260826 `
    --base nocontrol_s13_20260824
