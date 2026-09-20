# Input1101 demand reduction — completed short native comparison

2026-09-20. User requested testing the urban upstream vehicle input. Turn removal is deferred: no connector or route was removed. The original network is preserved. These are demand sensitivity tests, not controller performance or plant calibration qualification.

## Conditions and execution

- Reference: `../native_v1/none_s23/run`, completed native no-control 3000s recording, reused.
- New runs: `p90/run` and `p80/run`, both completed to3000s at seed23; native LDP/readback verification passed. Wall time including loading/verification:180.60s and172.31s.
- Only the six saved volume entries of input1101 on link69 were scaled by0.9/0.8. Full XML comparison after restoring those six values matched the reference. Geometry, routes, signal programs, VSL/DSD, native meters, seed and1s recording are unchanged.
- Existing `diagnostics/fast_nc_run.ps1` executed both runs sequentially, with the owned-process300s no-progress watchdog. No controller/model was invoked; no live vehicle scans or concurrent large analysis. Both VISSIM processes exited normally.
- `preparation.json` pins the source and scenarios. `configured_demand.csv` contains all six intervals and conditional destination demands. This source reduction intentionally reduces all destinations from input1101. It is not a destination-preserving reduction of71 alone.

At the1800–2700s peak, configured demand in veh/h:

| Input1101 factor | Total | FW_W | FW_E | Through75 | Direct via71, all turns |
|---|---:|---:|---:|---:|---:|
|100%|2100|630|630|630|210|
|90%|1890|567|567|567|189|
|80%|1680|504|504|504|168|

These are configured conditional demands through1134→1138; actual counts are stochastic and include other origins/recirculation.

## Same1800–2850s observation window

Stopped means speed below5km/h. Mean stock includes moving and stopped vehicles. Losses are ERR events confirmed against the following network-wide FZP frame; losses are not discharge or TTD.

| Measure |100%|90%|80%|
|---|---:|---:|---:|
|71 arrivals during window|521|492|497|
|71 normal departures|497|482|489|
|71 abnormal losses|15|12|12|
|71 mean stock [veh]|27.03|24.24|25.41|
|71 mean stopped vehicles|22.15|19.82|20.82|
|71 loss / initial stock plus arrivals|2.80%|2.36%|2.33%|
|10643 arrivals|243|251|246|
|10643 normal departures|243|213|229|
|10643 stock, start→end|56→56|10→48|41→58|
|10643 mean stock [veh]|53.04|37.12|52.17|
|10643 mean stopped vehicles|40.18|28.74|40.46|
|10643 abnormal losses|0|0|0|

71 waiting decreases modestly in both reduced cases.10643 does not improve monotonically. The lower90% mean also reflects its much lower stock at1800s; it subsequently builds a queue. This is not evidence that90% increases off-ramp capacity.

Over2400–3000s,10643 mean stock is52.13/49.95/58.67 and normal departures144/142/132. At3000s its stock remains47/45/48. Thus no scenario demonstrates full clearance by3000s.

## Which origin actually supplies71?

Native vehicle IDs were traced from their first recorded network link. All identified first links for the local sample map to saved vehicle inputs. Counts below include vehicles already on71 at1800s and arrivals through2850s; a return is another visit.

| Origin |100%|90%|80%|
|---|---:|---:|---:|
|Input1101, link69|67|62|59|
|Input1098, link74|255|234|241|
|All origins,71 visits|536|508|514|

Input1101 accounts for only67/536=12.5% of baseline71 visits. Input1098 accounts for47.6%; the10643 sample is entirely from that origin. Other significant baseline sources are input1099/link26 (61), input1102/link32 (57), and input1100/link66 (31). The original route table alone was not a complete origin attribution.

Reducing1101 by20% therefore is not a20% reduction in total demand reaching71. It also reduces on-ramp demand, which changes the freeway interaction. This experiment cannot isolate the contribution of71 approach demand from those changes, and it does not establish that excess demand is the sole cause of the bottleneck.

## Verification and limits

- Existing extractor checked local stock-flow conservation every second andSC1004 SG2/5 against native LDP for all three recordings,1800–3000s.
- `analysis/summary.json`, per-case CSV/evidence and `analysis/observed_origins.json` retain results and origin counts.
- Whole-run raw ERR and parsed records are retained. Lane-change removals remain elsewhere in the network as well. All three cases have a VISSIG DLL notice; the relevantSC1004 native signal sequences still match the saved program. Do not label these runs error-free.
- End-of-run ERR contains unfinished input counts, with none reported for1101. Runs stop at3000s while saved SimPeriod is9001s; the reported remainder has not been separated into due-but-blocked versus remaining scheduled demand. It is not treated as a proven insertion-failure count or a cleared network.
- One seed and a3000s horizon: no independent-seed robustness or cooldown claim. The same seed does not preserve identical vehicles/arrival sequences after changing input demand.
- No full-network/Ω TTT benefit is claimed from these lower-demand cases. No model/core parameters or default scenario have been promoted.

Recommendation: preserve turn movements. Input1101 reduction provides some local relief but is not a demonstrated cure for10643. Before reducing this source more aggressively, distinguish the freeway-origin71-bound demand and its urban receiving service. A repeated seed can then determine whether the90% improvement is robust; new runs beyond the two authorized short conditions have not been started.

Reproduction: `../input1101_sweep.py prepare` creates new prepared scenarios (requires a fresh output directory), existing native runner with `-Seed23 -Execute` runs each case; `analyze` and `origins` perform offline extraction. Outputs are never silently overwritten by preparation or main analysis.
