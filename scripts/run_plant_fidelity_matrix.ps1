<#
.SYNOPSIS
Run the strict VISSIM plant-fidelity baseline or demand/seed matrix.

.DESCRIPTION
Run the fixed/no-control VISSIM fidelity baseline matrix sequentially.

The runner deliberately invokes one VISSIM process at a time. Each case keeps
its state/action JSON, logs, VISSIM error file, and provenance manifest through
the watchdog wrapper.
#>
[CmdletBinding()]
param(
  [string]$OutDir = "evaluation\runs\plant_fidelity_audit_20260805",
  [int]$SimPeriod = 3600,
  [int]$WarmupSec = 900,
  [int]$StateLogIntervalSec = 5,
  [int[]]$Seeds = @(13, 29, 47),
  [double[]]$DemandScales = @(0.75, 1.0, 1.25),
  [string]$RuntimeSourceManifest = "outputs\runtime_source_v2_1.json",
  [string]$PreflightManifest = "outputs\preflight_manifest_v3.json",
  [string]$TopologyApproval = "outputs\topology_approval_v2_1.json",
  [string]$AuditJsonManifest = "outputs\baseline_generic_audit_v2.json",
  [string]$AuditMarkdownReport = "reports\baseline_generic_audit_v2.md",
  [string]$BaselineSnapshotManifest = "outputs\baseline_snapshot_v2_1.json",
  [switch]$BaselineOnly,
  [switch]$Strict,
  [switch]$RequireComplete,
  [switch]$DryRun,
  [Alias("?")][switch]$Help
)

$ErrorActionPreference = "Stop"
if ($Help) {
  Get-Help $PSCommandPath -Full
  exit 0
}
$b1aMode = [bool]($Strict -and $RequireComplete)
if ([bool]$Strict -ne [bool]$RequireComplete) {
  throw "Plant fidelity B1a runs require both -Strict and -RequireComplete, or neither for legacy mode"
}
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$watchdog = Join-Path $PSScriptRoot "run_real_world_single_watchdog_distributed_core15n41.ps1"

if ($BaselineOnly -and ($SimPeriod -ne 3600 -or $WarmupSec -ne 900)) {
  throw "-BaselineOnly requires SimPeriod=3600 and WarmupSec=900"
}

$python = $env:RW_PYTHON_EXE
if (-not $python -or -not (Test-Path -LiteralPath $python -PathType Leaf)) {
  throw "RW_PYTHON_EXE must name an existing Python executable"
}
$python = (Resolve-Path -LiteralPath $python).Path
$numsimRoot = $env:NUMSIM_REPO_ROOT
if ([string]::IsNullOrWhiteSpace($numsimRoot)) {
  $numsimRoot = Join-Path $repo "vendor\NumSim-mine"
}
if (-not [System.IO.Path]::IsPathRooted($numsimRoot)) {
  $numsimRoot = Join-Path $repo $numsimRoot
}
$numsimRoot = [System.IO.Path]::GetFullPath($numsimRoot)

if (-not [System.IO.Path]::IsPathRooted($OutDir)) {
  $OutDir = Join-Path $repo $OutDir
}
$OutDir = [System.IO.Path]::GetFullPath($OutDir)
foreach ($manifestVariable in @("RuntimeSourceManifest", "PreflightManifest", "TopologyApproval", "AuditJsonManifest", "AuditMarkdownReport", "BaselineSnapshotManifest")) {
  $value = Get-Variable -Name $manifestVariable -ValueOnly
  if (-not [System.IO.Path]::IsPathRooted($value)) {
    $value = Join-Path $repo $value
  }
  Set-Variable -Name $manifestVariable -Value ([System.IO.Path]::GetFullPath($value))
}
if (-not $DryRun -and (Test-Path -LiteralPath $OutDir)) {
  $existing = @(Get-ChildItem -LiteralPath $OutDir -Force -ErrorAction Stop)
  if ($existing.Count -gt 0) {
    throw "Strict run output directory must be new or empty: $OutDir"
  }
}
if (-not $DryRun -and $BaselineOnly -and (Test-Path -LiteralPath $BaselineSnapshotManifest -PathType Leaf)) {
  Remove-Item -LiteralPath $BaselineSnapshotManifest -Force -ErrorAction Stop
}
if (-not $DryRun) {
  foreach ($auditOutput in @($AuditJsonManifest, $AuditMarkdownReport)) {
    if (Test-Path -LiteralPath $auditOutput -PathType Leaf) {
      Remove-Item -LiteralPath $auditOutput -Force -ErrorAction Stop
    }
  }
}

if ($b1aMode -and -not $DryRun) {
  $sourceVerifier = Join-Path $PSScriptRoot "verify_runtime_source.py"
  & $python -B $sourceVerifier --repo $repo --out $RuntimeSourceManifest --strict
  if ($LASTEXITCODE -ne 0) { throw "Runtime source verification failed (exit $LASTEXITCODE)" }
  $preflightBuilder = Join-Path $PSScriptRoot "build_preflight_manifest.py"
  & $python -B $preflightBuilder --repo $repo --runtime-source $RuntimeSourceManifest --watchdog $watchdog --out $PreflightManifest --strict
  if ($LASTEXITCODE -ne 0) { throw "Preflight verification failed (exit $LASTEXITCODE)" }
}

$cases = @()
if ($BaselineOnly) {
  $cases += [pscustomobject]@{ Label = "nominal"; Scale = 1.0; Seed = 13 }
} else {
  foreach ($scale in $DemandScales) {
    $label = if ($scale -lt 1.0) { "low" } elseif ($scale -gt 1.0) { "congested" } else { "nominal" }
    foreach ($seed in $Seeds) {
      $cases += [pscustomobject]@{ Label = $label; Scale = [double]$scale; Seed = [int]$seed }
    }
  }
}

Write-Host "Plant fidelity matrix: $($cases.Count) sequential case(s)"
$dryRunFailures = 0
foreach ($case in $cases) {
  $scaleTag = ([string]::Format([Globalization.CultureInfo]::InvariantCulture, "{0:0.00}", $case.Scale)).Replace(".", "p")
  $name = "fixed_nocontrol_$($case.Label)_d$scaleTag`_seed$($case.Seed)"
  $arguments = @{
    Name = $name
    OutDir = $OutDir
    SimPeriod = $SimPeriod
    ControlIntervalSec = 60
    ControlStartSec = $WarmupSec
    WarmupController = "no-control"
    Controller = "no-control"
    Seed = $case.Seed
    StateLogIntervalSec = $StateLogIntervalSec
    DemandScale = $case.Scale
    AuditAnchorsSec = "900,1500,2100,2700"
    MaxAttempts = 3
  }
  if ($b1aMode) {
    $arguments.PreflightManifest = $PreflightManifest
    $arguments.TopologyApproval = $TopologyApproval
    $arguments.B1aRequired = $true
    $arguments.B1aDryRun = $DryRun
  }

  if ($DryRun) {
    Write-Host "DRY_RUN $name demand=$($case.Scale) seed=$($case.Seed)"
    if ($b1aMode) {
      $watchdogExit = 0
      $watchdogReason = ""
      try {
        & $watchdog @arguments
        $watchdogExit = $LASTEXITCODE
      } catch {
        $watchdogExit = 1
        $watchdogReason = $_.Exception.Message
      }
      if ($watchdogExit -ne 0) {
        $dryRunFailures += 1
        Write-Host "DRY_RUN_B1A_NOT_EVALUATED name=$name exit=$watchdogExit reason=$watchdogReason"
      }
    }
    continue
  }

  Write-Host "RUN $name demand=$($case.Scale) seed=$($case.Seed)"
  & $watchdog @arguments
  if ($LASTEXITCODE -ne 0) {
    throw "Plant fidelity case failed: $name (exit $LASTEXITCODE)"
  }
}

if (-not $DryRun) {
  $audit = Join-Path $PSScriptRoot "audit_plant_fidelity.py"
  $auditArguments = @(
    "-B", $audit,
    "--repo", $repo,
    "--action-dir", $OutDir,
    "--numsim-root", $numsimRoot,
    "--json-out", $AuditJsonManifest,
    "--markdown-out", $AuditMarkdownReport
  )
  $auditArguments += @("--strict", "--require-complete")
  foreach ($gateName in @(
      "input_provenance",
      "network_xml",
      "signal_controller_scope",
      "link_partition",
      "assignment_ties",
      "adjacency",
      "storage_capacity",
      "vendor_snapshot",
      "numsim_source_match",
      "state_observation_contract",
      "action_inventory",
      "projection_diagnostics",
      "runtime_provenance",
      "preflight_provenance",
      "vissim_error_log"
  )) {
    $auditArguments += @("--required-gate", $gateName)
  }
  & $python @auditArguments
  if ($LASTEXITCODE -ne 0) {
    throw "Static/dynamic evidence aggregation failed (exit $LASTEXITCODE)"
  }
  if ($BaselineOnly) {
    $baselineValidator = Join-Path $PSScriptRoot "validate_baseline_snapshot.py"
    & $python -B $baselineValidator $OutDir --runtime-source $RuntimeSourceManifest --preflight $PreflightManifest --audit $AuditJsonManifest --out $BaselineSnapshotManifest --strict --require-complete
    if ($LASTEXITCODE -ne 0) {
      throw "Baseline snapshot validation failed (exit $LASTEXITCODE)"
    }
  }
}

if ($DryRun -and $dryRunFailures -gt 0) {
  Write-Host "B1A_DRY_RUN_NOT_EVALUATED cases=$dryRunFailures"
}

Write-Host "DONE plant fidelity matrix"
