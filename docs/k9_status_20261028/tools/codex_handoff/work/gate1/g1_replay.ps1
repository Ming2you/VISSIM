# Gate 1 offline run of ONE decision (T=900, first SDMPC decision) of the codex adapter on the B frozen tree FRZ_B0,
# from a recorded v3c3 state (no VISSIM, no COM). Derived from work/b0/run_replay_b0.ps1 (1b32085d...). Differences:
#  - code root = FRZ_B0 (read-only use; the SDMPC tangent code cache __tangentcache__ is excluded from FREEZE by design),
#  - inputs from gate1/pristine/<Src>/T<t6>, outputs under gate1/out/<Label>/<Src>/T<t6> and gate1/runs/<Src>/T<t6>,
#  - the RW_* variables are the non-empty RW_* of the run provenance in the input tree (= runner -PreflightOnly output of
#    the same seed and tuning), instead of a fixed list,
#  - plain adapter call (no audit-hook wrapper), python process priority = the parameter (default Normal: no B run is up),
#  - extra cleared variables as in the A1 wrapper v2 (NUMBA*/PYTHON*/OPENBLAS/NPY/MKL extras), env_hsw from -ExtraEnv.
param(
  [Parameter(Mandatory=$true)][int]$T,
  [Parameter(Mandatory=$true)][string]$Src,
  [Parameter(Mandatory=$true)][string]$Label,
  [Parameter(Mandatory=$true)][string]$TuningRel,
  [string]$ExtraEnv = '',
  [string]$Note = '',
  [ValidateSet('Normal','BelowNormal')][string]$Priority = 'Normal',
  [string]$PyExe = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
)
$ErrorActionPreference = 'Stop'
$G1 = 'D:\VISSIM-merge\k8_gate_trees\codexhandoff\gate1'
$CODE = 'D:\VISSIM-merge\k8_gate_trees\codexhandoff\b0\frozen\sdmpc31_a49981ff_202610260258'
$WORK0 = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\work\a0'
$PY = $PyExe
$DEPS = 'D:\VISSIM-window264-deps'
$decName = @{ 'va_s31' = 'decisions_sdmpc31_v3c3_k92va_s31'; 'va_s31gk' = 'decisions_sdmpc31_v3c3_k92va_s31';
              'va_s41' = 'decisions_sdmpc31_v3c3_k92va_s41'; 'va_s43' = 'decisions_sdmpc31_v3c3_k92va_s43' }[$Src]
$provName = @{ 'va_s31' = 'run_provenance_sdmpc31_v3c3_k92va_s31.json'; 'va_s31gk' = 'run_provenance_sdmpc31_v3c3_k92va_s31.json';
               'va_s41' = 'run_provenance_sdmpc31_v3c3_k92va_s41.json'; 'va_s43' = 'run_provenance_sdmpc31_v3c3_k92va_s43.json' }[$Src]
if (-not $decName) { throw "unknown source label $Src" }
$t6 = '{0:D6}' -f $T
$p6 = '{0:D6}' -f ($T - 150)
$pristine = Join-Path $G1 ('pristine\' + $Src + '\T' + $t6)
$runT = Join-Path $G1 ('runs\' + $Src + '\T' + $t6)
$run = Join-Path $runT 'run'
$dec = Join-Path $run $decName
$out = Join-Path $G1 ('out\' + $Label + '\' + $Src + '\T' + $t6)
if (Test-Path -LiteralPath $out) { throw "output folder exists: $out" }
$tuning = Join-Path $CODE $TuningRel
if (-not (Test-Path -LiteralPath $tuning -PathType Leaf)) { throw "tuning missing: $tuning" }
New-Item -ItemType Directory -Force -Path $out | Out-Null
$statePath = Join-Path $out 'replay_state.json'
$tuningSha = (Get-FileHash -LiteralPath $tuning -Algorithm SHA256).Hash.ToLowerInvariant()
$s = [ordered]@{ T = $T; src = $Src; label = $Label; mode = 'plain'; tuning = $tuning; tuning_sha256 = $tuningSha; py_exe = $PyExe; code_root = $CODE;
  extra_env = $ExtraEnv; note = $Note; wrapper_pid = $PID; priority_requested = $Priority; status = 'preparing' }
($s | ConvertTo-Json -Depth 5) | Set-Content -Encoding UTF8 -LiteralPath $statePath
& robocopy.exe (Join-Path $pristine 'run') $run /MIR /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy mirror failed $LASTEXITCODE" }
if (Test-Path -LiteralPath (Join-Path $dec ('action_' + $t6 + '.json'))) { throw 'output already present in working tree' }
# environment: clear, then RW_* from the input provenance (non-empty values), then the declared numeric env
$cleared = @('NUMBA_NUM_THREADS','NUMBA_THREADING_LAYER','NUMBA_CACHE_DIR','NUMBA_DISABLE_JIT','NUMBA_OPT','NUMBA_DEBUG',
  'PYTHONPYCACHEPREFIX','PYTHONHOME','PYTHONSTARTUP','PYTHONPATH','PYTHONOPTIMIZE','PYTHONWARNINGS','PYTHONINSPECT','PYTHONNOUSERSITE',
  'OPENBLAS_VERBOSE','OPENBLAS_MAIN_FREE','NPY_ENABLE_CPU_FEATURES','MKL_CBWR','MKL_ENABLE_INSTRUCTIONS')
foreach ($n in $cleared) { if (Test-Path -LiteralPath ('Env:' + $n)) { Remove-Item -LiteralPath ('Env:' + $n) } }
foreach ($item in @(Get-ChildItem Env: | Where-Object { $_.Name -like 'RW_*' })) { Remove-Item -LiteralPath ('Env:' + $item.Name) }
$prov = Get-Content -LiteralPath (Join-Path $run $provName) -Raw -Encoding UTF8 | ConvertFrom-Json
$rwSet = [ordered]@{}
foreach ($p in $prov.env.PSObject.Properties) { if ($p.Name -like 'RW_*' -and [string]$p.Value -ne '') { $rwSet[$p.Name] = [string]$p.Value } }
if ($rwSet['RW_SIGNAL_OBSERVATION_CONFIG_SHA256'] -ne $tuningSha) { throw 'provenance tuning sha differs from the tuning file' }
foreach ($k in $rwSet.Keys) { [Environment]::SetEnvironmentVariable($k, $rwSet[$k], 'Process') }
$env:PYTHONUTF8 = '1'; $env:PYTHONDONTWRITEBYTECODE = '1'; $env:PYTHONHASHSEED = '0'
$env:PYTHONPATH = $DEPS + ';' + $CODE
$env:NUMSIM_REPO_ROOT = Join-Path $CODE 'vendor\NumSim-mine'
$env:OMP_NUM_THREADS = '1'; $env:OPENBLAS_NUM_THREADS = '1'; $env:MKL_NUM_THREADS = '1'
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
$pyArgs = @('-B', $adapter) + $argsList
$perfCsv = Join-Path $out 'cpu_load.csv'
$tp = Start-Process -FilePath 'typeperf.exe' -ArgumentList @('"\Processor(_Total)\% Processor Time"', '"\System\Processor Queue Length"', '-si', '5', '-o', ('"' + $perfCsv + '"'), '-y') -WindowStyle Hidden -PassThru
$s.typeperf_pid = $tp.Id
$s.rw_from_provenance = $rwSet
$s.env = [ordered]@{}
foreach ($e in (Get-ChildItem Env: | Where-Object { $_.Name -like 'RW_*' -or $_.Name -like 'PYTHON*' -or $_.Name -like 'NUMSIM*' -or $_.Name -like '*_NUM_THREADS' -or $_.Name -like 'NUMBA*' -or $_.Name -like 'NPY_*' -or $_.Name -like 'OPENBLAS_*' -or $_.Name -like 'MKL_*' } | Sort-Object Name)) { $s.env[$e.Name] = $e.Value }
$s.other_python_vissim_at_start = @(Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(python|Vissim|cscript)' } | ForEach-Object { [string]$_.ProcessId + ' ' + $_.Name })
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
if ($Priority -eq 'BelowNormal') { try { $proc.PriorityClass = [System.Diagnostics.ProcessPriorityClass]::BelowNormal } catch {} }
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
