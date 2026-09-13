# Common-price simultaneous perturbation audit — 2026-09-11

This is an implementation/audit checkpoint, not a measured traffic benefit.
Production sources were not changed for this experiment and no model or VISSIM
run was launched by this audit task.

## Existing implementation

`vendor/NumSim-mine/src/controllers/stackelberg_wu_metered.py:907` estimates a
global objective gradient from simultaneous high/low `LeverMove` schedules.
The legacy caller at line1264 supplies one primary-green coordinate per signal,
raw meter values, VSL keys and a networkwide offset cycle. The schedule path
`vendor/NumSim-mine/src/controllers/rollout_endpoint.py:111` redistributes the
remaining greens from that primary coordinate. The legacy price caller
subtracts separately computed local costs.

Those inputs differ from the current whole-phase, owner-cycle, zoned-VSL,
canonically quantized-meter, common-response external-price definition. The
existing switch cannot be enabled as a drop-in replacement.

The comment near line34 claims a historical 16/32-pair correlation comparison.
The scoped filename/source searches in this checkout did not locate the
underlying SPSA experiment artifact. That comment is not independent evidence
against the present formulation. `reports/codex_review_request_20260811.md:388`
also records an uncompleted exact-FD/SPSA qualification harness; its old timing
claims belong to another model/network generation.

## Diagnostic implementation

`diagnostics/compare_joint_block_spsa.py` consumes an already measured common
price field and its secants. It reconstructs the actual observed owner probes;
it does not invent nominal symmetric moves or sum multiple green exchange
vectors outside the permitted box.

For each of 8/16 pairs it cycles one basis direction per owner and draws
independent owner signs. Each side combines different owners' anchor/probe
values. The existing canonical realizer must preserve every non-diagnostic
requested field; the supplied writer/fixed-box validator must succeed. Meter
and discrete-VSL probes at an upper bound therefore remain one-sided.

For owner i it records sign_i × (ΔJ−ΔC_i), using J and C_i from the same two
physical responses. Other-owner contributions cause finite-sample variation;
nonlinear interactions can introduce bias away from the actual anchor. This
is a sparse block simultaneous-perturbation comparison, not dense symmetric
SPSA and not an exact finite-difference replacement.

The report preserves each failed pair, physical/context tokens, basis coverage,
external-delta MAE and relative L1 error, sign agreement, coordinate-price
errors, response counts and wall/CPU time. Relative L1 uses the sum of absolute
exact single-owner external deltas as denominator. Missing coordinates remain
unknown. Selected actions stay null unless a separate selection comparison is
performed. No approximate field is installed by this helper.

Seven synthetic tests pass in `diagnostics/test_joint_block_spsa.py`, including
one-sided bounds, complete/incomplete coverage, same-response local subtraction,
context mismatch, reproducibility, canonical-realization failure and timeout.
Actual saved-state 8/16-pair measurement and any selection/native comparison
remain to be run by the root task after its production source freeze.
