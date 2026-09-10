The reusable first-interval audit is ready. It uses the installed canonical model, one recorded action and one 150 s endpoint; it never starts VISSIM or an optimizer search.

From the review worktree, after the run has written its 1050 s paused state and an FZP row later than 1050 s:

```powershell
& 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -X utf8 diagnostics/audit_live_prediction_interval.py --run codex_area_sources_beta0_s13_20260910 --config diagnostics/area_candidate_configs/n7_area_beta0.json --output-prefix diagnostics/source_interval_900_1050
```

Missing initial/action/final files or an unclosed live FZP interval return `pending` with exit code 2 and create no report. Complete audits now write a JSON, Markdown report, `_sources.csv`, `_cells.csv` and `_cell_trace.csv`; existing outputs are never replaced. Use another output prefix for another audit. A complete interval whose actuation audit fails exits 1 with the evidence retained. Source/config, action serialization, timestamp, closure or input-mutation failures raise explicitly.

The normal mode checks the executed run’s source manifest and candidate config hash. It pins actual state, previous action, action JSON/CSV, run provenance, model code and referenced evidence before/after replay. It also calls the canonical CSV writer into a memory stream: every physical column must match the recorded CSV. The replay’s four physical lever vectors must stay unchanged at every freeway substep. Only after prediction finishes are the future state and trajectories read.

The report separates:

- Ω, freeway and remaining Ω (urban plus ramps) endpoint stocks; paused COM and 1 s FZP are distinct observation phases.
- Ω/freeway/urban residence and the magnitude of component-error cancellation. Model freeway residence uses its actual 10 s post-step convention; physical residence uses 1 s trapezoidal integration, with left/right alternatives retained.
- Observed outward crossings, inferred terminal departures and unresolved interior disappearances. Reentry is a new observed boundary entry, not source generation. Terminal inference and missed subsecond excursions remain explicit limitations.
- Each of the ten native internal inputs’ desired demand, model admission, unadmitted demand, source-road first appearance, source stock/stopped count and finite model target occupancy. Target storage can span more than its input road, so those stock scopes are explicitly distinguished. The full Ω generation dictionary also includes existing shared/internal sources outside these ten native inputs.
- Actual SG/meter one-second immediate/post-step readbacks, VSL distribution readbacks and the exact physical command CSV. Every second is required; gaps, noninteger timestamps, NaN and duplicates fail. The sole documented exception is exactly two identical immediate ramp rows at the interval start, caused by ApplyActionCsv followed by ApplyRuntimeRampMeters. Raw duplicate rows, keys, indices and rationale remain in the report. VSL readback requires both finite DesSpeedDistr(10)/DesSpeedDistr(70) values and does not claim hard vehicle speed compliance.

The first-seen source count is attributed to an input only if the pinned network gives that road no incoming connectors and exactly that input. It is an admitted-input lower bound under complete recording and unique vehicle IDs; vehicles crossing a short source between samples remain unattributed. Reappearance after a sampled disappearance is counted separately. Desired native volume is not substituted for actual admission.

Validation completed:

- `diagnostics.test_live_prediction_interval`: 15 focused regressions pass. They cover crossing/reentry, terminal versus interior loss, source first appearance versus reappearance, complete final timestamp blocks, partial rows, record ordering, changed measured byte ranges, aggregate-error cancellation, missing/duplicate/noninteger/nonfinite signal rows and finite two-value VSL readbacks. The initial ramp reapplication exception is separately tested against conflicting, middle-second, urban and threefold duplicates. Added cell tests preserve physical/model density geometry, keep empty-cell speed unavailable, reject mismatched cell axes and detect a predicted recovery while the observed endpoint remains congested.
- `diagnostics/source_interval_cli_nc_final_validation.json` and adjacent Markdown/CSV: installed canonical 900–1050 s replay and bounded FZP measurement complete in 17.75 s. Initial snapshot/action/forecast remain byte-identical in memory; Ω stock and flux close; 151 frames are complete; selected raw byte ranges rehash exactly; source changes during the audit are zero. Canonical serialization matches the recorded 74 physical NC command rows.
- This is deliberately `validation_only`: the historical NC model source differs from the current model, and its CSV contains no controlled signal plan. `replay_matches_executed_model` and `executed_command_audit_valid` are both false. These results validate diagnostic execution, not the predictive accuracy or performance of the forthcoming MPC run.
- `diagnostics/source_interval_900_1050.json` and adjacent Markdown/CSV: the actual new run passes in 19.25 s. Executed source/config hashes match; no source/input byte changes occur; the canonical writer matches all 213 physical command rows. All 130 signal/ramp groups have complete one-second coverage and valid requested/readback states. Eight identical start-ramp reapplications are explicitly retained; 66 VSL rows each have two finite matching values. The model uses the actual previous action at 750 s, actual raw state at 900 s and actual chosen action at 900 s. The FZP measurement reads 21.8 MB by seek, observes the complete 1051 s lookahead, and hashes the selected 424,035 rows.

The actual first interval still has substantial predictive error: Ω residence is 85.025271 model versus 79.918056 physical veh·h. FW error is +6.594525 and urban/ramp error is −1.487310 veh·h. Final Ω stock is 2306.743006 model versus 2080 paused COM vehicles: FW error +259.087207 and urban/ramp error −32.344202 vehicles. Model TD is 442.756257 versus 483 observed crossings plus 227 terminal-inferred departures; four interior disappearances remain unresolved. These are one-interval observations, not a performance or causal ablation claim.

The next actual 1200–1350 s interval is saved separately as `diagnostics/source_interval_1200_1350*`. It passes the same executed-source, held-command, readback, payload-immutability and conservation checks in 20.438 s. `_cells.csv` contains 42 endpoint comparisons; `_cell_trace.csv` contains 672 model rows (42 cells × initial plus 15 ten-second states). JSON snapshots now copy model speed, density and effective lane vectors without changing state.

E8 is initialized at the observed 36.173 km/h, but predicts 96.116 at 1350 s versus observed 40.485 (+55.631 km/h); predicted N is 33.313 versus 66. E9 starts at observed 51.287 and predicts 84.791 versus observed 43.168 (+41.623 km/h); N is 30.367 versus 26. Both model cells cross 60 km/h at their first ten-second step, whereas both observed endpoints remain below 60. This threshold is a diagnostic convention; exact observed recovery/onset times are not inferred from two endpoints. Across all 42 cells, speed MAE is 18.176 km/h and signed bias is −7.291 km/h, so slower predictions elsewhere partly conceal these local positive errors. Native density uses the COM physical length/lanes; an additional column normalizes observed stock into the model's continuity geometry.

The earlier NC and 900–1050 reports retain their original diagnostic source hashes and bytes; they are not regenerated as if the new cell fields had existed then. The previous stage audit is preserved byte-for-byte as `diagnostics/live_prediction_interval_stage_paths_900_1050.json`. The refreshed current stage audit identifies this history and validates the latest 1200–1350 source inventory.

The earlier `source_interval_cli_nc_validation*` and `source_interval_cli_nc_command_validation*` are preserved development validation outputs. Stage only the final validation set listed below. No historical first-interval result has been overwritten. The old `live_beta0_interval_prediction.py` keeps its historical main/report; only its physical-window function was parameterized and enriched. Its environment setup now occurs inside main, preventing import-side changes to another diagnostic process.

Explicit stage set for this task:

```text
diagnostics/audit_live_prediction_interval.py
diagnostics/test_live_prediction_interval.py
diagnostics/signal_readback_cadence.py
diagnostics/live_prediction_interval_handoff.md
diagnostics/live_beta0_interval_prediction.py
diagnostics/source_interval_cli_nc_final_validation.json
diagnostics/source_interval_cli_nc_final_validation.md
diagnostics/source_interval_cli_nc_final_validation_sources.csv
diagnostics/source_interval_900_1050.json
diagnostics/source_interval_900_1050.md
diagnostics/source_interval_900_1050_sources.csv
diagnostics/source_interval_1200_1350.json
diagnostics/source_interval_1200_1350.md
diagnostics/source_interval_1200_1350_sources.csv
diagnostics/source_interval_1200_1350_cells.csv
diagnostics/source_interval_1200_1350_cell_trace.csv
diagnostics/live_prediction_interval_stage_paths_900_1050.json
diagnostics/live_prediction_interval_stage_paths.json
```

No production module, active config, evidence input or run manifest was modified. This interval keeps source generation and SC15 corrections jointly active; it does not estimate their separate causal effects. Flow's narrow code review found no new blocker. VSL's independent review reproduced the historical trace auditor's missing-cadence false acceptance and NaN VSL acceptance; both are fixed in the new pure shared helper. Neither peer review is presented as an independent full model rerun. `status=complete` denotes a measured interval: callers must also require `executed_command_audit_valid=true` and `replay_matches_executed_model=true`; the CLI exits 1 for a completed interval with invalid actuation.
