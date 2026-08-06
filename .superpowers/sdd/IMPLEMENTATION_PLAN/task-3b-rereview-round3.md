# Task 3b Scoped Re-review - Round 3

**Verdict: CHANGES_REQUIRED**

## Round-2 Finding

### Certification-consumer sequencing - ADDRESSED

`IMPLEMENTATION_PLAN.md:352-358` now freezes E-cert, I-2, I-4, J, and K as authorized consumers of one campaign, treats their preregistered accesses as one scientific open, embargoes results, and retires the wave on unregistered or post-release access. The execution matrix assigns `CERT-PREP` and `CERT-WAVE` before all five consumers (`IMPLEMENTATION_PLAN.md:611-617`), explicitly says the orchestrator invokes them in one restricted campaign (`:620-622`), and the dependency graph preserves that sequence (`:647-652`). E-cert no longer consumes the wave before I/J.

## New Load-bearing Breakage

### Important R3-I1. CERT-PREP requires hashes for certification runs that do not yet exist

**Current references:** `IMPLEMENTATION_PLAN.md:352-353`, `IMPLEMENTATION_PLAN.md:611-612`.

Before opening wave A, the campaign manifest is required to contain nine `parent/run` hashes, and `CERT-PREP` must freeze nine parents. But the restricted `CERT-WAVE` command is the step that creates those parent runs and their manifest. Actual run/telemetry/content hashes cannot be known at CERT-PREP. Treating planned configuration hashes as completed run hashes would falsely certify artifacts that have not run; requiring actual hashes deadlocks the sequence.

**Replacement text:**

```markdown
CERT-PREP freezes the nine expected Cartesian parent specifications, preregistered `pair_id`/run-request IDs, demand/seed/config hashes, and every authorized consumer/code hash. It does not claim hashes of runtime outputs that do not yet exist.

CERT-WAVE allocates immutable run IDs before launch, executes exactly those nine requests, and records actual parent telemetry/artifact hashes in the sealed campaign manifest. PASS requires request-to-run linkage 9/9, request/config hash mismatch 0, actual artifact hash missing 0, and unexpected run ID 0. Downstream consumers accept only those post-run hashes.
```

### Important R3-I2. Intermediate result paths bypass the stated ACL embargo

**Current references:** `IMPLEMENTATION_PLAN.md:349-355`, `IMPLEMENTATION_PLAN.md:357-358`, `IMPLEMENTATION_PLAN.md:612-622`.

The only concrete denied/restricted filesystem root is `evaluation/runs/certification_wave_A`. E-cert, I-2, I-4, J, and K write scientific outputs directly to ordinary `outputs/` and `reports/` paths (`IMPLEMENTATION_PLAN.md:613-617`). Those paths are not declared ACL-restricted or staged, so an external session can read an intermediate result before K while the plan still reports unauthorized access 0. The prose embargo is therefore not enforceable by the commands as written.

**Replacement text:**

```markdown
CERT-WAVE creates one ACL-restricted campaign staging root containing certification inputs and every intermediate E-cert/I-2/I-4/J/K output. All registered consumer commands write only beneath that staging root. The ACL/access logger covers both reads and writes for the input and result trees and proves that only the orchestrator identity and registered child processes accessed them.

K writes its audit and release manifest inside staging. After K completes, the orchestrator atomically publishes one signed, exact-hash result bundle to the normal `outputs/` and `reports/` paths and then records the single release event. No scientific result path exists outside staging before that release. Any failed ACL probe, pre-release external access, alternate output path, or partial publish retires the wave.
```

Update the consumer commands at `IMPLEMENTATION_PLAN.md:613-617` to receive an orchestrator-provided restricted staging output path rather than writing directly to public `outputs/` or `reports/` locations.

**Final verdict: CHANGES_REQUIRED.** Consumer sequencing is repaired, but CERT-PREP must distinguish request hashes from post-run hashes and the embargo must cover every intermediate result path.
