# o_run_probe.ps1 - run the O1/O2 plant probe for ONE prepared state (no VISSIM, no COM). vsl_v3c3, 2026-10-27 KST.
# Derived from c_port/vsl/work/v3_run_probes.ps1 (64cf states) and codex_handoff/work/gate1/g1_replay.ps1 (B states):
# mirror pristine -> runs/<label>; RW_* = the non-empty RW_* of the (relocated) run provenance, RW_PYTHON = local python;
# tuning sha must equal RW_SIGNAL_OBSERVATION_CONFIG_SHA256; env_hsw; threads 1; PYTHONHASHSEED=0; python -B;
# BelowNormal; cwd = code root. Windows PowerShell 5.1, ASCII only.
param(
  [Parameter(Mandatory=$true)][string]$Label,
  [Parameter(Mandatory=$true)][string]$Source,
  [Parameter(Mandatory=$true)][int]$T,
  [Parameter(Mandatory=$true)][string]$SpecFile,
  [Parameter(Mandatory=$true)][string]$OutJson
)
$ErrorActionPreference = 'Stop'
$ROOT = 'D:\VISSIM-merge\k8_gate_trees\vsl_v3c3\o1o2'
$O = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\vsl_v3c3\o1o2'
$PY = 'C:\Users\TRLAB\AppData\Local\Programs\Python\Python312\python.exe'
$DEPS = 'D:\VISSIM-window264-deps'
$WRAP = Join-Path $O 'tools\o_probe.py'
try { (Get-Process -Id $PID).PriorityClass = 'BelowNormal' } catch {}
$tun = 'diagnostics\repin_v3c3_review_20261001\urban_rm269\aggregate270\native413_adopted355\'
$map = @{
  'a1'     = @{ code = 'code64'; dec = 'decisions_sdmpc31_sdmpc8100_s29'; prov = 'run_provenance_sdmpc31_sdmpc8100_s29.json'; tuning = $tun + 'optimized_config.json' };
  'joint'  = @{ code = 'code64'; dec = 'decisions_sdmpc31_sdmpc8100_s29'; prov = 'run_provenance_sdmpc31_sdmpc8100_s29.json'; tuning = $tun + 'optimized_config.json' };
  'window' = @{ code = 'code64'; dec = 'decisions_sdmpc31_sdmpc8100_s29'; prov = 'run_provenance_sdmpc31_sdmpc8100_s29.json'; tuning = $tun + 'window_config.json' };
  'off'    = @{ code = 'code64'; dec = 'decisions_sdmpc31_sdmpc8100_s29'; prov = 'run_provenance_sdmpc31_sdmpc8100_s29.json'; tuning = $tun + 'off_config.json' };
  'b31'    = @{ code = 'codeB1'; dec = 'decisions_sdmpc31_sdmpc9000_s31'; prov = 'run_provenance_sdmpc31_sdmpc9000_s31.json'; tuning = 'diagnostics\b0_v3c3\config_b0_v3c3.json' };
  'b41'    = @{ code = 'codeB1'; dec = 'decisions_sdmpc31_sdmpc9000_s41'; prov = 'run_provenance_sdmpc31_sdmpc9000_s41.json'; tuning = 'diagnostics\b0_v3c3\config_b0_v3c3.json' };
  'b43'    = @{ code = 'codeB1'; dec = 'decisions_sdmpc31_sdmpc9000_s43'; prov = 'run_provenance_sdmpc31_sdmpc9000_s43.json'; tuning = 'diagnostics\b0_v3c3\config_b0_v3c3.json' }
}[$Source]
if (-not $map) { throw "unknown source $Source" }
$CODE = Join-Path $ROOT $map.code
$t6 = '{0:D6}' -f $T; $p6 = '{0:D6}' -f ($T - 150)
$pristine = Join-Path $ROOT ('pristine\' + $Label)
$runT = Join-Path $ROOT ('runs\' + $Label)
$dec = Join-Path $runT ('sdmpc\' + $map.dec)
$log = Join-Path $O 'logs\o_run_probe.log'
function Note([string]$m) { Add-Content -LiteralPath $log -Value ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + ' KST [pid=' + $PID + '] ' + $m) }
if (Test-Path -LiteralPath $OutJson) { Note ("skip {0}: output exists" -f $Label); exit 0 }
& robocopy.exe $pristine $runT /MIR /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy mirror failed $LASTEXITCODE" }
$cleared = @('NUMBA_NUM_THREADS','NUMBA_THREADING_LAYER','NUMBA_CACHE_DIR','NUMBA_DISABLE_JIT','NUMBA_OPT','NUMBA_DEBUG',
  'PYTHONPYCACHEPREFIX','PYTHONHOME','PYTHONSTARTUP','PYTHONPATH','PYTHONOPTIMIZE','PYTHONWARNINGS','PYTHONINSPECT','PYTHONNOUSERSITE',
  'OPENBLAS_VERBOSE','OPENBLAS_MAIN_FREE','NPY_ENABLE_CPU_FEATURES','MKL_CBWR','MKL_ENABLE_INSTRUCTIONS')
foreach ($n in $cleared) { if (Test-Path -LiteralPath ('Env:' + $n)) { Remove-Item -LiteralPath ('Env:' + $n) } }
foreach ($item in @(Get-ChildItem Env: | Where-Object { $_.Name -like 'RW_*' })) { Remove-Item -LiteralPath ('Env:' + $item.Name) }
$tuning = Join-Path $CODE $map.tuning
$tuningSha = (Get-FileHash -LiteralPath $tuning -Algorithm SHA256).Hash.ToLowerInvariant()
$prov = Get-Content -LiteralPath (Join-Path $runT ('sdmpc\' + $map.prov)) -Raw -Encoding UTF8 | ConvertFrom-Json
$rw = [ordered]@{}
foreach ($p in $prov.env.PSObject.Properties) { if ($p.Name -like 'RW_*' -and [string]$p.Value -ne '') { $rw[$p.Name] = [string]$p.Value } }
$rw['RW_PYTHON'] = $PY
if ($rw['RW_SIGNAL_OBSERVATION_CONFIG_SHA256'] -ne $tuningSha) { throw ('provenance tuning sha differs from the tuning file: ' + $rw['RW_SIGNAL_OBSERVATION_CONFIG_SHA256'] + ' vs ' + $tuningSha) }
if (-not (Test-Path -LiteralPath $rw['RW_OBS150_DETECTORS'])) { throw ('obs150 detector table missing: ' + $rw['RW_OBS150_DETECTORS']) }
foreach ($k in $rw.Keys) { [Environment]::SetEnvironmentVariable($k, $rw[$k], 'Process') }
$env:PYTHONUTF8 = '1'; $env:PYTHONDONTWRITEBYTECODE = '1'; $env:PYTHONHASHSEED = '0'
$env:PYTHONPATH = $DEPS + ';' + $CODE
$env:NUMSIM_REPO_ROOT = Join-Path $CODE 'vendor\NumSim-mine'
$env:OMP_NUM_THREADS = '1'; $env:OPENBLAS_NUM_THREADS = '1'; $env:MKL_NUM_THREADS = '1'
$env:OPENBLAS_CORETYPE = 'Haswell'; $env:NPY_DISABLE_CPU_FEATURES = 'AVX512F AVX512CD AVX512_SKX AVX512_CLX'; $env:NUMBA_CPU_NAME = 'haswell'
$env:O_PROBE_SPEC = (Get-Content -LiteralPath $SpecFile -Raw -Encoding UTF8)
$env:O_PROBE_OUT = $OutJson
$adapter = Join-Path $CODE 'evaluation\controllers\vissim_stackelberg_adapter.py'
$argsList = @('-B', $WRAP, $adapter,
  '--state-json', (Join-Path $dec ('state_' + $t6 + '.json')),
  '--out-action-json', (Join-Path $dec ('action_' + $t6 + '.json')),
  '--out-action-csv', (Join-Path $dec ('action_' + $t6 + '.csv')),
  '--mapping-json', (Join-Path $CODE 'evaluation\real_world_modi_control_ver2n21_20260907\control_mapping_ver2n21.json'),
  '--controller', 'wu-link',
  '--detector-mapping-json', 'evaluation\real_world_modi_control_ver2_20260907\detector_local_mapping_ver2_20260907.json',
  '--calibration-json', (Join-Path $CODE 'evaluation\calibration\real_world_prediction_calibration_core17legs4b_20260820.json'),
  '--tuning-json', $tuning,
  '--previous-action-json', (Join-Path $dec ('action_' + $p6 + '.json')))
$quoted = @($argsList | ForEach-Object { '"' + $_ + '"' }) -join ' '
$base = [IO.Path]::Combine([IO.Path]::GetDirectoryName($OutJson), [IO.Path]::GetFileNameWithoutExtension($OutJson))
Note ("start {0} src={1} T={2} code={3} tuning_sha={4} spec={5}" -f $Label, $Source, $T, $CODE, $tuningSha, $SpecFile)
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$proc = Start-Process -FilePath $PY -ArgumentList $quoted -WorkingDirectory $CODE -NoNewWindow -PassThru `
  -RedirectStandardOutput ($base + '.stdout.txt') -RedirectStandardError ($base + '.stderr.txt')
$null = $proc.Handle
try { $proc.PriorityClass = 'BelowNormal' } catch {}
Note ("pid {0} {1}" -f $Label, $proc.Id)
$proc.WaitForExit()
$sw.Stop()
Note ("end {0} exit={1} wall={2:N1}s" -f $Label, $proc.ExitCode, $sw.Elapsed.TotalSeconds)
if (Test-Path -LiteralPath (Join-Path $dec ('action_' + $t6 + '.json'))) { Note ("WARNING action file written for {0}" -f $Label) }
exit $proc.ExitCode
