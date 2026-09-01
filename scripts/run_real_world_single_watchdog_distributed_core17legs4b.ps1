<#
Run one real-world Gaepo modi VISSIM controller case with a no-progress watchdog.

Progress is the newest mtime among the run log, state CSV, action CSV, and
decision action JSONs. If nothing moves for StallSec seconds, cscript/VISSIM are
killed and the case is retried up to MaxAttempts.
#>
# 위치인자 바인딩을 끈다. 호출자가 실수로 위치인자를 흘리면(예: 문자열 splat —
# `@("-ForceStepwise")` 가 String 으로 언롤돼 문자 14개로 쪼개진 2026-09-01 사고)
# 파라미터가 조용히 밀리는 대신 즉시 죽는다. 호출부 42곳 전부가 명명인자라 회귀 위험이 없다.
[CmdletBinding(PositionalBinding=$false)]
param(
  [Parameter(Mandatory=$true)][string]$Name,
  # 어댑터 경로. 비우면 정본을 쓴다. 실험용 사본을 돌릴 때만 넘긴다 —
  # 기본값이 정본이라 안 넘기면 기존 호출과 완전히 같다.
  [string]$Adapter = "",
  [string]$Network = "",
  [string]$OutDir = "",
  [int]$SimPeriod = 1800,
  [int]$ControlIntervalSec = 60,
  [int]$Seed = 13,
  [string]$Controller = "stackelberg",
  [string]$Tuning = "",
  [string]$Calibration = "",
  [string]$Mapping = "",
  [string]$VbsConfig = "",
  [int]$ControlStartSec = -1,
  [string]$WarmupController = "no-control",
  [int]$StateLogIntervalSec = 30,
  [double]$DemandScale = 1.0,
  [string]$DemandProfile = "",
  [string]$VehicleInputRoles = "",
  [int]$IncidentLink = 0,
  [int]$IncidentLane = 0,
  [double]$IncidentPos = -1.0,
  [int]$IncidentStartSec = -1,
  [int]$IncidentEndSec = -1,
  [string]$IncidentName = "",
  # 도시 유입 게이트 맵. 격자 leg 방위에서 유도되므로 leg 을 고치면 같이 움직인다.
  # 2026-08-19: 비워두면 러너 VBS 가 8방위 시절 기본값(urban_input_gate_map_20260811.csv)으로
  # 떨어지고, 그 대장의 in_SC9001_S 를 core17legs4b config 가 몰라서 어댑터가 ValueError 로
  # 런을 세운다(vissim_stackelberg_adapter.py:3120). legs4b 대장을 기본값으로 박는다.
  [string]$UrbanInputGateMap = "evaluation\real_world_modi_inventory\urban_input_gate_map_legs4b_20260819.csv",
  [switch]$ForceStepwise,
  [int]$StallSec = 300,
  [int]$MaxAttempts = 3,
  [int]$DoneRows = 0,
  [string]$AuditAnchorsSec = ""
)

$ErrorActionPreference = "Continue"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
function Resolve-RepoPath([string]$PathValue) {
  if ($PathValue -eq "") { return "" }
  if ([System.IO.Path]::IsPathRooted($PathValue)) {
    return [System.IO.Path]::GetFullPath($PathValue)
  }
  return [System.IO.Path]::GetFullPath((Join-Path $repo $PathValue))
}

if ($OutDir -eq "") {
  $OutDir = Join-Path $repo "evaluation\runs\real_world_modi_watchdog"
}
$OutDir = Resolve-RepoPath $OutDir
# 2026-08-27. -Tuning 기본값을 없앤다. 종전 기본값
# (real_world_modi_pstack_distributed_core17legs4b_20260819.json) 은 정본 통합 때
# 격리 폴더로 옮겨져 더는 존재하지 않는다. 그런데 어댑터의 load_optional_json 은
# 없는 경로에서 조용히 {} 를 돌려주므로, -Tuning 을 빠뜨리면 **무설정 런이 정상
# 종료**하고 TTT 만 다르게 나온다. 시끄럽게 죽는 편이 낫다.
if ($Tuning -eq "") {
  Write-Output "!! -Tuning 이 필요하다. 정본: evaluation/configs/canon_{tau,bstoA,plantfix,fdfit}_20260827.json"
  exit 2
}
$Tuning = Resolve-RepoPath $Tuning
if (-not (Test-Path $Tuning)) {
  Write-Output ("!! -Tuning 파일이 없다: {0}" -f $Tuning)
  exit 2
}
if ($Calibration -eq "") {
  $Calibration = Join-Path $repo "evaluation\calibration\real_world_prediction_calibration_core17legs4b_20260820.json"
}
$Calibration = Resolve-RepoPath $Calibration
if ($Mapping -eq "") {
  $Mapping = Join-Path $repo "evaluation\real_world_modi_control_distributed_20260728\control_mapping_distributed_core17legs4b_20260819.json"
}
$Mapping = Resolve-RepoPath $Mapping
if ($VehicleInputRoles -eq "") {
  $VehicleInputRoles = Join-Path $repo "evaluation\real_world_modi_inventory\vehicle_input_roles.csv"
}
$VehicleInputRoles = Resolve-RepoPath $VehicleInputRoles
if ($DemandProfile -ne "") {
  $DemandProfile = Resolve-RepoPath $DemandProfile
}
if ($ControlIntervalSec -le 0 -or ($ControlIntervalSec % 10) -ne 0) {
  throw "ControlIntervalSec must be a positive multiple of the 10s ramp-meter cycle. Got $ControlIntervalSec."
}
if ($StateLogIntervalSec -le 0) {
  throw "StateLogIntervalSec must be positive. Got $StateLogIntervalSec."
}

$runner = Join-Path $repo "scripts\run_real_world_stackelberg_controller.vbs"
if ($Network -eq "") {
  $Network = Join-Path $repo "network\real_world_gaepo_modi\modi_eval_rw_control.inpx"
}
$net = Resolve-RepoPath $Network
if ($Adapter) { $adapter = Resolve-RepoPath $Adapter }
else { $adapter = Join-Path $repo "evaluation\controllers\vissim_stackelberg_adapter.py" }
# VBS generated config (positional arg 14). This carries RW_LOCAL_OBSERVABLE_LINKS and
# RW_DETECTOR_MAPPING_PATH, i.e. WHAT THE PLANT RECORDS into state_*.json local_observation.
# 2026-08-04: this was hardcoded to the base config while grids passed a distributed
# -Mapping. Result: the plant logged only 22 observable links (base) while G6 scoring
# projected with the distributed 175-link detector mapping, so 153 links had no data and
# the observed objective captured 1.4% of urban vehicles. Every urban-axis candidate was
# then scored with the wrong sign. Default keeps the old path = bit-identical.
# 2026-08-25: 기본값을 **본선 전용 계획** 형제를 가진 사본으로 옮긴다.
#
# 러너는 sgplan 을 이 파일의 형제(<config>_sgplan.vbs)로 찾는다. 옛 형제는 액추에이션
# 계획의 현시 그룹에 **미드블록 SG(9+)를 함께 넣은** 판이라, 그 축이 미드블록 창으로
# 잡혀 본선 SG 창이 분율로 깎였다 - SC5 p1 은 axis 97(SG20 창) 기준 43/97 = 0.4433 이라
# 컨트롤러가 54.5초를 주문해도 본선에 24.2초만 배달됐다(1초 되읽기 12주기 실측).
#
# 러너는 RW_MAINLINE_SG_ONLY=1 로 이미 sg<=8 만 COM 으로 몰고 미드블록엔 ContrByCOM 조차
# 안 건다(:1827-1833). 계획만 아직 미드블록을 현시에 넣고 있었다. 본선만 보면 이미
# 완전한 4현시 순차다(SC5 43+23+47+25 = 138 = 모델 예산, +4x3s 황색 = 150 = 주기).
#
# 실측: mainline_20260825 = 4723.9 (무제어 4808.1 대비 -84.2). 같은 스택에서 옛 계획을
# 쓴 allfix_20260825 는 4783.9 였다 - **이 한 줄이 -60.0 이다.**
#
# 무제어 기준선은 영향을 받지 않는다 - nocontrol 런은 signal/signal_sg 행을 하나도 쓰지
# 않고 VISSIM native 프로그램이 그대로 돈다(실측 확인: vsl 71 + ramp_meter 8 행뿐).
#
# 옛 계획으로 되돌리려면 -VbsConfig 로 ..._core17legs4b_20260819.vbs 를 넘기면 된다.
if ($VbsConfig -eq "") {
  $VbsConfig = Join-Path $repo "evaluation\generated\real_world_modi_control_config_distributed_core17legs4b_mainline_20260825.vbs"
}
$vbsConfig = Resolve-RepoPath $VbsConfig
if (-not (Test-Path $vbsConfig)) { Log "ERROR vbs config not found: $vbsConfig"; exit 2 }

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$progress = Join-Path $OutDir "WATCHDOG_PROGRESS.txt"

function Log($m) {
  $line = ("{0}  {1}" -f (Get-Date -Format "MM-dd HH:mm:ss"), $m)
  for ($r = 0; $r -lt 5; $r++) {
    try { [System.IO.File]::AppendAllText($progress, $line + "`r`n"); break }
    catch { Start-Sleep -Milliseconds 200 }
  }
  Write-Host $line
}

function Kill-Vissim {
  Get-Process -Name "VISSIM200","VISSIM200CL","cscript" -ErrorAction SilentlyContinue |
    Stop-Process -Force -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 3
}

function Clear-DecisionDir([string]$Dir) {
  if (-not (Test-Path $Dir)) {
    New-Item -ItemType Directory -Force -Path $Dir | Out-Null
    return
  }
  Get-ChildItem -LiteralPath $Dir -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -like "action_*.json" -or $_.Name -like "action_*.csv" -or $_.Name -like "state_*.json" } |
    Remove-Item -Force -ErrorAction SilentlyContinue
}

function Normalize-ProcessPathEnv {
  $pathValue = [Environment]::GetEnvironmentVariable("Path", "Process")
  if ([string]::IsNullOrWhiteSpace($pathValue)) {
    $pathValue = [Environment]::GetEnvironmentVariable("PATH", "Process")
  }
  [Environment]::SetEnvironmentVariable("PATH", $null, "Process")
  [Environment]::SetEnvironmentVariable("Path", $null, "Process")
  if (-not [string]::IsNullOrWhiteSpace($pathValue)) {
    [Environment]::SetEnvironmentVariable("Path", $pathValue, "Process")
  }
}

function Q($s) { '"' + $s + '"' }

function Get-ArtifactEvidence([string]$ArtifactPath) {
  $exists = -not [string]::IsNullOrWhiteSpace($ArtifactPath) -and (Test-Path -LiteralPath $ArtifactPath -PathType Leaf)
  [ordered]@{
    path = $ArtifactPath
    exists = $exists
    sha256 = if ($exists) { (Get-FileHash -LiteralPath $ArtifactPath -Algorithm SHA256).Hash.ToLowerInvariant() } else { "" }
  }
}

function Get-ExactGitCommit([string]$RepositoryPath) {
  if ([string]::IsNullOrWhiteSpace($RepositoryPath) -or -not (Test-Path -LiteralPath $RepositoryPath -PathType Container)) {
    return ""
  }
  $topLevel = (& git -C $RepositoryPath rev-parse --show-toplevel 2>$null)
  if ([string]::IsNullOrWhiteSpace($topLevel)) { return "" }
  $expected = [System.IO.Path]::GetFullPath($RepositoryPath).TrimEnd('\')
  $actual = [System.IO.Path]::GetFullPath(([string]$topLevel).Trim()).TrimEnd('\')
  if (-not $expected.Equals($actual, [System.StringComparison]::OrdinalIgnoreCase)) { return "" }
  return [string](& git -C $RepositoryPath rev-parse HEAD 2>$null)
}

function Copy-VissimError([string]$DestinationDir) {
  $vissimErr = [System.IO.Path]::ChangeExtension($net, ".err")
  if (Test-Path -LiteralPath $vissimErr -PathType Leaf) {
    Copy-Item -LiteralPath $vissimErr -Destination (Join-Path $DestinationDir "vissim_network.err") `
      -Force -ErrorAction SilentlyContinue
  }
}

$stateCsv = Join-Path $OutDir "state_$Name.csv"
$actionCsv = Join-Path $OutDir "action_$Name.csv"
$bottleneckLinkCsv = Join-Path $OutDir "bottleneck_links_$Name.csv"
$bottleneckSegmentCsv = Join-Path $OutDir "bottleneck_segments_$Name.csv"
$decisionDir = Join-Path $OutDir "decisions_$Name"
$log = Join-Path $OutDir "runlog_$Name.txt"
New-Item -ItemType Directory -Force -Path $decisionDir | Out-Null
$runId = [guid]::NewGuid().ToString("N")

$provenanceFiles = [ordered]@{
  network = Get-ArtifactEvidence $net
  main_vbs_runner = Get-ArtifactEvidence $runner
  watchdog_wrapper = Get-ArtifactEvidence $PSCommandPath
  adapter = Get-ArtifactEvidence $adapter
  calibration = Get-ArtifactEvidence $Calibration
  tuning = Get-ArtifactEvidence $Tuning
  control_mapping = Get-ArtifactEvidence $Mapping
  generated_vbs_config = Get-ArtifactEvidence $vbsConfig
  vehicle_input_roles = Get-ArtifactEvidence $VehicleInputRoles
  # 2026-08-19: provenance 가 2026-08-05 세대를 해시하고 있었다. core17legs4b 정본으로 옮긴다.
  # 링크 배정은 권역 정본이 대신한다 - 그것이 이 세대의 배정이다.
  link_assignment = Get-ArtifactEvidence (Join-Path $repo "outputs\urban_player_territory_v1_20260819.json")
  intersection_adjacency = Get-ArtifactEvidence (Join-Path $repo "outputs\intersection_adjacency_core17legs4b_20260819.json")
  storage_capacity = Get-ArtifactEvidence (Join-Path $repo "outputs\urban_storage_capacity_core17legs4b_20260819.json")
  pn_boundary_turns = Get-ArtifactEvidence (Join-Path $repo "outputs\pn_boundary_turns_v1_20260819.json")
  numsim_snapshot = Get-ArtifactEvidence (Join-Path $repo "vendor\NumSim-mine\SNAPSHOT.md")
}
$signalPrograms = @(
  Get-ChildItem -LiteralPath ([System.IO.Path]::GetDirectoryName($net)) -Filter "*.sig" -File -ErrorAction SilentlyContinue |
    Sort-Object Name |
    ForEach-Object { Get-ArtifactEvidence $_.FullName }
)
$workspaceCommit = Get-ExactGitCommit $repo
$numsimRootEnv = [Environment]::GetEnvironmentVariable("NUMSIM_REPO_ROOT", "Process")
$numsimRoot = $numsimRootEnv
if ([string]::IsNullOrWhiteSpace($numsimRoot)) {
  $numsimRoot = Join-Path $repo "vendor\NumSim-mine"
}
$provenanceFiles.numsim_default_yaml = Get-ArtifactEvidence (Join-Path $numsimRoot "src\config\default.yaml")
$numsimCommit = ""
if (-not [string]::IsNullOrWhiteSpace($numsimRoot) -and (Test-Path -LiteralPath $numsimRoot)) {
  $numsimCommit = Get-ExactGitCommit $numsimRoot
}
$numsimSnapshotCommit = ""
$numsimSnapshotPath = Join-Path $numsimRoot "SNAPSHOT.md"
if (Test-Path -LiteralPath $numsimSnapshotPath -PathType Leaf) {
  $match = [regex]::Match([System.IO.File]::ReadAllText($numsimSnapshotPath), "(?<![0-9a-f])[0-9a-f]{7,40}(?![0-9a-f])", "IgnoreCase")
  if ($match.Success) { $numsimSnapshotCommit = $match.Value }
}
# 거동을 바꾸는 RW_* 환경변수를 provenance 에 남긴다.
#
# 왜. 이 러너는 RW_FORCE_STEPWISE / RW_AUDIT_ANCHORS_SEC / RW_RUN_ID / RW_RUN_MANIFEST_PATH
# 넷만 저장·설정·원복하고 나머지는 **부모 셸에서 그대로 상속**한다. 그런데 어댑터와 VBS 가
# 읽는 RW_* 는 그보다 훨씬 많고(RW_ADAPTER_MODE · RW_STOPPED_SPLIT · RW_SUBWINDOW_SERVICE ·
# RW_NARROW_AXIS_SG · RW_MAINLINE_SG_ONLY · RW_QUEUE_ORIGIN_FILTER · RW_OFFSET_WRITER ...),
# 그것들이 실런 기록에 **한 줄도 안 남았다**. 팔끼리 비교할 때 무엇이 켜져 있었는지
# 사후에 알 방법이 없다 - 논문 재현성에 직접 걸린다.
#
# 순수 추가다. 값을 바꾸지 않고 적기만 한다.
$rwEnv = [ordered]@{}
foreach ($e in (Get-ChildItem Env: | Where-Object { $_.Name -like "RW_*" } | Sort-Object Name)) {
  $rwEnv[$e.Name] = [string]$e.Value
}
# RW_ADAPTER_MODE 는 tuning 뒤에 적용돼 설정의 leader_candidate_count / max_nash_iter 를
# 조용히 덮어쓴다(fuller-smoke = 9->5 / 4->2). 켜져 있으면 크게 알린다.
if (-not [string]::IsNullOrWhiteSpace($env:RW_ADAPTER_MODE)) {
  Log "WARNING $Name RW_ADAPTER_MODE=$($env:RW_ADAPTER_MODE) - tuning 의 탐색 예산을 덮어쓴다. 의도한 것이 아니면 지우고 다시 돌려라."
}
$provenance = [ordered]@{
  schema_version = 1
  run_id = $runId
  name = $Name
  created_at = (Get-Date).ToString("o")
  workspace_root = $repo
  workspace_git_commit = [string]$workspaceCommit
  numsim_repo_root_env = [string]$numsimRootEnv
  numsim_repo_root_effective = [string]$numsimRoot
  numsim_git_commit = [string]$numsimCommit
  numsim_snapshot_commit = [string]$numsimSnapshotCommit
  seed = $Seed
  sim_period_sec = $SimPeriod
  control_interval_sec = $ControlIntervalSec
  state_log_interval_sec = $StateLogIntervalSec
  demand_scale = $DemandScale
  demand_profile = $DemandProfile
  controller = $Controller
  audit_anchors_sec = $AuditAnchorsSec
  env = $rwEnv
  files = $provenanceFiles
  signal_programs = $signalPrograms
}
$provenancePath = Join-Path $OutDir "run_provenance_$Name.json"
[System.IO.File]::WriteAllText(
  $provenancePath,
  ($provenance | ConvertTo-Json -Depth 8),
  [System.Text.UTF8Encoding]::new($false)
)

function Archive-AttemptOutputs([int]$Attempt) {
  $archive = Join-Path $OutDir ("attempt_{0:00}_{1}" -f $Attempt, $Name)
  New-Item -ItemType Directory -Force -Path $archive | Out-Null
  foreach ($path in @($stateCsv, $actionCsv, $bottleneckLinkCsv, $bottleneckSegmentCsv, $log, "$log.err")) {
    if (Test-Path $path) {
      Copy-Item -LiteralPath $path -Destination (Join-Path $archive ([System.IO.Path]::GetFileName($path))) -Force -ErrorAction SilentlyContinue
    }
  }
  if (Test-Path $decisionDir) {
    $decisionArchive = Join-Path $archive ([System.IO.Path]::GetFileName($decisionDir))
    Copy-Item -LiteralPath $decisionDir -Destination $decisionArchive -Recurse -Force -ErrorAction SilentlyContinue
  }
  Copy-VissimError $archive
}

if ($DoneRows -gt 0 -and (Test-Path $stateCsv)) {
  $rows = (Get-Content $stateCsv | Measure-Object -Line).Lines
  if ($rows -ge $DoneRows) {
    Log "SKIP $Name rows=$rows"
    exit 0
  }
}

for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
  Kill-Vissim
  Clear-DecisionDir $decisionDir
  $argline = "//nologo " + (Q $runner) + " " + (Q $net) + " " + (Q $stateCsv) + " " + (Q $actionCsv) + " " + (Q $decisionDir) +
    " $SimPeriod $ControlIntervalSec $Seed " + (Q $adapter) + " " + (Q $Calibration) + " " + (Q $Tuning) + " " + (Q $Mapping) +
    " " + (Q $Controller) + " $ControlStartSec " + (Q $WarmupController) + " " + (Q $vbsConfig)
  $argline = $argline + " $StateLogIntervalSec"
  $argline = $argline + " $DemandScale"
  $argline = $argline + " " + (Q $DemandProfile) + " " + (Q $VehicleInputRoles)
  $argline = $argline + " $IncidentLink $IncidentLane $IncidentPos $IncidentStartSec $IncidentEndSec " + (Q $IncidentName)
  $argline = $argline + " " + (Q $UrbanInputGateMap)

  $t0 = Get-Date
  Normalize-ProcessPathEnv
  $oldForceStepwise = [Environment]::GetEnvironmentVariable("RW_FORCE_STEPWISE", "Process")
  $oldAuditAnchors = [Environment]::GetEnvironmentVariable("RW_AUDIT_ANCHORS_SEC", "Process")
  $oldRunId = [Environment]::GetEnvironmentVariable("RW_RUN_ID", "Process")
  $oldRunManifest = [Environment]::GetEnvironmentVariable("RW_RUN_MANIFEST_PATH", "Process")
  if ($ForceStepwise) {
    [Environment]::SetEnvironmentVariable("RW_FORCE_STEPWISE", "1", "Process")
  } else {
    [Environment]::SetEnvironmentVariable("RW_FORCE_STEPWISE", $null, "Process")
  }
  if ([string]::IsNullOrWhiteSpace($AuditAnchorsSec)) {
    [Environment]::SetEnvironmentVariable("RW_AUDIT_ANCHORS_SEC", $null, "Process")
  } else {
    [Environment]::SetEnvironmentVariable("RW_AUDIT_ANCHORS_SEC", $AuditAnchorsSec, "Process")
  }
  [Environment]::SetEnvironmentVariable("RW_RUN_ID", $runId, "Process")
  [Environment]::SetEnvironmentVariable("RW_RUN_MANIFEST_PATH", $provenancePath, "Process")
  $cscriptExe = Join-Path $env:SystemRoot "System32\cscript.exe"
  if (-not (Test-Path $cscriptExe)) { $cscriptExe = "cscript.exe" }
  $proc = Start-Process -FilePath $cscriptExe -ArgumentList $argline -RedirectStandardOutput $log `
    -RedirectStandardError "$log.err" -WorkingDirectory $repo -PassThru -WindowStyle Hidden
  [Environment]::SetEnvironmentVariable("RW_FORCE_STEPWISE", $oldForceStepwise, "Process")
  [Environment]::SetEnvironmentVariable("RW_AUDIT_ANCHORS_SEC", $oldAuditAnchors, "Process")
  [Environment]::SetEnvironmentVariable("RW_RUN_ID", $oldRunId, "Process")
  [Environment]::SetEnvironmentVariable("RW_RUN_MANIFEST_PATH", $oldRunManifest, "Process")
  if (-not $proc -or -not $proc.Id) {
    throw "Failed to start cscript for $Name attempt=$attempt"
  }
  Log "START $Name attempt=$attempt pid=$($proc.Id)"

  while ($true) {
    Start-Sleep -Seconds 20
    if ($proc.HasExited) {
      $done = Select-String -Path $log -Pattern "STAGE=SIM_DONE" -Quiet -ErrorAction SilentlyContinue
      if ($done) {
        Copy-VissimError $OutDir
        Log "OK $Name attempt=$attempt elapsed=$([int]((Get-Date)-$t0).TotalSeconds)s"
        exit 0
      }
      Log "EXIT_NO_DONE $Name attempt=$attempt"
      Archive-AttemptOutputs $attempt
      break
    }

    $lastT = $proc.StartTime
    $signals = @()
    $signals += Get-Item $log -ErrorAction SilentlyContinue
    $signals += Get-Item $stateCsv -ErrorAction SilentlyContinue
    $signals += Get-Item $actionCsv -ErrorAction SilentlyContinue
    $signals += Get-Item $bottleneckLinkCsv -ErrorAction SilentlyContinue
    $signals += Get-Item $bottleneckSegmentCsv -ErrorAction SilentlyContinue
    $signals += Get-ChildItem (Join-Path $decisionDir "action_*.json") -ErrorAction SilentlyContinue |
      Sort-Object LastWriteTime -Descending | Select-Object -First 1
    foreach ($signal in $signals) {
      if ($signal -and $signal.LastWriteTime -gt $lastT) {
        $lastT = $signal.LastWriteTime
      }
    }
    $idle = [int]((Get-Date) - $lastT).TotalSeconds
    if ($idle -gt $StallSec) {
      Log "WATCHDOG_KILL $Name attempt=$attempt idle=${idle}s"
      try { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue } catch {}
      Kill-Vissim
      Archive-AttemptOutputs $attempt
      break
    }
  }
}

Log "FAIL $Name after $MaxAttempts attempts"
exit 1
