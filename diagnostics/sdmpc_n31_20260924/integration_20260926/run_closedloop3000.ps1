param([switch]$PreflightOnly,[string]$FrozenTree='', [string]$ResultsRoot='', [switch]$ResumeAfterCompletedNc,
      [switch]$Detached,
      [string]$StatusPath='',
      [string]$TuningRelativePath='',
      [ValidateRange(1,2147483647)][int]$Seed=29,
      [ValidateRange(150,9000)][int]$SimPeriod=3000,
      [ValidateSet('nc','sdmpc')][string[]]$Arms=@('nc','sdmpc'))
# A finite pair through the existing frozen runner/watchdog. No new adapter.
$ErrorActionPreference='Stop'
$taskDir=$PSScriptRoot
$repoRoot=[IO.Path]::GetFullPath((Join-Path $taskDir '../../..'))
$frozen='D:/VISSIM_runs/20260926_selected1200_replay/frozen/sdmpc31_886a014a_202609262128'
$runsRoot='D:/VISSIM_runs/20260926_sd31_closedloop3000'
if ($SimPeriod -ne 3000 -and -not $ResultsRoot) {throw 'An explicit new ResultsRoot is required for another horizon'}
if ($Seed -ne 29 -and -not $ResultsRoot) {throw 'An explicit new ResultsRoot is required for another seed'}
if ($SimPeriod % 150) {throw 'SimPeriod must contain whole 150-second control intervals'}
if ($FrozenTree) {$frozen=[IO.Path]::GetFullPath($FrozenTree)}
if ($ResultsRoot) {$runsRoot=[IO.Path]::GetFullPath($ResultsRoot)}
if (-not $StatusPath) {$StatusPath=Join-Path $taskDir ('closedloop'+$SimPeriod+'_status.json')}
$StatusPath=[IO.Path]::GetFullPath($StatusPath)
$pythonExe='C:/Users/alsrj/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$pwshExe='C:/Users/alsrj/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
$selectedRoot=Join-Path $frozen 'diagnostics/sdmpc_n31_20260924/integration_20260926/selected'
$tuningPath=Join-Path $selectedRoot 'config_n31_v2.json'
if ($TuningRelativePath) {
    $tuningPath=[IO.Path]::GetFullPath((Join-Path $frozen $TuningRelativePath))
    $frozenPrefix=[IO.Path]::GetFullPath($frozen).TrimEnd('\','/')+[IO.Path]::DirectorySeparatorChar
    if ([IO.Path]::IsPathRooted($TuningRelativePath) -or
        -not $tuningPath.StartsWith($frozenPrefix,[StringComparison]::OrdinalIgnoreCase) -or
        -not (Test-Path -LiteralPath $tuningPath -PathType Leaf)) {
        throw 'Tuning override must name an existing file inside the verified frozen runtime'
    }
}
if ($Detached) {
    # One on-demand Windows task owns the existing frozen runner. No trigger/retry;
    # it is independent of the Codex execution service that can be replaced by updates.
    if (-not $FrozenTree -or -not $ResultsRoot -or $Arms.Count -ne 1 -or $ResumeAfterCompletedNc) {
        throw 'Detached launch requires explicit frozen/results paths and exactly one arm'
    }
    if (Test-Path -LiteralPath (Join-Path $runsRoot 'STOP')) {throw 'STOP exists; no launch'}
    $account=[System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    if ($account -ne (Get-CimInstance Win32_ComputerSystem).UserName) {
        throw 'Detached launch requires the logged-on user, not a sandbox/service account'
    }
    $mode=if($PreflightOnly){'preflight'}else{'run'}
    $receiptPath=Join-Path $runsRoot ('detached_'+$mode+'.json')
    if (Test-Path -LiteralPath $receiptPath) {throw 'Detached launch receipt already exists; inspect it before another launch'}
    $script=Join-Path $selectedRoot '../run_closedloop3000.ps1'
    $script=[IO.Path]::GetFullPath($script)
    if (-not (Test-Path -LiteralPath $script)) {throw 'Frozen canonical runner is missing'}
    $taskName='Codex-VISSIM-sd31-'+$mode+'-'+(Get-Date -Format 'yyyyMMddHHmmssfff')
    $argv=@('-NoProfile','-NonInteractive','-WindowStyle','Hidden','-File',$script,
            '-FrozenTree',$frozen,'-ResultsRoot',$runsRoot,'-StatusPath',$StatusPath,
            '-SimPeriod',[string]$SimPeriod,'-Arms',$Arms[0])
    if($PreflightOnly){$argv+='-PreflightOnly'}
    if($TuningRelativePath){
        if(-not (Get-Command $script).Parameters.ContainsKey('TuningRelativePath')) {
            throw 'Freeze the updated canonical launcher before using a detached tuning override'
        }
        $argv+=@('-TuningRelativePath',$TuningRelativePath)
    }
    if($Seed -ne 29){
        if(-not (Get-Command $script).Parameters.ContainsKey('Seed')) {
            throw 'Detached seed override requires an updated frozen canonical launcher; no launch performed'
        }
        $argv+=@('-Seed',[string]$Seed)
    }
    if(@($argv | Where-Object {$_ -match '["\r\n]'}).Count){throw 'Invalid command-line argument'}
    $arguments=($argv | ForEach-Object {'"'+$_+'"'}) -join ' '
    $action=New-ScheduledTaskAction -Execute $pwshExe -Argument $arguments -WorkingDirectory $frozen
    $principal=New-ScheduledTaskPrincipal -UserId $account -LogonType Interactive -RunLevel Limited
    $settings=New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 24) `
        -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -Priority 5
    $task=New-ScheduledTask -Action $action -Principal $principal -Settings $settings
    if ($task.Triggers -or $task.Settings.RestartCount -ne 0) {throw 'Detached experiment must have no trigger or automatic retry'}
    New-Item -ItemType Directory -Force -Path $runsRoot | Out-Null
    $receipt=[ordered]@{task_name=$taskName;task_path='\';mode=$mode;user=$account;
        status='prepared';created_at=[DateTimeOffset]::Now.ToString('o');launcher_pid=$PID;
        frozen_runner=$script;runner_sha256=(Get-FileHash -LiteralPath $script -Algorithm SHA256).Hash.ToLowerInvariant();
        execute=$pwshExe;arguments=$arguments;results_root=$runsRoot;status_path=$StatusPath;
        recurring=$false;automatic_retries=0;cleanup='Unregister only this task after it is terminal; retain this receipt'}
    $receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $receiptPath -Encoding utf8
    Register-ScheduledTask -TaskName $taskName -InputObject $task | Out-Null
    Export-ScheduledTask -TaskName $taskName | Set-Content -LiteralPath (Join-Path $runsRoot ('detached_'+$mode+'.xml')) -Encoding utf8
    Start-ScheduledTask -TaskName $taskName
    $receipt.status='dispatched'
    $receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $receiptPath -Encoding utf8
    Write-Output ('DETACHED_TASK='+$taskName)
    Write-Output ('DETACHED_RECEIPT='+$receiptPath)
    exit 0
}
function Save-Status([string]$stage,[string]$arm,[object]$details) {
    [ordered]@{stage=$stage;arm=$arm;time=[DateTimeOffset]::Now.ToString('o');pid=$PID;details=$details} |
      ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $StatusPath -Encoding utf8
}
try {
    if (Test-Path -LiteralPath (Join-Path $runsRoot 'STOP')) { throw 'STOP exists; no restart' }
    Set-Location -LiteralPath $frozen
    foreach($item in @(Get-ChildItem Env: | Where-Object {$_.Name -like 'RW_*'})) {
        [Environment]::SetEnvironmentVariable($item.Name,$null,'Process')
    }
    $env:RW_PYTHON=$pythonExe; $env:RW_MAINLINE_SG_ONLY='1'; $env:RW_OFFSET_WRITER='experiment'
    $env:RW_RAMP_AMBER_SEC='0'; $env:RW_DECISION_FAIL_FAST='1'; $env:RW_QUEUE_COUNTER='1'
    $env:PYTHONUTF8='1'; $env:PYTHONDONTWRITEBYTECODE='1'
    $env:PYTHONPATH='C:/Users/alsrj/Desktop/학술/찐찐막/Codex/VISSIM/.review-deps/sdmpc;'+$frozen
    $env:NUMSIM_REPO_ROOT=Join-Path $frozen 'vendor/NumSim-mine'
    $env:OMP_NUM_THREADS='1'; $env:OPENBLAS_NUM_THREADS='1'; $env:MKL_NUM_THREADS='1'
    & $pythonExe -B (Join-Path $frozen 'diagnostics/sdmpc_n31_20260924/tools/freeze_manifest.py') verify $frozen
    if ($LASTEXITCODE -ne 0) { throw 'Frozen runtime verification failed' }
    foreach($arm in $Arms) {
        if (Test-Path -LiteralPath (Join-Path $runsRoot 'STOP')) { throw 'STOP exists; no next run' }
        $name='sdmpc31_'+$arm+$SimPeriod+'_s'+$Seed
        $out=Join-Path $runsRoot $arm
        $netDir=Join-Path $out 'network'
        $network=Join-Path $netDir ($name+'.inpx')
        if (-not (Test-Path -LiteralPath $out)) {
            New-Item -ItemType Directory -Path $netDir | Out-Null
            Copy-Item -LiteralPath (Join-Path $selectedRoot 'network/native_seed29.inpx') -Destination $network
            Get-ChildItem -LiteralPath (Join-Path $selectedRoot 'network') -Filter '*.sig' |
              ForEach-Object {Copy-Item -LiteralPath $_.FullName -Destination $netDir}
        }
        if ((Get-FileHash -LiteralPath $network -Algorithm SHA256).Hash.ToLowerInvariant() -cne '64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc') { throw 'Network differs' }
        if ($ResumeAfterCompletedNc -and $arm -eq 'nc') {
            $nativeLog=Get-Content -LiteralPath (Join-Path $out ('runlog_'+$name+'.txt')) -Raw
            $launchText=Get-Content -LiteralPath (Join-Path $out 'launch.log') -Raw
            $provenance=Get-Content -LiteralPath (Join-Path $out ('run_provenance_'+$name+'.json')) -Raw | ConvertFrom-Json
            if ($nativeLog -notmatch '(?m)^STAGE=SIM_DONE\r?$' -or $nativeLog -notmatch ('(?m)^SIM_SEC='+$SimPeriod+'\r?$') -or
                $launchText -notmatch ('OK '+[regex]::Escape($name)+' attempt=1 ') -or
                $provenance.seed -ne $Seed -or $provenance.sim_period_sec -ne $SimPeriod -or $provenance.controller -ne 'no-control' -or
                [IO.Path]::GetFullPath($provenance.workspace_root) -ne $frozen -or
                $provenance.files.network.sha256 -ne '64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc') {
                throw 'NC resume requires the completed matching frozen run; no rerun or overwrite'
            }
            Save-Status 'completed_nc_reused' $arm @{out_dir=$out;name=$name;frozen=$frozen}
            continue
        }
        if (Test-Path -LiteralPath (Join-Path $out ('runlog_'+$name+'.txt'))) { throw 'Previous native attempt exists; preserve it' }
        $runOut=$out
        if ($PreflightOnly) { $runOut=Join-Path $out 'preflight' }
        $controller=if($arm -eq 'nc') {'no-control'} else {'wu-link'}
        $arguments=@('-NoProfile','-File',(Join-Path $frozen 'scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1'),
          '-Name',$name,'-Network',$network,'-OutDir',$runOut,'-SimPeriod',[string]$SimPeriod,'-ControlIntervalSec','150','-Seed',[string]$Seed,
          '-Controller',$controller,'-ControlStartSec','900','-WarmupController','no-control','-StateLogIntervalSec','150',
          '-DemandScale','1','-DemandProfile',(Join-Path $selectedRoot 'scenario/profile.csv'),
          '-VehicleInputRoles',(Join-Path $frozen 'evaluation/real_world_modi_inventory/vehicle_input_roles.csv'),
          '-UrbanInputGateMap',(Join-Path $frozen 'evaluation/real_world_modi_inventory/urban_input_gate_map_ver2_20260907.csv'),
          '-Calibration',(Join-Path $frozen 'evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json'),
          '-Mapping',(Join-Path $frozen 'evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json'),
          '-Tuning',$tuningPath,
          '-VbsConfig',(Join-Path $selectedRoot 'scenario/lane_native_b110.vbs'),
          '-NoGlobalKill','-MaxAttempts','1','-StartupStallSec','300','-StallSec','2400')
        if ($PreflightOnly) { $arguments+='-PreflightOnly' }
        else {
            $live=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^Vissim'})
            # The cscript may exit just before its COM server closes. Only wait;
            # never close another process or replay a completed simulation.
            for($wait=0; $live.Count -and $wait -lt 30; $wait++) {
                if (Test-Path -LiteralPath (Join-Path $runsRoot 'STOP')) {throw 'STOP exists; no next run'}
                Start-Sleep -Seconds 1
                $live=@(Get-CimInstance Win32_Process | Where-Object {$_.Name -match '^Vissim'})
            }
            if($live.Count) {throw 'Another VISSIM is open; preserve it and do not launch'}
        }
        Save-Status $(if($PreflightOnly){'preflight'}else{'native_running'}) $arm @{name=$name;out_dir=$out;frozen=$frozen;controller=$controller;arguments=$arguments}
        $launchLog=Join-Path $out $(if($PreflightOnly){'preflight_launch.log'}else{'launch.log'})
        & $pwshExe @arguments *> $launchLog
        if ($LASTEXITCODE -ne 0) {throw "Watchdog failed: $launchLog"}
        if (-not $PreflightOnly) {
            if (-not (Select-String -LiteralPath (Join-Path $out ('runlog_'+$name+'.txt')) -Pattern '^STAGE=SIM_DONE' -Quiet)) {throw 'No native completion'}
            Save-Status 'native_arm_complete' $arm @{out_dir=$out;name=$name}
        }
    }
    Save-Status $(if($PreflightOnly){'preflight_complete'}else{'requested_native_arms_complete_unanalyzed'}) '' @{out_dir=$runsRoot;terminal=$SimPeriod;arms=$Arms;gain_qualified=$false;native9000=($SimPeriod -eq 9000)}
} catch {
    Save-Status 'failed' '' ([string]$_)
    Write-Error $_
    exit 1
}
