param(
  [Parameter(Mandatory=$true)][string]$SelectedPrepared,
  [Parameter(Mandatory=$true)][string]$Tuning,
  [Parameter(Mandatory=$true)][ValidatePattern('^[A-Za-z0-9_-]+$')][string]$Name,
  [ValidateSet('wu-link','no-control','diagnostic-signal-profile','diagnostic-rule-profile')][string]$Controller='wu-link',
  # Short diagnostics remain the default; selected recovery comparisons use9000.
  [ValidateRange(1050,9000)][int]$SimPeriod=1050,
  [int]$ControlStartSec=900,
  [int]$Seed=13,
  [ValidateSet('decision','full')][string]$StateLogMode='decision',
  [ValidateSet(30,150)][int]$StateLogIntervalSec=150,
  [string]$DemandDirectory='',
  [switch]$DenseSignalAudit,
  [string]$Python='C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe',
  [switch]$Execute
)
$ErrorActionPreference='Stop'
$repo=Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $repo
if ($SimPeriod % 150) { throw 'SimPeriod must end on a150-second boundary' }
if ($ControlStartSec -lt 150 -or $ControlStartSec % 150 -or $ControlStartSec -ge $SimPeriod) { throw 'ControlStartSec must precede SimPeriod on a positive150-second boundary' }
if ($Seed -lt 1) { throw 'Seed must be positive' }
$selected=(Resolve-Path -LiteralPath $SelectedPrepared).Path
$config=(Resolve-Path -LiteralPath $Tuning).Path
$output=Join-Path $repo ('evaluation/runs/'+$Name)
if (Test-Path -LiteralPath $output) { throw 'Require a new run output' }
$profileDirectory=if ($DemandDirectory) { if ([IO.Path]::IsPathRooted($DemandDirectory)) { [IO.Path]::GetFullPath($DemandDirectory) } else { [IO.Path]::GetFullPath((Join-Path $repo $DemandDirectory)) } } else { Join-Path $repo ('diagnostics/selected_control_demand/'+$Name) }
# Match diagnostic_environment()'s explicit bootstrap removal before starting any
# Python process. Keep unrelated PYTHONPATH entries, never activate a trace here.
Get-ChildItem Env: | Where-Object Name -like 'RW_*' | ForEach-Object { Remove-Item -LiteralPath ('Env:'+$_.Name) }
$bootstraps=@('phase_trace_bootstrap','decision_profile_bootstrap','evaluation_trace_bootstrap','decision_resource_bootstrap') | ForEach-Object { [IO.Path]::GetFullPath((Join-Path $PSScriptRoot $_)) }
$env:PYTHONPATH=(@($env:PYTHONPATH -split [IO.Path]::PathSeparator | Where-Object { $_ -and [IO.Path]::GetFullPath($_) -notin $bootstraps }) -join [IO.Path]::PathSeparator)
$helper=Join-Path $PSScriptRoot 'prepare_selected_control_demand.py'
$proofText=& $Python -B -X utf8 $helper --selected-prepared $selected --tuning $config --output $profileDirectory --plan
if ($LASTEXITCODE -ne 0) { throw 'Selected204 demand cannot use canonical multiplier profile' }
$proof=$proofText | ConvertFrom-Json
$configDoc=Get-Content -LiteralPath $config -Raw -Encoding UTF8 | ConvertFrom-Json
# The current chosen v4 config is flattened and uses the per-second physical
# head observer. Do not silently degrade a legacy measured30-second estimator.
if ($configDoc.extends) { throw 'Pass a flattened controller tuning file' }
if ($configDoc.urban.capacity.measured -and !$configDoc.urban.capacity.head_observation.enabled -and
    ($StateLogMode -ne 'full' -or $StateLogIntervalSec -ne 30)) {
  throw 'Legacy measured capacity requires explicit full30-second scans; head-observer ON supports decision/150 logs'
}
if ($configDoc.actuation.real_world_signal_control.apply_to_no_control) { throw 'Warmup must leave urban signals native' }
$frozenSignalReplay=$Controller -eq 'diagnostic-signal-profile'
$ruleBaseline=$Controller -eq 'diagnostic-rule-profile'
if ($frozenSignalReplay) {
  if ($null -ne $configDoc.adapter.joint_owner_game) { throw 'Frozen replay must not configure a joint solver' }
  if ($null -eq $configDoc.diagnostic.signal_profile -or
      !$configDoc.diagnostic.signal_profile.source_action_csv -or
      !$configDoc.diagnostic.signal_profile.source_action_csv_sha256) { throw 'Frozen replay requires pinned source command CSV' }
  if ($configDoc.actuation.real_world_signal_control.offset_writer -ne 'test_only') { throw 'Frozen replay requires the explicit test_only offset writer' }
  if ($configDoc.urban.capacity.head_observation.enabled -ne $true -or
      $configDoc.execution.native_signal_record -ne $true) { throw 'Frozen replay must retain head observations and native signal recording' }
}
$arguments=@{
  Name=$Name;Controller=$Controller;Network=$proof.network;OutDir=$output;Tuning=$proof.controller_tuning;
  Calibration='evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json';
  Mapping='evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json';
  VbsConfig=$(if ($proof.vbs_config) { $proof.vbs_config } else { 'evaluation/real_world_modi_control_ver2n21_20260907/real_world_modi_control_config_ver2n21.vbs' });
  UrbanInputGateMap='evaluation/real_world_modi_inventory/urban_input_gate_map_ver2_20260907.csv';
  VehicleInputRoles='evaluation/real_world_modi_inventory/vehicle_input_roles.csv';
  DemandProfile=(Join-Path $profileDirectory 'profile.csv');DemandScale=1;
  SimPeriod=$SimPeriod;ControlIntervalSec=150;ControlStartSec=$ControlStartSec;WarmupController='no-control';Seed=$Seed;
  StateLogIntervalSec=$StateLogIntervalSec;StartupStallSec=300;StallSec=2400;MaxAttempts=1;NoGlobalKill=$true
}
if ($frozenSignalReplay) { $arguments.ForceStepwise=$true }
if ($ruleBaseline) {
  if (-not $configDoc.diagnostic.rule_profile.enabled -or $configDoc.diagnostic.rule_profile.control_start_sec -ne $ControlStartSec) { throw 'Rule profile must declare the actual control start' }
  $arguments.WarmupController='diagnostic-rule-profile'
  $arguments.ForceStepwise=$true
}
if ($proof.native_signal_record) {
  $arguments.Network=$proof.runtime_network
  $arguments.NetworkRecordingProof=$proof.network_recording_proof.path
}
$fastSignalExecution=[bool]$proof.native_signal_record -and -not $DenseSignalAudit
$plan=[ordered]@{execute=[bool]$Execute;selected_demand=$proof;arguments=$arguments;state_log_mode=$StateLogMode;
  observer_note='head_observation ON still performs required1-second head/vehicle observations; decision/150 suppresses only extra trace scans/rows';
  warmup_note="Same native network, demand within1e-10vph, VSL120 and open meters; actual first${ControlStartSec}s FZP equality remains a one-time runtime gate";
  native_profile_note='New native_internal_inputs and shared_approach declarations change only demand_profile plus derivation; config changes only those two declaration paths; existing validators remain active'}
if ($proof.native_signal_record) { $plan.signal_execution_mode=if ($fastSignalExecution) {'changed_writes_native_postcheck'} else {'dense_diagnostic_native_postcheck'} }
if ($ruleBaseline) { $plan.warmup_note="All four rule arms use VSL100 and open meters from the first command through ${ControlStartSec}s; native urban signals remain unchanged" }
if (-not $Execute) { $plan | ConvertTo-Json -Depth 8; exit 0 }
if (@(Get-Process -Name VISSIM200,VISSIM200CL -ErrorAction SilentlyContinue).Count) { throw 'Existing native VISSIM process: refuse concurrent execution (no process is stopped)' }
if (Test-Path -LiteralPath $profileDirectory) { throw 'Require new demand directory (no profile overwrite)' }
& $Python -B -X utf8 $helper --selected-prepared $selected --tuning $config --output $profileDirectory
if ($LASTEXITCODE -ne 0) { throw 'Demand profile preparation failed' }
$plan | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $profileDirectory 'launch.json') -Encoding UTF8
# Only this process environment changes. The canonical watchdog records its own
# runtime provenance and owns exact-PID timeout cleanup; no second watchdog.
$env:PYTHONUTF8='1'; $env:RW_PYTHON=$Python
$env:RW_OFFSET_WRITER=if ($frozenSignalReplay) {'test_only'} else {'experiment'}
$env:RW_NATIVE_EVAL='1'; $env:RW_VEHREC_RESOLUTION='1'; $env:RW_VEHICLE_ROUTES='1'
$env:RW_QUEUE_COUNTER='1'; $env:RW_QUEUE_WINDOW='1'; $env:RW_STATE_LOG=$StateLogMode
$env:RW_SIGNAL_READBACK_SEC=if ($fastSignalExecution) {'0'} else {'1'}
$env:RW_SIGNAL_WRITE_ON_CHANGE=if ($fastSignalExecution) {'1'} else {'0'}
if ($proof.native_signal_record) { $env:RW_PERF='1' }
# Separate PS process makes watchdog exit status explicit and lets this wrapper
# write a completion receipt. No duplicate timeout/kill policy is introduced.
New-Item -ItemType Directory -Path $output | Out-Null
$watchdog=Join-Path $repo 'scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1'
$argumentJson=($arguments | ConvertTo-Json -Compress).Replace("'","''")
$childCode="`$doc=ConvertFrom-Json '$argumentJson'; `$a=@{}; foreach (`$p in `$doc.PSObject.Properties) { `$a[`$p.Name]=`$p.Value }; & '"+$watchdog.Replace("'","''")+"' @a; exit `$LASTEXITCODE"
$encoded=[Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($childCode))
$existingIds=@(Get-Process -Name VISSIM200,VISSIM200CL -ErrorAction SilentlyContinue | ForEach-Object Id)
$started=Get-Date; $identity=$null; $ownershipAmbiguous=$false
$child=Start-Process -FilePath (Join-Path $env:SystemRoot 'System32/WindowsPowerShell/v1.0/powershell.exe') -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-EncodedCommand',$encoded) -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $output 'watchdog_stdout.txt') -RedirectStandardError (Join-Path $output 'watchdog_stderr.txt')
$childHandle=$child.Handle
while (-not $child.HasExited) {
  if ($null -eq $identity) {
    $nativeMatches=@(Get-Process -Name VISSIM200,VISSIM200CL -ErrorAction SilentlyContinue | Where-Object {
      $_.Id -notin $existingIds -and $_.StartTime -ge $started -and $_.MainWindowTitle.IndexOf([IO.Path]::GetFileName($proof.network),[StringComparison]::OrdinalIgnoreCase) -ge 0
    })
    if ($nativeMatches.Count -eq 1) { $identity=[ordered]@{pid=$nativeMatches[0].Id;started=$nativeMatches[0].StartTime.ToUniversalTime().ToString('o')} }
    if ($nativeMatches.Count -gt 1) { $ownershipAmbiguous=$true }
  }
  Start-Sleep -Milliseconds 1000
}
$child.WaitForExit(); $watchdogExit=$child.ExitCode
$alive=$null
if ($identity -and -not $ownershipAmbiguous) {
  $deadline=(Get-Date).AddSeconds(20)
  do {
    $p=Get-Process -Id $identity.pid -ErrorAction SilentlyContinue
    $alive=[bool]($p -and $p.StartTime.ToUniversalTime().ToString('o') -eq $identity.started)
    if ($alive) { Start-Sleep -Milliseconds 250 }
  } while ($alive -and (Get-Date) -lt $deadline)
}
$observation=[ordered]@{watchdog_exit_code=$watchdogExit;watchdog_pid=$child.Id;watchdog_start=$child.StartTime.ToUniversalTime().ToString('o');owned_native=$identity;owned_native_alive=$alive;ownership_ambiguous=$ownershipAmbiguous;started=$started.ToUniversalTime().ToString('o');finished=(Get-Date).ToUniversalTime().ToString('o')}
$observationPath=Join-Path $output 'wrapper_exit_observation.json'
$observation | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $observationPath -Encoding UTF8
& $Python -B -X utf8 (Join-Path $PSScriptRoot 'selected_control_completion.py') --run $output --name $Name --terminal $SimPeriod --observation $observationPath --checks (Join-Path $profileDirectory 'checks.json')
if ($LASTEXITCODE -ne 0) { exit 1 }
exit $watchdogExit
