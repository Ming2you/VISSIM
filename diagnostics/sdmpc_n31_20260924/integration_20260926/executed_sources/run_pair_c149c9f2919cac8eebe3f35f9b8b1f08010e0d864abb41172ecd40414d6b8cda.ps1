param([switch]$PreflightOnly,[string]$FrozenTree='', [string]$ProtocolPath='', [string]$ResultsRoot='')
$ErrorActionPreference = 'Stop'
$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../..'))
$taskRoot = $PSScriptRoot
if ($ProtocolPath) { $taskRoot=Split-Path -Parent ([IO.Path]::GetFullPath($ProtocolPath)) }
$selectedRoot = Join-Path (Split-Path -Parent $taskRoot) 'selected'
$runsRoot = 'D:/VISSIM_runs/20260926_selected1200_replay'
if ($ResultsRoot) {$runsRoot=[IO.Path]::GetFullPath($ResultsRoot)}
if ($ProtocolPath -and -not $ResultsRoot) {throw 'A new protocol requires an explicit new result directory'}
$pwshExe = 'C:/Users/alsrj/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
$pythonExe = 'C:/Users/alsrj/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$watchdog = Join-Path $repoRoot 'scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1'
$protocol = Get-Content -LiteralPath (Join-Path $taskRoot 'protocol.json') -Raw | ConvertFrom-Json
$replayController = 'wu-link'
if ($protocol.controller) { $replayController = [string]$protocol.controller }
if ($replayController -notin @('wu-link','diagnostic-ramp-profile')) { throw 'Unsupported replay controller' }
if (-not $PreflightOnly -and $protocol.native_authorization_pending) {
    throw 'This prepared experiment has no native launch authorization; preserve the existing STOP'
}
if ($protocol.arms.Count -ne 2 -or $protocol.start_sec % 150 -or $protocol.end_sec-$protocol.start_sec -ne 450) {
    throw 'Replay requires a finite two-arm,450-second comparison'
}
function Hash([string]$p) { (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() }
function Save-Status([string]$stage, [string]$arm, [object]$more) {
    [ordered]@{stage=$stage; arm=$arm; time=[DateTimeOffset]::Now.ToString('o'); pid=$PID; details=$more} |
      ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $taskRoot 'status.json') -Encoding utf8
}
try {
    Set-Location -LiteralPath $repoRoot
    if (Test-Path -LiteralPath (Join-Path $runsRoot 'STOP')) { throw 'STOP exists; no restart' }
    foreach ($pin in $protocol.command_pins.PSObject.Properties) {
        if ((Hash $pin.Name) -cne $pin.Value) { throw "Changed command source: $($pin.Name)" }
    }
    if ((Hash $protocol.network) -cne $protocol.network_sha256) { throw 'Network source changed' }
    # Physical runtime settings match the completed R3 prefix. Observations are
    # retained for one matched replay; the controller itself is never called.
    foreach ($item in @(Get-ChildItem Env: | Where-Object { $_.Name -like 'RW_*' })) {
        [Environment]::SetEnvironmentVariable($item.Name,$null,'Process')
    }
    $env:RW_PYTHON=$pythonExe; $env:RW_MAINLINE_SG_ONLY='1'; $env:RW_OFFSET_WRITER='experiment'
    $env:RW_RAMP_AMBER_SEC='0'; $env:RW_DECISION_FAIL_FAST='1'; $env:RW_QUEUE_COUNTER='1'
    $env:PYTHONUTF8='1'; $env:PYTHONDONTWRITEBYTECODE='1'
    $env:PYTHONPATH='C:/Users/alsrj/Desktop/학술/찐찐막/Codex/VISSIM/.review-deps/sdmpc;'+$repoRoot
    $env:NUMSIM_REPO_ROOT=Join-Path $repoRoot 'vendor/NumSim-mine'
    $prepared=Join-Path $taskRoot 'launch_inputs.json'
    if (-not (Test-Path -LiteralPath $prepared)) {
        if (Test-Path -LiteralPath $runsRoot) { throw 'Unclaimed result directory exists; preserve it' }
        New-Item -ItemType Directory -Path $runsRoot | Out-Null
        $plans=@()
        foreach ($arm in $protocol.arms) {
            $caseDir=Join-Path $runsRoot $arm
            $networkDir=Join-Path $caseDir 'network'
            New-Item -ItemType Directory -Path $networkDir | Out-Null
            $name='sdmpc31_g_'+$protocol.start_sec+'_'+$arm+'_s'+$protocol.seed
            $network=Join-Path $networkDir ($name+'.inpx')
            Copy-Item -LiteralPath $protocol.network -Destination $network
            Get-ChildItem -LiteralPath (Split-Path -Parent $protocol.network) -Filter '*.sig' |
              ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination $networkDir }
            if ((Hash $network) -cne $protocol.network_sha256) { throw 'Copied network differs' }
            $configDir=Join-Path $taskRoot $arm
            $runnerConfig=Join-Path $configDir 'replay.vbs'
            $text=[IO.File]::ReadAllText((Join-Path $selectedRoot 'scenario/lane_native_b110.vbs'))
            $commands=[IO.Path]::GetRelativePath($repoRoot,(Join-Path $configDir 'commands'))
            $text += "`r`nRW_COMMAND_REPLAY_DIR = `"$commands`"`r`nRW_PYTHON_EXE = `"$pythonExe`"`r`n"
            [IO.File]::WriteAllText($runnerConfig,$text,[Text.UTF8Encoding]::new($false))
            Copy-Item -LiteralPath (Join-Path $selectedRoot 'scenario/lane_native_b110_sgplan.vbs') -Destination (Join-Path $configDir 'replay_sgplan.vbs')
            $manifest=Get-Content -LiteralPath (Join-Path $selectedRoot 'plant_n31_v2.json') -Raw | ConvertFrom-Json
            $manifest.sources.runner_config.path=[IO.Path]::GetRelativePath($repoRoot,$runnerConfig).Replace('\','/')
            $manifest.sources.runner_config.sha256=Hash $runnerConfig
            $manifestPath=Join-Path $configDir 'plant_replay.json'
            $manifest | ConvertTo-Json -Depth 90 | Set-Content -LiteralPath $manifestPath -Encoding utf8
            $tuning=Get-Content -LiteralPath (Join-Path $selectedRoot 'config_n31_v2.json') -Raw | ConvertFrom-Json
            $tuning.freeway.lane_plant=[IO.Path]::GetRelativePath($repoRoot,$manifestPath).Replace('\','/')
            $tuningPath=Join-Path $configDir 'config_replay.json'
            $tuning | ConvertTo-Json -Depth 90 | Set-Content -LiteralPath $tuningPath -Encoding utf8
            $plans += [ordered]@{arm=$arm; name=$name; network=$network; out_dir=$caseDir; tuning=$tuningPath; vbs_config=$runnerConfig}
        }
        $plans | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $prepared -Encoding utf8
    }
    $plans=Get-Content -LiteralPath $prepared -Raw | ConvertFrom-Json
    if (-not $PreflightOnly) {
        if (-not $FrozenTree) { throw 'Native replay requires the existing freeze_worktree verified copy' }
        & $pythonExe -B (Join-Path $FrozenTree 'diagnostics/sdmpc_n31_20260924/tools/freeze_manifest.py') verify $FrozenTree
        if ($LASTEXITCODE -ne 0) { throw 'Frozen runtime verification failed' }
        $watchdog=Join-Path $FrozenTree 'scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1'
        $env:NUMSIM_REPO_ROOT=Join-Path $FrozenTree 'vendor/NumSim-mine'
        $env:PYTHONPATH='C:/Users/alsrj/Desktop/학술/찐찐막/Codex/VISSIM/.review-deps/sdmpc;'+$FrozenTree
        foreach ($plan in $plans) {
            foreach ($field in @('tuning','vbs_config')) {
                $plan.$field=Join-Path $FrozenTree ([IO.Path]::GetRelativePath($repoRoot,$plan.$field))
            }
        }
    }
    foreach ($plan in $plans) {
        if (Test-Path -LiteralPath (Join-Path $runsRoot 'STOP')) { throw 'STOP exists; no next run' }
        $log=Join-Path $plan.out_dir ('runlog_'+$plan.name+'.txt')
        if (Test-Path -LiteralPath $log) { throw "Existing native attempt is preserved: $log" }
        if (-not $PreflightOnly) {
            $live=@(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^Vissim' })
            if ($live.Count) { throw 'VISSIM is already open; no intervention or new launch' }
        }
        $arguments=@('-NoProfile','-File',$watchdog,'-Name',$plan.name,'-Network',$plan.network,
          '-OutDir',$plan.out_dir,'-SimPeriod',[string]$protocol.end_sec,'-ControlIntervalSec','150','-Seed',[string]$protocol.seed,
          '-Controller',$replayController,'-ControlStartSec','900','-WarmupController','no-control',
          '-StateLogIntervalSec','150','-DemandScale','1','-DemandProfile',(Join-Path $selectedRoot 'scenario/profile.csv'),
          '-VehicleInputRoles',(Join-Path $repoRoot 'evaluation/real_world_modi_inventory/vehicle_input_roles.csv'),
          '-UrbanInputGateMap',(Join-Path $repoRoot 'evaluation/real_world_modi_inventory/urban_input_gate_map_ver2_20260907.csv'),
          '-Calibration',(Join-Path $repoRoot 'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'),
          '-Mapping',(Join-Path $repoRoot 'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json'),
          '-Tuning',$plan.tuning,'-VbsConfig',$plan.vbs_config,'-NoGlobalKill','-MaxAttempts','1',
          '-StartupStallSec','300','-StallSec','2400')
        if ($PreflightOnly) { $arguments += '-PreflightOnly' }
        Save-Status $(if ($PreflightOnly) {'preflight'} else {'native_running'}) $plan.arm $plan
        $launchLog=Join-Path $plan.out_dir $(if ($PreflightOnly) {'preflight.log'} else {'launch.log'})
        & $pwshExe @arguments *> $launchLog
        if ($LASTEXITCODE -ne 0) { throw "Watchdog/preflight failed; inspect $launchLog" }
        if (-not $PreflightOnly) {
            if (-not (Select-String -LiteralPath $log -Pattern '^STAGE=SIM_DONE' -Quiet)) { throw "No SIM_DONE: $log" }
            Save-Status 'native_arm_complete' $plan.arm $plan
        }
    }
    Save-Status $(if ($PreflightOnly) {'preflight_complete'} else {'both_native_complete_unanalyzed'}) '' $plans
} catch {
    Save-Status 'failed' '' ([string]$_)
    Write-Error $_
    exit 1
}
