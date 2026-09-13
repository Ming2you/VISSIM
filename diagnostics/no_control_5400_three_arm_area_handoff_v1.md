# NC5400 area measurement producer: ready, no actual analysis executed

`measure_no_control_5400_three_arm_area.py` reads the new driver's receipt at `diagnostics/no_control_network_arms/r01/manifest.json`. It refuses to start before all three arms have status `passed`, exit 0, valid process/readback gates and the batch has `all_three_passed`, `completed=true`, `valid=true`, `source_changes=[]`.

The intended actual directories come from that receipt: `codex_nc5400_r01_baseline_s13`, `codex_nc5400_r01_lcd10635_2000_s13`, and `codex_nc5400_r01_upstream1135_s13`. No run is launched or inferred from a partially written directory.

After the parent confirms completion, from the review worktree:

```powershell
& 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B -X utf8 diagnostics/measure_no_control_5400_three_arm_area.py `
  --manifest diagnostics/no_control_network_arms/r01/manifest.json `
  --out diagnostics/no_control_5400_three_arm_area_v1
```

The output directory must not exist. A failed analysis preserves its partial output and requires a new output name; it does not overwrite evidence.

The unchanged `scripts/measure_control_area.py` runs once per arm with `--fzp-only --end-sec 5400`. This means one FZP **parsing** pass per arm, plus that canonical tool's existing full-byte SHA read. The new producer does not parse or rescan FZP itself. All later calculations read the small cumulative area CSV. This is observational measurement, not a model or timing benchmark.

## Outputs and checks

- `comparison.json` and `windows.csv`: whole 0–5400; six 900-second windows; supplementary 750–900 and 900–1050. Windows use events `(start,end]` and cumulative TTT differences, independently recomputed with left/right and trapezoid integration. All six main windows must sum to the full result; every individual and aggregate stock closure must be zero.
- Per arm: canonical `area_metrics.json`, `area_timeseries.csv`, `physical_link_residence.csv`; exact command/stdout/stderr; `membership_analysis_only.json`; `observed_outside_exit_pairs.csv`; and preserved native-error evidence/raw bytes.
- The original physical partition remains 635 inside / 601 outside, with terminals 24 and 120. All 1236 physical link XML elements must match between variants after normalizing only connector 10635's allowed lane-change distance. Only the analysis copy's network path/SHA binding changes; the original membership and all inputs remain untouched.
- Alive inside→outside crossings count as TTD. Every reported observed exit pair is checked against the physical partition. Internal urban/freeway/ramp transitions do not count as entry or exit. All eight onramps and six offramps are internal; the two external offramps 10479→125 and 10645→123 remain legitimate exit paths.
- Exactly 5400 FZP frames at times 1…5400, one-second intervals, no gaps, no final COM replacement, and no extrapolated tail are required. The frame at 5400 is censored: its remaining vehicles do not become exits. The initial empty-network assumption is inherited from the canonical tool.
- Full TTT must equal the sum of physical inside-link residence. Terminal and unresolved totals must match their per-link sums. First appearances inside remain distinct from observed boundary entries and are not relabeled as proven internal generation.

## Native deletion evidence remains separate

The producer reuses the existing native ERR parser on only the canonical watchdog's preserved `vissim_network.err` and `vissim_simulation_001.err` inside each completed run. It never reads the overwrite-prone live network ERR or mistakes WSH `.txt.err` for native warnings. Raw bytes, source SHA, complete-line-prefix audit, unparsed warnings and event details are preserved. Both expected files, complete tails, no unparsed removal lines and no duplicate removal records are needed for full deletion aggregates; missing/ambiguous evidence produces an incomplete status and null aggregate, not zero loss.

Native removal counts are grouped by inside nonterminal / inside terminal / outside and native warning time windows. They are **not yet matched by ID/time to the canonical FZP disappearance events**. The report sets that claim to false. Earlier genuine outside exits by a subsequently removed vehicle remain valid; no ID blacklist or automatic TTD subtraction is performed. Unknown inside disappearances already contribute zero TTD, while shortening observed stock and TTT. A native deletion at terminal 24/120 raises a review flag for the separate terminal inference; it is not silently reclassified.

The source pins cover the producer, reused measurement/parser helpers, physical membership and its original sources, exact variant INPX files, completed driver receipt, per-run provenance/logs and native ERR bytes. The driver's runtime source pins are retained as historical provenance; temporary signal-clock swaps during an unrelated replay are neither consulted nor presented as area-measurement dependencies.

Six small in-memory tests passed before handoff: six-window accounting with a prior valid exit and later unknown loss; missing/duplicate frame rejection; censored-tail rejection; contradictory event/cumulative rejection; rejecting an internal transfer mislabeled as outside TTD; and a running-batch guard that stops before measurement. They do not execute the canonical CLI, read actual-run FZP, import a traffic model or access COM. Actual three-arm measurement remains pending the parent's completion notice.
