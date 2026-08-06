# V2.1 Amendment Proposal: Dynamic Validation, SPSA, and Runtime

Review basis: branch `codex/plant-fidelity-v2-1`, commit/baseline
`cb3c44d170b7f818baae7af399fb65c93b6fb1e3`. This review is read-only with
respect to `IMPLEMENTATION_PLAN.md` and source code.

## Executive verdict

The current plan is not executable as a production promotion gate in three
areas.

1. The paired-future section names dimensions and headline ranking thresholds,
   but does not define an independent run identity, replay-from-zero contract,
   prefix parity, an unambiguous action clock, channel-level action levels,
   metric formulas, or fail-closed aggregation.
2. The SPSA section states useful target statistics, but the implementation does
   not currently evaluate exactly the same objective in FD and SPSA, does not
   support an N-phase tangent basis, has no noise-floor or sample-size protocol,
   and has no full production-decision parity gate.
3. The runtime section has one production sample at 154.746472 s. Production
   leaves both SPSA and price parallelism disabled, the only parallel helper
   covers green rollouts, parallel failure silently retries serially, the VBS
   adapter wait has no decision deadline, and the audit measures Python time
   rather than observation-to-readback latency.

The 45 s hard target is **not feasible on the current production path from the
available evidence**. It is arithmetically plausible after a redesign: the
measured target needs a 3.44x speedup to reach 45 s and 5.16x to reach the 30 s
p95 target, while the plan reports 131 independent rollouts, 0.44 s per rollout,
and 20 logical cores. The ideal parallel lower bound is encouraging, but it is
not evidence because only green FD is parallelized and no production benchmark
with workers enabled exists. SPSA is also not an available escape hatch: the
reported `k=16/32` magnitude ratios 2.53/3.29 fail the proposed 0.90--1.10 slope
gate.

## Required disposition

Keep all of the following production defaults unchanged until their gates pass:

- `price_spsa_enabled = False`;
- `price_parallel_workers = 0`;
- native fixed timing as fallback;
- no claim that the dynamic plant is valid for P-Stack/G6 promotion.

The amendment below is deliberately fail-closed. `NOT_EVALUATED` never counts
as `PASS`, an aggregate never rescues a failing demand/horizon/channel stratum,
and stale or mixed-run artifacts are rejected rather than inferred.

---

## Finding DYN-1 (P0): J-1 does not define paired replay from t=0

### Evidence

- `IMPLEMENTATION_PLAN.md:435-438` says to branch from an anchor with the same
  seed/demand, but it does not say how VISSIM state is restored or replayed.
- `scripts/run_plant_fidelity_matrix.ps1:41-69` runs only one no-control baseline
  case per demand/seed and never runs action arms.
- `scripts/run_g6_branch_grid.ps1:3-21` acknowledges that VISSIM state restore is
  unavailable and uses common-prefix seed replay, but this is only a comment in
  a separate G6 runner.
- `scripts/run_g6_branch_grid.ps1:91-92` creates one horizon from one warmup,
  while `scripts/run_g6_branch_grid.ps1:150-185` restarts each candidate; it does
  not create independent anchor experiments for 900/1500/2100/2700.
- `scripts/run_g6_branch_grid.ps1:155-160` skips a case solely because a terminal
  state file exists, without checking manifest/hash completeness.

### Exact replacement text for plan J-1/J-2

Replace `IMPLEMENTATION_PLAN.md:435-443` with the following text:

```markdown
### J-1. Paired-future replay contract (new, blocking)

VISSIM state restore is not assumed. Every `(demand, seed, anchor, arm, repeat)`
is a fresh process that loads the same immutable INPX and replays from `t=0`.
The interval `[0, anchor]` uses the exact active fixed programs, no-control VSL,
unrestricted ramp release, the same demand schedule, and the same random seed.
The branch action is installed only after an exact anchor snapshot is recorded.
It is held open-loop through `anchor + 15 * 60 s`; no controller re-decision is
allowed inside the future.

Required matrix:

- demand scale `{0.75, 1.00, 1.25}`;
- seed `{13, 29, 47}`;
- anchor `{900, 1500, 2100, 2700}` s;
- horizon `{1, 3, 5, 10, 15}` at `T_c=60 s`;
- eleven physical runs per demand/seed/anchor: three identical base repeats plus
  eight isolated perturbation arms defined in J-3.

This is `3 * 3 * 4 * 11 = 396` sequential VISSIM runs. Only one VISSIM process
may exist at a time. A run is complete only when its manifest, prefix trace,
anchor snapshot, all five horizon snapshots, action/readback trace, VISSIM
`.err`, and terminal marker exist and their hashes validate. File existence
alone is not a resume criterion.

Each case has a 1,800 s wall-clock hard limit, a 300 s no-progress limit, and at
most two attempts. A killed/failed attempt receives a new `run_id` and is
preserved under `attempts/`; it is never merged with its replacement. The batch
hard limit is 96 h. Exceeding either limit is `FAIL`, not a partial pass.
```

### Implementation, dependencies, commands, and artifacts

Add a dedicated runner rather than extending the baseline-only loop in place:

- `scripts/run_plant_paired_future_matrix.ps1`;
- `scripts/run_real_world_paired_future.vbs`;
- `scripts/analyze_plant_paired_futures.py`;
- `scripts/tests/test_paired_future_contract.py`.

Dependency order: S1, A, C, D, E, F, G, and H must pass before collecting this
matrix. J-1 also depends on DYN-2 run identity and DYN-3 action-clock semantics.

Executable command:

```powershell
powershell -NoProfile -File scripts/run_plant_paired_future_matrix.ps1 `
  -OutDir evaluation/runs/plant_fidelity_v2_1 `
  -DemandScales 0.75,1.00,1.25 -Seeds 13,29,47 `
  -AnchorsSec 900,1500,2100,2700 -Horizons 1,3,5,10,15 `
  -ControlIntervalSec 60 -MaxAttempts 2 -CaseTimeoutSec 1800 `
  -StallSec 300 -BatchTimeoutSec 345600
```

Required artifacts under
`evaluation/runs/plant_fidelity_v2_1/<experiment_id>/`:

- `experiment_manifest.json`;
- `runs/<run_id>/run_manifest.json` and `vissim_network.err`;
- `runs/<run_id>/prefix_trace.jsonl`;
- `runs/<run_id>/anchor_state.json`;
- `runs/<run_id>/future_H{1,3,5,10,15}.json`;
- `runs/<run_id>/action_trace.csv` and `signal_readback.csv`;
- `paired_future_rows.jsonl`;
- `dynamic_gate_report.json` and `dynamic_gate_report.md`.

---

## Finding DYN-2 (P0): run identity and anchor-prefix parity are incompatible with current artifacts

### Evidence

- `scripts/run_real_world_single_watchdog_distributed_core15n41.ps1:176-177`
  creates a random `run_id` once per wrapper invocation.
- `scripts/run_real_world_stackelberg_controller.vbs:1466-1470` embeds that
  `run_id` in every state JSON.
- `harness/g6/run_g6_shadow.py:110-117` hashes the entire anchor state file and
  requires byte equality across arms. Distinct valid run IDs therefore make the
  current whole-file equality check fail even when physical states match.
- `harness/g6/run_g6_shadow.py:100-101` silently chooses the alphabetically
  first arm as the anchor source after the hash check; there is no explicit base
  identity.
- `scripts/audit_plant_fidelity.py:1106-1117` infers a run ID from a directory
  when no explicit ID is present. That is acceptable for old inventory but is
  unsafe for paired evidence.
- `scripts/audit_plant_fidelity.py:1292-1315` checks mixed provenance within a
  run, but does not validate pair/arm/attempt identity or prefix equality.

### Exact addition text for plan J-1

Add the following immediately after the new J-1 matrix text:

```markdown
#### J-1a. Identity and prefix parity (blocking)

All identities use canonical JSON plus SHA-256. `run_id` is unique per physical
process attempt and is never used as the paired-state hash. Every artifact must
carry:

- `experiment_id = sha256(contract version, repo commit, NumSim tree, INPX,
  SIG set, mapping, detector mapping, calibration, tuning, demand matrix)`;
- `pair_id = sha256(experiment_id, demand_schedule_hash, demand_scale, seed,
  anchor_sec, control_interval_sec)`;
- `run_id = UUIDv4` for one process attempt;
- `attempt_no`, `arm_id`, and `repeat_no`;
- `prefix_contract_hash = sha256(network_hash, SIG set, demand schedule, seed,
  warmup action, incident schedule, sampling clock)`;
- `physical_state_hash` over the canonical dynamic state only; provenance,
  paths, timestamps, run IDs, and arm labels are excluded.

Missing identity is `FAIL`; directory-name inference is forbidden for v2.1
artifacts. For every `pair_id`, all arms and repeats must have distinct run IDs,
the same prefix contract hash, and exactly equal canonical prefix samples at
`t=0,5,...,anchor` s. Each sample hashes ordered vehicle
`(VehNo,VehType,Lane,Pos,Speed)`, active SG states, demand/input state, incident
state, and `SimSec`. The projected anchor state hash must also be identical.
Any mismatch quarantines the entire pair and it contributes to no metric.

The base and perturbation traces must first diverge after actuation: anchor
snapshots are equal and the first permitted physical-state divergence is the
state at `anchor+1 s`. Earlier divergence is `FAIL`; no divergence by
`anchor+60 s` is an action-authority `FAIL` for a non-base arm.
```

### Implementation, commands, and thresholds

The prefix comparator must compare the canonical payload rather than file bytes.
Add `evaluation/controllers/run_identity.py` (or the established shared hash
module if one exists) and golden vectors for Python, PowerShell/.NET, and VBS.
Do not reuse the path fallback in `_payload_run_id` for schema v2.1.

Unit command:

```powershell
python -B -m unittest scripts.tests.test_paired_future_contract `
  scripts.tests.test_audit_plant_fidelity tests.test_vissim_stackelberg_adapter_fidelity
```

Artifact and gate: `prefix_parity.json` must report `396/396` complete runs,
`36/36` complete pair IDs, zero duplicate run IDs, zero inferred IDs, zero
prefix mismatches, zero early divergences, and zero non-live perturbation arms.

---

## Finding DYN-3 (P0): action timing and action levels are ambiguous

### Evidence

- In stepwise mode, `scripts/run_real_world_stackelberg_controller.vbs:416-425`
  calls `RunControllerDecision(stepNo)` before `RunSingleStep`; the JSON is
  labelled `stepNo` although the COM simulation has not executed that step.
- In event-continuous mode, `scripts/run_real_world_stackelberg_controller.vbs:520-541`
  runs to the target first and then decides/applies. The two modes therefore do
  not have the same labelled action epoch.
- `scripts/run_real_world_stackelberg_controller.vbs:707-732` records and times
  the state/decision, while `:751-882` applies the CSV afterward; no validity
  interval or based-on state hash is checked before COM writes.
- `harness/g6/run_g6_shadow.py:142-150` assumes observations are exactly
  `t0 + h*T_c`, but it does not verify the VISSIM `SimSec` represented by the
  state JSON.
- Existing action levels are ad hoc: `harness/g6/g6_core.py:105-128` mixes VSL
  50--100, ramp 600--1364, two-phase green 25/75, and offset +30, without a
  low/base/high contract or symmetric offset arm.
- `harness/g6/g6_core.py:93-103` documents duplicate/non-live VSL and green
  candidates in the prior set.

### Exact addition text for plan J

Add this as new J-3 and renumber the existing metric/gate subsections:

```markdown
### J-3. Canonical action epoch and perturbation levels

The canonical anchor is the VISSIM COM state with `SimSec == anchor_sec` after
that second has completed. The harness must: (1) run to the anchor, (2) capture
and hash the pre-action state, (3) issue and read back one complete action, and
(4) resume simulation. The action has `decision_time_sec=anchor_sec`,
`valid_from_sec=anchor_sec`, `valid_until_sec=anchor_sec+900`, and
`based_on_state_hash=anchor physical_state_hash`. It affects `(anchor,
anchor+1]` first. Future H is sampled only where COM `SimSec == anchor+60*H`.
Stepwise/event mode is an implementation choice but must satisfy this clock
fixture byte-for-byte.

All arms hold one action through H=15. Non-focal channels remain exactly at the
base action. Low/base/high values are:

| channel | low | middle | high | base index |
|---|---:|---:|---:|---:|
| VSL command | 60 km/h | 90 km/h | 120 km/h | high |
| each ramp release | 0.35 capacity | 0.65 capacity | 1.00 capacity | high |
| selected stage green | `g0-0.25*G` | `g0` | `g0+0.25*G` | middle |
| runtime offset lag | `-C/8` | `0` | `+C/8` | middle |

`G` is the active program's effective green and `C` its native cycle. Green is
projected onto the N-stage bounded simplex: preserve total effective green,
respect every stage minimum/maximum, and redistribute the opposite change over
the other stages in proportion to their base green. If either realized green
step is less than `0.15*G`, that actuator is ineligible and must be replaced by
the next predeclared signal in the same topology stratum; clipping an arm and
keeping its label is forbidden. Offset is enabled only after S1/F proves sign,
activation boundary, and readback. Every requested row must read back exactly;
one missing/partial row fails the run.

The eleven runs are `base_r1/base_r2/base_r3`, VSL 60/90, ramp 0.35/0.65,
green low/high, and offset -C/8/+C/8. The three base futures quantify replay
noise; they are not three independent ranking candidates.
```

### Required fixtures and artifact fields

Add unit/integration fixtures for `t0=900`, action at 900, first affected state
901, and endpoints 960/1080/1200/1500/1800. Repeat for anchor 2700, ending at
3600. Every action row records requested value, realized value after projection,
COM readback, valid interval, state hash, and activation boundary.

`action_contract.json` thresholds: zero stale hashes, zero actions before the
anchor, zero early state divergence, zero partial rows, 100% readback, and
realized/requested error `<=1e-9` in native units after declared projection.

---

## Finding DYN-4 (P0): horizon, channel, and sample aggregation are undefined

### Evidence

- `IMPLEMENTATION_PLAN.md:444-450` lists channels and three ranking thresholds,
  but gives no metric formula, missing-data policy, or per-horizon/stratum rule.
- `harness/g6/g6_core.py:265-310` replaces the production follower objective
  with state accumulation for scoring; that can be a ranking proxy but does not
  supply direct queue, speed, count, flux, or TTT accuracy gates.
- `harness/g6/run_g6_shadow.py:193-208` emits objective/TTT/spillback only.
- `plant/src/vissim_strict/shadow.py:499-501` takes the arithmetic mean of
  decision Spearman values and pools pairwise counts, allowing strong horizons
  or large cells to hide a weak H=1/demand/channel stratum.
- The existing strict contract already supplies initial calibration thresholds:
  `plant/docs/vissim_strict_plant_g0_contract.md:792-798`.

### Exact replacement text for plan J-3/J-4

Replace current `IMPLEMENTATION_PLAN.md:444-451` with:

```markdown
### J-4. Dynamic channels, estimands, and aggregation

The oracle and model must emit the same entity IDs and units for:

- urban movement queue and link storage occupancy (veh);
- freeway segment count (veh) and vehicle-weighted speed (km/h);
- boundary, ramp, urban, and freeway interval inflow/outflow (veh/60 s);
- total/freeway/urban interval and cumulative TTT (veh*h);
- spillback onset/release and active constraint IDs.

Vehicle IDs/crossings are used to derive flux and VISSIM TTT; aggregate state
accumulation is not accepted as the only TTT oracle. Missing entities, missing
horizon samples, non-finite values, unexplained clipping, and mass residual over
`max(5 veh, 3% of observed inventory)` fail their pair before aggregation.

The atomic independent unit is one complete `pair_id`, not an entity-time row.
For each pair and horizon, first aggregate entities within a channel, then form
the `(demand, horizon, channel)` stratum over three seeds and four anchors.
Report each seed separately and the macro mean over 12 pairs. A stratum passes
only when all 12 pairs are complete, its macro metric passes, and no seed metric
exceeds `1.25 *` the stated limit. Report a 10,000-resample seed-block bootstrap
95% interval (all four anchors stay together), but do not use another stratum to
rescue failure. Overall numbers are descriptive only.

### J-5. One-step and multi-step gates

H=1 is a separate hard gate. For every demand stratum:

- urban queue and storage NMAE <=25% (promotion <=15%);
- freeway vehicle-weighted speed MAPE <=10%;
- segment count MAE <= `max(5 veh, 10% of observed mean count)`;
- GEH <=5 for at least 85% of interval-flux entity samples and signed total-flow
  bias <=10%;
- total, freeway, and urban interval TTT absolute percentage error <=15%.

H=3 and H=5 are production hard gates. Over the complete trajectory to H:

- cumulative total/freeway/urban TTT error <=20%;
- terminal urban queue/storage NMAE <=30% (promotion <=20%);
- speed MAPE <=15%;
- count MAE <= `max(7.5 veh, 15%)`;
- flux GEH/bias retains the H=1 85%/10% limits.

H=10 and H=15 are long-horizon stability hard gates:

- cumulative TTT error <=25%;
- terminal urban queue/storage NMAE <=35%;
- speed MAPE <=20%;
- count MAE <= `max(10 veh, 20%)`;
- no non-finite state, negative stock, unexplained clipping, capacity violation,
  or mass-invariant failure.

NMAE is `sum(abs(pred-obs))/max(sum(obs),1 veh)` over the declared entities;
zero-observation strata also report MAE and may pass only when MAE <=1 veh.
Speed MAPE uses observed-vehicle weights and denominator
`max(observed_speed,5 km/h)`. TTT percentage error uses denominator
`max(observed_TTT,1 veh*h)`. The report must include signed bias next to every
absolute metric.
```

### Commands and artifacts

Analyzer command:

```powershell
python -B scripts/analyze_plant_paired_futures.py `
  --run-dir evaluation/runs/plant_fidelity_v2_1/<experiment_id> `
  --horizons 1,3,5,10,15 --control-interval-sec 60 `
  --bootstrap-seed 20260805 --bootstrap-reps 10000 `
  --out-json outputs/plant_fidelity_v2_1/<experiment_id>/dynamic_gate_report.json `
  --out-md outputs/plant_fidelity_v2_1/<experiment_id>/dynamic_gate_report.md
```

Add `dynamic_channel_rows.jsonl`, `dynamic_by_pair.json`,
`dynamic_by_stratum.json`, and `mass_invariant_failures.json`. All formulas,
denominators, exclusions, and sample counts must be present in the JSON.

---

## Finding DYN-5 (P0): ranking and spillback gates can pass on pooled or degenerate evidence

### Evidence

- `IMPLEMENTATION_PLAN.md:447-450` requires rho 0.70/pairwise 0.80/no repeated
  reversal but does not define material ties, sample size, or per-horizon gates.
- `plant/src/vissim_strict/shadow.py:391-403` compares the model-selected top arm
  with all other arms and pools those comparisons globally.
- `plant/src/vissim_strict/shadow.py:413-423` builds one confusion matrix without
  enforcing positive/negative support.
- `reports/plant_fidelity_audit.md:139-140` explicitly says the old F1=1.0 from a
  single label is invalid and requires at least 20 positive and 20 negative
  examples.
- `PLANT_FIDELITY_AUDIT_REQUEST.md:271-274` records the unresolved H=1 rho
  0.4378, H=1 pairwise 0.000, pooled pairwise 0.75, and degenerate spillback
  labels. H=1 therefore cannot be averaged with H=5/10/15.

### Exact addition text for plan J

Add:

```markdown
### J-6. Action-ranking and spillback gates

Ranking is evaluated separately for H=1,3,5,10,15 and separately for each
demand stratum; H=1 cannot be averaged with later horizons. The three identical
base repeats define replay objective noise
`eps_J=max(1e-6 veh*h, q95(|J_base_i-J_base_j|))`. A pairwise comparison is
material only when the VISSIM absolute objective difference exceeds both
`2*eps_J` and `0.5%*max(|J_base|,1 veh*h)`; smaller differences are ties and are
reported `INDETERMINATE`, not correct or incorrect.

For every horizon and demand stratum:

- macro mean cell-level Spearman rho over complete material rankings >=0.70;
- top-action material pairwise agreement >=0.80 and one-sided 95% Wilson lower
  bound >=0.75;
- each isolated channel has at least 24 material comparisons and agreement
  >=0.80;
- repeated sign reversals = 0, where repeated means the same channel/level
  direction is reversed in at least two of three seeds at an anchor/horizon;
- the H=1 gate passes independently.

Spillback is an event, not a constant horizon label. Record first onset and first
release per physical storage/queue ID. Initial promotion requires F1 >=0.80;
release requires F1 >=0.90. Both require at least 20 VISSIM-positive and 20
VISSIM-negative episodes, onset/release median absolute timing error <=60 s,
and p90 timing error <=120 s. Threshold is 0.90 physical occupancy for both
model and oracle; zero-capacity entities are excluded and listed.

If the fixed 3x3 matrix lacks class support, run only the predeclared spillback
augmentation: demand 1.25, seeds 59/71/89, restrictive ramp and green arms, up
to 120 additional episodes. Stop when both classes have 20 examples. If support
is still insufficient, the gate is `NOT_EVALUATED`; do not alter the occupancy
threshold, labels, or candidate set after seeing results.
```

Artifacts: `ranking_by_horizon_demand_channel.json`,
`ranking_indeterminate_pairs.jsonl`, `spillback_events.jsonl`, and
`spillback_confusion.json`. The audit must display raw TP/FP/FN/TN and support
counts next to F1.

---

## Finding SPSA-1 (P0): FD and SPSA do not currently evaluate one identical function

### Evidence

- `vendor/NumSim-mine/src/controllers/stackelberg_wu_metered.py:692-718`
  defines a price objective whose hinge term depends on `forecast`.
- Metering passes `forecast` into `_price_ttt` at `:801-810`, while green, VSL,
  offset, and joint helpers omit it at `:627-646`, `:812-847`, and `:923-973`.
- SPSA also omits `forecast` at `:1027-1032`.
- FD computes barrier endpoints and adds their derivative at `:1411-1420` and
  `:1488-1521`; SPSA forces `bar_hi = bar_lo = 0` at `:1408-1410` and
  `:1483-1487`. Enabling barrier therefore changes the function.
- SPSA's joint ramp safety certificate uses one all-ramp-high rollout
  (`:1037-1047`) instead of the per-ramp high endpoint used by FD
  (`:1488-1495`), so production feasibility can differ even if the gradient is
  close.
- There are no SPSA or price-parallel tests in `vendor/NumSim-mine/src/tests`;
  the existing marginal-price tests exercise channel behavior, not estimator
  parity.

### Exact replacement text for plan I-1

Replace `IMPLEMENTATION_PLAN.md:372-402` with:

```markdown
### I-1. Exact FD/SPSA estimator qualification (blocking)

FD and SPSA must call one pure `evaluate_price_point(state, previous, forecast,
control, objective_spec)` function. It returns the final state hash and explicit
components: near TTT, far term, hinge, protected-queue term, barrier, total
objective, max density by ramp/link, feasibility, and clipping. No estimator or
channel may omit `forecast` or a component. FD and SPSA use identical horizon,
terminal state, previous action, local-cost subtraction, trust region, safety
certificate, and objective flags.

Before statistical comparison, run single-coordinate endpoint fixtures for
green, meter, VSL, offset, and every N-phase basis coordinate. FD and the SPSA
point builder must produce byte-identical control payloads, final state hashes,
objective components, and feasibility for the same physical endpoint. Required
count: at least 12 qualification states stratified over all three demands, all
three seeds, free/congested anchors, and active/inactive barrier/hinge/far flags.
Any endpoint mismatch is `FAIL` and stops the SPSA experiment.

Production perturbation sizes are green 6 s, meter
`max(300 veh/h,0.20*capacity)`, VSL 10 km/h, and offset C/8. Record the realized
bounded-simplex/circular displacement; divide by realized span, never the
requested unclipped span.

For each qualification state, estimate objective noise with 20 identical-control
rollouts under shuffled worker scheduling. Define
`eps_J=max(q99(|J_r-J_1|), 1e-9*max(|J_1|,1))` and coordinate noise
`eps_g=2*eps_J/realized_span`. A coordinate is material only when
`|g_FD|*realized_span >= max(5*eps_J,0.005*max(|J0|,1))`; smaller coordinates
are `INDETERMINATE` and are excluded from sign/magnitude pass counts while their
rate is reported.

Evaluate SPSA pair counts k in `{8,16,32,64}` with 30 independent deterministic
direction batches per qualification state. Select the smallest k satisfying all
gates; do not tune k on production-decision results. On material normalized
coordinates:

- sign reversals = 0;
- normalized RMSE `||g_SPSA-g_FD||2/||g_FD||2 <=0.20`;
- through-origin slope `dot(g_FD,g_SPSA)/dot(g_FD,g_FD)` in `[0.90,1.10]`;
- median absolute normalized error <=0.15 and p95 <=0.35;
- overall one-sided exact Clopper-Pearson 95% upper bound for sign error <=0.05
  with at least 59 material comparisons;
- each channel has at least 29 material comparisons, zero reversals, and a
  channel sign-error upper bound <=0.10.

All statistics are computed first per independent direction batch and then
clustered by qualification state. Report 10,000 state-block bootstrap 95%
intervals. Activation requires the upper confidence limit for NRMSE <=0.20 and
the complete slope interval inside `[0.90,1.10]`.
```

### Implementation and command

Refactor first; do not bolt comparison code around the current divergent helpers.
Add:

- `vendor/NumSim-mine/src/controllers/price_rollout.py`;
- `vendor/NumSim-mine/src/tests/test_price_rollout_endpoint_parity.py`;
- `vendor/NumSim-mine/src/tests/test_spsa_fd_parity.py`;
- `scripts/run_spsa_fd_parity.py`.

Command:

```powershell
python -B scripts/run_spsa_fd_parity.py `
  --states outputs/plant_fidelity_v2_1/<experiment_id>/qualification_states.json `
  --pairs 8,16,32,64 --batches 30 --null-repeats 20 `
  --bootstrap-reps 10000 --seed 20260805 `
  --out outputs/plant_fidelity_v2_1/<experiment_id>/spsa_fd_parity.json
```

The JSON must preserve every endpoint, component, direction seed, realized span,
FD estimate, SPSA estimate, material/indeterminate reason, and confidence
interval. A markdown summary alone is insufficient.

---

## Finding SPSA-2 (P0): N-phase tangent parity and production-decision parity are absent

### Evidence

- `vendor/NumSim-mine/src/controllers/stackelberg_wu_metered.py:1005-1007`
  hardcodes `p1` and `p2 = total_green - p1` inside SPSA.
- The FD green helper also hardcodes the same two-phase representation at
  `:640-643` and `:729-733`; matching two wrong endpoints does not establish
  N-phase correctness.
- `evaluation/controllers/vissim_stackelberg_adapter.py:1573-1588` enables four
  price channels for flagship but does not set `price_spsa_enabled`, pair count,
  or a tangent basis.
- `evaluation/controllers/vissim_stackelberg_adapter.py:1839-1847` calls the full
  production decision and exports only numeric metadata; there is no paired FD
  versus SPSA decision comparison.
- `IMPLEMENTATION_PLAN.md:388-389` asks for tangent-space and real N-phase tests,
  but does not define coordinates or a production decision acceptance rule.

### Exact addition text for plan I-1/I-2

Add:

```markdown
#### I-1a. N-phase coordinate contract

For a signal with N active stages, price coordinates live in an `(N-1)`
dimensional deterministic Helmert tangent basis `B_N` with `1^T B_N = 0`.
Physical green is `project_bounded_simplex(g0 + B_N q, total=G, min, max)`.
FD perturbs one q coordinate; SPSA perturbs all q coordinates with the same
projector. The realized secant in q-space is recorded. The reported physical
stage gradient is `B_N * gradient_q` with zero-sum check <=1e-12. Coordinates
that collapse under bounds are ineligible, not zero gradients. Tests must cover
N=2,3,4,5,6 and every active N in the generated signal manifest.

#### I-1b. Full production-decision parity

Estimator-level success is necessary but not sufficient. Run the unmodified
production `decide_with_info` path twice from the same serialized state,
previous action, forecast, sidecar state, and refresh counter: exact FD and the
candidate SPSA k. Use all 36 demand/seed/anchor states and three independent SPSA
direction seeds per state (`n=108`). Reset sidecars between twins.

Required parity:

- controller status, feasibility, safety certificates, fallback class, selected
  leader candidate, and spillback guard are exactly equal in 108/108 twins;
- command payload hash is exactly equal, or differs by at most one declared
  quantization level while the exact-FD rescored objective difference is below
  the material floor; equivalence must hold in 108/108 twins;
- every material selected-versus-runner-up ordering has the same sign;
- no SPSA decision has worse exact-FD rescored objective by more than
  `max(2*eps_J,0.5%*|J_FD|)`;
- the one-sided exact 95% lower bound on production-equivalence probability is
  >=0.95.

Any safety/status mismatch is an unconditional failure. SPSA remains OFF in
production until both estimator and full-decision parity pass on a new source
hash.
```

Add `production_decision_parity.jsonl` and
`production_decision_parity_summary.json`. The command must use the same
`pstack-flagship` adapter entry point as VISSIM, not a reduced controller probe.

---

## Finding RT-1 (P0): multiprocessing is partial, silent on failure, and not production-wired

### Evidence

- `vendor/NumSim-mine/src/controllers/stackelberg_wu_metered.py:752-770`
  parallelizes only green endpoint tasks and constructs a fresh
  `ProcessPoolExecutor` for that call.
- `:772-780` catches every exception and silently recomputes all work serially;
  no error, fallback, or elapsed-time telemetry is returned.
- `:781-783` manually increments only the parent's rollout counter after worker
  completion; there is no submitted/completed/failed/cancelled breakdown.
- Meter, VSL, offset, cross, and relinearization rollouts remain serial at
  `:785-973`, `:1477-1524`, `:1580-1619`, and `:1740-1768`.
- Defaults are `price_parallel_workers=0` and `price_spsa_enabled=False` at
  `:149-157`; `build_pstack_flagship_controller` does not override them at
  `evaluation/controllers/vissim_stackelberg_adapter.py:1562-1615`.
- The plan's workers=0/workers=5 bit-equality item at
  `IMPLEMENTATION_PLAN.md:411-416` does not cover all channels, failures, timeout,
  or full decision output.

### Exact replacement text for plan I-3

Replace `IMPLEMENTATION_PLAN.md:411-417` with:

```markdown
### I-3. Unified rollout scheduler and deterministic multiprocessing

All pure price-point evaluations (green, meter, VSL, offset, required cross
points, and certificates) are submitted to one scheduler per price refresh.
Task IDs and reduction order are deterministic. Windows uses `spawn`; the worker
initializer receives one immutable serialized context and workers return only
`PriceRolloutResult`. Parent reduction is sorted by task ID so workers=1 and
workers=N produce bit-identical objective components, gradients, certificates,
metadata excluding timing/PID, and final action payload.

Benchmark workers `{1,4,8,12,16,20}` on the target 20-logical-core host and
select the smallest count that passes runtime. Never exceed logical cores or the
number of tasks. A worker task has a 5 s hard limit, pool startup has a 3 s hard
limit, price refresh has a 20 s target and 25 s hard limit. One worker error,
timeout, broken pool, missing result, duplicate result, or non-finite component
is explicit `PRICE_SCHEDULER_FAIL`; production must not silently retry the whole
batch serially after 20 s.

Telemetry per refresh: backend/start method, worker count, context bytes,
startup time, task count by channel, submitted/completed/failed/cancelled,
per-task queue/run/return time, parent reduction time, rollout count, cache hits,
deadline remaining, exception type, and fallback reason. Parent rollout count
must equal completed physical evaluations and is checked against the task
manifest.

Promotion requires workers=1 versus selected-N bit parity on 36 states, 10
repeats each, zero scheduler failures, zero count mismatches, and identical
production action hashes. Keep `price_parallel_workers=0` until this passes.
```

### Tests, benchmark, and artifacts

Add `test_price_scheduler_serial_parallel.py`,
`test_price_scheduler_broken_worker.py`, and
`test_price_scheduler_deadline.py`. Fault injection must cover worker exception,
hang, process death, duplicate/missing task, non-finite result, and parent
cancellation.

```powershell
python -B scripts/benchmark_price_scheduler.py `
  --states outputs/plant_fidelity_v2_1/<experiment_id>/qualification_states.json `
  --workers 1,4,8,12,16,20 --repeats 10 `
  --task-timeout-sec 5 --startup-timeout-sec 3 --batch-timeout-sec 25 `
  --out outputs/plant_fidelity_v2_1/<experiment_id>/price_scheduler_benchmark.json
```

Artifacts include raw `price_scheduler_trace.jsonl`, parity hashes, CPU model,
logical/physical core count, RAM, Python version, process start method, and cold
versus warm labels.

---

## Finding RT-2 (P0): no decision timeout, wrong latency boundary, and incomplete fallback telemetry

### Evidence

- `scripts/run_real_world_stackelberg_controller.vbs:2485-2505` polls the Python
  process until it exits with no timeout.
- The outer watchdog only kills after no file progress for 300 s by default
  (`scripts/run_real_world_single_watchdog_distributed_core15n41.ps1:309-343`),
  much later than the 45 s decision limit, and kills VISSIM/cscript together.
- `evaluation/controllers/vissim_stackelberg_adapter.py:4387-4393` starts timing
  inside Python. `:4856-4866` stops before VBS parses/applies the CSV and COM
  readback, so `decision_wall_sec` is not end-to-end control latency.
- Adapter exceptions fall back to `ControlAction.fixed` at
  `evaluation/controllers/vissim_stackelberg_adapter.py:4804-4808` and still
  produce valid outputs. This is not the contract's last-feasible reissue, and
  the current audit does not count it as a fallback interval.
- VBS regards a complete fallback CSV as a successful decision at
  `scripts/run_real_world_stackelberg_controller.vbs:733-749`.
- `scripts/audit_plant_fidelity.py:1773-1779` gates any count of Python wall
  samples, even one, at p95 30/max 45; the evidence manifest has exactly one
  154.746472 s sample (`reports/plant_fidelity_evidence_manifest.json:1504-1510`).
- The strict runtime/fallback contract already specifies p50/p95/hard limits and
  fallback order at `plant/docs/vissim_strict_plant_g0_contract.md:727-746`.

### Exact replacement text for plan I-4 and K

Replace `IMPLEMENTATION_PLAN.md:418-422` and extend K with:

```markdown
### I-4. End-to-end runtime, deadline, and fallback contract

Runtime is measured from the start of the anchor observation scan to completion
of COM action readback, not only inside Python. Required stage budgets are:

| stage | p95 budget | hard budget |
|---|---:|---:|
| observation scan + state JSON | 2 s | 3 s |
| adapter startup/config/provenance | 2 s | 3 s |
| price scheduler | 15 s | 25 s |
| leader/follower solve | 8 s | 8 s |
| guards/prediction/serialization | 1 s | 2 s |
| CSV validation + COM apply/readback | 2 s | 4 s |
| end-to-end | 30 s | 45 s |

The adapter receives an absolute monotonic deadline. At 30 s it emits a target
overrun event; at 42 s the VBS wrapper terminates only the adapter/worker process
tree and reserves 3 s to reissue and validate fallback. VISSIM remains alive and
paused. The 300 s case watchdog is only a simulation-stall guard and is not a
decision timeout.

Fallback order is: (1) one timeout/invalid output: reissue the last feasible
command against the current state with new action ID/hash/validity and rerun all
safety/readback checks; (2) if unavailable or revalidation fails, use validated
native fixed plan; (3) two consecutive failures, hash mismatch, signal conflict,
mass violation, or stale state: latch fixed plan until an explicit healthy
decision clears it. Never reuse an old CSV/hash and never leave the interval
uncontrolled. Silent fallback is forbidden.

Each interval records observation/decision/action IDs and hashes, stage start/end
times, deadline, timeout stage, process/worker termination, fallback source,
reason code, consecutive failure count, revalidation result, COM readback, and
recovery event. Runtime reports include controller-success and fallback latency
separately; a fast fallback does not count as a successful controller decision.

Runtime promotion uses at least 100 production `pstack-flagship` H=3 end-to-end
decisions from all 3 demands and all 3 seeds, with at least 10 per demand/seed
stratum and both cold/warm samples. Gates: p50 <=15 s, p95 <=30 s, max <=45 s,
controller fallback rate <5%, timeout rate <1%, silent fallback 0, stale action
0, readback failure 0, and fault-injection recovery 100%. Every demand/seed
stratum must have p95 <=30 s and max <=45 s.

### K. Audit integration

The audit accepts explicit `--dynamic-report`, `--spsa-report`,
`--scheduler-report`, and `--runtime-report`. Missing or stale reports are
`NOT_EVALUATED`; any report hash that does not match the current experiment ID,
repo/NumSim/network/config hashes, or action schema is `FAIL`. The final release
requires all one-step, multi-step, ranking, spillback, SPSA (if enabled),
scheduler (if enabled), runtime, fallback, provenance, and signal gates to pass.
```

### Runtime command and artifacts

```powershell
powershell -NoProfile -File scripts/run_pstack_runtime_shadow.ps1 `
  -OutDir evaluation/runs/pstack_runtime_v2_1 `
  -DemandScales 0.75,1.00,1.25 -Seeds 13,29,47 `
  -MinDecisionSamples 100 -DecisionTargetSec 30 -DecisionTimeoutSec 45 `
  -AdapterKillSec 42 -FallbackReserveSec 3

python -B scripts/audit_plant_fidelity.py --repo . `
  --action-dir evaluation/runs/plant_fidelity_v2_1/<experiment_id> `
  --dynamic-report outputs/plant_fidelity_v2_1/<experiment_id>/dynamic_gate_report.json `
  --spsa-report outputs/plant_fidelity_v2_1/<experiment_id>/spsa_fd_parity.json `
  --scheduler-report outputs/plant_fidelity_v2_1/<experiment_id>/price_scheduler_benchmark.json `
  --runtime-report outputs/plant_fidelity_v2_1/<experiment_id>/runtime_report.json `
  --strict
```

Required artifacts:

- `decision_runtime_trace.jsonl` with all stage timestamps;
- `runtime_by_stratum.json` and `runtime_report.md`;
- `fallback_events.jsonl` and `fallback_fault_injection.json`;
- `stale_action_fault_injection.json`;
- `readback_fault_injection.json`;
- final audit manifest hashing every report.

---

## 45-second feasibility assessment

### What current evidence establishes

- The observed production H=3 adapter decision is 154.746472 s
  (`reports/plant_fidelity_evidence_manifest.json:1504-1510` and
  `reports/plant_fidelity_audit.md:56`). This fails both p95 30 s and hard 45 s.
- The sample size is one, so it says nothing defensible about p95; it is enough
  to prove the current configuration fails the hard limit.
- The same audit reports 131 price rollouts. The plan reports 0.44 s per rollout,
  98.4% of refresh time in rollouts, 20 logical cores, and a 610 KB controller
  pickle (`IMPLEMENTATION_PLAN.md:419-422`). Even the reported serial rollout
  subtotal is `131 * 0.44 = 57.64 s`, above the hard limit before the rest of the
  decision.
- Current production does not set `price_parallel_workers` or SPSA. The only
  multiprocessing helper covers green endpoints, so the ideal 20-way arithmetic
  cannot be attributed to the current call graph.
- The reported SPSA k=16 and k=32 times (14.9/28.7 s) look useful, but their
  magnitude ratios (2.53/3.29) fail parity and cannot justify production.

### Decision

**Current path: NO-GO.** The 45 s target is not feasible from current evidence
and must remain a failed gate.

**Amended path: plausible, unproven.** Full-channel deterministic batching could
in principle reduce the rollout component enough, and a future qualified SPSA
could reduce evaluations further. Feasibility is established only when the
unified scheduler or qualified SPSA produces at least 100 end-to-end production
samples meeting every per-stratum runtime and fallback threshold above. Do not
convert arithmetic idealization, worker microbenchmarks, or estimator-only time
into a release claim.

## Dependency and promotion order

1. Complete S1/A/C/D/E/F/G/H and freeze hashes.
2. Implement DYN-2 identity/canonical hashing and DYN-3 action clock.
3. Implement DYN-1 replay runner, then DYN-4/5 analysis and audit integration.
4. Refactor one price evaluator and N-phase basis; pass endpoint parity.
5. Collect FD reference/noise data; qualify or reject each SPSA k.
6. Pass full production-decision parity before enabling SPSA.
7. Implement unified scheduler; pass serial/parallel/fault/deadline tests.
8. Implement adapter-only timeout, last-feasible/fixed fallback, and telemetry.
9. Run the >=100-decision runtime shadow benchmark on target hardware.
10. Rerun the complete audit under a new experiment ID. Only an all-PASS manifest
    may change production defaults.

## Minimum test command set

```powershell
python -B -m unittest discover -s scripts/tests -p 'test_*fidelity*.py'
python -B -m unittest scripts.tests.test_paired_future_contract
python -B -m unittest discover -s vendor/NumSim-mine/src/tests -p 'test_*price*.py'
python -B -m unittest vendor.NumSim-mine.src.tests.test_price_rollout_endpoint_parity
python -B -m unittest vendor.NumSim-mine.src.tests.test_spsa_fd_parity
python -B -m unittest vendor.NumSim-mine.src.tests.test_price_scheduler_serial_parallel
python -B -m unittest vendor.NumSim-mine.src.tests.test_price_scheduler_broken_worker
python -B -m unittest vendor.NumSim-mine.src.tests.test_price_scheduler_deadline
python -B -m unittest plant.tests.test_vissim_strict_shadow
```

If the vendor package path cannot be imported with dotted unittest names because
of the `NumSim-mine` directory name, execute those files directly with the same
approved interpreter and `NUMSIM_REPO_ROOT` pinned to the vendored tree; record
the interpreter path and tree hash in the test manifest.
