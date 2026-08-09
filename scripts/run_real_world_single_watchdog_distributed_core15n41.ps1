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
  [switch]$ForceStepwise,
  [int]$StallSec = 300,
  [int]$MaxAttempts = 3,
  [int]$DoneRows = 0,
  [string]$AuditAnchorsSec = "",
  [string]$PreflightManifest = "",
  [switch]$B1aRequired,
  [string]$TopologyApproval = "",
  [switch]$B1aDryRun,
  [string]$B1aSyntheticFixtureSpec = ""
)

$ErrorActionPreference = "Continue"
$repo = [System.IO.Path]::GetFullPath((Resolve-Path (Join-Path $PSScriptRoot "..")).Path)
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
  $Tuning = Join-Path $repo "evaluation\configs\real_world_modi_pstack_distributed_core15n41_20260805.json"
}
$Tuning = Resolve-RepoPath $Tuning
if ($Calibration -eq "") {
  $Calibration = Join-Path $repo "evaluation\calibration\real_world_prediction_calibration_pshb4500fix_20260724.json"
}
$Calibration = Resolve-RepoPath $Calibration
if ($Mapping -eq "") {
  $Mapping = Join-Path $repo "evaluation\real_world_modi_control_distributed_20260728\control_mapping_distributed_core15n41_20260805.json"
}
$Mapping = Resolve-RepoPath $Mapping
if ($VehicleInputRoles -eq "") {
  $VehicleInputRoles = Join-Path $repo "evaluation\real_world_modi_inventory\vehicle_input_roles.csv"
}
$VehicleInputRoles = Resolve-RepoPath $VehicleInputRoles
if ($DemandProfile -ne "") {
  $DemandProfile = Resolve-RepoPath $DemandProfile
}
if ($PreflightManifest -ne "") {
  $PreflightManifest = Resolve-RepoPath $PreflightManifest
  if (-not (Test-Path -LiteralPath $PreflightManifest -PathType Leaf)) {
    throw "Preflight manifest not found: $PreflightManifest"
  }
}
if ($TopologyApproval -ne "") {
  $TopologyApproval = Resolve-RepoPath $TopologyApproval
  if (-not (Test-Path -LiteralPath $TopologyApproval -PathType Leaf)) {
    throw "Topology approval not found: $TopologyApproval"
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
  $Network = Join-Path $repo "network\real_world_gaepo_modi\modi_eval_rw_control.inpx"
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
  $VbsConfig = Join-Path $repo "evaluation\generated\real_world_modi_control_config_distributed_core15n41_20260805.vbs"
}
$vbsConfig = Resolve-RepoPath $VbsConfig
if (-not (Test-Path $vbsConfig)) { Log "ERROR vbs config not found: $vbsConfig"; exit 2 }

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
    Where-Object { $_.Name -like "action_*.json" -or $_.Name -like "action_*.csv" -or $_.Name -like "state_*.json" -or $_.Name -like "anchor_*.json" } |
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
  $fullPath = if ([string]::IsNullOrWhiteSpace($ArtifactPath)) { "" } else { [System.IO.Path]::GetFullPath($ArtifactPath) }
  $item = if ($exists) { Get-Item -LiteralPath $ArtifactPath -ErrorAction Stop } else { $null }
  [ordered]@{
    path = $fullPath
    exists = $exists
    sha256 = if ($exists) { (Get-FileHash -LiteralPath $ArtifactPath -Algorithm SHA256).Hash.ToLowerInvariant() } else { "" }
    size_bytes = if ($exists) { [long]$item.Length } else { $null }
    last_write_time_utc = if ($exists) { $item.LastWriteTimeUtc.ToString("o") } else { "" }
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

function Get-B1aWorkspaceRelativeFile([string]$PathValue, [string]$Label) {
  if ([string]::IsNullOrWhiteSpace($PathValue)) { throw "$Label is required" }
  $full = [System.IO.Path]::GetFullPath($PathValue)
  $item = Get-Item -LiteralPath $full -Force -ErrorAction Stop
  if (-not ($item -is [System.IO.FileInfo])) { throw "$Label is not a file: $full" }
  if (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) { throw "$Label is a reparse point: $full" }
  $rootFull = [System.IO.Path]::GetFullPath($repo).TrimEnd('\')
  $rootPrefix = $rootFull + '\'
  $fullCanonical = [System.IO.Path]::GetFullPath($item.FullName)
  if (-not $fullCanonical.StartsWith($rootPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "$Label escapes the workspace: $full"
  }
  $cursor = $item.Directory
  while ($null -ne $cursor) {
    if (($cursor.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) { throw "$Label has a reparse ancestor: $($cursor.FullName)" }
    if ($cursor.FullName.TrimEnd('\\').Equals($repo.TrimEnd('\\'), [System.StringComparison]::OrdinalIgnoreCase)) { break }
    $cursor = $cursor.Parent
  }
  if ($null -eq $cursor) { throw "$Label is not contained by the workspace" }
  return $fullCanonical.Substring($rootPrefix.Length).Replace('\\', '/')
}

function Get-B1aWorkspaceRelativeDestination([string]$PathValue, [string]$Label) {
  $full = [System.IO.Path]::GetFullPath($PathValue)
  $rootPrefix = $repo.TrimEnd('\\') + '\\'
  if (-not $full.StartsWith($rootPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "$Label escapes the workspace: $full"
  }
  $probe = $full
  while (-not (Test-Path -LiteralPath $probe)) {
    $parent = [System.IO.Path]::GetDirectoryName($probe)
    if ([string]::IsNullOrWhiteSpace($parent) -or $parent -eq $probe) { throw "$Label has no existing workspace ancestor: $full" }
    $probe = $parent
  }
  $cursor = Get-Item -LiteralPath $probe -Force -ErrorAction Stop
  while ($null -ne $cursor) {
    if (($cursor.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) { throw "$Label has a reparse ancestor: $($cursor.FullName)" }
    if ($cursor.FullName.TrimEnd('\\').Equals($repo.TrimEnd('\\'), [System.StringComparison]::OrdinalIgnoreCase)) { break }
    $cursor = $cursor.Parent
  }
  if ($null -eq $cursor) { throw "$Label is not contained by the workspace" }
  return $full.Substring($rootPrefix.Length).Replace('\\', '/')
}

function New-B1aExclusiveDirectory([string]$PathValue, [string]$Label) {
  if (Test-Path -LiteralPath $PathValue) { throw "$Label already exists: $PathValue" }
  try {
    New-Item -ItemType Directory -Path $PathValue -ErrorAction Stop | Out-Null
  } catch {
    throw "exclusive $Label create failed: $PathValue ($($_.Exception.Message))"
  }
  $item = Get-Item -LiteralPath $PathValue -Force -ErrorAction Stop
  if (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) { throw "$Label is a reparse point: $PathValue" }
  return [System.IO.Path]::GetFullPath($PathValue)
}

function New-B1aSharedDirectory([string]$PathValue, [string]$Label) {
  try {
    New-Item -ItemType Directory -Force -Path $PathValue -ErrorAction Stop | Out-Null
  } catch {
    throw "shared $Label create failed: $PathValue ($($_.Exception.Message))"
  }
  $item = Get-Item -LiteralPath $PathValue -Force -ErrorAction Stop
  if (-not $item.PSIsContainer) { throw "$Label is not a directory: $PathValue" }
  if (($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) { throw "$Label is a reparse point: $PathValue" }
  return [System.IO.Path]::GetFullPath($PathValue)
}

function Copy-B1aConfigCreateOnce([string]$Source, [string]$Destination) {
  if (Test-Path -LiteralPath $Destination) { throw "attempt config already exists: $Destination" }
  $parent = [System.IO.Path]::GetDirectoryName($Destination)
  $temporary = Join-Path $parent ('.' + [System.IO.Path]::GetFileName($Destination) + '.' + $PID + '.' + [guid]::NewGuid().ToString('N') + '.tmp')
  try {
    $input = [System.IO.File]::Open($Source, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::Read)
    try {
      $output = [System.IO.File]::Open($temporary, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
      try { $input.CopyTo($output) } finally { $output.Dispose() }
    } finally { $input.Dispose() }
    [System.IO.File]::Move($temporary, $Destination)
  } finally {
    if (Test-Path -LiteralPath $temporary -PathType Leaf) { Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue }
  }
  $sourceHash = (Get-FileHash -LiteralPath $Source -Algorithm SHA256).Hash.ToLowerInvariant()
  $copyHash = (Get-FileHash -LiteralPath $Destination -Algorithm SHA256).Hash.ToLowerInvariant()
  $sourceBytes = [System.IO.File]::ReadAllBytes($Source)
  $copyBytes = [System.IO.File]::ReadAllBytes($Destination)
  $equalBytes = $sourceBytes.Length -eq $copyBytes.Length
  if ($equalBytes) {
    for ($index = 0; $index -lt $sourceBytes.Length; $index++) {
      if ($sourceBytes[$index] -ne $copyBytes[$index]) { $equalBytes = $false; break }
    }
  }
  if ($sourceHash -ne $copyHash -or -not $equalBytes) {
    throw "attempt config copy does not match its bound source"
  }
  return $copyHash
}

function Get-B1aSchedulePlan(
  [int]$PeriodSec,
  [int]$DecisionIntervalSec,
  [string]$ControllerName,
  [int]$StartSec,
  [int]$LogIntervalSec,
  [string]$AnchorsSec,
  [bool]$Stepwise
) {
  if ($PeriodSec -le 0) { throw "SimPeriod must be positive" }
  if ($DecisionIntervalSec -le 0) { throw "ControlIntervalSec must be positive" }
  if ($LogIntervalSec -le 0) { throw "StateLogIntervalSec must be positive" }
  if ($StartSec -lt -1 -or $StartSec -gt $PeriodSec) { throw "ControlStartSec must be -1 or within SimPeriod" }
  $controllerKey = $ControllerName.Trim().ToLowerInvariant().Replace('_', '-')
  if ([string]::IsNullOrWhiteSpace($controllerKey)) { throw "Controller is required" }
  $mode = if ($Stepwise) {
    'stepwise'
  } elseif ($controllerKey -in @('no-control','diagnostic-vsl60-only','diagnostic-vsl80-only')) {
    'continuous_static'
  } elseif ($controllerKey.StartsWith('diagnostic-') -or $controllerKey -eq 'stackelberg') {
    'continuous_event'
  } else {
    'stepwise'
  }

  $decisionTimes = New-Object 'System.Collections.Generic.HashSet[Int64]'
  [void]$decisionTimes.Add(1)
  $singleDecision = ($mode -eq 'continuous_event' -and $controllerKey.StartsWith('diagnostic-') -and $StartSec -ge 0)
  if ($mode -eq 'continuous_static' -or $singleDecision) {
    if ($StartSec -gt 1) { [void]$decisionTimes.Add([int64]$StartSec) }
  } else {
    for ($time = $DecisionIntervalSec; $time -le $PeriodSec; $time += $DecisionIntervalSec) {
      [void]$decisionTimes.Add([int64]$time)
    }
  }

  $logTimes = New-Object 'System.Collections.Generic.HashSet[Int64]'
  [void]$logTimes.Add(1)
  for ($time = $LogIntervalSec; $time -le $PeriodSec; $time += $LogIntervalSec) {
    [void]$logTimes.Add([int64]$time)
  }
  [void]$logTimes.Add([int64]$PeriodSec)

  $anchorTimes = New-Object 'System.Collections.Generic.HashSet[Int64]'
  if (-not [string]::IsNullOrWhiteSpace($AnchorsSec)) {
    foreach ($rawToken in $AnchorsSec.Split(',')) {
      $token = $rawToken.Trim()
      if ($token -notmatch '^(0|[1-9][0-9]*)$') { throw "AuditAnchorsSec contains a non-canonical integer: $rawToken" }
      $value = 0L
      if (-not [int64]::TryParse($token, [Globalization.NumberStyles]::None, [Globalization.CultureInfo]::InvariantCulture, [ref]$value) -or $value -lt 0 -or $value -gt $PeriodSec) {
        throw "AuditAnchorsSec contains an out-of-range time: $rawToken"
      }
      [void]$anchorTimes.Add($value)
    }
  }

  $allowed = New-Object 'System.Collections.Generic.HashSet[Int64]'
  foreach ($time in $decisionTimes) { [void]$allowed.Add($time) }
  foreach ($time in $anchorTimes) {
    if ($logTimes.Contains($time)) { [void]$allowed.Add($time) }
  }
  $normalizedAnchors = @($anchorTimes | Sort-Object)
  $allowedCaptureTimes = @($allowed | Sort-Object | ForEach-Object { [double]$_ })
  return [pscustomobject]@{
    mode = $mode
    single_decision = $singleDecision
    decision_times = @($decisionTimes | Sort-Object)
    log_times = @($logTimes | Sort-Object)
    allowed_capture_times = $allowedCaptureTimes
    normalized_audit_anchors_sec = ($normalizedAnchors -join ',')
  }
}

# Single template serializer for both the publish path and the dry-run path.
# PowerShell 5.1 ConvertTo-Json emits a double with no fractional part as an integer
# literal, and the consumer contract (plant/src/vissim_strict/run_evidence.py) rejects
# integers in allowed_capture_times. Both callers must therefore share this
# normalization, otherwise the dry-run validates different bytes than are published.
function ConvertTo-B1aTemplateJson($Value, [bool]$Compress) {
  if ($Compress) { $json = $Value | ConvertTo-Json -Depth 12 -Compress }
  else { $json = $Value | ConvertTo-Json -Depth 12 }
  $allowedValues = $null
  $hasAllowedValues = $false
  if ($Value -is [System.Collections.IDictionary] -and $Value.Contains('allowed_capture_times')) {
    $allowedValues = $Value['allowed_capture_times']
    $hasAllowedValues = $true
  } elseif ($null -ne $Value.PSObject.Properties['allowed_capture_times']) {
    $allowedValues = $Value.allowed_capture_times
    $hasAllowedValues = $true
  }
  if ($hasAllowedValues) {
    $formattedTimes = @($allowedValues | ForEach-Object {
      ([double]$_).ToString('0.0###############', [Globalization.CultureInfo]::InvariantCulture)
    })
    $replacement = '"allowed_capture_times":[' + ($formattedTimes -join ',') + ']'
    $pattern = '"allowed_capture_times"\s*:\s*\[[^\]]*\]'
    $matches = [regex]::Matches($json, $pattern)
    if ($matches.Count -ne 1) { throw 'allowed_capture_times JSON contract replacement failed' }
    $json = [regex]::Replace($json, $pattern, [System.Text.RegularExpressions.MatchEvaluator]{ param($match) $replacement }, 1)
  }
  return $json
}

function Write-B1aJsonTemplate([string]$PathValue, $Value) {
  $json = ConvertTo-B1aTemplateJson $Value $false
  $bytes = [System.Text.UTF8Encoding]::new($false).GetBytes($json + "`n")
  $stream = [System.IO.File]::Open($PathValue, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
  try { $stream.Write($bytes, 0, $bytes.Length); $stream.Flush($true) } finally { $stream.Dispose() }
}

function Assert-B1aConfigMatch([string]$Source, [string]$Copy, [string]$ExpectedHash, [string]$When) {
  if (-not (Test-Path -LiteralPath $Source -PathType Leaf) -or -not (Test-Path -LiteralPath $Copy -PathType Leaf)) { throw "config missing $When" }
  $sourceHash = (Get-FileHash -LiteralPath $Source -Algorithm SHA256).Hash.ToLowerInvariant()
  $copyHash = (Get-FileHash -LiteralPath $Copy -Algorithm SHA256).Hash.ToLowerInvariant()
  if ($sourceHash -ne $ExpectedHash -or $copyHash -ne $ExpectedHash) { throw "config hash mismatch $When" }
  $sourceBytes = [System.IO.File]::ReadAllBytes($Source); $copyBytes = [System.IO.File]::ReadAllBytes($Copy)
  if ($sourceBytes.Length -ne $copyBytes.Length) { throw "config byte length mismatch $When" }
  for ($index = 0; $index -lt $sourceBytes.Length; $index++) {
    if ($sourceBytes[$index] -ne $copyBytes[$index]) { throw "config byte mismatch $When" }
  }
}

function Move-B1aStageFile([string]$Source, [string]$Destination) {
  if (-not (Test-Path -LiteralPath $Source -PathType Leaf)) { throw "staged artifact is missing: $Source" }
  if (Test-Path -LiteralPath $Destination) { throw "staged artifact destination already exists: $Destination" }
  [System.IO.File]::Move($Source, $Destination)
}

function Assert-B1aResultPass([string]$PathValue, [string]$Label) {
  if (-not (Test-Path -LiteralPath $PathValue -PathType Leaf)) { throw "$Label is missing" }
  $result = Get-Content -Raw -LiteralPath $PathValue | ConvertFrom-Json -ErrorAction Stop
  if ($result.schema_version -ne 'run-manifest-creation-result-v2.1' -or $result.status -ne 'PASS') { throw "$Label is not PASS" }
}

function Invoke-B1aTemplateValidationNoWrite([string]$PythonPath, [string]$ProducerPath, $Template) {
  $json = ConvertTo-B1aTemplateJson $Template $true
  $startInfo = New-Object System.Diagnostics.ProcessStartInfo
  $startInfo.FileName = $PythonPath
  $startInfo.Arguments = '-B ' + (Q $ProducerPath) + ' --validate-template-stdin --workspace-root ' + (Q $repo)
  $startInfo.WorkingDirectory = $repo
  $startInfo.UseShellExecute = $false
  $startInfo.CreateNoWindow = $true
  $startInfo.RedirectStandardInput = $true
  $startInfo.RedirectStandardOutput = $true
  $startInfo.RedirectStandardError = $true
  $process = New-Object System.Diagnostics.Process
  $process.StartInfo = $startInfo
  if (-not $process.Start()) { throw 'B1a dry-run validator failed to start' }
  try {
    $utf8 = [System.Text.UTF8Encoding]::new($false)
    $bytes = $utf8.GetBytes($json)
    $process.StandardInput.BaseStream.Write($bytes, 0, $bytes.Length)
    $process.StandardInput.Close()
    $stdout = $process.StandardOutput.ReadToEndAsync(); $stderr = $process.StandardError.ReadToEndAsync()
    if (-not $process.WaitForExit(30000)) { try { $process.Kill() } catch {}; throw 'B1a dry-run validator timed out' }
    if (-not $stdout.Wait(5000) -or -not $stderr.Wait(5000) -or $process.ExitCode -ne 0) { throw 'B1a dry-run request validation failed' }
  } finally { $process.Dispose() }
}

function Get-B1aLatestProgressUtc([datetime]$StartedUtc, [string[]]$Paths) {
  $latest = $StartedUtc
  foreach ($pathValue in $Paths) {
    if ([string]::IsNullOrWhiteSpace($pathValue) -or -not (Test-Path -LiteralPath $pathValue)) { continue }
    $item = Get-Item -LiteralPath $pathValue -Force -ErrorAction SilentlyContinue
    if ($item -and $item.LastWriteTimeUtc -gt $latest) { $latest = $item.LastWriteTimeUtc }
    if ($item -and $item.PSIsContainer) {
      $child = Get-ChildItem -LiteralPath $pathValue -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
      if ($child -and $child.LastWriteTimeUtc -gt $latest) { $latest = $child.LastWriteTimeUtc }
    }
  }
  return $latest
}

function Stop-B1aAttemptProcesses($Process, [int[]]$BaselineVissimIds) {
  if ($null -ne $Process -and -not $Process.HasExited) {
    $taskkill = Join-Path $env:SystemRoot 'System32\taskkill.exe'
    if (Test-Path -LiteralPath $taskkill -PathType Leaf) {
      $killInfo = New-Object System.Diagnostics.ProcessStartInfo
      $killInfo.FileName = $taskkill; $killInfo.Arguments = "/PID $($Process.Id) /T /F"; $killInfo.UseShellExecute = $false; $killInfo.CreateNoWindow = $true
      $killer = [System.Diagnostics.Process]::Start($killInfo)
      if ($killer) { if (-not $killer.WaitForExit(5000)) { try { $killer.Kill() } catch {} }; $killer.Dispose() }
    }
    if (-not $Process.HasExited) { try { $Process.Kill() } catch {} }
  }
  $baseline = @{}; foreach ($pidValue in $BaselineVissimIds) { $baseline[[int]$pidValue] = $true }
  Get-Process -Name 'VISSIM200','VISSIM200CL' -ErrorAction SilentlyContinue | Where-Object { -not $baseline.ContainsKey([int]$_.Id) } | Stop-Process -Force -ErrorAction SilentlyContinue
}

function Invoke-B1aMonitoredProcess(
  [string]$FilePath,
  [string]$ArgumentLine,
  [string]$WorkingDirectory,
  [string]$StdoutPath,
  [string]$StderrPath,
  [hashtable]$ChildEnvironment,
  [string[]]$ProgressPaths,
  [int]$IdleTimeoutSec,
  [int[]]$BaselineVissimIds
) {
  if ($IdleTimeoutSec -le 0) { throw 'StallSec must be positive' }
  $startInfo = New-Object System.Diagnostics.ProcessStartInfo
  $startInfo.FileName = $FilePath; $startInfo.Arguments = $ArgumentLine; $startInfo.WorkingDirectory = $WorkingDirectory
  $startInfo.UseShellExecute = $false; $startInfo.CreateNoWindow = $true; $startInfo.RedirectStandardOutput = $true; $startInfo.RedirectStandardError = $true
  foreach ($key in $ChildEnvironment.Keys) {
    if ($null -eq $ChildEnvironment[$key]) { $startInfo.EnvironmentVariables.Remove([string]$key) } else { $startInfo.EnvironmentVariables[[string]$key] = [string]$ChildEnvironment[$key] }
  }
  $stdoutStream = [System.IO.File]::Open($StdoutPath, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::ReadWrite)
  $stderrStream = [System.IO.File]::Open($StderrPath, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::ReadWrite)
  $process = New-Object System.Diagnostics.Process; $process.StartInfo = $startInfo
  $stdoutTask = $null; $stderrTask = $null; $timedOut = $false; $startedUtc = [datetime]::UtcNow
  try {
    if (-not $process.Start()) { throw 'child process start returned false' }
    $startedUtc = $process.StartTime.ToUniversalTime()
    $stdoutTask = $process.StandardOutput.BaseStream.CopyToAsync($stdoutStream)
    $stderrTask = $process.StandardError.BaseStream.CopyToAsync($stderrStream)
    while (-not $process.HasExited) {
      Start-Sleep -Milliseconds 250
      $latest = Get-B1aLatestProgressUtc $startedUtc (@($StdoutPath,$StderrPath) + $ProgressPaths)
      if (([datetime]::UtcNow - $latest).TotalSeconds -gt $IdleTimeoutSec) {
        $timedOut = $true
        Stop-B1aAttemptProcesses $process $BaselineVissimIds
        break
      }
    }
    if (-not $process.WaitForExit(10000)) { Stop-B1aAttemptProcesses $process $BaselineVissimIds; if (-not $process.WaitForExit(5000)) { throw 'child process did not terminate after bounded kill' } }
    if ($stdoutTask -and -not $stdoutTask.Wait(10000)) { throw 'stdout drain timed out' }
    if ($stderrTask -and -not $stderrTask.Wait(10000)) { throw 'stderr drain timed out' }
    $stdoutStream.Flush($true); $stderrStream.Flush($true)
    return [pscustomobject]@{ pid=$process.Id; exit_code=[int]$process.ExitCode; timed_out=$timedOut; termination_reason=$(if ($timedOut) {'watchdog_timeout'} elseif ($process.ExitCode -eq 0) {'normal'} else {'process_error'}) }
  } catch {
    Stop-B1aAttemptProcesses $process $BaselineVissimIds
    throw
  } finally {
    $stdoutStream.Dispose(); $stderrStream.Dispose(); $process.Dispose()
  }
}

function Get-B1aPython([string]$PathValue) {
  if ([string]::IsNullOrWhiteSpace($PathValue) -or -not (Test-Path -LiteralPath $PathValue -PathType Leaf)) { throw "B1a required mode needs RW_PYTHON_EXE" }
  $resolved = (Resolve-Path -LiteralPath $PathValue).Path
  $version = & $resolved -B -c "import sys; print('%d.%d' % sys.version_info[:2])"
  if ($LASTEXITCODE -ne 0 -or [version]$version -lt [version]'3.10') { throw "B1a required mode needs Python >=3.10" }
  return $resolved
}


function New-B1aRequestTemplate($RunId, $CampaignId, [int]$AttemptNumber, $AttemptRelative, $CreationRelative, [bool]$ValidateOnly, $InputBindings, $SourceBindings, $Schedule, $ApprovalRelative, $PreflightRelative) {
  $simulation = [ordered]@{ sim_period_sec=$SimPeriod; control_interval_sec=$ControlIntervalSec; seed=$Seed; controller=$Controller; control_start_sec=$ControlStartSec; warmup_controller=$WarmupController; state_log_interval_sec=$StateLogIntervalSec; demand_scale=$DemandScale; demand_profile=$InputBindings.demand_profile; incident_link=$IncidentLink; incident_lane=$IncidentLane; incident_pos_m=$IncidentPos; incident_start_sec=$IncidentStartSec; incident_end_sec=$IncidentEndSec; incident_name=$IncidentName }
  return [ordered]@{ schema_version='run-manifest-request-v2.1'; workspace_root=$repo; run_directory=$AttemptRelative; run_id=$RunId; campaign_id=$CampaignId; attempt=$AttemptNumber; qualification=[ordered]@{mode='live_required'}; topology_approval=$ApprovalRelative; preflight=$PreflightRelative; producer_sources=$SourceBindings; configuration=[ordered]@{inputs=$InputBindings; simulation=$simulation}; allowed_capture_times=@($Schedule.allowed_capture_times); output_manifest="$AttemptRelative/run_manifest_v2_1.json"; creation_result_output=$CreationRelative; validate_only=$ValidateOnly }
}

function Write-B1aAttemptFailure([string]$AttemptDir, [string]$Message) {
  if ([string]::IsNullOrWhiteSpace($AttemptDir) -or -not (Test-Path -LiteralPath $AttemptDir -PathType Container)) { return }
  $failurePath = Join-Path $AttemptDir 'attempt_failure.txt'
  if (-not (Test-Path -LiteralPath $failurePath)) { [System.IO.File]::WriteAllText($failurePath, $Message + "`r`n", [System.Text.UTF8Encoding]::new($false)) }
}

function Invoke-B1aRequiredWatchdog {
  $ErrorActionPreference = 'Stop'
  if ($MaxAttempts -le 0 -or $StallSec -le 0) { throw 'MaxAttempts and StallSec must be positive' }
  if ([string]::IsNullOrWhiteSpace($TopologyApproval) -or [string]::IsNullOrWhiteSpace($PreflightManifest)) { throw 'B1a required mode requires explicit -TopologyApproval and -PreflightManifest' }
  $python = Get-B1aPython ([Environment]::GetEnvironmentVariable('RW_PYTHON_EXE', 'Process'))
  $manifestProducer = Join-Path $repo 'scripts\build_run_manifest_v2_1.py'
  $inputBindings = [ordered]@{
    network = Get-B1aWorkspaceRelativeFile $net 'network'; generated_vbs_config = Get-B1aWorkspaceRelativeFile $vbsConfig 'generated VBS config'; adapter = Get-B1aWorkspaceRelativeFile $adapter 'adapter'
    calibration = Get-B1aWorkspaceRelativeFile $Calibration 'calibration'; tuning = Get-B1aWorkspaceRelativeFile $Tuning 'tuning'; control_mapping = Get-B1aWorkspaceRelativeFile $Mapping 'control mapping'
    vehicle_input_roles = Get-B1aWorkspaceRelativeFile $VehicleInputRoles 'vehicle input roles'; demand_profile = if ([string]::IsNullOrWhiteSpace($DemandProfile)) { $null } else { Get-B1aWorkspaceRelativeFile $DemandProfile 'demand profile' }
  }
  $approvalRelative = Get-B1aWorkspaceRelativeFile $TopologyApproval 'topology approval'; $preflightRelative = Get-B1aWorkspaceRelativeFile $PreflightManifest 'preflight manifest'
  $schedule = Get-B1aSchedulePlan $SimPeriod $ControlIntervalSec $Controller $ControlStartSec $StateLogIntervalSec $AuditAnchorsSec ([bool]$ForceStepwise)
  $sourceBindings = [ordered]@{
    watchdog = Get-B1aWorkspaceRelativeFile $PSCommandPath 'watchdog source'; vbs = Get-B1aWorkspaceRelativeFile $runner 'VBS source'; adapter = $inputBindings.adapter
    run_manifest_producer = Get-B1aWorkspaceRelativeFile $manifestProducer 'run manifest producer'; topology_approval_validator = Get-B1aWorkspaceRelativeFile (Join-Path $repo 'scripts\approve_physical_stock_topology.py') 'topology approval validator'
    state_manifest_builder = Get-B1aWorkspaceRelativeFile (Join-Path $repo 'scripts\build_state_manifest_v2_1.py') 'state manifest builder'; physical_projection_module = Get-B1aWorkspaceRelativeFile (Join-Path $repo 'plant\src\vissim_strict\physical_projection.py') 'physical projection module'
# v3 N0-1: the two v2.2 producers are no longer required source roles. They are never built,
# so binding them here made every required-mode run die at source binding. The remaining ten
# role bindings and the exact-set check in build_run_manifest_v2_1.py are unchanged.
    preflight_producer = Get-B1aWorkspaceRelativeFile (Join-Path $repo 'scripts\build_preflight_manifest.py') 'preflight producer'; monotonic_clock_helper = Get-B1aWorkspaceRelativeFile (Join-Path $repo 'scripts\read_monotonic_clock.py') 'monotonic clock helper'
    supported_version_policy = Get-B1aWorkspaceRelativeFile (Join-Path $repo 'plant\policies\supported_vissim_versions_v2_1.json') 'supported version policy'
  }
  $campaignId = [guid]::NewGuid().ToString('N'); $runId = [guid]::NewGuid().ToString('N')
  $plannedAttempt = Join-Path (Join-Path $OutDir $campaignId) ('attempt_01_' + $runId); $attemptRelative = Get-B1aWorkspaceRelativeDestination $plannedAttempt 'planned attempt directory'
  $creationRelative = "$attemptRelative/run_manifest_creation_result_v2_1.json"
  $plannedTemplate = New-B1aRequestTemplate $runId $campaignId 1 $attemptRelative $creationRelative $false $inputBindings $sourceBindings $schedule $approvalRelative $preflightRelative
  if ($B1aDryRun) {
    Invoke-B1aTemplateValidationNoWrite $python $manifestProducer $plannedTemplate
    Write-Host "B1A_REQUIRED_DRY_RUN_NOT_EVALUATED name=$Name mode=$($schedule.mode) allowed_capture_times=$($schedule.allowed_capture_times -join ',')"
    return
  }
  [void](Get-B1aWorkspaceRelativeDestination $OutDir 'OutDir')
  $OutDir = New-B1aSharedDirectory $OutDir 'OutDir'
  [void](Get-B1aWorkspaceRelativeDestination $OutDir 'OutDir')
  $campaignPath = Join-Path $OutDir $campaignId; [void](Get-B1aWorkspaceRelativeDestination $campaignPath 'campaign directory'); $campaignDir = New-B1aExclusiveDirectory $campaignPath 'campaign directory'
  for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
    $runId = [guid]::NewGuid().ToString('N'); $attemptDir = ''
    $attemptPath = Join-Path $campaignDir ('attempt_{0:00}_{1}' -f $attempt, $runId); $attemptRelative = Get-B1aWorkspaceRelativeDestination $attemptPath 'attempt directory'
    $manifestRelative = "$attemptRelative/run_manifest_v2_1.json"; $creationRelative = "$attemptRelative/run_manifest_creation_result_v2_1.json"; $validationRelative = "$attemptRelative/run_manifest_validation_result_v2_1.json"
    $stagePrefix = '.stage_attempt_{0:00}_{1}' -f $attempt,$runId
    $templateStage = Join-Path $campaignDir ($stagePrefix + '_request_template.json'); $requestStage = Join-Path $campaignDir ($stagePrefix + '_request.json')
    $validationTemplateStage = Join-Path $campaignDir ($stagePrefix + '_validation_template.json'); $validationRequestStage = Join-Path $campaignDir ($stagePrefix + '_validation_request.json')
    try {
      $template = New-B1aRequestTemplate $runId $campaignId $attempt $attemptRelative $creationRelative $false $inputBindings $sourceBindings $schedule $approvalRelative $preflightRelative
      Write-B1aJsonTemplate $templateStage $template
      & $python -B $manifestProducer --request-template $templateStage --write-request (Get-B1aWorkspaceRelativeDestination $requestStage 'staged request') --workspace-root $repo
      if ($LASTEXITCODE -ne 0) { throw "B1a request construction failed attempt=$attempt" }
      & $python -B $manifestProducer --request $requestStage --workspace-root $repo --run-directory $attemptRelative --creation-result-output $creationRelative
      if ($LASTEXITCODE -ne 0) { throw "B1a manifest creation failed attempt=$attempt" }
      $attemptDir = (Resolve-Path -LiteralPath $attemptPath).Path
      Assert-B1aResultPass (Join-Path $attemptDir 'run_manifest_creation_result_v2_1.json') 'manifest creation result'
      Move-B1aStageFile $templateStage (Join-Path $attemptDir 'run_manifest_request_template_v2_1.json'); Move-B1aStageFile $requestStage (Join-Path $attemptDir 'run_manifest_request_v2_1.json')
      $validation = New-B1aRequestTemplate $runId $campaignId $attempt $attemptRelative $validationRelative $true $inputBindings $sourceBindings $schedule $approvalRelative $preflightRelative
      Write-B1aJsonTemplate $validationTemplateStage $validation
      & $python -B $manifestProducer --request-template $validationTemplateStage --write-request (Get-B1aWorkspaceRelativeDestination $validationRequestStage 'staged validation request') --workspace-root $repo
      if ($LASTEXITCODE -ne 0) { throw "B1a validation request construction failed attempt=$attempt" }
      & $python -B $manifestProducer --request $validationRequestStage --workspace-root $repo --run-directory $attemptRelative --creation-result-output $validationRelative --validate-only
      if ($LASTEXITCODE -ne 0) { throw "B1a manifest validation failed attempt=$attempt" }
      Assert-B1aResultPass (Join-Path $attemptDir 'run_manifest_validation_result_v2_1.json') 'manifest validation result'
      Move-B1aStageFile $validationTemplateStage (Join-Path $attemptDir 'run_manifest_validate_template_v2_1.json'); Move-B1aStageFile $validationRequestStage (Join-Path $attemptDir 'run_manifest_validate_request_v2_1.json')
      $decisionDir = New-B1aExclusiveDirectory (Join-Path $attemptDir 'decisions') 'decision directory'; $stateCsv = Join-Path $attemptDir 'state.csv'; $actionCsv = Join-Path $attemptDir 'actions.csv'
      $stdoutPath = Join-Path $attemptDir 'runlog.txt'; $stderrPath = Join-Path $attemptDir 'runlog.err.txt'; $configCopy = Join-Path $attemptDir 'generated_config.vbs'
      $configHash = Copy-B1aConfigCreateOnce $vbsConfig $configCopy; Assert-B1aConfigMatch $vbsConfig $configCopy $configHash 'before launch'
      $manifestPath = Join-Path $attemptDir 'run_manifest_v2_1.json'; $manifestHash = (Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256).Hash.ToLowerInvariant()
      $validateRequestPath = Join-Path $attemptDir 'run_manifest_validate_request_v2_1.json'
      & $python -B $manifestProducer --request $validateRequestPath --workspace-root $repo --run-directory $attemptRelative --creation-result-output $validationRelative --validate-only
      if ($LASTEXITCODE -ne 0) { throw "B1a immediate prelaunch source rehash failed attempt=$attempt" }
      Assert-B1aConfigMatch $vbsConfig $configCopy $configHash 'immediately before launch'
      $argline = "//nologo " + (Q $runner) + " " + (Q $net) + " " + (Q $stateCsv) + " " + (Q $actionCsv) + " " + (Q $decisionDir) + " $SimPeriod $ControlIntervalSec $Seed " + (Q $adapter) + " " + (Q $Calibration) + " " + (Q $Tuning) + " " + (Q $Mapping) + " " + (Q $Controller) + " $ControlStartSec " + (Q $WarmupController) + " " + (Q $configCopy) + " $StateLogIntervalSec $DemandScale " + (Q $DemandProfile) + " " + (Q $VehicleInputRoles) + " $IncidentLink $IncidentLane $IncidentPos $IncidentStartSec $IncidentEndSec " + (Q $IncidentName)
      $childEnvironment = @{ RW_FORCE_STEPWISE=$(if ($ForceStepwise) {'1'} else {$null}); RW_AUDIT_ANCHORS_SEC=$(if ($schedule.normalized_audit_anchors_sec) {$schedule.normalized_audit_anchors_sec} else {$null}); RW_PYTHON=$python; RW_RUN_ID=$runId; RW_RUN_MANIFEST_PATH=$manifestPath; RW_RUN_MANIFEST_SHA256=$manifestHash; RW_B1A_REQUIRED='1'; RW_QUALIFICATION_MODE='live_required' }
      $cscriptExe = Join-Path $env:SystemRoot 'System32\cscript.exe'; if (-not (Test-Path -LiteralPath $cscriptExe -PathType Leaf)) { $cscriptExe = 'cscript.exe' }
      $baselineVissimIds = @(Get-Process -Name 'VISSIM200','VISSIM200CL' -ErrorAction SilentlyContinue | ForEach-Object { [int]$_.Id })
      $processResult = Invoke-B1aMonitoredProcess $cscriptExe $argline $attemptDir $stdoutPath $stderrPath $childEnvironment @($stateCsv,$actionCsv,$decisionDir) $StallSec $baselineVissimIds
      $postConfigOk = $true; try { Assert-B1aConfigMatch $vbsConfig $configCopy $configHash 'after termination' } catch { $postConfigOk = $false }
      & $python -B $manifestProducer --request $validateRequestPath --workspace-root $repo --run-directory $attemptRelative --creation-result-output $validationRelative --validate-only
      $rehashOk = ($LASTEXITCODE -eq 0); $done = Select-String -LiteralPath $stdoutPath -Pattern 'STAGE=SIM_DONE' -Quiet -ErrorAction SilentlyContinue
      if ($processResult.exit_code -eq 0 -and -not $processResult.timed_out -and $done -and $rehashOk -and $postConfigOk) { Write-Host "OK_REQUIRED $Name campaign=$campaignId attempt=$attempt run_id=$runId"; return }
      throw "attempt did not qualify exit=$($processResult.exit_code) timeout=$($processResult.timed_out) done=$done rehash=$rehashOk config=$postConfigOk"
    } catch {
      if (-not $attemptDir -and (Test-Path -LiteralPath $attemptPath -PathType Container)) { $attemptDir = (Resolve-Path -LiteralPath $attemptPath).Path }
      Write-B1aAttemptFailure $attemptDir $_.Exception.Message
      Write-Host "FAIL_REQUIRED $Name campaign=$campaignId attempt=$attempt run_id=$runId reason=$($_.Exception.Message)"
    } finally {
      foreach ($stagedPath in @($templateStage,$requestStage,$validationTemplateStage,$validationRequestStage)) {
        if (Test-Path -LiteralPath $stagedPath -PathType Leaf) {
          Remove-Item -LiteralPath $stagedPath -Force -ErrorAction SilentlyContinue
        }
      }
    }
  }
  throw "B1a required watchdog failed after $MaxAttempts attempts"
}

function Invoke-B1aSyntheticFixtureHarness([string]$SpecPath) {
  $ErrorActionPreference = 'Stop'
  $spec = Get-Content -Raw -LiteralPath $SpecPath | ConvertFrom-Json -ErrorAction Stop
  $expected = @('schema_version','qualification','out_dir','config_source','child_file','child_arguments','stall_sec','max_attempts')
  $actualFields = (@($spec.PSObject.Properties.Name | Sort-Object) -join ',')
  $expectedFields = (@($expected | Sort-Object) -join ',')
  if ($actualFields -ne $expectedFields) { throw 'synthetic fixture fields mismatch' }
  if ($spec.schema_version -ne 'b1a-watchdog-synthetic-fixture-v1' -or $spec.qualification.mode -ne 'synthetic_fixture' -or @($spec.qualification.PSObject.Properties.Name).Count -ne 1) { throw 'synthetic fixture qualification mismatch' }
  $fixtureOut = [System.IO.Path]::GetFullPath([string]$spec.out_dir); $fixtureConfig = [System.IO.Path]::GetFullPath([string]$spec.config_source); $childFile = [System.IO.Path]::GetFullPath([string]$spec.child_file)
  if (-not (Test-Path -LiteralPath $fixtureConfig -PathType Leaf) -or -not (Test-Path -LiteralPath $childFile -PathType Leaf)) { throw 'synthetic fixture input is missing' }
  $fixtureStall = [int]$spec.stall_sec; $fixtureAttempts = [int]$spec.max_attempts
  if ($fixtureStall -le 0 -or $fixtureAttempts -le 0) { throw 'synthetic fixture limits must be positive' }
  $fixtureOut = New-B1aSharedDirectory $fixtureOut 'synthetic fixture output directory'
  $campaignId = [guid]::NewGuid().ToString('N'); $campaignDir = New-B1aExclusiveDirectory (Join-Path $fixtureOut $campaignId) 'synthetic campaign directory'
  for ($fixtureAttempt = 1; $fixtureAttempt -le $fixtureAttempts; $fixtureAttempt++) {
    $runId = [guid]::NewGuid().ToString('N'); $attemptDir = New-B1aExclusiveDirectory (Join-Path $campaignDir ('attempt_{0:00}_{1}' -f $fixtureAttempt,$runId)) 'synthetic attempt directory'
    $configCopy = Join-Path $attemptDir 'generated_config.vbs'; $configHash = Copy-B1aConfigCreateOnce $fixtureConfig $configCopy
    $stdoutPath = Join-Path $attemptDir 'stdout.txt'; $stderrPath = Join-Path $attemptDir 'stderr.txt'
    $childArgs = ([string]$spec.child_arguments).Replace('{attempt}', [string]$fixtureAttempt).Replace('{attempt_dir}', $attemptDir)
    $childEnvironment = @{ RW_QUALIFICATION_MODE='synthetic_fixture'; RW_RUN_ID=$runId; RW_B1A_REQUIRED=$null; RW_SYNTHETIC_ATTEMPT=[string]$fixtureAttempt; RW_SYNTHETIC_ATTEMPT_DIR=$attemptDir; RW_SYNTHETIC_CONFIG_COPY=$configCopy }
    $result = $null; $postConfigOk = $false
    try {
      Assert-B1aConfigMatch $fixtureConfig $configCopy $configHash 'synthetic immediately before launch'
      $result = Invoke-B1aMonitoredProcess $childFile $childArgs $attemptDir $stdoutPath $stderrPath $childEnvironment @($attemptDir) $fixtureStall @()
    } catch {
      Write-B1aAttemptFailure $attemptDir $_.Exception.Message
    } finally {
      try { Assert-B1aConfigMatch $fixtureConfig $configCopy $configHash 'synthetic after termination' ; $postConfigOk = $true } catch { Write-B1aAttemptFailure $attemptDir $_.Exception.Message }
    }
    if ($result -and $result.exit_code -eq 0 -and -not $result.timed_out -and $postConfigOk) {
      Write-Host "SYNTHETIC_FIXTURE_NOT_EVALUATED campaign=$campaignId attempt=$fixtureAttempt run_id=$runId"
      return
    }
    if (-not (Test-Path -LiteralPath (Join-Path $attemptDir 'attempt_failure.txt'))) { Write-B1aAttemptFailure $attemptDir "synthetic attempt failed exit=$($result.exit_code) timeout=$($result.timed_out) termination=$($result.termination_reason) config=$postConfigOk" }
  }
  throw "synthetic fixture failed after $fixtureAttempts attempts"
}

if (-not [string]::IsNullOrWhiteSpace($B1aSyntheticFixtureSpec)) {
  if ($B1aRequired -or $B1aDryRun) { throw 'synthetic fixture cannot be combined with live-required or dry-run mode' }
  Invoke-B1aSyntheticFixtureHarness (Resolve-RepoPath $B1aSyntheticFixtureSpec)
  exit 0
}

if ($B1aDryRun -and -not $B1aRequired) { throw '-B1aDryRun requires -B1aRequired' }
if ($B1aRequired) {
  Invoke-B1aRequiredWatchdog
  exit 0
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$stateCsv = Join-Path $OutDir "state_$Name.csv"
$actionCsv = Join-Path $OutDir "action_$Name.csv"
$bottleneckLinkCsv = Join-Path $OutDir "bottleneck_links_$Name.csv"
$bottleneckSegmentCsv = Join-Path $OutDir "bottleneck_segments_$Name.csv"
$decisionDir = Join-Path $OutDir "decisions_$Name"
$log = Join-Path $OutDir "runlog_$Name.txt"
$vissimErrSource = [System.IO.Path]::ChangeExtension($net, ".err")
$vissimErrEvidencePath = Join-Path $OutDir "vissim_error_evidence_$Name.json"
$vissimErrArtifactPath = Join-Path $OutDir "vissim_network_$Name.err"
$wallTimeProfilePath = Join-Path $OutDir "wall_time_profile_$Name.json"
$runArtifactManifestPath = Join-Path $OutDir "run_artifact_manifest_$Name.json"
$staleErrArchiveRoot = "$OutDir.pre_run_err_archive"
New-Item -ItemType Directory -Force -Path $decisionDir | Out-Null
$runId = [guid]::NewGuid().ToString("N")
$preservedVbsConfig = Join-Path $OutDir "generated_vbs_config_$Name.vbs"
Copy-Item -LiteralPath $vbsConfig -Destination $preservedVbsConfig -Force -ErrorAction Stop

$provenanceFiles = [ordered]@{
  network = Get-ArtifactEvidence $net
  main_vbs_runner = Get-ArtifactEvidence $runner
  watchdog_wrapper = Get-ArtifactEvidence $PSCommandPath
  adapter = Get-ArtifactEvidence $adapter
  calibration = Get-ArtifactEvidence $Calibration
  tuning = Get-ArtifactEvidence $Tuning
  control_mapping = Get-ArtifactEvidence $Mapping
  generated_vbs_config = Get-ArtifactEvidence $vbsConfig
  preserved_generated_vbs_config = Get-ArtifactEvidence $preservedVbsConfig
  vehicle_input_roles = Get-ArtifactEvidence $VehicleInputRoles
  link_assignment = Get-ArtifactEvidence (Join-Path $repo "outputs\link_player_assignment_20260805.json")
  intersection_adjacency = Get-ArtifactEvidence (Join-Path $repo "outputs\intersection_adjacency8_20260805.json")
  storage_capacity = Get-ArtifactEvidence (Join-Path $repo "outputs\urban_storage_capacity_20260805.json")
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
$preflightEvidence = Get-ArtifactEvidence $PreflightManifest
$preflightFingerprint = ""
if ($preflightEvidence.exists) {
  try {
    $preflightPayload = Get-Content -Raw -LiteralPath $PreflightManifest | ConvertFrom-Json
    if ([string]$preflightPayload.status -ne "PASS") { throw "preflight status is not PASS" }
    $preflightFingerprint = [string]$preflightPayload.fingerprint_sha256
    if ([string]::IsNullOrWhiteSpace($preflightFingerprint) -and $null -ne $preflightPayload.fingerprint) {
      $preflightFingerprint = [string]$preflightPayload.fingerprint.sha256
    }
    if ([string]::IsNullOrWhiteSpace($preflightFingerprint)) {
      throw "preflight fingerprint_sha256 is missing"
    }
  } catch {
    throw "Invalid preflight manifest: $($_.Exception.Message)"
  }
}

function Write-JsonAtomic([string]$Path, $Value) {
  $fullPath = [System.IO.Path]::GetFullPath($Path)
  $directory = [System.IO.Path]::GetDirectoryName($fullPath)
  New-Item -ItemType Directory -Force -Path $directory | Out-Null
  $temporary = Join-Path $directory (".{0}.{1}.{2}.tmp" -f [System.IO.Path]::GetFileName($fullPath), $PID, [guid]::NewGuid().ToString("N"))
  try {
    [System.IO.File]::WriteAllText(
      $temporary,
      (($Value | ConvertTo-Json -Depth 12) + "`n"),
      [System.Text.UTF8Encoding]::new($false)
    )
    if (Test-Path -LiteralPath $fullPath -PathType Leaf) {
      [System.IO.File]::Replace($temporary, $fullPath, $null)
    } else {
      [System.IO.File]::Move($temporary, $fullPath)
    }
  } finally {
    if (Test-Path -LiteralPath $temporary -PathType Leaf) {
      Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue
    }
  }
}

function Get-TextSha256([string]$Text) {
  $algorithm = [System.Security.Cryptography.SHA256]::Create()
  try {
    $bytes = [System.Text.UTF8Encoding]::new($false).GetBytes($Text)
    return ([System.BitConverter]::ToString($algorithm.ComputeHash($bytes))).Replace("-", "").ToLowerInvariant()
  } finally {
    $algorithm.Dispose()
  }
}

function Get-PythonIdentity([string]$PythonPath) {
  $artifact = Get-ArtifactEvidence $PythonPath
  if (-not $artifact.exists) { throw "RW_PYTHON_EXE is missing: $PythonPath" }
  $raw = & $artifact.path -B -c "import json,sys; print(json.dumps({'executable':sys.executable,'version':sys.version,'version_triplet':list(sys.version_info[:3])}))"
  if ($LASTEXITCODE -ne 0) { throw "RW_PYTHON_EXE identity probe failed (exit $LASTEXITCODE)" }
  try { $identity = ([string]$raw | ConvertFrom-Json) }
  catch { throw "RW_PYTHON_EXE identity probe returned invalid JSON: $($_.Exception.Message)" }
  $reported = [System.IO.Path]::GetFullPath([string]$identity.executable)
  $expected = [System.IO.Path]::GetFullPath([string]$artifact.path)
  if (-not $reported.Equals($expected, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "RW_PYTHON_EXE identity probe path mismatch: expected=$expected actual=$reported"
  }
  return [ordered]@{
    path = $expected
    exists = $true
    sha256 = [string]$artifact.sha256
    version = [string]$identity.version
    version_triplet = @($identity.version_triplet | ForEach-Object { [int]$_ })
  }
}
$pythonIdentity = Get-PythonIdentity ([Environment]::GetEnvironmentVariable("RW_PYTHON_EXE", "Process"))
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
  python_executable = $pythonIdentity
  preflight_manifest = $preflightEvidence
  preflight_fingerprint_sha256 = $preflightFingerprint
  seed = $Seed
  sim_period_sec = $SimPeriod
  control_interval_sec = $ControlIntervalSec
  control_start_sec = $ControlStartSec
  warmup_controller = $WarmupController
  state_log_interval_sec = $StateLogIntervalSec
  demand_scale = $DemandScale
  demand_profile = $DemandProfile
  controller = $Controller
  audit_anchors_sec = $AuditAnchorsSec
  files = $provenanceFiles
  signal_programs = $signalPrograms
}
$provenancePath = Join-Path $OutDir "run_provenance_$Name.json"
Write-JsonAtomic $provenancePath $provenance

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
}

$staleErrEvidence = @()
function Archive-StaleVissimError([int]$Attempt) {
  if (-not (Test-Path -LiteralPath $vissimErrSource -PathType Leaf)) { return }
  New-Item -ItemType Directory -Force -Path $staleErrArchiveRoot | Out-Null
  $archivePath = Join-Path $staleErrArchiveRoot ("attempt_{0:00}_{1}.err" -f $Attempt, $Name)
  Copy-Item -LiteralPath $vissimErrSource -Destination $archivePath -Force -ErrorAction Stop
  $script:staleErrEvidence += [ordered]@{
    attempt = $Attempt
    source_path = $vissimErrSource
    archived_path = [System.IO.Path]::GetFullPath($archivePath)
    sha256 = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
    archived_at_utc = (Get-Date).ToUniversalTime().ToString("o")
  }
  Remove-Item -LiteralPath $vissimErrSource -Force -ErrorAction Stop
}

function Write-VissimErrorEvidence([int]$Attempt, [int]$ProcessExitCode) {
  $checkedAt = (Get-Date).ToUniversalTime().ToString("o")
  $present = Test-Path -LiteralPath $vissimErrSource -PathType Leaf
  if (Test-Path -LiteralPath $vissimErrArtifactPath -PathType Leaf) {
    Remove-Item -LiteralPath $vissimErrArtifactPath -Force -ErrorAction Stop
  }
  $artifact = $null
  if ($present) {
    Copy-Item -LiteralPath $vissimErrSource -Destination $vissimErrArtifactPath -Force -ErrorAction Stop
    $artifact = Get-ArtifactEvidence $vissimErrArtifactPath
  }
  $bindingText = "run_id=$runId`nrun_name=$Name`nattempt=$Attempt`npresent=$($present.ToString().ToLowerInvariant())`nsource_path=$vissimErrSource`npost_exit_checked_at_utc=$checkedAt"
  Write-JsonAtomic $vissimErrEvidencePath ([ordered]@{
    schema_version = "vissim-error-evidence-v2.1"
    run_id = $runId
    run_name = $Name
    attempt = $Attempt
    process_exit_code = $ProcessExitCode
    source_path = $vissimErrSource
    post_exit_checked_at_utc = $checkedAt
    source_checked_after_process_exit = $true
    present = $present
    artifact = $artifact
    stale_pre_run = @($staleErrEvidence)
    binding_text = $bindingText
    binding_sha256 = Get-TextSha256 $bindingText
  })
}

function Write-WallTimeProfile([int]$Attempt, [datetime]$StartedAt, [datetime]$FinishedAt, [int]$ProcessExitCode) {
  Write-JsonAtomic $wallTimeProfilePath ([ordered]@{
    schema_version = "wall-time-profile-v2.1"
    status = if ($ProcessExitCode -eq 0) { "PASS" } else { "FAIL" }
    run_id = $runId
    run_name = $Name
    attempt = $Attempt
    process_exit_code = $ProcessExitCode
    started_at_utc = $StartedAt.ToUniversalTime().ToString("o")
    finished_at_utc = $FinishedAt.ToUniversalTime().ToString("o")
    elapsed_wall_sec = [math]::Round(($FinishedAt - $StartedAt).TotalSeconds, 6)
  })
}

function Write-RunArtifactManifest([int]$Attempt, [int]$ProcessExitCode) {
  $wallTimeProfile = Get-Content -LiteralPath $wallTimeProfilePath -Raw -Encoding UTF8 | ConvertFrom-Json
  $decisionArtifacts = @(
    Get-ChildItem -LiteralPath $decisionDir -File -ErrorAction Stop |
      Where-Object {
        $_.Name -like "state_*.json" -or $_.Name -like "anchor_*.json" -or
        $_.Name -like "action_*.json" -or $_.Name -like "action_*.csv"
      } |
      Sort-Object Name |
      ForEach-Object { Get-ArtifactEvidence $_.FullName }
  )
  $outputArtifacts = [ordered]@{
    state_csv = Get-ArtifactEvidence $stateCsv
    cumulative_action_csv = Get-ArtifactEvidence $actionCsv
    stdout_runlog = Get-ArtifactEvidence $log
    stderr_runlog = Get-ArtifactEvidence "$log.err"
    signal_readback_csv = Get-ArtifactEvidence (Join-Path $decisionDir "signal_readback.csv")
    generated_vbs_config_copy = Get-ArtifactEvidence $preservedVbsConfig
    vissim_error_evidence = Get-ArtifactEvidence $vissimErrEvidencePath
    wall_time_profile = Get-ArtifactEvidence $wallTimeProfilePath
  }
  $finalizedAt = Get-Date
  Write-JsonAtomic $runArtifactManifestPath ([ordered]@{
    schema_version = "run-artifact-manifest-v2.1"
    status = if ($ProcessExitCode -eq 0) { "PASS" } else { "FAIL" }
    run_id = $runId
    run_name = $Name
    attempt = $Attempt
    process_exit_code = $ProcessExitCode
    finalized_at_utc = $finalizedAt.ToUniversalTime().ToString("o")
    run_window = [ordered]@{
      started_at_utc = [string]$wallTimeProfile.started_at_utc
      finished_at_utc = [string]$wallTimeProfile.finished_at_utc
      filesystem_mtime_tolerance_sec = 2.0
    }
    artifact_roles = [ordered]@{
      simulation_output_keys = @("state_csv", "cumulative_action_csv", "stdout_runlog", "stderr_runlog", "signal_readback_csv")
      post_exit_evidence_keys = @("vissim_error_evidence", "wall_time_profile")
      pre_run_input_keys = @("generated_vbs_config_copy")
      decision_artifacts = "simulation_output"
    }
    run_provenance = Get-ArtifactEvidence $provenancePath
    output_artifacts = $outputArtifacts
    decision_artifacts = $decisionArtifacts
  })
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
  Archive-StaleVissimError $attempt
  foreach ($activeEvidence in @($vissimErrEvidencePath, $vissimErrArtifactPath, $wallTimeProfilePath, $runArtifactManifestPath)) {
    if (Test-Path -LiteralPath $activeEvidence -PathType Leaf) {
      Remove-Item -LiteralPath $activeEvidence -Force -ErrorAction Stop
    }
  }
  Clear-DecisionDir $decisionDir
  $argline = "//nologo " + (Q $runner) + " " + (Q $net) + " " + (Q $stateCsv) + " " + (Q $actionCsv) + " " + (Q $decisionDir) +
    " $SimPeriod $ControlIntervalSec $Seed " + (Q $adapter) + " " + (Q $Calibration) + " " + (Q $Tuning) + " " + (Q $Mapping) +
    " " + (Q $Controller) + " $ControlStartSec " + (Q $WarmupController) + " " + (Q $vbsConfig)
  $argline = $argline + " $StateLogIntervalSec"
  $argline = $argline + " $DemandScale"
  $argline = $argline + " " + (Q $DemandProfile) + " " + (Q $VehicleInputRoles)
  $argline = $argline + " $IncidentLink $IncidentLane $IncidentPos $IncidentStartSec $IncidentEndSec " + (Q $IncidentName)

  $t0 = Get-Date
  Normalize-ProcessPathEnv
  $oldForceStepwise = [Environment]::GetEnvironmentVariable("RW_FORCE_STEPWISE", "Process")
  $oldAuditAnchors = [Environment]::GetEnvironmentVariable("RW_AUDIT_ANCHORS_SEC", "Process")
  $oldRunId = [Environment]::GetEnvironmentVariable("RW_RUN_ID", "Process")
  $oldRunManifest = [Environment]::GetEnvironmentVariable("RW_RUN_MANIFEST_PATH", "Process")
  $oldRwPython = [Environment]::GetEnvironmentVariable("RW_PYTHON", "Process")
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
  [Environment]::SetEnvironmentVariable(
    "RW_PYTHON",
    [Environment]::GetEnvironmentVariable("RW_PYTHON_EXE", "Process"),
    "Process"
  )
  $cscriptExe = Join-Path $env:SystemRoot "System32\cscript.exe"
  if (-not (Test-Path $cscriptExe)) { $cscriptExe = "cscript.exe" }
  $proc = Start-Process -FilePath $cscriptExe -ArgumentList $argline -RedirectStandardOutput $log `
    -RedirectStandardError "$log.err" -WorkingDirectory $repo -PassThru -WindowStyle Hidden
  [Environment]::SetEnvironmentVariable("RW_FORCE_STEPWISE", $oldForceStepwise, "Process")
  [Environment]::SetEnvironmentVariable("RW_AUDIT_ANCHORS_SEC", $oldAuditAnchors, "Process")
  [Environment]::SetEnvironmentVariable("RW_RUN_ID", $oldRunId, "Process")
  [Environment]::SetEnvironmentVariable("RW_RUN_MANIFEST_PATH", $oldRunManifest, "Process")
  [Environment]::SetEnvironmentVariable("RW_PYTHON", $oldRwPython, "Process")
  if (-not $proc -or -not $proc.Id) {
    throw "Failed to start cscript for $Name attempt=$attempt"
  }
  Log "START $Name attempt=$attempt pid=$($proc.Id)"

  while ($true) {
    Start-Sleep -Seconds 20
    if ($proc.HasExited) {
      $done = Select-String -Path $log -Pattern "STAGE=SIM_DONE" -Quiet -ErrorAction SilentlyContinue
      $exitCode = [int]$proc.ExitCode
      if ($done -and $exitCode -eq 0) {
        $finishedAt = Get-Date
        Write-VissimErrorEvidence $attempt $exitCode
        Write-WallTimeProfile $attempt $t0 $finishedAt $exitCode
        Write-RunArtifactManifest $attempt $exitCode
        Log "OK $Name attempt=$attempt elapsed=$([int]((Get-Date)-$t0).TotalSeconds)s"
        exit 0
      }
      Log "EXIT_INCOMPLETE $Name attempt=$attempt stage_done=$done exit_code=$exitCode"
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
