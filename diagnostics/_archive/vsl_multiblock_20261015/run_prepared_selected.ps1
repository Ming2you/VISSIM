param([Parameter(Mandatory=$true)][string]$FrozenTree,[switch]$WaitForFreeze)
$ErrorActionPreference='Stop'
$runtime=$PSScriptRoot
$an='C:/Users/alsrj/Desktop/학술/찐찐막/Codex/VISSIM/.review-artifacts/vsl_multiblock_20261015'
$source='D:/VISSIM_packages/vsl_multizone355_20261015'
$runs='D:/VISSIM_runs/20261015_vsl_multizone2250_s29'
$task=Join-Path $source 'diagnostics/sdmpc_n31_20260924/integration_20260926/native_vsl_multizone2250'
$runnerRel='diagnostics/sdmpc_n31_20260924/integration_20260926/native_pair1200/run_pair.ps1'
$protocolRel='diagnostics/sdmpc_n31_20260924/integration_20260926/native_vsl_multizone2250/protocol.json'
$pwsh='C:/Users/alsrj/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
function Hash([string]$p){(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()}
function Stops { @((Join-Path $runtime 'STOP'),(Join-Path $runs 'STOP'),(Join-Path $runs 'selected/STOP'),(Join-Path $source 'STOP')) | Where-Object {Test-Path -LiteralPath $_} }
$state=[ordered]@{stage='validating_dispatch';wrapper_pid=$PID;wrapper_created_utc=(Get-Process -Id $PID).StartTime.ToUniversalTime().ToString('o');runner_invocations=0;native_launches=0;native_arms=[ordered]@{};owned_processes=@();automatic_retries=0}
function Save-State { $state['updated_utc']=[DateTimeOffset]::UtcNow.ToString('o');$state | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $runtime 'pair_state.json') -Encoding utf8 }
function Capture-Owners($all,$rootId,$birth,$owners) {
  $root=$all | Where-Object {$_.ProcessId -eq $rootId -and [Math]::Abs(($_.CreationDate.ToUniversalTime()-([DateTimeOffset]$birth).UtcDateTime).TotalSeconds) -lt .001}
  if($root){$tree=@{([int]$root.ProcessId)=$root};$grew=$true;while($grew){$grew=$false;foreach($p in $all){if($tree.ContainsKey([int]$p.ParentProcessId) -and -not $tree.ContainsKey([int]$p.ProcessId) -and $p.CreationDate -ge $tree[[int]$p.ParentProcessId].CreationDate){$tree[[int]$p.ProcessId]=$p;$grew=$true}}};foreach($p in $tree.Values){$key=[string]$p.ProcessId+':'+$p.CreationDate.ToUniversalTime().ToString('o');$owners[$key]=[ordered]@{pid=$p.ProcessId;created_utc=$p.CreationDate.ToUniversalTime().ToString('o');name=$p.Name}}}
  foreach($arm in @('selected')){
    $dir=Join-Path $runs $arm;$name='sdmpc31_g_2250_'+$arm+'_s29';$watch=Join-Path $dir 'WATCHDOG_PROGRESS.txt';$log=Join-Path $dir ('runlog_'+$name+'.txt')
    if(Test-Path -LiteralPath $log){$state.native_arms[$arm]=[ordered]@{attempted=$true;runlog=$log};$tail=Get-Content -LiteralPath $log -Tail 50;$times=@(foreach($line in $tail){if($line -match '(?:actual_sim_sec=|^NATIVE_SIM_PROGRESS sim_sec=|^OBS150_BUNDLE sim_sec=|^SIM_SEC=)([0-9.]+)'){[double]$Matches[1]}});if($times.Count){$state.native_arms[$arm]['last_actual_sec']=($times|Measure-Object -Maximum).Maximum;if(-not $state.Contains('first_observed_actual_progress_sec')){$state['first_observed_actual_progress_sec']=($times|Measure-Object -Minimum).Minimum;$state['first_progress_observed_utc']=[DateTimeOffset]::UtcNow.ToString('o')}}}
    if(Test-Path -LiteralPath $watch){$watchMatches=@(Select-String -LiteralPath $watch -Pattern ('VISSIM_PROCESS '+[regex]::Escape($name)+' pid=(\d+)'));foreach($match in $watchMatches){$v=$all|Where-Object {$_.ProcessId -eq [int]$match.Matches[0].Groups[1].Value -and $_.CreationDate.ToUniversalTime() -ge ([DateTimeOffset]$birth).UtcDateTime -and $_.Name -match '^Vissim'};if($v){$key=[string]$v.ProcessId+':'+$v.CreationDate.ToUniversalTime().ToString('o');$owners[$key]=[ordered]@{pid=$v.ProcessId;created_utc=$v.CreationDate.ToUniversalTime().ToString('o');name=$v.Name;arm=$arm}}}}
  }
  $state.native_launches=$state.native_arms.Count;$state.owned_processes=@($owners.Values)
}
try {
  if(@(Stops).Count){throw 'STOP exists; no dispatch'}
  if($WaitForFreeze){
    $freezeReceipt=Get-Content -LiteralPath (Join-Path $runtime 'freeze_launch.json') -Raw|ConvertFrom-Json
    $freezeOwner=Get-CimInstance Win32_Process -Filter ('ProcessId='+[int]$freezeReceipt.pid)
    if($freezeOwner -and [Math]::Abs(($freezeOwner.CreationDate.ToUniversalTime()-([DateTimeOffset]$freezeReceipt.creation_utc).UtcDateTime).TotalSeconds) -lt .001){
      $freezeProcess=Get-Process -Id $freezeReceipt.pid -ErrorAction Stop
      if([Math]::Abs(($freezeProcess.StartTime.ToUniversalTime()-([DateTimeOffset]$freezeReceipt.creation_utc).UtcDateTime).TotalSeconds) -ge .001){throw 'Freeze PID identity changed'}
      $state.stage='waiting_existing_canonical_freeze';Save-State
      while(-not $freezeProcess.WaitForExit(10000)){if(@(Stops).Count){throw 'STOP while waiting for freeze; no native dispatch'}}
    }
    if(@(Stops).Count){throw 'STOP after freeze; no native dispatch'}
    $freezeLog=Get-Content -LiteralPath (Join-Path $runtime 'freeze.log') -Tail 15
    $freezePathLine=@($freezeLog|Where-Object{$_ -match '^FRZ='})
    if(-not ($freezeLog -match '^FREEZE_DONE ') -or $freezePathLine.Count -ne 1){throw 'Freeze ended without normal completion; preserve without retry'}
    if([IO.Path]::GetFullPath($freezePathLine[0].Substring(4)) -ne [IO.Path]::GetFullPath($FrozenTree)){throw 'Frozen path differs from completed receipt'}
    $manifestPath=Join-Path $FrozenTree 'FREEZE.json'
    $manifest=Get-Content -LiteralPath $manifestPath -Raw|ConvertFrom-Json
    if([IO.Path]::GetFullPath($manifest.source) -ne [IO.Path]::GetFullPath($source) -or [IO.Path]::GetFullPath($manifest.frozen) -ne [IO.Path]::GetFullPath($FrozenTree)){throw 'Frozen manifest root differs'}
    $gateRoot=Get-Content -LiteralPath (Join-Path $an 'plan.json') -Raw|ConvertFrom-Json
    $gatePlan=$gateRoot.next_stage
    if(-not $gatePlan.preflight_verified -or $gatePlan.freeze_count -ne 1 -or $gatePlan.native_launches -ne 0){throw 'Prepared finite budget differs'}
    foreach($relative in @($protocolRel,$runnerRel)){
      $pin=$manifest.files.PSObject.Properties[$relative].Value
      if(-not $pin -or (Hash (Join-Path $FrozenTree $relative)) -cne $pin -or (Hash (Join-Path $source $relative)) -cne $pin){throw 'Frozen protocol/runner pin differs'}
    }
    $gatePlan.freeze_verified=$true;$gatePlan.frozen_tree=$FrozenTree;$gatePlan.status='freeze_complete_preparing_native';$gatePlan.updated_utc=[DateTimeOffset]::UtcNow.ToString('o')
    $gateRoot.status='freeze_complete_preparing_native';$gateRoot.updated_utc=[DateTimeOffset]::UtcNow.ToString('o')
    $gateRoot|ConvertTo-Json -Depth 90|Set-Content -LiteralPath (Join-Path $an 'plan.json') -Encoding utf8
    [ordered]@{stage='canonical_freeze_completed';freeze_pid=$freezeReceipt.pid;freeze_created_utc=$freezeReceipt.creation_utc;frozen_tree=$FrozenTree;manifest_sha256=(Hash $manifestPath);file_count=$manifest.file_count;total_bytes=$manifest.total_bytes;native_launches=0;full_manifest_revalidation='performed by unchanged canonical native runner before simulation'}|ConvertTo-Json -Depth 5|Set-Content -LiteralPath (Join-Path $runtime 'freeze_completion.json') -Encoding utf8
  }
  $planRoot=Get-Content -Raw -LiteralPath (Join-Path $an 'plan.json')|ConvertFrom-Json
  $plan=$planRoot.next_stage
  if(-not $plan.preflight_verified -or -not $plan.freeze_verified -or [IO.Path]::GetFullPath($plan.frozen_tree) -ne [IO.Path]::GetFullPath($FrozenTree)){throw 'Preflight/freeze not certified'}
  if((Hash (Join-Path $source $protocolRel)) -cne $plan.installed_protocol_sha256 -or (Hash (Join-Path $FrozenTree $protocolRel)) -cne $plan.installed_protocol_sha256){throw 'Protocol differs'}
  if((Hash (Join-Path $source $runnerRel)) -cne (Hash (Join-Path $FrozenTree $runnerRel))){throw 'Canonical runner differs'}
  while(@(Get-CimInstance Win32_Process|Where-Object {$_.Name -match '^Vissim'}).Count){if(@(Stops).Count){throw 'STOP while waiting for other VISSIM'};$state.stage='waiting_other_vissim';Save-State;Start-Sleep -Seconds 10}
  if(@(Stops).Count){throw 'STOP before native claim'}
  foreach($arm in @('selected')){if(Test-Path -LiteralPath (Join-Path $runs ($arm+'/runlog_sdmpc31_g_2250_'+$arm+'_s29.txt'))){throw 'Existing native attempt preserved'}}
  $claim=Join-Path $runtime 'native_runner_claim.json';$stream=[IO.File]::Open($claim,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::Read);$text=[Text.Encoding]::UTF8.GetBytes(($state|ConvertTo-Json -Depth 5));$stream.Write($text,0,$text.Length);$stream.Dispose()
  $args=@('-NoProfile','-NonInteractive','-WindowStyle','Hidden','-File',(Join-Path $source $runnerRel),'-FrozenTree',$FrozenTree,'-ProtocolPath',(Join-Path $source $protocolRel),'-ResultsRoot',$runs)
  if(@($args|Where-Object {$_ -match '["\r\n]'}).Count){throw 'Invalid argument'};$quoted=($args|ForEach-Object {'"'+$_+'"'}) -join ' '
  $proc=Start-Process -FilePath $pwsh -ArgumentList $quoted -WindowStyle Hidden -WorkingDirectory $source -PassThru -RedirectStandardOutput (Join-Path $runtime 'native_pair.log') -RedirectStandardError (Join-Path $runtime 'native_pair.err')
  $birth=$proc.StartTime.ToUniversalTime().ToString('o');$state['runner_pid']=$proc.Id;$state['runner_created_utc']=$birth;$state.runner_invocations=1;$state.stage='canonical_runner_active';Save-State
  [ordered]@{pid=$proc.Id;created_utc=$birth;executable=$pwsh;arguments=$args;frozen_tree=$FrozenTree;protocol=$plan.installed_protocol;protocol_sha256=$plan.installed_protocol_sha256;automatic_retries=0;max_native_arms=1} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $runtime 'native_runner_launch.json') -Encoding utf8
  $planRoot.status='canonical_native_running';$plan.status='canonical_native_running';$plan.native_launches=1
  $plan|Add-Member -NotePropertyName native_runner_launch -NotePropertyValue (Join-Path $runtime 'native_runner_launch.json') -Force
  $planRoot.updated_utc=[DateTimeOffset]::UtcNow.ToString('o');$planRoot|ConvertTo-Json -Depth 90|Set-Content -LiteralPath (Join-Path $an 'plan.json') -Encoding utf8
  $owners=@{};$stopSeen=$false
  while(-not $proc.HasExited){
    if(@(Stops).Count){$stopSeen=$true;if(-not (Test-Path -LiteralPath (Join-Path $runs 'STOP'))){'Queue STOP: finish/preserve current arm; block further dispatch'|Set-Content -LiteralPath (Join-Path $runs 'STOP') -Encoding utf8};$state.stage='stop_requested_no_kill'}
    Capture-Owners @(Get-CimInstance Win32_Process) $proc.Id $birth $owners;Save-State;Start-Sleep -Seconds 10;$proc.Refresh()
  }
  $proc.WaitForExit();$state['runner_exit_code']=$proc.ExitCode;Capture-Owners @(Get-CimInstance Win32_Process) $proc.Id $birth $owners
  if($proc.ExitCode -ne 0 -or $stopSeen -or @(Stops).Count){throw 'Canonical pair stopped or failed; no retry'}
  $nativeStatus=Get-Content -Raw -LiteralPath (Join-Path $task 'status.json')|ConvertFrom-Json
  if($nativeStatus.stage -ne 'requested_native_arms_complete_unanalyzed'){throw 'Pair did not normally finish'}
  foreach($arm in @('selected')){ $text=Get-Content -LiteralPath (Join-Path $runs ($arm+'/runlog_sdmpc31_g_2250_'+$arm+'_s29.txt')) -Tail 150;if(-not ($text -match '^STAGE=SIM_DONE$') -or -not ($text -match '^SIM_SEC=2700$')){throw 'Normal2700 marker missing'};if(-not @($owners.Values|Where-Object {$_.arm -eq $arm -and $_.name -match '^Vissim'}).Count){throw 'Native creation identity missing; do not certify closure'} }
  do {$all=@(Get-CimInstance Win32_Process);$alive=@($all|Where-Object {$owners.ContainsKey([string]$_.ProcessId+':'+$_.CreationDate.ToUniversalTime().ToString('o'))});if($alive.Count){$state.stage='waiting_owned_teardown';Save-State;Start-Sleep -Seconds 10}}while($alive.Count)
  $state.stage='selected_native_complete_wrapper_exit_pending';$state['normal_native_end_sec']=2700;$state['all_recorded_runner_processes_closed']=$true;Save-State
  $state | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $runtime 'native_pair_completion.json') -Encoding utf8
  Write-Output 'SELECTED_NATIVE_COMPLETE_UNANALYZED; wrapper exit must be verified before analysis'
} catch {
  $state.stage='failed_or_stopped_no_retry';$state['error']=[string]$_;Save-State
  $state | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $runtime 'native_pair_failure.json') -Encoding utf8
  Write-Error $_;exit 1
}
