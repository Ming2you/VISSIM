# B1a slice 2: adapter projection-only and bounded projection reference

## Purpose and precedence

Implement the adapter half of the approved B1a trusted live path. The production
adapter must project one strict VISSIM state to the approved A2 physical-stock topology
before any NumSim/controller work, publish one physical projection sidecar plus one
bounded reference, and require the normal action path to validate and consume those
exact bytes before any controller, candidate, or fallback evaluation.

Read `.superpowers/sdd/IMPLEMENTATION_PLAN/task-b1a-run-live-trust-brief.md` first. Its
normative closure and fix-round amendments govern. Preserve all S0R/S1/A1/A2/B1a
capture/core/run-manifest contracts. This slice does not edit VBS/watchdog launch or
timing, does not implement post-run manifests/live replay, and does not implement B1b
transfer dynamics. Live COM and live p95 remain `NOT_EVALUATED`.

## Shared package interfaces

Implement controller-independent validators/builders under `plant/src/vissim_strict`
and export the public interfaces from `__init__.py`. Do not duplicate projection,
canonical JSON, path, hash, or run-manifest validation logic in the adapter.

- Add strict validation for a complete `projection-v2.1` sidecar. Recompute its
  semantic hash, normalized projection hash, assignment/stock totals, view summaries,
  diagnostics, exact run/state/topology/approval bindings, and the one-vehicle/one-stock
  mass identities. Never trust authored counts, status, reasons, or hashes.
- Add exact `physical-projection-reference-v2.1` production and validation. Its exact
  keys are
  `schema_version/status/reasons/qualification/run_id/sim_sec/run_manifest_sha256/state_path/state_file_sha256/topology_file_sha256/topology_semantic_sha256/projection_sidecar_path/projection_sidecar_file_sha256/projection_sidecar_semantic_sha256/normalized_projection_sha256/record_count/assigned_count/stock_total/global_residual/semantic_sha256`.
- The reference contains no assignments. PASS requires empty reasons and exact
  qualification copied from the immutable run manifest. Canonical JSON v1 hashes every
  listed field except `semantic_sha256`, including status and reasons.
- Reference validation must bounded-reopen the exact state and sidecar; validate the
  immutable run manifest and approved topology; independently recompute file hashes,
  semantic hashes, normalized projection hash, record/assigned/stock totals, and global
  residual; and reject missing/extra keys, duplicate JSON keys, nonfinite/boolean
  numerics, path escape/reparse/case/slash mismatch, identity mismatch, or non-PASS.
- Apply the approved bounds before opening/reading: state envelope <=8 MiB, projection
  sidecar <=16 MiB, projection reference <=32 KiB. Paths stored in JSON are canonical
  workspace-relative forward-slash paths and resolve to exact non-reparse contained
  files. Preserve spaces and non-ASCII Windows paths.
- Use atomic same-directory publication with complete canonical LF-terminated UTF-8
  bytes. A reader must never observe a partial final file. Failure must not leave stale
  PASS evidence that a later normal adapter invocation can accept.

## Projection-only adapter path

Extend `evaluation/controllers/vissim_stackelberg_adapter.py` with a production
`--projection-only` mode and explicit inputs for the immutable run manifest, approved
physical topology, output projection sidecar, and output projection reference. Make
action outputs/controller/configuration arguments conditionally required only for the
normal action path.

The projection-only ordering is binding:

1. Parse arguments and bounded strict-load the run manifest/state.
2. Validate the immutable run manifest through the shared package API and verify the
   adapter's executed source binding.
3. Resolve and validate the exact approved topology/approval binding from that
   manifest; reject a caller-supplied topology that differs in path, file hash, or
   semantic hash.
4. Strict-normalize the root `vehicle_records` and call the sole public
   `project_vehicle_records` implementation exactly once.
5. Atomically publish the validated projection sidecar, then the bounded validated
   reference, and exit success without writing any action file.

Before step 5 fails, no PASS reference may exist. This path must return before
`repo_imports`, NumSim import/path mutation, controller/config/forecast construction,
candidate evaluation, fallback evaluation, previous-action parsing, mapping/calibration
loading that is irrelevant to projection, or action JSON/CSV writing. There must be no
second projector implementation.

## Normal action path

Add required normal-path inputs for the exact projection-reference path and expected
file SHA-256, plus the immutable run-manifest path. Before `repo_imports` or any
controller/fallback/candidate work, the adapter must:

- validate the run manifest and adapter source binding;
- validate the reference through the shared validator, which reopens the exact state,
  topology, and sidecar and recomputes every binding and mass value;
- compare the caller-supplied reference hash byte-for-byte;
- bind `(run_id, sim_sec)`, qualification, state path/hash, topology path/hashes, and
  run-manifest hash exactly.

The normal path must use this prevalidated projection result as the sole B1a physical
projection input and carry its hashes/identity into action provenance. It must not call
`project_vehicle_records` again and must not proceed through a legacy aggregate-only
bypass when the reference is absent or invalid. This slice may adapt the validated
ledger into the existing state-construction boundary, but it must not invent B1b
substep transfer dynamics or claim plant-future fidelity.

## Tests

Add focused package and adapter tests covering:

- exact reference happy path and every top-level missing/extra/type/range/status/hash
  mutation;
- sidecar assignment/stock/view/diagnostic/normalized-hash mutation, including coherent
  rehash attempts and mass residuals;
- state, run, qualification, topology, approval, path, file-hash, semantic-hash, and
  `(run_id,sim_sec)` mismatch;
- bounds checked before read, malformed/duplicate/nonfinite JSON, stale PASS handling,
  partial-publication visibility, spaces/non-ASCII paths, slash/case/reparse/escape;
- projection-only calls the sole projector exactly once and cannot reach NumSim,
  controller/config/forecast/candidate/fallback/action writers even when those entry
  points are poisoned;
- normal mode rejects missing/invalid/mismatched reference before NumSim/candidate or
  fallback evaluation, consumes a valid prevalidated ledger, never reprojects, and
  records exact projection provenance in both action outputs;
- existing legacy behavior is available only outside explicitly required B1a mode;
  required mode has no permissive fallback.

Run the new focused tests plus B1a core/provenance/run-manifest, A1/A2, compiler/signal,
and existing adapter-fidelity regressions. Do not manufacture a live COM or p95 PASS.

## Report

Write
`.superpowers/sdd/IMPLEMENTATION_PLAN/task-b1a-adapter-projection-reference-slice-report.md`
with changed files, public schemas/APIs, exact adapter ordering, commands/counts/results,
remaining future-slice dependencies, and self-review. Return `DONE`,
`DONE_WITH_CONCERNS`, `NEEDS_CONTEXT`, or `BLOCKED` and keep live gates honest.
