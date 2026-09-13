# Four recorded inputs for performance equivalence

Prepared without running the model or VISSIM. Source check at `dd13e0810fe4fc5582a863cb19839fe0f2464d9f` on 2026-09-10. Exact paths, raw SHA256 values, expanded commands and source checks are in `performance_replay_four_states_20260910.json`.

Each row defines its own before/after pair. The initial row tests v4 head observations; the later rows test an explicitly head-OFF configuration. Their wall times must not be treated as a single experiment that changes only traffic state.

| Recorded condition | Exact run and time | Previous action | Replay family, beta | Physical evidence and limit |
|---|---|---|---|---|
| Initial | `codex_contract_observed_nc_s13_1050_v2_20260910`, 900 s | 750 s | `contract_candidate_configs_v4`, 300 | Ω 1,763; FW 841; E8 19 vehicles, 112.11 km/h. Real 750–900 head window. New v4 resource floors start cold; no later warm history is invented. Only 150 s of subsequent actual observations exist. |
| Congestion onset | `codex_area_sources_beta0_s13_20260910`, 1500 s | 1350 s | `performance_head_off_baseline_v1`, 300 | Ω 2,917; FW 1,177; E8 87 vehicles, 22.33 km/h. Actual route-bearing snapshot, no head window. |
| Severe congestion | `codex_area_sources_beta0_s13_20260910`, 3300 s | 3150 s | `performance_head_off_baseline_v1`, 300 | Ω 5,126; FW 2,973; E8 263 vehicles, 2.42 km/h. |
| Partial recovery at W0 | `codex_area_sources_beta0_s13_20260910`, 4950 s | 4800 s | `performance_head_off_baseline_v1`, 300 | Ω 5,285; FW 3,267; W0 36.63 km/h, but E8 remains at 1.81 km/h. There is no demonstrated network-wide recovery. W0 slows again at 5070 s; 450 s of actual follow-up exist. |

From the worktree, these are the baseline commands. They are prepared commands, not executions performed for this report.

```powershell
$perfPython = 'C:/Users/alsrj/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
& $perfPython -X utf8 -m diagnostics.run_area_production_preflight --run codex_contract_observed_nc_s13_1050_v2_20260910 --time 900 --beta 300 --controller wu-link --config-directory contract_candidate_configs_v4 --resource-counters --timeout-sec 1800 --execute
& $perfPython -X utf8 -m diagnostics.run_area_production_preflight --run codex_area_sources_beta0_s13_20260910 --time 1500 --beta 300 --controller wu-link --config-directory performance_head_off_baseline_v1 --resource-counters --timeout-sec 1800 --execute
& $perfPython -X utf8 -m diagnostics.run_area_production_preflight --run codex_area_sources_beta0_s13_20260910 --time 3300 --beta 300 --controller wu-link --config-directory performance_head_off_baseline_v1 --resource-counters --timeout-sec 1800 --execute
& $perfPython -X utf8 -m diagnostics.run_area_production_preflight --run codex_area_sources_beta0_s13_20260910 --time 4950 --beta 300 --controller wu-link --config-directory performance_head_off_baseline_v1 --resource-counters --timeout-sec 1800 --execute
```

The runner selects the last actual action strictly before the snapshot. All four selected paths were checked against the previous-action entries above. The snapshot, previous action and config payload SHA must remain exact for each pair. `--resource-counters` records exit counters; normal wall comparisons must not enable cProfile or candidate tracing. Detailed candidate equivalence belongs to a separately instrumented pair.

For the optimized run, preserve the same command and inputs, changing only `--config-directory` to a separately prepared after-family with byte-identical config payloads and the reviewed new source pins. No after-family was created here. Do not rewrite this baseline manifest or bypass the runner's stale-source rejection after a source change.

The original OFF v3 source manifest has four stale pins: `local_signal_service.py`, `runtime_setup.py`, `urban_flow_accounting.py`, and `vissim_stackelberg_adapter.py`. It remains preserved. The new OFF baseline copies all four beta config files byte for byte and changes their provenance manifest only. Compared with current v4, the only config leaf differences are `urban.capacity.head_observation.enabled=false` and absence of `urban.capacity.head_resource_contract`.

At preparation, v4 passed all 137 source pins. The auxiliary OFF family passed 138: the current 137-source contract plus the original OFF overlay, retained explicitly for provenance. Two pinned head-resource data files are unused by this OFF payload. `performance_head_off_baseline_v1/copy_proof.json` records the original/new manifest relationship, exact copies, source differences and zero source changes. Its manifest SHA256 is `4dff9693849f1a70cd476cd072c71c98ff5ebccad80ebfeff2fc6bdfc025b766`.

Before accepting speed results, require successful controller completion, no fallback or serial price retry, expected workers closed, unchanged input/source hashes, exact action CSV and equal normalized realized controls, selected candidate, prices and objective. Whole output action JSON bytes may differ because timing and provenance fields change; its SHA is retained as evidence, not used as a semantic equality test. Prior-action input bytes must match exactly. The existing profiled 900 s action is a retained output reference, not a normal wall-time baseline.
