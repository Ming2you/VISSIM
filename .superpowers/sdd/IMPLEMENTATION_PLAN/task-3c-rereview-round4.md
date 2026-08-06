# Task 3c Scoped Re-review - Round 4

**Verdict: CHANGES_REQUIRED**

## Verified Fixes

### CERT-PREP request/config freeze - ADDRESSED

`IMPLEMENTATION_PLAN.md:352-358` now freezes expected parent specifications, preregistered pair/request IDs, demand/seed/config hashes, and authorized consumer/code hashes without claiming nonexistent runtime-output hashes. `CERT-WAVE` allocates immutable run IDs before launch, records actual telemetry/artifact hashes after execution, and gates request-to-run linkage 9/9 plus zero config mismatch, missing actual hash, or unexpected run ID. The matrix and dependency graph preserve `CERT-PREP -> CERT-WAVE -> consumers` (`IMPLEMENTATION_PLAN.md:620-626`, `:657-663`).

### Staged consumers, K, and release ordering - MOSTLY ADDRESSED

E-cert, I-2, I-4, J, and K use `$campaignStage` inputs/results, K depends on all four scientific consumers, and `CERT-RELEASE` follows K (`IMPLEMENTATION_PLAN.md:622-632`). The normative text covers read/write logging for both staging trees, alternate outputs, intermediate access, partial publication, and a single signed atomic release (`IMPLEMENTATION_PLAN.md:360-367`).

## Load-bearing Breakage Introduced by the Fix

### Important R4-I1. E-fit denies a different path from the actual certification staging root

`E-fit` still passes `-DeniedCertificationRoot evaluation/runs/certification_wave_A` (`IMPLEMENTATION_PLAN.md:617`), but `CERT-WAVE` now writes the campaign under `evaluation/runs/.certification_staging/wave_A` (`IMPLEMENTATION_PLAN.md:621`). The fit-side ACL and denied-path probe can therefore pass against the obsolete path while leaving the real certification input/result tree readable. That defeats the claimed certification-read count of zero and the enforceable holdout isolation.

Use one canonical reserved staging root in both commands, preferably denying the parent `evaluation/runs/.certification_staging` to the fit identity before any wave directory is created, and make the probe/access log verify that exact resolved root.

**Final verdict: CHANGES_REQUIRED.** The output-hash deadlock and staged consumer/release sequence are repaired, but the ACL path mismatch leaves the embargo unenforced against E-fit.
