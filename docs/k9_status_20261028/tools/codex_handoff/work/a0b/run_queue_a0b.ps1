# A0b queue (2026-10-25): replay the recorded codex joint decisions T = 1050 ... 2550 one at a time on env_hsw.
# Each decision starts from its own recorded state and recorded previous action (pristine/T<T>, built by work/a0/s4_build_inputs.py);
# decisions are NOT chained. No VISSIM, no COM. Replays use work/a0/run_replay2.ps1 unchanged (label a0b_hsw).
# After each replay: A0-CMP-1 comparison (s13_compare.py), command summary (s20_cmdsummary.py), row listing (a0b_rows.py).
# Stops (writes a0b.stop) if C: or D: has < 8 GB free before a replay. A failed replay is recorded and the queue continues.
param([string]$Ts = '1050,1200,1350,1500,1650,1800,1950,2100,2250,2400,2550')
$W0 = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\work\a0'
$W = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\work\a0b'
$A0 = 'D:\VISSIM-merge\k8_gate_trees\codexhandoff\a0'
$PY = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
$LABEL = 'a0b_hsw'
$stateFile = Join-Path $W 'queue_a0b.state.txt'
function Note([string]$m) { ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz') + ' ' + $m) | Add-Content -Encoding UTF8 $stateFile }
function RunPy([string[]]$PyArgs, [string]$OutBase) {
  $quoted = @($PyArgs | ForEach-Object { '"' + $_ + '"' }) -join ' '
  $p = Start-Process -FilePath $PY -ArgumentList ('-B ' + $quoted) -NoNewWindow -Wait -PassThru `
    -RedirectStandardOutput ($OutBase + '.out.txt') -RedirectStandardError ($OutBase + '.err.txt')
  return $p.ExitCode
}
$hsw = 'OPENBLAS_CORETYPE=Haswell;NPY_DISABLE_CPU_FEATURES=AVX512F AVX512CD AVX512_SKX AVX512_CLX;NUMBA_CPU_NAME=haswell'
$env:PYTHONHASHSEED = '0'; $env:PYTHONUTF8 = '1'; $env:PYTHONDONTWRITEBYTECODE = '1'
Note ('start wrapper_pid=' + $PID + ' priority=' + (Get-Process -Id $PID).PriorityClass + ' Ts=' + $Ts)
foreach ($T in @($Ts.Split(',') | ForEach-Object { [int]$_ })) {
  $c = [math]::Round((Get-PSDrive C).Free / 1GB, 1); $d = [math]::Round((Get-PSDrive D).Free / 1GB, 1)
  Note ("T=$T disk C=$c GB D=$d GB")
  if ($c -lt 8 -or $d -lt 8) { Note 'STOP: disk below 8 GB'; 'stop disk' | Set-Content -Encoding UTF8 (Join-Path $W 'a0b.stop'); exit 2 }
  $vis = @(Get-Process -Name 'VISSIM*' -ErrorAction SilentlyContinue | ForEach-Object { $_.Id }) -join ','
  Note ("T=$T replay start (other VISSIM PIDs seen, not touched: [$vis])")
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $W0 'run_replay2.ps1') -T $T -Label $LABEL -ExtraEnv $hsw `
    -Note "A0b env_hsw T=$T; recorded state + recorded previous action; not chained"
  Note ("T=$T replay end exit=" + $LASTEXITCODE)
  $od = Join-Path $A0 ('out\' + $LABEL + '\T' + ('{0:D6}' -f $T))
  $csv = Join-Path $od ('files\sdmpc\decisions_sdmpc31_sdmpc8100_s29\action_' + ('{0:D6}' -f $T) + '.csv')
  if (-not (Test-Path -LiteralPath $csv)) { Note ("T=$T no action CSV produced; comparison skipped"); continue }
  $e1 = RunPy @((Join-Path $W0 's13_compare.py'), "$T", $LABEL) (Join-Path $od 's13')
  $e2 = RunPy @((Join-Path $W0 's20_cmdsummary.py'), $LABEL, "$T") (Join-Path $od 's20')
  $e3 = RunPy @((Join-Path $W 'a0b_rows.py'), "$T", $LABEL) (Join-Path $od 'rows')
  Note ("T=$T compare exits s13=$e1 s20=$e2 rows=$e3")
}
$e4 = RunPy @((Join-Path $W 'a0b_summary.py'), (Join-Path $W 'a0b_summary.json')) (Join-Path $W 'a0b_summary')
Note ("summary exit=$e4")
'done' | Set-Content -Encoding UTF8 (Join-Path $W 'queue_a0b.done')
Note 'done'
