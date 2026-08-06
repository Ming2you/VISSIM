# Task 3a Scoped Re-review - Round 2

Reviewed only the round-1 findings N1 and R1-R4 against the current
`IMPLEMENTATION_PLAN.md` (693 lines). Settled findings were not reopened.

## Verdict

**CHANGES_REQUIRED**

**SPEC COMPLIANCE: FAIL**

**DOCUMENT QUALITY: FAIL**

R1-R4 are addressed. N1 remains unresolved at the executable one-shot boundary: the
plan consumes a sealed certification manifest that no task produces, and the direct
E-fit Python command does not enforce the stated OS/file ACL separation.

## Finding disposition

| Round-1 finding | Verdict | Current evidence |
|---|---|---|
| N1 one-shot certification execution | **NOT_ADDRESSED** | `-BaselineOnly`, 6+9=15 parent counts, separate E-fit/E-cert commands, and wave retirement are fixed at 127-131, 332-351, 372-373, and 590-602. However, `outputs/certification_wave_A_manifest_v2_1.json` is consumed at 602 without a producing task, and E-fit's direct command at 601 does not establish or verify the ACL promised at 349 and 601. |
| R1 signed bias/spillback keys | **ADDRESSED** | Lines 528-549 define signed-bias limits using each H-specific denominator/limit, retain flow bias `<=10%`, key spillback by certification seed, prohibit pooling, and remove the undefined interface-p95 gate. |
| R2 SPSA h/support/UCB | **ADDRESSED** | Lines 384-413 define channel-specific h, realized displacement, 12 clusters per `channel x demand x H`, nonempty material support, overall/channel exact UCB limits, and independent Bernoulli counting. |
| R3 exact commands | **ADDRESSED** | Lines 591 and 593 use the exact INPX path; no blocking command contains `<inpx>`. |
| R4 seven-field matrix/schemas/K paths | **ADDRESSED** | Lines 581-611 provide seven distinct columns, machine-readable artifact paths/schema versions, numeric-verdict references, common required schema keys, and exact K JSON/Markdown output paths. |

## Critical finding

### N1. Sealed-wave production and ACL enforcement are missing

**Location:** `IMPLEMENTATION_PLAN.md:349-351`, `IMPLEMENTATION_PLAN.md:601-606`,
`IMPLEMENTATION_PLAN.md:621-635`

The prose requires E-fit to have no access to certification telemetry. The matrix then
runs the fitter directly under the ordinary repository Python process at 601; no wrapper,
restricted token, allowlist, ACL setup command, denied-path probe, or ACL evidence
artifact enforces that requirement.

E-cert at 602 consumes `outputs/certification_wave_A_manifest_v2_1.json`, but no matrix
row creates that file. J creates only `outputs/paired_future_manifest_v2_1.json` at 605
and currently depends on all of E. The graph likewise places E before the production
endpoint and J at 621-627. Therefore the sealed wave cannot be opened by a declared
command without either inventing an unplanned step or creating an E/J dependency cycle.

**Replacement text:**

Replace E/J execution rows and the corresponding dependency edges with an explicit
three-stage boundary:

```markdown
| E-fit | development parents 6 only | **NEW** isolated-fit wrapper and fitter | `powershell -NoProfile -File scripts/run_calibration_fit_isolated.ps1 -DevelopmentManifest outputs/calibration_development_manifest_v2_1.json -DeniedCertificationRoot evaluation/runs/certification_wave_A -Out evaluation/calibration/physical_stock_calibration_v2_1.json` | calibration JSON plus `outputs/calibration_fit_access_log_v2_1.json`; `physical-calibration-v2.1`/`access-log-v2.1` | fit/CI/prior/support PASS; denied-path probe returns access denied; certification reads `0` | A/B; any readable certification path or access-log gap stops |
| CERT-WAVE | frozen calibration/source/topology/candidate/threshold/auditor hashes and pre-registered seeds 47/59/71 | **NEW** one-shot certification orchestrator | `powershell -NoProfile -File scripts/run_certification_wave_v2_1.ps1 -Request outputs/certification_wave_A_request_v2_1.json -OutDir evaluation/runs/certification_wave_A` | `outputs/certification_wave_A_manifest_v2_1.json`, `certification-wave-v2.1`; exactly 9 parent IDs plus all pre-registered J/I/runtime child IDs and open/access log | parent Cartesian cells 9/9; duplicate/missing 0; one scientific open; frozen hash mismatch 0 | E-fit and production endpoint/I-1 freeze; second open or partial wave retires wave A |
| E-cert | frozen calibration + CERT-WAVE manifest | **NEW** read-only one-shot validator | `& $python -B scripts/validate_physical_stock_calibration.py --calibration evaluation/calibration/physical_stock_calibration_v2_1.json --certification-manifest outputs/certification_wave_A_manifest_v2_1.json --out reports/physical_stock_calibration_certification_v2_1.json` | certification JSON, `physical-calibration-certification-v2.1` | every E per-stock certification gate PASS | CERT-WAVE; mutation, second scientific open, or failure retires wave A |
| J | CERT-WAVE manifest and paired child runs | paired manifest builder/analyzer | `& $python -B scripts/build_paired_future_manifest.py --certification-manifest outputs/certification_wave_A_manifest_v2_1.json --out outputs/paired_future_manifest_v2_1.json` | paired manifest JSON, `paired-future-v2.1` | J prefix/action/per-stratum/support gates | CERT-WAVE; failure/partial cell blocks promotion |
```

Replace the affected dependency graph with:

```text
A-2 -> B -> E-fit frozen calibration
A-2 + B + C + D-core + E-fit -> production rollout endpoint/objective
production endpoint + I-1 frozen k/thresholds + all frozen manifests
  -> CERT-WAVE one-shot open
CERT-WAVE -> E-cert + J paired gates + I-2 decision parity + I-4 runtime evidence
E-cert + J + I-2 + I-4 + strict provenance -> K strict complete audit
```

The isolated-fit wrapper must run under an enforceable restricted identity or staged
allowlist where the certification root is absent/denied; a prose promise or fitter-side
path check is not an ACL boundary.

## Important findings

None.

## Minor findings

None.

## New load-bearing breakage from round-2 fixes

The missing CERT-WAVE producer/dependency edge and unenforced ACL described under N1 are
the only new load-bearing breakage identified. No other round-2 regression was found.

## Final decision

**SPEC COMPLIANCE: FAIL** - calibration/certification separation is stated but cannot be
executed without an undeclared wave-opening step.

**DOCUMENT QUALITY: FAIL** - the execution matrix has an unresolved input producer and
an ACL requirement with no enforcing command or evidence artifact.

**CHANGES_REQUIRED**
