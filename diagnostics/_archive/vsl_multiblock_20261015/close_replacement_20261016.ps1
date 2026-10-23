# Read-only process verification; write an analysis receipt only after all gates pass.
$ErrorActionPreference='Stop'
$runtime='D:/VISSIM_runtime/20261016_vsl_multizone2250_repaired'
$runs='D:/VISSIM_runs/20261016_vsl_multizone2250_repaired_s29'
$output=Join-Path $PSScriptRoot 'native_analysis_repaired_20261016'
$receiptPath=Join-Path $output 'runtime_closure.json'
if(Test-Path -LiteralPath $receiptPath){throw 'Existing closure preserved; reuse it'}
foreach($path in @((Join-Path $runtime 'STOP'),(Join-Path $runs 'STOP'),(Join-Path $runs 'selected/STOP'))){if(Test-Path -LiteralPath $path){throw 'STOP preserved; no normal closure certification'}}
$completion=Get-Content -LiteralPath (Join-Path $runtime 'native_pair_completion.json') -Raw|ConvertFrom-Json
if($completion.stage -ne 'selected_native_complete_wrapper_exit_pending' -or $completion.runner_exit_code -ne 0 -or $completion.normal_native_end_sec -ne 2700 -or -not $completion.all_recorded_runner_processes_closed){throw 'Normal completion evidence missing'}
$log=Join-Path $runs 'selected/runlog_sdmpc31_g_2250_selected_s29.txt'
$tail=Get-Content -LiteralPath $log -Tail 150
if(-not ($tail -match '^STAGE=SIM_DONE$') -or -not ($tail -match '^SIM_SEC=2700$')){throw 'Normal SIM_DONE2700 absent'}
$state=Get-Content -LiteralPath (Join-Path $runtime 'pair_state.json') -Raw|ConvertFrom-Json
if($state.stage -ne $completion.stage -or $state.runner_exit_code -ne 0){throw 'Latest state differs'}
$owners=@($completion.owned_processes)
if(-not @($owners|Where-Object{$_.name -match '^Vissim' -and $_.arm -eq 'selected'}).Count){throw 'VISSIM identity missing'}
foreach($file in @('preflight_launch.json','freeze_launch.json','native_wrapper_launch.json','native_runner_launch.json')){
    $r=Get-Content -LiteralPath (Join-Path $runtime $file) -Raw|ConvertFrom-Json
    $birth=if($r.creation_utc){$r.creation_utc}else{$r.created_utc}
    if(-not $birth){throw 'Owner creation missing'}
    $owners += [pscustomobject]@{pid=[int]$r.pid;created_utc=([DateTimeOffset]$birth).ToUniversalTime().ToString('o');name=$file}
}
$all=@(Get-CimInstance Win32_Process -ErrorAction Stop)
$checks=@(foreach($owner in $owners){
    $current=@($all|Where-Object{$_.ProcessId -eq [int]$owner.pid})
    $alive=$false
    if($current.Count){$alive=[Math]::Abs(($current[0].CreationDate.ToUniversalTime()-([DateTimeOffset]$owner.created_utc).UtcDateTime).Ticks) -le 10}
    [ordered]@{pid=[int]$owner.pid;created_utc=([DateTimeOffset]$owner.created_utc).ToUniversalTime().ToString('o');name=$owner.name;owned_process_closed=(-not $alive);current_pid_creation_utc=$(if($current.Count){$current[0].CreationDate.ToUniversalTime().ToString('o')}else{$null})}
})
if(@($checks|Where-Object{-not $_.owned_process_closed}).Count){throw 'Recorded owner still active; defer analysis'}
New-Item -ItemType Directory -Path $output -Force|Out-Null
[ordered]@{checked_utc=[DateTimeOffset]::UtcNow.ToString('o');runs_root=$runs;arms=@('selected');normal_native_end_sec=2700;owner_exit_code=0;wrapper_closed=$true;all_owned_processes_closed=$true;processes=$checks;completion_path=(Join-Path $runtime 'native_pair_completion.json');completion_sha256=(Get-FileHash -LiteralPath (Join-Path $runtime 'native_pair_completion.json')).Hash.ToLowerInvariant();creation_comparison='UTC timestamps; tolerance1microsecond for CIM truncation';native_runs_added_by_this_script=0}|ConvertTo-Json -Depth 8|Set-Content -LiteralPath $receiptPath -Encoding utf8
Write-Output ('CLOSED_NATIVE_2700 '+$receiptPath)
