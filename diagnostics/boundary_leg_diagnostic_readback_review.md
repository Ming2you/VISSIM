# Boundary-leg diagnostic: one-ULP baseline difference

The reported `leader_boundary_leg_excluded_veh` difference does not feed selection, λ or physical transitions in the current Ω/follower-TTT path. It is still an output difference, so the original strict-comparator FAIL should remain preserved. This conclusion does not exempt that sum in other controller/objective modes.

Root reported two unmodified baseline values, 3177.0260891219514 and 3177.026089121952 veh, while command, price, J and constraint results were identical. Their difference is one float ULP, 4.547473508864641e-13 veh. This independent review audits the dependency path; it does not independently rerun or recompare those decisions.

`TrafficState.boundary_leg_vehicles` (`state.py:1365–1386`) adds occupancy by iterating a local `boundary_storage_links` set. That string-set order can change between interpreter hash seeds. The function writes only local variables and its local set, with no state/config mutation. Its callers are the leader accumulation helper and `objective_urban_vehicles`.

`Leader._state_accumulation_base` (`leader.py:768–781`) returns `state_base` and `boundary_excluded`. `objective_terms` computes them at line 876, then its active `objective_mode='follower_ttt'` branch uses the supplied endpoint objective as `base`, independently of these sums. `boundary_excluded` is only recorded as `leader_boundary_leg_excluded_veh` at line 943. The companion state-base diagnostics are also not the active objective base.

The canonical area normalizer requires follower-TTT mode and returns the endpoint Ω objective as `leader_total_objective`. It does not consume the boundary diagnostic. Full, Wu PFO and proxy selection read `leader_total_objective`; exact-key search across all canonical controllers and vendor source finds only the producer and a base-fallback metadata copy (`stackelberg_mpc.py:1897`), excluding tests. The diagnostic remains in output metadata through general dictionary copies.

The λ/corrector and urban dynamics use `protected_accumulation_veh` (`state.py:1395`), which sums its own ordered storage/movement mappings and does not call `boundary_leg_vehicles` or read the diagnostic. This is a separate computation, not a rounded copy of the excluded-leg sum. No feedback from the reported diagnostic into the next physical state was found.

In a different `state_accumulation` objective mode, the leader chooses `state_base`, which contains this boundary subtraction. The finding is therefore scoped to the reviewed Ω configuration and is not permission to drop arbitrary diagnostic fields from all comparisons.

The accompanying producer performs only source parsing, reference search, two-scalar arithmetic and SHA checks; source changes are empty and model evaluations zero. For a fresh bitwise performance comparison, explicitly record one `PYTHONHASHSEED` before launching the parent Python interpreter and let workers inherit it. Changing the environment after interpreter startup does not retroactively fix its hash order. No production sum, comparator rule or runtime setting was changed here.
