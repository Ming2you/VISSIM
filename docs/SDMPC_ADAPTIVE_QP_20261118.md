# S-DMPC: QP reduction and post-PFO adaptive selection

This branch assembles the S-DMPC runtime from the local experiment snapshot at
`8072913b6b741ecbd86ae06c67e5734ae66b536a` on the previously published plant
baseline `9a8320eccfcb92cf870a7eb108cd3184c24b0a7b`. It contains code, pinned
small inputs and tests; it does not contain VISSIM results or FZP trajectories.

## Controller behavior

* Fixed QP variables are eliminated before solving and restored with full
  constraint verification. The Dykstra fallback defaults to at most 3,000
  sweeps and 3 seconds; a non-converged or infeasible result is rejected.
  These defaults can be disabled explicitly with `SDMPC_QP_REDUCE=0` or
  `SDMPC_QP_FALLBACK_LIMIT=0` for controlled comparisons.
* Full PFO and original VSL/RM discrete checks remain enabled. The full traffic
  state and its flows, capacity constraints and objective remain in prediction.
* Optional post-PFO Lagrangian selection uses all three environment variables
  `SDMPC_POST_PFO_LAGRANGIAN=1`, `SDMPC_EXPERIMENTAL_LAGRANGIAN_SELECTION=1`,
  and `SDMPC_EXPERIMENTAL_ADAPTIVE_THRESHOLD=0.01` (or `0.05`/`0.1`).
  PFO runs on all actuators first; nonselected controls are then fixed at that
  PFO anchor. The price update is approximate, not a KKT certificate.
  Omit these variables for the unscreened Full baseline.
* Default tuning is `diagnostics/repin_v3c3_review_20261001/urban_rm269/aggregate270/native413_adopted355/optimized_config.json`.
  The tested network SHA-256 is `64cf5f55fe9990f3e25bc4fedebf4ab1e4634c8138dbcf5697a136c48cb559dc`.
  Experiments used seed 29, 8100 s, 150 s control intervals, 450 s prediction,
  terminal cost OFF, Omega701 and the existing SC1001 allocation model.

## Evidence and limitations

The original unscreened Full with both QP changes completed 8100 s. At the
saved 900 s state the new default baseline reproduced its prior command CSV
SHA-256 `508b330211f316cc3bba46b7cb07a8027eb7f5b30c78e978e84b56448a00c519`.
Saved-state tests of the three thresholds passed the final feasibility and
command-binding checks; 25, 19 and 18 of 33 groups were selected respectively.
Those solutions were not certified converged.

The 0.01 VISSIM run completed 8100 s with runner exit 0 and 45 fresh / 3 held
decisions. The queue required at least 46 fresh decisions, so it stopped and
0.05/0.1 did not run. At 5100, 5850, and 6450 s the recorded causes were PFO
QP failure, a pre-selection group QP failure, and missing observed speed,
respectively. Seed29 alone cannot establish general closed-loop performance.
The reported Omega TTT excludes outside-Omega road time and latent insertion
waiting. SC1001's inspected connector stocks were conserved in tested states,
but an observation-summary bookkeeping discrepancy remains unresolved.

| Seed 29, 0–8100 s | Full + reduced QP + bounded fallback | Post-PFO selection τ=0.01 |
| --- | ---: | ---: |
| Omega701 TTT (veh·h) | 6,969.95 | 7,069.01 |
| Urban roads + off-ramps TTT (veh·h) | 3,435.73 | 3,519.81 |
| Eastbound freeway + on-ramps TTT (veh·h) | 2,063.10 | 2,080.02 |
| Westbound freeway + on-ramps TTT (veh·h) | 1,471.12 | 1,469.18 |
| Outside Omega road TTT (veh·h) | 1,619.29 | 1,621.75 |
| Median decision wall time, fresh decisions (s) | 234.84 | 206.21 |
| Fresh / held decisions | 47 / 1 | 45 / 3 |

These are one-seed, realized closed-loop values; decision-time comparisons
can reflect different system load. The native experiment does not establish
separate execution-readback coverage or convergence to a global optimum.

## Local tests

Install the project's existing Python requirements and expose this repository
and `vendor/NumSim-mine` on `PYTHONPATH`. Then run the two tests below:

```powershell
python -m unittest diagnostics.sdmpc_n31_20260924.tests.test_qp_official_defaults
python -m unittest diagnostics.sdmpc_n31_20260924.tests.test_qp_experimental_regression
```

These unit tests do not replace VISSIM native execution and actuator readback.
