$ErrorActionPreference='Stop'
$repo=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../../../..'))
$runner=Join-Path $repo 'diagnostics/sdmpc_n31_20260924/integration_20260926/native_pair1200/run_pair.ps1'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($runner,[ref]$tokens,[ref]$errors)
if($errors.Count){throw ($errors | Out-String)}
foreach($name in @('Hash','Assert-CompletedReplay','Wait-OwnedVissimExit')){
 $node=$ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq $name},$true)
 . ([scriptblock]::Create($node.Extent.Text))
}
$FrozenTree='D:/VISSIM_runs/20261001_onset2250_runtime/frozen/sdmpc31_7ecace62_202610010455'
$protocol=[pscustomobject]@{seed=29;end_sec=2700}
$checks=[Collections.Generic.List[string]]::new()
function Must-Fail([scriptblock]$Action,[string]$label){
 $failed=$false;try{& $Action | Out-Null}catch{$failed=$true}
 if(-not $failed){throw ('Expected rejection: '+$label)};$checks.Add($label)
}
foreach($arm in @('held_actual','rm_only')){
 $name='sdmpc31_g_2250_'+$arm+'_s29'
 $original='D:/VISSIM_runs/20261001_onset2250_s29/'+$arm
 $copy=Join-Path $PSScriptRoot ('fixture_'+$arm)
 New-Item -ItemType Directory -Path $copy -Force | Out-Null
 foreach($file in @('WATCHDOG_PROGRESS.txt','native_network_performance.json',('runlog_'+$name+'.txt'),('run_provenance_'+$name+'.json'))){
  Copy-Item -LiteralPath (Join-Path $original $file) -Destination (Join-Path $copy $file)
 }
 $provenance=Get-Content -LiteralPath (Join-Path $copy ('run_provenance_'+$name+'.json')) -Raw | ConvertFrom-Json
 $plan=[pscustomobject]@{name=$name;arm=$arm;out_dir=$copy;network=$provenance.files.network.path;
  tuning=$provenance.files.tuning.path;vbs_config=$provenance.files.generated_vbs_config.path}
 $log=Join-Path $copy ('runlog_'+$name+'.txt')
 Assert-CompletedReplay $plan $log
 $checks.Add('completed_'+$arm+'_accepted_without_native_execution')
 $protocol.seed=30
 Must-Fail {Assert-CompletedReplay $plan $log} ($arm+'_wrong_seed_rejected')
 $protocol.seed=29
 $bad=Join-Path $copy 'incomplete.txt'
 [IO.File]::WriteAllText($bad,([IO.File]::ReadAllText($log).Replace('STAGE=SIM_DONE','STAGE=INCOMPLETE')))
 Must-Fail {Assert-CompletedReplay $plan $bad} ($arm+'_incomplete_rejected')
 $correct=$plan.tuning;$plan.tuning=$plan.network
 Must-Fail {Assert-CompletedReplay $plan $log} ($arm+'_wrong_tuning_rejected')
 $plan.tuning=$correct
}
# OS methods are mocked below: never inspect, wait on, or stop live VISSIM.
$launch=Get-Date
$script:pidForTest=46432
$script:creationForTest=$launch.AddSeconds(1)
$script:exitResult=$true;$script:waitCalls=0
function Get-CimInstance {param($ClassName)
 [pscustomobject]@{Name='Vissim200.exe';ProcessId=$script:pidForTest;CreationDate=$script:creationForTest}
}
function Get-Process {param($Id,$ErrorAction)
 $p=[pscustomobject]@{StartTime=$script:processCreation}
 $p | Add-Member -MemberType ScriptMethod -Name WaitForExit -Value {
  param($timeout)
  if($timeout -ne 30000){throw 'Unexpected blocking interval'}
  $script:waitCalls++;return $script:exitResult
 }
 return $p
}
$script:processCreation=$script:creationForTest
Wait-OwnedVissimExit $plan $launch | Out-Null
if($script:waitCalls -ne 1){throw 'No owned teardown wait'}
$checks.Add('owned_teardown_waited_once_30s_no_kill')
$script:pidForTest=99999
Must-Fail {Wait-OwnedVissimExit $plan $launch} 'unrelated_pid_rejected'
$script:pidForTest=46432;$script:processCreation=$script:creationForTest.AddMinutes(1)
Must-Fail {Wait-OwnedVissimExit $plan $launch} 'reused_pid_creation_rejected'
$script:processCreation=$script:creationForTest;$script:exitResult=$false
Must-Fail {Wait-OwnedVissimExit $plan $launch} 'teardown_timeout_rejected_without_retry_or_kill'
if($script:waitCalls -ne 2){throw 'Unrelated processes were waited on'}
$result=[ordered]@{passed=$true;checks=$checks;new_native_runs=0;live_process_interactions=0}
$result | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'verification.json') -Encoding utf8
$result | ConvertTo-Json -Depth 4
