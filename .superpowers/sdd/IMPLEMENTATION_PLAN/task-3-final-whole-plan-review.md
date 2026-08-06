# Final Whole-Plan Review

## Findings

### Critical C1. The production MPC rollout integration is an unowned prerequisite

**Plan references:** `IMPLEMENTATION_PLAN.md:395-398`, `:618-620`, `:650-663`, `:709-715`.

The plan repeatedly consumes a "production endpoint" but never defines a blocking task that implements it in the actual P-Stack decision path. This permits all topology, calibration, parity, and audit artifacts to pass while `StackelbergWuMeteredController.decide_with_info` still evaluates candidates through the legacy plant. That is the current code shape: `evaluation/controllers/vissim_stackelberg_adapter.py:4743-4748` invokes that controller, and `vendor/NumSim-mine/src/controllers/stackelberg_mpc.py:2398,2526` still calls legacy `run_coupled_interval`. The final deliverable can therefore collapse into an audit package rather than the production MPC rollout system required by the brief.

**Replacement text:** Insert this blocking section before Section I, add the matching execution-matrix row, and replace dependency-graph references to the bare "production endpoint" with task `H`.

```markdown
## H. Production MPC rollout integration - P0

Implement the pure `evaluate_price_point(state, previous, forecast, action_schedule, objective_spec)` endpoint in **NEW** `plant/src/vissim_strict/production.py`. Integrate it through `plant/src/vissim_strict/bridge.py`, `vendor/NumSim-mine/src/controllers/stackelberg_mpc.py`, `vendor/NumSim-mine/src/controllers/stackelberg_wu_metered.py`, and `evaluation/controllers/vissim_stackelberg_adapter.py`. MPC continues to generate feasible candidates, compare objectives, and select the action; the endpoint only projects state and evaluates controller-independent dynamics, constraints, lever response, and objective components. Stackelberg leader/follower candidate scoring, exact FD, SPSA, no-control replay, and audit replay must all call this same endpoint and frozen parameter set. No production candidate may call legacy `run_coupled_interval` or a separate audit-only kernel.

Command: `& $python -B scripts/verify_production_rollout_path_v2_1.py --config evaluation/configs/real_world_modi_pstack_v8_urban36_budget_20260805.json --out outputs/production_rollout_path_v2_1.json`.

Artifact schema `production-rollout-path-v2.1` records every `decide_with_info` candidate, endpoint code/hash, topology/calibration/objective/action-schedule hashes, objective components, and selected action. PASS: green/VSL/meter/eligible-offset/no-control paths covered; strict endpoint calls equal candidate evaluations; legacy/audit-only candidate calls 0; controller performs all action selection; one-step and H=3 production integration tests pass; any uninstrumented candidate or hash mismatch is FAIL.
```

Add this matrix row:

```markdown
| H | frozen topology/signal/calibration + production config | exact files named in H + **NEW** verifier | H command | `outputs/production_rollout_path_v2_1.json`, `production-rollout-path-v2.1` | all candidate channels use one strict endpoint; legacy/audit-only calls 0 | A/B/C/D-core/E-fit; any bypass or hash mismatch stop |
```

Replace `A-2 + B + C + D-core + E-fit -> production controller-independent rollout endpoint/objective` with `A-2 + B + C + D-core + E-fit -> H production integration`, and make `I-1`, `I-3`, `CERT-PREP`, and promotion depend on `H=PASS`.

### Critical C2. Paired VISSIM futures certify a different action schedule from production

**Plan references:** `IMPLEMENTATION_PLAN.md:479-496`, `:503-504`, `:513-515`.

The plan applies every immediate action for one 60-second interval and then restores base. The current production `_predict` holds a candidate across the prediction horizon and can walk later green/VSL/meter values (`vendor/NumSim-mine/src/controllers/stackelberg_mpc.py:2403-2526`). The strict contract also represents move blocking and multi-entry schedules. A one-interval VISSIM pulse cannot certify H=3/5/10/15 predictions, lever magnitudes, or rankings from a held/walked production schedule. The fixed `anchor+1` first-divergence rule is also wrong whenever a signal action has a later safe activation boundary.

**Replacement text:** Replace lines 479-496 and 503-504 with:

```markdown
Every paired arm replays from `t=0`. At the anchor, the harness captures the pre-action COM state and asks the hash-bound production endpoint to emit the exact `ActionSchedule` used for candidate scoring. Plant and VISSIM consume byte-identical schedule entries, including `activation_boundary_sec`, every entry's half-open `[start_time_sec,end_time_sec)`, move-blocking/walk behavior, and restoration command. An impulse-only schedule is a separate diagnostic experiment and cannot promote a held or multi-entry production schedule.

The prefix must be identical through the state immediately before the schedule's first effective transition. The first allowed divergence is the state after that transition. For the current `control_horizon_steps=1, move_blocking=true` policy, the candidate remains effective over `[anchor_sec, anchor_sec + 60*H)` and base is restored only after reading the `anchor_sec + 60*H` endpoint. If production emits another schedule, that exact schedule is authoritative for both branches.

The run key contains `action_schedule_hash` and `first_effective_transition`; H is an endpoint dimension when one physical branch supplies multiple horizons. Clock fixtures cover anchors 900/2700 and every H, proving prefix equality, first affected state, all entry boundaries, final affected state, restoration/readback, and endpoint state. Missing, early, late, partial, or stale actuation is FAIL and is never repaired by shifting a window.
```

### Important I1. Required development and certification workloads have no executable producers

**Plan references:** `IMPLEMENTATION_PLAN.md:332-339`, `:388-389`, `:411-416`, `:466-467`, `:612-625`.

Five commands consume manifests that no task creates: `state_manifest_v2_1.json`, `development_pairs_v2_1.json`, `calibration_development_manifest_v2_1.json`, `spsa_qualification_request_v2_1.json`, and `runtime_development_request_v2_1.json`. The stated total of 15 parents also omits the three demand-by-seed-31 qualification parents. On the sealed side, `CERT-WAVE` asserts only 9/9 parent linkage, while J has no command that executes its t=0 child branches and I-4 requires at least 100 attempts and 10 independent VISSIM runs in every demand-by-seed-by-cold/warm stratum. `build_paired_future_manifest.py` only builds/analyzes a manifest; it cannot create the evidence it consumes.

**Replacement text:** Replace lines 332-334 and 388-389 with:

```markdown
Calibration uses six development parents. SPSA qualification adds three qualification-only parents for demand 0.75/1.0/1.25 with seed 31; these may not enter calibration. Wave A has nine sealed certification parents. Thus the campaign has 18 physical parents in three disjoint roles: 6 calibration-development, 3 SPSA-qualification-only, and 9 certification. Every role and allowed downstream consumer is hash-bound; missing/duplicate/cross-role use is FAIL.
```

Add a producer row before B-1:

```markdown
| DEV-DATA | demands 0.75/1.0/1.25; seeds13/29 plus qualification-only31; anchors900/1500/2100/2700 | **NEW** `scripts/run_development_data_v2_1.ps1` and manifest builder | `powershell -NoProfile -File scripts/run_development_data_v2_1.ps1 -Strict -RequireComplete -Out outputs/development_campaign_v2_1` | the five required manifests plus `development-campaign-v2.1` | calibration parents 6/6; qualification-only parents 3/3; anchors complete; role overlap 0 | H prerequisites; any missing role/hash/anchor stops |
```

Replace CERT-PREP/CERT-WAVE/J semantics with:

```markdown
CERT-PREP freezes exact sets and counts for 9 parent requests, every t=0 paired child request derived from the frozen lever inventory and production `ActionSchedule`, all 108 decision twins, and a live runtime/restart schedule sufficient for each preregistered 100-attempt/10-independent-run cold/warm stratum. CERT-WAVE executes those registered sets sequentially under the embargo and records expected-to-actual linkage N/N separately for parents, paired children, decision twins, and runtime attempts/runs. Zero evidence may be inferred from a parent manifest alone.

J execution command: `& $python -B scripts/run_paired_future_campaign_v2_1.py --request $campaignStage\requests\paired_future_requests_v2_1.json --out $campaignStage\results\paired_future_manifest_v2_1.json`. It launches every branch from `t=0`, proves prefix identity before applying the frozen schedule, runs the production plant endpoint from the same anchor state, and exits nonzero on any missing/duplicate child or incomplete cell.
```

### Important I2. Lever-effect magnitude has no quantitative gate, and ranking/noise inference is under-specified

**Plan references:** `IMPLEMENTATION_PLAN.md:23-28`, `:522-533`, `:557-560`, `:683-685`.

The top-level contract requires lever-effect sign, magnitude, and ranking. J-4 gates trajectory errors and ranking only; no threshold compares plant `Delta J` magnitude with paired VISSIM `Delta J`. Also, a q95 estimated from only three base repeats is not a defensible noise quantile, and point-estimate Spearman/pairwise gates can treat correlated rows from the same parent/anchor as independent support.

**Replacement text:** Replace lines 522-524 and 557-560 with:

```markdown
Before opening certification, run at least 20 independent `t=0` base replays per development parent/anchor. Define the conservative noise floor as `eps_J=max(1e-6 veh*h,max_{i,j}|J_base_i-J_base_j|)`; repeats estimate noise only and never increase action-effect or ranking support. Freeze `eps_J` by stratum before the sealed wave.

For every `demand x H x channel x seed` stratum, material actions satisfy `|Delta J_VISSIM| > max(2*eps_J,0.005*max(|J_base|,1 veh*h))`. Require `effect_NMAE=sum|Delta J_plant-Delta J_VISSIM|/max(sum|Delta J_VISSIM|,n*eps_J) <=0.25`, absolute signed-effect bias `<=0.15`, and material sign agreement 100%. Require at least 24 independent material comparisons in that same stratum; otherwise BLOCKED. Spearman `>=0.70` and top-pairwise `>=0.80` must hold both as point estimates and as 95% lower confidence bounds from a parent-then-anchor cluster bootstrap. No H, demand, channel, lever, or seed failure may be rescued by pooling.
```

Add `effect_NMAE`, signed-effect bias, and material-sign agreement to the J/K gate table and machine-readable schema.

### Important I3. Offset enablement has policy prose but no blocking command or artifact

**Plan references:** `IMPLEMENTATION_PLAN.md:321-326`, `:625-628`, `:665-666`, `:699`.

The dependency graph names `D-offset-enable`, but the execution matrix has no such task. Nothing issues the profile-scoped enable record or proves that startup rejects absent, stale, normalized-150s, or cross-profile evidence. This leaves a safety-critical promotion step manual and unauditable.

**Replacement text:** Add this matrix row before CERT-RELEASE and make K/CERT-RELEASE consume it when offset is requested:

```markdown
| D-offset-enable | exact native profile/hash + D-core PASS + complete offset-specific J effect/magnitude/ranking PASS + I-4 PASS | **NEW** `scripts/issue_offset_enable_record_v2_1.py`; adapter/VBS startup guard | `& $python -B scripts/issue_offset_enable_record_v2_1.py --profile-hash <native-profile-hash> --d-core $campaignStage\results\signal_action_contract_v2_1.json --paired $campaignStage\results\paired_future_manifest_v2_1.json --runtime $campaignStage\results\runtime_v2_1.json --out $campaignStage\results\offset_enable_v2_1.json` | `offset-enable-v2.1`, exact evidence/code hashes and `enabled` | all same-profile native gates PASS; normalized/cross-profile/stale/missing evidence or any NOT_EVALUATED keeps `intent_only` and exits nonzero |
```

### Important I4. The first fallback action is not required to be safe for the current state

**Plan references:** `IMPLEMENTATION_PLAN.md:461-473`.

Giving a last feasible payload a new ID/hash/validity does not make it feasible for the current queues, signal phase, authority, or safety constraints. The plan can therefore meet the 45-second clock by applying a stale-state command under a fresh identity.

**Replacement text:** Replace lines 464-465 with:

```markdown
Fallback order: copy only the payload of the last feasible command, then reissue it against the current observation with a new `based_on_state_hash`, action ID/hash, validity interval, and activation boundary. Before COM application, rerun topology/profile hash, authority, current signal phase/min-green/conflict, actuator bounds, mass-state, spillback guard, and safety-certificate validation. Any failure immediately selects the validated native fixed plan. Two consecutive controller failures latch the fixed plan. Old CSVs/hashes are never reused, and fallback generation, validation, application, and readback remain inside the 45-second hard deadline.
```

## Verdict

**CHANGES_REQUIRED**

**Spec compliance: FAIL.** SC12 shared-lane semantics, one-stock physics, native-cycle separation, whole-run calibration/certification roles, SPSA gradient/decision parity intent, and the 45-second target are substantially correct. Approval is blocked because the actual MPC path is not a defined deliverable task, paired futures use the wrong production action clock, lever-effect magnitude is ungated, and offset/fallback promotion is not fully fail-closed.

**Document quality: FAIL.** Multiple blocking commands consume artifacts with no producer, certification child/runtime workloads are not enumerated or linked, and the dependency graph treats an unimplemented production endpoint as if it already existed.
