# Physical freeway cell geometry

Implemented an opt-in physical grid in the existing accounting and adapter. No vendor code, native network, VSL placement, inputs, routes or signals were changed by this work. The existing dirty adapter was preserved; `geometry_source_patch.diff` is relative to the exact working files captured before this change, not relative to a clean Git checkout.

The selected grid keeps 21 cells in each direction. Each constant-lane section is divided uniformly; the actual lane transition is an exact cell edge. It contains no mixed-lane cells.

| Direction | Physical transition | Cells before / after | Lengths before / after |
|---|---:|---:|---:|
| East | 6841.743 m, 4 to 3 lanes | 13 / 8 | 526.287923 / 492.785625 m |
| West | 3822.359 m, 3 to 4 lanes | 7 / 14 | 546.051286 / 497.010071 m |

The minimum cell length is 492.785625 m. With the retained 10 s model step, the advective ratio at 155 km/h is at most 0.87372. This checks transport resolution; it is not a proof of stability of every nonlinear METANET term. Merely moving the old west transition boundary would have created a 284.5 m cell, which is why the section-wise partition was selected.

Configuration: set `freeway.geometry_profile` to `diagnostics/demand_sweep/user_native_20260914/metanet_terms_implementation_v2/physical_geometry21_v1.json`, retaining `freeway.segment_lanes=mapping`. `adapter.install_freeway_segment_lanes` calls the new `install_freeway_geometry_profile`; callers may also explicitly call the latter after constructing a config. The loader pins the original mapping content, validates all 42 lengths/lanes, sets `freeway_variable_cell_lengths=True` and `physical_vehicle_counts=True`, installs the existing vehicle-count hook, and records profile provenance. Repeated loading is idempotent.

`evaluation.controllers.freeway_geometry.geometry_fingerprint(geometry)` pins physical chains and boundary attachments while ignoring seed, demand, controls and the observation grid. Extraction must compare this fingerprint against the profile before using its new cell edges. The generator used the already completed seed13 physical geometry only; it did not inspect or rescan traffic.

The shared function `freeway_geometry.cell_lengths_km(net, road, count)`, also exported as `area_freeway_accounting.cell_lengths_km(cfg, road, count)`, now supplies:

- continuity vehicle stocks and post-lane-change density coordinates;
- receiving space at the destination cell;
- density updates, METANET speed updates and merge speed losses;
- adapter and `TrafficState` vehicle-count getters;
- VISSIM observation projection and the freeway excess-stock diagnostic.

Cell FD rows receive the same `segment_length_km`, preventing the existing speed wrapper from reintroducing another length. Native observation projection rejects missing cells or an old-grid length instead of silently accepting it. The original scalar length remains untouched and is used exactly when the opt-in is absent. No buffer cells are introduced.

Internal flow ledgers retain their vehicle-event definition. Ramp, off-ramp and terminal flow amounts are not rescaled by cell length. Cell conservation uses the new N coordinates and the same accepted transfers; freeway residence still uses end-of-substep N times the original 10 s interval.

Changed port assignments (zero-based; unchanged physical positions):

| Port | Old cell | New cell |
|---|---:|---:|
| OR_D_E_signal | 13 | 12 |
| OR_D_E_direct | 14 | 13 |
| OR_D_W_signal | 7 | 6 |
| OR_F_W_signal | 12 | 11 |
| RM_C10644 | 13 | 12 |

The component harness/extractor owner must use the regenerated physical ports. Old 30 s cell summaries cannot reconstruct the new N, speed and crossing counts exactly: re-extraction from the existing native FZP is required. A label such as E14 now identifies another spatial interval; before/after local discharge comparisons must fix the physical chain coordinate or explicitly state the changed interval.

Validation completed:

- 12 offline tests in `test_physical_geometry.py` passed: two full legacy 450 s windows; physical lane purity, transition positions, port placement and structural fingerprint; three vehicle-count getters; dynamic lane loss without phantom vehicles; cell conservation with source/merge/off/terminal flows; residence; merge length; receiving length; strict observation projection; malformed profile rejection; idempotence; unsupported-solver guards.
- The legacy windows at 1350 and 3600 s include both directions, every 30 s state and actual boundary-flow row. They match the pre-edit values exactly. The first test attempt detected only the concurrently introduced diagnostic field `dynamic_off_storage=false`; no traffic values changed. That known OFF field was explicitly checked, and the root owner subsequently removed it from the legacy return shape. This was not resolved by widening a numerical tolerance.
- Syntax parsing passed for all six changed/new Python files, `git diff --check` found no whitespace errors, and the real `configure_freeway_runtime` opt-in call passed.

Supported scope remains the canonical freeway component. The vendor local follower still uses scalar continuity lengths. Both `link_predictor._freeway_query_setup` and `adapter.run_joint_owner_decision` explicitly reject this new geometry until that local kernel is updated and checked. They do not affect old configurations. This work therefore does not claim that the full GNE controller has been migrated. Native VSL positions and writer mappings also remain unchanged; applied native commands must be projected by physical position when comparing a subsequent VSL trial.

Independent-review follow-up: the installed `link_predictor.install.selected` wrapper could bypass `_freeway_query_setup` when `local_landing_state=False`, the default setting. A regression test first reproduced that unauthorized scalar-kernel call. The wrapper now rejects variable geometry before either branch. Only the new targeted test was rerun: it passes and also proves that the non-opt-in default still calls the original solver exactly once. The initial 12 passing tests were not needlessly repeated. This is an additional 13th test, recorded separately in the checks JSON.

Artifacts: `physical_geometry21_v1.json`, `build_physical_geometry.py`, `test_physical_geometry.py`, `legacy_before.json`, `source_before.zip`, `geometry_source_patch.diff`, and `geometry_implementation_checks.json`. Existing frozen sources and results remain available in the parent's baseline archive.
