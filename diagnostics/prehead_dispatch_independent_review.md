# Pre-head dispatch index independent review

Do not apply the current identity/count-only index under the requested full-value cache contract. Four bounded counterexamples keep the exact input dictionary and its length, but change live values that the original methods consume. The proposed index remains active and returns a different service decision or validation result. This is a cache-contract defect; it is not evidence that the current full-MPC run actually mutates its native-input specification.

Only diagnostic files were written. No production code, input, model state from a run, Git index, endpoint, optimizer or VISSIM was changed or executed. Review source fingerprints, timestamp and reproductions are in `prehead_dispatch_independent_review.json`; `review_prehead_dispatch_index.py` reruns four small method comparisons. Source changes were empty.

## Current runtime lifecycle

| Path | What was inspected | Consequence |
|---|---|---|
| `native_input_prehead.configure_input:18–109` | Builds a fresh branch table, computes probabilities, returns a normal dict | This is construction before index installation, not immutable publication. |
| `native_internal_input.configure:253–430` | Assembles local `specs`; publishes the one `cfg.network.native_internal_inputs` assignment at419; subsequent schedule/metadata construction is read-only to that table | No later nested native-input writer was found in this function. |
| `runtime_setup.configure_runtime:144–195` | Native configure → projection support/SC2001 projection → state and native initialization | Consumers were inspected for cfg writes; observed mutations target copied detectors/raw and candidate state, not the input specs. |
| `native_input_prehead.initialize/receive_generated/advance/receive_accepted/finish_step` | Read the input map and nested branch/origin/WN fields; mutate state cohorts, queues, stock and ledger | Current canonical rollout has no intentional nested cfg mutation here. |
| `native_internal_input.prepare_projection/projection_claims/initialize/advance` | Read source table; construct copied projection data, validate evidence, mutate private source state and stock | No nested table mutation was found. |
| `native_input_routes`, `route_choice_corridor` generated receiver, `projection_support`, `area_runtime` | All named consumers found by a full `evaluation` + `vendor` text search were read | No current downstream writer was found. Text search is not an alias-proof or a runtime write barrier. |
| `runtime_setup.install_worker_runtime:205+` | Reinstalls hooks using the pickled cfg, does not reconstruct native inputs | Pickle/deepcopy preserve ordinary dict aliases, but do not freeze values. |
| `vendor/NumSim-mine/src/models/state.py:207–208` | `NetworkConfig` is a normal mutable `@dataclass`, no frozen option/deep immutable input type | Neither the public cfg nor its nested dicts enforce the index's immutability precondition. |

The recorded `rg` query found only the direct publish assignment at419. Configure also rejects a second native-input configure on an already configured cfg; that guards reconfiguration, not mutation of an existing dict. A source identity/count check plus absence of current intentional writers is insufficient for the user's explicit no mutable-ID-only cache requirement.

## Reproduced stale reads

| Mutation after `prepare_dispatch_index` | Original | Proposed cached behavior |
|---|---|---|
| route2 movement B→C, cohort still blocked with2vehicles | `limit_intended(C, available4, intended8)=2` | Returns4 using old B mapping: changed physical receiving/service limit. |
| origin→an empty existing storage | `_check` rejects the1vehicle tagged subset exceeding that storage | Check returns successfully against the old origin: suppresses an existing invariant. |
| W/N list A,C→B,C | Accepting A records no first-head W/N debit | Records A=2, so later residual first-head service can differ. |
| input kind prehead→irrelevant | No pre-head notification or cohort debit | Still consumes the old input view and removes0.6 tagged vehicle. |

Each case preserves source object identity and input count. The reproduction uses original method logic and the author's generated candidate; it does not replace validation with mocks. The four expected differences are not claimed to be valid reconfigured traffic scenarios: their purpose is to prove the cache no longer observes the same live operands as the original API.

## Narrow correction options

1. Keep a value-checked index only if its dependency signature covers the entire source input membership/filter (`input_no`, `kind`) and, for every selected input, the current origin, route-tag→movement mapping and W/N membership. Preserve insertion order where it controls the original sum/scan. Missing or unfamiliar values must follow the original path instead of raising earlier from eager index construction. Rebuild or bypass on any dependency change. Measure this guarded version before accepting its performance benefit.
2. Prefer the smaller call-local alternative if a full signature eliminates the gain: `receive_accepted` already has `inputs`; pass that same lookup into its final `_check` within the call, retaining every check, scan and addition order. No reference is kept between invocations. This does not require claiming the cfg is deeply immutable.
3. An enforced immutable projection could support a longer-lived index, but would need a real publication/serialization/mutation API and broader tests. An assertion in a docstring or the current identity/count check is not such enforcement and is unnecessary scope for this small optimization.

Hubble agreed to leave the larger index unapplied until the contract is resolved. The existing18 tests and synthetic benchmark demonstrate fixed-config equivalence only. They do not cover these same-cardinality mutations. The tests use `pickle.loads` in the same process; that proves alias preservation but is not a fresh-process worker execution. After any revised cross-call index, add exact nested mutation tests plus an actual spawned worker/restore check; no full optimizer is needed for that gate.
