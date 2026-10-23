"""Adapt the existing owned-run wrapper to the authorized single selected arm."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORIGINAL = Path('E:/VISSIM_runtime/20261011_vsl349_off2250/run_prepared_pair.ps1')
text = ORIGINAL.read_text(encoding='utf-8-sig')

def replace(old, new, count=1):
    global text
    assert text.count(old) == count, (old, text.count(old), count)
    text = text.replace(old, new)

replace("$an='E:/VISSIM_analysis/20261011_vsl_response349/causal_off2250_analysis_v2'", "$an='" + HERE.as_posix() + "'")
replace("$source='E:/VISSIM_workspaces/vsl349_causal_20261011'", "$source='D:/VISSIM_packages/vsl_multizone355_20261015'")
replace("$runs='E:/VISSIM_runs/20261011_vsl349_off2250_s29'", "$runs='D:/VISSIM_runs/20261015_vsl_multizone2250_s29'")
replace('native_vsl349_off2250', 'native_vsl_multizone2250', 2)
replace("(Join-Path $runs 'hold/STOP'),(Join-Path $runs 'vsl90/STOP')", "(Join-Path $runs 'selected/STOP'),(Join-Path $source 'STOP')")
replace("@('hold','vsl90')", "@('selected')", 3)
replace("$gatePlan=Get-Content -LiteralPath (Join-Path $an 'plan.json') -Raw|ConvertFrom-Json", "$gateRoot=Get-Content -LiteralPath (Join-Path $an 'plan.json') -Raw|ConvertFrom-Json\n    $gatePlan=$gateRoot.next_stage")
replace("$gatePlan|ConvertTo-Json -Depth 90|Set-Content", "$gateRoot.status='freeze_complete_preparing_native';$gateRoot.updated_utc=[DateTimeOffset]::UtcNow.ToString('o')\n    $gateRoot|ConvertTo-Json -Depth 90|Set-Content")
replace("$plan=Get-Content -Raw -LiteralPath (Join-Path $an 'plan.json')|ConvertFrom-Json", "$planRoot=Get-Content -Raw -LiteralPath (Join-Path $an 'plan.json')|ConvertFrom-Json\n  $plan=$planRoot.next_stage")
replace("if(@(Get-CimInstance Win32_Process|Where-Object {$_.Name -match '^Vissim'}).Count){throw 'Other VISSIM is open; no termination or dispatch'}", "while(@(Get-CimInstance Win32_Process|Where-Object {$_.Name -match '^Vissim'}).Count){if(@(Stops).Count){throw 'STOP while waiting for other VISSIM'};$state.stage='waiting_other_vissim';Save-State;Start-Sleep -Seconds 10}\n  if(@(Stops).Count){throw 'STOP before native claim'}")
replace('max_native_arms=2', 'max_native_arms=1')
replace("$owners=@{};$stopSeen=$false", "$planRoot.status='canonical_native_running';$plan.status='canonical_native_running';$plan.native_launches=1\n  $plan|Add-Member -NotePropertyName native_runner_launch -NotePropertyValue (Join-Path $runtime 'native_runner_launch.json') -Force\n  $planRoot.updated_utc=[DateTimeOffset]::UtcNow.ToString('o');$planRoot|ConvertTo-Json -Depth 90|Set-Content -LiteralPath (Join-Path $an 'plan.json') -Encoding utf8\n  $owners=@{};$stopSeen=$false")
replace("'both_native_complete_unanalyzed'", "'requested_native_arms_complete_unanalyzed'")
replace("'both_native_complete_wrapper_exit_pending'", "'selected_native_complete_wrapper_exit_pending'")
replace('BOTH_NATIVE_COMPLETE_UNANALYZED', 'SELECTED_NATIVE_COMPLETE_UNANALYZED')
replace("$state.native_arms[$arm]['last_actual_sec']=($times|Measure-Object -Maximum).Maximum", "$state.native_arms[$arm]['last_actual_sec']=($times|Measure-Object -Maximum).Maximum;if(-not $state.Contains('first_observed_actual_progress_sec')){$state['first_observed_actual_progress_sec']=($times|Measure-Object -Minimum).Minimum;$state['first_progress_observed_utc']=[DateTimeOffset]::UtcNow.ToString('o')}")

assert 'MaxAttempts' not in text  # unchanged canonical runner enforces MaxAttempts1
assert "@('hold','vsl90')" not in text and 'max_native_arms=2' not in text
target = HERE / 'run_prepared_selected.ps1'
assert not target.exists()
target.write_text(text, encoding='utf8')
receipt = dict(
    wrapper=str(target), wrapper_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
    reused_pattern=str(ORIGINAL), reused_pattern_sha256=hashlib.sha256(ORIGINAL.read_bytes()).hexdigest(),
    native_budget=1, retries=0, canonical_runner_unchanged=True,
    normal_completion_requires='SIM_DONE2700, runner exit0, all recorded process identities exited, then external wrapper closure verification',
)
(HERE / 'wrapper_preparation.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf8')
print(json.dumps(receipt))
