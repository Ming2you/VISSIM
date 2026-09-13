# Known W_out route proposal — independent read-only review

Reviewed the draft at **2026-09-10 12:01:13 KST**. The accompanying JSON records
each file's exact SHA and modification time. Patch SHA at that snapshot:
`fa9dff10b6efb881cb19e8ec4665c15628d06f13c25f04ce8a8c74060e44fb9f`.
The author was still preparing portable checks during review; the findings
below are scoped to this draft, not a production application or MPC success.
I did not edit the proposal or production, run endpoints, or launch VISSIM.

No remaining blocking service/stock/ready-time defect was found by source
review in the current **known routes ON, Ω accounting ON** scope. Two missing
integration guards were found and corrected by the author during review:

- The ΩOFF schedule wrapper bypasses `schedule_offramp_arrivals_accounted`,
  which is where the new direct-receipt tag hook lives. The proposal now rejects
  known routes ON with ΩOFF before mutating configuration/state. This is an
  explicit scope restriction; the old feature-OFF path remains supported.
- Held post-choice unknown stock previously did not affect the existing
  `route_choice_prediction_route_complete` diagnostic. Its quantity now joins
  the existing held-unknown total and completeness result. The two saved
  fixtures have zero such unknown stock; this guard is for other snapshots.

## Stock owner and service order

`SC1004_W_out` remains the sole physical stock. Initialization attaches aliases
to the original projected records without changing storage, release buffer or
Ω ledger. Each positive physical assignment must name only this storage, and
the number of records must equal its occupancy. The current-route subsets are:

| Snapshot | Physical N | Known free | Known R_F_W | Known R_F_E | Before-choice |
|---|---:|---:|---:|---:|---:|
| 1200 | 20 | 12 | 4 | 0 | 4 |
| 3300 | 105 | 34 | 61 | 1 | 9 |

The initial fixtures have empty pending-release buffers. The helper nevertheless
preserves the existing aggregate readiness schedule when a buffer is present:
it distributes tags proportionally over existing due buckets. This retains
total ready N but **does not recover the unknown correlation of vehicle IDs,
destinations and due times**. The pending regression is aggregate timing
evidence, not observed per-route travel-time identification.

New urban receipts obtain the same `step + _link_delay_steps` used by the
existing owner for its release reservation. New direct receipts use the current
landing boundary, matching the original direct landing's absence of an extra
release delay. Mature pre-choice stock uses the existing normalized prior once;
after that its target persists. Unknown post-choice stock is held and not
redrawn. `reach/arrived` is the existing coarse finite travel-rate restriction;
unknown stock stays in its denominator and does not grant extra service to
known stock.

The original legsplit body still applies receiving capacity after the urban
body, reconciles accepted receipts, withdraws the source, and emits transfers.
Only then does `known_legsplit_commit` debit matching aliases. It validates
destination requests and the exact source-stock delta before doing so. Rejected
requests remain tagged for their original destinations. Plan references and
cohorts live within one candidate state; the existing tests cover clone
isolation and a fresh serialized worker. I read those tests but did not rerun
their suite or duplicate the author's endpoints.

## Free exit and route-evidence limits

The proposal adds no new Ω transfer emitter or intermediate sink. Existing
`legsplit:SC1004_W_out` transfer code continues to emit the accepted free amount;
68/121/10682 are inside Ω, while 10773/123 are outside. Existing 123 tail stock
has its separate original owner, so these tags do not duplicate that stock.
The patch changes which accepted quantities remain eligible for a free exit;
it does not move the old coarse exit timing gate. A resulting change in TTD
is not evidence that physical exit timing is now exact. The original aggregate
W_out travel/free-leg timing remains a model limitation.

Initial `1130:3 → free` is supported by each current route observation. Future
scalar `OR_F_E` direct receipts have no observed vehicle ID or current route.
The author now labels their `free` target as a **native-path prior**, and
validates that the pinned INPX has only one static route containing 10682,
namely 1130:3. Geometry alone is insufficient: 10682 joins 121 lane 1 at
118.446 m; the R_F_W connector 10646 leaves that same lane at 233.020 m,
just before 10773's free exit at 233.365 m. The prior is an explicit model
assumption and does not reconstruct freeway cohort provenance or prove that
the old scalar total off-ratio is correct.

## Saved evidence and what remains

The earlier saved 1200/3300 endpoints report stock closure, immutable inputs,
held commands and source changes `[]`, but predate four draft edits. The author
subsequently supplied `known_wout_replay_final_1200.json` (2.774 seconds) and
`known_wout_replay_final_3300.json` (3.489 seconds). I independently checked that
the final replay pins match the current helper/generator/replay/test sources
and that each complete metrics object equals its earlier counterpart exactly.
These are the author's endpoint runs, not independent endpoint executions by
this reviewer. Recorded E8 speeds remain 96.1159 and 13.5844 km/h, respectively.
The later portable12/fresh-worker checks cover the guards and completeness.

No conflict was found with the head-resource proposal: that proposal limits
10629's accepted regular service; this one receives the already accepted
quantity into the existing W_out owner and tags it. They do not own the same
capacity budget, initial projection or physical transfer. Root should perform
the actual combined runtime validation after the production freeze; this peer
review makes no full-MPC or performance claim.
