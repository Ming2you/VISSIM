<#
Run one real-world Gaepo modi VISSIM controller case with a no-progress watchdog.

Progress is the newest mtime among the run log, state CSV, action CSV, and
decision action JSONs. If nothing moves for StallSec seconds, cscript/VISSIM are
killed and the case is retried up to MaxAttempts.
#>
param(
  [Parameter(Mandatory=$true)][string]$Name,
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
  [int]$StateLogIntervalSec = 5,
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
  # 비우면 러너가 자기 기본값(urban_input_gate_map_20260811.csv)으로 떨어진다.
  [string]$UrbanInputGateMap = "",
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
if ($Tuning -eq "") {
  $Tuning = Join-Path $repo "evaluation\configs\real_world_modi_pstack_distributed_pedovrx_20260814.json"
}
$Tuning = Resolve-RepoPath $Tuning
if ($Calibration -eq "") {
  $Calibration = Join-Path $repo "evaluation\calibration\real_world_prediction_calibration_pshb4500fix_20260724.json"
}
$Calibration = Resolve-RepoPath $Calibration
if ($Mapping -eq "") {
  $Mapping = Join-Path $repo "evaluation\real_world_modi_control_distributed_20260728\control_mapping_distributed_pedovrx_20260814.json"
}
$Mapping = Resolve-RepoPath $Mapping
if ($VehicleInputRoles -eq "") {
  $VehicleInputRoles = Join-Path $repo "evaluation\real_world_modi_inventory\vehicle_input_roles.csv"
}
$VehicleInputRoles = Resolve-RepoPath $VehicleInputRoles
if ($DemandProfile -ne "") {
  $DemandProfile = Resolve-RepoPath $DemandProfile
}
# 게이트맵을 절대경로로 굳혀서 provenance 가 해시까지 남기게 한다. 비우면 러너가
# 자기 기본값(urban_input_gate_map_20260811.csv)으로 떨어지는데, 그것은 pedovrx
# 격자의 맵이 아니다 - 부모런은 반드시 명시로 넘긴다.
if ($UrbanInputGateMap -ne "") {
  $UrbanInputGateMap = Resolve-RepoPath $UrbanInputGateMap
  if (-not (Test-Path -LiteralPath $UrbanInputGateMap -PathType Leaf)) {
    throw "UrbanInputGateMap not found: $UrbanInputGateMap"
  }
}
if ($ControlIntervalSec -le 0 -or ($ControlIntervalSec % 10) -ne 0) {
  throw "ControlIntervalSec must be a positive multiple of the 10s ramp-meter cycle. Got $ControlIntervalSec."
}
if ($StateLogIntervalSec -le 0) {
  throw "StateLogIntervalSec must be positive. Got $StateLogIntervalSec."
}

$runner = Join-Path $repo "scripts\run_real_world_stackelberg_controller.vbs"
if ($Network -eq "") {
  $Network = Join-Path $repo "network\real_world_gaepo_modi\modi_eval_userfix_20260814e.inpx"
}
$net = Resolve-RepoPath $Network
$adapter = Join-Path $repo "evaluation\controllers\vissim_stackelberg_adapter.py"
# VBS generated config (positional arg 14). This carries RW_LOCAL_OBSERVABLE_LINKS and
# RW_DETECTOR_MAPPING_PATH, i.e. WHAT THE PLANT RECORDS into state_*.json local_observation.
# 2026-08-04: this was hardcoded to the base config while grids passed a distributed
# -Mapping. Result: the plant logged only 22 observable links (base) while G6 scoring
# projected with the distributed 175-link detector mapping, so 153 links had no data and
# the observed objective captured 1.4% of urban vehicles. Every urban-axis candidate was
# then scored with the wrong sign. Default keeps the old path = bit-identical.
if ($VbsConfig -eq "") {
  $VbsConfig = Join-Path $repo "evaluation\generated\real_world_modi_control_config_distributed_pedovrx_20260814.vbs"
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
    # 파일명에 $Name 을 넣는다. 예전에는 고정 "vissim_network.err" 라 한 OutDir 에 여러 런을
    # 넣으면 마지막 것만 남았다. "망 편집 후 .err 의 Error 델타부터 봐라"가 운영 규칙인데
    # 배치 런에서는 그 근거가 사라져 있었다.
    Copy-Item -LiteralPath $vissimErr -Destination (Join-Path $DestinationDir "vissim_network_$Name.err") `
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
  link_assignment = Get-ArtifactEvidence (Join-Path $repo "outputs\link_player_assignment_pedfold_20260814.json")
  intersection_adjacency = Get-ArtifactEvidence (Join-Path $repo "outputs\intersection_adjacency_pedfold_20260814.json")
  # 2026-08-16: jam168 로 옮긴다. 여기가 낡은 채로 있으면 런이 자기가 쓰지도 않은 격자를
  # 증거로 기록한다 - 게다가 이 파일이 어댑터의 `_storage_effective_lanes` 가 차로수를
  # 유도하는 바로 그 근거라, 차로보정 A/B 의 핵심 근거를 틀리게 남기게 된다.
  storage_capacity = Get-ArtifactEvidence (Join-Path $repo "outputs\urban_storage_capacity_jam168_20260815.json")
  # 게이트맵은 런마다 달라지는데 provenance 에 빠져 있었다. 실제로 쓴 파일을 남긴다.
  urban_input_gate_map = Get-ArtifactEvidence $UrbanInputGateMap
  numsim_snapshot = Get-ArtifactEvidence (Join-Path $repo "vendor\NumSim-mine\SNAPSHOT.md")
  # 거동을 바꾸는 RW_* 환경변수를 그대로 남긴다. 어댑터가 metadata 에 적는 것이 "Python 이
  # 실제로 읽은 값"이라면, 이건 "셸이 무엇을 물려줬는가"다. A/B arm 을 사후에 확정하려면
  # 둘 다 있어야 하고, 둘이 어긋나면 전파가 끊긴 것이다.
  env = @{
    RW_LANE_DELAY_CORRECTION   = "$env:RW_LANE_DELAY_CORRECTION"
    RW_NARROW_AXIS_SG          = "$env:RW_NARROW_AXIS_SG"
    RW_ADAPTER_MODE            = "$env:RW_ADAPTER_MODE"
    RW_WARMSTART_SEC           = "$env:RW_WARMSTART_SEC"
    RW_QUEUE_ORIGIN_FILTER     = "$env:RW_QUEUE_ORIGIN_FILTER"
    RW_VALIDATION_FIXED_SIGNAL = "$env:RW_VALIDATION_FIXED_SIGNAL"
    RW_RESTORE_RELEASE_BUFFERS = "$env:RW_RESTORE_RELEASE_BUFFERS"
    RW_PYTHON                  = "$env:RW_PYTHON"
  }
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
  # 결정 1건이 3~4분 걸린다. 그동안 state/action 이 안 움직여 무진행 워치독이 정상
  # 풀이를 죽인다. 솔버가 진행을 흘리는 파일을 지정하고 아래 신호 목록에 넣는다.
  $oldProgressFile = [Environment]::GetEnvironmentVariable("NUMSIM_STACKELBERG_PROGRESS_FILE", "Process")
  $progressFile = Join-Path $decisionDir "stackelberg_progress_$Name.jsonl"
  [Environment]::SetEnvironmentVariable("NUMSIM_STACKELBERG_PROGRESS_FILE", $progressFile, "Process")
  $cscriptExe = Join-Path $env:SystemRoot "System32\cscript.exe"
  if (-not (Test-Path $cscriptExe)) { $cscriptExe = "cscript.exe" }
  $proc = Start-Process -FilePath $cscriptExe -ArgumentList $argline -RedirectStandardOutput $log `
    -RedirectStandardError "$log.err" -WorkingDirectory $repo -PassThru -WindowStyle Hidden
  [Environment]::SetEnvironmentVariable("RW_FORCE_STEPWISE", $oldForceStepwise, "Process")
  [Environment]::SetEnvironmentVariable("RW_AUDIT_ANCHORS_SEC", $oldAuditAnchors, "Process")
  [Environment]::SetEnvironmentVariable("RW_RUN_ID", $oldRunId, "Process")
  [Environment]::SetEnvironmentVariable("RW_RUN_MANIFEST_PATH", $oldRunManifest, "Process")
  [Environment]::SetEnvironmentVariable("NUMSIM_STACKELBERG_PROGRESS_FILE", $oldProgressFile, "Process")
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
    # 결정 풀이 중 진행 신호 - 이게 움직이면 무진행이 아니다.
    $signals += Get-Item $progressFile -ErrorAction SilentlyContinue
    $signals += Get-Item ([IO.Path]::ChangeExtension($progressFile, ".csv")) -ErrorAction SilentlyContinue
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
