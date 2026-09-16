# Four-arm native postprocessor readiness

Status: metadata-only and synthetic checks passed; no FZP scanned by this review.

- Driver: `../../native_fixed_profile_v2/analysis/analyze_four_arms.py`; explicit `--experiment` selects v3. Four synthetic tests passed.
- `run_none` completed receipt, exact source network SHA, final 2250-second native log, and command/LDP validation pass.
- Baseline proof is a full 2250-second original-native FZP and LDP comparison with saved/effective SimPeriod 9001. A command-only proof cannot unlock analysis.
- Ω membership audit passes for all 1,236 existing physical links: canonical source ledger pins retained, link/connector sets and from/to topology unchanged, canonical corridors/crossings/terminals rechecked. Actual endpoint geometry and terminal lengths are recorded separately. No old network SHA is replaced.
- Extraction outputs are compatible with `ObservationData`: geometry/profile pin, cells, flows, boundaries, all 16 port stocks/entries/live drains, travel cohorts.
- `model_component` means freeway + eight off connectors + target on-ramp 10490. `component` means freeway + all 16 connectors. Both are alternatives to, never additions to, Ω.
- Native component TTT includes all physical source-link vehicles, including finite negative positions; canonical grid cells exclude negative chain positions. Matched model comparisons must use sampled cell/cohort scope or report that difference.
- Component TTT provides 1-second trapezoid, left and right integrals. A model start-stock integral should not silently be compared as if it used the same integration rule.
- Actual native OFF remains OFF. Head crossings and mainline merges are distinct; LDP state uses event upper-frame time. Known removals cannot become normal TTD.

Execution is held until the root confirms all four native runs have completed. Then each FZP is opened once; partial outputs/failures are preserved. Output target is `results_v1` under this directory.
