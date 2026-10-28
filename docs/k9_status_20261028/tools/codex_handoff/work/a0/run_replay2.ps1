# A0 offline replay of ONE recorded codex joint decision (no VISSIM, no COM).
# Mirrors pristine inputs to the fixed working tree, sets the codex runner env conventions,
# runs the adapter exactly as the VBS command line does, samples CPU load, records timings.
param(
  [Parameter(Mandatory=$true)][int]$T,
  [Parameter(Mandatory=$true)][string]$Label,
  [switch]$Trace,
  [string]$ExtraEnv = '',
  [string]$Note = '',
  [string]$Wrapper = '',
  [string]$TuningName = 'optimized_config.json',
  [string]$PyExe = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
)
$ErrorActionPreference = 'Stop'
$A0 = 'D:\VISSIM-merge\k8_gate_trees\codexhandoff\a0'
$WORK = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\work\a0'
$PY = $PyExe
$DEPS = 'D:\VISSIM-window264-deps'
$CODE = Join-Path $A0 'code'
$t6 = '{0:D6}' -f $T
$p6 = '{0:D6}' -f ($T - 150)
$pristine = Join-Path $A0 ('pristine\T' + $t6)
$runT = Join-Path $A0 ('runs\T' + $t6)
$run = Join-Path $runT 'sdmpc'
$dec = Join-Path $run 'decisions_sdmpc31_sdmpc8100_s29'
$out = Join-Path $A0 ('out\' + $Label + '\T' + $t6)
if (Test-Path -LiteralPath $out) { throw "output folder exists: $out" }
New-Item -ItemType Directory -Force -Path $out | Out-Null
$statePath = Join-Path $out 'replay_state.json'
$s = [ordered]@{ T = $T; label = $Label; tuning_name = $TuningName; py_exe = $PyExe; trace = [bool]$Trace; extra_env = $ExtraEnv; note = $Note;
  wrapper_pid = $PID; priority = (Get-Process -Id $PID).PriorityClass.ToString(); status = 'preparing' }
($s | ConvertTo-Json -Depth 5) | Set-Content -Encoding UTF8 -LiteralPath $statePath
# fresh working tree = pristine
& robocopy.exe $pristine $runT /MIR /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy mirror failed $LASTEXITCODE" }
if (Test-Path -LiteralPath (Join-Path $dec ('action_' + $t6 + '.json'))) { throw 'output already present in working tree' }
# env: codex runner conventions (run_closedloop3000.ps1:109-117) + recorded RW_* (run_provenance /env)
foreach ($item in @(Get-ChildItem Env: | Where-Object { $_.Name -like 'RW_*' })) { [Environment]::SetEnvironmentVariable($item.Name, $null, 'Process') }
$rw = [ordered]@{
  RW_DECISION_FAIL_FAST = '1'; RW_DECISION_HOLD_PREVIOUS = '1'; RW_DECISION_TIMEOUT_SEC = '1800';
  RW_LANE_PLANT_OBSERVATION = '1'; RW_MAINLINE_SG_ONLY = '1';
  RW_OBS150_DETECTORS = (Join-Path $CODE 'diagnostics\sdmpc_n31_20260924\integration_20260926\selected\obs150\obs150_detectors_v2.csv');
  RW_OBS150_DETECTORS_SHA256 = '108debbb4b021796b195927ba2140dafab571e1d976734190f5d8f5bd255cfbc';
  RW_OBS150_EXPECTED_SIMRES = '10'; RW_OBS150_GT = ''; RW_OBS150_VEHREC_SEC = '5';
  RW_OBSERVATION_CADENCE = 'decision150'; RW_OFFSET_WRITER = 'experiment'; RW_PYTHON = $PY;
  RW_QUEUE_COUNTER = '1'; RW_QUEUE_WINDOW = '0'; RW_RAMP_AMBER_SEC = '0'; RW_SIGNAL_OBSERVATION = '0';
  RW_SIGNAL_OBSERVATION_CONFIG_SHA256 = 'c90882628ddc75c0c75c9a82771c96a50614b297839ec32c506859a969dc1df3';
  RW_STATE_LOG = 'decision'; RW_VEHICLE_OBSERVATION_INTERVAL_SEC = '1' }
foreach ($k in $rw.Keys) { if ($rw[$k] -ne '') { [Environment]::SetEnvironmentVariable($k, $rw[$k], 'Process') } }
$env:PYTHONUTF8 = '1'; $env:PYTHONDONTWRITEBYTECODE = '1'; $env:PYTHONHASHSEED = '0'
$env:PYTHONPATH = $DEPS + ';' + $CODE
$env:NUMSIM_REPO_ROOT = Join-Path $CODE 'vendor\NumSim-mine'
$env:OMP_NUM_THREADS = '1'; $env:OPENBLAS_NUM_THREADS = '1'; $env:MKL_NUM_THREADS = '1'
foreach ($n in @('NUMBA_NUM_THREADS','NUMBA_THREADING_LAYER','NUMBA_CACHE_DIR','NUMBA_DISABLE_JIT')) { [Environment]::SetEnvironmentVariable($n, $null, 'Process') }
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
  '--tuning-json', (Join-Path $CODE ('diagnostics\repin_v3c3_review_20261001\urban_rm269\aggregate270\native413_adopted355\' + $TuningName)),
  '--previous-action-json', (Join-Path $dec ('action_' + $p6 + '.json')))
if ($Wrapper -ne '') { $pyArgs = @('-B', $Wrapper, $adapter) + $argsList }
elseif ($Trace) { $pyArgs = @('-B', (Join-Path $WORK 'trace_main.py'), (Join-Path $out 'trace_opens.tsv'), $adapter) + $argsList }
else { $pyArgs = @('-B', $adapter) + $argsList }
# CPU load sampler (own process; stopped by its PID only)
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
$s.python_pid = $proc.Id
($s | ConvertTo-Json -Depth 5) | Set-Content -Encoding UTF8 -LiteralPath $statePath
$proc.WaitForExit()
$code = $proc.ExitCode
$sw.Stop()
$end = Get-Date
try { Stop-Process -Id $tp.Id -ErrorAction Stop } catch {}
$s.exit_code = $code
$s.end = $end.ToString('yyyy-MM-dd HH:mm:ss.fff zzz')
$s.wall_sec = [math]::Round($sw.Elapsed.TotalSeconds, 3)
# collect every file that is new or changed versus the pristine input tree
$s.status = 'collecting'
($s | ConvertTo-Json -Depth 5) | Set-Content -Encoding UTF8 -LiteralPath $statePath
& 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe' -B (Join-Path $WORK 's5_collect.py') $pristine $runT (Join-Path $out 'files') > (Join-Path $out 'collect.txt') 2>&1
$s.collect_exit = $LASTEXITCODE
$s.status = 'done'
($s | ConvertTo-Json -Depth 5) | Set-Content -Encoding UTF8 -LiteralPath $statePath
