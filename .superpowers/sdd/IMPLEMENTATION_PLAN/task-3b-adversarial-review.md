# Task 3b Adversarial Review

**Verdict: CHANGES_REQUIRED**

The plan has materially improved, and the SC12 shared-lane interpretation itself is supported by the INPX. It is not yet promotion-safe: several mass, holdout, timing, ranking, SPSA, and runtime gates can pass while certifying the wrong behavior.

## Critical

### C1. The global mass equation can certify duplicated or lost internal transfers

**Plan references:** `IMPLEMENTATION_PLAN.md:184-191`, `IMPLEMENTATION_PLAN.md:197-213`, `IMPLEMENTATION_PLAN.md:506`.

`closing = opening + external_in + internal_in - internal_out - sink_out` is unsafe as a global identity. If one departure is inserted into two downstream stocks, independently logged `internal_in=2x` and `internal_out=x` makes the equation balance while total physical mass grows by `x`. Conversely, a dropped transfer can be hidden by a smaller `internal_in`. `N_unobservable` is also unconstrained and can become a balancing residual. The current implementation's post-update clip shows why a transfer-level contract is required (`vendor/NumSim-mine/src/models/urban_queue_model.py:1022-1032`). Lane-interval uniqueness alone does not prove transition conservation.

**Replacement text for B-1 (replace lines 197-213):**

```markdown
The projection ledger keys every scanned VISSIM vehicle by `(run_id, VehNo)` and maps it to exactly one physical stock. `N_unobservable` is not a residual: every such vehicle must occupy an explicit, typed external/origin stock with source evidence; otherwise projection is FAIL.

For every substep and stock `i`, record
`closing_i = opening_i + accepted_external_i - sink_i + sum_j F[j,i] - sum_k F[i,k]`.
Every internal transfer has one immutable `transfer_id`, one source debit, one destination credit, one vehicle amount, and one substep. The source and destination transfer multisets must be identical. The global identity is only
`N_physical_close = N_physical_open + accepted_external - sink_out`;
internal flow does not appear in the global equation. Rejected external demand remains in an explicit source/gate stock.

PASS: unique `(run_id,VehNo)->stock_id` mapping 100%; explicit unobservable stock coverage 100%; per-stock and global residual `<=1e-6 veh`; internal transfer multiset mismatch 0; duplicate/missing transfer IDs 0; clipped-away mass 0; forced split/merge/full-receiver fixtures preserve every vehicle.
```

### C2. The sealed holdout is reopened by the mandated defect loop

**Plan references:** `IMPLEMENTATION_PLAN.md:56-57`, `IMPLEMENTATION_PLAN.md:305-313`, `IMPLEMENTATION_PLAN.md:325-327`, `IMPLEMENTATION_PLAN.md:402`, `IMPLEMENTATION_PLAN.md:449-458`, `IMPLEMENTATION_PLAN.md:507`.

Seed 47 is called a sealed holdout, but J runs it, K exposes per-seed failures, and K then requires fixing and rerunning the related paired cells. That is iterative tuning on the holdout. A hash does not prevent access, and no fresh certification split is reserved. The summary also demands a calibration "holdout gate" although E-2 defines no holdout predictive statistic.

**Replacement text for E-1 and K:**

```markdown
Seeds 13/29 are development data: training and congested model/threshold selection. Before opening seed 47, freeze and hash source, topology, calibration, candidate set, perturbation sizes, metric definitions, thresholds, and auditor code. Seed 47 is a one-shot certification set and is not visible to fitting, threshold selection, candidate replacement, or the defect-fix loop.

If seed 47 fails a scientific gate, retire it. Any subsequent promotion attempt requires a new calibration version and predeclared fresh certification seeds (initially 59/71/89); the failed seed may remain diagnostic only. Rerun seed 47 only for a proven infrastructure failure that occurred before action application and could not depend on an outcome. K's defect loop runs development cells only. The promotion artifact records holdout-open time, access log, one-shot result, and retirement status.

Define the calibration holdout metrics and thresholds explicitly, or remove "holdout gate PASS" from the Gate Summary.
```

### C3. Prefix parity and the action epoch are still off-by-one compatible

**Plan references:** `IMPLEMENTATION_PLAN.md:385-404`, `IMPLEMENTATION_PLAN.md:398`, `IMPLEMENTATION_PLAN.md:424-425`.

"Anchor immediately after" and "first control epoch" do not identify whether the anchor second has completed, when the pre-action state is sampled, or which 60 state transitions are affected. The current stepwise runner demonstrates the hazard: at interval boundaries it calls `RunControllerDecision(stepNo)` before `RunSingleStep` (`scripts/run_real_world_stackelberg_controller_perf.vbs:365-378`), so the JSON label can be one second ahead of the COM state. A prefix can hash-match while plant and VISSIM apply the arm to different transitions. Delayed signal/offset activation can also make a nominal 60-second request have zero or more than 60 seconds of realized effect.

**Replacement text for J-1/J-2:**

```markdown
The canonical anchor is the COM state after the transition ending at `SimSec == anchor_sec` has completed. Pause VISSIM, capture and hash that pre-action physical state, then issue and read back the complete action before resuming. Prefix equality includes all samples through this pre-action anchor state. The first permitted arm/base state divergence is `anchor_sec+1`.

The action is valid for exactly the 60 transitions whose start times satisfy
`anchor_sec <= t < anchor_sec+60`; restore base before the transition starting at `anchor_sec+60`. Record `based_on_state_hash`, request time, valid interval, first/last effective transition, projected value, and COM readback. Plant replay uses the identical interval. Missing, early, late, partial, or stale actuation is FAIL; it is not repaired by shifting observation windows. A channel with cycle-boundary lag is evaluable only if its realized readback proves the same 60-transition contract.

Clock fixtures must cover anchors 900 and 2700, first affected states 901/2701, base restoration at 960/2760, and endpoints `anchor+60*H` for every H.
```

### C4. Ranking and spillback support can be manufactured by pooling correlated rows

**Plan references:** `IMPLEMENTATION_PLAN.md:424-442`, `IMPLEMENTATION_PLAN.md:449-450`, `IMPLEMENTATION_PLAN.md:509`.

The minimum 12 ranking cells are the three seeds times four anchors, but anchors from one 3,600-second run are correlated and `replicate` can inflate the count. "Each seed separately reported" is not a per-seed pass rule. Spearman is not defined as a within-prefix action contrast, so common baseline congestion can drive a high correlation even when action effects are wrong. Spillback "20 positives/20 negatives" does not define an independent episode: 20 one-second rows from one spillback event would pass, and pooling many easy links can hide failure at a critical ramp or boundary.

**Replacement text for J-3/J-4:**

```markdown
For ranking, compute `Delta J(action)=J(action)-J(base)` within the same prefix. A complete cell contains every predeclared feasible low/base/high arm; incomplete mandatory cells are BLOCKED, not dropped. Gate separately by `demand x H x channel x lever x seed`, then macro-average only already-passing seed strata. Each seed must contain all four anchors; repeats quantify replay noise and never increase support. Report run/seed-cluster confidence intervals. A tie is permitted only when the within-prefix contrast is below the preregistered replay-noise and material-effect thresholds.

Spillback support is counted by independent `(run_id, anchor, physical_stock_id)` episodes, with at most one positive and one negative label per episode; one-second rows are used only for onset/release time. Gate separately by the predeclared `demand x H x channel x asset-class` strata and report TP/FP/FN/TN plus distinct run, seed, anchor, and stock counts. Each mandatory congested stratum requires at least 20 VISSIM-positive and 20 VISSIM-negative independent episodes, F1 `>=0.80`, onset/release median absolute error `<=60 s`, and p90 `<=120 s`. No pooling across H, demand, channel, seed, or asset class can satisfy missing support. Insufficient mandatory support is BLOCKED.
```

### C5. The SPSA statistics have unit errors, selection freedom, and false independence

**Plan references:** `IMPLEMENTATION_PLAN.md:331-349`, `IMPLEMENTATION_PLAN.md:484-485`, `IMPLEMENTATION_PLAN.md:510`.

`MAD` from repeated objective evaluations has objective units, while `g_fd` has objective/action units; comparing them directly at lines 337-343 is dimensionally invalid. Excluding every `abs(g_fd)<=noise_floor` sample without a minimum material count allows a bad estimator to pass on an empty remainder. The plan gives no SPSA pair count, direction-batch count, finite-difference step-convergence check, confidence interval, or anti-cherry-picking rule. Multiple lever signs from one simultaneous perturbation are correlated, so treating them as independent Bernoulli trials invalidates the Clopper-Pearson bound. Existing source evidence already identifies cross-term bias even at `k=16/32` (`vendor/NumSim-mine/src/controllers/stackelberg_wu_metered.py:34-37`), so this is not theoretical.

**Replacement text for I-1:**

```markdown
Call one pure `evaluate_price_point(...)` for FD and SPSA and require byte-identical endpoint controls, objective components, feasibility, terminal state hash, and realized perturbation span. Compute objective noise `eps_J` from at least 20 identical-control evaluations per qualification state and coordinate noise `eps_g = 2*eps_J/realized_span`. Compare central FD at `h` and `h/2`; failure of the preregistered convergence tolerance is INDETERMINATE and BLOCKED for a required production coordinate.

Predeclare qualification states, direction seeds, and SPSA pair counts `k in {8,16,32,64}`. Use 30 independent direction batches per state and select the smallest passing k on development/selection data only. Require at least 12 state clusters spanning every demand, seed, H, channel, free/congested regime, and active/inactive barrier regime; require at least 29 material comparisons per channel. A required stratum below support is BLOCKED, not PASS.

Compute nRMSE and regression per `channel x demand x H`, with state-block bootstrap 95% intervals. Promotion requires the nRMSE upper limit `<=0.20`, the complete slope interval within `0.90..1.10`, and zero repeated material sign reversals. For an exact Clopper-Pearson sign bound, predeclare one coordinate per independent state-direction batch; never count multiple coordinates from the same SPSA pair as independent. Report all-coordinate sign rates separately with state-cluster intervals. Freeze k and every threshold before the sealed holdout.
```

### C6. The 30/45-second gate can pass via fast fallback or a narrowed clock

**Plan references:** `IMPLEMENTATION_PLAN.md:369-381`, `IMPLEMENTATION_PLAN.md:511`.

The proposed clock starts at the adapter entrance, while the current `154.746 s` evidence times the Python subprocess call (`scripts/run_real_world_stackelberg_controller_perf.vbs:653-689`) and still excludes pre-call state writing and post-call COM application. Changing the boundary can create an apparent speedup. The plan permits explicit production fallbacks because it only bans *silent* fallback and says "certification run fallback 0" without defining that subset. Pooling cold and warm decisions also permits one cold sample plus 99 warm samples. A timeout set at 45 seconds cannot include worker cancellation and safe fallback and still guarantee return by 45 seconds; on Windows, cancelling a future does not terminate a running worker.

**Replacement text for I-4:**

```markdown
Runtime is end-to-end monotonic time from the start of the anchor observation scan through validated COM action readback. Also report adapter-only and `decide_with_info` times, but they cannot satisfy the operational gate. Pass an absolute deadline to every scheduler task. Emit the soft event at 30 s; at 42 s terminate and recycle only the adapter/worker process tree, leaving VISSIM paused and alive, then reserve 3 s to generate, validate, apply, and read back fallback. Cleanup and fallback are inside the 45-second maximum; timeout samples are uncensored.

Benchmark nominal/congested x cold/warm as four separate strata on recorded target hardware, with at least 100 attempts and at least 10 independent VISSIM runs per stratum. Randomize blocked run order and record CPU, RAM, power state, worker count, process start method, and competing load. Controller-success latency and fallback latency are separate; a fallback never counts as a successful fast decision.

Promotion requires each stratum's run-cluster 95% upper confidence limit for p95 `<=30 s`, observed end-to-end max `<=45 s`, controller fallback rate `<5%`, timeout rate `<1%`, silent fallback 0, stale action 0, readback failure 0, orphan worker 0, and fault-injection recovery 100%. Missing or censored attempts are FAIL.
```

## Important

### I1. SC12 is shared through+left, but the plan turns a schedule equality into a false physical invariant

**Plan references:** `IMPLEMENTATION_PLAN.md:154-166`, `IMPLEMENTATION_PLAN.md:504`.

The integrated plan is correct to reject the left-only interpretation. Connector 10241 starts at EB lane 1 and has two connector lanes (`modi_eval_rw_control.inpx:13684-13703`), while 10242 separately starts at lane 2 (`:13706-13707`); therefore EB lane 2 can feed both straight connector lane 2 and the left connector. The WB geometry is analogous (`:13619-13639`, `:13662-13663`). However, heads 50201/50202 are distinct lane-2/lane-1 heads on SG5/SG2, and 50601/50602 are distinct heads on SG1/SG6 (`:29061-29068`). Their equality in the three current SIG programs is a native schedule fact (`network/real_world_gaepo_modi/개포동 test-bed5.sig:89-316`), not a physical requirement. SG2 and SG5 can physically differ by holding EB lane 2 red while serving lane 1; no network change is needed for that. A network/head change is needed only to give lane-2 through and lane-2 left different indications.

**Replacement text for S1-3 lines 158-162:**

```markdown
Lane 2 is one physical stock with through/left composition. EB lane-2 through and left both obey head 50201/SG5; WB lane-2 through and left both obey head 50601/SG1. Lane-1 through independently obeys SG2/SG6. Verify that SG2=SG5 and SG1=SG6 in every current native program and record this as a profile-specific stage-bundle policy, not a physical head invariant. Production may preserve that bundle; allowing SG2!=SG5 or SG1!=SG6 requires conflict/min-green/readback qualification but no lane/head network change. Separating lane-2 through from lane-2 left does require a new lane/head network profile.

PASS: exact connector-lane reachability, one lane-2 stock, route composition sum 1, lane-2 movements mapped only to their lane-2 head, and zero violation of the declared profile policy.
```

### I2. Boundary/ramp/freeway gates prove topology and aggregate flow, not backpressure

**Plan references:** `IMPLEMENTATION_PLAN.md:228-246`, `IMPLEMENTATION_PLAN.md:431-438`, `IMPLEMENTATION_PLAN.md:525`.

Coverage, coordinate, and aggregate-flow equality can all pass if downstream supply never constrains upstream sending. Network-wide WAPE can hide a blocked critical interface among many easy links. The plan also does not explicitly retain rejected boundary-in/freeway/ramp arrivals in source stocks, define merge competition, or test off-ramp blockage propagation. A finite `boundary_out` must represent the physical exit link; the sink beyond its downstream end must not acquire an invented finite queue.

**Replacement text to append to B-3/B-4:**

```markdown
External boundary, freeway-mainline, and ramp arrivals enter only when their first physical receiver accepts them; rejected arrivals remain in typed origin/gate stocks. At merges, all competing sending flows share one downstream receiving budget with a declared priority rule. At diverges, route-class FIFO/non-FIFO behavior is declared from lane connectivity; full off-ramp storage propagates upstream through exactly those blocked classes. A boundary-out stock covers only the actual in-network exit-link storage; its downstream sink is unbounded unless VISSIM contains an explicit downstream bottleneck.

Behavioral PASS fixtures: full urban receiver, full freeway merge receiver, full off-ramp storage, blocked physical exit link, and rejected external source. Each fixture must show the expected upstream queue increase and downstream-flow decrease, transfer-ledger conservation, no relocation, and no clipping. Paired promotion reports per-interface errors and macro/p95 across interfaces; network-wide WAPE alone cannot pass a boundary, ramp, off-ramp, or freeway gate.
```

### I3. The stated baseline omits 75 plant tests, and the canonical compiler command is currently invalid

**Plan references:** `IMPLEMENTATION_PLAN.md:90-97`, `IMPLEMENTATION_PLAN.md:126-128`, `IMPLEMENTATION_PLAN.md:472`, `IMPLEMENTATION_PLAN.md:502`.

The two discovery commands cover 21 `scripts/tests` methods and 10 `tests` methods, but omit 75 methods under `plant/tests`, even though the plan changes `plant/src/vissim_strict`. Thus "all 31/31" can pass with the plant kernel broken. Also, the cited compiler currently accepts positional `inpx` plus `--output` (`plant/src/vissim_strict/compiler.py:124-131`), not `--network ... --out`; the exact plan command fails unless the CLI is deliberately changed.

**Replacement text for the commands and PASS rule:**

```powershell
python -B scripts/verify_runtime_source.py --repo . --out outputs/runtime_source_v2_1.json
python -B -m unittest discover -s scripts/tests -v
python -B -m unittest discover -s tests -v
python -B -m unittest discover -s plant/tests -v
python -B -m plant.src.vissim_strict.compiler network/real_world_gaepo_modi/modi_eval_rw_control.inpx --output outputs/signal_reference_v2_1.json
```

```markdown
PASS: every discovered test in all three roots passes; discovered/executed/skipped counts are recorded and skipped or unexpectedly undiscovered tests are FAIL. Mark `scripts/verify_runtime_source.py` explicitly as a new deliverable. If the compiler CLI is intentionally changed, add a CLI contract test and keep the command above synchronized with it.
```

## Minor

### M1. Objective-weight normalization conflicts with objective exclusion

**Plan references:** `IMPLEMENTATION_PLAN.md:34-41`, `IMPLEMENTATION_PLAN.md:186-191`, `IMPLEMENTATION_PLAN.md:230-235`.

Requiring every stock's `objective_weights` to sum to one conflicts with the allowed exclude mode for boundary/exit stocks, where all objective weights may legitimately be zero. This can force hidden attribution merely to satisfy topology.

**Replacement text for A-2 PASS:**

```markdown
PASS: physical lane-interval missing/duplicate 0; ownership-attribution weights sum to `1 +/-1e-9`; objective weights are validated per named mode and sum to either 1 for included stocks or 0 for explicitly excluded stocks; objective mode never changes the physical state/flow trace.
```

## Falsification Result By Requested Area

| Area | Result |
|---|---|
| SC12 shared through+left geometry | Supported by connector lane count and lane-head evidence |
| SC12 SG coupling | Overstated; pair equality is policy/schedule, not physical necessity |
| One-vehicle-one-stock conservation | Falsified by aggregate internal-flow accounting loophole |
| Boundary/ramp/freeway backpressure | Not proven by current gates |
| Train/holdout separation | Contradicted by K's rerun loop |
| Paired t=0 replay/action epoch | Prefix intent is sound; executable clock remains ambiguous |
| Per-stratum ranking/spillback support | Falsified by pooling and pseudoreplication loopholes |
| Exact FD versus SPSA statistics | Not statistically qualified as written |
| 30/45-second runtime gate | Can be gamed by clock narrowing, pooling, and explicit fallback |

**Final verdict: CHANGES_REQUIRED.**
