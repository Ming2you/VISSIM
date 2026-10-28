# A0 speed-candidate set (2026-10-25 resume). One heavy job at a time, strictly sequential.
# Candidate S1 = bytecode prefix cache (PYTHONPYCACHEPREFIX, pre-filled by compileall) + NUMBA_NUM_THREADS=2.
# Neither changes code bytes or config. Each replay is compared with THIS PC's own baseline replay under the same env.
#   spd_hsw : env_hsw numeric env + S1, T = 900, 2700, 4950  (baseline = out/env_hsw)
#   spd_base: base env + S1, T = 900                         (baseline = out/base_rep2)
$WORK = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\work\a0'
$PREFIX = 'D:\VISSIM-merge\k8_gate_trees\codexhandoff\a0\pycache_prefix'
$stateFile = Join-Path $WORK 'speed_set2.state.txt'
function Note([string]$m) { ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss zzz') + ' ' + $m) | Add-Content -Encoding UTF8 $stateFile }
Note ('start wrapper_pid=' + $PID)
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WORK 'run_compileall.ps1')
Note ('compileall ' + (Get-Content -Encoding UTF8 (Join-Path $WORK 'compileall.state.txt') -Raw).Trim())
$hsw = 'OPENBLAS_CORETYPE=Haswell;NPY_DISABLE_CPU_FEATURES=AVX512F AVX512CD AVX512_SKX AVX512_CLX;NUMBA_CPU_NAME=haswell'
$s1 = 'PYTHONPYCACHEPREFIX=' + $PREFIX + ';NUMBA_NUM_THREADS=2'
foreach ($t in @(900, 2700, 4950)) {
  Note ('spd_hsw T=' + $t + ' start')
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WORK 'run_replay.ps1') -T $t -Label 'spd_hsw' -ExtraEnv ($hsw + ';' + $s1) -Note 'S1 (bytecode prefix cache + NUMBA_NUM_THREADS=2) on env_hsw'
  Note ('spd_hsw T=' + $t + ' end exit=' + $LASTEXITCODE)
}
Note 'spd_base T=900 start'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WORK 'run_replay.ps1') -T 900 -Label 'spd_base' -ExtraEnv $s1 -Note 'S1 (bytecode prefix cache + NUMBA_NUM_THREADS=2) on base env'
Note ('spd_base T=900 end exit=' + $LASTEXITCODE)
'done' | Set-Content -Encoding UTF8 (Join-Path $WORK 'speed_set2.done')
Note 'done'
