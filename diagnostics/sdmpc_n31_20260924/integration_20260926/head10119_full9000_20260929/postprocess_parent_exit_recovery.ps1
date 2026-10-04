$ErrorActionPreference='Stop'
$runRoot='E:/VISSIM_runs/20260929_sd31_head10119_9000'
$reviewRoot='C:/Users/alsrj/Desktop/학술/찐찐막/Codex/VISSIM/.worktrees/sd31-upstream-20260926/diagnostics/sdmpc_n31_20260924/integration_20260926/head10119_full9000_20260929'
$receipt=Get-Content -LiteralPath (Join-Path $runRoot 'detached_run.json') -Raw | ConvertFrom-Json -DateKind String
$postStatus=Join-Path $reviewRoot 'postprocess_recovery_status.json'
if(Test-Path -LiteralPath $postStatus){throw 'Existing recovery; inspect before another launch'}
$deadline=[DateTimeOffset]::Now.AddHours(6)
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class OwnedExit {
 [DllImport("kernel32.dll", SetLastError=true)] public static extern IntPtr OpenProcess(uint access,bool inherit,int pid);
 [DllImport("kernel32.dll", SetLastError=true)] public static extern bool GetExitCodeProcess(IntPtr process,out uint code);
 [DllImport("kernel32.dll")] public static extern bool CloseHandle(IntPtr handle);
}
'@
$owned=@(
 [pscustomobject]@{id=17892;name='cscript.exe';created=[DateTime]'2026-09-29T06:32:59.003630+09:00';token='run_real_world_stackelberg_controller.vbs';handle=[IntPtr]::Zero;exit=$null},
 [pscustomobject]@{id=8036;name='VISSIM200.exe';created=[DateTime]'2026-09-29T06:33:00.875855+09:00';token='Vissim200.exe';handle=[IntPtr]::Zero;exit=$null}
)
function Save-PostStatus($stage,$detail){
 [ordered]@{stage=$stage;detail=$detail;pid=$PID;creation_time=(Get-Process -Id $PID).StartTime.ToString('o');time=[DateTimeOffset]::Now.ToString('o');native_task=$receipt.task_name;new_native_runs=0;automatic_retries=0;parent_task_exit=3221225786;original_failure_preserved='postprocess_status.json'} | ConvertTo-Json | Set-Content -LiteralPath $postStatus -Encoding utf8
}
try {
 foreach($entry in $owned){
  $p=Get-CimInstance Win32_Process -Filter ("ProcessId="+$entry.id)
  if(-not $p -or $p.Name -cne $entry.name -or [math]::Abs(($p.CreationDate-$entry.created).TotalMilliseconds) -gt 1 -or $p.CommandLine -notlike ('*'+$entry.token+'*')){throw 'Owned process identity mismatch; do not attach or restart'}
  if($entry.id -eq 17892 -and ($p.CommandLine -notlike '*20260929_sd31_head10119_9000*' -or $p.CommandLine -notlike '* 9000 150 29 *')){throw 'Wrong native invocation'}
  $entry.handle=[OwnedExit]::OpenProcess(0x1000,$false,$entry.id)
  if($entry.handle -eq [IntPtr]::Zero){throw 'Cannot hold owned process query handle'}
 }
 [ordered]@{time=[DateTimeOffset]::Now.ToString('o');pid=$PID;creation_time=(Get-Process -Id $PID).StartTime.ToString('o');owned=@($owned | Select-Object id,name,created);reason='Parent runner/watchdog exited; exact native children remain live. Only wait for these held process handles; no restart, kill, COM calls or model mutation.'} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $reviewRoot 'postprocess_recovery_owner.json') -Encoding utf8
 Save-PostStatus 'waiting_owned_native_closure' 'Parent failed; original cscript/VISSIM still running. No traffic analysis during run.'
 while($true){
  if(Test-Path -LiteralPath (Join-Path $runRoot 'STOP')){throw 'STOP; no postprocessing'}
  if([DateTimeOffset]::Now -ge $deadline){throw 'Wait deadline reached; owned native left untouched'}
  $running=$false
  foreach($entry in $owned){
   [uint32]$code=0
   if(-not [OwnedExit]::GetExitCodeProcess($entry.handle,[ref]$code)){throw 'Cannot read owned process exit code'}
   if($code -eq 259){$running=$true}else{$entry.exit=$code}
  }
  if(-not $running){break}
  Start-Sleep -Seconds 30
 }
 if(@($owned | Where-Object {$_.exit -ne 0}).Count){throw 'Original native child failed; retain partial files'}
 $nativeLog=Join-Path $runRoot 'sdmpc/runlog_sdmpc31_sdmpc9000_s29.txt'
 $logText=Get-Content -LiteralPath $nativeLog -Raw
 foreach($pattern in @('(?m)^STAGE=SIM_DONE\r?$','(?m)^SIM_SEC=9000(?:\.0+)?\r?$','(?m)^DECISIONS_FAILED=0\r?$','(?m)^OBSERVATION_FAILURES=0\r?$','(?m)^SIGNAL_FAILURES=0\r?$','(?m)^ACTION_FORMAT_FAILURES=0\r?$','(?m)^COM_FAILURES=0\r?$')){
  if($logText -notmatch $pattern){throw ('Missing native completion/integrity evidence: '+$pattern)}
 }
 if($logText -match '(?m)^ERROR='){throw 'Native error record; preserve and investigate'}
 $nativeProof=[ordered]@{stage='requested_native_arms_complete_unanalyzed';arm='';time=[DateTimeOffset]::Now.ToString('o');details=@{out_dir=$runRoot;arms=@('sdmpc');terminal=9000;gain_qualified=$false;native9000=$true};recovery=@{parent_task_result=3221225786;original_status='status.json';original_postprocess_failure='postprocess_status.json';child_exit_codes=@($owned | Select-Object id,name,created,exit);native_log=$nativeLog;native_log_sha256=(Get-FileHash -LiteralPath $nativeLog).Hash.ToLowerInvariant();scope='Actual native completion recovered from held child handles and native integrity/terminal records. Parent task remains failed; no claim of a successful scheduled task.'}}
 $nativeProof | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $reviewRoot 'recovered_native_status.json') -Encoding utf8
 if((Get-FileHash -LiteralPath 'D:/VISSIM_runs/20260928_sd31_d4e2_9000/STOP').Hash.ToLowerInvariant() -ne '91b2163b02b01447242909dee8e7f773d18e76a6594bd9db8de64d2a48246fc3'){throw 'Old9000 STOP changed'}
 if(Test-Path -LiteralPath (Join-Path $reviewRoot 'analysis/summary.json')){throw 'Preserve existing analysis; no duplicate scan'}
 Save-PostStatus 'analysis' 'Native closed; existing analyzer with matched completed NC'
 Set-Location -LiteralPath 'D:/VISSIM_runs/20260929_head10119_selected2700_runtime/sdmpc31_886a014a_202609290605'
 $env:PYTHONUTF8='1';$env:PYTHONDONTWRITEBYTECODE='1'
 $env:PYTHONPATH='C:/Users/alsrj/Desktop/학술/찐찐막/Codex/VISSIM/.review-deps/sdmpc;C:/Users/alsrj/Desktop/학술/찐찐막/Codex/VISSIM/.review-deps/plots;D:/VISSIM_runs/20260929_head10119_selected2700_runtime/sdmpc31_886a014a_202609290605'
 $env:NUMSIM_REPO_ROOT=Join-Path (Get-Location) 'vendor/NumSim-mine'
 $env:MPLCONFIGDIR=Join-Path $env:TEMP 'codex_vissim_postprocess_mpl'
 $analyzer='diagnostics/sdmpc_n31_20260924/integration_20260926/native_pair1200/analyze_pair.py'
 $arguments=@('-B',$analyzer,'--closed-loop-9000','--runs-root',$runRoot,'--nc-run-dir','D:/VISSIM_runs/20260927_sd31_wiring9000/nc','--output-dir',(Join-Path $reviewRoot 'analysis'),'--status-json',(Join-Path $reviewRoot 'recovered_native_status.json'))
 & 'C:/Users/alsrj/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' @arguments *> (Join-Path $reviewRoot 'postprocess.log')
 if($LASTEXITCODE -ne 0){throw 'Native analysis failed; preserve outputs, inspect postprocess.log'}
 if(Test-Path -LiteralPath (Join-Path $runRoot 'STOP')){throw 'STOP; no cached plot analysis'}
 Save-PostStatus 'cached_diagnostics' 'Existing aggregates and snapshots only; no new FZP scan'
 & 'C:/Users/alsrj/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' @arguments --cached-diagnostics *> (Join-Path $reviewRoot 'cached_diagnostics.log')
 if($LASTEXITCODE -ne 0){throw 'Cached diagnostics failed; preserve comparison, inspect cached_diagnostics.log'}
 Save-PostStatus 'complete' 'Analysis and cached figures complete; goal completion still requires result review'
} catch {Save-PostStatus 'failed_or_stopped' ([string]$_);Write-Error $_;exit 1}
finally { foreach($entry in $owned){if($entry.handle -ne [IntPtr]::Zero){[void][OwnedExit]::CloseHandle($entry.handle)}} }

