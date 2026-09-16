# Port dynamics independent review — FAIL pending I1

Scope: changes to `metanet_calibration_v1/canonical_harness.py`, `boundary_factory.py`, and `extract_observations.py` relative to those exact files in `baseline_frozen_sources.zip`. The calibration driver and full urban forecast are excluded. No source, raw INPX or process file was changed; no raw FZP was read. One small read-only Python `-B` fault injection was run in memory.

## Important I1 — nonfinite drainage becomes a valid zero-service boundary

Locations: `boundary_factory.py:128–132` and `canonical_harness.py:70–75`.

The factory creates `off_drain_vph` but omits it from its finite/nonnegative boundary validation. `DelayedPort.release()` then evaluates `max(0., service_vph)`, which silently converts NaN to zero. A malformed drainage observation consequently changes a connector into a blocked boundary while returning an apparently successful forecast, contrary to the explicit invalid-input/failed-rollout contract.

Concrete reproduction used the new seed13 observations, cutoff 900, history forecast, and `port_profile.json`. Only the in-memory `departures_veh` values for connector 10481 at times 780, 810, 840, 870 and 900 were replaced by the string `nan`. The factory returned a NaN drain. The unmodified E-direction 450-second rollout returned 315 cell rows and 180 port rows without exception, with connector 10481 cumulative departures equal to 0.0 and all reported port stocks finite. No stored observations were changed.

Required fix: reject nonfinite and negative drainage explicitly when constructing the new boundary, and enforce a finite/nonnegative service contract before `DelayedPort.release()` mutates stock. The new port constructor/admission inputs should use equivalent explicit validation so NaN cannot bypass comparison-based checks. Add a targeted invalid-drain regression; zero service remains a valid, distinct value.

Current observations contain no such nonfinite values; this finding concerns the new fail-closed contract, not evidence that the current traffic extraction was corrupted. Critical findings: none. Other Important findings: none. Minor findings: none.

## Normal-data evidence and model limits

- Both seed13 and seed17 have 4,800 port rows and 300 position-cohort snapshots. Cohort counts, port end stocks and corresponding boundary snapshot stocks agree exactly at every observed cutoff. Nonfinite cohort fields, unresolved absences and nonzero conservation residuals are all zero for both seeds.
- Across the 16 physical ports, seed13 has 28,013 arrivals and 27,895 departures; seed17 has 28,124 arrivals and 28,014 departures. The ending stocks account for the differences. `PortObserver` records an observed transition to another link as departure and preserves disappearance as unresolved evidence rather than drainage.
- The model drains available cohorts, computes remaining storage, then admits the actual captured freeway off-flow once. No duplicate admission or ordinary-data stock loss was found. Initial cohorts enter once at the cutoff. Newly admitted cohorts use the end-of-step clock plus travel time; this is the documented conservative discrete delay, not instantaneous passage.
- History mode accesses completed port exit intervals ending at or before cutoff and the cutoff cohorts. Conditioned mode explicitly uses future measured exits. No new future-state reset or hidden future drain access was found in the history path.
- The fixed travel profile uses all seed13 trips; `CALIBRATION_PROTOCOL.json` correctly labels temporal checks descriptive and seed17 a development check rather than a fresh independent holdout. External exit rates remain a drainage-service proxy. Connector-only moving/ready stocks do not constitute a full urban signal or downstream queue forecast.
- Verified-network relocation still requires the exact prepared receipt SHA before extraction and rechecks it afterward. The original path/current SHA/expected SHA and selected artifact are recorded. Actual physical geometry must match the profile fingerprint, with homogeneous physical lanes checked before extraction. The extractor source snapshot and post-pass source equality guard are retained.

Reviewed source SHA256 values: harness `2651fc847913b7d89e357c19bb9453ab417475051922e6d332558b755bf46e13`; factory `d0a8ba4c3ff7c94772a1b67cc3cbee6d918b09d594ff61e24745d1d0ca921af0`; extractor `4ab8df66ca842021e374ea22b15fb96c876a6e27284097696bdc3efc6100c8f2`.

## Geometry review follow-up — PASS

The prior Important geometry finding is resolved. `link_predictor.selected()` now rejects `freeway_variable_cell_lengths` before either local solver branch. The added installed-hook regression verifies the default `local_landing_state=False` rejection and preserves exactly one original call with geometry disabled. The updated checks record failure before the fix and success afterward. This scoped follow-up used source/report inspection and did not rerun the geometry tests.
