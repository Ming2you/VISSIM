# B0 replay queue (no VISSIM): full decisions of the b0 codex tree on recorded v3c3 states, one at a time, BELOW_NORMAL.
# A1 guard (rules of the B0 task): while a replay runs, if the A1 decision in progress has run longer than 1,500 s
# (A1 state_T.json written, action_T.csv not yet), the replay's own process tree is stopped (own PIDs only), the queue
# waits until that A1 decision ends, and the replay is started again once under a new label (<label>_r2).
# Stops the queue if C: or D: has < 8 GB free.  Writes work/b0/queue_b0.state.txt.
param([string]$Items = 'R1|va_s31|3450|diagnostics\b0_v3c3\config_b0_v3c3.json;R2|va_s31gk|3450|diagnostics\b0_v3c3\config_b0_v3c3_groupkeys.json;R3|va_s31|1800|diagnostics\b0_v3c3\config_b0_v3c3.json')
$W = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\work\b0'
$A1DEC = 'D:\VISSIM_runs\20261025_codex_a1_s29\sdmpc\decisions_sdmpc31_sdmpc8100_s29'
$PY = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
$hsw = 'OPENBLAS_CORETYPE=Haswell;NPY_DISABLE_CPU_FEATURES=AVX512F AVX512CD AVX512_SKX AVX512_CLX;NUMBA_CPU_NAME=haswell'
$stateFile = Join-Path $W 'queue_b0.state.txt'
function Note([string]$m) { ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz') + ' ' + $m) | Add-Content -Encoding UTF8 $stateFile }
function A1Running {
  # seconds the A1 decision in progress has run, or -1 when none is in progress
  $st = Get-ChildItem -Path (Join-Path $A1DEC 'state_*.json') -ErrorAction SilentlyContinue | Sort-Object Name | Select-Object -Last 1
  if (-not $st) { return -1 }
  $t6 = $st.Name.Substring(6, 6)
  if (Test-Path -LiteralPath (Join-Path $A1DEC ('action_' + $t6 + '.csv'))) { return -1 }
  return [int]((Get-Date) - $st.LastWriteTime).TotalSeconds
}
function Descendants([int]$Root) {
  $all = @(Get-CimInstance Win32_Process | Select-Object ProcessId, ParentProcessId)
  $out = @($Root); $frontier = @($Root)
  while ($frontier.Count) {
    $next = @($all | Where-Object { $frontier -contains $_.ParentProcessId } | ForEach-Object { [int]$_.ProcessId })
    $out += $next; $frontier = $next
  }
  return $out
}
$env:PYTHONHASHSEED = '0'; $env:PYTHONUTF8 = '1'; $env:PYTHONDONTWRITEBYTECODE = '1'
Note ('start wrapper_pid=' + $PID + ' priority=' + (Get-Process -Id $PID).PriorityClass + ' items=' + $Items)
foreach ($item in $Items.Split(';')) {
  $id, $src, $T, $tun = $item.Split('|')
  $label = 'b0' + $id
  $attempt = 1
  while ($true) {
    $c = [math]::Round((Get-PSDrive C).Free / 1GB, 1); $d = [math]::Round((Get-PSDrive D).Free / 1GB, 1)
    if ($c -lt 8 -or $d -lt 8) { Note "STOP: disk C=$c D=$d GB"; 'stop disk' | Set-Content -Encoding UTF8 (Join-Path $W 'queue_b0.stop'); exit 2 }
    while ((A1Running) -gt 1500) { Note "$label waiting: A1 decision in progress > 1500 s"; Start-Sleep -Seconds 60 }
    $lab = $(if ($attempt -eq 1) { $label } else { $label + '_r' + $attempt })
    $a = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $W 'run_replay_b0.ps1'), '-T', $T, '-Src', $src, '-Label', $lab,
           '-TuningRel', $tun, '-Mode', 'full', '-ExtraEnv', ('"' + $hsw + '"'), '-Note', ('"B0 ' + $id + ' full replay"'))
    $p = Start-Process -FilePath 'powershell.exe' -ArgumentList $a -WindowStyle Hidden -PassThru
    Note ("$lab start T=$T src=$src tuning=$tun child_pid=" + $p.Id + " C=$c D=$d GB")
    $guarded = $false
    while (-not $p.HasExited) {
      Start-Sleep -Seconds 30
      $run = A1Running
      if ($run -gt 1500) {
        $tree = Descendants $p.Id
        Note ("$lab GUARD: A1 decision running $run s > 1500 s; stopping own PIDs " + ($tree -join ','))
        foreach ($k in ($tree | Sort-Object -Descending)) { try { Stop-Process -Id $k -Force -ErrorAction Stop } catch {} }
        $guarded = $true
        break
      }
    }
    if ($guarded -and $attempt -lt 2) { $attempt++; continue }
    Note ("$lab end exit=" + $(if ($p.HasExited) { $p.ExitCode } else { 'stopped' }))
    break
  }
}
& $PY -B (Join-Path $W 'b0_replay_summary.py') (Join-Path $W 'b0_replay_summary.json') > (Join-Path $W 'b0_replay_summary.out.txt') 2>&1
Note ("summary exit=" + $LASTEXITCODE)
'done' | Set-Content -Encoding UTF8 (Join-Path $W 'queue_b0.done')
Note 'done'
