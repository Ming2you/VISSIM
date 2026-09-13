# Selected physical signal clock cache — unapplied handoff

Recommend the validated-clock cache plus exact finite-interval memo, confined to `signal_actuation_contract.py`. The finite-only alternative had no benefit in this workload and is not in the proposed patch. Production, candidate ranges, objective/constraint logic, queues, capacities, routes and receiving ownership were not changed.

Root's completed profile used the same final command CSV as the unprofiled run. Parent call counts reported were phase_fraction3,949,417 and validate_vector7,096,408, with further worker calls. The earlier first10worker snapshot reported phase_fraction1,098,540 / validate_vector1,536,120 / written_offset768,060 calls and only92 phase-layout cache misses. The absolute self/cumulative profile costs remain under root QA because Python3.12 cProfile/sys.monitoring may mix thread attribution; nested cumulative times and parallel worker times must not be added or treated as wall time. The proposal is motivated by repeated work; its isolated timing below does not depend on those disputed stage totals.

## Reproducible reference and unchanged calculation

`fixtures/signal_clock_dd13e08.py` contains exactly five function bodies from current dd13e08 (bounds, validate_vector, _phase_windows, written_offset_sec, phase_fraction). The function source hashes and original module SHA are in its manifest. No Git lookup is needed to run the tests, and no adapter/vendor body is copied. The unchanged production plan writer, offset authority and types supply dependencies.

A cache miss executes the existing validation/writer normalization in the same order, including its duplicate validation. Cached clock values consist only of cycle, written offset and immutable phase windows. The exact original finite loop is retained: absolute integer seconds, `x - floor(x/cycle)*cycle`, unchanged comparison and accumulation, unchanged division. The None mean/superperiod branch stays separate. No modulo-cycle reduction, continuous overlap substitute or approximate/rounded candidate key is introduced.

The complete value key contains signal, current4floatgreens, live phases, green_min, explicit effective total, write clamp, selected segments/order, amber/all-red, writer, and the actual relevant offset operands. Test-only forced table/scalar diagnostics are included; intent_only and experiment remain distinct. Action/cfg/spec identities and saved candidate markers are not used. New unknown/unhashable or nonfinite key values take the original validation path. Scalar/offset operands are checked for exact built-in immutable/finite types before each dictionary lookup. Only selected plan _segments/_order tuples use a separate bounded guard: the full tuple tree is first checked recursively, every leaf must be an exact builtin immutable finite value, and the exact tuple is then retained strongly. A later id lookup is accepted only when the retained value `is` the supplied tuple. Such a proven tuple tree cannot change; a replacement tuple is checked anew. Strong references prevent object-ID reuse while registered. The guard stores no cfg/control/spec or mutable container. This prevents custom equality/hash implementations from imitating a valid cached numeric key while avoiding repeated deep traversal of an already proven plan. Forced scalar diagnostic keys retain their presence bits, so absent and explicit None remain distinct.

A missing effective-total override deliberately bypasses the compiled-clock cache. Its original cycle getter can update fallback diagnostics; caching that path would otherwise suppress observable side effects. OFF/nonselected/native/unsignalized dispatch remains unchanged, and original error paths remain active for invalid inputs after a valid cached hit.

The immutable-plan guard is bounded at1,024 tuple trees (FIFO eviction), the clock cache at16,384 entries; the finite-interval LRU at131,072. Neither stores candidate/state/cfg objects, and weakref tests verify collection. Peak process/worker RSS under a full search has not been measured. Cache statistics are process-local and are not inserted into score/output metadata. Workers begin with empty local caches and reinstall the same five clock aliases.

## Exact regressions and isolated timing

12 focused tests PASS in9.796s; 19,763 outcome comparisons against the original/current functions match exact IEEE float bytes (or exception class/message), plus generated-patch-function and local-profile checks. Source changes are [].

Coverage includes all17 selected signals; live/dead/unknown/unsignalized phases; cycles150/150.001/149.999; signed, wrapped and rounding-boundary offsets; absolute steps29999–30001; fractional Tu/step; mean branch; green/offset/config/plan/writer mutation and candidate copies; invalid/NaN/Inf values; forced-key absent/None with a valid later scalar; a custom int subclass equal to cached zero but converting to NaN; inherited OFF/native values and fallback counters; actual follower profiles; fresh worker restore and all5 actual clock aliases; bounded clock eviction and no cfg/control retention. The sentinel150001/150.001 gives VBS FMod0 but nonzero Python%; the proposal retains the VBS result. The published patch's changed functions are separately compiled in an isolated function namespace and compared to the frozen reference.

The benchmark uses one actual900 configuration/action, offset-only copies0/+10/-10,17signals×4phases×30steps =6,120 queries per pass. Four trials rotate all four methods in order, reporting medians. Warm values below cover three passes. All output bits, input pickle and source/input hashes are unchanged.

| Method | Cold one pass(s) | Warm three passes(s) | Warm clock-only ratio |
|---|---:|---:|---:|
|original|0.087007|0.259355|1.000×|
|finite_only|0.087801|0.261313|0.993×|
|validated_clock_full_check|0.063109|0.176170|1.472×|
|validated_clock_and_finite (proved tuple guard)|0.036302|0.104870|2.473×|

The first recursive-check version was slower than the original and is preserved in signal_clock_cache_benchmark_initial_slow.json. Moving validation after cache lookup made a later version faster but unsafe for custom equal-valued keys; its timing is preserved in signal_clock_cache_benchmark_before_peer_fix.json and is superseded. The safe full-check intermediate version is preserved in signal_clock_cache_proposal_full_check.py and signal_clock_cache_benchmark_full_check.json. The final version checks changing operands every time and reuses only exact proven immutable plan tuple trees; it is compared with the full-check version in the same benchmark batch. Peer findings are preserved in signal_clock_cache_peer_findings.json; the original findings output is not overwritten. The absent/None collision produced four actual SC1004 p3 step mismatches and is now covered by a regression. Timing changed across runs and includes host load; compare each method within its same rotated batch, not absolute times across batches. Full-MPC wall acceleration is still unverified, and this repeated-query benchmark does not establish its cache-hit distribution or peak memory. Root should compare the same pinned full decision before/after application, requiring identical command/action/score outputs and bounded workers.

## Patch and next gate

`diagnostics/signal_clock_cache.patch` SHA256 `d75097744dad4214dc60ed42ef10b5ca18df00d41e1a93771afe68e0a6eb451f` passes git apply --check against original source `8a470f7083fb3452756cd39573a690cc164989a079cd66eb10e1279f0a8f4c1f` and remains unapplied. It adds the selected cache primitives to the existing signal module and narrows phase_fraction to consume them. No new runtime helper module or adapter is required. The public original written-offset writer validator remains unchanged.

Commands:

```powershell
python -X utf8 -m unittest diagnostics.test_signal_clock_cache -v
python -X utf8 -m diagnostics.benchmark_signal_clock_cache
python -X utf8 -m diagnostics.prepare_signal_clock_cache_patch
git apply --check diagnostics/signal_clock_cache.patch
```

Files: proposal, focused test, benchmark producer/JSON, original5function fixture/manifest, patch generator/patch/manifest, exact-validation JSON and console. The generator/test intentionally reject a mismatched production source fingerprint. After root applies the patch, migrate that gate to the known before/after hash and actual imports; do not regenerate the baseline from the new implementation. Production application, independent review and full-decision acceptance remain root-owned. Hubble independently identified the two key-collision issues above; both were corrected in the diagnostic proposal and regression. Re-running his unchanged counterexample producer after the fix yielded zero output mismatches and the original custom-input exception; its new output is signal_clock_cache_peer_recheck_after_fix.json. Immutable-tree guard tests separately verify repeated identical-object proof reuse, equal replacement tuple revalidation, custom/list/NaN rejection, strong-reference retention and bounded eviction. The new patch remains unapplied; no claim is made that independent review or full-decision acceptance of this revised version is complete.

## Canonical test migration prepared separately

`signal_clock_cache_test_migration.patch` (SHA2568bba97dc4d43b4d11c9aafc032f75f12af26de797875796ceba626ce74d0a11d) changes only the focused test. It accepts only the frozen original clock SHA or exact reviewed after-LF SHA9581813d96fb27a7275ba41766763bd0bf123a200fb15b8cec8bf42e484227b5. The original five-function fixture/manifest are unchanged. After production application, the generated-function regression exercises the actual canonical implementation instead of trying to reapply the source proposal. A fresh worker first calls all five actual canonical clock aliases without proposal substitution, verifies exact frozen-reference outputs and source SHA, then separately tests the proposal alias path. When the patched source is installed it also requires actual cache hits and misses.

The generated test migration was validated before application:12 tests PASS6.689s, including the actual unchanged canonical worker path; `signal_clock_cache_canonical_validation.json` explicitly records cache_installed=false. This does not certify the post-application run. Both production patch and migration patch remain unapplied. Root can apply them sequentially and run `python -X utf8 -m unittest diagnostics.test_signal_clock_cache -v`; the output must then record cache_installed=true and no source changes. A first migration-only schema mistake (treating the function inventory dictionary as a list) failed before any tests ran; its first_red log/JSON are preserved, corrected without changing the frozen fixture.

## Independent review completed after the final guard

Hubble independently checked the final immutable-tuple guard in eight bounded checks and reran both earlier counterexamples against the corrected final proposal. `signal_clock_tuple_guard_independent_review.json` and `signal_clock_cache_independent_final_recheck.json` record PASS for strong-reference retention, exact-object identity, equal replacement tuple revalidation, eviction, deep mutable/custom-subclass rejection, owner collection, absent/None distinction and the original custom-input error. The proposal SHA74fb9667e1f6b06b2801252bcbaba077de7605b90ada977d950e7d3006490c5b and patch SHAd75097744dad4214dc60ed42ef10b5ca18df00d41e1a93771afe68e0a6eb451f were unchanged. This supersedes the earlier pending-independent-review statement above. The peer review did not rerun the benchmark or a full decision. Production application and post-application canonical/full-decision acceptance remain pending root's gate.
