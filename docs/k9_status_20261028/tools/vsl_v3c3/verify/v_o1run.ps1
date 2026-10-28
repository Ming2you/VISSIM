# v_o1run.ps1 - VERIFY_VSL (2026-10-27 KST). One O1 re-check run (v3c3-s43 B state T=1,800) with v_o1probe.py.
# Takes the shared lock heavy.lock (CreateNew, wait/retry 30 s), copies code + pristine input into our own folder under
# D:\VISSIM-merge\k8_gate_trees\vsl_v3c3\verify_o1 (authors' trees read only), sets the run environment from the
# input's run provenance (RW_*), python -B, PYTHONHASHSEED=0, threads 1, BelowNormal. Releases the lock (own token only).
$ErrorActionPreference = 'Stop'
$LOCK = 'D:\VISSIM-merge\k8_gate_trees\heavy.lock'
$V = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\vsl_v3c3\verify'
$PY = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
$DEPS = 'D:\VISSIM-window264-deps'
$SRC_CODE = 'D:\VISSIM-merge\k8_gate_trees\vsl_v3c3\o1o2\codeB1'
$SRC_IN = 'D:\VISSIM-merge\k8_gate_trees\vsl_v3c3\o1o2\pristine\o1_b43_T001800'
$ROOT = 'D:\VISSIM-merge\k8_gate_trees\vsl_v3c3\verify_o1'
$CODE = Join-Path $ROOT 'codeB1'
$RUN = Join-Path $ROOT 'runs\b43_T001800'
$DEC = Join-Path $RUN 'sdmpc\decisions_sdmpc31_sdmpc9000_s43'
$OUTJ = Join-Path $V 'out\o1_recheck_b43_T001800.json'
$log = Join-Path $V 'logs\o1run.log'
function Note([string]$m) { Add-Content -LiteralPath $log -Value ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' KST [pid=' + $PID + '] ' + $m) }
try { (Get-Process -Id $PID).PriorityClass = 'BelowNormal' } catch {}
$token = 'verify_vsl_o1_' + [guid]::NewGuid().ToString()
$deadline = (Get-Date).AddMinutes(90); $have = $false; $waits = 0
while (-not $have) {
  try {
    $fs = [IO.File]::Open($LOCK, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    $b = [Text.Encoding]::ASCII.GetBytes("owner=verify_vsl_o1 token=$token pid=$PID time=" + (Get-Date -Format 'yyyy-MM-ddTHH:mm:ss') + "`r`n")
    $fs.Write($b, 0, $b.Length); $fs.Close(); $have = $true
  } catch {
    if ((Get-Date) -gt $deadline) { Note "lock wait timeout after $waits waits"; exit 9 }
    $waits++
    if ($waits -eq 1 -or ($waits % 10) -eq 0) { $who = ''; try { $who = (Get-Content -LiteralPath $LOCK -Raw) } catch {}; Note ("lock busy, waiting: " + $who.Trim()) }
    Start-Sleep -Seconds 30
  }
}
Note "lock acquired token=$token waits=$waits"
$rc = 0
try {
  & robocopy.exe $SRC_CODE $CODE /MIR /XD __tangentcache__ __pycache__ /NFL /NDL /NJH /NJS /NP | Out-Null
  if ($LASTEXITCODE -ge 8) { throw "robocopy code failed $LASTEXITCODE" }
  & robocopy.exe $SRC_IN $RUN /MIR /NFL /NDL /NJH /NJS /NP | Out-Null
  if ($LASTEXITCODE -ge 8) { throw "robocopy input failed $LASTEXITCODE" }
  $relo = & $PY -B (Join-Path $V 'v_reloc.py')
  if ($LASTEXITCODE -ne 0) { throw "relocation failed" }
  Note ("reloc " + $relo)
  foreach ($rel in @('evaluation\controllers\sdmpc.py','evaluation\controllers\vissim_stackelberg_adapter.py','evaluation\controllers\area_freeway_accounting.py','diagnostics\b0_v3c3\config_b0_v3c3.json')) {
    Note ("sha {0} {1}" -f $rel, (Get-FileHash -LiteralPath (Join-Path $CODE $rel) -Algorithm SHA256).Hash.ToLowerInvariant())
  }
  foreach ($n in @('NUMBA_NUM_THREADS','NUMBA_THREADING_LAYER','NUMBA_CACHE_DIR','NUMBA_DISABLE_JIT','NUMBA_OPT','NUMBA_DEBUG','PYTHONPYCACHEPREFIX','PYTHONHOME','PYTHONSTARTUP','PYTHONPATH','PYTHONOPTIMIZE','PYTHONWARNINGS','PYTHONINSPECT','PYTHONNOUSERSITE','OPENBLAS_VERBOSE','OPENBLAS_MAIN_FREE','NPY_ENABLE_CPU_FEATURES','MKL_CBWR','MKL_ENABLE_INSTRUCTIONS')) {
    if (Test-Path -LiteralPath ('Env:' + $n)) { Remove-Item -LiteralPath ('Env:' + $n) }
  }
  foreach ($item in @(Get-ChildItem Env: | Where-Object { $_.Name -like 'RW_*' })) { Remove-Item -LiteralPath ('Env:' + $item.Name) }
  $tuning = Join-Path $CODE 'diagnostics\b0_v3c3\config_b0_v3c3.json'
  $tsha = (Get-FileHash -LiteralPath $tuning -Algorithm SHA256).Hash.ToLowerInvariant()
  $prov = Get-Content -LiteralPath (Join-Path $RUN 'sdmpc\run_provenance_sdmpc31_sdmpc9000_s43.json') -Raw -Encoding UTF8 | ConvertFrom-Json
  foreach ($p in $prov.env.PSObject.Properties) { if ($p.Name -like 'RW_*' -and [string]$p.Value -ne '') { [Environment]::SetEnvironmentVariable($p.Name, [string]$p.Value, 'Process') } }
  $env:RW_PYTHON = $PY
  if ($env:RW_SIGNAL_OBSERVATION_CONFIG_SHA256 -ne $tsha) { throw "tuning sha mismatch $tsha" }
  $env:PYTHONUTF8 = '1'; $env:PYTHONDONTWRITEBYTECODE = '1'; $env:PYTHONHASHSEED = '0'
  $env:PYTHONPATH = $DEPS + ';' + $CODE
  $env:NUMSIM_REPO_ROOT = Join-Path $CODE 'vendor\NumSim-mine'
  $env:OMP_NUM_THREADS = '1'; $env:OPENBLAS_NUM_THREADS = '1'; $env:MKL_NUM_THREADS = '1'
  $env:OPENBLAS_CORETYPE = 'Haswell'; $env:NPY_DISABLE_CPU_FEATURES = 'AVX512F AVX512CD AVX512_SKX AVX512_CLX'; $env:NUMBA_CPU_NAME = 'haswell'
  $env:V_O1_OUT = $OUTJ
  $adapter = Join-Path $CODE 'evaluation\controllers\vissim_stackelberg_adapter.py'
  $argsList = @('-B', (Join-Path $V 'v_o1probe.py'), $adapter,
    '--state-json', (Join-Path $DEC 'state_001800.json'),
    '--out-action-json', (Join-Path $DEC 'action_001800.json'),
    '--out-action-csv', (Join-Path $DEC 'action_001800.csv'),
    '--mapping-json', (Join-Path $CODE 'evaluation\real_world_modi_control_ver2n21_20260907\control_mapping_ver2n21.json'),
    '--controller', 'wu-link',
    '--detector-mapping-json', 'evaluation\real_world_modi_control_ver2_20260907\detector_local_mapping_ver2_20260907.json',
    '--calibration-json', (Join-Path $CODE 'evaluation\calibration\real_world_prediction_calibration_core17legs4b_20260820.json'),
    '--tuning-json', $tuning,
    '--previous-action-json', (Join-Path $DEC 'action_001650.json'))
  $quoted = @($argsList | ForEach-Object { '"' + $_ + '"' }) -join ' '
  $sw = [Diagnostics.Stopwatch]::StartNew()
  $proc = Start-Process -FilePath $PY -ArgumentList $quoted -WorkingDirectory $CODE -NoNewWindow -PassThru `
    -RedirectStandardOutput (Join-Path $V 'logs\o1run.stdout.txt') -RedirectStandardError (Join-Path $V 'logs\o1run.stderr.txt')
  $null = $proc.Handle
  try { $proc.PriorityClass = 'BelowNormal' } catch {}
  Note ("python pid {0}" -f $proc.Id)
  $proc.WaitForExit(); $sw.Stop()
  Note ("python exit={0} wall={1:N1}s" -f $proc.ExitCode, $sw.Elapsed.TotalSeconds)
  if (Test-Path -LiteralPath (Join-Path $DEC 'action_001800.json')) { Note 'WARNING action file written' }
  $rc = $proc.ExitCode
} catch {
  Note ("ERROR " + $_.Exception.Message); $rc = 5
} finally {
  $c = ''; try { $c = Get-Content -LiteralPath $LOCK -Raw } catch {}
  if ($c -like "*$token*") { Remove-Item -LiteralPath $LOCK -Force; Note 'lock released (own token)' } else { Note 'lock NOT ours at end; left untouched' }
}
Note "done rc=$rc"
exit $rc
