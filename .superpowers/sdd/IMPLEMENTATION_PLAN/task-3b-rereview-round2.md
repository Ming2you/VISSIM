# Task 3b Scoped Re-review - Round 2

**Verdict: CHANGES_REQUIRED**

## Round-1 Finding

### Parent cardinality - ADDRESSED

`IMPLEMENTATION_PLAN.md:332-339` now states the full Cartesian design unambiguously: 6 development parents, 9 sealed wave-A certification parents, and 15 unique demand-seed parents total. `IMPLEMENTATION_PLAN.md:372-373` makes those counts, missing/duplicate cells, and split overlap explicit PASS gates. The execution matrix also separates `E-fit` inputs as 6 development parents and `E-cert` inputs as 9 wave-A parents (`IMPLEMENTATION_PLAN.md:601-602`).

## Round-2 Checks

### BaselineOnly - VERIFIED

`IMPLEMENTATION_PLAN.md:127-131` defines one fixed/no-control demand-1.0/seed-13 parent and forbids Cartesian or certification expansion. The matrix command and verdict at `IMPLEMENTATION_PLAN.md:590` require exactly one complete 3,600-second parent and stop on any seed, demand, or path expansion. This closes the baseline-versus-matrix ambiguity.

### E-fit isolation - VERIFIED

`IMPLEMENTATION_PLAN.md:349-351` gives the fit process only the development manifest, removes certification telemetry through OS/file ACLs, and freezes fit plus source/topology/candidate/threshold/auditor hashes before certification access. `IMPLEMENTATION_PLAN.md:601` uses the six-parent development manifest and makes certification-file access a stop condition.

### Seven-field contract - VERIFIED

The normative seven items remain explicit at `IMPLEMENTATION_PLAN.md:65-71`. The matrix at `IMPLEMENTATION_PLAN.md:586-607` supplies inputs/hashes, implementation paths, commands, artifact path/schema, numeric verdict, prerequisites, and stop condition for every task; prerequisites and stop share the final display column but remain separately stated in each row. Required machine-readable keys and JSON authority are fixed at `IMPLEMENTATION_PLAN.md:609-611`.

## New Load-bearing Breakage

### Important R2-I1. E-cert consumes the one-shot wave before required I/J consumers

**Current references:** `IMPLEMENTATION_PLAN.md:342-351`, `IMPLEMENTATION_PLAN.md:417-419`, `IMPLEMENTATION_PLAN.md:450-457`, `IMPLEMENTATION_PLAN.md:484-485`, `IMPLEMENTATION_PLAN.md:556-568`, `IMPLEMENTATION_PLAN.md:601-605`, `IMPLEMENTATION_PLAN.md:625-635`.

The new isolation text says a separate one-shot `E-cert` validator opens wave A, and the matrix says a second scientific open retires the wave (`IMPLEMENTATION_PLAN.md:602`). Yet production decision parity uses 36 sealed certification states, runtime is stratified by certification seed, and J promotion uses the same sealed wave. The dependency graph places E before J, while K requires J and I. Under the literal one-shot rule, E-cert consumes the only authorized open and makes required I/J access a retiring second open. If multiple preregistered consumers are intended to share one certification campaign, that exception and result embargo are not defined.

**Replacement text:**

```markdown
Before opening a certification wave, create one `certification_campaign_manifest` that freezes the wave ID, all parent/run hashes, and the exact authorized consumers and code hashes for E-cert, I-2 decision parity, I-4 runtime, J paired futures, and K audit. One campaign orchestrator grants those consumers read-only access and withholds every scientific result until all preregistered consumers have completed or the campaign has failed. E-fit has no access.

Multiple preregistered consumers within that single first-pass campaign are not separate scientific opens. Any unregistered access, any access after results are released, any rerun after a scientific failure, or any changed consumer/code/hash retires the entire wave and requires the next fresh certification wave. Infrastructure-only retries retain the existing pre-action/outcome-independent exception and are recorded in the access log.
```

Replace the `E-cert` stop clause at `IMPLEMENTATION_PLAN.md:602` with:

```text
E-fit freeze + campaign manifest; unauthorized/post-release/changed-hash access retires wave
```

**Final verdict: CHANGES_REQUIRED.** The cardinality fix is correct, but the one-shot certification access model must allow all preregistered E/I/J/K consumers in one embargoed campaign without silently reopening the wave.
