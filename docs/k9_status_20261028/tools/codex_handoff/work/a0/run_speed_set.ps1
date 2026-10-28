# Sequential speed-candidate replays (one heavy job at a time): compileall prefix, then T=900, 2700, 4950.
$WORK = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\work\a0'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WORK 'run_compileall.ps1')
$extra = 'OPENBLAS_CORETYPE=Haswell;NPY_DISABLE_CPU_FEATURES=AVX512F AVX512CD AVX512_SKX AVX512_CLX;NUMBA_CPU_NAME=haswell;PYTHONPYCACHEPREFIX=D:\VISSIM-merge\k8_gate_trees\codexhandoff\a0\pycache_prefix;NUMBA_NUM_THREADS=10'
foreach ($t in @(900, 2700, 4950)) {
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WORK 'run_replay.ps1') -T $t -Label 'speed_b' -ExtraEnv $extra -Note 'env_hsw + bytecode prefix cache + NUMBA_NUM_THREADS=10'
}
'done' | Set-Content -Encoding UTF8 (Join-Path $WORK 'speed_set.done')
