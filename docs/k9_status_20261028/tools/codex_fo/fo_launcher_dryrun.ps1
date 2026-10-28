# [FO copy 2026-10-27 KST, PRE_FO s5: copy of codex_handoff/b/b_launcher_dryrun.ps1 (sha256 fa5652b59f56e1e3613b9ed5a482f45e9056aaf7b30d81b36e7339ab8ee6e7d1) with names changed and the declared FO
# additions; full diff in codex_handoff/fo/work/run/launcher_b_to_fo.diff. The original header follows.]
# Dry run of fo_launcher.ps1 (2026-10-27; copy of the B dry-run harness fa5652b5... with names changed + FO cases). Windows PowerShell 5.1. No WMI, no process start, no VISSIM: the launcher runs
# with -Mode dryrun on roots under b/dryrun/<run>/<case>, VISSIM counts / disk / run outcomes / files from a scenario JSON.
# Each case states what it expects (launched keys, stop reason, exit code, try-end statuses, log patterns); the result
# and every case's launcher log are appended to fo/fo_launcher_dryrun.log. ASCII only.
$ErrorActionPreference = 'Stop'
$SPB = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\fo'
$L = Join-Path $SPB 'fo_launcher.ps1'
$OUT = Join-Path $SPB 'fo_launcher_dryrun.log'
$RUN = Join-Path $SPB ('dryrun\run_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
New-Item -ItemType Directory -Force -Path $RUN | Out-Null
$UTF8 = New-Object System.Text.UTF8Encoding $false
function W([string]$m) { [IO.File]::AppendAllText($OUT, $m + "`r`n", $UTF8) }
$done31 = @(@{ path = 's31\fo_launch\wrapper_run1_try1_end.json'; text = '{"runner_exit":0}' }, @{ path = 's31\sdmpc\runlog_sdmpc31_sdmpc9000_s31.txt'; text = "STAGE=SIM_DONE`r`nSIM_SEC=9000`r`n" })
$done41 = @(@{ path = 's41\fo_launch\wrapper_run1_try1_end.json'; text = '{"runner_exit":0}' }, @{ path = 's41\sdmpc\runlog_sdmpc31_sdmpc9000_s41.txt'; text = "STAGE=SIM_DONE`r`nSIM_SEC=9000`r`n" })
$done43 = @(@{ path = 's43\fo_launch\wrapper_run1_try1_end.json'; text = '{"runner_exit":0}' }, @{ path = 's43\sdmpc\runlog_sdmpc31_sdmpc9000_s43.txt'; text = "STAGE=SIM_DONE`r`nSIM_SEC=9000`r`n" })
$cases = @(
  @{ name = 'A_busy_then_free'; outcomes = @{}; steps = @(
      @{ vissim = 4; note = 'PC at cap 4 (others)' }, @{ vissim = 5; note = 'PC above cap' }, @{ vissim = 3; note = 'one seat free -> s31' },
      @{ vissim = 4; note = 'cap again (incl. ours)' }, @{ vissim = 2; note = 'free -> s41' }, @{ vissim = 3; note = 'free -> s43' },
      @{ vissim = 4; note = 'all launched' }, @{ vissim = 4; note = 'all complete'; write = ($done31 + $done41 + $done43) });
    expect_launched = @('s31_run1_try1', 's41_run1_try1', 's43_run1_try1'); expect_stop = ''; expect_exit = 0;
    expect_tryend = @{ s31_run1_try1 = 'completed'; s41_run1_try1 = 'completed'; s43_run1_try1 = 'completed' };
    expect_log = @('action=SEAT_BUSY s31_run1_try1 \(vissim=4', 'action=SEAT_BUSY s31_run1_try1 \(vissim=5', 'action=SEAT_BUSY s41_run1_try1 \(vissim=4', 'LAUNCHER_EXIT all seeds ended') },
  @{ name = 'C_stop_file_before_launch'; outcomes = @{}; steps = @(
      @{ vissim = 1; note = 'STOP_FO_LAUNCHER present'; write = @(@{ path = 'STOP_FO_LAUNCHER'; text = 'stop' }) }, @{ vissim = 0; note = 'free' });
    expect_launched = @(); expect_stop = 'STOP_FILE'; expect_exit = 0; expect_tryend = @{}; expect_log = @('LAUNCH_STOPPED reason=STOP_FILE', 'LAUNCHER_EXIT launching stopped') },
  @{ name = 'C2_stop_file_after_s31'; outcomes = @{}; steps = @(
      @{ vissim = 1; note = 'free -> s31' }, @{ vissim = 2; note = 'STOP appears'; write = @(@{ path = 'STOP_FO_LAUNCHER'; text = 'stop' }) },
      @{ vissim = 1; note = 's31 completes'; write = $done31 });
    expect_launched = @('s31_run1_try1'); expect_stop = 'STOP_FILE'; expect_exit = 0; expect_tryend = @{ s31_run1_try1 = 'completed' }; expect_log = @('LAUNCHER_EXIT launching stopped') },
  @{ name = 'D_seat_refusal_retry'; outcomes = @{ s31_run1_try1 = 'refused' }; steps = @(
      @{ vissim = 3; note = 'free -> s31 try1, runner refuses at cap' }, @{ vissim = 4; note = 'cap' }, @{ vissim = 3; note = 'free -> s31 try2' }, @{ vissim = 4; note = 'cap' });
    expect_launched = @('s31_run1_try1', 's31_run1_try2'); expect_stop = ''; expect_exit = 0; expect_tryend = @{ s31_run1_try1 = 'seat_refused' };
    expect_log = @('action=SEAT_BUSY s31_run1_try2', 'VISSIM_WAIT_END s31_run1_try1 reason=run_ended') },
  @{ name = 'E_abnormal_end_stops'; outcomes = @{}; steps = @(
      @{ vissim = 2; note = 'free -> s31' }, @{ vissim = 4; note = 'cap' },
      @{ vissim = 2; note = 's31 runner exit 1 after watchdog started'; write = @(@{ path = 's31\fo_launch\wrapper_run1_try1_end.json'; text = '{"runner_exit":1}' }, @{ path = 's31\sdmpc\launch.log'; text = 'FAIL' }) },
      @{ vissim = 1; note = 'free, must not launch' });
    expect_launched = @('s31_run1_try1'); expect_stop = 'ABNORMAL_END'; expect_exit = 0; expect_tryend = @{ s31_run1_try1 = 'abnormal:runner_exit_1' }; expect_log = @('LAUNCH_STOPPED reason=ABNORMAL_END') },
  @{ name = 'E2_wrapper_gone_no_record'; outcomes = @{}; steps = @(
      @{ vissim = 2; note = 'free -> s31' }, @{ vissim = 2; note = 's31 wrapper gone, no record'; dead = @('s31_run1_try1') }, @{ vissim = 1; note = 'free, must not launch' });
    expect_launched = @('s31_run1_try1'); expect_stop = 'ABNORMAL_END'; expect_exit = 0; expect_tryend = @{ s31_run1_try1 = 'abnormal:wrapper_gone_without_record' }; expect_log = @('LAUNCH_STOPPED reason=ABNORMAL_END') },
  @{ name = 'F_recount_just_before_launch'; outcomes = @{}; steps = @(
      @{ vissim = 3; vissim_recount = 4; note = 'other session takes the seat between count and launch' }, @{ vissim = 3; note = 'free -> s31' });
    expect_launched = @('s31_run1_try1'); expect_stop = ''; expect_exit = 0; expect_tryend = @{}; expect_log = @('action=SEAT_BUSY_RECOUNT s31_run1_try1') },
  @{ name = 'G_pending_reservation'; outcomes = @{ s31_run1_try1 = 'timeout' }; steps = @(
      @{ vissim = 2; note = 'free -> s31, its VISSIM does not show within the wait' }, @{ vissim = 3; note = '3 + pending 1 = cap' },
      @{ vissim = 3; note = 's31 VISSIM shows'; write = @(@{ path = 's31\sdmpc\WATCHDOG_PROGRESS.txt'; text = "10-26 00:00:00  VISSIM_PROCESS sdmpc31_sdmpc9000_s31 pid=7003`r`n" }) });
    expect_launched = @('s31_run1_try1', 's41_run1_try1'); expect_stop = ''; expect_exit = 0; expect_tryend = @{};
    expect_log = @('VISSIM_WAIT_END s31_run1_try1 reason=timeout', 'pending=1 .* action=SEAT_BUSY s41_run1_try1 \(vissim=3 pending=1\)') },
  @{ name = 'H_stall_relaunch_once'; outcomes = @{}; steps = @(
      @{ vissim = 1; note = 'free -> s31' }, @{ vissim = 2; note = 'free -> s41' }, @{ vissim = 3; note = 'free -> s43' },
      @{ vissim = 3; note = 'monitor: stall record, s31 run1 stopped, folder renamed'; dead = @('s31_run1_try1'); write = @(@{ path = '_launcher\stalled_s31_run1.json'; text = '{"by":"monitor"}' }); rename = @(@{ from = 's31'; to = 's31_try1_stalled' }) },
      @{ vissim = 4; note = 'cap' },
      @{ vissim = 4; note = 'monitor: run2 stalls too'; dead = @('s31_run2_try1'); write = @(@{ path = '_launcher\stalled_s31_run2.json'; text = '{"by":"monitor"}' }) },
      @{ vissim = 2; note = 's41, s43 complete'; write = ($done41 + $done43) });
    expect_launched = @('s31_run1_try1', 's31_run2_try1', 's41_run1_try1', 's43_run1_try1'); expect_stop = 'ABNORMAL_END'; expect_exit = 0;
    expect_tryend = @{ s31_run1_try1 = 'stalled_handled'; s31_run2_try1 = 'abnormal:stalled_again'; s41_run1_try1 = 'completed'; s43_run1_try1 = 'completed' };
    expect_log = @('LAUNCHED s31_run2_try1', 'LAUNCH_STOPPED reason=ABNORMAL_END detail=s31 s31_run2_try1 abnormal:stalled_again', 'POLL n=6 .*s41=active.*stop=ABNORMAL_END action=none', 'LAUNCHER_EXIT all seeds ended') },
  @{ name = 'I_disk_low'; outcomes = @{}; steps = @(@{ vissim = 1; disk = @{ C = 7.5; D = 200 }; note = 'C below 8 GB' });
    expect_launched = @(); expect_stop = 'DISK_LOW'; expect_exit = 0; expect_tryend = @{}; expect_log = @('LAUNCH_STOPPED reason=DISK_LOW') },
  @{ name = 'I2_disk_per_run'; outcomes = @{}; steps = @(
      @{ vissim = 1; disk = @{ C = 20; D = 20 }; note = 'D 20 >= 8 x 1 -> s31' }, @{ vissim = 2; disk = @{ C = 20; D = 20 }; note = 'D 20 >= 8 x 2 -> s41' },
      @{ vissim = 3; disk = @{ C = 20; D = 20 }; note = 'D 20 < 8 x 3 -> stop' });
    expect_launched = @('s31_run1_try1', 's41_run1_try1'); expect_stop = 'DISK_LOW'; expect_exit = 0; expect_tryend = @{}; expect_log = @('need D>=24') },
  @{ name = 'J_seat_wait_12h'; outcomes = @{}; steps = @(@{ vissim = 4; first_start_hours_ago = 12.5; note = 'still at cap 12.5 h after first start' });
    expect_launched = @(); expect_stop = 'SEAT_WAIT_LIMIT'; expect_exit = 0; expect_tryend = @{}; expect_log = @('LAUNCH_STOPPED reason=SEAT_WAIT_LIMIT') },
  @{ name = 'M_gate_not_passed'; gate = '{"pass": false}'; outcomes = @{}; steps = @(@{ vissim = 0; note = 'gate pass false: must not launch' }, @{ vissim = 0; note = 'free' });
    expect_launched = @(); expect_stop = 'GATE_NOT_PASSED'; expect_exit = 0; expect_tryend = @{}; expect_log = @('LAUNCH_STOPPED reason=GATE_NOT_PASSED', 'LAUNCHER_EXIT launching stopped') },
  @{ name = 'N_pre_changed_after_s31'; outcomes = @{}; steps = @(
      @{ vissim = 1; note = 'free -> s31' }, @{ vissim = 2; note = 'PRE file changed on disk'; write = @(@{ path = '_fixed\PRE_FO.md'; text = 'changed' }) },
      @{ vissim = 2; note = 'still changed' }, @{ vissim = 1; note = 's31 completes'; write = $done31 });
    expect_launched = @('s31_run1_try1'); expect_stop = 'SHA_MISMATCH'; expect_exit = 0; expect_tryend = @{ s31_run1_try1 = 'completed' }; expect_log = @('LAUNCH_STOPPED reason=SHA_MISMATCH') },
  @{ name = 'L_marker_without_receipt'; outcomes = @{}; steps = @(
      @{ vissim = 1; note = 'existing marker, no receipt'; write = @(@{ path = '_launcher\launched_s31_run1_try1.json'; text = '{"key":"s31_run1_try1"}' }) });
    expect_launched = @('s31_run1_try1'); expect_lines = 0; expect_stop = 'ABNORMAL_END'; expect_exit = 0; expect_tryend = @{ s31_run1_try1 = 'abnormal:marker_without_receipt' }; expect_log = @('abnormal:marker_without_receipt') }
)
# FO addition: every dry-run root gets its own PRE / rule / pins / gate files (_fixed\...) and passes their shas.
function Invoke-Launcher([string]$root, [string]$log, [string]$scen, [string]$gateText = '{"pass": true}') {
  $fx = Join-Path $root '_fixed'; New-Item -ItemType Directory -Force -Path $fx | Out-Null
  $files = [ordered]@{ Pre = 'PRE_FO.md'; Rule = 'COMPARE_RULE_FO.md'; Pins = 'PINS_FO.sha256'; Gate = 'fog_summary.json' }
  $a = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $L, '-Mode', 'dryrun', '-Root', $root, '-Log', $log, '-Scenario', $scen, '-PollSec', '0', '-VissimUpWaitSec', '3')
  foreach ($k in $files.Keys) {
    $p = Join-Path $fx $files[$k]
    if (-not (Test-Path -LiteralPath $p)) { $body = 'dryrun ' + $k; if ($k -eq 'Gate') { $body = $gateText }; [IO.File]::WriteAllText($p, $body, $UTF8) }
    $a += @(('-' + $k + 'File'), $p, ('-' + $k + 'Sha'), (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant())
  }
  & powershell.exe @a | Out-Null
  return $LASTEXITCODE
}
function Check($c, [string]$root, [string]$log, [int]$code) {
  $LD = Join-Path $root '_launcher'
  $got = @(Get-ChildItem -LiteralPath $LD -Filter 'launched_*.json' -ErrorAction SilentlyContinue | ForEach-Object { $_.Name -replace '^launched_', '' -replace '\.json$', '' } | Sort-Object)
  $want = @($c.expect_launched | Sort-Object)
  $stop = ''; $sp = Join-Path $LD 'LAUNCH_STOPPED.json'; if (Test-Path -LiteralPath $sp) { $stop = [string](Get-Content -LiteralPath $sp -Raw -Encoding UTF8 | ConvertFrom-Json).reason }
  $txt = Get-Content -LiteralPath $log -Raw -Encoding UTF8
  $bad = @()
  if (($got -join ',') -ne ($want -join ',')) { $bad += ('launched got=[' + ($got -join ',') + '] want=[' + ($want -join ',') + ']') }
  if ($stop -ne $c.expect_stop) { $bad += ('stop got=' + $stop + ' want=' + $c.expect_stop) }
  if ($code -ne $c.expect_exit) { $bad += ('exit got=' + $code + ' want=' + $c.expect_exit) }
  foreach ($k in $c.expect_tryend.Keys) {
    $p = Join-Path $LD ('tryend_' + $k + '.json'); $s = ''
    if (Test-Path -LiteralPath $p) { $s = [string](Get-Content -LiteralPath $p -Raw -Encoding UTF8 | ConvertFrom-Json).status }
    if ($s -ne $c.expect_tryend[$k]) { $bad += ('tryend ' + $k + ' got=' + $s + ' want=' + $c.expect_tryend[$k]) }
  }
  foreach ($pat in $c.expect_log) { if ($txt -notmatch $pat) { $bad += ('log missing /' + $pat + '/') } }
  if ($txt -match ' ERROR ') { $bad += 'log has ERROR' }
  $lines = 0; $wl = Join-Path $root 'wmi_launch_lines.txt'; if (Test-Path -LiteralPath $wl) { $lines = @(Get-Content -LiteralPath $wl).Count }
  $wantLines = $want.Count; if ($c.ContainsKey('expect_lines')) { $wantLines = [int]$c.expect_lines }
  if ($lines -ne $wantLines) { $bad += ('wmi_launch_lines got=' + $lines + ' want=' + $wantLines) }
  return ,$bad
}
$realRoot = 'D:\VISSIM_runs\20261028_codex_fo_v3c3'
$realBefore = Test-Path -LiteralPath $realRoot
$vis0 = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^Vissim' } | ForEach-Object { $_.ProcessId }) -join ','
W ('==== dry run ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' KST run_dir=' + $RUN)
W ('launcher sha256=' + (Get-FileHash -LiteralPath $L -Algorithm SHA256).Hash.ToLowerInvariant() + ' harness sha256=' + (Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant())
W ('real root exists before=' + $realBefore + ' ; PC VISSIM before=[' + $vis0 + ']')
$nPass = 0; $nFail = 0
foreach ($c in $cases) {
  $dir = Join-Path $RUN $c.name; $root = Join-Path $dir 'root'; New-Item -ItemType Directory -Force -Path $root | Out-Null
  $scen = Join-Path $dir 'scenario.json'; $log = Join-Path $dir 'launcher.log'
  ([ordered]@{ outcomes = $c.outcomes; steps = $c.steps } | ConvertTo-Json -Depth 8) | Set-Content -Encoding UTF8 -LiteralPath $scen
  $gt = '{"pass": true}'; if ($c.ContainsKey('gate')) { $gt = [string]$c.gate }
  $code = Invoke-Launcher $root $log $scen $gt
  $bad = Check $c $root $log $code
  if ($bad.Count) { $nFail++; W ('CASE ' + $c.name + ' FAIL exit=' + $code + ' :: ' + ($bad -join ' | ')) } else { $nPass++; W ('CASE ' + $c.name + ' PASS exit=' + $code) }
  W ('---- ' + $c.name + ' launcher.log'); W ((Get-Content -LiteralPath $log -Raw -Encoding UTF8).TrimEnd())
}
# B: restart on the same root (existing markers must never be launched again)
$dir = Join-Path $RUN 'B_restart_existing_marker'; $root = Join-Path $dir 'root'; New-Item -ItemType Directory -Force -Path $root | Out-Null
$log = Join-Path $dir 'launcher.log'
$s1 = Join-Path $dir 'scenario1.json'; ([ordered]@{ outcomes = @{}; steps = @(@{ vissim = 1; note = 'first launcher: free -> s31, then the launcher stops (session loss)' }) } | ConvertTo-Json -Depth 8) | Set-Content -Encoding UTF8 -LiteralPath $s1
$code1 = Invoke-Launcher $root $log $s1
$s2 = Join-Path $dir 'scenario2.json'; ([ordered]@{ outcomes = @{}; steps = @(@{ vissim = 2; note = 'restarted launcher: s31 marker exists -> s41' }, @{ vissim = 3; note = 'free -> s43' }, @{ vissim = 4; note = 'nothing left' }) } | ConvertTo-Json -Depth 8) | Set-Content -Encoding UTF8 -LiteralPath $s2
$code2 = Invoke-Launcher $root $log $s2
$cB = @{ expect_launched = @('s31_run1_try1', 's41_run1_try1', 's43_run1_try1'); expect_stop = ''; expect_exit = 0; expect_tryend = @{};
  expect_log = @('s31=active\(s31_run1_try1 vissim=60311\) s41=waiting_first_launch .* action=LAUNCHED s41_run1_try1', 'action=nothing_to_launch') }
$bad = Check $cB $root $log $code2
if ($code1 -ne 0) { $bad += ('first exit=' + $code1) }
if ($bad.Count) { $nFail++; W ('CASE B_restart_existing_marker FAIL :: ' + ($bad -join ' | ')) } else { $nPass++; W ('CASE B_restart_existing_marker PASS exit=' + $code1 + ',' + $code2) }
W '---- B_restart_existing_marker launcher.log'; W ((Get-Content -LiteralPath $log -Raw -Encoding UTF8).TrimEnd())
# K: a second launcher while the instance lock is held
$dir = Join-Path $RUN 'K_instance_lock'; $root = Join-Path $dir 'root'; New-Item -ItemType Directory -Force -Path (Join-Path $root '_launcher') | Out-Null
$log = Join-Path $dir 'launcher.log'; $sK = Join-Path $dir 'scenario.json'
([ordered]@{ outcomes = @{}; steps = @(@{ vissim = 0; note = 'must not run' }) } | ConvertTo-Json -Depth 8) | Set-Content -Encoding UTF8 -LiteralPath $sK
$hold = [IO.File]::Open((Join-Path $root '_launcher\instance.lock'), [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
try { $codeK = Invoke-Launcher $root $log $sK } finally { $hold.Dispose() }
$txtK = Get-Content -LiteralPath $log -Raw -Encoding UTF8
$okK = ($codeK -eq 2) -and ($txtK -match 'INSTANCE_LOCKED') -and -not (Test-Path -LiteralPath (Join-Path $root '_launcher\STATE.json'))
if ($okK) { $nPass++; W ('CASE K_instance_lock PASS exit=' + $codeK) } else { $nFail++; W ('CASE K_instance_lock FAIL exit=' + $codeK) }
W '---- K_instance_lock launcher.log'; W $txtK.TrimEnd()
$realAfter = Test-Path -LiteralPath $realRoot
$vis1 = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^Vissim' } | ForEach-Object { $_.ProcessId }) -join ','
W ('real root exists after=' + $realAfter + ' ; PC VISSIM after=[' + $vis1 + ']')
W ('SUMMARY pass=' + $nPass + ' fail=' + $nFail + ' run_dir=' + $RUN)
'SUMMARY pass=' + $nPass + ' fail=' + $nFail + ' run_dir=' + $RUN
