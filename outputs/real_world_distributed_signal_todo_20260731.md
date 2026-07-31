# Real-world distributed signal control handoff

Date: 2026-07-31

## Current State

- Repository remote: `https://github.com/Ming2you/VISSIM.git`
- Real-world Gaepo `modi` evaluation copy and control scripts were added under `network/real_world_gaepo_modi`, `scripts`, `evaluation/configs`, `evaluation/generated`, and `evaluation/real_world_modi_*`.
- VSL and ramp-meter COM actuation paths are implemented through the real-world VISSIM runner.
- Signal COM actuation currently works at the `SignalController + SignalGroup` runtime state level, but the high-level adapter still writes `major_green`, `minor_green`, and `offset` per logical signal/player.
- The 15-core distributed player generator exists, but the player-to-SC mapping is not final. The earlier `SC108`/`SC109` interpretation should not be treated as authoritative.

## Verified

- 15 signal rows can be emitted by the adapter.
- Diagnostic COM smoke verified that selected signal controllers receive `readback=stored`.
- Monitoring-only signal agents can be kept out of the action CSV while remaining observable.
- Prediction-audit calibration override is applied through the real-world P-Stack tuning chain.

## Important Caveat

The actual VISSIM network uses dual-ring style signal organization. A physical player/intersection may not correspond one-to-one with a single VISSIM `SignalController`. The next mapping pass should use user-verified player definitions rather than inferred SC centroids.

## Recommended Next Work

1. User supplies a player mapping table:
   - minimum: `player_id, sc_no, signal_head_no`
   - better: `player_id, sc_no, sg_no, axis_or_barrier, signal_head_no, link_no`
2. Rebuild distributed player config from that table.
3. Keep the game model as a two-phase/barrier abstraction for now:
   - `major_green`
   - `minor_green`
   - `offset`
4. Implement adapter projection from two-phase/barrier actions to dual-ring `SC + SG` runtime control.
5. Run a 30 s diagnostic COM smoke:
   - every controlled player SG receives a stored readback
   - monitoring-only signals produce no action rows
6. Run 4500 s Stackelberg/P-Stack test with the corrected mapping.
7. Run prediction accuracy audit on the 4500 s decision directory.
8. Update calibration only after the corrected-mapping run completes.

## Do Not Use As Final Evidence

- `evaluation/runs/rw_15core_sc108_4500_20260728`
- Any 15-core result generated before the user-verified SC/SG/player mapping is supplied

Those runs are useful only as COM/runner smoke artifacts, not as final performance evidence.
