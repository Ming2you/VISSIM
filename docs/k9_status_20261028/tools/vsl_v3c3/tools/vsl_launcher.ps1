# vsl_launcher.ps1 - seat-aware launcher for the three v3c3 fixed VSL-only runs (D-K9-95; PRE_VSL.md section 5).
# Windows PowerShell 5.1, ASCII only. Started detached by WMI (Win32_Process.Create) so it outlives the Claude session.
#
# Per poll (every -PollSec s; one log line per event in -Log):
#   * STOP file <Root>\STOP_VSL_LAUNCHER, a changed fixed file (sha), C: or D: below 8 GB, or an abnormal run end
#     -> launching stops for good (LAUNCH_STOPPED.json, kept across restarts). Running runs are never touched then.
#   * Seeds 31, 41, 43 in this order, attempt 1 each (output <Root>\s<S>\run, log <Root>\s<S>\launch.log).
#   * Seat rule: under an exclusive lock file it counts PC-wide processes named ^VISSIM (ours and others) plus our
#     launched runs whose VISSIM has not shown yet (pending, at most -VissimUpWaitSec after launch) and launches only
#     when count + pending < 4. One launch per poll.
#   * Once-only: before WMI Create it creates _launcher\launched_s<S>_run<A>.json with FileMode.CreateNew; a seed/attempt
#     with a marker is never launched again (also after a launcher restart).
#   * Stall (user policy): fast_nc_run.ps1 itself kills only its own cscript + VISSIM (PID + start time) when the FZP
#     time does not advance for 300 s and writes run.json error Startup300s/Progress300s. Backstop: if progress.csv has
#     not advanced for -StallBackstopSec (600 s) while the run's cmd.exe is still alive, this launcher kills only that
#     run's own cscript and VISSIM (PID + start time from run.json), never by name. A stalled attempt 1 is relaunched
#     once as attempt 2 (output run_retry1, log launch_retry1.log); a stalled attempt 2 is abnormal.
#   * Exit when nothing is active and nothing is left to launch, or after -GiveUpHours. Exit 2 = another instance runs.
#   * -Mode dryrun: no WMI, no kill, no process is started; VISSIM counts, disk, process liveness and run files come from
#     -Scenario (JSON steps); -Root must be under the VS\dryrun folder.
param(
  [ValidateSet('run', 'dryrun')][string]$Mode = 'run',
  [string]$Root = 'D:\VISSIM_runs\20261027_vsl_v3c3',
  [string]$Log = '',
  [string]$Scenario = '',
  [ValidateRange(0, 600)][int]$PollSec = 60,
  [ValidateRange(1, 3600)][int]$VissimUpWaitSec = 600,
  [ValidateRange(301, 7200)][int]$StallBackstopSec = 600,
  [double]$GiveUpHours = 24
)
$ErrorActionPreference = 'Stop'
$script:LMODE = $Mode
$VS = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\vsl_v3c3'
$REAL_ROOT = 'D:\VISSIM_runs\20261027_vsl_v3c3'
$DRY_BASE = Join-Path $VS 'dryrun'
$RUNNER = 'D:\VISSIM-merge\sim3\diagnostics\fast_nc_run.ps1'
$SEEDS = @(31, 41, 43)
$CAP = 4
$MIN_FREE_GB = 8
$UTF8 = New-Object System.Text.UTF8Encoding $false
$FIXED = [ordered]@{}
$FIXED['D:\VISSIM-merge\sim3\diagnostics\fast_nc_run.ps1'] = '269345dade5657a25e224728985a2a32e35fa0e1669404a631591a191fb67136'
$FIXED['D:\VISSIM-merge\sim3\diagnostics\fast_nc_runner.vbs'] = 'bf07acdaaa678d764ccbd0fd237a5aad85c3419f0628790358dd478ffc5e2cf1'
$FIXED['D:\VISSIM-merge\sim3\diagnostics\fast_fixed_profile_verify.py'] = '914413913c41f6e085b840fa8e33bd7eda6dc7bc74cc10f88622d3c64084de7e'
$FIXED['D:\VISSIM-merge\sim3\diagnostics\validate_native_signal_record.py'] = '4a647072d82afdb20cbf0c933b9d947a6a95450b3b84eac41ccff31220f501d3'
$FIXED['D:\VISSIM_runs\20261027_vsl_v3c3\s31\prepared\prepared.json'] = '79eefd753a3f0717e5cad254b120bb3a38ef52ea47979e6dbc0e667d8c91a52a'
$FIXED['D:\VISSIM_runs\20261027_vsl_v3c3\s41\prepared\prepared.json'] = '27ccd7ba91410153d28ca62709bbbeb68d99969f5ca4f9c1d360a53ff2a039ed'
$FIXED['D:\VISSIM_runs\20261027_vsl_v3c3\s43\prepared\prepared.json'] = '36170f2d3fb1852e3002498b80d370bb5ddfe3e8f3fbcb3b30fc6360e76aed45'
$FIXED['D:\VISSIM_runs\20261027_vsl_v3c3\launch_lines_vsl.txt'] = '0456cf45944b5be5752c36434bc49135531e2004989a23dc1fdeb0ecd6a41396'

$Root = [IO.Path]::GetFullPath($Root).TrimEnd('\')
if ($script:LMODE -eq 'run') {
  if ($Root -ne $REAL_ROOT) { throw "run mode root must be $REAL_ROOT" }
  if (-not $Log) { $Log = Join-Path $REAL_ROOT 'vsl_launcher.log' }
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
  for ($r = 0; $r -lt 3; $r++) {
    try { return (Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json) } catch { Start-Sleep -Milliseconds 300 }
  }
  return $null
}
function Open-Lock([string]$path) {
  try { return [IO.File]::Open($path, [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None) } catch { return $null }
}
function Get-OutName([int]$attempt) { if ($attempt -eq 1) { return 'run' } else { return 'run_retry1' } }
function Get-LogName([int]$attempt) { if ($attempt -eq 1) { return 'launch.log' } else { return 'launch_retry1.log' } }
function Get-Key([int]$seed, [int]$attempt) { return ('s{0}_run{1}' -f $seed, $attempt) }
function Get-CmdLine([int]$seed, [int]$attempt) {
  $base = Join-Path $Root ('s' + $seed)
  return ('cmd.exe /c powershell.exe -NoProfile -ExecutionPolicy Bypass -File ' + $RUNNER + ' -Prepared ' + $base + '\prepared -Output ' +
          $base + '\' + (Get-OutName $attempt) + ' -Execute -MinimumFreeGiB 8 -AllowConcurrent > ' + $base + '\' + (Get-LogName $attempt) + ' 2>&1')
}
function Test-Fixed {
  if ($script:LMODE -eq 'dryrun') { if ($script:simShaBad) { return 'dryrun simulated sha change' } else { return '' } }
  foreach ($p in $FIXED.Keys) {
    if (-not (Test-Path -LiteralPath $p)) { return ('missing ' + $p) }
    $h = (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($h -ne $FIXED[$p]) { return ($p + ' ' + $h) }
  }
  return ''
}

# ---------------- dry-run simulation ----------------
$script:sc = $null; $script:step = -1; $script:simVissim = 0; $script:simDisk = $null; $script:simDead = @(); $script:simShaBad = $false
$script:simWmi = 0; $script:simKills = @()
function Apply-Step {
  $script:step++
  $steps = @($script:sc.steps)
  if ($script:step -ge $steps.Count) { return $false }
  $s = $steps[$script:step]
  $script:simVissim = [int]$s.vissim
  if ($null -ne $s.disk) { $script:simDisk = @{ C = [double]$s.disk.C; D = [double]$s.disk.D } }
  if ($null -ne $s.sha_bad) { $script:simShaBad = [bool]$s.sha_bad }
  foreach ($w in @($s.write)) { if ($null -eq $w) { continue }
    $p = Join-Path $Root $w.path; New-Item -ItemType Directory -Force -Path (Split-Path -Parent $p) | Out-Null
    [IO.File]::WriteAllText($p, [string]$w.text, $UTF8) }
  foreach ($d in @($s.dead)) { if ($d) { $script:simDead += [string]$d } }
  Note ('DRYRUN_STEP ' + ($script:step + 1) + '/' + $steps.Count + ' others_vissim=' + $script:simVissim + ' note=' + [string]$s.note)
  return $true
}
function Get-VissimCount {
  if ($script:LMODE -eq 'dryrun') {
    $n = $script:simVissim
    foreach ($s in $SEEDS) { foreach ($a in 1, 2) {
      $rj = Read-Json (Join-Path (Join-Path $Root ('s' + $s)) ((Get-OutName $a) + '\run.json'))
      if ($rj -and $rj.vissim -and -not $rj.finished -and -not ($script:simDead -contains (Get-Key $s $a))) { $n++ } } }
    return $n
  }
  return @(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^VISSIM' }).Count
}
function Get-Disk {
  if ($script:LMODE -eq 'dryrun' -and $script:simDisk) { return $script:simDisk }
  return @{ C = [math]::Round((Get-PSDrive C).Free / 1GB, 1); D = [math]::Round((Get-PSDrive D).Free / 1GB, 1) }
}
function Test-CmdAlive($rcpt, [int]$seed, [int]$attempt) {
  if ($script:LMODE -eq 'dryrun') { return -not ($script:simDead -contains (Get-Key $seed $attempt)) }
  if (-not $rcpt -or -not $rcpt.ProcessId) { return $false }
  $p = Get-CimInstance Win32_Process -Filter ('ProcessId=' + [int]$rcpt.ProcessId) -ErrorAction SilentlyContinue
  if (-not $p) { return $false }
  if ([string]$p.CreationDate.ToUniversalTime().Ticks -ne [string]$rcpt.creation_ticks) { return $false }
  $want = '*-Prepared ' + (Join-Path $Root ('s' + $seed)) + '\prepared -Output*'
  return ([string]$p.CommandLine -like $want)
}

# ---------------- run state ----------------
function Get-Attempt([int]$seed, [int]$attempt) {
  $key = Get-Key $seed $attempt
  if (-not (Test-Path -LiteralPath (Join-Path $LD ('launched_' + $key + '.json')))) { return $null }
  $res = Join-Path (Join-Path $Root ('s' + $seed)) (Get-OutName $attempt)
  $rcpt = Read-Json (Join-Path $LD ('receipt_' + $key + '.json'))
  $rj = Read-Json (Join-Path $res 'run.json')
  $end = Read-Json (Join-Path $LD ('end_' + $key + '.json'))
  $o = [pscustomobject]@{ seed = $seed; attempt = $attempt; key = $key; res = $res; rcpt = $rcpt; rj = $rj; status = ''; detail = '' }
  if ($end) { $o.status = [string]$end.status; $o.detail = [string]$end.detail; return $o }
  if (-not $rcpt) { return (Set-End $o 'abnormal' 'marker_without_receipt') }
  if ([int]$rcpt.ReturnValue -ne 0) { return (Set-End $o 'abnormal' ('wmi_return_value_' + $rcpt.ReturnValue)) }
  if ($rj -and $rj.finished) {
    if ($rj.completed -eq $true) { return (Set-End $o 'done' 'completed') }
    $err = [string]$rj.error
    $stalled = $err.StartsWith('Startup300s') -or $err.StartsWith('Progress300s') -or (Test-Path -LiteralPath (Join-Path $LD ('backstop_kill_' + $key + '.json')))
    if ($stalled) { return (Set-End $o 'stalled' $err) }
    return (Set-End $o 'abnormal' ('run_not_completed: ' + $err))
  }
  if (Test-CmdAlive $rcpt $seed $attempt) { $o.status = 'active'; return $o }
  # cmd.exe gone: give the receipt writer a moment, then classify
  Start-Sleep -Milliseconds 500
  $rj = Read-Json (Join-Path $res 'run.json')
  if ($rj -and $rj.finished) { $o.rj = $rj; return (Get-Attempt $seed $attempt) }
  return (Set-End $o 'abnormal' 'runner_gone_without_finished_run_json')
}
function Set-End($o, [string]$status, [string]$detail) {
  $p = Join-Path $LD ('end_' + $o.key + '.json')
  if (New-Marker $p ([ordered]@{ key = $o.key; status = $status; detail = $detail; res = $o.res; time = (Get-Date).ToString('o'); launcher_pid = $PID })) {
    Note ('RUN_END ' + $o.key + ' status=' + $status + ' detail=' + $detail)
  }
  $o.status = $status; $o.detail = $detail
  return $o
}
function Stop-Launching([string]$why) {
  $p = Join-Path $LD 'LAUNCH_STOPPED.json'
  if (New-Marker $p ([ordered]@{ why = $why; time = (Get-Date).ToString('o'); launcher_pid = $PID })) { Note ('LAUNCH_STOPPED ' + $why) }
}
function Test-Stopped { return (Test-Path -LiteralPath (Join-Path $LD 'LAUNCH_STOPPED.json')) }

function Invoke-Backstop($o) {
  # progress.csv must have advanced within StallBackstopSec; fast_nc_run.ps1 already stops its own run at 300 s.
  $pc = Join-Path $o.res 'progress.csv'
  $rcptTime = [datetime]::Parse([string]$o.rcpt.time)
  $last = $rcptTime
  if (Test-Path -LiteralPath $pc) {
    $lw = (Get-Item -LiteralPath $pc).LastWriteTime
    if ($lw -gt $last) { $last = $lw }
  }
  $age = ((Get-Date) - $last).TotalSeconds
  if ($script:LMODE -eq 'dryrun' -and $script:sc.steps[$script:step].stall_age_sec) {
    $v = $script:sc.steps[$script:step].stall_age_sec.($o.key); if ($null -ne $v) { $age = [double]$v }
  }
  if ($age -lt $StallBackstopSec) { return }
  $mk = Join-Path $LD ('backstop_kill_' + $o.key + '.json')
  if (Test-Path -LiteralPath $mk) { return }
  $rj = $o.rj
  $kills = @()
  $targets = @()
  if ($rj -and $rj.cscript_pid) { $targets += [pscustomobject]@{ pid = [int]$rj.cscript_pid; start = [string]$rj.cscript_start; what = 'cscript' } }
  if ($rj -and $rj.vissim -and $rj.vissim.pid) { $targets += [pscustomobject]@{ pid = [int]$rj.vissim.pid; start = [string]$rj.vissim.start; what = 'vissim' } }
  foreach ($t in $targets) {
    if ($script:LMODE -eq 'dryrun') { $script:simKills += ($o.key + ':' + $t.what + ':' + $t.pid); $kills += ($t.what + ':' + $t.pid + ':dryrun'); continue }
    $p = Get-Process -Id $t.pid -ErrorAction SilentlyContinue
    if ($p -and $t.start -and ([datetime]::Parse($t.start).ToUniversalTime() -eq $p.StartTime.ToUniversalTime())) {
      Stop-Process -Id $t.pid -Force; $kills += ($t.what + ':' + $t.pid)
    } else { $kills += ($t.what + ':' + $t.pid + ':not_ours_or_gone') }
  }
  [void](New-Marker $mk ([ordered]@{ key = $o.key; age_sec = $age; kills = $kills; time = (Get-Date).ToString('o') }))
  Note ('STALL_BACKSTOP ' + $o.key + ' no progress for ' + [math]::Round($age) + ' s; killed own PIDs only: ' + ($kills -join ','))
}

function Invoke-Launch([int]$seed, [int]$attempt) {
  $key = Get-Key $seed $attempt
  $base = Join-Path $Root ('s' + $seed)
  $res = Join-Path $base (Get-OutName $attempt)
  $lg = Join-Path $base (Get-LogName $attempt)
  if ((Test-Path -LiteralPath $res) -or (Test-Path -LiteralPath $lg)) { Stop-Launching ('output or log exists before launch: ' + $key); return $false }
  $lock = Open-Lock (Join-Path $LD 'seat.lock')
  if (-not $lock) { Note 'SEAT_LOCK_BUSY'; return $false }
  try {
    $n = Get-VissimCount
    $pending = 0
    foreach ($s in $SEEDS) { foreach ($a in 1, 2) {
      $o = Get-Attempt $s $a
      if ($o -and $o.status -eq 'active' -and -not ($o.rj -and $o.rj.vissim)) {
        if (((Get-Date) - [datetime]::Parse([string]$o.rcpt.time)).TotalSeconds -lt $VissimUpWaitSec) { $pending++ } } } }
    if ($n + $pending -ge $CAP) { Note ('SEAT_WAIT ' + $key + ' vissim=' + $n + ' pending=' + $pending); return $false }
    $mk = Join-Path $LD ('launched_' + $key + '.json')
    $cmd = Get-CmdLine $seed $attempt
    if (-not (New-Marker $mk ([ordered]@{ key = $key; time = (Get-Date).ToString('o'); launcher_pid = $PID; launcher_sha256 = $SELF_SHA; vissim_before = $n; pending = $pending; cmdline = $cmd }))) {
      Note ('MARKER_EXISTS ' + $key + ' (never launched twice)'); return $false
    }
    $disk = Get-Disk
    if ($script:LMODE -eq 'dryrun') {
      $script:simWmi++
      $rc = [ordered]@{ key = $key; ReturnValue = 0; ProcessId = 9000 + $script:simWmi; creation_ticks = '0'; time = (Get-Date).ToString('o'); vissim_before = $n; pending = $pending; cmdline = $cmd; dryrun = $true }
    } else {
      $r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd; CurrentDirectory = $Root }
      $ticks = ''
      if ($r.ReturnValue -eq 0) { $pp = Get-CimInstance Win32_Process -Filter ('ProcessId=' + [int]$r.ProcessId) -ErrorAction SilentlyContinue; if ($pp) { $ticks = [string]$pp.CreationDate.ToUniversalTime().Ticks } }
      $rc = [ordered]@{ key = $key; ReturnValue = [int]$r.ReturnValue; ProcessId = [int]$r.ProcessId; creation_ticks = $ticks; time = (Get-Date).ToString('o'); vissim_before = $n; pending = $pending; cmdline = $cmd }
    }
    Save-Json (Join-Path $LD ('receipt_' + $key + '.json')) $rc
    $line = (Get-Date).ToString('o') + '  ' + $key + '  RV=' + $rc.ReturnValue + ' PID=' + $rc.ProcessId + ' VISSIM_before=' + $n + ' pending=' + $pending + ' freeC_GB=' + $disk.C + ' freeD_GB=' + $disk.D + ' | ' + $cmd
    [IO.File]::AppendAllText((Join-Path $Root 'wmi_launch_lines_vsl.txt'), $line + "`r`n", $UTF8)
    Note ('LAUNCH ' + $key + ' RV=' + $rc.ReturnValue + ' PID=' + $rc.ProcessId + ' vissim_before=' + $n + ' pending=' + $pending)
    return $true
  } finally { $lock.Dispose() }
}

# ---------------- main ----------------
$inst = Open-Lock (Join-Path $LD 'instance.lock')
if (-not $inst) { Note 'ANOTHER_INSTANCE_RUNNING exit 2'; exit 2 }
try {
  $fsp = Join-Path $LD 'first_start.json'
  if (-not (Test-Path -LiteralPath $fsp)) { Save-Json $fsp ([ordered]@{ time = (Get-Date).ToString('o'); launcher_pid = $PID; launcher_sha256 = $SELF_SHA; mode = $script:LMODE }) }
  $first = [datetime]::Parse([string](Read-Json $fsp).time)
  Note ('START sha256=' + $SELF_SHA + ' root=' + $Root + ' poll=' + $PollSec + ' backstop=' + $StallBackstopSec)
  if ($script:LMODE -eq 'dryrun') { $script:sc = Get-Content -LiteralPath $Scenario -Raw -Encoding UTF8 | ConvertFrom-Json }
  while ($true) {
    if ($script:LMODE -eq 'dryrun') { if (-not (Apply-Step)) { Note 'DRYRUN_END scenario exhausted'; break } }
    if (((Get-Date) - $first).TotalHours -gt $GiveUpHours) { Stop-Launching 'give_up_hours'; Note 'EXIT give_up_hours'; break }
    if (-not (Test-Stopped)) {
      if ((Test-Path -LiteralPath (Join-Path $Root 'STOP_VSL_LAUNCHER')) -or (Test-Path -LiteralPath (Join-Path $Root 'STOP'))) { Stop-Launching 'stop_file' }
      $bad = Test-Fixed; if ($bad) { Stop-Launching ('fixed_file_changed ' + $bad) }
      $disk = Get-Disk; if ($disk.C -lt $MIN_FREE_GB -or $disk.D -lt $MIN_FREE_GB) { Stop-Launching ('disk_low C=' + $disk.C + ' D=' + $disk.D) }
    }
    $active = 0; $todo = @()
    foreach ($s in $SEEDS) {
      $o1 = Get-Attempt $s 1; $o2 = Get-Attempt $s 2
      foreach ($o in @($o1, $o2)) { if ($o -and $o.status -eq 'active') { $active++; Invoke-Backstop $o } }
      foreach ($o in @($o1, $o2)) { if ($o -and $o.status -eq 'abnormal') { Stop-Launching ('abnormal_end ' + $o.key + ' ' + $o.detail) } }
      if ($o2 -and $o2.status -eq 'stalled') { Stop-Launching ('stalled_again ' + $o2.key) }
      if (-not $o1) { $todo += [pscustomobject]@{ seed = $s; attempt = 1 } }
      elseif ($o1.status -eq 'stalled' -and -not $o2) { $todo += [pscustomobject]@{ seed = $s; attempt = 2 } }
    }
    if (-not (Test-Stopped) -and $todo.Count -gt 0) {
      $t = $todo[0]
      [void](Invoke-Launch $t.seed $t.attempt)
    }
    if ($active -eq 0 -and ((Test-Stopped) -or $todo.Count -eq 0)) {
      # re-check after a possible launch in this poll
      $any = $false
      foreach ($s in $SEEDS) { foreach ($a in 1, 2) { $o = Get-Attempt $s $a; if ($o -and $o.status -eq 'active') { $any = $true } } }
      if (-not $any) {
        $sum = @(); foreach ($s in $SEEDS) { foreach ($a in 1, 2) { $o = Get-Attempt $s $a; if ($o) { $sum += ($o.key + '=' + $o.status) } } }
        Note ('EXIT nothing active; stopped=' + (Test-Stopped) + ' ' + ($sum -join ' '))
        break
      }
    }
    if ($script:LMODE -eq 'run') { Start-Sleep -Seconds $PollSec } elseif ($PollSec -gt 0) { Start-Sleep -Seconds $PollSec }
  }
} finally { $inst.Dispose() }
if ($script:LMODE -eq 'dryrun') { Note ('DRYRUN_SUMMARY wmi_creates=' + $script:simWmi + ' kills=' + ($script:simKills -join ',')) }
exit 0
