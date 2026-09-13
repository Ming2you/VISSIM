# Price worker lifecycle and profiling boundaries

Read-only source audit, 2026-09-10. Scope is the frozen `wu-link` implementation and `diagnostics/contract_candidate_configs_v4/n7_area_beta300.json` (SHA-256 `f3e48ac4df925c59aa18e1c40431d835e41b915f37c5a5af1d5d4dec38aa830b`). The earlier `contract_candidate_configs` directory is not the configuration source for this report. No optimizer, endpoint, VISSIM, production edit, or Git mutation was performed. W_out work is stopped and preserved in `known_wout_local_parity_handoff.md`. Source pins and machine-readable hook names are in the adjacent JSON.

## Active configuration, without inferring performance

|Setting|Frozen v4 / exact builder behavior|Source|
|---|---|---|
|price workers|10, reduced to `min(workers, task_count)` per batch|v4 `price_parallel.workers`; adapter:7081|
|green, meter, VSL, offset prices|All four enabled by the Wu-link builder|adapter:7041–7044|
|offset walk|4 inner iterations; walk requires cycle/8-aligned delta and no SPSA|adapter:7045; metered:1485|
|phase prices|enabled; delta 6 s; weight .25|v4 `phase_price`|
|phase local calculation|`price_local_model=phased`, `local_cost_model=phased`, ramp-aware; 12 refinement rounds, exchange steps [6]|v4 `phase_price`; adapter:7157–7160|
|phase inside GNE|Not enabled: `phase_price.in_gne` absent, follower class default False|priced:543; adapter:7132|
|meter inside GNE|True, link freeway consumer; do not infer False from stale builder docstring|v4 `agent_topology.metering_in_gne`; adapter:7205–7211|
|price loop/default variants|one price iteration, refresh interval 1; price-lite/SPSA/cross-price variants False; price-far False (no flagship override)|metered constructor; adapter:7046–7055|
|candidate/grid pools|Config says serial; actual Wu candidate override independently forces parent serial|v4 `config_overrides.mpc`; metered:2713–2763|
|VSL task equivalence|Zone-aware dedupe active; original logical corners and representative endpoint tasks differ|runtime_setup:33; adapter:8330–8404|
|objective|Ω TTT − 300/3600 × TD; endpoint far/soft extras/pruning disabled by current objective contract|area_runtime:189–225|

These are configuration/source-derived flags, not measured invocation counts. The frozen config's old benchmark notes are historical and provide no current runtime ranking. The planned all-lever GNE change has not been applied here.

## Real call graph and channel counts

Adapter main builds the controller and terminal-cost wrapper, then `install_price_worker_bootstrap`, then `decide_with_info` (adapter:12655–12666). `StackelbergWuMeteredController.decide_with_info` calls `_maybe_refresh_signal_prices` before leader candidate search (metered:420–434). The priced subclass calls the base refresh and then phase refresh whenever `phase_price_enabled` (priced:1066–1075); the phased adapter replaces this latter implementation.

|Channel / measurement boundary|Task and actual evaluation units|Process behavior|
|---|---|---|
|`_green_price_rollouts` (metered:593)|2 tasks per entry in `pts`; worker `_price_worker_green` (102) calls `_global_rollout_metrics_with_green` (576) once|New executor per batch at 623; `map` at 628|
|meter block in base `_maybe_refresh_signal_prices` (1364)|Parent `local_metering_costs`, one shared reference endpoint when points exist, then hi/lo endpoints for each noncollapsed ramp span; leaf `_global_rollout_metrics_with_metering` (646)|No metering price pool in this path|
|`_offset_walk_batch` (724) → `_price_batch` (673)|One task per signal; `_price_worker_offset_walk` (85) executes an adaptive cached walk. A task can call `_global_rollout_ttt_with_offset` (764) several times|New executor at 689; `map` at 694. Count actual offset endpoint leaves, not walk iterations or task count|
|`_vsl_price_rollouts` (adapter nested patched function:8355) → `_price_batch`|Original hi/lo corners at 8361; effective-control groups at 8383; only representatives at 8386 go to `_price_worker_vsl`|Same generic batch creator; expanded returned logical rows are not new endpoint evaluations|
|phased `_refresh_phase_prices` (adapter nested `patched`:2219)|Parent baseline endpoint at 2237, parent base local costs at 2258, one task for each valid phase direction at 2266, then parent moved local costs at 2280|`_phase_price_rollouts` (priced:923) creates a new executor at 955, task worker `_price_worker_phase` at 82|
|leader `_evaluate_candidate_set` (metered:2713)|Selected candidate list, then `_evaluate_full_candidate` calls; priced outer wrapper records per-candidate wall time and N_UF cache hit delta|Parent serial. Base `stackelberg_mpc` process/thread pools are not this override|
|PFO / base evaluation / phase refinement|`_evaluate_fallback_candidates`, `_leader_evaluation_base`, actual follower solve and `apply_phase_price_refinement` have separate nested calls|Do not count PFO as an ordinary `_evaluate_full_candidate` solely from candidate metadata|

A fresh pool is constructed for each parallel batch. Price pools are not persistent fields and `controller.close()` is not their shutdown boundary. Base persistent leader/grid pool helpers exist, but are not the active Wu price-pool lifecycle.

## Spawn, transfer, waiting, exit

1. The parent builds tasks and passes `(self, state, previous, forecast, parent_patch_present)` as initializer arguments. The controller contains cfg and worker bootstrap; its follower `__getstate__` drops `_phase_ctx_cache` (priced:215), but other serialized attributes remain. Do not equate the tiny bootstrap dictionary with total payload size.
2. Python 3.12.14 `ProcessPoolExecutor.submit` lazily creates spawn processes. `_spawn_process` calls `Process.start` then stores `self._processes[p.pid]` (stdlib process.py:791). Windows serializes process/initializer arguments during start. Each fresh worker imports Python/modules and unpickles the controller.
3. Controller `__setstate__` (priced:777) restores its dictionary, imports the adapter named in bootstrap, and calls `install_price_worker_runtime_patches` **before `_price_worker_init` runs**. The adapter delegates to `runtime_setup.install_worker_runtime` (202). This reinstalls signal/ready hooks, tau/far/legsplit/landing/freeway hooks, route/native accounting and area endpoint hooks from configured cfg; it does not rerun observation projection or measured parameter estimation.
4. `_price_worker_init` validates the restored marker then stores the fixed operating point in `_PRICE_WORKER_CTX`. `_process_worker` loops on `call_queue.get`, invokes the task, and sends result or exception. `_price_worker_phase`'s local variable named `pid` is a **phase ID**, not an OS process ID.
5. Current `pool.map` uses the stdlib default chunksize 1 and no timeout. Each task becomes a `_process_chunk` job containing one item. Returned results are consumed in submission order; waiting on an early result may coexist with later completed results. `Future.result` wall time is wait-inclusive, not worker compute time.
6. Exiting `with ProcessPoolExecutor(...)` calls `shutdown(wait=True)`. The manager wakes, sends sentinels, joins children; the parent joins its manager thread. `shutdown` time can include outstanding work, child exit and the newly enabled child profile export. Each batch's lexical elapsed time therefore includes more than model computation.
7. Batch errors are caught and the **whole batch** is recomputed serially, with `price_parallel_serial_rerun_count` and `price_parallel_last_error`. Some worker tasks may already have executed before the failed batch. Count attempted, completed and accepted computations separately; do not discard worker work from a failed attempt.

## Existing cProfile and lightweight next boundaries

Root's `decision_profile.py` starts from sitecustomize in parent and children. This includes unpickle / `__setstate__` / runtime bootstrap; an initializer-only profile would miss them. PID/PPID and per-process start/end perf timestamps already provide the process tree. Per-PID `_price_worker_green`, `_price_worker_vsl`, `_price_worker_offset_walk`, `_price_worker_phase` entries identify the channel used by that child. Repeated batches of one channel cannot be separated by aggregated pstats alone; do not invent their individual timings.

Keep production and the active profile run unchanged. If exact batch timing is needed in the next diagnostic run, the smallest read-only leaf instrumentation is:

- One parent event for enter/leave of `_green_price_rollouts`, `_offset_walk_batch`, the final VSL dedupe method, `_phase_price_rollouts`, `_refresh_phase_prices` and `_evaluate_full_candidate`. Include process ID, monotonic batch ID, channel, task count, begin/end perf time, completed/result count and exception. For a candidate record index/stage/N_UF and cache-hit delta, without copying the entire state.
- Wrap stdlib executor `__init__`, `_spawn_process`, `map` iterator consumption, and `shutdown` only in a diagnostic bootstrap. Retain actual arguments/order/results; restore on exit. After real `_spawn_process`, emit newly added child PID(s) and parent batch ID. `map` call-return timing alone measures eager submission, not the iteration wait; instrument the iterator separately. Do not consume it early or convert to a list.
- Count worker tasks by actual worker method invocations and endpoint leaves by `_global_rollout_*` / `_global_ttt_with_phases`. Root cProfile already counts these with no wrapper. If phase-local counts are required, include final `_phase_refine_signal_setup` / `_phase_local_cost_phased` wrappers and common `local_signal_service` leaves; cProfile uses their concrete file/line, not only repeated names such as `patched`/`cost`.
- Do not replace module-level worker functions with locally defined wrapper closures: spawn pickling and the VSL dedupe installer's captured `_price_worker_vsl` would make that incomplete or fail. Instrument their called class-method leaves or stdlib lifecycle. Phase uses an imported `_price_worker_init` alias too.
- **Historical assumption, corrected by the later experiment below:** “Parent main-thread cProfile excludes queue feeder/manager thread function bodies.” This is false for the installed Python 3.12.14 cProfile. The original recommendation against treating parent `submit` elapsed as pure pickle/IPC time still holds. No extra `pickle.dumps(controller)` should be inserted into the timed decision just to estimate bytes.

Do not sum process lifetimes or inclusive cumulative function times as a decomposition of decision wall time. Worker CPU totals can be summed as CPU-seconds; their overlapping wall times cannot. Profile export itself is timed separately by root's helper. Profiled vs unprofiled performance needs a matching decision later, not comparison to old benchmark comments.

## Counter interpretation and completion QA

`wu_price_rollout_count` is not a complete total: green successful parallel batches explicitly add task count to the parent (metered:643), whereas generic VSL/offset `_price_batch` returns worker values without returning their incremented counters. Phase assigns `len(tasks)+1` separately, overwriting on refresh; it is a planned evaluation count, not a sum of all attempts. The phase refresh happens after the base price metadata snapshot, so that snapshot can also predate a later phase batch failure. `price_parallel_last_error` is a string and the adapter exports only numeric result metadata (12670–12674). These are reporting limitations, not observed failures of the pending run.

Use actual per-PID pstats endpoint-leaf counts and channel-task counts to reconcile logical counts. Do not add both outer Ω endpoint wrapper calls and inner vendor endpoint calls: one physical evaluation traverses both. Use either the outer `area_runtime.evaluate_price_point` count or the vendor leaf count as the global total, then classify by parent leaf caller. Local cost evaluations and candidate cache hits are separate units.

Completion requires the parent exit/decision result, matched started/finished sidecars for every observed child PID, a readable pstats per completed process, and no surviving owned child. A missing child sidecar is not zero work. Group profiles by source/config SHA, channel and parent PID. Preserve the same input/control semantics and candidate result before comparing timings; no hotspot order or speedup claim is made in this audit.

## Later correction: cProfile thread attribution

Root's `probe_cprofile_thread_attribution.py/.json` reproduced child-thread function recording despite enable on main, with the child's real caller wrongly attributed to `threading.wait` (count zero). The installed CPython 3.12.14 implementation uses process-global monitoring and a single current profiler context. Thus earlier claims of main-thread-only cProfile coverage are withdrawn; function caller/cumulative attribution across threads is not reliable evidence of an isolated parent thread. Independent process CPU, lifetime timestamps and memory counters remain separate measurements. The original audit JSON/source pins remain historical. New `evaluation_trace.py` uses `sys.setprofile` main-thread call/return tracing per process and refuses occupied `sys.monitoring` tools, including cProfile tool 2. Its own timing includes diagnostic overhead and is not a normal benchmark.
