# B1a slice 1: immutable run identity and monotonic clock

## Purpose

Implement the first executable slice of the approved trusted runner/live-evidence
architecture. This slice creates and strictly validates the immutable per-attempt
`run-manifest-v2.1`, pins the supported VISSIM version policy and producer sources, and
provides the cross-process monotonic-clock helper. It does not edit VBS, watchdog,
adapter controller flow, post-run manifests, or live replay.

Read `.superpowers/sdd/IMPLEMENTATION_PLAN/task-b1a-run-live-trust-brief.md` first. Its
`Normative closure`, `Fix-round-4`, and `Fix-round-5/6` amendments govern. Preserve all
existing B1a/A1/A2 contracts and keep live gates `NOT_EVALUATED`.

## Public implementation

Add a controller-independent public module under `plant/src/vissim_strict` for exact
run-evidence schemas, canonical payloads, validation exceptions, and strict validators.
Export it through `plant/src/vissim_strict/__init__.py`.

The module must implement:

- exact `run-manifest-v2.1` top-level and nested validation;
- canonical JSON v1 semantic payload/hash;
- strict qualification, run/campaign/attempt identity, allowed capture time,
  configuration, approved topology, preflight, producer role, policy, path, numeric,
  and duplicate-binding checks;
- `validate_run_manifest` returning one immutable validated result or one typed error;
- create-once atomic publication helpers: absent destination succeeds, byte-identical
  validate-only reuse succeeds without rewrite, differing existing bytes fail without
  modifying the manifest;
- a separate deterministic `run-manifest-creation-result-v2.1` writer for creation
  failure/success evidence. A stale result is atomically replaced; the immutable
  manifest is never replaced after creation.

Update `scripts/build_state_manifest_v2_1.py` to delegate its existing run-manifest
checks to the shared strict validator. Do not leave a permissive second implementation.

## Producer CLI

Add `scripts/build_run_manifest_v2_1.py`. Required inputs cover the exact workspace,
run directory, run/campaign/attempt identities, qualification mode, topology approval,
preflight, all closed producer-source roles, all configuration input files, simulation
fields, allowed capture times, output manifest, and creation-result output. A structured
JSON request is allowed to keep the PowerShell invocation bounded, but that request
must itself have an exact versioned schema, contained paths, deterministic semantic
hash, and stale-output behavior.

The producer must validate `topology-approval-v2.1` with the existing independent A2
replay, validate the exact PASS preflight and required producer source hashes, build the
five-key approved topology binding, and reject sources/configuration that disagree.
The output directory must be an exclusive non-reparse descendant of the workspace.

Exit codes: `0=created or byte-identical validate-only success`, `1=typed failure`.
Every parseable invocation with usable creation-result output replaces that result.

## Supported-version policy

Add a checked-in `supported-vissim-versions-v2.1` policy and shared strict parser. The
policy has an exact field set and semantic hash. Preserve the raw COM string; accept
only finite ASCII input whose leading major is exactly `20` or `2020`, normalize both
to integer `2020`, and reject all other/empty/malformed values. The policy binding in
the run manifest is exact `schema_version/path/file_sha256/semantic_sha256`.

The policy parser is pure and does not claim a live COM observation. Synthetic mode is
always insufficient for the live gate regardless of version text.

## Monotonic helper

Add `scripts/read_monotonic_clock.py`. It performs no file/network/import side effects
outside standard-library startup, requires Windows Python >=3.10, reads exactly one
`time.perf_counter_ns()`, and writes exactly one ASCII line
`python_perf_counter_ns=<positive decimal integer>\n` to stdout with empty stderr.
Success exits 0; unsupported platform/version or invalid counter exits 1 without a
success-looking line. Expose a pure parser for this framing in the shared module.

## Tests

Add focused tests for:

- exact happy-path manifest and every missing/extra top-level or nested key;
- run ID/campaign/attempt/qualification/type/range/enum/time mutations;
- approved topology, approval/preflight/source/config/policy path+hash disagreement;
- duplicate executed-source binding and demand-profile null/present equality;
- mutable snapshot-time injection and unsorted/duplicate/empty allowed times;
- absolute/escaping/reparse/case/slash/non-ASCII/space paths under Windows semantics;
- exclusive create, byte-identical reuse without mtime change, differing no-clobber,
  concurrent create race, and deterministic creation-result replacement;
- malformed/huge standard JSON values replacing stale result without uncaught errors;
- exact supported-version parser/policy and tamper cases;
- monotonic helper exact stdout/stderr/framing, increasing readings, unsupported-path
  behavior, and parser mutations.

Run focused B1a core/provenance, preflight, A1/A2, and compiler regressions. Do not
regenerate checked-in real PASS artifacts unless their complete current source universe
can be rebuilt and validated; stale real evidence must remain honestly invalid.

## Report

Write `.superpowers/sdd/IMPLEMENTATION_PLAN/task-b1a-run-manifest-slice-report.md` with
changed files, exact schemas, commands/results, source/preflight compatibility, live
gate state, and self-review. Return no live COM or p95 PASS claim.
