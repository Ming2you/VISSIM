# A0 timeout-key check: T=900 replay on env_hsw with a tuning copy whose only change is
# runtime.decision_timeout_sec 1800 -> 2390 (a0 scratch file optimized_config_t2390.json, sha 9365141f...).
# RW_SIGNAL_OBSERVATION_CONFIG_SHA256 follows the tuning sha as the codex watchdog would set it (watchdog:231).
# Compared with out/env_hsw/T000900 (same env, original tuning).
$WORK = 'C:\Users\TRLAB\AppData\Local\Temp\claude\C--Users-TRLAB-Desktop----\491ef689-f002-4605-9dc5-e6d363495788\scratchpad\k8\codex_handoff\work\a0'
$hsw = 'OPENBLAS_CORETYPE=Haswell;NPY_DISABLE_CPU_FEATURES=AVX512F AVX512CD AVX512_SKX AVX512_CLX;NUMBA_CPU_NAME=haswell'
$sha = 'RW_SIGNAL_OBSERVATION_CONFIG_SHA256=9365141f1e210d37a19049aa3b331fa114f054f1778241b6850b9e89a7285142'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WORK 'run_replay_tuning.ps1') -T 900 -Label 'tmo2390_hsw' -ExtraEnv ($hsw + ';' + $sha) -TuningName 'optimized_config_t2390.json' -Note 'timeout key 1800->2390 only, env_hsw'
'done' | Set-Content -Encoding UTF8 (Join-Path $WORK 'tmo.done')
