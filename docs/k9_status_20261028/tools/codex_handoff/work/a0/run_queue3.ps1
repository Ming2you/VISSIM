# A0 queue 3 (2026-10-25 13:17 KST): the PC is idle now (no other python/VISSIM seen). Two back-to-back T=900 replays
# on env_hsw, without and with S1, to (a) measure the decision time with no other-session load and
# (b) separate the S1 time effect from load drift. Strictly one at a time.
$WORK = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\work\a0'
$stateFile = Join-Path $WORK 'queue3.state.txt'
function Note([string]$m) { ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz') + ' ' + $m) | Add-Content -Encoding UTF8 $stateFile }
$hsw = 'OPENBLAS_CORETYPE=Haswell;NPY_DISABLE_CPU_FEATURES=AVX512F AVX512CD AVX512_SKX AVX512_CLX;NUMBA_CPU_NAME=haswell'
$s1 = 'PYTHONPYCACHEPREFIX=D:\VISSIM-merge\k8_gate_trees\codexhandoff\a0\pycache_prefix;NUMBA_NUM_THREADS=2'
$r2 = Join-Path $WORK 'run_replay2.ps1'
Note ('start wrapper_pid=' + $PID)
Note 'env_hsw_idle T=900 start'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $r2 -T 900 -Label 'env_hsw_idle' -ExtraEnv $hsw -Note 'env_hsw repeat, PC idle at launch'
Note ('env_hsw_idle T=900 end exit=' + $LASTEXITCODE)
Note 'spd_hsw_idle T=900 start'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $r2 -T 900 -Label 'spd_hsw_idle' -ExtraEnv ($hsw + ';' + $s1) -Note 'env_hsw + S1 repeat, PC idle at launch'
Note ('spd_hsw_idle T=900 end exit=' + $LASTEXITCODE)
'done' | Set-Content -Encoding UTF8 (Join-Path $WORK 'queue3.done')
Note 'done'
