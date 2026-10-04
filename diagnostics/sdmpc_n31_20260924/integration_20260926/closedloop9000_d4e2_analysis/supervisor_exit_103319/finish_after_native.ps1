# One finite postprocessing dependency. Never starts/stops VISSIM or retries.
$ErrorActionPreference='Stop'
$output=$PSScriptRoot
$runRoot='D:/VISSIM_runs/20260928_sd31_d4e2_9000'
$nc='D:/VISSIM_runs/20260927_sd31_wiring9000/nc'
$frozen='D:/VISSIM_runs/20260928_sd31_d4e2_runtime/frozen/sdmpc31_886a014a_202609280537'
$taskName='Codex-VISSIM-sd31-run-20260928060432474'
$pythonExe='C:/Users/alsrj/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
$analysis=Join-Path $frozen 'diagnostics/sdmpc_n31_20260924/integration_20260926/native_pair1200/analyze_pair.py'
$statusFile=Join-Path $output 'postprocess_status.json'
$marker=[IO.File]::Open((Join-Path $output 'postprocess_started.lock'),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read)
$marker.Dispose()
function Save-State([string]$stage,[object]$detail) {
    [ordered]@{stage=$stage;time=[DateTimeOffset]::Now.ToString('o');pid=$PID;details=$detail} |
      ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $statusFile -Encoding utf8
}
function Check-Stop {
    if(Test-Path -LiteralPath (Join-Path $runRoot 'STOP')) {throw 'STOP exists; no postprocessing'}
}
try {
    Check-Stop
    if(Test-Path -LiteralPath (Join-Path $output 'summary.json')) {throw 'Preserve existing analysis'}
    $owner=Get-Process -Id 31020 -ErrorAction SilentlyContinue
    if($owner) {
        if([Math]::Abs(($owner.StartTime-[datetime]'2026-09-28T06:04:32.7847642+09:00').TotalMilliseconds) -gt 1) {throw 'Owner PID identity differs'}
        Save-State 'waiting_for_native_owner_exit' @{owner_pid=31020;owner_start=$owner.StartTime.ToString('o');analysis_path=$analysis}
        while(-not $owner.WaitForExit(50000)) { Check-Stop }
    }
    Check-Stop
    $status=Get-Content -LiteralPath (Join-Path $runRoot 'status.json') -Raw|ConvertFrom-Json
    if($status.stage -ne 'requested_native_arms_complete_unanalyzed' -or $status.details.terminal -ne 9000 -or
       @($status.details.arms).Count -ne 1 -or $status.details.arms[0] -ne 'sdmpc') {throw 'Native run did not complete successfully'}
    $expected=@{31020='2026-09-28T06:04:32.784764+09:00';884='2026-09-28T06:04:47.321372+09:00';31064='2026-09-28T06:04:48.475490+09:00';16776='2026-09-28T06:04:50.007707+09:00'}
    foreach($proc in @(Get-CimInstance Win32_Process|Where-Object{$expected.ContainsKey([int]$_.ProcessId)})) {
        if([Math]::Abs(($proc.CreationDate-[datetime]$expected[[int]$proc.ProcessId]).TotalMilliseconds) -le 1) {throw ('Owned process still open: '+$proc.ProcessId)}
    }
    $task=Get-ScheduledTask -TaskName $taskName
    $info=Get-ScheduledTaskInfo -TaskName $taskName
    # The scheduler may publish its terminal result just after the owner exits.
    for($attempt=0;$attempt -lt 30 -and $task.State -eq 'Running';$attempt++) {
        Start-Sleep -Seconds 1; Check-Stop
        $task=Get-ScheduledTask -TaskName $taskName; $info=Get-ScheduledTaskInfo -TaskName $taskName
    }
    if($task.State -eq 'Running' -or $info.LastTaskResult -ne 0) {throw 'Task lacks successful terminal result'}
    [ordered]@{verified_at=[DateTimeOffset]::Now.ToString('o');process_exit_verified=$true;original_processes=$expected;
      task=$taskName;task_state=[string]$task.State;last_task_result=$info.LastTaskResult;
      status_sha256=(Get-FileHash -LiteralPath (Join-Path $runRoot 'status.json') -Algorithm SHA256).Hash.ToLowerInvariant()} |
      ConvertTo-Json -Depth 6|Set-Content -LiteralPath (Join-Path $output 'process_closure.json') -Encoding utf8
    Set-Location -LiteralPath $frozen
    $env:PYTHONUTF8='1'; $env:PYTHONDONTWRITEBYTECODE='1'
    $env:PYTHONPATH='C:/Users/alsrj/Desktop/학술/찐찐막/Codex/VISSIM/.review-deps/sdmpc;'+$frozen
    $env:NUMSIM_REPO_ROOT=Join-Path $frozen 'vendor/NumSim-mine'
    $env:OMP_NUM_THREADS='1'; $env:OPENBLAS_NUM_THREADS='1'; $env:MKL_NUM_THREADS='1'
    $arguments=@('-B',$analysis,'--closed-loop-9000','--runs-root',$runRoot,'--nc-run-dir',$nc,'--output-dir',$output,'--status-json',(Join-Path $runRoot 'status.json'))
    Check-Stop
    Save-State 'analyzing_closed_native' @{analysis_sha256=(Get-FileHash -LiteralPath $analysis -Algorithm SHA256).Hash.ToLowerInvariant();arguments=$arguments}
    & $pythonExe @arguments *> (Join-Path $output 'analysis.log')
    if($LASTEXITCODE -ne 0) {throw 'Closed-run comparison failed; see analysis.log'}
    $result=Get-Content -LiteralPath (Join-Path $output 'summary.json') -Raw|ConvertFrom-Json
    if(-not $result.paired_prefix_exact -or -not $result.original_initial_history_exact -or
       -not $result.arms.nc.native_execution_passed -or -not $result.arms.sdmpc.native_execution_passed) {throw 'Native application or common initial history verification failed'}
    Check-Stop
    Save-State 'cached_spatial_analysis' @{summary='summary.json'}
    & $pythonExe @arguments --cached-diagnostics *> (Join-Path $output 'cached_diagnostics.log')
    if($LASTEXITCODE -ne 0) {throw 'Cached spatial analysis failed; see cached_diagnostics.log'}
    Save-State 'complete_pending_interpretation' @{summary='summary.json';spatial='spatial_decision_audit.json';gain_qualified=$false;new_native_runs=0;calibration_changes=0}
} catch {
    Save-State 'failed_preserved' ([string]$_)
    Write-Error $_
    exit 1
}
