# Selected signal clock hot path: read-only review

The active physical-clock path repeats vector validation and writer normalization even when the phase window is already cached. A bounded value-key cache is a plausible optimization, but no current timing or speedup is claimed. Parent/worker cProfile must decide whether repeated validation, the finite second loop, or another caller dominates. No production source, model setting, candidate action or runtime input was changed; no endpoint/MPC/VISSIM was executed for this review.

## Actual path and repeated work

`runtime_setup.configure_runtime` installs the physical candidate contract, then `install_monitor_fixed_signal_runtime_patch` builds a wrapper and assigns the same function to urban_queue_model, distributed_coordinator, local_signal_plant, wu_distributed and wu_faithful_follower. Workers rebuild these aliases from their configured network. The outer `signal_actuation_contract.wrap_clock` dispatches selected physical movements to `phase_fraction`; native/monitor and contract-OFF paths still belong to the previous wrapper.

A selected signalled finite-time call in phase_fraction currently does:

1. Read the four current green values and validate them.
2. Call written_offset_sec, which reads the same four values and validates them again; recompute the serialized cycle and normalize the writer's offset.
3. Recompute the cycle again; retrieve the existing _phase_windows LRU result.
4. For each absolute integer second intersecting the urban interval, evaluate the exact VBS expression `x - floor(x / cycle) * cycle`, test the phase window and accumulate the same overlap formula.

By direct source counting this is two validate_vector calls, two bounds calls and at least six explicit signal_live_phases calls per selected finite clock query, even on a _phase_windows cache hit. For the active 5-second urban step it also performs five FMod calculations. These are branch-specific static counts, not measured aggregate call counts. A fallback effective-green calculation can add further signal/live-phase reads.

The calling graph includes every actual urban service query, route-choice signal service and newly joined head-resource budget, plus local GNE green/offset and phase-price refinement. The physical local `_offset_green_fractions_vec` shares a profile among movements with the same `(phase, unsignalized)` only inside that invocation; another candidate or global rollout reconstructs it. Head budget and movement service can query the same physical signal/time without sharing an action-wide clock result.

## Existing caches and boundaries

| Existing cache | Key/lifetime | What remains |
|---|---|---|
| _phase_windows | Bounded LRU16384; selected segments, order, 4greens, clearance | Removes plan layout; not vector validation, writer offset or per-second evaluation. |
| Native _union_green_overlap | Program identity with strong reference, groups, absolute start/end, controller offset | Already memoizes the fixed .sig overlap. This is a separate continuous native schedule calculation; do not replace it with the selected integer-event clock. |
| Adapter share_of | Spec identity plus strong reference inside each installed wrapper | Native share only; selected physical dispatch returns before it. Its historical source comments are not current profiling evidence. |
| Local phase GF | (phase, unsignalized), one local-fractions call | Reuses same phase within a candidate, not across global calls or repeated candidates. |
| Shared phase setup | signal within one fresh ctx | Deliberately invalidates inherited `_phase_ctx_cache` between invocations because stocks, ready reservations and mutable Wu flow caches matter. Do not restore this cache as a signal optimization. |

## Smallest safe sequence after profiling

Start with a pure finite-interval memo only if the FMod/loop matters. Keep the existing dispatch, validation and written-offset calculation in the same order. Cache only the loop's scalar result by `(cycle, written_offset, lo, hi, duration, absolute_start, absolute_end)`. Retain the exact original arithmetic and accumulation order on misses, with a bounded process-local cache. This skips repeated second loops without coupling to state, config identity or candidate metadata. It intentionally does not remove validation overhead.

If validation is the larger measured cost, add a separate validated-clock compilation keyed by all current scalar/tuple operands: signal, the four float greens in PHASES order, effective total, green_min, physical write clamp, live phases, selected segments/order, amber/all-red, writer and relevant offset operands. Its result can hold the already validated cycle, written offset and immutable phase windows. The first implementation can scope this acceleration to the existing physical experiment writer; other writer modes then delegate unchanged. General test_only support requires the forced-offset table/scalar diagnostic values in the key, since changing control.offsets alone does not describe the written offset. No new controller lever or altered model is required.

Do not key on id(control), id(cfg), id(spec), a diagnostics marker or a rounded approximation of the candidate. Controls are copied and mutated in-place by searches, offsets can change independently, and the same process can build another cfg. Either include full current value dependencies or keep the existing path. Invalid candidate input must still raise before returning an old successful cached result. Network getter fallback counters are observable side effects; a wider memo must not suppress them unintentionally. Cache valid pure computations, not those getters or their error checking blindly.

Do not reduce absolute time modulo cycle. With 150.001/149.999-second cycles and float arithmetic, the exact VBS FMod expression can differ from Python `%` and from a computation made at a reduced time. Do not substitute floor arithmetic with a lookup table over a guessed cycle, use a continuous green-overlap shortcut for selected signals, or sum a prefix table in a different floating order. The `urban_step_index=None` mean path computes a rational superperiod with gcd and is distinct from a finite rollout; its result must never collide with a finite-step entry.

Cached profile arrays or dictionaries must not be shared mutable results between candidates. Prefer immutable tuples internally and reconstruct the output mapping/list contract as required. A pure clock cache needs no queue, ramp, capacity, demand, receiving or readiness operand. Those quantities do affect service and must continue through their existing current-state computation. Clock reuse must leave accepted-only resource budgets local to the invocation.

## Required regressions and profiling acceptance

- Compare reference and cached results bit-for-bit (not tolerance only), including all selected 17 plans, live/dead phases, same-phase unsignalized peel-offs, zero/default/missing phase and non-selected/monitor delegation.
- Compare actual writer CSV and unchanged VBS state functions at signed offsets, zero/cycle boundaries, cycles150/150.001/149.999, late absolute steps29999/30000/30001, fractional Tu/step boundaries, and the None mean branch. Keep the existing actual VBS FMod oracle rather than using Python percent as the only oracle.
- Probe green values at physical limits and rounding boundaries, dead nonzero values, NaN/Inf, invalid budget/live phase set/offset, and valid→invalid mutation after a cache hit. Preserve exceptions and accepted values exactly.
- Reuse and copy a ControlAction, change greens, offset, cfg duration, live phases, effective total, plan/order/clearance and writer mode independently; each relevant change must invalidate. Include test_only forced table/scalar metadata if that path is cached. OFF/native results stay exact after ON use in the same process.
- Repeated runtime install and actual main builder must preserve all five clock aliases; a fresh worker recomputes the same output with its own empty cache. Pickle and inputs remain unchanged. Cache capacity/eviction tests must show bounded memory and no ID reuse assumptions.
- Retain head/shared service ready/receiving regressions: a clock cache cannot cache accepted flow, resurrect old q0/pending state, or collapse unsignalized and signal-controlled members.
- Profile parent and workers separately: total/self time and call counts for phase_fraction, validate_vector, bounds/live phases, written_offset_sec, local_fractions; _phase_windows cache_info and native overlap hit/miss deltas. Measure cold/warm timings and memory against exactly pinned baseline inputs. Only after equivalent output and objective/action traces can speedup be claimed.

Existing diagnostics/test_signal_actuation_contract.py covers selected plans, offsets/dead phases, local profiles, actual worker aliases and a VBS decimal-cycle oracle. Its existing tests use some tolerance comparisons and historical fixtures, so they are useful coverage, not a substitute for a new exact-output cache regression. This review did not rerun them or modify their saved outputs.

Source fingerprints and the static dependency summary are in signal_clock_hotpath_review.json. No cache code has been implemented or proposed patch applied.
