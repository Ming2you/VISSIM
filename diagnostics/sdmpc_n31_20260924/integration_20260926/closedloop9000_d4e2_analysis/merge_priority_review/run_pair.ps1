$ErrorActionPreference = 'Stop'
$plan = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'prepared_review.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$outputRoot = 'D:/VISSIM_runs/20260928_merge10484_priority_s47'
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../../../../..'))
$runner = Join-Path $repo '.worktrees/control-full-review/diagnostics/fast_nc_run.ps1'
$shell = (Get-Process -Id $PID).Path
$oldStop = 'D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP'
$oldStopHash = (Get-FileHash -LiteralPath $oldStop -Algorithm SHA256).Hash
$status = [ordered]@{stage='running'; pid=$PID; started=(Get-Date).ToString('o'); jobs=@(); active=$null; error=$null; scope='Exactly two priority-only seed47 3300s runs; no automatic retries'}
function Save-Status { $status | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $outputRoot 'queue_status.json') -Encoding UTF8 }
try {
    foreach ($job in $plan.stage1_plans) {
        if (Test-Path -LiteralPath (Join-Path $outputRoot 'STOP')) { $status.stage='stopped'; Save-Status; exit 0 }
        if ((Get-FileHash -LiteralPath $oldStop -Algorithm SHA256).Hash -ne $oldStopHash) { throw 'Old STOP changed; refuse continuation' }
        $status.active=$job.arm; Save-Status
        $jobLog=Join-Path $outputRoot ($job.arm + '_launcher.log')
        & $shell -NoProfile -File $runner -Prepared $job.prepared -Output $job.output -Seed 47 -Execute -AllowConcurrent -MinimumFreeGiB 4 *> $jobLog
        if ($LASTEXITCODE -ne 0) { throw ('Native job failed: '+$job.arm+'; '+$jobLog) }
        $receipt=Get-Content -LiteralPath (Join-Path $job.output 'run.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        if (-not $receipt.completed) { throw ('Incomplete native job: '+$job.arm) }
        $status.jobs += @{arm=$job.arm; completed=$true; receipt=(Join-Path $job.output 'run.json')}
        Save-Status
    }
    $status.stage='complete'; $status.active=$null; $status.finished=(Get-Date).ToString('o'); Save-Status
} catch {
    $status.stage='failed'; $status.error=$_.ToString(); $status.finished=(Get-Date).ToString('o'); Save-Status
    throw
}
