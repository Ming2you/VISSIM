param(
    [int]$EndSec=3000,
    [ValidateSet('none','vsl','rm','both')][string[]]$Arms=@('none','vsl','rm','both'),
    [ValidatePattern('^v[0-9]+$')][string]$Revision='v2',
    [string]$SelectedPrepared='diagnostics/demand_sweep/fw080_urban050/prepared',
    [ValidatePattern('^[A-Za-z0-9_-]+$')][string]$CasePrefix='rule100',
    [string]$QueueManifest
)
$ErrorActionPreference='Stop'
$repo=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location -LiteralPath $repo
if ($QueueManifest) {
    # Finite, sequential batch using the existing native runner; no traffic analysis.
    $plan=Get-Content -LiteralPath $QueueManifest -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($plan.schema -ne 'native-rule-queue/v1') { throw 'Queue manifest schema' }
    $queueRoot=(Resolve-Path -LiteralPath $plan.root).Path
    $statePath=Join-Path $queueRoot 'queue_status.json'
    if (Test-Path -LiteralPath $statePath) { throw 'Queue already has a status file; inspect before resuming' }
    $state=[ordered]@{status='waiting_current'; queue_pid=$PID; queue_start=(Get-Process -Id $PID).StartTime.ToString('o');
        started=(Get-Date).ToString('o'); updated=$null; active=$null; error=$null; finished=$null; results=@()}
    function Save-Queue {
        $state.updated=(Get-Date).ToString('o')
        $tmpPath=$statePath+'.tmp'
        $state | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $tmpPath -Encoding UTF8
        Move-Item -LiteralPath $tmpPath -Destination $statePath -Force
    }
    function Check-Queue-Pins {
        foreach ($pin in $plan.code_sha256.PSObject.Properties) {
            if ((Get-FileHash -LiteralPath $pin.Name -Algorithm SHA256).Hash.ToLowerInvariant() -ne $pin.Value) {
                throw ('Pinned code changed: '+$pin.Name)
            }
        }
    }
    function Stop-Requested { return Test-Path -LiteralPath (Join-Path $queueRoot 'STOP') }
    Save-Queue
    try {
        Check-Queue-Pins
        # Let the already-owned C: run and its queued post-run plot finish first.
        while ($true) {
            if (Stop-Requested) { $state.status='stopped'; Save-Queue; exit 0 }
            $prior=$null
            try { $prior=Get-Content -LiteralPath (Join-Path $plan.wait_run 'run.json') -Raw -Encoding UTF8 | ConvertFrom-Json } catch {}
            if ($prior -and $prior.finished -and -not $prior.owned_native_alive) { break }
            Start-Sleep -Seconds 5
        }
        $waitId=if ($plan.wait_id) { $plan.wait_id } else { 'p100_none' }
        $state.results+=@{id=$waitId; completed=[bool]$prior.completed; run=$plan.wait_run; reused_current=$true}
        if ($prior.completed) {
            $plotDeadline=(Get-Date).AddMinutes(5)
            while (-not (Test-Path -LiteralPath $plan.wait_heatmap)) {
                if (Stop-Requested) { $state.status='stopped'; Save-Queue; exit 0 }
                if ((Get-Date) -gt $plotDeadline) { throw 'Current NC completed but its queued heatmap is missing' }
                Start-Sleep -Seconds 5
            }
        }
        foreach ($job in $plan.jobs) {
            if (Stop-Requested) { $state.status='stopped'; Save-Queue; exit 0 }
            Check-Queue-Pins
            if (@(Get-Process -Name 'VISSIM*' -ErrorAction SilentlyContinue).Count) { throw 'Existing VISSIM outside the next owned job; queue halted without killing it' }
            foreach ($path in @($job.output,$job.prepared,$job.log)) {
                if (-not ([IO.Path]::GetFullPath($path)).StartsWith($queueRoot+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)) { throw 'Job path escapes queue root' }
            }
            if (Test-Path -LiteralPath $job.output) { throw ('Preserve existing output: '+$job.output) }
            $state.status='running'; $state.active=$job.id; Save-Queue
            $global:LASTEXITCODE=0
            & (Join-Path $repo 'diagnostics/fast_nc_run.ps1') -Prepared $job.prepared -Output $job.output -Execute -MinimumFreeGiB 8 *> $job.log
            $jobExit=$LASTEXITCODE
            $receiptPath=Join-Path $job.output 'run.json'
            $receipt=$null
            if (Test-Path -LiteralPath $receiptPath) { $receipt=Get-Content -LiteralPath $receiptPath -Raw -Encoding UTF8 | ConvertFrom-Json }
            $result=[ordered]@{id=$job.id; run=$job.output; wrapper_exit=$jobExit; completed=($null -ne $receipt -and $receipt.completed); heatmap=$null; error=$null}
            if ($receipt) { $result.error=$receipt.error }
            if ($result.completed -and $job.plot_case) {
                $state.status='plotting_nc'; Save-Queue
                $plotArgs=@('--case',$job.plot_case,'--both-off-half','--demand-pct',$job.percent)
                if ($job.plot_demand_label) { $plotArgs+=@('--demand-label',$job.plot_demand_label) }
                if ($job.plot_control_arm) { $plotArgs+=@('--control-arm',$job.plot_control_arm) }
                & $plan.python -B -X utf8 $plan.plot_script @plotArgs *> $job.plot_log
                if ($LASTEXITCODE -ne 0) { $result.error='NC heatmap failed; native data retained' }
                else { $result.heatmap=Join-Path $job.plot_case 'east_heatmap.png' }
            }
            $state.results+=,$result; $state.active=$null; Save-Queue
            if ($receipt -and $receipt.owned_native_alive) { throw 'Failed job still owns a native process; do not overlap' }
            # Failed independent runs are retained; do not retry or invent success.
        }
        $failed=@($state.results | Where-Object { -not $_.completed -or $_.error })
        $state.status=if ($failed.Count) {'complete_with_failures'} else {'complete'}
        $state.finished=(Get-Date).ToString('o'); Save-Queue
        exit 0
    } catch {
        $state.status='needs_attention'; $state.error=$_.Exception.Message; Save-Queue
        throw
    }
}
foreach ($arm in $Arms) {
    $name="${CasePrefix}_${arm}${EndSec}_s13_${Revision}"
    $log=Join-Path $PSScriptRoot ($name+'_console.log')
    if (Test-Path -LiteralPath $log) { throw "Preserve existing case log: $log" }
    & ./diagnostics/run_selected_control_trial.ps1 `
        -SelectedPrepared $SelectedPrepared `
        -Tuning (Join-Path $PSScriptRoot ('config_'+$arm+'_'+$Revision+'.json')) `
        -Name $name -Controller diagnostic-rule-profile -SimPeriod $EndSec `
        -ControlStartSec 900 -Seed 13 -Execute *> $log
    if ($LASTEXITCODE -ne 0) { throw "Rule case failed; preserved $name" }
    $receipt=Get-Content -LiteralPath (Join-Path $repo "evaluation/runs/$name/completion_receipt.json") -Raw | ConvertFrom-Json
    if (-not $receipt.completed) { throw "Rule case did not complete: $name" }
    Write-Output "RULE_CASE_COMPLETED arm=$arm end=$EndSec run=$name"
}
