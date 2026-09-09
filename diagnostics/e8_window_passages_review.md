# Full 150-second passage windows around 10682

The full requested windows support the earlier spatial finding: the low average E9 density is compatible with a localized restriction immediately before the direct diverge. In the 1-second fixed-signal arms, lanes 2 and 3 have almost no measured passage just after that diverge during congestion, while lane 4 carries most through traffic. Offset10 changes branch arrivals and their timing, but these four windows do not show a general increase in direct-branch discharge or identify a capacity.

Data: `e8_window_passages_{NC,n7,zero,offset10}.json`, preserved byte-for-byte inside `e8_observation_evidence.zip`; compact `e8_window_passages_summary.csv`, `e8_window_passages_closure.csv`, and source manifest remain directly readable. The JSON retains every event's vehicle ID, old/new link and position, time bracket, interpolated time, lane endpoints and inference tag, plus stock membership changes and endpoint vehicle IDs. All files concern the old completed runs; the live beta0 run and production files were untouched. The adjacent bundle manifest pins all five member hashes and the archive hash. On a fresh checkout, extract with `python -m zipfile -e diagnostics/e8_observation_evidence.zip diagnostics` before the commands below. The archive reduces 12.3 MB of generated JSON to 0.68 MB without removing observations.

## Measurement contract

`probe_e8_window_passages.py` seeks directly to the two selected spans, including bracketing frames, and reads only those spans. Final extraction read 379,335,005 bytes: NC 33.54 MB, n7 32.82 MB, zero 157.12 MB, offset10 155.86 MB. Each run completed in less than 6 seconds; a 256 MiB and 45-second limit applies per run. The earlier snapshot reader's default 32 MiB budget remains unchanged. Six diagnostics tests validate binary lookup, crossing times and lane ambiguity, direct entry versus through passage, unique skipped-connector labeling, non-inference of unknown multi-link routes, and a removal warning coincident with the last recorded frame.

Mainline gates are at E8→E9 = 4621.726 m and one metre before/after the 10682 diverge = 4745.884/4747.884 m. Additional gates at 4609.819 and 4900.956 m bracket the two physical merges. Branch entry/exit is proved by consecutive observations on/off the named connector. If the exact source/target is observed, crossing time is linearly interpolated by distance along that known physical path. Interpolation assumes uniform progress only within the 1- or 5-second observation bracket; the full bracket is retained. No density×speed estimate is used for passage counts.

The nominal event windows are **(1050,1200], (1200,1350], (3150,3300], (3300,3450]**. Tables below assign by interpolated time. Lower/upper bracket counts are also exported. NC/n7's 5-second observations create boundary uncertainty; zero/offset's 1-second frames bracket the integer boundaries exactly. A connector skipped between samples would be tagged inferred only when its physical source-target pair is unique. There are **no inferred connectors, interval-only events or reverse crossings** in these extracted spans. This does not recover all unobserved routes outside the bounded spans.

Crossing lane is an endpoint proxy, not an exact subsecond observation. Both endpoint lanes are saved. Different endpoint lanes prove ambiguity; equal endpoints do not rule out an unobserved intermediate lane change. The 5-second NC/n7 data are especially unsuitable for treating the later lane at the narrow diverge section as the exact lane at crossing. The 1-second pair provides the clearer lane comparison.

## Observed passage counts

These are vehicle passage events per 150 seconds, not measured capacities and not requested meter rates. The connector columns count arrivals to 10682, exits from 10682, and actual exits from merge connectors 10639/10681 into the mainline.

|Run|Start|E8→E9|Before diverge|After diverge|10682 entry|10682 exit|10639 merge|10681 merge|
|---|---:|---:|---:|---:|---:|---:|---:|---:|
|NC|1050|187|183|147|36|39|8|9|
|NC|1200|187|187|153|34|32|9|16|
|NC|3150|110|109|81|28|31|8|12|
|NC|3300|101|110|79|31|32|13|9|
|n7|1050|185|188|149|40|42|8|13|
|n7|1200|191|184|145|39|47|9|12|
|n7|3150|122|119|86|33|33|7|13|
|n7|3300|111|106|75|31|32|9|14|
|zero|1050|177|180|144|36|39|8|13|
|zero|1200|185|185|142|43|42|9|14|
|zero|3150|98|101|68|33|32|12|13|
|zero|3300|120|121|89|32|32|15|6|
|offset10|1050|190|192|146|46|45|8|13|
|offset10|1200|189|181|147|34|34|9|14|
|offset10|3150|120|113|83|30|31|7|11|
|offset10|3300|106|108|76|32|31|9|8|

The earlier cached passage tables assign events to the later observation's half-open bin. Those values can differ by one or two events at boundaries, e.g. n7 direct departures during 3150–3450 were 64 by that definition and are 65 by the present interpolation convention. These are different, explicitly retained time-assignment rules, not a revised claim of one exact physical boundary time from 5-second data.

During 3150–3450, NC and n7 each have approximately the same through discharge after the diverge (160 and 161 events). The fixed zero and offset10 arms have 157 and 159. Direct exits are 63, 65, 64 and 62 respectively. Thus lower stock or better network metrics do not establish a larger discharge capacity at this node.

The paired offset arms both command their meters fully open. Nevertheless, 10639 merge receipts change from 27 to 16 over the congested 300 seconds, while 10681 receipts remain 19 in total. Upstream signal offsets can alter realized merge receipts through arrivals and timing even with identical meter commands. Conversely, the first two onset windows have identical 10639 receipts (8 then 9) and identical 10681 receipts (13 then 14) in the paired arms. The dynamic n7 comparison changes multiple levers; it cannot isolate a meter treatment effect from these data alone.

## Lane restriction at the actual diverge

For the 1-second pair, later-endpoint lane counts just after 4747.884 m during 3150–3450 are:

|Arm|Lane 1|Lane 2|Lane 3|Lane 4|Total|Endpoint-lane disagreements|
|---|---:|---:|---:|---:|---:|---:|
|zero|28|1|1|127|157|1|
|offset10|16|1|0|142|159|0|

Lane 4 accounts for 80.9% and 89.3% of through passages. In contrast, the E8→E9 crossing counts in lanes 2 and 3 over the same windows are zero 24/10 and offset10 18/16, with no differing endpoint lanes at that boundary. Vehicles entering the upstream part of E9 on these lanes are not simply continuing through the diverge section in the same lane. The earlier t3301 snapshot places their stopped queues immediately before the diverge. This combination supports a localized lane-change/diverge restriction rather than a uniformly usable low-density E9. It does not identify each queued vehicle's desired route; only observed connector transitions and matched warning routes supply route evidence.

## Flow and stock closure; explicit removal

We independently count gates/branch transfers and compare with physical ID inventories in three control volumes: mainline 4609.819–4900.956 m; mainline 4621.726–4747.884 m; and connector 10682 itself. Exact stock closure uses **recorded endpoints**, 1051→1201 etc. for NC/n7, and 1050→1200 etc. for the 1-second pair. This preserves an exact 150-second duration without pretending an unrecorded NC t1050 inventory was measured.

All 48 sampled membership identities close. Gate/branch flux also closes independently for every row except the two overlapping volumes containing one removed vehicle. Offset vehicle **14249** is last recorded at t3237 on link 2, lane 3, local position 1999.86 m (chain 4734.387 m), speed 0; it is absent at t3238. The warning at t3237 identifies the same vehicle on direct route 1130-3 removed after 60 seconds waiting for a lane change. A warning coincident with the last recorded second is therefore matched to the inclusive [3237,3238] disappearance bracket. It is one vehicle, not two losses merely because two volumes include it.

For offset10's 4621.726–4747.884 m volume during 3150–3300, gate/branch net inflow is +7, stock rises 47→53 (+6), and this verified removal supplies the remaining −1. After explicitly accounting for that removal, **48/48 physical flux closures have zero residual**. No unverified interior disappearance or newly appeared ID remains in these selected volumes/windows. The NC warning cache is unavailable, but no disappearance in these volumes requires warning-based resolution.

This is an observational conservation result, not validation of a particular traffic model. The dataset now supplies complete-window branch receipts and through discharge with censoring preserved. It supports the proposed branch-specific state and physical-order interface; it still does not justify an arbitrary lane-loss factor, discharge cap, two-branch fit, or forced VSL reward. Identifying a discharge law requires route-resolved queued exposure and downstream conditions over additional windows/seeds, rather than treating these one-seed counts as a parameter.

Reproduce with `python -m unittest diagnostics.test_indexed_fzp diagnostics.test_e8_window_passages -v`, then `python diagnostics/probe_e8_window_passages.py NC n7 zero offset10` and `python diagnostics/summarize_e8_window_passages.py`. The second command reads bounded slices of completed recordings; the last command only reads the generated evidence JSON.
