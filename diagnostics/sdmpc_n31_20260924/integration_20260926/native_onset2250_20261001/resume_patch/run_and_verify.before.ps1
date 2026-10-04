param([Parameter(Mandatory=$true)][string]$FrozenTree)
$ErrorActionPreference='Stop'
$source=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../..'))
$relative='diagnostics/sdmpc_n31_20260924/integration_20260926'
$jobRoot='D:/VISSIM_runs/20261001_onset2250_s29'
$protocol=Join-Path $PSScriptRoot 'protocol.json'
$pwsh='C:/Users/alsrj/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
$python='C:/Users/alsrj/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
function Status($stage,$detail){
 [ordered]@{stage=$stage;detail=$detail;pid=$PID;creation_time=(Get-Process -Id $PID).StartTime.ToString('o');time=[DateTimeOffset]::Now.ToString('o');authorized_runs=4} |
  ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $jobRoot 'job_status.json') -Encoding utf8
}
try {
 Set-Location -LiteralPath $source
 if(Test-Path -LiteralPath (Join-Path $jobRoot 'STOP')){throw 'STOP; no launch'}
 $p=Get-Content -LiteralPath $protocol -Raw | ConvertFrom-Json
 if(-not $p.native_factorial -or $p.native_authorization_pending -or $p.end_sec -ne 2700 -or @($p.arms).Count -ne 4){throw 'Outside the prepared four runs'}
 if((Get-FileHash -LiteralPath $p.prior_stop).Hash.ToLowerInvariant() -ne $p.prior_stop_sha256){throw 'Old9000 STOP changed'}
 # The orchestration entry stays in the worktree; every native runtime is frozen.
 $relativeRunner=$relative+'/native_pair1200/run_pair.ps1'
 if((Get-FileHash -LiteralPath (Join-Path $source $relativeRunner)).Hash -ne (Get-FileHash -LiteralPath (Join-Path $FrozenTree $relativeRunner)).Hash){throw 'Launcher changed after freezing'}
 Status 'native_running' 'Four finite2700s command replays; no optimizer, no retry'
 & $pwsh -NoProfile -File (Join-Path $source $relativeRunner) -FrozenTree $FrozenTree -ProtocolPath $protocol -ResultsRoot $jobRoot *> (Join-Path $jobRoot 'native_launch.log')
 if($LASTEXITCODE -ne 0){throw 'Native launcher failed; preserve outputs; no retry'}
 if(Test-Path -LiteralPath (Join-Path $jobRoot 'STOP')){throw 'STOP; no postprocessing'}
 $status=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'status.json') -Raw | ConvertFrom-Json
 if($status.stage -ne 'requested_native_arms_complete_unanalyzed'){throw 'Native queue not complete'}
 Status 'postprocessing' 'All native runs closed; verify prefix, execution, area costs and8ramps once'
 Set-Location -LiteralPath $FrozenTree
 $env:PYTHONUTF8='1';$env:PYTHONDONTWRITEBYTECODE='1'
 $env:PYTHONPATH='C:/Users/alsrj/Desktop/학술/찐찐막/Codex/VISSIM/.review-deps/sdmpc;'+$FrozenTree
 $analyzer=Join-Path $FrozenTree ($relative+'/native_pair1200/analyze_pair.py')
 & $python -B $analyzer --replay-protocol $protocol --runs-root $jobRoot *> (Join-Path $jobRoot 'postprocess.log')
 if($LASTEXITCODE -ne 0){throw 'Native execution/prefix/area validation failed; inspect postprocess.log'}
 & $python -B $analyzer --replay-protocol $protocol --runs-root $jobRoot --cached-replay-ramp-audit *> (Join-Path $jobRoot 'ramp_audit.log')
 if($LASTEXITCODE -ne 0){throw 'Eight-ramp audit failed; preserve area results; inspect ramp_audit.log'}
 Status 'complete' 'Four native runs and prescribed analysis complete; no more runs queued'
} catch {
 Status 'failed_or_stopped' ([string]$_)
 Write-Error $_
 exit 1
}
