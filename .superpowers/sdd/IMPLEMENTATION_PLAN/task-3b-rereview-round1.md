# Task 3b Scoped Re-review - Round 1

**Verdict: CHANGES_REQUIRED**

## Prior Findings

| Prior finding | Verdict | Current evidence |
|---|---|---|
| C1. Transfer-level mass conservation | **ADDRESSED** | `IMPLEMENTATION_PLAN.md:215-218` makes `(run_id,VehNo)` ownership unique and forbids residual `N_unobservable`; `:220-224` defines per-stock conservation, immutable transfer IDs, exactly one debit/credit, transfer-multiset equality, and a global equation without internal flow; `:226-231` retains rejected demand and makes mismatch, duplicate/missing IDs, clipping, and forced split/merge/full-receiver failures blocking. |
| C2. One-shot certification separation | **ADDRESSED** | `IMPLEMENTATION_PLAN.md:329-345` separates development from certification, freezes all selection inputs before opening wave A, retires a failed wave, and requires fresh seeds/version after scientific failure; `:361-364` defines certification metrics; `:468-470` restricts promotion to sealed-wave seeds; `:539-550` excludes opened certification failures from the fix loop. |
| C3. Canonical action epoch | **ADDRESSED** | `IMPLEMENTATION_PLAN.md:447-450` defines the anchor after the ending transition, pause/capture/readback/resume order, prefix endpoint, and first allowed divergence; `:461-464` records state hash/effective transitions and adds exact clock fixtures; `:471-483` fixes the 60-transition validity interval, base restoration, identical plant interval, and delayed-offset blocking rule. |
| C4. Per-seed ranking and independent spillback support | **ADDRESSED** | `IMPLEMENTATION_PLAN.md:490-501` uses three base repeats only for noise, within-prefix `Delta J`, mandatory complete cells, and forbids repeats from increasing support; `:525-527` gates by demand/H/channel/lever/seed and requires every seed to pass; `:529-532` counts independent `(run_id,anchor,physical_stock_id)` episodes, requires per-stratum positive/negative support, and forbids pooling across seed and other dimensions. |
| C5. SPSA units, support, and independence | **ADDRESSED** | `IMPLEMENTATION_PLAN.md:370-380` enforces one endpoint, converts objective noise to gradient units, and adds `h` versus `h/2` convergence; `:381-389` preregisters k/directions, requires state/material support, and uses per-stratum state-block intervals; `:390-397` counts only one preregistered coordinate per independent state-direction batch, requires exact CP support, handles N-stage bases, blocks empty remainder, and freezes selection before certification. |
| C6. End-to-end runtime and fallback | **ADDRESSED** | `IMPLEMENTATION_PLAN.md:425-431` preserves both clocks but gates only scan-to-readback end-to-end time, terminates workers at 42 seconds, and includes fallback in the 45-second maximum; `:432-437` defines safe fallback, four-dimensional strata, independent runs, hardware provenance, and uncensored timeout handling; `:439-441` gates p95 UCL, max, fallback/timeout, readback, orphan workers, and fault recovery. |
| I1. SC12 profile-policy nuance | **ADDRESSED** | `IMPLEMENTATION_PLAN.md:168-174` preserves shared lane-2 through/left geometry and maps each lane to its actual head; `:175-182` explicitly labels SG-pair equality as profile policy rather than a physical invariant and requires a network/head change only to separate lane-2 indications. |
| I2. Boundary/ramp/freeway backpressure | **ADDRESSED** | `IMPLEMENTATION_PLAN.md:248-257` bounds the physical exit stock, keeps its sink unbounded when appropriate, and retains rejected external arrivals; `:261-269` defines physical queues, receiving-budget merge competition, and lane-derived diverge blocking; `:274-276` requires full-receiver/merge/off-ramp/exit/source behavioral fixtures and per-interface gates; `:580` makes their validator blocking. |
| I3. Test and compiler commands | **ADDRESSED** | `IMPLEMENTATION_PLAN.md:75-78` reports all 106 baseline tests; `:94-109` marks the source verifier NEW, requires `RW_PYTHON_EXE`, executes all three test roots in the import context they require, and blocks discovery loss/skips; `:140-142` uses the compiler's positional INPX plus `--output`; `:566-575` adds CLI/dry-run contracts. |
| M1. Objective modes | **ADDRESSED** | `IMPLEMENTATION_PLAN.md:207-209` separates ownership normalization from named include/exclude objective weights; `:248-253` requires byte-identical physical traces between objective modes and exact boundary-contribution accounting. |

## New Load-bearing Breakage

### Important N1. Parent-run cardinality contradicts the revised certification matrix

**Current references:** `IMPLEMENTATION_PLAN.md:331-337`, `IMPLEMENTATION_PLAN.md:468-470`, `IMPLEMENTATION_PLAN.md:539-540`, `IMPLEMENTATION_PLAN.md:583`.

The table defines 6 development parents (`2 demands x 2 seeds` plus `1 demand x 2 seeds`) and 9 wave-A certification parents (`3 demands x 3 seeds`), for 15 total. This is confirmed by J requiring every certification seed over all three demands. However, line 331 still says nine runs total, and the execution-contract row at line 583 says "nine development parents." An implementer can satisfy either stale count while omitting required development or sealed-wave cells.

**Replacement text:**

```markdown
3,600-second parent runs are 15 for the first promotion attempt: 6 development parents and 9 sealed wave-A certification parents. Wave A contains the full Cartesian product of demands `0.75/1.0/1.25` and seeds `47/59/71`. Any fresh certification wave likewise contains 9 parents over the same three demands and its three preregistered fresh seeds.

PASS: development parent count 6, wave-A certification parent count 9, unique demand-seed parent count 15, expected Cartesian cell missing/duplicate 0, and development/certification overlap 0.
```

Replace the E execution-matrix input phrase at `IMPLEMENTATION_PLAN.md:583` with:

```text
six development parents + nine sealed wave-A certification parents
```

**Final verdict: CHANGES_REQUIRED.** All prior findings are addressed; the parent-matrix cardinality contradiction must be corrected before approval.
