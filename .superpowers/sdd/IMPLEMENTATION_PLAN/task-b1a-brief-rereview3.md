# B1a brief repair round 3 re-review

## Verdict

**REVISE**

All three previously OPEN Critical items are now addressed. One new Important omission
remains in the state-manifest producer: the `--states-root` discovery/completeness and
state-set hash semantics are undefined, and the exact command points at a broad
historical run root. This can either omit required states or make the canonical command
permanently `NOT_EVALUATED`, depending on implementation choices.

Counts: **prior OPEN items ADDRESSED 3 / OPEN 0; new findings ADDRESSED 0 / OPEN 1**.
Open severity: **Critical 0 / Important 1**.

## Prior OPEN dispositions

### 1. Replayable topology approval

**ADDRESSED**

The brief now supplies all load-bearing parts of the approval contract:

- an exact producer command with workspace, preflight, graph, routes, topology, and
  output arguments;
- a full `topology-approval-v2.1` JSON shape with global artifact fields;
- exact source paths and file/semantic hash field names for preflight/A1/A2 inputs;
- a separate approved-topology binding to exact topology bytes and semantics;
- a precise canonical semantic-hash payload;
- workspace-root-relative path resolution and containment;
- consumer-side loading, file/semantic recomputation, source revalidation, and matching
  against the separately supplied topology;
- atomic replacement with deterministic FAIL output and exit 1, PASS exit 0, and no
  stale-PASS claim when the output path is unusable.

Excluding `status` and `reasons` from the approval semantic payload is coherent because
the consumer separately requires `status=PASS` and `reasons=[]`. This approval remains
provenance/trust infrastructure and does not implement B1b.

### 2. State-manifest root, hashes, and producer CLI

**ADDRESSED** for the previously reported path/hash/CLI defects.

The manifest now uses `base_dir: ".."` from its required `outputs` location, resolves
that root once, and requires it to equal canonical `--workspace-root`. The workspace-
relative approval, topology, run, state, and sidecar examples therefore resolve to the
intended files instead of `outputs/outputs/...`. Child absolute paths, child `..`
escapes, duplicate resolved paths, and symlink/reparse escapes fail.

`input_hashes` is populated with approval, topology file/semantic, and state-set hashes;
the producer computes rather than accepts hashes. The exact producer CLI and exact
top-level/state-entry schema are present. A separate new producer-completeness issue is
reported below rather than leaving this prior path repair OPEN.

### 3. Immutable run manifest versus snapshot time

**ADDRESSED**

The immutable online run manifest is now limited to run identity, approved topology,
configuration, and optional allowed capture times. It no longer stores or mutates one
actual snapshot time. Actual `sim_sec` equality is correctly confined to snapshot-level
evidence: root state, `paused_at_sim_sec`, both COM capture times, post-run manifest
entry, assignment, and sidecar. This supports multiple states under one immutable run-
manifest hash while preserving exact per-snapshot attribution.

Run ID equality still spans the immutable run manifest and all snapshot outputs, which
is the correct run-level binding.

## New finding

### N-I1. State discovery and state-set hash semantics are not defined

**OPEN**

The sole producer command accepts only `--states-root evaluation/runs`, but the brief
does not define:

- which filenames are states (`state_*.json`, `anchor_*.json`, or another set);
- whether discovery is recursive;
- how archived/retried/stale runs and generated projection sidecars are excluded;
- how each state is paired with exactly one immutable run manifest;
- what proves that all required states for the selected run/campaign were included;
- whether states lacking the new envelope are included as `NOT_EVALUATED` or silently
  excluded;
- the canonical payload and ordering for `state_set_semantic_sha256`;
- the canonical payload for the manifest's own `semantic_sha256`.

The exact command's broad historical root already contains legacy run directories and
state artifacts. Including them makes the aggregate `NOT_EVALUATED`; filtering them by
presence of the new envelope can hide missing required evidence and allow a false PASS.
Either behavior is compatible with the current prose, so this is load-bearing rather
than an implementation detail.

Repair by making selection explicit and closed. Prefer a required run/campaign manifest
or repeatable `--state`/`--run-manifest` inputs over unconstrained recursive discovery.
If `--states-root` remains, define exact include/exclude patterns, attempt selection,
run-manifest pairing, and completeness identity. Define
`state_set_semantic_sha256` over a canonical list containing at least resolved workspace-
relative state path, state file hash, run ID, simulation time, run-manifest path/hash,
and sidecar path, sorted by `(run_id,sim_sec,state_path)`. Define the state manifest
`semantic_sha256` payload exactly, as was done for topology approval.

## New contradiction check

No new Critical contradiction was introduced. The repaired approval hash/status split,
workspace-root path model, and immutable-run/snapshot-time split are internally
consistent. The only new Important issue is the producer's undefined state universe and
hash scope above.

The B1a/B1b boundary remains clean. The brief still does not implement substep stocks,
transfer debit/credit, accepted external or sink flow, clipping removal, travel-time
buffers, receiving/sending constraints, or `TrafficState.total_physical_vehicles()`.
B-2/B-3/B-4 and promotion remain blocked after B1a.
