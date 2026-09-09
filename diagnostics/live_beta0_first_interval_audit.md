First beta0 interval audit: first_interval_pass_next_decision_failed.

Run codex_area_beta0_s13_20260910; observation interval [900, 1050) seconds.

First command CSV identical to final preflight: True.

CSV SHA256: ed2c4736e193e9f2c7eaf118ab9382c267efc4995b987de3d93bee4eb40fa46a.

Signal/ramp command mismatches=0; persistence mismatches=0; incomplete groups=0.

All 130 commanded groups have 150 s coverage. The 122 urban groups each showed GREEN, AMBER and RED; all 8 ramps remained GREEN for the entire interval. The 66 VSL writes/readbacks matched the 120 km/h commands. Thirteen of 17 controller offsets were nonzero. This interval therefore does not demonstrate a restrictive metering or VSL effect.

The 900 s decision completed in 119.516566 s with exact phase/meter scoring and writer assertions. Initial physical Omega stock 1763 equals model 1763.0; all 12 compared raw snapshot sections match the preflight input. Predicted 450 s Omega TTT/J = 297.857340619338 veh*h and TTD = 1470.396120917891 veh; beta = 0 s. These are model predictions, not measured interval performance.

The 1050 s next decision failed during observation projection: one physical vehicle on link 10421 has unresolved model stock support. No 1050 s action JSON/CSV was produced and no fallback_fixed was logged. This failure does not invalidate the completed 900–1050 s actuation check; it prevents claiming a completed simulation run.

This is a decision/actuation audit, not a performance or beta comparison. Sources and exact counters are in the adjacent JSON.
