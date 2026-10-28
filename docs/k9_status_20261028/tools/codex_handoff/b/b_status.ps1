# B run status (2026-10-26). Read-only: writes nothing, starts nothing, stops nothing. Windows PowerShell 5.1, ASCII only.
# Reads the launcher records (<root>/_launcher: launched_*, receipt_*, tryend_*, owned_*, STATE.json, LAUNCH_STOPPED.json,
# stalled_*), the launcher log, and each seed's results root (b_launch wrapper records, native_status.json, sdmpc/ run log,
# state/action CSV, decisions folder, WATCHDOG_PROGRESS.txt, launch.log).
# Per seed: launched? (tries and their status), wrapper alive, VISSIM pid alive, sim_sec (last state CSV row), decisions
# (count, last T / wall / exit, non-zero exits, max wall), decision in progress (T, progress lines, age), holds
# (DECISION_HOLD_ATTEMPT / DECISION_HELD_PREVIOUS with T), last progress age over the declared progress signals
# (LOG 2026-10-26 11:58; IDLE flag when > -IdleLimit = 499 s, PRE_B_CONCURRENT s7-1), CPU seconds of the run's process tree
# (wrapper and descendants + its VISSIM; for the s7-2 check run this twice 120 s apart), runner exit, SIM_DONE / SIM_SEC.
# usage: powershell -NoProfile -ExecutionPolicy Bypass -File b_status.ps1 [-Root <root>] [-IdleLimit 499]
param([string]$Root = 'D:\VISSIM_runs\20261026_codex_b_v3c3', [int]$IdleLimit = 499,
      [string]$LauncherLog = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\b\b_launcher.log')
$ErrorActionPreference = 'Continue'
$UTF8 = New-Object System.Text.UTF8Encoding $false
$SEEDS = @(31, 41, 43)
$LD = Join-Path $Root '_launcher'
$now = Get-Date
function Read-Json([string]$path) {
  if (-not (Test-Path -LiteralPath $path)) { return $null }
  try { return (Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json) } catch { return $null }
}
function Read-Text([string]$path) {
  if (-not (Test-Path -LiteralPath $path)) { return '' }
  $fs = $null
  try {
    $fs = [IO.File]::Open($path, [IO.FileMode]::Open, [IO.FileAccess]::Read, ([IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete))
    $sr = New-Object IO.StreamReader($fs, $UTF8, $true); return $sr.ReadToEnd()
  } catch { return '' } finally { if ($fs) { $fs.Dispose() } }
}
function Read-LastLine([string]$path) {
  if (-not (Test-Path -LiteralPath $path)) { return '' }
  $fs = $null
  try {
    $fs = [IO.File]::Open($path, [IO.FileMode]::Open, [IO.FileAccess]::Read, ([IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete))
    $n = [Math]::Min([int64]8192, $fs.Length); [void]$fs.Seek(-$n, [IO.SeekOrigin]::End)
    $buf = New-Object byte[] $n; [void]$fs.Read($buf, 0, $n)
    $lines = @($UTF8.GetString($buf) -split "`r?`n" | Where-Object { $_.Trim() -ne '' })
    if ($lines.Count) { return $lines[$lines.Count - 1] } else { return '' }
  } catch { return '' } finally { if ($fs) { $fs.Dispose() } }
}
function Age($item) { if ($item) { return [int]($now - $item.LastWriteTime).TotalSeconds } else { return -1 } }

$procs = @(Get-CimInstance Win32_Process)
$byPid = @{}; $byParent = @{}
foreach ($p in $procs) { $byPid[[int]$p.ProcessId] = $p; $pp = [int]$p.ParentProcessId; if (-not $byParent.ContainsKey($pp)) { $byParent[$pp] = New-Object System.Collections.ArrayList }; [void]$byParent[$pp].Add($p) }
function Get-Tree([int]$rootPid) {
  $list = New-Object System.Collections.ArrayList
  if (-not $byPid.ContainsKey($rootPid)) { return @() }
  $q = New-Object System.Collections.Queue; $q.Enqueue($byPid[$rootPid])
  while ($q.Count) { $p = $q.Dequeue(); [void]$list.Add($p)
    if ($byParent.ContainsKey([int]$p.ProcessId)) { foreach ($c in $byParent[[int]$p.ProcessId]) { if ($c.CreationDate -ge $p.CreationDate) { $q.Enqueue($c) } } } }
  return @($list)
}
function Cpu($p) { if (-not $p) { return 0.0 }; return ([double]$p.KernelModeTime + [double]$p.UserModeTime) / 1e7 }

# ---------------- header ----------------
$vis = @($procs | Where-Object { $_.Name -match '^Vissim' })
$ours = @{}
$out = New-Object System.Collections.ArrayList
$launchers = @($procs | Where-Object { $_.Name -match '^powershell' -and [string]$_.CommandLine -like '*b_launcher.ps1*' -and [string]$_.CommandLine -notlike '*dryrun*' })
$lastLog = Read-LastLine $LauncherLog
$logAge = Age (Get-Item -LiteralPath $LauncherLog -ErrorAction SilentlyContinue)
$state = Read-Json (Join-Path $LD 'STATE.json')
$stop = Read-Json (Join-Path $LD 'LAUNCH_STOPPED.json')
$stopFiles = @(@('STOP_B_LAUNCHER', 'STOP') | Where-Object { Test-Path -LiteralPath (Join-Path $Root $_) })
$c = [math]::Round((Get-PSDrive C).Free / 1GB, 1); $d = [math]::Round((Get-PSDrive D).Free / 1GB, 1)
[void]$out.Add(('B_STATUS ' + $now.ToString('yyyy-MM-dd HH:mm:ss') + ' KST root=' + $Root + ' root_exists=' + (Test-Path -LiteralPath $Root)))
[void]$out.Add(('launcher processes=[' + (@($launchers | ForEach-Object { [string]$_.ProcessId + '@' + $_.CreationDate.ToString('MM-dd HH:mm:ss') }) -join ',') + '] log_age=' + $logAge + 's'))
[void]$out.Add(('launcher last log: ' + $lastLog))
if ($state) { [void]$out.Add(('launcher STATE poll=' + $state.poll + ' time=' + $state.time + ' action=' + $state.action + ' stop=' + $state.stop)) }
[void]$out.Add(('launch stopped=' + $(if ($stop) { $stop.reason + ' (' + $stop.detail + ') at ' + $stop.time } else { 'no' }) + ' stop_files=[' + ($stopFiles -join ',') + ']'))
[void]$out.Add(('disk C=' + $c + ' GB D=' + $d + ' GB' + $(if ($c -lt 8 -or $d -lt 8) { ' DISK_BELOW_8GB' } else { '' })))

# ---------------- seeds ----------------
$seedLines = New-Object System.Collections.ArrayList
foreach ($seed in $SEEDS) {
  $name = 'sdmpc31_sdmpc9000_s' + $seed
  $keys = @(Get-ChildItem -LiteralPath $LD -Filter ('launched_s{0}_run*_try*.json' -f $seed) -ErrorAction SilentlyContinue | ForEach-Object {
    $m = [regex]::Match($_.Name, '^launched_s\d+_run(\d+)_try(\d+)\.json$'); if ($m.Success) { [pscustomobject]@{ a = [int]$m.Groups[1].Value; t = [int]$m.Groups[2].Value; key = ('s{0}_run{1}_try{2}' -f $seed, $m.Groups[1].Value, $m.Groups[2].Value) } } } | Sort-Object a, t)
  if (-not $keys.Count) { [void]$seedLines.Add(('s' + $seed + ' launched=no')); continue }
  $tryTxt = @()
  foreach ($k in $keys) {
    $te = Read-Json (Join-Path $LD ('tryend_' + $k.key + '.json'))
    $rc = Read-Json (Join-Path $LD ('receipt_' + $k.key + '.json'))
    $st = 'live?'
    if ($te) { $st = [string]$te.status }
    elseif ($rc -and $rc.ProcessId -and $byPid.ContainsKey([int]$rc.ProcessId)) {
      $p = $byPid[[int]$rc.ProcessId]
      if ([string]$p.CommandLine -like '*b_wrapper_b1.ps1*' -and (-not $rc.wrapper_creation_ticks -or [string]$p.CreationDate.ToUniversalTime().Ticks -eq [string]$rc.wrapper_creation_ticks)) { $st = 'wrapper_alive' } else { $st = 'wrapper_pid_reused?' }
    } elseif ($rc) { $st = 'wrapper_not_running(no tryend yet)' } else { $st = 'no_receipt' }
    $tryTxt += ($k.key + ':' + $st)
  }
  $last = $keys[$keys.Count - 1]
  $res = Join-Path $Root ('s' + $seed)
  if ($last.a -eq 1 -and (Test-Path -LiteralPath (Join-Path $LD ('stalled_s{0}_run1.json' -f $seed))) -and (Test-Path -LiteralPath ($res + '_try1_stalled'))) { $res = $res + '_try1_stalled' }
  $sd = Join-Path $res 'sdmpc'; $dec = Join-Path $sd ('decisions_' + $name); $bl = Join-Path $res 'b_launch'
  $tm = 'run{0}_try{1}' -f $last.a, $last.t
  $rc = Read-Json (Join-Path $LD ('receipt_' + $last.key + '.json'))
  $wpid = 0; if ($rc) { $wpid = [int]$rc.ProcessId }
  $walive = $false
  if ($wpid -and $byPid.ContainsKey($wpid)) { $p = $byPid[$wpid]; $walive = ([string]$p.CommandLine -like '*b_wrapper_b1.ps1*') -and (-not $rc.wrapper_creation_ticks -or [string]$p.CreationDate.ToUniversalTime().Ticks -eq [string]$rc.wrapper_creation_ticks) }
  $wp = Read-Text (Join-Path $sd 'WATCHDOG_PROGRESS.txt')
  $vm = [regex]::Matches($wp, ('VISSIM_PROCESS ' + $name + ' pid=(\d+)')); $vpid = 0; if ($vm.Count) { $vpid = [int]$vm[$vm.Count - 1].Groups[1].Value }
  $valive = $vpid -and $byPid.ContainsKey($vpid) -and ($byPid[$vpid].Name -match '^Vissim')
  if ($valive) { $ours[$vpid] = 's' + $seed }
  $wdLast = Read-LastLine (Join-Path $sd 'WATCHDOG_PROGRESS.txt')
  # run log
  $rlp = Join-Path $sd ('runlog_' + $name + '.txt'); $rl = Read-Text $rlp
  $nDec = 0; $lastDec = '-'; $nNon = 0; $maxWall = 0.0; $holdAtt = @(); $held = @(); $stage = '-'; $simDone = $false; $simSecLine = '-'
  if ($rl) {
    $ms = [regex]::Matches($rl, '(?m)^CONTROLLER_DECISION sim_sec=(\d+) wall_sec=([0-9.]+) result=exit=(-?\d+)')
    $nDec = $ms.Count
    foreach ($m in $ms) { $w = [double]$m.Groups[2].Value; if ($w -gt $maxWall) { $maxWall = $w }; if ($m.Groups[3].Value -ne '0') { $nNon++ } }
    if ($ms.Count) { $m = $ms[$ms.Count - 1]; $lastDec = 'T=' + $m.Groups[1].Value + ' wall=' + $m.Groups[2].Value + 's exit=' + $m.Groups[3].Value }
    foreach ($m in [regex]::Matches($rl, '(?m)^DECISION_HOLD_ATTEMPT sim_sec=(\d+) cause=(\S+)(?:.*?DECISION_FAILED type=(\S+))?')) { $holdAtt += ($m.Groups[1].Value + ':' + $m.Groups[2].Value + $(if ($m.Groups[3].Value) { ':' + $m.Groups[3].Value } else { '' })) }
    foreach ($m in [regex]::Matches($rl, '(?m)^DECISION_HELD_PREVIOUS sim_sec=(\d+)')) { $held += $m.Groups[1].Value }
    $sm = [regex]::Matches($rl, '(?m)^(STAGE|STARTUP_STAGE)=(.*)$'); if ($sm.Count) { $stage = $sm[$sm.Count - 1].Value.Trim() }
    $simDone = $rl -match '(?m)^STAGE=SIM_DONE\r?$'
    $x = [regex]::Match($rl, '(?m)^SIM_SEC=(\d+)'); if ($x.Success) { $simSecLine = $x.Groups[1].Value }
  }
  $simSec = '-'
  $sl = Read-LastLine (Join-Path $sd ('state_' + $name + '.csv')); if ($sl -match '^([0-9.]+),') { $simSec = $Matches[1] }
  # decision in progress
  $inprog = '-'
  $sj = @(Get-ChildItem -Path (Join-Path $dec 'state_*.json') -ErrorAction SilentlyContinue | Sort-Object Name)
  if ($sj.Count) {
    $lastS = $sj[$sj.Count - 1]; $T = ($lastS.BaseName -replace '^state_', '')
    if (-not (Test-Path -LiteralPath (Join-Path $dec ('action_' + $T + '.csv')))) {
      $pj = Get-Item -LiteralPath (Join-Path $dec ('action_' + $T + '.joint.progress.jsonl')) -ErrorAction SilentlyContinue
      $pl = 0; if ($pj) { $pl = @((Read-Text $pj.FullName) -split "`n" | Where-Object { $_.Trim() }).Count }
      $inprog = 'T=' + [int]$T + ' since=' + (Age $lastS) + 's progress_lines=' + $pl + ' progress_age=' + (Age $pj) + 's'
    }
  }
  # progress signals (declared list) and idle
  $sig = @()
  foreach ($pth in @($rlp, (Join-Path $sd ('state_' + $name + '.csv')), (Join-Path $sd ('action_' + $name + '.csv')), (Join-Path $sd 'WATCHDOG_PROGRESS.txt'))) { $i = Get-Item -LiteralPath $pth -ErrorAction SilentlyContinue; if ($i) { $sig += $i } }
  $sig += Get-ChildItem -Path (Join-Path $dec 'action_*.json') -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  $sig += Get-ChildItem -Path (Join-Path $dec 'action_*.joint.progress.jsonl') -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if (-not (Test-Path -LiteralPath $rlp)) {
    $sig += Get-ChildItem -Path (Join-Path $bl '*') -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    $i = Get-Item -LiteralPath (Join-Path $sd 'launch.log') -ErrorAction SilentlyContinue; if ($i) { $sig += $i }
  }
  $newest = $sig | Where-Object { $_ } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  $idle = Age $newest
  # end records
  $end = Read-Json (Join-Path $bl ('wrapper_' + $tm + '_end.json')); $err = Read-Json (Join-Path $bl ('wrapper_' + $tm + '_error.json'))
  $exitTxt = '-'; if ($end) { $exitTxt = 'runner_exit=' + $end.runner_exit + ' wall=' + $end.wall_sec + 's' } elseif ($err) { $exitTxt = 'wrapper_error' }
  $ns = Read-Json (Join-Path $res 'native_status.json'); $nsTxt = '-'; if ($ns) { $nsTxt = [string]$ns.stage }
  $errLen = -1; $ef = Get-Item -LiteralPath ($rlp + '.err') -ErrorAction SilentlyContinue; if ($ef) { $errLen = $ef.Length }
  # CPU of the run's process tree
  $tree = @(); if ($walive) { $tree = @(Get-Tree $wpid) }
  $cpu = 0.0; foreach ($p in $tree) { $cpu += Cpu $p }; if ($valive) { $cpu += Cpu $byPid[$vpid] }
  $names = @($tree | ForEach-Object { $_.Name -replace '\.exe$', '' } | Group-Object | ForEach-Object { $_.Name + 'x' + $_.Count }) -join ','
  [void]$seedLines.Add(('s' + $seed + ' launched=yes tries=[' + ($tryTxt -join ' ') + '] res=' + (Split-Path -Leaf $res)))
  [void]$seedLines.Add(('    wrapper=' + $wpid + $(if ($walive) { '(alive)' } else { '(not running)' }) + ' vissim=' + $vpid + $(if ($valive) { '(alive)' } elseif ($vpid) { '(gone)' } else { '' }) +
    ' sim_sec=' + $simSec + ' decisions=' + $nDec + ' last=[' + $lastDec + '] nonzero=' + $nNon + ' max_wall=' + $maxWall + 's'))
  [void]$seedLines.Add(('    in_progress=[' + $inprog + '] holds: attempts=' + $holdAtt.Count + ' [' + ($holdAtt -join ',') + '] held_previous=' + $held.Count + ' [' + ($held -join ',') + ']'))
  [void]$seedLines.Add(('    last_progress_age=' + $idle + 's (' + $(if ($newest) { $newest.Name } else { '-' }) + ')' + $(if ($idle -gt $IdleLimit) { ' IDLE_OVER_' + $IdleLimit } else { '' }) +
    ' cpu_tree=' + [math]::Round($cpu, 1) + 's procs=[' + $names + ']'))
  [void]$seedLines.Add(('    stage=[' + $stage + '] sim_done=' + $simDone + ' SIM_SEC=' + $simSecLine + ' exit=[' + $exitTxt + '] native_status=' + $nsTxt + ' runlog_err_bytes=' + $errLen))
  [void]$seedLines.Add(('    watchdog_last=[' + $wdLast + ']'))
}
$vtxt = @($vis | ForEach-Object { $id = [int]$_.ProcessId; if ($ours.ContainsKey($id)) { [string]$id + ':' + $ours[$id] } else { [string]$id + ':other' } }) -join ','
[void]$out.Add(('PC VISSIM count=' + $vis.Count + ' [' + $vtxt + ']'))
foreach ($l in $seedLines) { [void]$out.Add($l) }
$out
