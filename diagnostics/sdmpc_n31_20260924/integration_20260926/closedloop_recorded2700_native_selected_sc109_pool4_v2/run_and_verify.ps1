$ErrorActionPreference='Stop'
$jobRoot='D:/VISSIM_runs/20260929_sc109_selected2700_s47'
$source='C:/Users/alsrj/Desktop/학술/찐찐막/Codex/VISSIM/.worktrees/sd31-upstream-20260926'
$frozen='D:/VISSIM_runs/20260929_sc109_selected2700_runtime/sdmpc31_886a014a_202609290201'
$relative='diagnostics/sdmpc_n31_20260924/integration_20260926'
$protocol=Join-Path $source ($relative+'/closedloop_recorded2700_native_selected_sc109_pool4_v2/protocol.json')
$pwsh='C:/Users/alsrj/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
$python='C:/Users/alsrj/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
function JobStatus($stage,$detail){
 [ordered]@{stage=$stage;detail=$detail;pid=$PID;time=[DateTimeOffset]::Now.ToString('o');authorized_runs=1} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $jobRoot 'job_status.json') -Encoding utf8
}
try {
 Set-Location -LiteralPath $source
 if(Test-Path -LiteralPath (Join-Path $jobRoot 'STOP')){throw 'STOP; no launch'}
 $p=Get-Content -LiteralPath $protocol -Raw | ConvertFrom-Json
 if($p.native_authorization_pending -or @($p.arms).Count -ne 1 -or $p.arms[0] -ne 'selected' -or $p.end_sec -ne 3150 -or $p.seed -ne 47){throw 'Outside the single approved run'}
 if((Get-FileHash -LiteralPath $p.prior_stop).Hash.ToLowerInvariant() -ne $p.prior_stop_sha256){throw 'Old9000 STOP changed'}
 JobStatus 'native_running' 'One selected run only; reuse completed hold'
 & $pwsh -NoProfile -File (Join-Path $source ($relative+'/native_pair1200/run_pair.ps1')) -FrozenTree $frozen -ProtocolPath $protocol -ResultsRoot $jobRoot *> (Join-Path $jobRoot 'native_launch.log')
 if($LASTEXITCODE -ne 0){throw 'Native launcher failed; no retry; inspect native_launch.log'}
 if(Test-Path -LiteralPath (Join-Path $jobRoot 'STOP')){throw 'STOP; no postprocessing'}
 $status=Get-Content -LiteralPath (Join-Path (Split-Path $protocol) 'status.json') -Raw | ConvertFrom-Json
 if($status.stage -ne 'requested_native_arms_complete_unanalyzed'){throw 'Native not complete'}
 JobStatus 'postprocessing' 'Native closed; verify prefix, LDP/readbacks and residence once'
 Set-Location -LiteralPath $frozen
 $env:PYTHONUTF8='1';$env:PYTHONDONTWRITEBYTECODE='1'
 $env:PYTHONPATH='C:/Users/alsrj/Desktop/학술/찐찐막/Codex/VISSIM/.review-deps/sdmpc;'+$frozen
 $env:NUMSIM_REPO_ROOT=Join-Path $frozen 'vendor/NumSim-mine'
 & $python -B (Join-Path $frozen ($relative+'/native_pair1200/analyze_pair.py')) --replay-protocol $protocol --runs-root $jobRoot *> (Join-Path $jobRoot 'postprocess.log')
 if($LASTEXITCODE -ne 0){throw 'Postprocess failed; preserve all data; inspect postprocess.log'}
 & $python -B (Join-Path $frozen ($relative+'/native_pair1200/analyze_pair.py')) --replay-protocol $protocol --runs-root $jobRoot --cached-replay-ramp-audit *> (Join-Path $jobRoot 'ramp_audit.log')
 if($LASTEXITCODE -ne 0){throw 'Ramp audit failed; preserve completed native and Omega results; inspect ramp_audit.log'}
 JobStatus 'complete' 'One native run and postprocessing complete; no next run queued'
} catch {
 JobStatus 'failed_or_stopped' ([string]$_)
 Write-Error $_
 exit 1
}
