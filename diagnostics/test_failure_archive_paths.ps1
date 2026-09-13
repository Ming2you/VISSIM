param([Parameter(Mandatory=$true)][string]$Fixture)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$fixtureRoot = [IO.Path]::GetFullPath((Join-Path $repo $Fixture))
if (-not $fixtureRoot.StartsWith($repo + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Fixture must stay inside the repository' }
if (Test-Path -LiteralPath $fixtureRoot) { throw 'Use a fresh fixture; preserve prior evidence' }
$source = Join-Path $repo 'scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1'
$tokens = $null; $parseErrors = $null
$ast = [Management.Automation.Language.Parser]::ParseFile($source, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count) { throw 'Watchdog parse failure' }
$definition = $ast.Find({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Archive-AttemptOutputs'}, $true)
if (-not $definition) { throw 'Missing canonical archive function' }
. ([scriptblock]::Create($definition.Extent.Text))
# Only the native ERR producer is a fixture; the actual archive function runs.
function Copy-VissimError([string]$DestinationDir) {
  Copy-Item -LiteralPath $fixtureNativeErr -Destination (Join-Path $DestinationDir 'vissim_simulation_001.err') -Force
}
New-Item -ItemType Directory -Path $fixtureRoot | Out-Null
$Name = 'codex_phys8_fidelity_fw080_u050_cl9000_s13_v1'
$OutDir = Join-Path $fixtureRoot $Name
New-Item -ItemType Directory -Path $OutDir | Out-Null
$fixtureNativeErr = Join-Path $OutDir 'native_fixture.err'
[IO.File]::WriteAllText($fixtureNativeErr, 'fixture ERR')
$stateCsv = Join-Path $OutDir "state_$Name.csv"
$actionCsv = Join-Path $OutDir "action_$Name.csv"
$bottleneckLinkCsv = Join-Path $OutDir "bottleneck_links_$Name.csv"
$bottleneckSegmentCsv = Join-Path $OutDir "bottleneck_segments_$Name.csv"
$log = Join-Path $OutDir "runlog_$Name.txt"
$files = @($stateCsv, $actionCsv, $bottleneckLinkCsv, $bottleneckSegmentCsv, $log, "$log.err")
foreach ($path in $files) { [IO.File]::WriteAllText($path, ('fixture ' + [IO.Path]::GetFileName($path))) }
$decisionDir = Join-Path $OutDir "decisions_$Name"
New-Item -ItemType Directory -Path $decisionDir | Out-Null
$decisions = @('state_003150.json', 'action_003000.joint.json', 'action_003000.csv')
foreach ($decisionName in $decisions) { [IO.File]::WriteAllText((Join-Path $decisionDir $decisionName), ('fixture ' + $decisionName)) }
$legacy = Join-Path (Join-Path $OutDir ("attempt_01_$Name")) ([IO.Path]::GetFileName($bottleneckSegmentCsv))
if ($legacy.Length -le 260) { throw 'Fixture did not reproduce the failed legacy path length' }
Archive-AttemptOutputs 1
$archive = Join-Path $OutDir 'attempt_01'
$checks = @()
foreach ($path in $files) {
  $copy = Join-Path $archive ([IO.Path]::GetFileName($path))
  $equal = (Get-FileHash -LiteralPath $path).Hash -eq (Get-FileHash -LiteralPath $copy).Hash
  if (-not $equal) { throw 'Archived top-level bytes differ' }
  $checks += [ordered]@{source=$path; archived=$copy; bytes_equal=$equal; archived_path_length=$copy.Length}
}
foreach ($decisionName in $decisions) {
  $path = Join-Path $decisionDir $decisionName
  $copy = Join-Path (Join-Path $archive 'decisions') $decisionName
  $equal = (Get-FileHash -LiteralPath $path).Hash -eq (Get-FileHash -LiteralPath $copy).Hash
  if (-not $equal) { throw 'Archived decision bytes differ' }
  $checks += [ordered]@{source=$path; archived=$copy; bytes_equal=$equal; archived_path_length=$copy.Length}
}
if ([IO.File]::ReadAllText((Join-Path $archive 'vissim_simulation_001.err')) -ne 'fixture ERR') { throw 'Native ERR producer was not called' }
# Different Names may use the default/shared OutDir. Reuse the same decision
# basename and numbered ERR basename so a namespace collision cannot pass.
$dedicatedMaxPath = ($checks.archived_path_length | Measure-Object -Maximum).Maximum
$sharedOutDir = Join-Path $fixtureRoot 'shared'
New-Item -ItemType Directory -Path $sharedOutDir | Out-Null
$sharedChecks = @()
foreach ($Name in @('case_a', 'case_b')) {
  # Normalize a trailing separator before deciding whether OutDir is dedicated.
  $OutDir = $sharedOutDir + [IO.Path]::DirectorySeparatorChar
  $stateCsv = Join-Path $OutDir "state_$Name.csv"
  $actionCsv = Join-Path $OutDir "action_$Name.csv"
  $bottleneckLinkCsv = Join-Path $OutDir "bottleneck_links_$Name.csv"
  $bottleneckSegmentCsv = Join-Path $OutDir "bottleneck_segments_$Name.csv"
  $log = Join-Path $OutDir "runlog_$Name.txt"
  $files = @($stateCsv, $actionCsv, $bottleneckLinkCsv, $bottleneckSegmentCsv, $log, "$log.err")
  foreach ($path in $files) { [IO.File]::WriteAllText($path, ('fixture ' + $Name + ' ' + [IO.Path]::GetFileName($path))) }
  $decisionDir = Join-Path $OutDir "decisions_$Name"
  New-Item -ItemType Directory -Path $decisionDir | Out-Null
  $decisionPath = Join-Path $decisionDir 'action_003000.json'
  [IO.File]::WriteAllText($decisionPath, ('decision ' + $Name))
  $fixtureNativeErr = Join-Path $OutDir "native_$Name.err"
  [IO.File]::WriteAllText($fixtureNativeErr, ('native ERR ' + $Name))
  $archive = Join-Path $OutDir ("attempt_01_$Name")
  foreach ($path in @($files) + @($decisionPath, $fixtureNativeErr)) {
    $relative = if ($path -eq $decisionPath) { 'decisions/action_003000.json' } elseif ($path -eq $fixtureNativeErr) { 'vissim_simulation_001.err' } else { [IO.Path]::GetFileName($path) }
    $sharedChecks += [ordered]@{name=$Name; source=$path; archived=(Join-Path $archive $relative); original_sha256=(Get-FileHash -LiteralPath $path).Hash.ToLowerInvariant()}
  }
  Archive-AttemptOutputs 1
}
# Read both cases after the second archive: the first sources and copies must
# still match the SHA captured before either archive could replace evidence.
foreach ($check in $sharedChecks) {
  if ((Get-FileHash -LiteralPath $check.source).Hash.ToLowerInvariant() -cne $check.original_sha256) { throw 'Shared first/second source bytes changed' }
  if ((Get-FileHash -LiteralPath $check.archived).Hash.ToLowerInvariant() -cne $check.original_sha256) { throw 'Shared first/second archive missing or changed' }
  $check.bytes_equal = $true
}
if (Test-Path -LiteralPath (Join-Path $sharedOutDir 'attempt_01')) { throw 'Shared OutDir must retain per-Name archive namespaces' }
$result = [ordered]@{passed=$true; scope='Real PowerShell archive function with fixture files; no VISSIM/model execution'; source=$source; source_sha256=(Get-FileHash -LiteralPath $source).Hash.ToLower(); legacy_failing_path_length=$legacy.Length; copied_files=$checks.Count; checks=$checks; native_ERR_fixture_preserved=$true; shared_case_count=2; shared_copied_files=$sharedChecks.Count; shared_checks=$sharedChecks; shared_sources_and_archives_unchanged=$true}
$result | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $fixtureRoot 'result.json') -Encoding UTF8
[ordered]@{passed=$true; copied_files=$checks.Count; legacy_path_length=$legacy.Length; max_archived_path_length=$dedicatedMaxPath; shared_case_count=2; shared_copied_files=$sharedChecks.Count; shared_sources_and_archives_unchanged=$true} | ConvertTo-Json -Compress
