# A1 watch (read-only). One snapshot, or loop until a condition, for at most -MaxSec seconds.
# Progress signals = the watchdog's own list (run log, state CSV, action CSV, newest decisions action_*.json and,
# for unlimited decisions, action_*.joint.progress.jsonl; watchdog :962-998) + the watchdog log WATCHDOG_PROGRESS.txt.
# -Until T900 : return when runlog has CONTROLLER_DECISION sim_sec=900, or the run ended/failed, or idle > -IdleLimit.
param([int]$MaxSec = 0, [string]$Until = '', [int]$IdleLimit = 499, [int]$Every = 30,
      [string]$Log = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\work\a1\a1_watch.log')
$RES = 'D:\VISSIM_runs\20261025_codex_a1_s29'
$OUT = Join-Path $RES 'sdmpc'
$NAME = 'sdmpc31_sdmpc8100_s29'
$runlog = Join-Path $OUT ("runlog_" + $NAME + ".txt")
$dec = Join-Path $OUT ("decisions_" + $NAME)
function Note([string]$m) { ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' KST ' + $m) | Add-Content -Encoding UTF8 -LiteralPath $Log }
function Snap {
  $sig = @()
  foreach ($p in @($runlog, (Join-Path $OUT ("state_" + $NAME + ".csv")), (Join-Path $OUT ("action_" + $NAME + ".csv")), (Join-Path $OUT 'WATCHDOG_PROGRESS.txt'))) {
    $i = Get-Item -LiteralPath $p -ErrorAction SilentlyContinue; if ($i) { $sig += $i } }
  $sig += Get-ChildItem -Path (Join-Path $dec 'action_*.json') -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  $sig += Get-ChildItem -Path (Join-Path $dec 'action_*.joint.progress.jsonl') -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  $newest = $sig | Where-Object { $_ } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  $idle = if ($newest) { [int]((Get-Date) - $newest.LastWriteTime).TotalSeconds } else { -1 }
  $lastDec = ''; $simDone = $false; $stage = ''
  if (Test-Path -LiteralPath $runlog) {
    $m = Select-String -LiteralPath $runlog -Pattern '^CONTROLLER_DECISION sim_sec=(\d+) wall_sec=([0-9.]+) result=exit=(-?\d+)' | Select-Object -Last 1
    if ($m) { $lastDec = 'sim_sec=' + $m.Matches[0].Groups[1].Value + ' wall=' + $m.Matches[0].Groups[2].Value + ' exit=' + $m.Matches[0].Groups[3].Value }
    $simDone = [bool](Select-String -LiteralPath $runlog -Pattern '^STAGE=SIM_DONE' -Quiet)
    $s = Select-String -LiteralPath $runlog -Pattern '^(STAGE|STARTUP_STAGE)=' | Select-Object -Last 1
    if ($s) { $stage = $s.Line }
  }
  $prog = Get-ChildItem -Path (Join-Path $dec 'action_*.joint.progress.jsonl') -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  $progN = if ($prog) { $prog.Name + ' lines=' + (Get-Content -LiteralPath $prog.FullName | Measure-Object -Line).Lines } else { '' }
  $st = ''
  $sp = Join-Path $RES 'native_status.json'; if (Test-Path -LiteralPath $sp) { try { $st = (Get-Content -LiteralPath $sp -Raw | ConvertFrom-Json).stage } catch {} }
  $wend = Test-Path -LiteralPath (Join-Path $RES 'a1_launch\wrapper_run_end.json')
  $werr = Test-Path -LiteralPath (Join-Path $RES 'a1_launch\wrapper_run_error.json')
  $vis = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^Vissim' } | ForEach-Object { $_.ProcessId }) -join ','
  [pscustomobject]@{ idle = $idle; newest = $(if ($newest) { $newest.Name } else { '' }); last_decision = $lastDec; sim_done = $simDone; stage = $stage;
    progress = $progN; status = $st; wrapper_end = $wend; wrapper_error = $werr; vissim = $vis }
}
$t0 = Get-Date
while ($true) {
  $s = Snap
  $line = "idle=$($s.idle)s newest=$($s.newest) last_decision=[$($s.last_decision)] stage=[$($s.stage)] progress=[$($s.progress)] status=$($s.status) sim_done=$($s.sim_done) wrapper_end=$($s.wrapper_end) wrapper_error=$($s.wrapper_error) vissim=[$($s.vissim)]"
  $stop = ''
  if ($Until -eq 'T900' -and $s.last_decision -match '^sim_sec=(\d+)' -and [int]$Matches[1] -ge 900) { $stop = 'T900_DONE' }
  if ($s.wrapper_end -or $s.wrapper_error -or $s.sim_done) { $stop = 'RUN_ENDED' }
  if ($s.idle -gt $IdleLimit) { $stop = 'IDLE_OVER_LIMIT' }
  if ($MaxSec -le 0 -or $stop -or ((Get-Date) - $t0).TotalSeconds -ge $MaxSec) {
    Note ($(if ($stop) { $stop } else { 'snapshot' }) + ' ' + $line)
    ($(if ($stop) { $stop } else { 'RUNNING' }) + ' ' + $line)
    break
  }
  Start-Sleep -Seconds $Every
}
