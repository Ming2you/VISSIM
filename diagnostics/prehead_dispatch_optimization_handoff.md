# Pre-head lookup proposal — unapplied

The repeated work is real: each ordinary movement queries `_inputs`, which filters all ten configured internal inputs to recover the single 1093 pre-head input. Accepted movements then scan the same tagged subset, even when the accepted movement is unrelated. Those scans also validate the state, so this proposal **preserves every `_check` and `_blocked` call, every cohort iteration, its ordering, and every rejection condition**. It does not add an unrelated-movement or zero-accepted fast path.

The only cached information is immutable configuration: filtered input references, input-to-origin, input/route-to-movement, and the W/N movement set. The explicit builder runs after successful native input configuration. The index lives separately from `native_internal_inputs`, so exported source metadata is unchanged. Its reference to the source input dictionary survives actual cfg deepcopy/pickle. Replacement or size change of that dictionary makes the reader fall back to the old lookup until explicit rebuild. Mutation of branch definitions in place during a candidate rollout is outside this proposal's immutable-config contract; it is **not** a state-mutation cache and does not validate mutable configuration on each event.

**Peer review remains unapproved:** the runtime cfg is a plain mutable object; identity and length guards do not enforce the above immutability assumption. The reviewer requires either evidence that all relevant mutation owners obey the configuration boundary, complete value-dependency checks, or a narrower call-local reuse before adoption. No regression result below claims equivalence after arbitrary in-place cfg mutation. A smaller alternative is to pass the existing per-call filtered inputs to that same call's full `_check`; that removes fewer lookups and has not been implemented here.

## Evidence and limits

`prehead_partial_profile_audit.json` records the exact raw hashes and completion metadata of ten completed workers. They are a fixed lexical subset, not all workers or the parent process. Their function call counts are:

| Function | Calls | Main caller |
|---|---:|---|
| `_inputs` | 2,393,502 | `limit_intended` 1,570,500; `_check` 411,501 |
| `_blocked` | 1,968,501 | Every intended/accepted movement |
| `receive_accepted` | 398,001 | `urban_flow_accounting._receive_corridor` |
| `_check` | 411,501 | Accepted events 398,001; advance/generation/finish 4,500 each |

The actual accepting loops already exclude nonpositive accepted flow. Thus a zero-acceptance shortcut would not address the main accepting path. An unrelated-event shortcut would change when malformed pre-head state is detected. Neither is included.

Inclusive pstats times overlap and are not added. The full profile took substantially longer than the unprofiled decision, and the parent is separately checking Python 3.12 thread attribution. These counts identify repetition; the worker profile is not a claim about full-decision wall share or recoverable seconds.

## Validation

`python -X utf8 -m diagnostics.test_prehead_dispatch_optimization` passes 18 tests: nine focused original/candidate equivalence checks and nine tests using the actual raw900 contract/configuration, clock, receiving, geometry, and cfg-pickle path. Both proposed functions execute in memory through real runtime configuration; production files stay unchanged.

Invalid-state cases compare exception type, message, and post-exception state bytes: negative/nonfinite cohort counts, missing input/route identity, tagged queue/storage overflow, accounting mismatch, wrong step, and blocked early discharge. Unrelated and zero accepted calls retain full validation. No-op behavior without the feature/index and unchanged floating-point summation order are checked. Every original `_check` remains called; 4,000 repeated unrelated events give 4,000 checks and identical final state bytes.

The mock-wrapped call-count timing is explicitly unsuitable for speed estimates: the indexed case was slower there. A separate unmocked experiment alternates order four times at 3, 30 and 300 synthetic cohorts, with all validation enabled. The latest saved median indexed/original times are approximately 0.69, 0.86 and 0.90. The fixture sizes are synthetic and do not establish the actual worker distribution or whole-main speedup. Parent load may affect these short timings. Adoption should depend on a later identical-candidate real evaluation trace and unprofiled timing, not these ratios alone.

`git apply --check diagnostics/prehead_dispatch_optimization.patch` passes against pinned dd13e08 sources. The patch contains only `native_input_prehead.py` and the explicit post-config builder call in `native_internal_input.py`. No production files, configs, manifests, evidence, or Git index were changed. No VISSIM, full MPC, or extra endpoint was executed.

## Files

- `diagnostics/prepare_prehead_dispatch_optimization.py`: exact source-pinned in-memory proposal and LF patch producer.
- `diagnostics/prehead_dispatch_optimization.patch`: two-file contextual patch, unapplied.
- `diagnostics/prehead_dispatch_optimization_manifest.json`: original/proposed source hashes and contract.
- `diagnostics/test_prehead_dispatch_optimization.py`: equivalence and bounded timing harness.
- `diagnostics/prehead_dispatch_optimization_validation.json`: actual check results and all timing samples.
- `diagnostics/audit_prehead_profile_hotpath.py`: fixed completed-worker subset reader.
- `diagnostics/prehead_partial_profile_audit.json`: call/caller evidence with raw pstats hashes.
- This handoff.

Production source pins: pre-head `d915c0e52fa69f5b8a89dcf3614d0132c5c5ea3a03f1e8650164ce911612acef`; native inputs `f513f2bd7b6777f8c143710f990ea886dbdb9074575d99bfc88ba08ce7035a98`.
