# B1a Slice 3B fix round 4

## Objective

Close the sole Important finding in
`task-b1a-vbs-run-binding-capture-sidecar-fix3-rereview.md` and finish the complete
state-envelope replay invariant. Stay strictly within Slice 3B; no VISSIM/COM or later
slice work.

## Required fix

Create one shared Python validator used by capture production and reusable capture
validation that enforces the exact `vehicle_records` envelope and rederives all physical
count identities from the already strict six-field records:

- exact envelope fields/schema/completeness/source attributes/threshold;
- exact paused/capture times and nonnegative bounded integer count fields;
- `collection_count_before == collection_count_after == record_count == unique records`;
- `unobservable_count == external_source_count == 0`;
- canonical positive-decimal link-map keys and nonnegative bounded integer values;
- `full_network_link_counts` equals per-link record totals exactly;
- `full_network_link_stopped_counts` equals per-link `speed_kph < 1.0` totals exactly,
  including required zero keys and no missing/extra keys;
- derived stopped total is internally consistent; root `total_vehicles` and
  `stopped_vehicles`, when part of the required VBS state contract, must equal the
  derived totals.

Add producer and reusable-validator mutation tests for wrong/missing/extra count keys,
wrong stopped counts, boolean/string/negative/oversize map values, noncanonical keys,
count scalar drift, envelope extra/missing fields, and root total drift. Preserve every
prior Slice 3B fix. Update report/progress, run bounded no-VISSIM tests, and end
`IMPLEMENTED_PENDING_INDEPENDENT_REREVIEW`.

## Acceptance

The prior independent tamper repro fails in both producer and validator; focused tests
and `git diff --check` pass; live-only gates remain `NOT_EVALUATED`.
