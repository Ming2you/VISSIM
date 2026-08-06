# Task 3a - Specification and Document-Quality Review

Reviewed read-only against:

- `.superpowers/sdd/IMPLEMENTATION_PLAN/task-3-review-brief.md`
- `.superpowers/sdd/IMPLEMENTATION_PLAN/task-2-integration-brief.md`
- `.superpowers/sdd/IMPLEMENTATION_PLAN/task-2-integration-report.md`
- `IMPLEMENTATION_PLAN.md` (544 lines, working-tree version)

Repository inspection was limited to checking referenced paths and CLI definitions; no
plant source or evidence artifact was changed.

## Overall verdict

**CHANGES_REQUIRED**

**SPEC COMPLIANCE: FAIL**

**DOCUMENT QUALITY: FAIL**

The opening purpose is correct: lines 9-28 define a controller-independent rollout
plant that predicts the consequences of candidate controls while MPC owns action
selection. The plan is nevertheless not approvable because binding SC12 connectivity is
reversed, calibration data are reused for certification, offset promotion is circular,
required dynamic/SPSA/runtime gates are incomplete, and most blocking tasks are not
executable task specifications.

## Binding-requirement audit

| Requirement | Verdict | Plan evidence / problem |
|---|---|---|
| MPC rollout plant, not trajectory clone or audit-only model | PARTIAL | Purpose passes at 9-28; final deliverables at 536-542 omit the production rollout API/controller integration and read like an evidence-only closeout. |
| Conservation, signal/time semantics, congestion, lever effect, latency | PARTIAL | Correct invariants are stated at 23-28, but the quantitative dynamic and latency contracts are incomplete. |
| S0 remains open until tests/source/strict runner/canonical signal/SC12 pass | FAIL | 73-118 permit S0R to precede S1; canonical signal and SC12 remain in S1 at 119-166. |
| SC12 exact source-lane connector sets | FAIL | 154-159 incorrectly make lane 2 shared with straight connectors. Required sets are 50201 -> `{10242}` and 50601 -> `{10240}`. |
| One physical stock; ownership/visibility/control/objective are views | PASS | 34-41 and 184-213 state the correct ontology and mass contract. |
| Calibration and certification disjoint by whole run | FAIL | E uses seeds 13/29 for fitting and J reuses 13/29 in the promotion matrix at 402-406. |
| Native per-SC cycles before native fidelity; 150 s cannot promote native | PASS | 268-274, 462-469, and 484-492 express the intended separation, subject to graph corrections below. |
| Offset disabled per profile until same-profile timing/readback/effect/ranking | FAIL | Production disablement is stated, but 413 allows offset only "after profile gate" while 295 requires offset futures to establish that gate. |
| Paired VISSIM futures replay from t=0 with identical prefix | PASS | 385-398 are directionally correct; the run identity and replay-noise schema still need strengthening. |
| Exact FD/SPSA use identical production endpoint/objective and compare final decisions | FAIL | 331-358 state the principle but omit binding endpoint fixtures, sample counts, deterministic coordinates, and exact certification/fallback parity. |
| Runtime around production `decide_with_info`, 45 s hard deadline, explicit fallback, no silent parallel fallback | FAIL | 360-381 omit an absolute deadline, adapter kill/reserve behavior, fallback order, low-demand strata, and readback-complete latency. |
| Every blocking task has seven-field executable contract | FAIL | Only S0R-1 and S1-1 show commands; one command names a missing file and the other uses invalid current CLI flags. |
| Body, gates, graph, traceability, and promotion semantics agree | FAIL | The graph has missing/circular edges; K excludes low demand in one sentence and says it is not waived in the next; the traceability table does not map the 14 binding requirements. |

## Critical findings

### C1. SC12 exact-lane topology is factually wrong

**Location:** `IMPLEMENTATION_PLAN.md:150-166`

Lines 154-159 assign straight connectors 10241/10238 to source lane 2 and call both
changed lanes shared straight-left lanes. The exact INPX lane ranges establish that
10241/10243 and 10238/10239 start from lane 1. Source lane 2 reaches only 10242 on the
eastbound side and 10240 on the westbound side. The plan therefore violates the
explicit task-3 binding requirement and would build the wrong movement authority into
the rollout plant. The equality constraint at 161 also turns an observed fixed-program
timing equality into an unjustified MPC action constraint.

**Replacement text for 150-166:**

```markdown
### S1-3. SC12 exact-lane head resolution

- Head `50201` is on `1220012103/2` (SC12/SG5). Its exact-lane downstream
  connector set is exactly `{10242}`, the EB left-turn route. Connectors `10241`
  and `10243` start from source lane 1 and are not controlled by this head.
- Head `50601` is on `1220013600/2` (SC12/SG1). Its exact-lane downstream
  connector set is exactly `{10240}`, the WB left-turn route. Connectors `10238`
  and `10239` start from source lane 1 and are not controlled by this head.
- Approach-level `relFlow` is demand evidence only and may not override exact
  lane-to-connector connectivity. Each physical lane stock still exists once;
  no link-level connector union may create movement membership.
- Record that SG2/SG5 and SG1/SG6 have zero native timeline difference in
  programs 1/2/3, but do not convert that fixed-program observation into an MPC
  equality constraint.

NEW artifact: `reports/sc12_head_resolution_v2_1.json`.
PASS requires head 50201 set exactly `{10242}`, head 50601 set exactly `{10240}`,
wrong-lane connector count `0`, resolved turn class `LEFT` for both heads,
unresolved SC12 heads `0`, and SG2/SG5 plus SG1/SG6 timeline delta `0 ms` in
programs 1/2/3. Any mismatch is FAIL and blocks topology, movement mapping, and
all SC12 paired-future runs.
```

### C2. S0 can close before canonical signal and SC12 evidence

**Location:** `IMPLEMENTATION_PLAN.md:73-119`, `IMPLEMENTATION_PLAN.md:473-478`

S0R contains source/tests/provenance and then hands off to S1, where the canonical
signal reference and SC12 decision remain open. That ordering violates the binding rule
that S0 is not complete while canonical signal or SC12 evidence is unresolved.

**Replacement text after line 77:**

```markdown
S0R remains `OPEN` until S0R-1/S0R-2/S0R-3, the canonical signal-reference
generator and validation, the time-indexed active-program/readback lock, and the
SC12 exact-lane artifact all PASS against one provenance fingerprint. A subsection
PASS does not close S0R. No topology, movement, dynamics, calibration, SPSA, or
promotion run may cite S0 as complete before this compound closure gate passes.
```

Also replace the first dependency edge at 474-475 with:

```text
S0R source/tests/strict provenance + canonical signal/program reference
    + SC12 exact-lane resolution
  -> A/C physical and signal-model work
```

### C3. Calibration runs are reused as certification evidence

**Location:** `IMPLEMENTATION_PLAN.md:56-57`, `IMPLEMENTATION_PLAN.md:305-313`,
`IMPLEMENTATION_PLAN.md:402-406`, `IMPLEMENTATION_PLAN.md:449-450`

Seeds 13 and 29 are used to fit/select physical parameters and then reused in J/K's
promotion matrix. Merely rerunning a deterministic seed under a different directory does
not make its state/future independent. This violates whole-run separation and permits
training behavior to influence certification.

**Replacement text for 303-313 and the J seed row:**

```markdown
### E-1. Disjoint whole-run split

| phase | demand | seeds | use |
|---|---|---|---|
| calibration training | 0.75, 1.0 | 13, 29 | fit only |
| calibration selection | 1.25 | 13, 29 | estimator/model selection only |
| sealed certification holdout | 0.75, 1.0, 1.25 | 47, 59, 71 | thresholds and promotion only |

The six calibration parents and nine certification parents have disjoint run IDs,
RNG seeds, telemetry, anchors, and future branches. Certification manifests are
inaccessible to fit/model/threshold-selection code until the calibration JSON and
its hash are frozen. Calibration runs may be reported diagnostically but can never
count toward a promotion sample or rescue a certification failure.

J promotion matrix: demands `0.75/1.0/1.25`, certification seeds `47/59/71`,
anchors `900/1500/2100/2700`, and H `1/3/5/10/15`.
```

### C4. One-step/multi-step gates are incomplete and failures can be pooled away

**Location:** `IMPLEMENTATION_PLAN.md:424-442`, `IMPLEMENTATION_PLAN.md:449-450`,
`IMPLEMENTATION_PLAN.md:508-509`

The table does not define normalized-error denominators, H-specific queue/count/speed
growth limits, signed bias, GEH coverage, zero-observation handling, or per-seed blocking
rules. Line 424 requires reporting by seed/channel/lever, but reporting is not gating.
Line 440 pools seed/anchor cells, and line 449 requires only nominal/congested seeds even
though line 450 says low demand is not waived. This violates the no-pooling and restored
quantitative-gate requirements.

**Replacement text for 424-442:**

```markdown
Every raw comparison is keyed by demand, certification seed, anchor, H, channel,
lever, entity, and interval. Overall aggregates are descriptive only. For each
`demand x H x channel x lever` stratum, all 12 seed/anchor pairs must be complete;
each seed is gated separately and may not exceed `1.25 *` the stated aggregate
limit. An H=1, demand, seed, channel, lever, invariant, or material-sign failure
cannot be rescued by another stratum.

Definitions: `NMAE=sum(abs(pred-obs))/max(sum(obs),1 veh)`; a zero-observation
stratum additionally requires MAE `<=1 veh`. Count percentage terms use observed
mean count. Speed MAPE is vehicle-weighted with denominator
`max(observed_speed,5 km/h)`. TTT APE uses
`max(observed_TTT,1 veh*h)`. Every absolute metric also reports signed bias.

Promotion gates:

| Horizon | Required gate |
|---|---|
| H=1 | urban queue/storage NMAE `<=15%`; travel-time median `<=5 s`, p95 `<=15 s`, queue-tail MAE `<=20 m`; freeway speed MAPE `<=10%`; count MAE `<=max(5 veh,10%)`; flux GEH `<=5` for `>=85%` of entity-interval rows and signed total-flow bias `<=10%`; total/freeway/urban TTT APE `<=10%` |
| H=3 | cumulative TTT APE `<=12%`; terminal urban queue/storage NMAE `<=20%`; speed MAPE `<=15%`; count MAE `<=max(7.5 veh,15%)`; H=1 flux GEH/bias limits retained |
| H=5 | cumulative TTT APE `<=15%`; terminal urban queue/storage NMAE `<=20%`; speed MAPE `<=15%`; count MAE `<=max(7.5 veh,15%)`; H=1 flux GEH/bias limits retained |
| H=10 | cumulative TTT APE `<=18%`; terminal urban queue/storage NMAE `<=35%`; speed MAPE `<=20%`; count MAE `<=max(10 veh,20%)`; no non-finite/negative state, clipping, capacity, or mass failure |
| H=15 | cumulative TTT APE `<=20%`; terminal urban queue/storage NMAE `<=35%`; speed MAPE `<=20%`; count MAE `<=max(10 veh,20%)`; no non-finite/negative state, clipping, capacity, or mass failure |

Urban/ramp boundary-flow WAPE must be `<=10%`; off-ramp WAPE `<=15%`.
Ranking is gated independently for every horizon and demand and for every isolated
channel. Each channel has at least 24 material comparisons, Spearman rho `>=0.70`,
top-action pairwise agreement `>=0.80`, and repeated material sign reversals `0`;
each seed must pass. H=1 passes independently.

Low-demand gates are required exactly as above. Only low-demand spillback may be
`NOT_EVALUATED` when fewer than five positive events exist. Congested certification
requires at least 20 positive and 20 negative episodes, F1 `>=0.80`, and onset and
release MAE `<=60 s`; insufficient support is `BLOCKED`.
```

### C5. SPSA qualification and production-decision parity are not executable or strong enough

**Location:** `IMPLEMENTATION_PLAN.md:331-358`

The plan leaves `numeric_tolerance`, repeat count, perturbation sizes, direction-batch
count, state count, and the N-phase basis undefined. "Material mean sign reversal 0" can
hide lever-level reversals. Production parity allows 5% selected-action mismatch and
does not require exact status, safety certificate, fallback class, or certification
parity. These are binding omissions.

**Replacement text for I-1/I-2:**

```markdown
FD and SPSA call one production `evaluate_price_point(state, previous, forecast,
control, objective_spec)` endpoint. It returns final-state hash, every objective
component, feasibility, clipping, safety/certification result, and total objective.
For an identical physical endpoint, control payload, final-state hash, objective
components, and feasibility must be byte-identical; one mismatch is FAIL.

Use at least 12 qualification states spanning all demands, certification seeds,
free/congested anchors, and active/inactive barrier/hinge/far terms. Use 20 null
repeats per state, SPSA pair counts `{8,16,32,64}`, and 30 independent deterministic
direction batches per state and k. Set `numeric_tolerance=1e-12` for deterministic
objective arithmetic and record the realized perturbation span. A coordinate is
material only when `abs(g_fd)*realized_span >= max(5*eps_J,
0.005*max(abs(J0),1))`, with `eps_J=max(q99(abs(J_r-J_1)),
1e-9*max(abs(J_1),1))`.

For an N-stage signal use a deterministic Helmert `(N-1)` tangent basis with
`1^T B_N=0`; project `g0+B_N*q` onto the bounded simplex. Test N=2/3/4/5/6 and
every active N. Bound-collapsed coordinates are ineligible, not zero gradients.

Select the smallest k for which every demand/H/channel report passes: reversals
`0`; nRMSE `<=0.20`; slope and its confidence interval inside `0.90..1.10`;
median normalized error `<=0.15`; p95 `<=0.35`; overall one-sided exact 95%
Clopper-Pearson sign-error upper bound `<=0.05` with at least 59 material
comparisons; and each channel has at least 29 material comparisons, reversals `0`,
and sign-error upper bound `<=0.10`.

Then run production `decide_with_info` FD/SPSA twins over 36 sealed certification
states and three independent SPSA direction seeds (`n=108`), resetting sidecars.
Controller status, feasibility, safety certificates, fallback class, selected
leader candidate, spillback guard, and meter certification must match in 108/108.
Command payloads must match exactly or differ by one declared quantization step
with exact-FD rescored regret below `max(2*eps_J,0.5%*abs(J_FD))`; every material
selected-versus-runner-up ordering must match. SPSA remains OFF until estimator
and decision artifacts PASS on the same source/objective hash.

NEW command/artifacts: `scripts/run_spsa_fd_parity.py`,
`spsa_fd_parity.json`, `production_decision_parity.jsonl`, and
`production_decision_parity_summary.json`.
```

### C6. Runtime lacks the binding deadline and fallback behavior

**Location:** `IMPLEMENTATION_PLAN.md:360-381`

The plan records a hard limit but not an enforceable absolute deadline. Its measurement
ends at `decide_with_info` return rather than action parse/apply/readback, it has no
adapter kill point or fallback reserve, and it never defines the fallback action. It
also benchmarks only nominal/congested strata, allowing low-demand or seed failures to
remain invisible.

**Replacement text for I-4:**

```markdown
Record two nested clocks: (1) exact production `decide_with_info` call entry to
return/fallback result, and (2) end-to-end anchor observation scan through validated
COM action readback. The adapter receives an absolute monotonic deadline. Emit a
target-overrun event at 30 s; at 42 s terminate only the adapter/worker process tree
and reserve 3 s to issue and validate fallback. VISSIM remains alive and paused.

Fallback order is: first, reissue the last feasible command against the current
state with a new action ID/hash/validity and rerun safety/readback checks; second,
use the validated native fixed plan; third, after two consecutive failures or any
hash/signal/mass/stale-state violation, latch the fixed plan until an explicit
healthy decision clears it. Never reuse an old CSV/hash and never leave an interval
uncontrolled. A fast fallback does not count as a successful controller decision.

Collect at least 100 production H=3 end-to-end decisions over all three demands
and all certification seeds, at least 10 per demand/seed stratum, with cold and
warm samples. Every stratum requires p95 `<=30 s` and max `<=45 s`; overall p50
`<=15 s`, controller fallback rate `<5%`, timeout rate `<1%`, silent fallback `0`,
stale action `0`, readback failure `0`, and fault-injection recovery `100%`.
Certification decisions used as performance evidence require fallback count `0`.
Workers 0/1/2/5 must retain exact selected action and objective/price tolerance
`<=1e-9`; parallel failure may not trigger silent serial recomputation.
```

### C7. Offset qualification is circular

**Location:** `IMPLEMENTATION_PLAN.md:289-299`, `IMPLEMENTATION_PLAN.md:408-416`,
`IMPLEMENTATION_PLAN.md:481-491`

D requires forced low/base/high offset futures before enablement, but J permits offset
arms only after the profile gate. The dependency graph also places all of D before J and
then requires D+J for offset. No run can legally produce the evidence needed to unlock
the writer.

**Replacement text for line 413 and D's release paragraph:**

```markdown
- offset certification arm: the isolated certification harness may issue
  `base-10/base/base+10 s` modulo the native cycle through a test-only writer after
  canonical timing, sign, activation-boundary, conflict, and readback pre-gates pass.
  The production writer remains `intent_only` during these runs.

Define `D-core` as timing/readback/sign/native-cycle/conflict validation. `D-core`
precedes J. Define `D-offset-enable` as same-profile `D-core` PASS plus J's offset
effect magnitude/ranking PASS plus runtime PASS on the same hashes. Only
`D-offset-enable` may release the production offset writer. Normalized-150 s
evidence never satisfies either native gate.
```

### C8. The dependency graph permits invalid ordering and contradicts itself

**Location:** `IMPLEMENTATION_PLAN.md:471-496`

C maps connectors to destination stocks but depends only on S1, not A's stock topology.
I claims to evaluate the production objective but depends only on C plus an abstract
objective, not the implemented A/B/E dynamics. J appears once before I and again after
"all ... SPSA/runtime prerequisites," so it is unclear whether J is a plant test or a
controller-promotion test. D/J also form the offset cycle above.

**Replacement text for 473-493:**

```text
S0R compound closure
  -> A-1 lane-route graph -> A-2 one-stock topology
  -> S1/C canonical signal, active program, native cycles

A-2 -> B projection/conservation -> B boundaries/ramps/freeway -> E frozen calibration
S1 + A-2 -> C movement/SG mapping + monitor schedule + action schema
S1 + C -> D-core timing/readback/sign/conflict gates

A-2 + B + C + D-core + E
  -> production controller-independent rollout endpoint/objective
  -> J paired-future harness and native non-offset plant gates

production rollout endpoint/objective
  -> I exact-FD/SPSA estimator qualification
  -> I production-decision parity
  -> I unified scheduler and runtime/fallback gate

J native plant gates + I decision parity + I runtime/fallback + strict provenance
  -> K strict complete audit -> native MPC promotion

D-core + J offset-specific effect/ranking + I runtime
  -> D-offset-enable for that exact network profile only

X-2 normalized-150 s -> separate report only; no native promotion edge
```

## Important findings

### I1. Calibration omits binding storage-fraction and ramp-capacity acceptance thresholds

**Location:** `IMPLEMENTATION_PLAN.md:315-327`, `IMPLEMENTATION_PLAN.md:507`

E records storage/discharge values but gates only jam-density uncertainty, prior
distance, cross-seed variation, and fallback-use fraction. There is no holdout verdict
for queue/storage split quality or per-ramp storage/discharge capacity, despite the
binding requirement and the Gate Summary's unsupported claim that a holdout gate exists.

**Replacement text after line 327:**

```markdown
Holdout PASS additionally requires: physical-capacity exceedance in `<=0.5%` of
stock-time rows with all excess conserved upstream/overflow; where queue split is
observed, queued-vehicle MAE `<=max(2 veh,10% of observed queue)` and signed bias
`<=5%`; every promoted storage-fraction estimate has 95% CI half-width `<=10%`;
each ramp/boundary storage and discharge-capacity estimate has 95% CI half-width
`<=15%`, holdout discharge WAPE `<=10%`, and signed bias `<=5%`. Missing support,
CI, source run IDs, or a failed per-stock gate is BLOCKED, never replaced by a
pooled average.
```

### I2. Named commands and paths are not executable as written

**Location:** `IMPLEMENTATION_PLAN.md:88-94`, `IMPLEMENTATION_PLAN.md:99-109`,
`IMPLEMENTATION_PLAN.md:123-128`, `IMPLEMENTATION_PLAN.md:172-186`

Repository checks found:

- `scripts/verify_runtime_source.py` does not exist and is not marked NEW.
- The current compiler accepts positional `inpx` and `--output`; line 127 uses
  unsupported `--network` and `--out`.
- `scripts/audit_plant_fidelity.py` has `--strict` but no `--require-complete`.
- `scripts/run_plant_fidelity_matrix.ps1` invokes the auditor without either strict
  option and has no `-Strict/-RequireComplete` parameters.
- `scripts/compile_physical_stock_topology.py` does not exist and is not marked NEW.
- `python` is not resolvable in the review shell, while the repository runner already
  recognizes `RW_PYTHON_EXE`; the plan has no interpreter preflight.

**Replacement text:**

```markdown
NEW paths/CLI work required before command execution:
`scripts/verify_runtime_source.py`, `scripts/compile_physical_stock_topology.py`,
auditor `--require-complete`, and runner `-Strict/-RequireComplete` parameters.
The interpreter preflight requires `RW_PYTHON_EXE` to name an existing executable
and records its path/version/hash; no bare-`python` fallback is allowed in strict mode.

```powershell
$python = $env:RW_PYTHON_EXE
if (-not $python -or -not (Test-Path -LiteralPath $python)) { throw "RW_PYTHON_EXE is required" }
& $python -B scripts/verify_runtime_source.py --repo . --out outputs/runtime_source_v2_1.json
& $python -B -m plant.src.vissim_strict.compiler network/real_world_gaepo_modi/modi_eval_rw_control.inpx --output outputs/signal_reference_v2_1.json
powershell -NoProfile -File scripts/run_plant_fidelity_matrix.ps1 -Strict -RequireComplete
```

Each NEW CLI must have a `--help`/dry-run contract test before its acceptance
command is considered executable.
```

### I3. The universal seven-field promise is not instantiated per task

**Location:** `IMPLEMENTATION_PLAN.md:65-71` and all blocking subsections

The document says every task will contain seven fields, but S0R-2, S0R-3, S1-2,
S1-3, A-1/A-2, B-1 through B-4, C-1 through C-4, D, E, I-1 through I-4, J-1
through J-4, K, and X do not each provide a concrete command, schema, dependency, and
stop condition. A global promise is not an executable task specification.

**Replacement text for 65-71:**

```markdown
Every blocking subsection ends with an `Execution contract` table containing
nonempty cells for `inputs+hashes`, `implementation paths`, `command`,
`artifact+schema/version`, `PASS/FAIL/NOT_EVALUATED rules`, `prerequisites`, and
`stop condition`. A baseline-missing path or flag is prefixed `NEW`. A task is
`NOT_READY`, and no downstream artifact may consume it, until all seven cells are
concrete and its command has a parser/dry-run test. The common rules in this section
do not substitute for task-local entries.
```

The next revision must add those task-local tables; inserting only this policy text is
not sufficient for approval.

### I4. Canonical run identity and replay-noise evidence are under-specified

**Location:** `IMPLEMENTATION_PLAN.md:387-398`, `IMPLEMENTATION_PLAN.md:415-425`

The key omits active-program schedule, adapter/controller/NumSim hashes, exact action
payload hash, validity interval, and controller entry point. A capped/retried low/high
arm can therefore collide with another run under the same `level`. `replicate` exists
but no replicate count or base-repeat noise procedure is specified, so `paired noise
floor` at 425 is undefined.

**Replacement text for 391-398 and the tie sentence:**

```text
(experiment_id, network_profile_hash, inpx_hash, signal_set_hash,
 active_program_schedule_hash, topology_hash, calibration_hash,
 adapter_hash, controller_hash, numsim_hash, demand, seed, anchor_sec, H,
 channel, lever_id, action_payload_hash, valid_from_sec, valid_until_sec,
 replicate)
```

```markdown
Run three independently scheduled base repeats per certification parent/anchor.
Define `eps_J=max(1e-6 veh*h,q95(abs(J_base_i-J_base_j)))`. A comparison is
material only when the VISSIM objective difference exceeds both `2*eps_J` and
`0.5%*max(abs(J_base),1 veh*h)`; otherwise it is `INDETERMINATE`, not a correct
tie. Every retry receives a new action-payload hash and run key.
```

### I5. Initial acceptance and promotion semantics conflict

**Location:** `IMPLEMENTATION_PLAN.md:144-145`, `IMPLEMENTATION_PLAN.md:255-258`,
`IMPLEMENTATION_PLAN.md:429-442`, `IMPLEMENTATION_PLAN.md:500-511`

The plan does not say whether promotion inherits initial gates. The ranking table places
Spearman only under initial acceptance while the summary requires both Spearman and
pairwise. Exact mapping is a 100% "target" but artifact generation tolerates unresolved
mass below 0.1%/1.0%. Signal event error is a 0.5 s "target," while S1 can leave it
NOT_EVALUATED at 1 Hz. These ambiguities can change the promotion result.

**Replacement text before the gate table at 429:**

```markdown
`Initial acceptance` is diagnostic and never authorizes production promotion.
`Promotion` is the conjunction of every initial gate and every promotion-only
gate. Movement mapping promotion requires exact coverage `100%` and unresolved
vehicle mass `0`; the 0.1%/1.0% limits are collection-only stop thresholds.
Native signal promotion requires event error `<=0.5 s`; a 1 Hz-only profile leaves
that gate `NOT_EVALUATED` and therefore BLOCKED. Except for the declared low-demand
spillback support exception, any required `NOT_EVALUATED` blocks promotion.
```

### I6. Final deliverables still describe an audit package, not the implemented rollout plant

**Location:** `IMPLEMENTATION_PLAN.md:536-544`

The opening purpose is appropriate, but the final list contains reports, evidence,
artifacts, a promotion record, and tests only. It does not name the production rollout
plant API, controller-independent dynamics implementation, MPC integration, action
writer, or deployed startup guard as required deliverables. That allows an audit-only
package to satisfy the written closeout.

**Replacement text for 536-542:**

```markdown
## Final deliverables

- Production controller-independent rollout implementation: projection, one-stock
  dynamics, signal/native-cycle semantics, lever response, boundaries/backpressure,
  and frozen-calibration loader, with the exact source paths and hashes listed.
- Production MPC integration through the unchanged `decide_with_info` entry point;
  MPC selects actions while the plant only evaluates candidate futures.
- Fail-closed Python/PowerShell/VBS action writer and profile-scoped startup guards
  for source, signal, topology, calibration, SPSA, runtime, and offset promotion.
- Unit/integration/paired-future/runtime tests proving the production code path,
  followed by `reports/plant_fidelity_audit_v2_1.md` and its hash-bound evidence
  manifest. Audit artifacts certify implementation; they are not a substitute for it.
```

### I7. The traceability table does not map the 14 binding requirements

**Location:** `IMPLEMENTATION_PLAN.md:513-534`

The requested deliverable was a v2-to-v2.1 table mapping each task-2 binding requirement
1-14. The current table instead lists 18 historical defects. Several rows claim coverage
that the body does not provide, especially calibration holdout thresholds, complete
dynamic gates, SPSA counts/parity, runtime fallback, per-task execution contracts, and
dependency/promotion consistency.

**Replacement table structure:**

```markdown
| Binding requirement | Normative sections | Commands/artifacts | Status |
|---:|---|---|---|
| 1 | S0R closure | runtime source, baseline tests, strict manifest | OPEN |
| 2 | S0R/S1 exact signal and SC12 | signal reference, SC12 exact-lane report | OPEN |
| 3 | S1 active-program schedule | signal reference/readback artifact | OPEN |
| 4 | A/C one-stock and movement coverage | topology/mapping artifacts | OPEN |
| 5 | B-2 speed-delay evolution | kinematics tests/report | OPEN |
| 6 | B-3/B-4 finite boundaries/backpressure | boundary/ramp artifacts | OPEN |
| 7 | E calibration/holdout | frozen calibration and holdout verdict | OPEN |
| 8 | C-3/D/X native cycle and offset | profile timing/effect records | OPEN |
| 9 | J replay/action/run schema | paired-future request/manifest | OPEN |
| 10 | B/J/K quantitative dynamics | dynamic gate report | OPEN |
| 11 | I-1/I-2 SPSA parity | estimator and decision artifacts | OPEN |
| 12 | I-3/I-4 scheduler/runtime | scheduler/runtime/fallback artifacts | OPEN |
| 13 | task-local execution contracts | seven-field table for every task | OPEN |
| 14 | dependency graph/K promotion | strict complete audit | OPEN |
```

### I8. The fixed 31-test gate can ignore all new v2.1 tests

**Location:** `IMPLEMENTATION_PLAN.md:90-97`, `IMPLEMENTATION_PLAN.md:458`,
`IMPLEMENTATION_PLAN.md:502`

`31/31` is the required baseline regression count, not the complete future suite. The
plan adds signal, topology, conservation, delay, SPSA, scheduler, fallback, and paired
future behavior but gives no aggregate command or zero-failure rule for those new tests.

**Replacement text for the S0R PASS sentence and Gate Summary:**

```markdown
PASS requires the immutable baseline suites `31/31` plus every NEW v2.1 unit,
contract, spawn-safety, fault-injection, and integration test at `0` failures.
The manifest records baseline and added-test counts separately; adding tests never
changes or dilutes the 31-test baseline denominator.
```

## Minor findings

### M1. The final audit output path would overwrite the baseline audit input

**Location:** `IMPLEMENTATION_PLAN.md:5`, `IMPLEMENTATION_PLAN.md:538`

The plan cites `reports/plant_fidelity_audit.md` as an input and again names it as the
final output. Preserve the original diagnosis and write the new verdict separately.

**Replacement text:**

```markdown
- `reports/plant_fidelity_audit_v2_1.md`: final strict verdict; retain
  `reports/plant_fidelity_audit.md` unchanged as baseline input evidence.
```

### M2. Human report statuses are not mapped to machine gate states

**Location:** `IMPLEMENTATION_PLAN.md:449-450`

`지지 가능 / 조건부 / 불가 / 미평가` is not mapped to
`PASS/FAIL/NOT_EVALUATED/BLOCKED`, so prose and strict exit behavior can disagree.

**Replacement text:**

```markdown
Machine state is authoritative: `PASS`, `FAIL`, `NOT_EVALUATED`, or `BLOCKED`.
Human labels map exactly as `PASS=지지 가능`, `FAIL=불가`,
`NOT_EVALUATED=미평가`, and `BLOCKED=조건부/승격 불가`; reports must include
both fields and the strict runner exits nonzero for every required non-PASS state.
```

## Positive controls retained

The next revision should preserve these correct parts:

- MPC/controller ownership and rollout-plant purpose at 9-28.
- One-stock physical ontology and objective-view separation at 32-41 and 184-213.
- Time-indexed active-program intent and raw-ms semantics at 138-148.
- Existing speed availability and remaining delay-model work at 215-226.
- Finite boundary/backpressure and objective dual view at 228-246.
- Native-cycle/normalized-150 s separation at 462-469.
- t=0 replay and prefix parity at 385-398.
- Current runtime evidence explicitly remains NO-GO at 369-381.

## Final decision

**SPEC COMPLIANCE: FAIL** - binding SC12, split, dynamics, SPSA, runtime, offset,
and promotion requirements remain unsatisfied.

**DOCUMENT QUALITY: FAIL** - commands, schemas, dependencies, traceability, and
task-local execution contracts are not yet reliable enough to execute without policy
decisions during implementation.

**CHANGES_REQUIRED**
