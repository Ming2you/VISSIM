# B0 ramp-arrival inspection run (configure level only, b0_probe_rampfc.py); copy of run_replay_b0.ps1 with the wrapper swapped.
# Copy of work/a0/run_replay2.ps1 with: b0 tree and pristine/<Src> inputs, a tuning path inside b0/code,
# a probe wrapper (configure = stop after configure; full = whole decision with open log; plain = no wrapper),
# and the python process set to BelowNormal (A1 runs at Normal).
param(
  [Parameter(Mandatory=$true)][int]$T,
  [Parameter(Mandatory=$true)][string]$Src,
  [Parameter(Mandatory=$true)][string]$Label,
  [Parameter(Mandatory=$true)][string]$TuningRel,
  [ValidateSet('configure','full','plain')][string]$Mode = 'configure',
  [string]$ExtraEnv = '',
  [string]$Note = '',
  [string]$PyExe = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
)
$ErrorActionPreference = 'Stop'
$B0 = 'D:\VISSIM-merge\k8_gate_trees\codexhandoff\b0'
$WORK = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\work\b0'
$WORK0 = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\work\a0'
$PY = $PyExe
$DEPS = 'D:\VISSIM-window264-deps'
$CODE = Join-Path $B0 'code'
$decName = @{ 'va_s31' = 'decisions_sdmpc31_v3c3_k92va_s31'; 'va_s31gk' = 'decisions_sdmpc31_v3c3_k92va_s31' }[$Src]
if (-not $decName) { throw "unknown source label $Src" }
$t6 = '{0:D6}' -f $T
$p6 = '{0:D6}' -f ($T - 150)
$pristine = Join-Path $B0 ('pristine\' + $Src + '\T' + $t6)
$runT = Join-Path $B0 ('runs\' + $Src + '\T' + $t6)
$run = Join-Path $runT 'run'
$dec = Join-Path $run $decName
$out = Join-Path $B0 ('out\' + $Label + '\' + $Src + '\T' + $t6)
if (Test-Path -LiteralPath $out) { throw "output folder exists: $out" }
$tuning = Join-Path $CODE $TuningRel
if (-not (Test-Path -LiteralPath $tuning -PathType Leaf)) { throw "tuning missing: $tuning" }
New-Item -ItemType Directory -Force -Path $out | Out-Null
$statePath = Join-Path $out 'replay_state.json'
$tuningSha = (Get-FileHash -LiteralPath $tuning -Algorithm SHA256).Hash.ToLowerInvariant()
$s = [ordered]@{ T = $T; src = $Src; label = $Label; mode = $Mode; tuning = $tuning; tuning_sha256 = $tuningSha; py_exe = $PyExe;
  extra_env = $ExtraEnv; note = $Note; wrapper_pid = $PID; priority = (Get-Process -Id $PID).PriorityClass.ToString(); status = 'preparing' }
($s | ConvertTo-Json -Depth 5) | Set-Content -Encoding UTF8 -LiteralPath $statePath
& robocopy.exe (Join-Path $pristine 'run') $run /MIR /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy mirror failed $LASTEXITCODE" }
# the provenance and network folder live beside the decision folder (same layout as the recorded run)
if (Test-Path -LiteralPath (Join-Path $dec ('action_' + $t6 + '.json'))) { throw 'output already present in working tree' }
foreach ($item in @(Get-ChildItem Env: | Where-Object { $_.Name -like 'RW_*' })) { Remove-Item -LiteralPath ('Env:' + $item.Name) }
$rw = [ordered]@{
  RW_DECISION_FAIL_FAST = '1'; RW_LANE_PLANT_OBSERVATION = '1'; RW_MAINLINE_SG_ONLY = '1';
  RW_OBS150_DETECTORS = (Join-Path $CODE 'diagnostics\sdmpc_n31_20260924\obs150\obs150_detectors_v2.csv');
  RW_OBS150_DETECTORS_SHA256 = '108debbb4b021796b195927ba2140dafab571e1d976734190f5d8f5bd255cfbc';
  RW_OBS150_EXPECTED_SIMRES = '10'; RW_OBS150_VEHREC_SEC = '5';
  RW_OBSERVATION_CADENCE = 'decision150'; RW_OFFSET_WRITER = 'experiment'; RW_PYTHON = $PY;
  RW_QUEUE_COUNTER = '1'; RW_QUEUE_WINDOW = '0'; RW_RAMP_AMBER_SEC = '0'; RW_SIGNAL_OBSERVATION = '0';
  RW_SIGNAL_OBSERVATION_CONFIG_SHA256 = $tuningSha;
  RW_STATE_LOG = 'decision'; RW_VEHICLE_OBSERVATION_INTERVAL_SEC = '1' }
foreach ($k in $rw.Keys) { if ($rw[$k] -ne '') { [Environment]::SetEnvironmentVariable($k, $rw[$k], 'Process') } }
$env:PYTHONUTF8 = '1'; $env:PYTHONDONTWRITEBYTECODE = '1'; $env:PYTHONHASHSEED = '0'
$env:PYTHONPATH = $DEPS + ';' + $CODE
$env:NUMSIM_REPO_ROOT = Join-Path $CODE 'vendor\NumSim-mine'
$env:OMP_NUM_THREADS = '1'; $env:OPENBLAS_NUM_THREADS = '1'; $env:MKL_NUM_THREADS = '1'
foreach ($n in @('NUMBA_NUM_THREADS','NUMBA_THREADING_LAYER','NUMBA_CACHE_DIR','NUMBA_DISABLE_JIT')) { if (Test-Path -LiteralPath ('Env:' + $n)) { Remove-Item -LiteralPath ('Env:' + $n) } }
if ($ExtraEnv -ne '') {
  foreach ($pair in $ExtraEnv.Split(';')) { if ($pair -match '^([^=]+)=(.*)$') { [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2], 'Process') } }
}
$adapter = Join-Path $CODE 'evaluation\controllers\vissim_stackelberg_adapter.py'
$argsList = @('--state-json', (Join-Path $dec ('state_' + $t6 + '.json')),
  '--out-action-json', (Join-Path $dec ('action_' + $t6 + '.json')),
  '--out-action-csv', (Join-Path $dec ('action_' + $t6 + '.csv')),
  '--mapping-json', (Join-Path $CODE 'evaluation\real_world_modi_control_ver2n21_20260907\control_mapping_ver2n21.json'),
  '--controller', 'wu-link',
  '--detector-mapping-json', 'evaluation\real_world_modi_control_ver2_20260907\detector_local_mapping_ver2_20260907.json',
  '--calibration-json', (Join-Path $CODE 'evaluation\calibration\real_world_prediction_calibration_core17legs4b_20260820.json'),
  '--tuning-json', $tuning,
  '--previous-action-json', (Join-Path $dec ('action_' + $p6 + '.json')))
$pyArgs = @('-B', (Join-Path $WORK 'b0_probe_rampfc.py'), (Join-Path $out 'rampfc.json'), (Join-Path $CODE 'diagnostics\b0_v3c3\config_b0_v3c3.json'), (Join-Path $CODE 'diagnostics\b0_v3c3\config_b0_v3c3_groupkeys.json'), $adapter) + $argsList
$perfCsv = Join-Path $out 'cpu_load.csv'
$tp = Start-Process -FilePath 'typeperf.exe' -ArgumentList @('"\Processor(_Total)\% Processor Time"', '"\System\Processor Queue Length"', '-si', '5', '-o', ('"' + $perfCsv + '"'), '-y') -WindowStyle Hidden -PassThru
$s.typeperf_pid = $tp.Id
$s.env = [ordered]@{}
foreach ($e in (Get-ChildItem Env: | Where-Object { $_.Name -like 'RW_*' -or $_.Name -like 'PYTHON*' -or $_.Name -like 'NUMSIM*' -or $_.Name -like '*_NUM_THREADS' -or $_.Name -like 'NUMBA*' -or $_.Name -like 'NPY_*' -or $_.Name -like 'OPENBLAS_*' } | Sort-Object Name)) { $s.env[$e.Name] = $e.Value }
$s.command = $PY + ' ' + ($pyArgs -join ' ')
$s.cwd = $CODE
$s.status = 'running'
$start = Get-Date
$s.start = $start.ToString('yyyy-MM-dd HH:mm:ss.fff zzz')
($s | ConvertTo-Json -Depth 5) | Set-Content -Encoding UTF8 -LiteralPath $statePath
Set-Location -LiteralPath $CODE
$quoted = @($pyArgs | ForEach-Object { '"' + $_ + '"' }) -join ' '
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$proc = Start-Process -FilePath $PY -ArgumentList $quoted -WorkingDirectory $CODE -NoNewWindow -PassThru `
  -RedirectStandardOutput (Join-Path $out 'stdout.txt') -RedirectStandardError (Join-Path $out 'stderr.txt')
$null = $proc.Handle
try { $proc.PriorityClass = [System.Diagnostics.ProcessPriorityClass]::BelowNormal } catch {}
$s.python_pid = $proc.Id
try { $s.python_priority = $proc.PriorityClass.ToString() } catch { $s.python_priority = 'unknown' }
($s | ConvertTo-Json -Depth 5) | Set-Content -Encoding UTF8 -LiteralPath $statePath
$proc.WaitForExit()
$code = $proc.ExitCode
$sw.Stop()
$end = Get-Date
try { Stop-Process -Id $tp.Id -ErrorAction Stop } catch {}
$s.exit_code = $code
$s.end = $end.ToString('yyyy-MM-dd HH:mm:ss.fff zzz')
$s.wall_sec = [math]::Round($sw.Elapsed.TotalSeconds, 3)
$s.status = 'collecting'
($s | ConvertTo-Json -Depth 5) | Set-Content -Encoding UTF8 -LiteralPath $statePath
& $PY -B (Join-Path $WORK0 's5_collect.py') (Join-Path $pristine 'run') $run (Join-Path $out 'files') > (Join-Path $out 'collect.txt') 2>&1
$s.collect_exit = $LASTEXITCODE
$s.status = 'done'
($s | ConvertTo-Json -Depth 5) | Set-Content -Encoding UTF8 -LiteralPath $statePath
