# B1a brief repair round 4 final re-review

## Verdict

**REVISE**

The broad-discovery, completeness, pairing, missing-file, ordering, and hash-scope parts
of the prior finding are repaired. The finding is not fully closed because the
selection's per-entry `required_vehicle_records` policy is dropped when producing the
state manifest, and the selection artifact itself is not hash-bound as a manifest
input. This creates one new Critical contradiction and one new Important provenance
omission.

Counts: **sole prior OPEN item ADDRESSED 0 / OPEN 1**. New issues within that item:
**Critical 1 / Important 1**.

## Sole prior finding disposition

### Closed state universe, completeness, pairing, and hashes

**OPEN**

The revision successfully fixes most of the requested contract:

- `--states-root` and broad filesystem discovery are removed;
- the producer consumes one closed `state-selection-v2.1` artifact;
- no glob, archive, retry, sidecar, or unlisted state can be inferred;
- `expected_entry_count`, list length, state-path uniqueness, and
  `(run_id,sim_sec)` uniqueness close the selected universe;
- every selected state is paired with one exact immutable run manifest and matching
  run/time provenance;
- missing listed files fail instead of disappearing;
- an empty selection is explicit and yields downstream `NOT_EVALUATED`;
- `state_set_semantic_sha256` has an exact ordered payload;
- the state-manifest `semantic_sha256` has an exact payload.

Two load-bearing defects remain.

## New Critical contradiction

### N-C1. `required_vehicle_records` is lost before validation

`state-selection-v2.1` entries contain `required_vehicle_records`, and the brief says a
listed state missing a **required** envelope remains listed and later fails validation.
But the exact `state-manifest-v2.1.states[]` schema does not carry that flag, and
`state_set_semantic_sha256` does not hash it. The validator receives only the state
manifest and topology, so it cannot distinguish:

- a selected state with `required_vehicle_records=true`, which must be FAIL when the
  envelope is absent; from
- a selected state with `required_vehicle_records=false`, for which the existing brief
  says absence is `NOT_EVALUATED`.

The producer cannot silently enforce the distinction either: the normative text says
the required-but-missing state remains listed for later FAIL, while the manifest loses
the fact that made it required. Two compliant implementations can therefore produce
different verdicts from identical manifest bytes.

Add `required_vehicle_records` to every state-manifest entry, require exact equality
with the selection entry, and include it in the canonical state-set hash and manifest
semantic payload through `states`. Tests must pin true+missing as FAIL and false+missing
as NOT_EVALUATED. Alternatively remove the flag entirely and declare every nonempty
B1a selection entry required, but then update the no-envelope status rule consistently.

## New Important omission

### N-I1. The closed selection artifact is not bound as an input

The producer command now consumes `outputs/state_selection_v2_1.json`, but the exact
state-manifest `input_hashes` and body contain neither its path nor its exact file or
semantic hash. `campaign_id` and `expected_entry_count` are also not propagated. The
manifest therefore cannot prove which closed campaign selection produced its state
universe, despite the global artifact contract requiring exact input hashes.

This matters beyond byte provenance because `campaign_id`, expected completeness, and
`required_vehicle_records` are selection semantics not fully represented by the current
state list. A different selection can generate the same currently hashed list while
carrying a different requirement policy.

Add a `state_selection` binding with workspace-relative path, file SHA-256, semantic
SHA-256, schema/status/reasons validation, `campaign_id`, and expected count. Include
the file/semantic hashes in `input_hashes`. Define the selection artifact's own exact
semantic payload over its behavioral global fields, campaign identity, expected count,
and canonical entries. The producer and validator must load and verify that binding, or
the producer must copy all selection semantics into the manifest and hash them
explicitly.

## Contradiction check

No other new Critical or Important contradiction was found. The closed list removes the
historical-run discovery problem, missing listed files fail closed, run-manifest pairing
is exact, and both newly defined manifest hashes have deterministic ordering and payload
scope for the fields they currently include.

The B1a/B1b boundary remains intact. State selection and projection manifests are
initial-state provenance only; no substep transfer, clipping, travel-time buffer,
receiving/sending, sink/source flow, or `TrafficState.total_physical_vehicles()` work is
introduced.
