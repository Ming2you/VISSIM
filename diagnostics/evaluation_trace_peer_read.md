# Return-trace independent read review

This is a source read review, not an independent execution or performance result. No solver, endpoint or VISSIM was run for it.

The collector reads locals/results and emits JSON; it does not replace a model callable, alter a control, or substitute an objective value. A serialization failure marks the trace invalid while leaving the model exception/result path alone. Float hex encoding preserves numerical distinctions, including signed zero. Actual controls include all four levers, allocation and the realized physical meter marker. Timing, source address and process identity are excluded from comparison, while price/lambda/config/state context and returned scores remain.

For the actual four price-worker entry functions, which do not nest each other, collection groups the task root and descendants in original order. It renumbers their local call IDs and sorts complete task traces across workers. This ignores process scheduling but preserves task multiplicity, within-task order, parent evaluation order and returned results. Missing/invalid sidecars and unmatched calls fail validity. The parent launcher must provide its observed child PID set to catch a child that never produced a start sidecar.

Three scope points were sent to the author:

1. `PricePointResult` also has `price_hinge`, `leader_hinge` and `protected_queue`; the initial `SCORE_FIELDS` omitted these components. Capturing the total alone could hide offsetting component differences. Include the actual fields even where today's area objective sets them to zero.
2. The current classifier observes logical follower solve boundaries, not every local candidate/scored closure. It cannot independently prove the internal local candidate evaluation sequence unchanged. Describe that limit or add explicit local boundaries; final action equality is a separate necessary check.
3. The proposed pre-head configuration index would add `cfg.network.native_prehead_dispatch_index`. Whole-cfg hashing would then change despite otherwise identical model inputs. Any exclusion must target only a proven pure derived index and be declared explicitly; never exclude all fields whose name resembles a cache. The clock proposal uses process-local module caches and has no such cfg change.

The original nested endpoint wrappers are counted once. Worker task keys include both task operands and context, so two different configured problems are not combined solely because their task labels match. Cache-reuse metadata is retained, and CSV/output equality remains the parent's independent final gate. No additional code-level behavior-changing issue was found in this bounded read scope.
