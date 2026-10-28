# A0 queue 2 (2026-10-25). Waits until the speed set has finished, then runs strictly one replay at a time:
#  1) tmo2390_hsw  T=900 : env_hsw, tuning copy with decision_timeout_sec 1800->2390 only (sha 9365141f...),
#                          RW_SIGNAL_OBSERVATION_CONFIG_SHA256 set to that sha (as watchdog:231 would). Baseline = out/env_hsw.
#  2) py31214_base T=4950: codex runtime Python 3.12.14 (same build string as codex current_environment), base env.
#  3) py31214_hsw  T=4950: codex runtime Python 3.12.14, env_hsw.
# Fidelity runs (2, 3) are compared with the codex record; they change the interpreter, not code or config.
$WORK = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\work\a0'
$stateFile = Join-Path $WORK 'queue2.state.txt'
function Note([string]$m) { ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz') + ' ' + $m) | Add-Content -Encoding UTF8 $stateFile }
Note ('start wrapper_pid=' + $PID + ' waiting for speed_set2.done')
while (-not (Test-Path -LiteralPath (Join-Path $WORK 'speed_set2.done'))) { Start-Sleep -Seconds 20 }
Note 'speed set finished; queue starts'
$hsw = 'OPENBLAS_CORETYPE=Haswell;NPY_DISABLE_CPU_FEATURES=AVX512F AVX512CD AVX512_SKX AVX512_CLX;NUMBA_CPU_NAME=haswell'
$cxpy = 'C:\Users\TRLAB\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$r2 = Join-Path $WORK 'run_replay2.ps1'
Note 'tmo2390_hsw T=900 start'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $r2 -T 900 -Label 'tmo2390_hsw' -ExtraEnv ($hsw + ';RW_SIGNAL_OBSERVATION_CONFIG_SHA256=9365141f1e210d37a19049aa3b331fa114f054f1778241b6850b9e89a7285142') -TuningName 'optimized_config_t2390.json' -Note 'timeout key 1800->2390 only, env_hsw'
Note ('tmo2390_hsw T=900 end exit=' + $LASTEXITCODE)
Note 'py31214_base T=4950 start'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $r2 -T 4950 -Label 'py31214_base' -PyExe $cxpy -Note 'codex runtime Python 3.12.14, base env'
Note ('py31214_base T=4950 end exit=' + $LASTEXITCODE)
Note 'py31214_hsw T=4950 start'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $r2 -T 4950 -Label 'py31214_hsw' -PyExe $cxpy -ExtraEnv $hsw -Note 'codex runtime Python 3.12.14, env_hsw'
Note ('py31214_hsw T=4950 end exit=' + $LASTEXITCODE)
'done' | Set-Content -Encoding UTF8 (Join-Path $WORK 'queue2.done')
Note 'done'
