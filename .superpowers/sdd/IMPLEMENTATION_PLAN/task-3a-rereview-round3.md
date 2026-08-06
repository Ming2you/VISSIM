# Task 3a Scoped Re-review - Round 3

Reviewed only the round-2 N1 finding against the current `IMPLEMENTATION_PLAN.md`
(710 lines): sealed-wave production, enforceable E-fit isolation, the single embargoed
authorized-consumer campaign, and the corresponding matrix/dependency changes.

## Verdict

**APPROVED**

**SPEC COMPLIANCE: PASS**

**DOCUMENT QUALITY: PASS**

This approves the implementation plan as a specification. All NEW paths, wrappers, and
CLI behavior remain implementation work and must still pass their declared parser,
dry-run, ACL, campaign, and strict-audit gates before production promotion.

## Round-2 finding disposition

| Finding | Verdict | Current evidence |
|---|---|---|
| N1 sealed-wave production and ACL enforcement | **ADDRESSED** | Lines 349-357 define restricted E-fit access, denied-path proof, pre-registered consumers, one-shot access, embargo, retirement, and retry semantics. Lines 608 and 611-622 provide the enforcing wrapper, campaign producer, authorized consumers, access/embargo artifacts, and sole K release. Lines 636-655 provide an acyclic dependency graph. |

## Verification

### Sealed-wave producer

**PASS** - `IMPLEMENTATION_PLAN.md:611-612` defines separate `CERT-PREP` and
`CERT-WAVE` tasks. CERT-PREP freezes calibration, SPSA, scheduler, source/topology,
candidate, auditor, and consumer/code hashes. CERT-WAVE has an exact command and creates
`outputs/certification_wave_A_manifest_v2_1.json` with the 9/9 parent gate,
open/access/embargo log, and retirement conditions.

### Enforceable ACL wrapper

**PASS** - `IMPLEMENTATION_PLAN.md:349-350` requires a restricted identity/allowlist,
ACL denial of the reserved certification root, a denied-path probe, and zero
certification reads. Matrix row E-fit at line 608 routes fitting through
`scripts/run_calibration_fit_isolated.ps1` and makes readable certification data or an
access-log gap a stop condition. The direct unrestricted fitter path from round 2 is no
longer the execution contract.

### One authorized-consumer campaign

**PASS** - `IMPLEMENTATION_PLAN.md:352-357` seals E-cert, I-2, I-4, J, and K consumer
and code hashes before opening the wave. Lines 613-617 define each registered read-only
consumer. Lines 620-622 require the CERT-WAVE orchestrator to invoke them in one
restricted campaign, embargo intermediate scientific results, release once after K, and
retire the wave on unregistered/post-release access or code/hash mutation.

### Dependencies and matrix

**PASS** - `IMPLEMENTATION_PLAN.md:593-626` gives all scoped tasks concrete inputs,
implementation paths, commands, versioned machine artifacts, numeric verdicts, and stop
conditions. The graph at 636-655 correctly orders:

```text
E-fit -> production endpoint -> I-1/I-3 -> CERT-PREP -> CERT-WAVE
CERT-WAVE -> E-cert/J/I-2/I-4 -> K release/promotion
```

E-cert no longer precedes its manifest producer, J no longer supplies an undeclared
input, and certification evidence is not available to E-fit or development selection.

## New load-bearing breakage

None found in the round-3 fixes.

## Final decision

**SPEC COMPLIANCE: PASS**

**DOCUMENT QUALITY: PASS**

**APPROVED**
