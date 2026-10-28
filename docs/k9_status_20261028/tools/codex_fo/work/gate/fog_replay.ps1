# FO gate offline run of ONE decision (T=900, first SDMPC decision) of the codex adapter on FRZ_FO, from a RECORDED B state
# (no VISSIM, no COM). Derived from work/gate1/g1_replay.ps1 (4fa41678..., gate 1 of B). Differences (only these):
#  - code root = FRZ_FO (parameter -Frz, must be under fo\frozen); inputs from fo/gate/pristine/<Src>/T<t6>, outputs under
#    fo/gate/out/<Label>/<Src>/T<t6> and fo/gate/runs/<Src>/T<t6>; source labels b_s31/b_s41/b_s43/b_s31b (B run folders);
#  - default priority BelowNormal (other sessions' work is on this PC; shared-lock rule for heavy jobs);
#  - the collector output is written by Start-Process redirection (UTF-8 text), not by PS 5.1 '>' (which writes UTF-16).
# Same as g1: RW_* = the non-empty RW_* of the run provenance in the input tree (tuning sha must equal the tuning file),
# plain adapter call with the B0/B adapter arguments (--controller wu-link, same mapping/detector mapping/calibration,
# --previous-action-json action_<T-150>.json), cleared NUMBA*/PYTHON*/OPENBLAS/NPY/MKL extras, env_hsw from -ExtraEnv,
# PYTHONHASHSEED=0, python -B, OMP/OPENBLAS/MKL threads 1, PYTHONPATH = deps;FRZ_FO, NUMSIM_REPO_ROOT = FRZ_FO/vendor/NumSim-mine.
param(
  [Parameter(Mandatory=$true)][int]$T,
  [Parameter(Mandatory=$true)][string]$Src,
  [Parameter(Mandatory=$true)][string]$Label,
  [Parameter(Mandatory=$true)][string]$TuningRel,
  [Parameter(Mandatory=$true)][string]$Frz,
  [string]$ExtraEnv = '',
  [string]$Note = '',
  [ValidateSet('Normal','BelowNormal')][string]$Priority = 'BelowNormal',
  [string]$PyExe = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
)
$ErrorActionPreference = 'Stop'
$G = 'D:\VISSIM-merge\k8_gate_trees\codexhandoff\fo\gate'
$CODE = [IO.Path]::GetFullPath($Frz)
if (-not $CODE.StartsWith('D:\VISSIM-merge\k8_gate_trees\codexhandoff\fo\frozen\', [StringComparison]::OrdinalIgnoreCase)) { throw "code root is not under fo\frozen: $CODE" }
$COLLECT = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\work\a0\s5_collect.py'
$PY = $PyExe
$DEPS = 'D:\VISSIM-window264-deps'
$seedOf = @{ 'b_s31' = 31; 'b_s31b' = 31; 'b_s41' = 41; 'b_s43' = 43 }
if (-not $seedOf.ContainsKey($Src)) { throw "unknown source label $Src" }
$sd = $seedOf[$Src]
$decName = 'decisions_sdmpc31_sdmpc9000_s' + $sd
$provName = 'run_provenance_sdmpc31_sdmpc9000_s' + $sd + '.json'
$t6 = '{0:D6}' -f $T
$p6 = '{0:D6}' -f ($T - 150)
$pristine = Join-Path $G ('pristine\' + $Src + '\T' + $t6)
$runT = Join-Path $G ('runs\' + $Src + '\T' + $t6)
$run = Join-Path $runT 'run'
$dec = Join-Path $run $decName
$out = Join-Path $G ('out\' + $Label + '\' + $Src + '\T' + $t6)
if (Test-Path -LiteralPath $out) { throw "output folder exists: $out" }
$tuning = Join-Path $CODE $TuningRel
if (-not (Test-Path -LiteralPath $tuning -PathType Leaf)) { throw "tuning missing: $tuning" }
New-Item -ItemType Directory -Force -Path $out | Out-Null
$statePath = Join-Path $out 'replay_state.json'
$tuningSha = (Get-FileHash -LiteralPath $tuning -Algorithm SHA256).Hash.ToLowerInvariant()
$s = [ordered]@{ T = $T; src = $Src; label = $Label; mode = 'plain'; tuning = $tuning; tuning_sha256 = $tuningSha; py_exe = $PyExe; code_root = $CODE;
  extra_env = $ExtraEnv; note = $Note; wrapper_pid = $PID; priority_requested = $Priority; status = 'preparing' }
function Save-State { [IO.File]::WriteAllText($statePath, ($s | ConvertTo-Json -Depth 5), (New-Object System.Text.UTF8Encoding $false)) }
Save-State
& robocopy.exe (Join-Path $pristine 'run') $run /MIR /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy mirror failed $LASTEXITCODE" }
if (Test-Path -LiteralPath (Join-Path $dec ('action_' + $t6 + '.json'))) { throw 'output already present in working tree' }
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
Save-State
Set-Location -LiteralPath $CODE
$quoted = @($pyArgs | ForEach-Object { '"' + $_ + '"' }) -join ' '
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$proc = Start-Process -FilePath $PY -ArgumentList $quoted -WorkingDirectory $CODE -NoNewWindow -PassThru `
  -RedirectStandardOutput (Join-Path $out 'stdout.txt') -RedirectStandardError (Join-Path $out 'stderr.txt')
$null = $proc.Handle
if ($Priority -eq 'BelowNormal') { try { $proc.PriorityClass = [System.Diagnostics.ProcessPriorityClass]::BelowNormal } catch {} }
$s.python_pid = $proc.Id
try { $s.python_priority = $proc.PriorityClass.ToString() } catch { $s.python_priority = 'unknown' }
Save-State
$proc.WaitForExit()
$exitCode = $proc.ExitCode
$sw.Stop()
$end = Get-Date
try { Stop-Process -Id $tp.Id -ErrorAction Stop } catch {}
$s.exit_code = $exitCode
$s.end = $end.ToString('yyyy-MM-dd HH:mm:ss.fff zzz')
$s.wall_sec = [math]::Round($sw.Elapsed.TotalSeconds, 3)
$s.status = 'collecting'
Save-State
$cp = Start-Process -FilePath $PY -ArgumentList @('-B', ('"' + $COLLECT + '"'), ('"' + (Join-Path $pristine 'run') + '"'), ('"' + $run + '"'), ('"' + (Join-Path $out 'files') + '"')) `
  -NoNewWindow -PassThru -Wait -RedirectStandardOutput (Join-Path $out 'collect.txt') -RedirectStandardError (Join-Path $out 'collect.err.txt')
$s.collect_exit = $cp.ExitCode
$s.status = 'done'
Save-State
