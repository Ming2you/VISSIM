$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$editsPath = Join-Path $PSScriptRoot 'com_execution_startup_edits_v1.json'
$doc = Get-Content -LiteralPath $editsPath -Raw -Encoding UTF8 | ConvertFrom-Json
$target = $doc.targets | Where-Object target -eq 'scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1'
$sourcePath = Join-Path $repo $target.target
if ((Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $target.source_sha256) { throw 'Frozen watchdog source changed' }
$original = [IO.File]::ReadAllText($sourcePath).Replace("`r`n", "`n")
$candidate = $original
foreach ($edit in $target.edits) {
  if ([regex]::Matches($candidate, [regex]::Escape($edit.old)).Count -ne $edit.count) { throw 'Edit occurrence differs' }
  $candidate = $candidate.Replace($edit.old, $edit.new)
}
$tokens = $null; $parseErrors = $null
$tree = [Management.Automation.Language.Parser]::ParseInput($candidate, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count) { throw ($parseErrors | Out-String) }
$oldTree = [Management.Automation.Language.Parser]::ParseInput($original, [ref]$tokens, [ref]$parseErrors)
foreach ($name in @('Find-RunVissimIdentity', 'Stop-RunProcesses')) {
  $newNode = $tree.Find({ param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq $name }, $true)
  $oldNode = $oldTree.Find({ param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq $name }, $true)
  if ($newNode.Extent.Text -cne $oldNode.Extent.Text) { throw "Process ownership function changed: $name" }
}
$functionNode = $tree.Find({ param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Test-SimulationStarted' }, $true)
# Only this pure file-reader function executes, never the watchdog script body.
. ([scriptblock]::Create($functionNode.Extent.Text))
$folder = Join-Path ([IO.Path]::GetTempPath()) ('codex_startup_marker_' + [guid]::NewGuid().ToString('N'))
$null = [IO.Directory]::CreateDirectory($folder)
$csv = Join-Path $folder 'state.csv'; $log = Join-Path $folder 'run.log'
$cases = [Collections.Generic.List[object]]::new()
function Check([string]$Name, [string]$LogText, [string]$CsvText, [bool]$Expected) {
  [IO.File]::WriteAllText($log, $LogText, [Text.Encoding]::ASCII)
  [IO.File]::WriteAllText($csv, $CsvText, [Text.Encoding]::ASCII)
  $actual = Test-SimulationStarted $csv $log
  if ($actual -ne $Expected) { throw "Case $Name expected $Expected got $actual" }
  $cases.Add([ordered]@{ name=$Name; expected=$Expected; actual=$actual })
}
try {
  Check 'actual_positive' "NATIVE_SIM_PROGRESS sim_sec=1.000000`r`n" 'sim_sec,n' $true
  Check 'marker_survives_long_decision_log' ("NATIVE_SIM_PROGRESS sim_sec=1.000000`n" + ('MODEL_WORKING' * 30000)) 'sim_sec,n' $true
  Check 'ordinary_activity_requested_step_not_actual' "STARTUP_STAGE=FIRST_STEP_DONE`nRUN_SINGLE_STEP sim_sec=1`nMODEL_WORKING`n" 'sim_sec,n' $false
  foreach ($value in @('0.000000','-1','NaN','Infinity','notanumber','1x','1,000000')) {
    Check ('reject_marker_' + $value) ("NATIVE_SIM_PROGRESS sim_sec=$value`n") 'sim_sec,n' $false
  }
  Check 'missing_numeric_value' 'NATIVE_SIM_PROGRESS sim_sec=' 'sim_sec,n' $false
  Check 'embedded_marker' "OTHER NATIVE_SIM_PROGRESS sim_sec=1.000000`n" 'sim_sec,n' $false
  Check 'marker_beyond_old_prefix_limit' (('ordinary startup activity' + "`n") * 5000 + "NATIVE_SIM_PROGRESS sim_sec=1.000000`n") 'sim_sec,n' $true
  Check 'state_positive_fallback' "working`n" "sim_sec,n`n1,7`n" $true
  Check 'state_positive_despite_bad_marker' "NATIVE_SIM_PROGRESS sim_sec=NaN`n" "sim_sec,n`n1,7`n" $true
  foreach ($value in @('0','-1','NaN','Infinity','junk')) {
    Check ('reject_state_' + $value) '' ("sim_sec,n`n$value,7`n") $false
  }
  $passed = Test-SimulationStarted $csv (Join-Path $folder 'missing.log')
  if ($passed) { throw 'Missing log plus invalid state must not pass' }
  $cases.Add([ordered]@{name='missing_log_and_invalid_state';expected=$false;actual=$passed})
  $afterHash = (Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash.ToLowerInvariant()
  if ($afterHash -ne $target.source_sha256) { throw 'Production source mutated' }
  [ordered]@{schema='com-startup-marker-focused-validation/v1';passed=$true;tests=$cases.Count;
    cases=@($cases.ToArray());watchdog_source_sha256=$afterHash;production_edits=0;com_runs=0;
    extracted_function_only=$true;full_candidate_powershell_parse=$true;owned_pid_cleanup_unchanged=$true} |
    ConvertTo-Json -Depth 6
} finally {
  # Only these two exact temporary files and the now-empty owned directory.
  if (Test-Path -LiteralPath $csv) { Remove-Item -LiteralPath $csv }
  if (Test-Path -LiteralPath $log) { Remove-Item -LiteralPath $log }
  Remove-Item -LiteralPath $folder
}
