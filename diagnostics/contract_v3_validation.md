# Contract v3: actual main integration passes; traffic outcomes pending

The corrected canonical controller completes the actual full main path on the recorded NC v2 state at 900 seconds for all four objective coefficients. The late phase installer no longer removes the shared service's explicit ready context. This is an integration result, not proof of traffic improvement or a final canonical model.

| Reward [seconds/vehicle] | Full process wall time [s] | Result |
|---:|---:|---|
| 0 | 182.906 | PASS |
| 60 | 218.313 | PASS |
| 150 | 219.812 | PASS |
| 300 | 210.125 | PASS |

The exact elapsed values in the original manifests are authoritative; the table is rounded. Each process validates the pure area leader objective, follower TTT minus rewarded outward crossings, consistent offset and finalized metering commands, unchanged source/input hashes and no surviving workers. No proposal code or substitute optimizer is installed by these full preflights. The 60/150 processes ran concurrently, so wall times are not a controlled performance benchmark.

Original results:

- `area_production_preflight/wu-link_t900_beta0_20260910T021243039859Z/manifest.json`
- `area_production_preflight/wu-link_t900_beta60_20260910T022356655777Z/manifest.json`
- `area_production_preflight/wu-link_t900_beta150_20260910T022355287228Z/manifest.json`
- `area_production_preflight/wu-link_t900_beta300_20260910T021854343272Z/manifest.json`

`contract_weight_preflight_v3_t900/assessment.md` reports all four predictions and `commands.csv` preserves all four lever families. At this state, 34 of 68 green fields and four of 17 offsets change with the coefficient. VSL and metering values are identical across the four candidates. Follower searched-rollout metrics and leader held-endpoint scores are deliberately separate. The higher-reward searched rollouts also have lower predicted TTT here; this shows search sensitivity rather than proving a globally optimal policy or a real traffic benefit.

The earlier failed main preflight and its pre-repair source hashes remain preserved. Bounded main/worker regression coverage and the remaining unsupported mixed ON/OFF-controller reuse lifecycle are documented in `shared_service_main_stack_fix.md` and its independent peer review. Production uses one controller configuration per process.

The v3 ON family pins 134 runtime inputs plus four flattened coefficient configurations. Its OFF observation comparison family adds only the head-flag overlay and pins 135 inputs plus four configurations. Staged checkout byte checks pass for all 138/139 paths. `signal_observation_pair_v3.json` verifies that materialized ON/OFF beta0 configurations differ only in the boolean head-observation flag.

`run_area_beta_trial.ps1` now passes an explicit optional `ForceStepwise` switch to the existing watchdog. The default remains false. This enables a matched NC observation comparison. The owned-process startup limit remains 300 seconds without simulation progress; runtime MPC computation uses the separate existing stall limit.

Actual observer ON, observer OFF stepwise and observer OFF continuous 1050-second NC runs have completed. Their trajectory and native signal comparisons are separate empirical evidence. A real beta300 all-lever 1050-second run was launched after the four full MPC checks; it was still running when this note was created. Later completion and physical outcomes must be read from that run's separate validation record.

Remaining model diagnoses include physical head capacity ownership and already-selected freeway-exit routes being redistributed in a downstream aggregate leg. These have not been repaired by this installer correction. The earlier complete 5400-second beta0 control run worsened area TTT and TTD; the v3 integration PASS does not replace that result or make the old run successful.
