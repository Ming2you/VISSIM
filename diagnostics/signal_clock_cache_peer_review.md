# Independent review of the unapplied clock cache

The finite-interval arithmetic keeps the original ordered integer-event sum, VBS-style `x-floor(x/cycle)*cycle`, exact duration, offset, phase window and absolute start/end operands. The clock key includes the live phase set, minimum, effective total, physical clamp, raw phase segments/order, clearances, writer and offset operands. Missing effective-total overrides correctly bypass memoization so the original fallback diagnostics remain observable. No candidate, receiver, stock or service result is cached.

Two bounded function-call counterexamples were reproduced against the actual configured 900-second fixture, without an endpoint, solver or VISSIM run. Exact source hashes and outputs are in `signal_clock_cache_peer_findings.json`; that evidence is preserved even after the proposal changes.

1. **Supported test-only writer:** `{signal_green_freeze_offset_sec:10}` and `{diagnostic_forced_signal_offset_sec:None, signal_green_freeze_offset_sec:10}` have the same `diag.get()` value tuple. The original writer uses offsets 10 and 0 respectively because the first present scalar key wins, even if conversion fails. A cache warmed with the first control incorrectly returns the first clock for the second. SC1004 p3 produces different GREEN fractions at steps 13, 14, 20 and 21. Preserve each scalar key's presence bit as well as its value.
2. **Custom-type bypass boundary:** an `int` subclass equal/hash-equal to 0 but whose float conversion returns NaN hits a previously cached builtin zero before `_immutable` is checked. The original raises `OffsetPromotionError`, while the proposal returns a fraction. Ordinary production actions use builtin floats, so this is a separate defensive-contract issue, not evidence that a current MPC candidate contains such a value. Unknown/custom dynamic operands must be ruled out or sent to the old path before hit lookup.

The read review did not identify another missing ordinary numeric operand. Threaded use of the manual OrderedDict LRU is outside this review; the actual selected price-worker and follower calls under inspection are process-local. The complete trace/timing check remains the parent's responsibility. A unit workload speed ratio is not a full decision speedup.

Recheck after a proposal fix with `python -X utf8 -m diagnostics.review_signal_clock_cache_findings --output diagnostics/signal_clock_cache_peer_recheck.json`; the producer refuses to overwrite the historical counterexample file. Production code was not changed.

## Final fixed proposal

Patch `d75097744dad4214dc60ed42ef10b5ca18df00d41e1a93771afe68e0a6eb451f`, proposal `74fb9667e1f6b06b2801252bcbaba077de7605b90ada977d950e7d3006490c5b`, independently rechecked: both counterexamples now match the original result/exception exactly. `signal_clock_cache_independent_final_recheck.json` preserves this separately from the original failure evidence.

Eight additional pure checks in `signal_clock_tuple_guard_independent_review.json` confirm exact builtin tuple/leaf types, a mutable leaf 200 levels deep, rejection of tuple/numeric subclasses, strong-reference protection against ID reuse, proof renewal for equal new tuples and evicted tuples, release of the containing cfg/control owner, and explicit cache clearing. Current scalar/offset operands are checked before every hit. Only the already proved immutable tuple itself uses the bounded identity registry. No additional blocker was found within this process-local, selected-clock scope. No benchmark, endpoint or full decision was repeated for the recheck.
