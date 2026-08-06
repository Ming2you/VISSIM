# Task 3a Scoped Re-review - Round 1

Reviewed against the corrected
`.superpowers/sdd/IMPLEMENTATION_PLAN/task-3-review-brief.md`, the current
`IMPLEMENTATION_PLAN.md` (673 lines), and
`.superpowers/sdd/IMPLEMENTATION_PLAN/task-3a-spec-review.md`.

## Verdict

**CHANGES_REQUIRED**

**SPEC COMPLIANCE: FAIL**

**DOCUMENT QUALITY: FAIL**

The corrected SC12 authority is accepted. The current plan now gets the shared
through+left lane, lane-head authority, and profile-scoped SG-pair policy right. Most
prior findings are addressed. Approval remains blocked by four incomplete prior
findings and one new load-bearing certification break introduced by the fixes.

## Prior-finding disposition

| Prior finding | Verdict | Current evidence |
|---|---|---|
| C1 SC12 exact-lane topology | **ADDRESSED** | The prior finding is superseded by the corrected authority. Lines 164-182 correctly retain lane-2 through connectors 10241/10238, left connectors 10242/10240, SG5/SG1 authority, one stock with movement composition, and profile-policy equality. |
| C2 S0 closure | **ADDRESSED** | Lines 80-83 make S0R a compound closure over source/tests/strict runner plus S1 signal/program/SC12 evidence; lines 596-600 agree. |
| C3 calibration/certification overlap | **ADDRESSED** | Lines 335-345 separate development seeds 13/29 from certification seeds 47/59/71 and define retirement/fresh-wave semantics. A new execution-level break is reported as N1 below. |
| C4 dynamic gates/pooling | **NOT_ADDRESSED** | Lines 512-532 add most missing thresholds, but signed-bias gates remain valueless at 514 and spillback support dimensions contradict the no-seed-pooling rule at 529-532. |
| C5 SPSA qualification/decision parity | **NOT_ADDRESSED** | Lines 370-412 add common endpoints, repeats, k, independence, tangent coordinates, and 108-twin parity. FD/SPSA perturbation sizes and numeric per-stratum support remain undefined; per-channel exact sign-error bounds are also absent. |
| C6 runtime/deadline/fallback | **ADDRESSED** | Lines 425-441 define both clocks, the 42+3 second deadline behavior, explicit fallback order, all demand/seed/cold-warm strata, no silent fallback, fault recovery, and the 45-second hard maximum. |
| C7 offset cycle | **ADDRESSED** | Lines 316-324, 481-483, and 617-618 split D-core, test-only offset certification, and profile-specific D-offset-enable without a circular production-writer dependency. |
| C8 dependency graph | **ADDRESSED** | Lines 593-619 correctly order compound S0, A/B/C/D/E, the production rollout endpoint, J, I, K, and offset enablement. |
| I1 calibration thresholds | **ADDRESSED** | Lines 357-364 add holdout capacity, queue split, storage fraction, ramp/boundary CI, discharge WAPE, bias, and per-stock blocking rules. |
| I2 command/path executability | **NOT_ADDRESSED** | NEW paths/flags and `RW_PYTHON_EXE` are now declared, but blocking matrix commands still contain literal `<inpx>` placeholders at 574 and 576; these are not executable PowerShell commands. |
| I3 seven-field task contracts | **NOT_ADDRESSED** | Lines 564-591 add a useful matrix, but it has no explicit quantitative-verdict or schema column; several rows provide only artifact labels and qualitative failure names. K also omits explicit versioned output paths. |
| I4 run identity/replay noise | **ADDRESSED** | Lines 445-464 and 490-501 add source/action hashes, validity, state identity, three base repeats, a numeric noise floor, material ties, and retry identity. |
| I5 initial/promotion semantics | **ADDRESSED** | Lines 285-286 and 503-510 define diagnostic initial acceptance, conjunctive promotion, exact mapping, and the blocking 0.5-second signal gate. |
| I6 production deliverables | **ADDRESSED** | Lines 659-671 explicitly require the production rollout implementation, unchanged MPC entry point, fail-closed writers/guards, tests, and separate v2.1 evidence. |
| I7 binding traceability | **ADDRESSED** | Lines 640-657 map all 14 task-2 binding requirements to normative sections and artifacts. |
| I8 106 baseline plus NEW tests | **ADDRESSED** | Lines 75-76, 97-109, 551, 571, and 629 preserve the immutable 106-test denominator and separately require every NEW test with zero failures/discovery loss. |
| M1 audit output overwrite | **ADDRESSED** | Lines 668-670 retain the baseline audit and use v2.1 output names. |
| M2 machine/human status mapping | **ADDRESSED** | Lines 539-542 define the authoritative machine states, human mappings, and strict nonzero behavior. |

## Critical findings

### N1. The one-shot certification execution path exposes sealed data before freeze

**Location:** `IMPLEMENTATION_PLAN.md:125-131`, `IMPLEMENTATION_PLAN.md:329-345`,
`IMPLEMENTATION_PLAN.md:573`, `IMPLEMENTATION_PLAN.md:583`

The repaired split is correct in principle but not executable as one-shot certification:

- Line 331 says there are nine total 3,600-second runs, while the table defines 4
  training + 2 selection + 9 certification parents, or **15**.
- The S0R-3 body specifies only nominal seed 13, but the command at 573 omits
  `-BaselineOnly`. The current runner defaults to seeds 13/29/47 across all three
  demands (`scripts/run_plant_fidelity_matrix.ps1:13-14,28-36`), exposing seed 47
  telemetry before calibration freeze.
- The E matrix row at 583 says "nine development parents" although there are six,
  and passes a manifest containing sealed certification data to the fitting command.
  The same row has no separate post-freeze one-shot validation command.

This defeats the access boundary at 339-345 even though the prose split itself is sound.

**Replacement text:**

Replace line 331 with:

```markdown
3,600초 parent run은 calibration/selection 6개와 sealed certification 9개,
총 15개다. 두 집합은 seed, run ID, telemetry, anchor와 future가 겹치지 않는다.
```

Replace matrix rows 573 and 583 with:

```markdown
| S0R-3 | fixed nominal seed-13 snapshot only | `powershell -NoProfile -File scripts/run_plant_fidelity_matrix.ps1 -Strict -RequireComplete -BaselineOnly` | `baseline-snapshot-v2.1` | S0R-2; seed/demand set이 `{13,1.0}`이 아니거나 incomplete 3600초 run이면 stop |
| E-fit | six development parents only (training 4 + selection 2); certification telemetry path is absent from the process ACL; **NEW** fitter | `& $python -B scripts/fit_physical_stock_calibration.py --development-manifest outputs/calibration_development_manifest_v2_1.json --train-seeds 13,29 --out evaluation/calibration/physical_stock_calibration_v2_1.json` | frozen `physical-calibration-v2.1`, calibration hash, sealed-wave request hash | A/B and development gates; any certification file access, split/CI/support failure, or unfrozen threshold code stops |
| E-cert | frozen source/topology/calibration/candidate/auditor hashes plus pre-registered wave-A seeds 47/59/71; **NEW** one-shot validator | `& $python -B scripts/validate_physical_stock_calibration.py --calibration evaluation/calibration/physical_stock_calibration_v2_1.json --certification-manifest outputs/certification_wave_A_manifest_v2_1.json --out reports/physical_stock_calibration_certification_v2_1.json` | immutable `physical-calibration-certification-v2.1`, open/access log, PASS/FAIL/BLOCKED verdict | E-fit freeze; any pre-freeze access, second scientific opening, missing parent, or per-stock failure retires wave A |
```

## Important findings

### R1. Dynamic signed-bias and spillback support gates remain ambiguous

**Prior finding:** C4

**Location:** `IMPLEMENTATION_PLAN.md:274-276`, `IMPLEMENTATION_PLAN.md:512-532`

Line 514 says every absolute metric also "gates" signed bias but supplies no signed-bias
threshold except flow. Lines 529-530 define mandatory support by
`demand x H x channel x asset-class`, omitting seed, while line 531 says seed pooling is
forbidden. B-4 also promises an interface-p95 gate at 276 without a threshold. An auditor
cannot implement one deterministic verdict from this text.

**Replacement text:**

```markdown
For queue/storage, speed, count and TTT, signed bias uses the same denominator as
the corresponding absolute metric and `abs(signed_bias)` must not exceed that
metric's H-specific numeric limit. Flow signed bias remains `<=10%`.

Spillback support and verdict are keyed by
`demand x H x channel x certification_seed x asset_class`; every mandatory key
requires at least 20 independent positive and 20 independent negative episodes.
Low-demand `NOT_EVALUATED` is decided on that same key when positives are below 5.

Delete the undefined "interface p95" phrase at line 276; per-interface promotion
uses the explicit urban/ramp WAPE `<=10%` and off-ramp WAPE `<=15%` gates at J-4.
```

### R2. SPSA still lacks exact perturbations and complete support thresholds

**Prior finding:** C5

**Location:** `IMPLEMENTATION_PLAN.md:375-394`

The convergence test refers to `h` and `h/2` without defining h for any channel.
Line 389 blocks a required stratum on "support 미달" but never gives its numeric
minimum. The exact sign-error bound is only overall, despite per-channel qualification
being binding.

**Replacement text after line 377:**

```markdown
Pre-register FD full-step `h` as green `6 s`, VSL `10 km/h`, offset `C/8`, and
ramp meter `max(300 veh/h,0.20*capacity)`; the convergence replicate uses `h/2`.
Both estimators divide by the realized bounded displacement, never the requested
unclipped span.

Every `channel x demand x H` stratum requires at least 12 independent state
clusters and a nonempty material set. Overall exact sign-error UCB requires at
least 59 independent material comparisons and is `<=0.05`; each channel requires
at least 29 and its one-sided exact 95% UCB is `<=0.10`. Any lower support is
`BLOCKED`, not PASS.
```

### R3. Blocking commands still contain non-executable placeholders

**Prior finding:** I2

**Location:** `IMPLEMENTATION_PLAN.md:574`, `IMPLEMENTATION_PLAN.md:576`

Literal `<inpx>` is not a resolved argument and is parsed specially by PowerShell.
The blocking S1/A commands must use the exact network path already fixed elsewhere in
the plan.

**Replacement text:**

```powershell
& $python -B -m plant.src.vissim_strict.compiler network/real_world_gaepo_modi/modi_eval_rw_control.inpx --output outputs/signal_reference_v2_1.json
& $python -B scripts/build_vissim_lane_graph.py --network network/real_world_gaepo_modi/modi_eval_rw_control.inpx --out outputs/vissim_lane_graph_v2_1.json
```

### R4. The execution matrix still does not supply artifact schemas and deterministic verdict fields

**Prior finding:** I3

**Location:** `IMPLEMENTATION_PLAN.md:564-591`

The matrix is a substantial improvement, but its five columns merge the required seven
fields. Artifact entries such as `urban-kinematics-v2.1`, `boundary-coupling-v2.1`, and
`runtime-v2.1` are labels, not schemas. Several stop conditions name a failure category
without the task's PASS/FAIL/NOT_EVALUATED thresholds. The K command also does not bind
the explicit v2.1 audit/manifest paths required at 668-670.

**Replacement text for the matrix contract:**

```markdown
Add separate `artifact path + schema` and `numeric verdict` columns. Every blocking
row names a machine-readable JSON artifact, required keys/units/sample dimensions,
and exact PASS/FAIL/NOT_EVALUATED/BLOCKED expressions, or cites the exact body lines
containing them. Markdown may be an additional rendering, never the sole gate artifact.

K command:
`& $python -B scripts/audit_plant_fidelity.py --paired-futures outputs/paired_future_manifest_v2_1.json --json-out reports/plant_fidelity_evidence_manifest_v2_1.json --markdown-out reports/plant_fidelity_audit_v2_1.md --strict --require-complete`
```

## Minor findings

None. No additional non-load-bearing issues are introduced in this round.

## Final decision

**SPEC COMPLIANCE: FAIL** - one-shot certification remains unsafe in the executable
path, and dynamic/SPSA gate definitions are still incomplete.

**DOCUMENT QUALITY: FAIL** - blocking commands and the seven-field execution matrix
still require unresolved interpretation.

**CHANGES_REQUIRED**
