<#
Run the fixed/no-control VISSIM fidelity baseline matrix sequentially.

The runner deliberately invokes one VISSIM process at a time. Each case keeps
its state/action JSON, logs, VISSIM error file, and provenance manifest through
the watchdog wrapper.
#>
param(
  [string]$OutDir = "evaluation\runs\plant_fidelity_audit_20260805",
  [int]$SimPeriod = 3600,
  [int]$WarmupSec = 900,
  [int]$StateLogIntervalSec = 5,
  [int[]]$Seeds = @(13, 29, 47),
  [double[]]$DemandScales = @(0.75, 1.0, 1.25),
  [switch]$BaselineOnly,
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$watchdog = Join-Path $PSScriptRoot "run_real_world_single_watchdog_distributed_core15n41.ps1"

if (-not [System.IO.Path]::IsPathRooted($OutDir)) {
  $OutDir = Join-Path $repo $OutDir
}
$OutDir = [System.IO.Path]::GetFullPath($OutDir)

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

  if ($DryRun) {
    Write-Host "DRY_RUN $name demand=$($case.Scale) seed=$($case.Seed)"
    continue
  }

  Write-Host "RUN $name demand=$($case.Scale) seed=$($case.Seed)"
  & $watchdog @arguments
  if ($LASTEXITCODE -ne 0) {
    throw "Plant fidelity case failed: $name (exit $LASTEXITCODE)"
  }
}

if (-not $DryRun) {
  $python = $env:RW_PYTHON_EXE
  if (-not $python) { $python = "python" }
  $audit = Join-Path $PSScriptRoot "audit_plant_fidelity.py"
  & $python -B $audit --repo $repo --action-dir $OutDir
  if ($LASTEXITCODE -ne 0) {
    throw "Static/dynamic evidence aggregation failed (exit $LASTEXITCODE)"
  }
}

Write-Host "DONE plant fidelity matrix"
