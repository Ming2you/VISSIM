# Actual 150-second observer failure and transport correction

The first observer smoke `codex_contract_observed_nc_s13_1050_20260910` stopped at 150 seconds on exact head geometry validation. All 235 head IDs, links, lanes and SG bindings match the pinned INPX. 116 positions differ only by VBS `CStr(CDbl(...))` transport precision; the largest difference is 4.55e-12 m. All 235 recorded positions equal the actual VBS serializer output and Python's 15-significant-digit canonical value exactly.

The installed consumer now canonicalizes only the expected INPX position to that serializer precision and still compares exactly. It adds no distance tolerance. Changed identity, NaN/bool and even one serialized coordinate unit remain rejected. No network, VBS, collector, input or configuration was changed by this correction.

The original raw 150-second state, preceding action, manifest and failed configuration are retained byte-exact in `fixtures/observer_precision_failure_v1.zip`. Tests extract a separate copy and relocate only path aliases. Before correction, canonical initialization reproduced the error. After correction, the same actual state/config/action initialized successfully with unchanged input bytes, valid window and zero capacity installation (the first eligible observations await a second window).

Validation: 4 new actual-fixture/serializer/tamper tests plus the existing 11 installed observer tests passed (15 total, 3.633 s). The serializer harness used actual VBS functions and fake COM only; no VISSIM or MPC was started. Source hashes and precise evidence are in `observer_head_precision_failure.json`. The stopped run is not a successful 1050-second smoke; completion and trajectory QA belong to the separate v2 retry.
