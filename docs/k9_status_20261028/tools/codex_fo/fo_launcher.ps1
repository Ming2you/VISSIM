# [FO copy 2026-10-27 KST, PRE_FO s5: copy of codex_handoff/b/b_launcher.ps1 (sha256 cb657ecbe0aa01fb810137422646fdba3c652191db7cc070c040058ae692d463) with names changed and the declared FO
# additions; full diff in codex_handoff/fo/work/run/launcher_b_to_fo.diff. The original header follows.]
# FO launcher (2026-10-27 KST, user decision D-K9-113; rules PRE_FO.md s5-s7; copy of the B launcher cb657ecb... with names changed). Windows PowerShell 5.1.
# Started detached by WMI (Win32_Process.Create) so it survives the Claude session. ASCII only (PS 5.1 reads BOM-less files as ANSI).
#
# What it does (one loop, poll every -PollSec s, one log line per poll in -Log):
#   * Seeds v3c3-s31, s41, s43, in this order. Each seed is launched for one run (attempt 1). A runner refusal at the
#     4-seat cap (runner exit 1, 'at the 4-seat cap', no launch.log, no runlog) is a failed launch TRY, not a run
#     (PRE_FO s6-4): the same seed/attempt is tried again (try+1, same results root) when a seat is free.
#   * Seat rule (s6): under an exclusive lock file it counts PC-wide processes named ^Vissim (ours + others) plus our own
#     launched runs whose VISSIM has not shown yet ("pending"; stricter than s6, never looser), and launches only when
#     count + pending < 4. The count is taken again just before the launch. After a launch it keeps the lock until the
#     watchdog writes 'VISSIM_PROCESS' for that run, or the run ends, or -VissimUpWaitSec (600 s) passes.
#   * Launch = PRE_B s1 on FRZ_FO with the FO config via fo_wrapper.ps1 (RW_* cleared, env_hsw, PYTHONHASHSEED=0) under codex pwsh 7,
#     WMI Win32_Process.Create, PriorityClass 32 (Normal), hidden, CurrentDirectory = FRZ_B1.
#   * Once-only: before WMI Create it creates _launcher/launched_s<seed>_run<A>_try<T>.json with FileMode.CreateNew; an
#     existing marker is never launched again, also after a launcher restart. Receipt: _launcher/receipt_<key>.json,
#     <res>/b_launch/wmi_launch_run<A>_try<T>.json, and one line in <root>/wmi_launch_lines.txt.
#   * Stops launching (writes _launcher/LAUNCH_STOPPED.json once, keeps it across restarts) on: STOP file
#     (<root>/STOP_FO_LAUNCHER or <root>/STOP), any launched run ending abnormally (runner/wrapper exit != 0 other than a
#     seat refusal, no STAGE=SIM_DONE / SIM_SEC=9000, wrapper error, wrapper gone without a record, WMI ReturnValue != 0),
#     disk (C < 8 GB, or D < 8 GB x (our active runs + this run)), a fixed-file sha change, seat wait > -SeatWaitHours
#     (12 h, s5-4) from the first launcher start (relaunch: from the stall record), > 20 tries.
#   * One-time relaunch (s7): it never kills. The monitor that stops a stalled run first writes
#     _launcher/stalled_s<seed>_run1.json, then stops only that run's PIDs and renames <root>/s<seed> to
#     <root>/s<seed>_try1_stalled. The launcher then treats run1 as handled (not abnormal) and launches run2 once into
#     <root>/s<seed> under the same seat rule. A stall record for run2 is abnormal.
#   * Exits when no launched run is active and (all seeds ended or launching stopped), or after -GiveUpHours (72 h) from
#     the first start. Runs it started keep going (they are detached). Exit 2 = another launcher holds the instance lock.
#   * -Mode dryrun: no WMI, no process is started; VISSIM counts, disk, run outcomes and files come from -Scenario
#     (JSON); -Root must be under b/dryrun. Used to test the logic before the real start.
param(
  [ValidateSet('run', 'dryrun')][string]$Mode = 'run',
  [string]$Root = 'D:\VISSIM_runs\20261028_codex_fo_v3c3',
  [string]$Log = '',
  [string]$Scenario = '',
  [ValidateRange(0, 600)][int]$PollSec = 90,
  [ValidateRange(1, 3600)][int]$VissimUpWaitSec = 600,
  [double]$SeatWaitHours = 12,
  [double]$GiveUpHours = 72,
  [string]$PreFile = '',
  [string]$PreSha = '',
  [string]$RuleFile = '',
  [string]$RuleSha = '',
  [string]$PinsFile = '',
  [string]$PinsSha = '',
  [string]$GateFile = '',
  [string]$GateSha = ''
)
$ErrorActionPreference = 'Stop'
# Script-scope copy of -Mode, always read as $script:LMODE: PowerShell names are case-insensitive, so a local $mode in a
# function would otherwise shadow -Mode for that function and every function it calls (found by the dry run).
$script:LMODE = $Mode
$SPB = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\fo'
$REAL_ROOT = 'D:\VISSIM_runs\20261028_codex_fo_v3c3'
$DRY_BASE = Join-Path $SPB 'dryrun'
$FRZ = 'D:\VISSIM-merge\k8_gate_trees\codexhandoff\fo\frozen\sdmpc31_a49981ff_202610271954'
$PWSH = 'C:\Users\TRLAB\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
$WRAPPER = Join-Path $SPB 'fo_wrapper.ps1'
$SEEDS = @(31, 41, 43)
$CAP = 4
$MAX_TRY = 20
$UTF8 = New-Object System.Text.UTF8Encoding $false
$FIXED = [ordered]@{}
$FIXED[(Join-Path $FRZ 'FREEZE.json')] = 'd7fa4db6c3ca854a3c6c7dfd352f97626d6f9ca9d0e5ea6f18e36fc779d37373'
$FIXED[(Join-Path $FRZ 'diagnostics\b0_v3c3\config_fo_v3c3.json')] = '80e0abefdb25526374c97d8f7a6b45b9ad434db1f3499cec208985038ac249f3'
$FIXED[(Join-Path $FRZ 'diagnostics\sdmpc_n31_20260924\integration_20260926\run_closedloop3000.ps1')] = '6ff68b385a4bf6dab23a26bea5a6015641a77808230bfc8366bbc5d2554b38f7'
$FIXED[(Join-Path $FRZ 'diagnostics\sdmpc_n31_20260924\network\baseline_s31_v3c3nc.inpx')] = '3de889f0257d998bed50611f798ea388bcf69396dbc40e5726b1e88ebdd31c2e'
$FIXED[$WRAPPER] = (Get-FileHash -LiteralPath $WRAPPER -Algorithm SHA256).Hash.ToLowerInvariant()   # FO: the start script checks it against -WrapperSha
# FO additions (PRE_FO s5): PRE_FO, COMPARE_RULE_FO, PINS_FO and the gate summary join the FIXED list (sha given at start)
$PAIRS4 = @(@('PreFile', $PreFile, $PreSha, 'PRE_FO.md'), @('RuleFile', $RuleFile, $RuleSha, 'COMPARE_RULE_FO.md'),
            @('PinsFile', $PinsFile, $PinsSha, 'PINS_FO.sha256'), @('GateFile', $GateFile, $GateSha, 'work\gate\fog_summary.json'))
foreach ($q in $PAIRS4) {
  $qf = [string]$q[1]; if (-not $qf) { $qf = Join-Path $SPB $q[3] }
  if ([string]$q[2] -notmatch '^[0-9a-f]{64}$') { throw ($q[0] + ' sha (64 hex) is required') }
  if ($script:LMODE -eq 'run' -and [IO.Path]::GetFullPath($qf) -ne (Join-Path $SPB $q[3])) { throw ('run mode ' + $q[0] + ' must be ' + (Join-Path $SPB $q[3])) }
  $FIXED[[IO.Path]::GetFullPath($qf)] = [string]$q[2]
  if ($q[0] -eq 'GateFile') { $GATE_PATH = [IO.Path]::GetFullPath($qf) }
}

$Root = [IO.Path]::GetFullPath($Root).TrimEnd('\')
if ($script:LMODE -eq 'run') {
  if ($Root -ne $REAL_ROOT) { throw "run mode root must be $REAL_ROOT" }
  if (-not $Log) { $Log = Join-Path $SPB 'fo_launcher.log' }
  if ($Scenario) { throw 'run mode takes no scenario' }
} else {
  if (-not $Root.StartsWith($DRY_BASE + '\', [StringComparison]::OrdinalIgnoreCase)) { throw "dryrun root must be under $DRY_BASE" }
  if (-not $Log -or -not $Scenario) { throw 'dryrun needs -Log and -Scenario' }
}
$LD = Join-Path $Root '_launcher'
New-Item -ItemType Directory -Force -Path $LD | Out-Null
$SELF_SHA = (Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant()

function Note([string]$m) {
  $line = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' KST [' + $script:LMODE + ' pid=' + $PID + '] ' + $m
  for ($r = 0; $r -lt 5; $r++) { try { [IO.File]::AppendAllText($Log, $line + "`r`n", $UTF8); break } catch { Start-Sleep -Milliseconds 200 } }
}
function Save-Json([string]$path, $obj) { [IO.File]::WriteAllText($path, ($obj | ConvertTo-Json -Depth 8), $UTF8) }
function New-Marker([string]$path, $obj) {
  $fs = $null
  try { $fs = [IO.File]::Open($path, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None) } catch { return $false }
  try { $b = $UTF8.GetBytes(($obj | ConvertTo-Json -Depth 8)); $fs.Write($b, 0, $b.Length) } finally { $fs.Dispose() }
  return $true
}
function Read-Json([string]$path) {
  if (-not (Test-Path -LiteralPath $path)) { return $null }
  try { return (Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json) } catch { return $null }
}
function Read-Text([string]$path) {
  if (-not (Test-Path -LiteralPath $path)) { return '' }
  $fs = $null
  try {
    $fs = [IO.File]::Open($path, [IO.FileMode]::Open, [IO.FileAccess]::Read, ([IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete))
    $sr = New-Object IO.StreamReader($fs, $UTF8, $true)
    return $sr.ReadToEnd()
  } catch { return '' } finally { if ($fs) { $fs.Dispose() } }
}
function Open-Lock([string]$path) {
  try { return [IO.File]::Open($path, [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None) } catch { return $null }
}
function Get-Name([int]$seed) { return ('sdmpc31_sdmpc9000_s' + $seed) }
function Get-Key([int]$seed, [int]$attempt, [int]$try) { return ('s{0}_run{1}_try{2}' -f $seed, $attempt, $try) }
function Get-Res([int]$seed, [int]$attempt) {
  $base = Join-Path $Root ('s' + $seed)
  if ($attempt -eq 1 -and (Test-Path -LiteralPath (Join-Path $LD ('stalled_s{0}_run1.json' -f $seed)))) {
    $st = $base + '_try1_stalled'
    if (Test-Path -LiteralPath $st) { return $st }
  }
  return $base
}
function Test-Fixed {
  foreach ($p in $FIXED.Keys) {
    if (-not (Test-Path -LiteralPath $p)) { return ('missing ' + $p) }
    $h = (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($h -ne $FIXED[$p]) { return ($p + ' ' + $h) }
  }
  return ''
}

# ---------------- dry-run simulation ----------------
$script:sc = $null; $script:step = -1; $script:simVissim = 0; $script:simRecount = 0; $script:simDisk = $null; $script:simDead = @()
function Apply-Step {
  $script:step++
  $steps = @($script:sc.steps)
  if ($script:step -ge $steps.Count) { return $false }
  $s = $steps[$script:step]
  $script:simVissim = [int]$s.vissim
  if ($null -ne $s.vissim_recount) { $script:simRecount = [int]$s.vissim_recount } else { $script:simRecount = $script:simVissim }
  if ($null -ne $s.disk) { $script:simDisk = @{ C = [double]$s.disk.C; D = [double]$s.disk.D } }
  foreach ($w in @($s.write)) { if ($null -eq $w) { continue }
    $p = Join-Path $Root $w.path; New-Item -ItemType Directory -Force -Path (Split-Path -Parent $p) | Out-Null
    [IO.File]::WriteAllText($p, [string]$w.text, $UTF8) }
  foreach ($r in @($s.rename)) { if ($null -eq $r) { continue }; Move-Item -LiteralPath (Join-Path $Root $r.from) -Destination (Join-Path $Root $r.to) }
  foreach ($d in @($s.dead)) { if ($d) { $script:simDead += [string]$d } }
  if ($null -ne $s.first_start_hours_ago) {
    $fsp = Join-Path $LD 'first_start.json'; $o = Read-Json $fsp
    $t = (Get-Date).ToUniversalTime().Ticks - [int64]([double]$s.first_start_hours_ago * [TimeSpan]::TicksPerHour)
    Save-Json $fsp ([ordered]@{ time = $o.time; start_ticks = [string]$t; launcher_pid = $o.launcher_pid; launcher_sha256 = $o.launcher_sha256; mode = $o.mode; dryrun_shifted = $true })
  }
  Note ('DRYRUN_STEP ' + ($script:step + 1) + '/' + $steps.Count + ' vissim=' + $script:simVissim + ' recount=' + $script:simRecount + ' note=' + [string]$s.note)
  return $true
}
function Get-VissimProcs([switch]$Recount) {
  if ($script:LMODE -eq 'dryrun') {
    $n = $script:simVissim; if ($Recount) { $n = $script:simRecount }
    $l = @(); for ($i = 1; $i -le $n; $i++) { $l += [pscustomobject]@{ ProcessId = 7000 + $i; Name = 'Vissim200.exe' } }
    return $l
  }
  return @(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^Vissim' })
}
function Get-Disk {
  if ($script:LMODE -eq 'dryrun' -and $script:simDisk) { return $script:simDisk }
  return @{ C = [math]::Round((Get-PSDrive C).Free / 1GB, 1); D = [math]::Round((Get-PSDrive D).Free / 1GB, 1) }
}

# ---------------- run records ----------------
function Get-Tries([int]$seed) {
  $l = @()
  foreach ($f in @(Get-ChildItem -LiteralPath $LD -Filter ('launched_s{0}_run*_try*.json' -f $seed) -ErrorAction SilentlyContinue)) {
    $m = [regex]::Match($f.Name, '^launched_s(\d+)_run(\d+)_try(\d+)\.json$')
    if ($m.Success -and [int]$m.Groups[1].Value -eq $seed) {
      $a = [int]$m.Groups[2].Value; $t = [int]$m.Groups[3].Value
      $l += [pscustomobject]@{ seed = $seed; attempt = $a; try = $t; key = (Get-Key $seed $a $t); status = ''; res = ''; vissim_pid = 0 }
    }
  }
  return @($l | Sort-Object attempt, try)
}
function Test-WrapperAlive($t, $rcpt) {
  $tmode = 'run{0}_try{1}' -f $t.attempt, $t.try
  $bl = Join-Path (Get-Res $t.seed $t.attempt) 'fo_launch'
  if ($script:LMODE -eq 'dryrun') {
    if ($script:simDead -contains $t.key) { return $false }
    if ((Test-Path -LiteralPath (Join-Path $bl ('wrapper_' + $tmode + '_end.json'))) -or (Test-Path -LiteralPath (Join-Path $bl ('wrapper_' + $tmode + '_error.json')))) { return $false }
    return $true
  }
  if (-not $rcpt -or -not $rcpt.ProcessId) { return $false }
  $p = Get-CimInstance Win32_Process -Filter ('ProcessId=' + [int]$rcpt.ProcessId) -ErrorAction SilentlyContinue
  if (-not $p) { return $false }
  if ($rcpt.wrapper_creation_ticks) { if ([string]$p.CreationDate.ToUniversalTime().Ticks -ne [string]$rcpt.wrapper_creation_ticks) { return $false } }
  $want = '*fo_wrapper.ps1" -Seed ' + $t.seed + ' -Attempt ' + $t.attempt + ' -Try ' + $t.try + '*'
  return ([string]$p.CommandLine -like $want)
}
function Save-TryEnd($t, [string]$status, [string]$detail) {
  $p = Join-Path $LD ('tryend_' + $t.key + '.json')
  if (-not (Test-Path -LiteralPath $p)) {
    [void](New-Marker $p ([ordered]@{ key = $t.key; status = $status; detail = $detail; res = (Get-Res $t.seed $t.attempt); time = (Get-Date).ToString('o'); launcher_pid = $PID }))
    Note ('TRY_END ' + $t.key + ' status=' + $status + ' detail=' + $detail)
  }
  return $status
}
function Get-TryStatus($t) {
  $e = Read-Json (Join-Path $LD ('tryend_' + $t.key + '.json'))
  if ($e) { return [string]$e.status }
  $rcpt = Read-Json (Join-Path $LD ('receipt_' + $t.key + '.json'))
  if (-not $rcpt) { return (Save-TryEnd $t 'abnormal:marker_without_receipt' '') }
  if ([int]$rcpt.ReturnValue -ne 0) { return (Save-TryEnd $t ('abnormal:wmi_return_value_' + $rcpt.ReturnValue) '') }
  if (Test-WrapperAlive $t $rcpt) { return 'active' }
  if (Test-Path -LiteralPath (Join-Path $LD ('stalled_s{0}_run{1}.json' -f $t.seed, $t.attempt))) {
    if ($t.attempt -eq 1) { return (Save-TryEnd $t 'stalled_handled' 'stall record by the monitor (PRE_FO s7)') }
    return (Save-TryEnd $t 'abnormal:stalled_again' 'stall record for run2')
  }
  $res = Get-Res $t.seed $t.attempt
  $tmode = 'run{0}_try{1}' -f $t.attempt, $t.try
  $bl = Join-Path $res 'fo_launch'
  $endJ = Join-Path $bl ('wrapper_' + $tmode + '_end.json'); $errJ = Join-Path $bl ('wrapper_' + $tmode + '_error.json')
  if ($script:LMODE -eq 'run' -and -not (Test-Path -LiteralPath $endJ) -and -not (Test-Path -LiteralPath $errJ)) { Start-Sleep -Seconds 3 }
  $rl = Join-Path $res ('sdmpc\runlog_' + (Get-Name $t.seed) + '.txt')
  $ll = Join-Path $res 'sdmpc\launch.log'
  if (Test-Path -LiteralPath $endJ) {
    $end = Read-Json $endJ
    if ($null -eq $end) { return (Save-TryEnd $t 'abnormal:unreadable_wrapper_end' $endJ) }
    $code = [int]$end.runner_exit
    if ($code -eq 0) {
      $txt = Read-Text $rl
      if ($txt -match '(?m)^STAGE=SIM_DONE\r?$' -and $txt -match '(?m)^SIM_SEC=9000\r?$') { return (Save-TryEnd $t 'completed' 'runner_exit 0, STAGE=SIM_DONE, SIM_SEC=9000') }
      return (Save-TryEnd $t 'abnormal:exit0_without_SIM_DONE_9000' $rl)
    }
    $det = ''
    $ns = Read-Json (Join-Path $bl ('native_status_' + $tmode + '.json'))
    if ($ns) { $det = [string]$ns.details }
    if (-not $det) { $det = (Read-Text (Join-Path $bl ('runner_' + $tmode + '.log'))) -replace '\s+', ' ' }
    $noRun = (-not (Test-Path -LiteralPath $ll)) -and (-not (Test-Path -LiteralPath $rl))
    if ($noRun -and $det -match 'at the 4-seat cap') { return (Save-TryEnd $t 'seat_refused' ('runner_exit ' + $code + ', runner refused at the 4-seat cap, no launch.log, no runlog')) }
    if ($noRun -and $det -match 'STOP exists') { return (Save-TryEnd $t 'stop_refused' ('runner_exit ' + $code + ', runner refused: STOP exists')) }
    $short = $det; if ($short.Length -gt 300) { $short = $short.Substring(0, 300) }
    return (Save-TryEnd $t ('abnormal:runner_exit_' + $code) $short)
  }
  if (Test-Path -LiteralPath $errJ) {
    $er = Read-Json $errJ; $msg = ''; if ($er) { $msg = [string]$er.error }; if ($msg.Length -gt 300) { $msg = $msg.Substring(0, 300) }
    return (Save-TryEnd $t 'abnormal:wrapper_error' $msg)
  }
  return (Save-TryEnd $t 'abnormal:wrapper_gone_without_record' ('no ' + $endJ))
}
function Get-RunVissimPid([string]$res, [int]$seed) {
  # The watchdog's Log writes each line to WATCHDOG_PROGRESS.txt and to the host (= the runner's launch.log).
  foreach ($f in @('sdmpc\WATCHDOG_PROGRESS.txt', 'sdmpc\launch.log')) {
    $txt = Read-Text (Join-Path $res $f)
    $ms = [regex]::Matches($txt, ('VISSIM_PROCESS ' + (Get-Name $seed) + ' pid=(\d+)'))
    if ($ms.Count) { return [int]$ms[$ms.Count - 1].Groups[1].Value }
  }
  return 0
}
function Get-SeedState([int]$seed) {
  $o = [pscustomobject]@{ seed = $seed; tries = @(); active = @(); need = $null; abnormal = ''; stopref = ''; done = $false; label = '' }
  $tries = @(Get-Tries $seed)
  foreach ($t in $tries) {
    $t.status = Get-TryStatus $t
    $t.res = Get-Res $t.seed $t.attempt
    if ($t.status -eq 'active') { $t.vissim_pid = Get-RunVissimPid $t.res $seed }
  }
  $o.tries = $tries
  $attempt = 1
  while ($true) {
    $ta = @($tries | Where-Object { $_.attempt -eq $attempt })
    if ($ta.Count -eq 0) {
      if ($attempt -eq 1) { $o.need = @{ attempt = 1; try = 1 }; $o.label = 'waiting_first_launch'; break }
      $dir = Join-Path $Root ('s' + $seed)
      if ((Test-Path -LiteralPath $dir) -or -not (Test-Path -LiteralPath ($dir + '_try1_stalled'))) { $o.label = 'stalled_waiting_rename'; break }
      $o.need = @{ attempt = 2; try = 1 }; $o.label = 'waiting_relaunch'; break
    }
    for ($i = 0; $i -lt $ta.Count - 1; $i++) {
      if ($ta[$i].status -ne 'seat_refused') { $o.abnormal = $ta[$i].key + ' ' + $ta[$i].status + ' (a later try exists)'; break }
    }
    if ($o.abnormal) { $o.label = 'abnormal'; break }
    $last = $ta[$ta.Count - 1]
    if ($last.status -eq 'active') { $o.active = @($last); $o.label = 'active(' + $last.key + ' vissim=' + $last.vissim_pid + ')'; break }
    if ($last.status -eq 'completed') { $o.done = $true; $o.label = 'completed(' + $last.key + ')'; break }
    if ($last.status -eq 'seat_refused') { $o.need = @{ attempt = $attempt; try = $last.try + 1 }; $o.label = 'seat_refused_waiting(' + $last.key + ')'; break }
    if ($last.status -eq 'stop_refused') { $o.stopref = $last.key; $o.label = 'stop_refused(' + $last.key + ')'; break }
    if ($last.status -eq 'stalled_handled' -and $attempt -eq 1) { $attempt = 2; continue }
    $o.abnormal = $last.key + ' ' + $last.status; $o.label = 'abnormal(' + $last.key + ')'; break
  }
  return $o
}
function Get-Pending($states) {
  $n = 0
  foreach ($s in $SEEDS) { foreach ($a in @($states[$s].active)) { if ($a -and $a.vissim_pid -eq 0) { $n++ } } }
  return $n
}
function Get-StopReason { $s = Read-Json (Join-Path $LD 'LAUNCH_STOPPED.json'); if ($s) { return [string]$s.reason }; return '' }
function Set-Stop([string]$reason, [string]$detail) {
  $p = Join-Path $LD 'LAUNCH_STOPPED.json'
  if (-not (Test-Path -LiteralPath $p)) {
    [void](New-Marker $p ([ordered]@{ reason = $reason; detail = $detail; time = (Get-Date).ToString('o'); launcher_pid = $PID }))
    Note ('LAUNCH_STOPPED reason=' + $reason + ' detail=' + $detail)
  }
}
function Test-StopFiles {
  foreach ($sf in @('STOP_FO_LAUNCHER', 'STOP')) { $p = Join-Path $Root $sf; if (Test-Path -LiteralPath $p) { return $p } }
  return ''
}
function Save-Owned([string]$key, [int]$wpid, [int]$vpid) {
  if ($script:LMODE -ne 'run') { return }
  $all = @(Get-CimInstance Win32_Process)
  $byParent = @{}
  foreach ($p in $all) { $pp = [int]$p.ParentProcessId; if (-not $byParent.ContainsKey($pp)) { $byParent[$pp] = New-Object System.Collections.ArrayList }; [void]$byParent[$pp].Add($p) }
  $list = New-Object System.Collections.ArrayList
  $q = New-Object System.Collections.Queue
  foreach ($p in $all) { if ([int]$p.ProcessId -eq $wpid) { $q.Enqueue($p) } }
  while ($q.Count) {
    $p = $q.Dequeue(); [void]$list.Add($p)
    if ($byParent.ContainsKey([int]$p.ProcessId)) { foreach ($c in $byParent[[int]$p.ProcessId]) { if ($c.CreationDate -ge $p.CreationDate) { $q.Enqueue($c) } } }
  }
  if ($vpid) { foreach ($p in $all) { if ([int]$p.ProcessId -eq $vpid) { [void]$list.Add($p) } } }
  $rows = @()
  foreach ($p in $list) {
    $cl = [string]$p.CommandLine; if ($cl.Length -gt 400) { $cl = $cl.Substring(0, 400) }
    $rows += [ordered]@{ pid = [int]$p.ProcessId; parent = [int]$p.ParentProcessId; name = [string]$p.Name; creation = $p.CreationDate.ToString('o');
      creation_ticks = [string]$p.CreationDate.ToUniversalTime().Ticks; command = $cl }
  }
  Save-Json (Join-Path $LD ('owned_' + $key + '.json')) ([ordered]@{ key = $key; time = (Get-Date).ToString('o'); wrapper_pid = $wpid; vissim_pid = $vpid; processes = $rows })
}
function Start-Try([int]$seed, [int]$attempt, [int]$try, $vis, [int]$pending, $disk) {
  $key = Get-Key $seed $attempt $try
  $res = Join-Path $Root ('s' + $seed)
  $tmode = 'run{0}_try{1}' -f $attempt, $try
  $marker = Join-Path $LD ('launched_' + $key + '.json')
  $visPids = @($vis | ForEach-Object { [int]$_.ProcessId })
  $mk = [ordered]@{ key = $key; seed = $seed; attempt = $attempt; try = $try; time = (Get-Date).ToString('o'); launcher_pid = $PID; mode = $script:LMODE;
    vissim_count_before = $visPids.Count; vissim_pids_before = $visPids; pending_before = $pending; disk_free_gb = $disk }
  if (-not (New-Marker $marker $mk)) { Note ('MARKER_EXISTS ' + $key + ' no launch'); return ('MARKER_EXISTS ' + $key) }
  New-Item -ItemType Directory -Force -Path (Join-Path $res 'fo_launch') | Out-Null
  $cmd = '"' + $PWSH + '" -NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + $WRAPPER + '" -Seed ' + $seed + ' -Attempt ' + $attempt + ' -Try ' + $try
  $before = (Get-Date).ToString('o'); $rv = -1; $wpid = 0; $ticks = ''; $created = ''
  if ($script:LMODE -eq 'run') {
    $startup = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ PriorityClass = [uint32]32; ShowWindow = [uint16]0 }
    $r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = $FRZ; ProcessStartupInformation = $startup }
    $rv = [int]$r.ReturnValue; $wpid = [int]$r.ProcessId
    try { $p = Get-CimInstance Win32_Process -Filter ('ProcessId=' + $wpid) -ErrorAction SilentlyContinue
      if ($p) { $ticks = [string]$p.CreationDate.ToUniversalTime().Ticks; $created = $p.CreationDate.ToString('o') } } catch {}
  } else {
    $rv = 0; $wpid = 900000 + $seed * 100 + $attempt * 10 + $try
    $oc = 'up'; if ($script:sc.outcomes -and $script:sc.outcomes.$key) { $oc = [string]$script:sc.outcomes.$key }
    $sd = Join-Path $res 'sdmpc'; $bl = Join-Path $res 'fo_launch'
    if ($oc -eq 'up') { New-Item -ItemType Directory -Force -Path $sd | Out-Null
      [IO.File]::AppendAllText((Join-Path $sd 'WATCHDOG_PROGRESS.txt'), ('10-26 00:00:00  VISSIM_PROCESS ' + (Get-Name $seed) + ' pid=' + (60000 + $seed * 10 + $try) + "`r`n"), $UTF8) }
    if ($oc -eq 'refused') {
      Save-Json (Join-Path $bl ('native_status_' + $tmode + '.json')) ([ordered]@{ stage = 'failed'; arm = ''; details = 'PC-wide VISSIM count is at the 4-seat cap; preserve them and do not launch' })
      Save-Json (Join-Path $bl ('wrapper_' + $tmode + '_end.json')) ([ordered]@{ runner_exit = 1; wall_sec = 120.0 }) }
    if ($oc -eq 'fail') {
      New-Item -ItemType Directory -Force -Path $sd | Out-Null; [IO.File]::WriteAllText((Join-Path $sd 'launch.log'), 'FAIL', $UTF8)
      Save-Json (Join-Path $bl ('native_status_' + $tmode + '.json')) ([ordered]@{ stage = 'failed'; arm = ''; details = 'Watchdog failed: launch.log' })
      Save-Json (Join-Path $bl ('wrapper_' + $tmode + '_end.json')) ([ordered]@{ runner_exit = 1; wall_sec = 300.0 }) }
  }
  $rc = [ordered]@{ key = $key; seed = $seed; attempt = $attempt; try = $try; time_before_create = $before; time_after_create = (Get-Date).ToString('o');
    ReturnValue = $rv; ProcessId = $wpid; wrapper_creation = $created; wrapper_creation_ticks = $ticks; CommandLine = $cmd; CurrentDirectory = $FRZ;
    PriorityClass = 32; launcher_pid = $PID; launcher_sha256 = $SELF_SHA; wrapper_sha256 = $FIXED[$WRAPPER]; mode = $script:LMODE;
    vissim_count_before = $visPids.Count; vissim_pids_before = $visPids; pending_before = $pending; disk_free_gb = $disk }
  Save-Json (Join-Path $LD ('receipt_' + $key + '.json')) $rc
  Save-Json (Join-Path $res ('fo_launch\wmi_launch_' + $tmode + '.json')) $rc
  $line = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' KST seed=' + $seed + ' attempt=' + $attempt + ' try=' + $try + ' ReturnValue=' + $rv + ' ProcessId=' + $wpid +
    ' Priority=32 vissim_before=' + $visPids.Count + ' pending_before=' + $pending + ' mode=' + $script:LMODE + ' Command=' + $cmd
  [IO.File]::AppendAllText((Join-Path $Root 'wmi_launch_lines.txt'), $line + "`r`n", $UTF8)
  Note ('LAUNCHED ' + $key + ' ReturnValue=' + $rv + ' wrapper_pid=' + $wpid + ' vissim_before=' + $visPids.Count + ' pending_before=' + $pending)
  if ($rv -ne 0) { return ('LAUNCH_FAILED ' + $key + ' rv=' + $rv) }
  $t = [pscustomobject]@{ seed = $seed; attempt = $attempt; try = $try; key = $key }
  $rco = Read-Json (Join-Path $LD ('receipt_' + $key + '.json'))
  $t0 = Get-Date; $up = 0; $why = 'timeout'
  while (((Get-Date) - $t0).TotalSeconds -lt $VissimUpWaitSec) {
    $up = Get-RunVissimPid $res $seed
    if ($up) { $why = 'vissim_process'; break }
    if (-not (Test-WrapperAlive $t $rco)) { $why = 'run_ended'; break }
    if ($script:LMODE -eq 'run') { Start-Sleep -Seconds 5 } else { Start-Sleep -Seconds 1 }
  }
  $sec = [int]((Get-Date) - $t0).TotalSeconds
  Note ('VISSIM_WAIT_END ' + $key + ' reason=' + $why + ' vissim_pid=' + $up + ' after=' + $sec + 's')
  try { Save-Owned $key $wpid $up } catch { Note ('OWNED_SNAPSHOT_ERROR ' + $key + ' ' + [string]$_) }
  return ('LAUNCHED ' + $key + ' wrapper_pid=' + $wpid + ' wait=' + $why + ' vissim_pid=' + $up)
}

# ---------------- start ----------------
if ($script:LMODE -eq 'dryrun') { $script:sc = Get-Content -LiteralPath $Scenario -Raw -Encoding UTF8 | ConvertFrom-Json }
$inst = Open-Lock (Join-Path $LD 'instance.lock')
if (-not $inst) { Note 'INSTANCE_LOCKED another launcher holds the instance lock; exit 2'; exit 2 }
$fsPath = Join-Path $LD 'first_start.json'
if (-not (Test-Path -LiteralPath $fsPath)) {
  [void](New-Marker $fsPath ([ordered]@{ time = (Get-Date).ToString('o'); start_ticks = [string](Get-Date).ToUniversalTime().Ticks; launcher_pid = $PID; launcher_sha256 = $SELF_SHA; mode = $script:LMODE }))
}
Note ('LAUNCHER_START root=' + $Root + ' self_sha=' + $SELF_SHA + ' wrapper_sha=' + $FIXED[$WRAPPER] + ' poll=' + $PollSec + 's upwait=' + $VissimUpWaitSec +
  's seatwait=' + $SeatWaitHours + 'h giveup=' + $GiveUpHours + 'h first_start=' + (Read-Json $fsPath).time + ' stop=' + (Get-StopReason) + ' ps=' + $PSVersionTable.PSVersion.ToString() +
  ' pre=' + $PreSha + ' rule=' + $RuleSha + ' pins=' + $PinsSha + ' gate=' + $GateSha)
# FO addition (PRE_FO s5): no launch unless the T=900 gate summary says pass = true (its sha is in FIXED as well)
$gj = Read-Json $GATE_PATH
if (-not $gj -or $gj.pass -ne $true) { Set-Stop 'GATE_NOT_PASSED' ('gate summary pass is not true: ' + $GATE_PATH) }
$bad0 = Test-Fixed; if ($bad0) { Set-Stop 'SHA_MISMATCH' $bad0 }
$poll = 0; $errors = 0
while ($true) {
  $poll++
  $sleep = $PollSec
  $exitNow = $false
  try {
    if ($script:LMODE -eq 'dryrun') { if (-not (Apply-Step)) { Note 'DRYRUN_END steps exhausted'; break } }
    $nowTicks = (Get-Date).ToUniversalTime().Ticks
    $fsTicks = [int64](Read-Json $fsPath).start_ticks
    $elapsedH = [math]::Round(($nowTicks - $fsTicks) / [double][TimeSpan]::TicksPerHour, 3)
    $sf = Test-StopFiles; if ($sf) { Set-Stop 'STOP_FILE' $sf }
    $states = @{}
    foreach ($s in $SEEDS) { $states[$s] = Get-SeedState $s }
    foreach ($s in $SEEDS) {
      if ($states[$s].abnormal) { Set-Stop 'ABNORMAL_END' ('s' + $s + ' ' + $states[$s].abnormal) }
      if ($states[$s].stopref) { Set-Stop 'STOP_FILE' ('runner refused with STOP exists: ' + $states[$s].stopref) }
    }
    $activeAll = @(); foreach ($s in $SEEDS) { $activeAll += @($states[$s].active | Where-Object { $_ }) }
    $vis = @(Get-VissimProcs)
    $pending = Get-Pending $states
    $disk = Get-Disk
    if ($disk.C -lt 8 -or $disk.D -lt 8) { Set-Stop 'DISK_LOW' ('C=' + $disk.C + ' D=' + $disk.D) }
    $action = 'none'
    if (-not (Get-StopReason)) {
      $cand = $null
      foreach ($s in $SEEDS) { if ($states[$s].need) { $cand = $states[$s]; break } }
      if (-not $cand) { $action = 'nothing_to_launch' }
      else {
        $na = [int]$cand.need.attempt; $nt = [int]$cand.need.try; $nkey = Get-Key $cand.seed $na $nt
        $deadline = $fsTicks + [int64]($SeatWaitHours * [TimeSpan]::TicksPerHour)
        if ($na -eq 2) {
          $stf = Get-Item -LiteralPath (Join-Path $LD ('stalled_s{0}_run1.json' -f $cand.seed))
          $deadline = $stf.LastWriteTime.ToUniversalTime().Ticks + [int64]($SeatWaitHours * [TimeSpan]::TicksPerHour)
        }
        if ($nowTicks -gt $deadline) { Set-Stop 'SEAT_WAIT_LIMIT' ($nkey + ' not launched within ' + $SeatWaitHours + ' h'); $action = 'SEAT_WAIT_LIMIT ' + $nkey }
        elseif ($nt -gt $MAX_TRY) { Set-Stop 'TRY_LIMIT' ($nkey + ' exceeds ' + $MAX_TRY + ' tries'); $action = 'TRY_LIMIT ' + $nkey }
        elseif (($vis.Count + $pending) -ge $CAP) { $action = 'SEAT_BUSY ' + $nkey + ' (vissim=' + $vis.Count + ' pending=' + $pending + ')' }
        else {
          $lk = Open-Lock (Join-Path $LD 'launch.lock')
          if (-not $lk) { $action = 'LOCK_BUSY ' + $nkey }
          else {
            try {
              $sf = Test-StopFiles
              $bad = ''; if (-not $sf) { $bad = Test-Fixed }
              $disk2 = Get-Disk
              $vis2 = @(Get-VissimProcs -Recount)
              if ($sf) { Set-Stop 'STOP_FILE' $sf; $action = 'STOP_FILE' }
              elseif ($bad) { Set-Stop 'SHA_MISMATCH' $bad; $action = 'SHA_MISMATCH' }
              elseif ($disk2.C -lt 8 -or $disk2.D -lt (8 * ($activeAll.Count + 1))) { Set-Stop 'DISK_LOW' ('C=' + $disk2.C + ' D=' + $disk2.D + ' need D>=' + (8 * ($activeAll.Count + 1))); $action = 'DISK_LOW' }
              elseif (($vis2.Count + $pending) -ge $CAP) { $action = 'SEAT_BUSY_RECOUNT ' + $nkey + ' (vissim=' + $vis2.Count + ' pending=' + $pending + ')' }
              else {
                $action = Start-Try $cand.seed $na $nt $vis2 $pending $disk2
                if ($action -like 'LAUNCHED*') { $sleep = [math]::Min($PollSec, 10) }
              }
            } finally { $lk.Dispose() }
          }
        }
      }
    }
    $ourV = @{}; foreach ($a in $activeAll) { if ($a.vissim_pid) { $ourV[[int]$a.vissim_pid] = 's' + $a.seed } }
    $vtxt = @($vis | ForEach-Object { $id = [int]$_.ProcessId; if ($ourV.ContainsKey($id)) { [string]$id + ':' + $ourV[$id] } else { [string]$id } }) -join ','
    $seedTxt = @($SEEDS | ForEach-Object { 's' + $_ + '=' + $states[$_].label }) -join ' '
    $stop = Get-StopReason; if (-not $stop) { $stop = '-' }
    Note ('POLL n=' + $poll + ' vissim=' + $vis.Count + ' [' + $vtxt + '] pending=' + $pending + ' disk=C' + $disk.C + ',D' + $disk.D + ' elapsed_h=' + $elapsedH + ' ' + $seedTxt + ' stop=' + $stop + ' action=' + $action)
    $seedRows = @()
    foreach ($s in $SEEDS) {
      $st = $states[$s]
      $seedRows += [ordered]@{ seed = $s; label = $st.label; need = $st.need; abnormal = $st.abnormal; done = $st.done;
        tries = @($st.tries | ForEach-Object { [ordered]@{ key = $_.key; status = $_.status; res = $_.res; vissim_pid = $_.vissim_pid } }) }
    }
    Save-Json (Join-Path $LD 'STATE.json') ([ordered]@{ time = (Get-Date).ToString('o'); poll = $poll; mode = $script:LMODE; launcher_pid = $PID; launcher_sha256 = $SELF_SHA;
      elapsed_h = $elapsedH; vissim_count = $vis.Count; vissim = $vtxt; pending = $pending; disk = $disk; stop = $stop; action = $action; seeds = $seedRows })
    # exit checks (recount actives after a possible launch)
    $anyActive = $false
    foreach ($s in $SEEDS) { foreach ($t in @(Get-Tries $s)) { if ((Get-TryStatus $t) -eq 'active') { $anyActive = $true } } }
    $allEnded = $true
    foreach ($s in $SEEDS) { $st = Get-SeedState $s; if (-not ($st.done -or $st.abnormal)) { $allEnded = $false } }
    if (-not $anyActive -and $allEnded) { Note 'LAUNCHER_EXIT all seeds ended'; $exitNow = $true }
    elseif (-not $anyActive -and (Get-StopReason)) { Note ('LAUNCHER_EXIT launching stopped (' + (Get-StopReason) + ') and no active run'); $exitNow = $true }
    elseif ($elapsedH -ge $GiveUpHours) { Note ('GIVE_UP elapsed_h=' + $elapsedH + ' >= ' + $GiveUpHours); $exitNow = $true }
    $errors = 0
  } catch {
    $errors++
    Note ('ERROR poll=' + $poll + ' line=' + $_.InvocationInfo.ScriptLineNumber + ' ' + [string]$_)
    if ($errors -ge 20) { Note 'TOO_MANY_ERRORS exit'; $exitNow = $true }
  }
  if ($exitNow) { break }
  if ($sleep -gt 0) { Start-Sleep -Seconds $sleep }
}
$inst.Dispose()
exit 0
