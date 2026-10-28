# FO stall monitor action (2026-10-27 KST, PRE_FO s7; user policy: a run with no progress for 5 minutes beyond normal is
# stopped - only its own PIDs - and relaunched once). Windows PowerShell 5.1, ASCII only. Never stops a process by name.
#   1. The seed's last launched try must be active (launcher marker + receipt, no tryend record).
#   2. Idle = age of the newest declared progress signal (run log, state CSV, action CSV, WATCHDOG_PROGRESS.txt, newest
#      action_*.json, newest action_*.joint.progress.jsonl; before the run log exists: fo_launch records and launch.log).
#      Idle <= -IdleLimit (499 s = normal maximum gap 199 s + 300 s) -> NOT_IDLE, nothing else.
#   3. CPU check: the run's own process tree = the wrapper PID of the receipt (PID + creation ticks must match) and its
#      descendants (child created after its parent), plus the VISSIM PID the watchdog wrote (name ^Vissim, listed with the
#      same creation ticks in owned_<key>.json). CPU seconds summed twice, -CpuWaitSec (120 s) apart. Increase > 1 s ->
#      SLOW_BUT_PROGRESSING, nothing stopped.
#   4. -Action check stops here (STALLED_CHECK_ONLY). -Action stop: writes _launcher/stalled_s<seed>_run<A>.json (create-new),
#      stops exactly those PIDs (deepest first), waits until they are gone, and for run 1 renames <root>/s<seed> to
#      <root>/s<seed>_try1_stalled (the launcher then launches run 2 once). A stall of run 2 is recorded the same way (no
#      rename); the launcher treats it as abnormal (stalled_again) and launches nothing more.
#   -Fake <json>: dry run only (root under fo\dryrun): idle_sec, cpu1, cpu2 come from the file; no process is read or stopped.
# usage: powershell -NoProfile -ExecutionPolicy Bypass -File fo_stall_stop.ps1 -Seed 31 [-Action check|stop] [-Root <root>]
param([Parameter(Mandatory = $true)][ValidateSet(31, 41, 43)][int]$Seed,
      [ValidateSet('check', 'stop')][string]$Action = 'check',
      [string]$Root = 'D:\VISSIM_runs\20261028_codex_fo_v3c3',
      [int]$IdleLimit = 499, [int]$CpuWaitSec = 120, [double]$CpuMinSec = 1.0, [string]$Fake = '')
$ErrorActionPreference = 'Stop'
$SPF = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\fo'
$UTF8 = New-Object System.Text.UTF8Encoding $false
$Root = [IO.Path]::GetFullPath($Root).TrimEnd('\')
$fk = $null
if ($Fake) {
  if (-not $Root.StartsWith((Join-Path $SPF 'dryrun') + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'fake mode root must be under fo\dryrun' }
  $fk = Get-Content -LiteralPath $Fake -Raw -Encoding UTF8 | ConvertFrom-Json
  $LOG = Join-Path $Root 'fo_stall_stop.log'
} else {
  if ($Root -ne 'D:\VISSIM_runs\20261028_codex_fo_v3c3') { throw 'real mode root must be the FO results root' }
  $LOG = Join-Path $SPF 'fo_stall_stop.log'
}
function Note([string]$m) { [IO.File]::AppendAllText($LOG, ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' KST [s' + $Seed + ' ' + $Action + '] ' + $m + "`r`n"), $UTF8) }
function Read-Json([string]$p) { if (-not (Test-Path -LiteralPath $p)) { return $null }; try { return (Get-Content -LiteralPath $p -Raw -Encoding UTF8 | ConvertFrom-Json) } catch { return $null } }
function Read-Text([string]$p) {
  if (-not (Test-Path -LiteralPath $p)) { return '' }
  $fs = $null
  try { $fs = [IO.File]::Open($p, [IO.FileMode]::Open, [IO.FileAccess]::Read, ([IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete)); $sr = New-Object IO.StreamReader($fs, $UTF8, $true); return $sr.ReadToEnd() }
  catch { return '' } finally { if ($fs) { $fs.Dispose() } }
}
$LD = Join-Path $Root '_launcher'
$name = 'sdmpc31_sdmpc9000_s' + $Seed
# 1. active try
$tries = @(Get-ChildItem -LiteralPath $LD -Filter ('launched_s{0}_run*_try*.json' -f $Seed) -ErrorAction SilentlyContinue | ForEach-Object {
  $m = [regex]::Match($_.Name, '^launched_s\d+_run(\d+)_try(\d+)\.json$'); if ($m.Success) { [pscustomobject]@{ a = [int]$m.Groups[1].Value; t = [int]$m.Groups[2].Value } } } | Sort-Object a, t)
if (-not $tries.Count) { Note 'NO_TRY launched marker missing'; 'NO_TRY'; exit 0 }
$last = $tries[$tries.Count - 1]
$key = 's{0}_run{1}_try{2}' -f $Seed, $last.a, $last.t
if (Test-Path -LiteralPath (Join-Path $LD ('tryend_' + $key + '.json'))) { Note ('NOT_ACTIVE ' + $key + ' has a tryend record'); 'NOT_ACTIVE'; exit 0 }
$rc = Read-Json (Join-Path $LD ('receipt_' + $key + '.json'))
if (-not $rc) { Note ('NO_RECEIPT ' + $key); 'NO_RECEIPT'; exit 0 }
$res = Join-Path $Root ('s' + $Seed)
$sd = Join-Path $res 'sdmpc'; $dec = Join-Path $sd ('decisions_' + $name); $bl = Join-Path $res 'fo_launch'
# 2. idle
if ($fk) { $idle = [int]$fk.idle_sec } else {
  $sig = @()
  $rlp = Join-Path $sd ('runlog_' + $name + '.txt')
  foreach ($p in @($rlp, (Join-Path $sd ('state_' + $name + '.csv')), (Join-Path $sd ('action_' + $name + '.csv')), (Join-Path $sd 'WATCHDOG_PROGRESS.txt'))) { $i = Get-Item -LiteralPath $p -ErrorAction SilentlyContinue; if ($i) { $sig += $i } }
  $sig += Get-ChildItem -Path (Join-Path $dec 'action_*.json') -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  $sig += Get-ChildItem -Path (Join-Path $dec 'action_*.joint.progress.jsonl') -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if (-not (Test-Path -LiteralPath $rlp)) {
    $sig += Get-ChildItem -Path (Join-Path $bl '*') -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    $i = Get-Item -LiteralPath (Join-Path $sd 'launch.log') -ErrorAction SilentlyContinue; if ($i) { $sig += $i }
  }
  $newest = $sig | Where-Object { $_ } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  $idle = -1; if ($newest) { $idle = [int]((Get-Date) - $newest.LastWriteTime).TotalSeconds }
}
if ($idle -le $IdleLimit) { Note ('NOT_IDLE ' + $key + ' idle=' + $idle + 's <= ' + $IdleLimit); 'NOT_IDLE'; exit 0 }
# 3. own process tree + CPU
function Get-Own {
  if ($fk) { return @{ pids = @($fk.pids); cpu = 0.0 } }
  $all = @(Get-CimInstance Win32_Process)
  $byPid = @{}; $byParent = @{}
  foreach ($p in $all) { $byPid[[int]$p.ProcessId] = $p; $pp = [int]$p.ParentProcessId; if (-not $byParent.ContainsKey($pp)) { $byParent[$pp] = New-Object System.Collections.ArrayList }; [void]$byParent[$pp].Add($p) }
  $list = New-Object System.Collections.ArrayList
  $w = $byPid[[int]$rc.ProcessId]
  if ($w -and [string]$w.CreationDate.ToUniversalTime().Ticks -eq [string]$rc.wrapper_creation_ticks -and [string]$w.CommandLine -like '*fo_wrapper.ps1*') {
    $q = New-Object System.Collections.Queue; $q.Enqueue($w)
    while ($q.Count) { $p = $q.Dequeue(); [void]$list.Add($p)
      if ($byParent.ContainsKey([int]$p.ProcessId)) { foreach ($c in $byParent[[int]$p.ProcessId]) { if ($c.CreationDate -ge $p.CreationDate) { $q.Enqueue($c) } } } }
  }
  $own = Read-Json (Join-Path $LD ('owned_' + $key + '.json'))
  $vm = [regex]::Matches((Read-Text (Join-Path $sd 'WATCHDOG_PROGRESS.txt')), ('VISSIM_PROCESS ' + $name + ' pid=(\d+)'))
  if ($vm.Count -and $own) {
    $vp = [int]$vm[$vm.Count - 1].Groups[1].Value
    $rec = @($own.processes | Where-Object { [int]$_.pid -eq $vp })
    if ($byPid.ContainsKey($vp) -and $byPid[$vp].Name -match '^Vissim' -and $rec.Count -and [string]$rec[0].creation_ticks -eq [string]$byPid[$vp].CreationDate.ToUniversalTime().Ticks) { [void]$list.Add($byPid[$vp]) }
  }
  $cpu = 0.0; foreach ($p in $list) { $cpu += ([double]$p.KernelModeTime + [double]$p.UserModeTime) / 1e7 }
  return @{ pids = @($list | ForEach-Object { [int]$_.ProcessId }); cpu = $cpu; procs = $list }
}
$o1 = Get-Own
if ($fk) { $c1 = [double]$fk.cpu1 } else { $c1 = $o1.cpu; Start-Sleep -Seconds $CpuWaitSec }
$o2 = Get-Own
if ($fk) { $c2 = [double]$fk.cpu2 } else { $c2 = $o2.cpu }
$dcpu = [math]::Round($c2 - $c1, 2)
if ($dcpu -gt $CpuMinSec) { Note ('SLOW_BUT_PROGRESSING ' + $key + ' idle=' + $idle + 's cpu_increase=' + $dcpu + 's pids=' + ($o2.pids -join ',')); 'SLOW_BUT_PROGRESSING'; exit 0 }
if ($Action -eq 'check') { Note ('STALLED_CHECK_ONLY ' + $key + ' idle=' + $idle + 's cpu_increase=' + $dcpu + 's pids=' + ($o2.pids -join ',')); 'STALLED_CHECK_ONLY'; exit 0 }
# 4. stop own PIDs, record, rename
$mk = Join-Path $LD ('stalled_s{0}_run{1}.json' -f $Seed, $last.a)
$body = ([ordered]@{ key = $key; seed = $Seed; attempt = $last.a; idle_sec = $idle; cpu_increase_sec = $dcpu; cpu_wait_sec = $CpuWaitSec;
  pids = $o2.pids; fake = [bool]$fk; time = (Get-Date).ToString('o'); by = 'fo_stall_stop.ps1' } | ConvertTo-Json -Depth 5)
$fs = $null
try { $fs = [IO.File]::Open($mk, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None); $b = $UTF8.GetBytes($body); $fs.Write($b, 0, $b.Length) }
catch { Note ('STALL_RECORD_EXISTS ' + $mk + ' no second stop'); 'STALL_RECORD_EXISTS'; exit 0 } finally { if ($fs) { $fs.Dispose() } }
Note ('STALLED ' + $key + ' idle=' + $idle + 's cpu_increase=' + $dcpu + 's record=' + $mk)
if ($fk) { Note ('FAKE would stop pids=' + ($o2.pids -join ',')) } else {
  foreach ($p in @($o2.procs | Sort-Object CreationDate -Descending)) {
    try { Stop-Process -Id ([int]$p.ProcessId) -Force -ErrorAction Stop; Note ('stopped pid=' + $p.ProcessId + ' ' + $p.Name) } catch { Note ('stop failed pid=' + $p.ProcessId + ' ' + [string]$_) }
  }
  for ($k = 0; $k -lt 60; $k++) { $alive = @($o2.pids | Where-Object { Get-Process -Id $_ -ErrorAction SilentlyContinue }); if (-not $alive.Count) { break }; Start-Sleep -Seconds 1 }
  Note ('alive after stop: ' + (@($o2.pids | Where-Object { Get-Process -Id $_ -ErrorAction SilentlyContinue }) -join ','))
}
if ($last.a -eq 1) {
  Move-Item -LiteralPath $res -Destination ($res + '_try1_stalled')
  Note ('RENAMED ' + $res + ' -> ' + $res + '_try1_stalled; the launcher relaunches run 2 once')
} else { Note 'run 2 stalled: no rename; the launcher records stalled_again (abnormal) and launches nothing more' }
'STOPPED'
exit 0
