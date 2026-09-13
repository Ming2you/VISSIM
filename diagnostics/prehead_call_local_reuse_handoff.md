# Pre-head call-local reuse: unapplied, focused tests pass

The proposal removes one repeated `_inputs(cfg)` filter only from the final `_check` inside `receive_accepted`. It adds no cfg/state/global dictionary cache, no flattened branch/origin index and no immutable-config assertion across calls. The original `_inputs`, `_blocked`, cohort iteration, proportional debit, pruning, W/N accounting and full validation equations are unchanged.

`_check(state,cfg,inputs=None)` still reads `state.native_input_prehead_state` first. When called with two arguments, as all other original callers do, it then obtains fresh `_inputs(cfg)` before constructing the same ordered validation sums. Only `receive_accepted` passes its already-filtered local mapping into its final validation. That mapping contains references to the original row dictionaries; it is not a snapshot of nested values.

The runtime patch touches only `evaluation/controllers/native_input_prehead.py`, two small hunks:

* before SHA256: `d915c0e52fa69f5b8a89dcf3614d0132c5c5ea3a03f1e8650164ce911612acef`
* proposed after-LF SHA256: `96a18bbbe299a10e3e91173af086464836988028dca0a94dc169f279c60c2806`
* patch SHA256: `6a41831624b3e418c6f04db9eedf3ba945015d16718e56ccf62ed9e7e8ae9506`

The production source remains at its before SHA. `prepare_prehead_call_local_reuse.py` performed only text/AST extraction and patch/manifest writing; it did not import a runtime module or execute any test. Its manifest preserves the generation-time `prepared_not_run_parent_requested_baseline_window` status. Root subsequently authorized the short test window: 11 focused tests passed in 0.216s, including the fresh synthetic subprocess, and `git apply --check` passed. The separate `prehead_call_local_reuse_validation.json` and console log pin that result; no performance measurement or production application is claimed.

## Why this is smaller than the rejected index

Every new call invokes `_inputs` afresh. Replacing the entire config mapping, changing an input's kind at equal cardinality, replacing a row, or changing nested branch/origin/WN values before the next call therefore cannot reuse a prior result. No pointer identity, size, dictionary hash or registry survives the call. The rejected `native_prehead_dispatch_index` proposal remains independent and unapplied.

The ordinary canonical body of `receive_accepted` changes only candidate state/cohorts. Its only intervening helper is the existing `_blocked`, a read-only sum. It does not yield, invoke a configurable callback or mutate cfg input membership. As with any reuse inside a synchronous routine, equivalence does not claim support for another thread or an injected callback replacing input membership mid-call. Tests additionally cover a nested value mutation during a synthetic `_blocked` hook because row references retain that value change; this is not a general concurrent-mutation contract.

`initialize`, `advance` and `finish_step` were deliberately left at their original two-argument `_check` calls. They invoke other projection, transfer or service helpers between reading inputs and validating. Their much smaller scan count does not justify expanding this first patch's assumptions.

This primitive can remain useful when the follower game changes: it depends only on the accepted-flow callback's existing state/accounting contract, not on player count, cost function, λ, candidate schedule or current green/VSL/meter choices. If a future implementation changes the accepted callback to mutate input membership or yield before validation, that change must revisit this local contract.

## Prepared tests and the next authorized window

`test_prehead_call_local_reuse.py` passed all 11 focused tests. They compare only the four relevant function bodies with frozen dd13e08 functions, retaining exact returned/error values and pickle bytes of mutated state. The immutable baseline fixture is `fixtures/prehead_call_local_dd13e08.py` (four functions only, not a controller copy), SHA `80ad03074be0070b559e79cb539b6d94cd1bf7142c460a9efc0708f4e4d486aa`. The test gate accepts only the known before/after production source and never regenerates the baseline after application.

Coverage prepared: full `_check`/`_blocked` call order with input scans 2→1; proportional actual departure; wrong-step, negative/NaN, missing input/route, subset/storage/balance errors and partial state; zero/unrelated notifications retaining validation and pruning; blocked/future-ready rejection; same-cardinality nested/config replacements between repeated calls; standalone `_check` remaining fresh; absent-feature behavior; cohort order, deepcopy/pickle independence; nested row-value visibility; and a fresh synthetic subprocess with no retained per-call data.

The synthetic worker test does not certify actual runtime bootstrap or a complete endpoint. A small existing actual pre-head regression can next exercise the canonical module or the reviewed functions in its real setup if root requests it. Full model/MPC timing remains root-owned. The commands below reproduce the completed focused check.

```powershell
python -X utf8 -m unittest diagnostics.test_prehead_call_local_reuse -v
git apply --check diagnostics/prehead_call_local_reuse.patch
```

Each nonempty accepted callback reaching validation can avoid one input-table filter. Empty-feature returns and early failures retain their original behavior. This is a count-level observation, not a speed claim: no benchmark, elapsed improvement, overall scan-reduction percentage or new model result is available. The baseline run is left undisturbed.
