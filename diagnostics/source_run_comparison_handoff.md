# Actual source-aware MPC versus observed NC: comparison CLI

Prepared for `codex_area_sources_beta0_s13_20260910` against `codex_area_observed_nc_s13_20260910`. This is an observation analysis tool. It does not import the adapter, solve an optimization, start VISSIM, or change runtime inputs. All outputs are constrained to a named subdirectory under `diagnostics`.

The new files are `compare_source_run.py`, `render_source_run_comparison.py`, and `test_source_run_comparison.py`. Existing measurement and actuation oracles are imported, not copied; `signal_readback_cadence.py` adds the stricter shared observation-only check without importing the adapter. The production code, active configurations, membership, calibration data, old reports, and run files were not edited.

## Commands

Run from the worktree root with the bundled Python interpreter. Use a fresh output name for each audit so evidence from earlier observations remains distinguishable.

```powershell
$reviewPython = 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
& $reviewPython -X utf8 -m diagnostics.compare_source_run --out diagnostics/source_run_comparison_first
```

The default command reads complete CSV prefixes. Missing or unfinished target observations and decisions remain pending. It does not wait or monitor the simulator. For a completed first interval, use `--start 900 --end 1050`; for the completed full run:

```powershell
& $reviewPython -X utf8 -m diagnostics.compare_source_run --run codex_area_sources_beta0_s13_20260910 --reference codex_area_observed_nc_s13_20260910 --start 900 --end 5400 --measure --focus-window 1050:1350 --focus-window 3150:3450 --out diagnostics/source_run_comparison_complete
& $reviewPython -X utf8 -m diagnostics.render_source_run_comparison diagnostics/source_run_comparison_complete
```

Optional `--preflight-reference <directory-or-CSV>` checks the first requested decision against its explicit reference using the existing oracle. Do not assume that a previous preflight has the same raw observation. Focus windows are bounded to 300 seconds each, read only completed FZP files, and have per-window byte/time budgets. `--measure` performs the existing full-FZP scans for both runs and is intentionally more expensive than the prefix audit.

## Definitions and outputs

- `comparison.json` and `measurement_contract.json` retain source hashes, completion/failure state, seed/network matching, common completed time window, measured differences, command vectors, scoring flags, and SG/ramp/VSL readback checks. A missing intermediate 150-second decision remains a pending interval instead of disappearing from the audit.
- Road/42-cell count and stopped stock use the existing 30-second observations. Slow onset requires count at least 5, speed below 30 km/h, and four consecutive samples spanning 90 seconds. Queue onset uses at least 10 stopped vehicles for 300 seconds. Empty cells are not slow traffic. Positive upstream onset lag is temporal ordering, not an identified shockwave speed.
- `road_curves.csv` covers the existing 13-link bottleneck set, including 10639/10682, 40/420, 70/71 and D/F interchange links. `cell_curves.csv` covers all freeway cells. Stock residence uses a trapezoid on the complete observed time grid. Plots use the same common time window and mask empty-cell speed; stopped plots show the existing trailing five-sample average.
- Actual CSV VSL speeds, meter green seconds, phase greens and offsets are compared separately. Each commanded SG must have one immediate row at each second in `[start,end)` and one post-step row in `(start,end]`; endpoint-only samples cannot establish continuous coverage. The only allowed duplicate is the documented pair of identical immediate ramp rows at interval start (initial action application plus first runtime reapplication), with both original rows retained. All other duplicate/missing/noninteger rows fail. Each VSL write needs both finite class10/class70 readbacks matching the command. RM's encoded rate is not measured physical flow. Zero offsets and unchanged commands are legitimate. The native NC run has no area-MPC scoring contract, so it is not failed for absent area flags. Physical comparisons can be present while actuation remains pending or failed; these are separate fields and must be read together.
- Full `measurement.area_metrics` is the canonical **0 to end** FZP-only measurement. `area_window` is separately sliced from its cumulative/event rows for the requested **900 to 5400** window. Events use destination timestamps in `(start,end]`; observed and terminal-inferred exits remain separate, and unresolved disappearances are never rewarded. The native-FZP phase must not be mixed with post-COM final snapshots.
- Connector scans preserve observed departures versus unique skipped-connector inference. The existing final censored 150-second block is excluded from summary discharge (requested 900–5400 gives connector summary 900–5250). Focus reports preserve existing per-event interval uncertainty and add stopped vehicle front-position extents by physical lane. Those extents do not prove a contiguous queue tail or causal spillback.
- The renderer writes three PNG/SVG pairs and `plot_provenance.json`: freeway speed, physical stopped stock, and actual command changes. No chart is invented without a matched common observed window.

## Validation completed before the live run

`python -X utf8 -m unittest diagnostics.test_source_run_comparison -v`: **12 tests passed**. Coverage includes onset cadence/gaps, empty cells, missing decisions, native-NC handling, wrapped/zero offsets, physical meter encoding, connector censoring, matching seed/network, output/run path restrictions, canonical Omega window event/stock closure, and the reproduced endpoint-only false-PASS case rejected by the strict cadence gate.

`source_run_comparison_nc_self_final` compares completed NC to itself with a real 1050–1200 FZP focus: all numerical road/cell differences are zero; focus event summaries agree; three sampled inventory residuals are zero; source changes are empty. The three PNG/SVG pairs passed visual and SVG-XML checks (the final figures preserve the reviewed axis/layout). `source_run_comparison_pending_v3` demonstrates explicit future-run pending behavior. Its source hashes identify the earlier producer revision; it is retained as historical evidence.

The canonical existing NC measurement was also sliced without rescanning: 900–5400 TTT **5282.9626388889 veh·h**, observed exits **16357**, terminal-inferred exits **7155**, unresolved inside disappearances **393**, stock **1765 to 4670**, sampled closure **0**. These are baseline measurements, not an MPC result.

The new strict readback integration was additionally checked on the completed historical retry1050–1200 interval: **130 SG/ramp groups**, full1s cadence PASS, **66 VSL writes with both class readbacks**, invalid0. `source_run_strict_readback_retry1050.json` records this bounded real-log test. A fresh process confirmed that importing/calling the observation CLI did not import `vissim_stackelberg_adapter`. This is historical actuation evidence, not a result for the new source-aware run.

The combined CLI `--measure` full-FZP path has not yet been rerun for this preparation; it calls the already-used canonical measurement/scanner functions. Full target measurements remain pending until the run completes. Simultaneous changes to several levers cannot be assigned separate causal effects from these comparisons alone.

## Actual four-lever schema correction

The first live 900–1500 prefix exposed `KeyError: cycle_sec` in the new command signature helper. Its synthetic lever test and NC self-comparison had not exercised real signal CSV rows. The actual CSV encodes `offset`, and physical cycle in `signal_sg.green_sec`; there are no `cycle_sec`/`offset_sec` columns. The helper now consumes `signal_timing_oracle.decisions_from_action_rows`, and pins that decoder and `action_csv_schema.py` in its source manifest. No production file changed.

A regression using committed `area_production_preflight/wu-link_t900_beta0_20260909T225309161773Z/action.csv` first reproduced the failure and now checks all 17 signal axes, 66 VSL writes, eight meters, and separate green/offset/VSL/meter changes. The suite now has **13 passing tests**. Original partial `source_run_comparison_1500` is retained; corrected output is `source_run_comparison_1500_fixed`. Its common 900–1500 observation window is comparable, all four completed actuation intervals pass, and analysis source changes are empty. The full-run completion/measurement fields correctly remain pending while simulation continues.
