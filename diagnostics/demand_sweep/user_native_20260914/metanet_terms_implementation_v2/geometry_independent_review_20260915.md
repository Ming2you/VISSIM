# Geometry independent review — FAIL

Reviewed 2026-09-15: `GEOMETRY_IMPLEMENTATION.md`, `geometry_source_patch.diff`, `geometry_implementation_checks.json`, the referenced implementation, profile and test source. Read-only source review and artifact hash reconciliation; no tests rerun, native process, network/source edit, or FZP read. The unfinished harness and port/storage changes are excluded.

## Important I1 — the installed local solver can bypass the unsupported-grid guard

Location: `evaluation/controllers/link_predictor.py:242–244`; new guard at `:311–312`.

Trigger: enable `freeway.geometry_profile` with `freeway.segment_lanes=mapping`, while `freeway.local_landing_state` remains absent or false, then enter `WuFaithfulFollower._solve_freeway_agent_local` through the installed runtime hook. `configure()` defaults that flag to false (`link_predictor.py:40`). `selected()` returns the original vendor method before reaching `_freeway_query_setup`, so the new geometry guard does not execute.

The original method directly calls `freeway_substep_local` (`vendor/NumSim-mine/src/controllers/wu_faithful_follower.py:2329`), whose stock, receiving, density, speed and merge calculations still use the scalar `freeway_segment_length_km` (`local_freeway_plant.py:171,194,279,303,318`). It therefore can score a physical-grid state with incompatible continuity lengths rather than failing closed. The component-only contract and explicit local-kernel prohibition are violated even though the currently intended component harness does not take this route.

Required fix: reject variable cell geometry before the `local_landing_state` branch in the installed canonical hook (or an equally comprehensive solver entry point), preserving legacy behavior when geometry is absent. The existing test at `test_physical_geometry.py:173–176` calls `_freeway_query_setup` directly and does not cover this actual dispatch path. Validate the installed solver with the flag both false and true; no vendor edit is necessary.

Critical findings: none. Other Important findings: none. Minor findings: none.

## Evidence supporting the remaining geometry changes

- Both roads have 21 cells. E has 13 cells at four lanes and 8 at three lanes, with the exact boundary at 6841.743 m. W has 7 cells at three lanes and 14 at four lanes, with the exact boundary at 3822.359 m. Minimum cell length is 492.785625 m.
- The canonical accounting path consistently uses the shared per-cell lengths and dynamic lanes for vehicle inventory, receiving storage, density reconstruction, speed propagation and merge-speed loss. Sending uses `rho * speed * lanes` in vehicles/hour. FD parameter rows receive the same lengths, preventing the existing speed wrapper from restoring old lengths.
- Physical observation projection requires all configured cells and matching lengths. Getter and excess-stock paths use the same physical lengths. Buffer support remains explicitly rejected in canonical accounting.
- The joint-owner entry guard at `vissim_stackelberg_adapter.py:12442–12443` is unconditional for the variable-grid flag. The local query guard itself is correct once entered; I1 concerns dispatch before it.
- The submitted checks report 12 passing tests, including exact complete 450 s legacy trajectories at starts 1350 and 3600, both directions. Those tests were reviewed but not rerun. The changed scalar/physical branches preserve the original scalar path when opt-in is absent.
- All six current source hashes exactly match `geometry_implementation_checks.json.source_after_sha256`. The profile file hash matches `3f436574bdfdfcb7f5ea2772a29eca0db58376db48bc123f578a056b9f1ea39f`. Its source-geometry hash also matches the saved seed13 observation geometry. Recomputing the structural fingerprint from those saved physical chains and ports gives `f659b5135f02cbf4a963097356e7bc8ed4f84240e10e826dd740344201881a7b`, equal to the profile. The bounded geometry patch contains no vendor edits, and `git status --short vendor` returned no changed vendor paths.

The loader verifies mapping content and records the physical fingerprint; it does not itself reconstruct current native geometry. As documented, the extractor/caller must compare the actual geometry fingerprint before applying the profile. That unfinished integration is outside this review. The altered native file must not bypass its source guard; an explicitly selected preserved source with the original SHA is a valid distinct provenance basis when recorded.
