# B run watch (read-only). Same signals as A1 a1_watch.ps1 (7a1fced1...): watchdog's own progress list (run log, state CSV,
# action CSV, newest decisions action_*.json, newest action_*.joint.progress.jsonl; watchdog :962-998) + WATCHDOG_PROGRESS.txt,
# plus (startup only) the wrapper records in b_launch and launch.log. One snapshot, or loop for at most -MaxSec seconds.
# Returns early on: -Until T900 (runlog has CONTROLLER_DECISION sim_sec>=900), run ended (SIM_DONE / wrapper end / wrapper error /
# native_status failed), idle > -IdleLimit, a new non-zero decision exit (EXIT_NONZERO, so it can be checked), STOP file.
param([Parameter(Mandatory = $true)][ValidateSet(31, 41, 43)][int]$Seed, [int]$MaxSec = 0, [string]$Until = '', [int]$IdleLimit = 499,
      [int]$Every = 30, [int]$KnownNonzero = -1,
      [string]$Log = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\work\b\b_watch.log')
$RES = 'D:\VISSIM_runs\20261026_codex_b_v3c3\s' + $Seed
$OUT = Join-Path $RES 'sdmpc'
$NAME = 'sdmpc31_sdmpc9000_s' + $Seed
$runlog = Join-Path $OUT ('runlog_' + $NAME + '.txt')
$dec = Join-Path $OUT ('decisions_' + $NAME)
function Note([string]$m) { ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' KST s' + $Seed + ' ' + $m) | Add-Content -Encoding UTF8 -LiteralPath $Log }
function Snap {
  $sig = @()
  foreach ($p in @($runlog, (Join-Path $OUT ('state_' + $NAME + '.csv')), (Join-Path $OUT ('action_' + $NAME + '.csv')), (Join-Path $OUT 'WATCHDOG_PROGRESS.txt'))) {
    $i = Get-Item -LiteralPath $p -ErrorAction SilentlyContinue; if ($i) { $sig += $i } }
  $sig += Get-ChildItem -Path (Join-Path $dec 'action_*.json') -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  $sig += Get-ChildItem -Path (Join-Path $dec 'action_*.joint.progress.jsonl') -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  $startup = $false
  if (-not (Test-Path -LiteralPath $runlog)) {
    $startup = $true
    $sig += Get-ChildItem -Path (Join-Path $RES 'b_launch\*') -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    $i = Get-Item -LiteralPath (Join-Path $OUT 'launch.log') -ErrorAction SilentlyContinue; if ($i) { $sig += $i }
  }
  $newest = $sig | Where-Object { $_ } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  $idle = if ($newest) { [int]((Get-Date) - $newest.LastWriteTime).TotalSeconds } else { -1 }
  $lastDec = ''; $simDone = $false; $stage = ''; $nDec = 0; $nNon = 0; $maxWall = 0.0; $held = 0; $holdAtt = 0
  if (Test-Path -LiteralPath $runlog) {
    $ms = @(Select-String -LiteralPath $runlog -Pattern '^CONTROLLER_DECISION sim_sec=(\d+) wall_sec=([0-9.]+) result=exit=(-?\d+)')
    $nDec = $ms.Count
    foreach ($m in $ms) { $w = [double]$m.Matches[0].Groups[2].Value; if ($w -gt $maxWall) { $maxWall = $w }; if ($m.Matches[0].Groups[3].Value -ne '0') { $nNon++ } }
    if ($ms.Count) { $m = $ms[-1]; $lastDec = 'sim_sec=' + $m.Matches[0].Groups[1].Value + ' wall=' + $m.Matches[0].Groups[2].Value + ' exit=' + $m.Matches[0].Groups[3].Value }
    $simDone = [bool](Select-String -LiteralPath $runlog -Pattern '^STAGE=SIM_DONE' -Quiet)
    $held = @(Select-String -LiteralPath $runlog -Pattern '^DECISION_HELD_PREVIOUS').Count
    $holdAtt = @(Select-String -LiteralPath $runlog -Pattern '^DECISION_HOLD_ATTEMPT').Count
    $s = Select-String -LiteralPath $runlog -Pattern '^(STAGE|STARTUP_STAGE)=' | Select-Object -Last 1
    if ($s) { $stage = $s.Line }
  }
  $prog = Get-ChildItem -Path (Join-Path $dec 'action_*.joint.progress.jsonl') -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  $progN = if ($prog) { $prog.Name + ' lines=' + (Get-Content -LiteralPath $prog.FullName | Measure-Object -Line).Lines } else { '' }
  $st = ''
  $sp = Join-Path $RES 'native_status.json'; if (Test-Path -LiteralPath $sp) { try { $st = (Get-Content -LiteralPath $sp -Raw | ConvertFrom-Json).stage } catch {} }
  $wend = @(Get-ChildItem -Path (Join-Path $RES 'b_launch\wrapper_run*_end.json') -ErrorAction SilentlyContinue).Count -gt 0
  $werr = @(Get-ChildItem -Path (Join-Path $RES 'b_launch\wrapper_run*_error.json') -ErrorAction SilentlyContinue).Count -gt 0
  $stop = (Test-Path -LiteralPath (Join-Path $RES 'STOP')) -or (Test-Path -LiteralPath 'D:\VISSIM_runs\20261026_codex_b_v3c3\STOP')
  $vis = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^Vissim' } | ForEach-Object { $_.ProcessId }) -join ','
  $errLen = -1; $ef = Get-Item -LiteralPath ($runlog + '.err') -ErrorAction SilentlyContinue; if ($ef) { $errLen = $ef.Length }
  $c = [math]::Round((Get-PSDrive C).Free / 1GB, 1); $d = [math]::Round((Get-PSDrive D).Free / 1GB, 1)
  [pscustomobject]@{ idle = $idle; startup = $startup; newest = $(if ($newest) { $newest.Name } else { '' }); last_decision = $lastDec; n_dec = $nDec; n_nonzero = $nNon;
    max_wall = $maxWall; held = $held; hold_attempts = $holdAtt; sim_done = $simDone; stage = $stage; progress = $progN; status = $st;
    wrapper_end = $wend; wrapper_error = $werr; stop = $stop; vissim = $vis; err_bytes = $errLen; disk = "C=$c D=$d" }
}
$t0 = Get-Date
$base = $KnownNonzero
while ($true) {
  $s = Snap
  if ($base -lt 0) { $base = $s.n_nonzero }
  $line = "idle=$($s.idle)s startup=$($s.startup) newest=$($s.newest) last_decision=[$($s.last_decision)] n_dec=$($s.n_dec) nonzero=$($s.n_nonzero) hold_attempts=$($s.hold_attempts) held=$($s.held) max_wall=$($s.max_wall) stage=[$($s.stage)] progress=[$($s.progress)] status=$($s.status) sim_done=$($s.sim_done) wrapper_end=$($s.wrapper_end) wrapper_error=$($s.wrapper_error) stop=$($s.stop) vissim=[$($s.vissim)] runlog_err_bytes=$($s.err_bytes) disk=[$($s.disk)]"
  $why = ''
  if ($Until -eq 'T900' -and $s.last_decision -match '^sim_sec=(\d+)' -and [int]$Matches[1] -ge 900) { $why = 'T900_DONE' }
  if ($s.n_nonzero -gt $base) { $why = 'EXIT_NONZERO' }
  if ($s.wrapper_end -or $s.wrapper_error -or $s.sim_done -or $s.status -eq 'failed') { $why = 'RUN_ENDED' }
  if ($s.stop) { $why = 'STOP_FILE' }
  if ($s.idle -gt $IdleLimit) { $why = 'IDLE_OVER_LIMIT' }
  if ($MaxSec -le 0 -or $why -or ((Get-Date) - $t0).TotalSeconds -ge $MaxSec) {
    Note ($(if ($why) { $why } else { 'snapshot' }) + ' ' + $line)
    ($(if ($why) { $why } else { 'RUNNING' }) + ' ' + $line)
    break
  }
  Start-Sleep -Seconds $Every
}
