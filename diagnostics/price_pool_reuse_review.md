# Decision-scoped price-pool reuse: evidence and blocker

**Do not apply a simple cached-pool patch.** Reusing worker interpreters may be useful, but the current four pools receive different controller snapshots. Existing evidence does not yet prove that those snapshots and all worker runtime state can be exchanged without changing the computation. No production patch is generated in this bounded review. This is a missing preservation proof, not a claim that current price outputs are wrong.

The review reads only the completed dd13e08 cProfile run `wu-link_t900_beta300_20260910T032525335593Z`, the completed v1 trace `wu-link_t900_beta300_20260910T035232419561Z`, and the price-worker source. The producer loads no runtime controller and starts no worker, endpoint, MPC or VISSIM. New model evaluations are zero; pinned source changes are empty. It parses four representative trace contexts and the 34 existing worker pstats files, preserving source/evidence SHA256 in `price_pool_reuse_review.json`.

## What the existing code and record establish

| Batch order | Workers | Tasks | Entry point |
|---|---:|---:|---|
| Green | 10 | 34 | `_green_price_rollouts`, stackelberg_wu_metered.py:619–632 |
| Offset walk | 10 | 15 | `_price_batch` → `_price_worker_offset_walk`, :673–699 |
| VSL | 4 | 4 | `_price_batch` → `_price_worker_vsl`, :701–743 |
| Full phase vector | 10 | 63 | `_phase_price_rollouts`, priced_wu_link_controller.py:951–962 |

Each current batch constructs a new `ProcessPoolExecutor`, calls `pool.map` in the supplied task-list order, waits for completion and shuts down its processes before continuing. Offset tasks contain an entire signal's sequential relinearization walk; breaking that task into independent endpoints would change its algorithm. Meter-price global endpoints are currently serial, outside these four pools, and are not moved by this proposal.

Each initializer receives `(self, state, previous, forecast, expect_patch)` from that batch's then-current parent values. Unpickling `PricedWuLinkStackelbergController` invokes `__setstate__`, which reinstalls the canonical runtime from the pinned bootstrap; `_price_worker_init` then verifies the installed patch and sets process-local `_PRICE_WORKER_CTX`. Initializer verification is not a replacement for the earlier unpickle/bootstrap step.

The first recorded worker in each batch has identical captured cfg, physical state, forecast and previous-action value digests. **Controller digests differ in all four batches.** Relative to green, offset already contains the newly calculated scalar-green and meter prices/references; VSL additionally has offset price/reference; phase additionally has VSL price/reference. The read-only table in JSON records exact field digests and differences. V1 does not include the known `_prev_coupling` and `_wu._last_offramp_flow/_has_last_offramp_flow` operational fields, so these contexts are not a complete serialized-controller proof.

The price workers are narrower than follower candidates. Green/VSL/phase tasks call global endpoint methods; offset walks use the passed `lc_map` and global offset endpoint. They do not execute a fresh follower best response or consume every follower price field. Thus the differing controller fields do **not** by themselves prove differing numerical outputs for a stale-context reuse. They do prove that keeping the first entire initializer payload is not faithful preservation of the current payload. A reduced immutable price-kernel dependency contract could justify dropping unused fields later; that contract has not been implemented or validated here.

## Cost evidence, with its limits

Across the 34 existing single-worker profiles:

| Entry | Calls | Sum of inclusive profiled seconds | Per-process range |
|---|---:|---:|---:|
| `PricedWuLinkStackelbergController.__setstate__` | 34 | 7.7419543 | 0.1906322–0.4111717 |
| Canonical `install_price_worker_runtime_patches` | 34 | 7.7362047 | 0.1904070–0.4108273 |
| `_price_worker_init` | 34 | 0.0004647 | 0.0000089–0.0000332 |

Bootstrap installation is nested inside unpickling; these rows must not be added. Worker times overlap and include profiling overhead. They are not saved decision wall time. Every worker sidecar says bootstrap imports occurred before profiling, so these records do not measure full import/startup cost. The parent cProfile shutdown attribution was independently shown unreliable due to thread mixing; its ~124s is not a removable-pool-cost estimate.

No current actual serialized-initializer byte count was preserved. The vendor comment claiming a 610KB controller and 0.03s import/0.22s build is historical and is not evidence for today's much larger physical runtime. Trace JSON byte sizes are not pickle/IPC sizes. No new payload serialization or timing measurement was run here.

A single ten-worker process group would create 24 fewer interpreters than the observed 34, but may still need all 34 worker/batch context installs to reproduce fresh snapshots. The amount of wall time or transfer volume saved is therefore unknown. Re-pickling the full context for every task could increase transfer multiplicity from 34 initializer copies to as many as 116 task copies before transport reuse; that is a design risk, not a measured bandwidth result.

## Minimum safe design and the unresolved gate

Reuse **processes only within one decision**, while retaining the four batch barriers, original task lists, worker method semantics, ordered result reconstruction, parent counters and serial-fallback behavior. Do not share a follower instance between leader candidates or change their order. Two possible context mechanisms need proof:

1. A full **batch epoch** contains the original batch's value snapshot. Every task must identify that epoch, and each worker must verify/install it before executing its first task for that epoch. Sending N “update context” tasks to an N-worker pool is not a broadcast: one worker can run more than one while another sees none. A task-bound epoch check avoids that stale-worker gap. The full payload, bootstrap compatibility and any process-global state retained across epochs must be verified. Per-task full transport is simplest to reason about but may be expensive; shared memory or an epoch registry adds lifetime/cleanup obligations and should not be introduced without measurement.
2. A smaller **immutable global-price kernel contract** can contain only exact endpoint inputs and policy fields actually read by these four workers. It must preserve the original `_rollout_spec`, physical finalizer, runtime bootstrap and offset-walk arithmetic, not replace them with an approximate model. This requires explicit dependency and exact-output evidence; a controller-ID or partial-key cache is not sufficient.

Both designs need an exact comparison of all 116 existing task outputs and offset-walk sub-results, not just the selected command. It should use one recorded `PYTHONHASHSEED` set before parent/worker interpreter startup, preserving the prior unrelated one-ULP baseline diagnostic failure. Repeated bootstrap installation in a reused process must match the fresh-process worker contract, including cfg-bound class wrappers. Broken-pool, initializer failure, mid-batch task failure and decision exceptions must close only the owned process group and preserve the current explicit serial-retry counters/reason. No pool or handle should enter controller pickle state.

Those gates are currently unavailable from the retained v1 contexts, and root prohibited new model execution for this task. The source supports a future epoch-based experiment, but not an unqualified reuse patch today. Clock-cache application and its exact baseline comparison remain independent. This review intentionally leaves production, launcher, pool lifetime and worker code untouched.
