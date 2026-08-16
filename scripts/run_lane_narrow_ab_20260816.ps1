<#
  RW_LANE_DELAY_CORRECTION / RW_NARROW_AXIS_SG 실런 A/B.

  2026-08-15 warmstart A/B 와 같은 틀이다 - 그 런이 발사 함정 넷을 전부 피한 형태라
  파라미터를 그대로 물려받는다.
    1. 게이트맵을 명시한다 (미지정이면 13.8% 조용한 오염)
    2. StallSec 2400 (300 이면 수요 스케일링 중 kill - COM 쓰기가 감시 파일을 안 건드린다)
    3. ControlStartSec 900 (-1 이면 warmup 이 없다)
    4. RW_ADAPTER_MODE 를 명시로 비운다 (부모 셸에서 누출된다)

  기준선을 새로 뜨는 이유: 오늘 커밋 769e0d8 이 정본 액추에이션 계획을 pedovrx 격자로
  재유도했고 SC1003 의 p2 녹색 예산이 23 s -> 69 s 로 바뀌었다. 8/15 A/B 의 arm 은
  기준선으로 쓸 수 없다.

  순서: 1차 질문(차로보정)이 먼저 끝나도록 base/lane 을 세 수요 모두 먼저 돌리고
  narrow/both 를 뒤에 둔다. 중간에 멈춰도 주 질문은 답이 나온다.
#>
param(
  [string]$OutDir = "evaluation\runs\lane_narrow_ab_20260816",
  [string]$Tag = "20260816",
  [int]$SimPeriod = 1800,
  [int]$ControlStartSec = 900,
  [int]$ControlIntervalSec = 60,
  [int]$Seed = 13,
  [int]$StallSec = 2400,
  [int]$MaxAttempts = 2,
  [string]$GateMap = "evaluation\real_world_modi_inventory\urban_input_gate_map_pedovr_20260814.csv",
  [double[]]$Demands = @(1.0, 0.75, 1.25),
  [string[]]$Arms = @("base", "lane", "narrow", "both"),
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

$armFlags = @{
  "base"   = @{ lane = "0"; narrow = "0" }
  "lane"   = @{ lane = "1"; narrow = "0" }
  "narrow" = @{ lane = "0"; narrow = "1" }
  "both"   = @{ lane = "1"; narrow = "1" }
}

# 1차 질문(차로보정)을 먼저 답하게 한다: base/lane 을 세 수요 모두 돈 뒤 narrow/both.
$primary = @("base", "lane") | Where-Object { $Arms -contains $_ }
$secondary = @("narrow", "both") | Where-Object { $Arms -contains $_ }
$plan = @()
foreach ($group in @($primary, $secondary)) {
  foreach ($d in $Demands) {
    foreach ($arm in $group) {
      $plan += [pscustomobject]@{ arm = $arm; demand = $d }
    }
  }
}

$absOut = Join-Path $repo $OutDir
if (-not (Test-Path $absOut)) { New-Item -ItemType Directory -Force -Path $absOut | Out-Null }
$progress = Join-Path $absOut "AB_PROGRESS.txt"

$total = $plan.Count
Write-Output "A/B 계획 $total 런 (한 런 약 75분 -> 약 $([math]::Round($total * 1.25, 1))시간)"
foreach ($p in $plan) { Write-Output ("  {0,-6} demand={1}" -f $p.arm, $p.demand) }
if ($DryRun) { Write-Output "DryRun - 발사하지 않는다"; return }

$index = 0
foreach ($p in $plan) {
  $index++
  $demandTag = ("d{0:000}" -f [int]([double]$p.demand * 100))
  $name = "{0}_{1}_{2}" -f $p.arm, $demandTag, $Tag

  $existing = Join-Path $absOut ("runlog_{0}.txt" -f $name)
  if (Test-Path $existing) {
    Write-Output "[$index/$total] SKIP $name (runlog 이미 있음)"
    continue
  }

  # 매 런마다 환경을 명시로 다시 세운다 - 이전 런의 값이 남지 않게 한다.
  #
  # RW_PYTHON 은 일부러 세우지 않는다. 러너의 인터프리터 후보 사다리
  # (run_real_world_stackelberg_controller.vbs:3962)가 RW_PYTHON 을 먼저 보고, 없으면
  # 현 환경에서 해석한다. 8/15 warmstart A/B·jam168_verify·오늘 스모크가 전부 그렇게
  # 해석된 같은 인터프리터로 돌았다. 시리즈 중간에 여기를 "고치면" 셀마다 인터프리터가
  # 갈려 A/B 가 깨진다. (예전 템플릿의 RW_PYTHON_EXE 는 VBS 내부 변수 이름이라 환경변수로는
  # 애초에 무효였다 - 지웠다.)
  $env:RW_WARMSTART_SEC = "900"
  $env:RW_ADAPTER_MODE = ""
  $env:RW_LANE_DELAY_CORRECTION = $armFlags[$p.arm].lane
  $env:RW_NARROW_AXIS_SG = $armFlags[$p.arm].narrow
  $env:RW_QUEUE_ORIGIN_FILTER = "0"
  $env:RW_VALIDATION_FIXED_SIGNAL = "0"
  $env:RW_RESTORE_RELEASE_BUFFERS = "off"

  $stamp = Get-Date -Format o
  $line = "[$index/$total] START $name  arm=$($p.arm) lane=$($env:RW_LANE_DELAY_CORRECTION) narrow=$($env:RW_NARROW_AXIS_SG) demand=$($p.demand)  $stamp"
  Write-Output $line
  Add-Content -Path $progress -Value $line -Encoding utf8

  $wdArgs = @(
    "-NoProfile", "-ExecutionPolicy", "Bypass",
    "-File", (Join-Path $repo "scripts\run_real_world_single_watchdog_distributed_pedovrx.ps1"),
    "-Name", $name,
    "-OutDir", $OutDir,
    "-SimPeriod", $SimPeriod,
    "-ControlIntervalSec", $ControlIntervalSec,
    "-ControlStartSec", $ControlStartSec,
    "-Controller", "stackelberg",
    "-WarmupController", "no-control",
    "-Seed", $Seed,
    "-StateLogIntervalSec", 5,
    "-DemandScale", $p.demand,
    "-UrbanInputGateMap", $GateMap,
    "-AuditAnchorsSec", "900,1500",
    "-StallSec", $StallSec,
    "-MaxAttempts", $MaxAttempts
  )

  $proc = Start-Process -FilePath "powershell.exe" -ArgumentList $wdArgs -NoNewWindow -Wait -PassThru
  $done = "[$index/$total] DONE  $name exit=$($proc.ExitCode)  $(Get-Date -Format o)"
  Write-Output $done
  Add-Content -Path $progress -Value $done -Encoding utf8

  if ($proc.ExitCode -ne 0) {
    # runlog 를 지운다. watchdog 이 시작할 때 이미 runlog 를 만들어 두므로, 그냥 두면
    # 위쪽 Test-Path SKIP 규칙에 걸려 **깨진 셀이 영구히 건너뛰어지고 조용히 비교에
    # 들어간다.** 실패한 셀은 흔적을 지워서 재실행이 실제로 다시 돌게 한다.
    Remove-Item -LiteralPath $existing -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath "$existing.err" -Force -ErrorAction SilentlyContinue
    $warn = "[$index/$total] 실패 - runlog 를 지웠다. 재실행하면 이 셀만 다시 돈다."
    Write-Output $warn
    Add-Content -Path $progress -Value $warn -Encoding utf8
  }
}

Write-Output "A/B 완료. 진행 로그: $progress"
