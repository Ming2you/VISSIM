The remaining support gaps are already used by recorded traffic. A single pass over every pinned Ver2 one-second recording found positive stock on exactly six of the28 unresolved physical links:10379,10381,10610,10611,10627 and10634. The five completed runs each cover1–5400 seconds; the two controlled β0 runs are censored at1050 and1350 seconds. The scan read136,697,201 vehicle rows, recomputed every raw FZP SHA, and matched all five existing completed-run measurement hashes. No model, input, run output or manifest was changed by this presence audit.

| Recorded run | 10379 unique vehicles | 10381 | 10610 | 10611 | 10627 | 10634 |
|---|---:|---:|---:|---:|---:|---:|
| Native NC (`codex_meter10639_g5_s13_20260910`; meter command had failed) |468|169|59|66|60|709|
| Meter retry |472|165|59|66|61|716|
| Fixed signal zero |468|156|52|61|55|790|
| Fixed signal green10 |476|163|60|67|54|788|
| Fixed signal offset10 |472|156|62|65|54|797|
| β0 stopped1050 |52|41|5|6|4|83|
| β0 retry stopped1350 |79|51|8|11|7|126|

These are unique vehicle IDs observed on each link within each run. They are not summed across links or experiments, and are not exact passage totals: a vehicle can traverse a short connector between one-second samples. The first observed times in every run are108,19,415,417,651 and227 seconds respectively. In native NC, the maximum concurrent stocks are4,1,1,1,3 and9 vehicles. Complete record counts, lanes, sample IDs/positions, positive-frame totals, first/last times, paths and hashes are retained in `unresolved_positive_occurrence_audit.json` and the per-run `unresolved_occurrence_cache/*.json`.

The106 complete decision/audit snapshots available across the12 pinned run folders were also inspected. The28-link set is positive only in the failed retry's1350 snapshot (10634:3). All37 snapshots from pure n7 and all37 from the earlier audit-affected n7 are zero on this set. That sparse decision sample explains why prior snapshot-only projection tests did not expose these physically active short links. It does not establish that their future use is safe. The five completed FZPs represent different control experiments; their counts are presence evidence, not a causal performance comparison.

The other22 links have no positive record in this audit:141,187,189,197,209,224,240,242,247,249,251,360,459,10382,10391,10392,10393,10394,10397,10398,10404 and10407. Their physical ambiguity is preserved. Zero occupancy in these finite sampled runs is not proof that another seed or control sequence cannot use them.

Physical follow-up is recorded in `positive_unresolved_connector_review.json`:

| Link(s) | Physical evidence | Required treatment |
|---|---|---|
|10379|Source1220008203 has no input/head and receives only10367/10374/10378. All three reviewed active canonical turns receive into `SC11_to_SC1`. Native1104:1 selects10379 before it merges with the dummy-input branch.|A connector-only source-lineage contract can establish the existing transit receiver. Validate all upstream accepted receiver identities; do not replace the mixed downstream road.|
|10381|Source236 has no incoming connector and only nativeinput1091. Native1105:1 selects10381. It joins the same east approach to SC1.|`in_SC1_E` is an available matching approach origin, but the current gate map leaves1091's gate empty (`internal`) and the anchored forecast omits `in_SC1_E`. A new explicit source-to-origin contract is needed. Initial stock repair alone leaves native internal-demand forecasting unresolved.|
|10610/10611|Native1063:3 reaches1220000102 before decision1128. Its two future choices go through10500→62→10603→404 or bypass10501→52.|A finite shared prefix and future route choice are required. `SC107_to_SC1005` and `SC107_to_SC1004` have different predicted queues and cannot each represent the whole pre-choice road.|
|10627/10634|Both join56 before future decision1129.|The separate route-choice corridor implementation owns this finite shared prefix; no single destination alias was added to support data.|

Both1128 branches remain inside the current635-link Ω through404 or52. No exit should be counted at10603→404. The south source382 is outside and enters at10618, so accepted source-to-prefix transfer must retain that actual entry event. Native10610 uses source lane1, while its immediate road's SC107 heads are on lanes2/3. Native1128's10603 branch leaves62 before that road's SC1005 heads. Those local service facts must be kept separate from the initial-stock ownership proof and checked against full upstream authority before generalizing control treatment.

The native1128 weights are both blank and therefore use the native default. That conditional future choice is not an observed50/50 route posterior. Vehicles already past a decision cannot have their history redrawn from this prior. The reusable design is one candidate-private finite-corridor engine parameterized by corridor ID, physical partition, branch count, accepted service group, queue versus unsignalled transit stage, and destination. It must include the east and south entrants10619/10618 and retain exact Ω crossing edges. No additional adapter is needed.
