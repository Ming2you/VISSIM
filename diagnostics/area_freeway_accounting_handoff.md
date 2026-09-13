# Freeway control-area events and the vehicle-count geometry defect

The new `evaluation/controllers/area_freeway_accounting.py` records actual selected freeway transfers without changing the vendor equations. The existing adapter and VBS remain untouched. Integration belongs after the urban event hooks and the geometry/FD runtime setup, in both parent and spawned price workers: `area_freeway_accounting.install(adapter, cfg)`.

`control_area_enabled=False` leaves the original methods installed. After installation, calls with a disabled config delegate to the captured original methods. Enabled calls require the candidate-owned ledger. Buffer chains and standalone exogenous ramp updates are explicitly unsupported; the latter lack the urban actual-release provenance. Legacy `freeway_follower.py:518` and `wu_distributed.py:583` call that standalone path; the live LinkAgentWuFollower local plant does not.

| Actual mutation | Event in the new module | Consequence |
|---|---|---|
| Mainline exogenous demand enters virtual origin queue | `external:mainline:FW -> origin:FW`, outside to outside | Zero TTD and zero area TTT for this queue |
| Receiving-limited accepted entry | `origin:FW -> freeway:FW` | Area entry; only the accepted amount |
| Actual urban meter release reaches freeway | `merge_pending:R -> freeway:FW` | Internal handoff; `actual_ramp_release * T_f` |
| Selected terminal outflow | `freeway:FW -> external:terminal:FW` | Actual area departure, independent of `state.freeway_flow` |
| Off-ramp removal | No event here | Urban scheduling owns the single FW-to-OR/direct event |
| Residence | After all off-ramp schedules in each `T_f` | End-of-substep FW stock, matching the existing METANET quadrature |

The two extracted methods resolve helpers from their canonical `_mn` and `_cp` modules at call time. This preserves installed lane, FD, speed and capacity helpers without storing a stale segment context. There is no production AST execution. Pinned source-method hashes and trajectory comparisons guard equation drift. `TrafficState.copy()` already deep-copies the ledger; no additional copy wrapper is installed.

The private methods preserve legacy TTT and diagnostics, including `include_ramp_queue_ttt=True`. The separate area ledger supplies the new objective. The handoff reservoir `merge_pending:*` is excluded from residence because it is a reservation alias between urban release and freeway update. This is the existing nested model's discrete quadrature, not an assertion of exact microscopic residence times.

## Count defect and its measured size

The observation projector is not the source of the large error. `traffic_state_from_vissim` divides each observed count by its row length and the configured cell lane count, and writes that lane count into `freeway_effective_lanes` (adapter lines 9460–9474 at preparation time). But `_freeway_vehicle_count_by_link` reads the nonexistent `state.freeway_lanes`; its fallback counts every cell as the network scalar 4 lanes. The calibration-installed `TrafficState` getter repeats the same error. Both also clamp effective lanes to at least 1, which is wrong for fractional spillback/incident lanes.

Read-only n7 reference at 900 seconds, using the current shared runtime:

| Count / residual, vehicles | FW_W | FW_E |
|---|---:|---:|
| Raw observed count | 468 | 373 |
| Actual continuity stock | 468.076578 | 372.938986 |
| Old adapter helper stock | 541.755299 | 404.933752 |
| Old helper minus continuity | +73.678721 | +31.994766 |
| 10-second old-helper stock change minus actual flux | +1.866083 | -1.846434 |
| 10-second continuity stock change minus actual flux | 0 | 0 |

The 105.673486-vehicle excess comes from the wrong lane field. The smaller observation/continuity gap comes from row lengths W=0.513357 km and E=0.513525 km versus the shared model continuity length 0.513441 km. The raw observation can be reconstructed exactly with its original row lengths and `freeway_effective_lanes`.

`diagnostics/freeway_count_geometry.patch` gates both count-getter corrections on the explicit `freeway.physical_vehicle_counts=true` setting. Enabled getters read `freeway_effective_lanes` and preserve positive fractional lanes down to the same `1e-9` floor as continuity. An absent or false flag preserves the original field and 1-lane floor, so the historical baseline remains reproducible. `runtime_setup.configure_freeway_runtime` carries an explicitly supplied boolean onto the network before state projection; spawned workers read that same network value. The flattened corrected arm is `diagnostics/freeway_counts_n7_config.json`. The patch changes no model updates, signal actions, VSLs, calibration values or the remaining length mismatch. At n7's uniform configured length, enabled getters agree with continuity and its actual flows. The adapter patch remains unapplied during the live run.

Area seeding and closing-stock checks should use `area_freeway_accounting.continuity_vehicle_counts(state, cfg)`. It implements the exact stock in the current continuity equation directly, rather than trusting convenience getters that may be patched by calibration. Report the raw physical observation and its tiny length projection difference as metadata. Do not synthesize entry/exit events from that difference.

If nonuniform physical lengths are subsequently introduced, merely correcting the count getters or the speed update is insufficient. One validated per-cell geometry source must be used in observation density conversion, initial stock, receiving space, lane-change density conversion, continuity denominator, speed convection/anticipation/merge terms, local freeway plant, and terminal stock reporting. The current global and local continuity equations both use the scalar `freeway_segment_length_km`; the segment speed wrapper alone can read `segment_length_km` from cell parameters. That future dynamics change is not part of the prepared lane-field fix.

## Verification and artifacts

- `diagnostics/test_area_freeway_accounting.py`: 6 tests PASS. Ordinary, incident lane reduction and zero-gradient terminal trajectories match the original method in every physical state field and return value; accepted-entry/terminal/merge transfers conserve stock; off-ramp scheduling precedes residence; candidate copies isolate their ledger; disabled calls delegate; unsupported provenance fails before mutation.
- `diagnostics/test_freeway_count_geometry.py`: 5 tests PASS. The pending patch is applied to source only in memory; absent/false flags retain the baseline, real n7 count error is reproduced and removed when enabled, raw count is independently reconstructed, six 10-second evolving actual-flow steps conserve the corrected counts, and both getters handle 0.25 effective lanes. The calibrated getter reads a changed flag at call time.
- `diagnostics/probe_freeway_area_geometry.py` writes `diagnostics/freeway_area_geometry_audit.json`; its extracted n7 transition equals the original physical state and diagnostics.
- `git apply --check diagnostics/freeway_count_geometry.patch` passes.

Run each test in its own Python process; these checks intentionally install and restore runtime hooks. Example commands from the worktree:

```powershell
& 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' diagnostics/test_area_freeway_accounting.py
& 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' diagnostics/test_freeway_count_geometry.py
& 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' diagnostics/probe_freeway_area_geometry.py
git apply --check diagnostics/freeway_count_geometry.patch
```

Full urban/freeway/endpoint integration remains a separate test once the urban event installer and objective endpoint are connected. These tests establish freeway event correctness and the count-getter repair; they do not certify the complete Omega objective or a live plant result.
