# V3 (VSL_OFFLINE): run the plant probe for each prepared state, ONE AT A TIME (no VISSIM, no COM).
# Mirrors pristine -> runs/<label>, sets the codex runner env exactly as the pinned A0 replay script
# (codex_handoff/work/a0/run_replay2.ps1, sha 119bbd38...) plus env_hsw, then runs
#   python -B v3_plant_probe.py <adapter> <adapter args>   (BelowNormal; output json per state)
param([string]$Only = '')
$ErrorActionPreference = 'Stop'
$ROOT = 'D:\VISSIM-merge\k8_gate_trees\codexhandoff\vsl_off'
$VS = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\c_port\vsl'
$PY = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
$DEPS = 'D:\VISSIM-window264-deps'
$CODE = Join-Path $ROOT 'code'
$WRAP = Join-Path $VS 'work\v3_plant_probe.py'
try { (Get-Process -Id $PID).PriorityClass = 'BelowNormal' } catch {}
$states = @(
  @{ label = 'a1_T001800'; T = 1800; seed13 = 110 },
  @{ label = 'a1_T003600'; T = 3600; seed13 = 100 },
  @{ label = 'cx_T001800'; T = 1800; seed13 = 110 },
  @{ label = 'cx_T004500'; T = 4500; seed13 = 110 }
)
$log = Join-Path $VS 'out\v3_run.log'
Add-Content $log ("{0} chain start pid={1}" -f (Get-Date -Format s), $PID)
foreach ($s in $states) {
  if ($Only -ne '' -and $s.label -ne $Only) { continue }
  $label = $s.label; $T = $s.T
  $t6 = '{0:D6}' -f $T; $p6 = '{0:D6}' -f ($T - 150)
  $pristine = Join-Path $ROOT ('pristine\' + $label)
  $runT = Join-Path $ROOT ('runs\' + $label)
  $dec = Join-Path $runT 'sdmpc\decisions_sdmpc31_sdmpc8100_s29'
  $outJ = Join-Path $VS ('out\v3_' + $label + '.json')
  if (Test-Path -LiteralPath $outJ) { Add-Content $log ("{0} skip {1}" -f (Get-Date -Format s), $label); continue }
  & robocopy.exe $pristine $runT /MIR /NFL /NDL /NJH /NJS /NP | Out-Null
  if ($LASTEXITCODE -ge 8) { throw "robocopy mirror failed $LASTEXITCODE" }
  foreach ($item in @(Get-ChildItem Env: | Where-Object { $_.Name -like 'RW_*' })) { [Environment]::SetEnvironmentVariable($item.Name, $null, 'Process') }
  $rw = [ordered]@{
    RW_DECISION_FAIL_FAST = '1'; RW_DECISION_HOLD_PREVIOUS = '1'; RW_DECISION_TIMEOUT_SEC = '1800';
    RW_LANE_PLANT_OBSERVATION = '1'; RW_MAINLINE_SG_ONLY = '1';
    RW_OBS150_DETECTORS = (Join-Path $CODE 'diagnostics\sdmpc_n31_20260924\integration_20260926\selected\obs150\obs150_detectors_v2.csv');
    RW_OBS150_DETECTORS_SHA256 = '108debbb4b021796b195927ba2140dafab571e1d976734190f5d8f5bd255cfbc';
    RW_OBS150_EXPECTED_SIMRES = '10'; RW_OBS150_VEHREC_SEC = '5';
    RW_OBSERVATION_CADENCE = 'decision150'; RW_OFFSET_WRITER = 'experiment'; RW_PYTHON = $PY;
    RW_QUEUE_COUNTER = '1'; RW_QUEUE_WINDOW = '0'; RW_RAMP_AMBER_SEC = '0'; RW_SIGNAL_OBSERVATION = '0';
    RW_SIGNAL_OBSERVATION_CONFIG_SHA256 = 'c90882628ddc75c0c75c9a82771c96a50614b297839ec32c506859a969dc1df3';
    RW_STATE_LOG = 'decision'; RW_VEHICLE_OBSERVATION_INTERVAL_SEC = '1' }
  foreach ($k in $rw.Keys) { [Environment]::SetEnvironmentVariable($k, $rw[$k], 'Process') }
  $env:PYTHONUTF8 = '1'; $env:PYTHONDONTWRITEBYTECODE = '1'; $env:PYTHONHASHSEED = '0'
  $env:PYTHONPATH = $DEPS + ';' + $CODE
  $env:NUMSIM_REPO_ROOT = Join-Path $CODE 'vendor\NumSim-mine'
  $env:OMP_NUM_THREADS = '1'; $env:OPENBLAS_NUM_THREADS = '1'; $env:MKL_NUM_THREADS = '1'
  foreach ($n in @('NUMBA_NUM_THREADS','NUMBA_THREADING_LAYER','NUMBA_CACHE_DIR','NUMBA_DISABLE_JIT')) { [Environment]::SetEnvironmentVariable($n, $null, 'Process') }
  # env_hsw (as A0b/A1)
  $env:OPENBLAS_CORETYPE = 'Haswell'; $env:NPY_DISABLE_CPU_FEATURES = 'AVX512F AVX512CD AVX512_SKX AVX512_CLX'; $env:NUMBA_CPU_NAME = 'haswell'
  $spec = @(
    @{ label = 'v110_all'; keys = @('FW_E__seg13'); blocks = @(0,1,2); value = 110.0 },
    @{ label = 'v100_all'; keys = @('FW_E__seg13'); blocks = @(0,1,2); value = 100.0 },
    @{ label = 'v90_all';  keys = @('FW_E__seg13'); blocks = @(0,1,2); value = 90.0 },
    @{ label = 's5_100_all'; keys = @('FW_E__seg5'); blocks = @(0,1,2); value = 100.0 }
  )
  if ($s.seed13 -eq 110) { $spec += @{ label = 'v100_b0'; keys = @('FW_E__seg13'); blocks = @(0); value = 100.0 } }
  else { $spec += @{ label = 'v110_b0'; keys = @('FW_E__seg13'); blocks = @(0); value = 110.0 } }
  $env:VSL_PROBE_SPEC = ($spec | ConvertTo-Json -Compress -Depth 5)
  $env:VSL_PROBE_OUT = $outJ
  $adapter = Join-Path $CODE 'evaluation\controllers\vissim_stackelberg_adapter.py'
  $argsList = @('-B', $WRAP, $adapter,
    '--state-json', (Join-Path $dec ('state_' + $t6 + '.json')),
    '--out-action-json', (Join-Path $dec ('action_' + $t6 + '.json')),
    '--out-action-csv', (Join-Path $dec ('action_' + $t6 + '.csv')),
    '--mapping-json', (Join-Path $CODE 'evaluation\real_world_modi_control_ver2n21_20260907\control_mapping_ver2n21.json'),
    '--controller', 'wu-link',
    '--detector-mapping-json', 'evaluation\real_world_modi_control_ver2_20260907\detector_local_mapping_ver2_20260907.json',
    '--calibration-json', (Join-Path $CODE 'evaluation\calibration\real_world_prediction_calibration_core17legs4b_20260820.json'),
    '--tuning-json', (Join-Path $CODE 'diagnostics\repin_v3c3_review_20261001\urban_rm269\aggregate270\native413_adopted355\optimized_config.json'),
    '--previous-action-json', (Join-Path $dec ('action_' + $p6 + '.json')))
  $quoted = @($argsList | ForEach-Object { '"' + $_ + '"' }) -join ' '
  Add-Content $log ("{0} start {1} spec={2}" -f (Get-Date -Format s), $label, $env:VSL_PROBE_SPEC)
  $sw = [System.Diagnostics.Stopwatch]::StartNew()
  $proc = Start-Process -FilePath $PY -ArgumentList $quoted -WorkingDirectory $CODE -NoNewWindow -PassThru `
    -RedirectStandardOutput (Join-Path $VS ('out\v3_' + $label + '.stdout.txt')) -RedirectStandardError (Join-Path $VS ('out\v3_' + $label + '.stderr.txt'))
  $null = $proc.Handle
  try { $proc.PriorityClass = 'BelowNormal' } catch {}
  Add-Content $log ("{0} pid {1} {2}" -f (Get-Date -Format s), $label, $proc.Id)
  $proc.WaitForExit()
  $sw.Stop()
  Add-Content $log ("{0} end {1} exit={2} wall={3:N1}s" -f (Get-Date -Format s), $label, $proc.ExitCode, $sw.Elapsed.TotalSeconds)
}
Add-Content $log ("{0} CHAIN_DONE" -f (Get-Date -Format s))
