# E8/E9: observed receiving space and a localized diverge constraint

E9's low average density is present in the physical observations. It is not merely lost stock in the model projection. That average combines a queue on lanes 1–3 immediately before the 10682 diverge with largely empty space after the diverge and a fast lane 4. Treating all this space as uniformly accessible receiving space omits a material spatial and lane restriction. The evidence supports a localized route/lane bottleneck; it does not identify a numerical capacity or establish that connector spillback alone caused the initial breakdown.

`e8_lane_receiving_evidence.json` contains the observations, source hashes, definitions, vehicle IDs for sparse boundary crossings, physical network endpoints and route references. Its exact bytes are shipped in `e8_observation_evidence.zip` with a hashed member manifest; extract with `python -m zipfile -e diagnostics/e8_observation_evidence.zip diagnostics`. `probe_e8_lane_receiving.py` reads existing lane/connector caches and binary-seeks 14 timestamp blocks per run. It read 14,753,244 FZP bytes across four runs, without a full trajectory scan, parameter fit, or production change. `test_indexed_fzp.py` verifies complete timestamp blocks before/after binary search; one test passes. The earlier `freeway_speed_terms_*` files remain historical traces from before the later meter-finalization integration and were not overwritten.

## Definitions and comparison limits

All positions below are FW_E chain distance. E8 is [4108.201, 4621.726) m; E9 is [4621.726, 5135.252) m. Four lanes are observed. COM segment counts are instantaneous and report stopped vehicles below 1 km/h. Our per-lane FZP snapshots separately count speeds below 1 and below 5 km/h. Cached lane data use 100 m × 30 s bins, vehicle-sample-weighted speed, and stopped fraction below 5 km/h. The bin density is samples / (30 / recording cadence) / 0.1 km per lane. These are distinct statistics, not interchangeable timestamps or thresholds.

NC and pure n7 record every 5 s at 1+5k; the frozen-signal zero and relative-offset10 arms record every 1 s. Exact lane snapshots use identical endpoints in all four runs. NC/n7 differ in their full policy; they are not a one-lever experiment. The zero/offset10 pair shares fixed greens and differs in relative offsets. Its frozen green vector came from the first, audit-affected n7 t2100 action, not from native signals or the pure n7 run. All evidence here is seed 13.

## Same-time physical stock

At COM t3300, E9 remains lightly occupied in every arm while E8 is heavily occupied:

|Run|E8 vehicles|E8 density|E8 speed|E9 vehicles|E9 density|E9 speed|
|---|---:|---:|---:|---:|---:|---:|
|NC|217|105.642|6.012|64|31.157|22.906|
|pure n7|213|103.695|4.925|62|30.184|19.596|
|fixed zero|242|117.813|5.134|64|31.157|25.901|
|relative offset10|196|95.419|7.024|61|29.697|18.412|

Density units are veh/km/lane; speed is km/h. The per-cell length rounding/scalar-model discrepancy is separate and much smaller than this E8/E9 difference. The integrated historical t3300 trace used E8/E9 densities 103.717/30.188 and produced an anticipation increment of +16.608 km/h in 10 s. The large physical gradient is real, but the same trace's predicted rapid recovery is not supported by the observed E8 speed.

At the identical FZP t3301 snapshot, pure n7 shows why the average misleads:

|Cell/lane|Vehicles|Density|Mean speed|Vehicles below 5 km/h|
|---|---:|---:|---:|---:|
|E8 / 1|73|142.155|1.428|67|
|E8 / 2|60|116.839|4.090|42|
|E8 / 3|63|122.682|3.588|52|
|E8 / 4|18|35.052|35.442|5|
|E9 / 1|16|31.157|7.934|9|
|E9 / 2|19|36.999|3.281|17|
|E9 / 3|16|31.157|7.990|12|
|E9 / 4|10|19.473|82.713|0|

The E9 stopped vehicles occupy only its upstream portion. In n7, the downstreammost stopped positions in lanes 1–3 are 4734.167, 4741.767 and 4734.507 m. The 10682 diverge starts at 4746.884 m: the lane-2 queue head is only 5.117 m upstream. No E9 lane-4 vehicle is below 5 km/h. NC, zero and offset10 show the same queue-head location, with no stopped E9 lane-4 vehicle. Thus both longitudinal averaging (roughly 120 m of queued road mixed with the remaining E9 length) and lane averaging conceal the restriction.

The independent 30 s bins support the snapshot. At n7 t3300, lane 2 has density/speed 151.7/1.4 in the 4600 m bin and 58.3/3.0 at 4700 m, then 1.7/44.3 at 4800 m and 3.3/75.4 at 4900 m. Lane 4 runs about 83–85 km/h through the 4600–4900 m bins. NC shows the same abrupt spatial transition. Low downstream stock therefore does not imply a uniform, unconstrained discharge path for all upstream routes.

## Onset and observed passages

The requested onset window is already left-censored: n7 lane 1 in the 4500 m bin has mean speed 10.4 km/h and stopped fraction 0.46 at t1050. Lanes 2–3 are then mostly fast. Lane 2 near 4600–4700 m slows markedly by t1140, and lane 3 slows later. These observations distinguish early lane-specific queues from the later cell-average congestion event; t1050 is not claimed as first onset. At t1201, E8 lane 1 still has 41 vehicles, speed 15.97 and 23 below 5 km/h, while E9 has no stopped vehicle in any lane. The instantaneous downstream clearance and persistent upstream queue can coexist; cyclic behavior also makes a 30 s bin differ from this snapshot.

Cached connector departures count an ID observed on the connector followed by an observation on a different link. The event is assigned to the later observation's 150 s bin, so exact bin-edge timing is uncertain by the recording cadence. A separately inferred source-to-target jump can fill a skipped connector; all 80 selected connector/block rows have zero inferred departures. Interior disappearance is excluded. The cache's generic limitation text still says 5 s for all runs; its measured `observation_step_sec` correctly reports 1 s for zero/offset10 and is the cadence used here. Values below are **observed departures**, not saturated capacities or requested meter rates:

|Run|10639 merges, 1050–1200 / 1200–1350 / 1350–1500|10639 merges, 3150–3450|10682 departures, 3150–3450|
|---|---|---:|---:|
|NC|8 / 9 / 13|21|63|
|pure n7|8 / 9 / 13|16|64|
|fixed zero|8 / 9 / 13|27|64|
|relative offset10|8 / 9 / 13|16|62|

Equal early 10639 totals do not exclude different arrival gaps, lane changes or downstream signal timing, but they do rule out explaining the early differences solely by these block merge totals. In congestion, direct-branch departures are similar despite different E8 stocks. Offset10's lower E8 stock is not evidence of a uniform increase in direct-connector capacity: it also changes urban arrivals and ramp timing. For example, zero has more 10639 departures and substantially more queued vehicles there than offset10.

We additionally match the same vehicle on the mainline before/after the E8→E9 boundary over seven common 5 s intervals. For intervals ending at 1081, 1201, 1351, 1471, 3181, 3301 and 3421, lower-bound crossing counts are NC [4,7,3,5,5,4,5], n7 [5,4,4,6,4,5,4], zero [4,4,5,4,3,5,3], offset10 [4,7,7,5,2,4,2]. A vehicle on a connector at either endpoint is not inferred as a crossing. These sparse samples show ongoing boundary passage; they are too sparse to estimate a 150 s flow or capacity.

## Route evidence and physical order

The network places signal branch 10643 at 4386.333 m, merge 10639 at 4610.819 m, direct branch 10682 at 4746.884 m and merge 10681 at 4899.956 m. The first merge-to-direct-diverge separation is 136.066 m. Existing grouped placement sends both R_F_E merges to cell 9 and both OR_F_E branches to cell 8, reversing part of this physical order. Moving the whole group one cell would break the correctly placed other branch; see `direct_branch_order_audit.json` and its design handoff.

Network route 1130-3 explicitly traverses 10682→121→10773. The cached warnings identify vehicles on this route removed after 60 s of waiting for lane change at link-2 positions immediately before the diverge. Pure n7 has 17 such direct-route removals over the full run (plus 5 on the earlier signal branch); none occurs inside the two requested windows. Offset10 has one at t3237, local position 1999.9 m, chain 4734.427 m, and another later. This is direct evidence of required lane-change failure near the queue head, not merely an inferred spillback mechanism. The NC warning cache is absent, so its count is unknown, not zero. Removal events are losses, not successful traffic discharge.

Connector 10682's own observed stopped tail was still 93.941 m from its entry at n7 t1200 and 21.968 m at t3300 (`direct_branch_order_audit.json`). Those snapshots do not establish a queue reaching its entrance. Its 226.52 m × one-lane geometry is not an identified capacity, and the downstream aggregate containing link 121 is not a substitute for connector-specific stock.

## Smallest identifiable next change

The next model change should preserve physical branch order and restricted access at the diverge while retaining the four control groups. First expose branch-specific queue, route share and accepted receipts: 10639 and 10681 enter at different cells; 10643 and 10682 exit at different nodes. These must remain separately conserved through local prediction and global coupling. Then introduce a localized pre-diverge queue/receiving interface that distinguishes route/lane-constrained traffic from the open through path. Splitting at a surveyed node is physically grounded, but a finer grid alone does not identify the discharge constraint or cure the positive-gradient acceleration.

Before assigning a node discharge rule, collect complete queued-interval boundary passages and route/lane cohorts, including arrival gaps, accepted merges and direct/through exits, and distinguish periods with available downstream connector space. Validate stock/flow closure and held-out NC/n7/zero/offset intervals and seeds. The present sparse observations cannot justify a new numerical capacity, arbitrary lane-loss ratio, two-branch FD fit, or VSL reward. Accounting and signal/meter score-to-actuation repairs address separate proven inconsistencies; they do not by themselves supply this missing local physical state.
