# RM10681 origin demand audit (partial origin coverage)

Unlike10639,10681 receives three approach cohorts:52,66 and46→68. Actual NC/RM XML routing subtrees are identical. Decision1135 splits3:1:1; route4 to10681 has probability1/5.

| Upstream decision | Path to68 | Parent turn | Conditional10681 probability |
|---|---|---:|---:|
|1123 on52|52→10629→68|10/12|1/6|
|1124 on66|66→10633→68|6/8|0.15|
|1125 on46|46→10625→68|6/8|0.15|

Only the isolated source66/input1100 contribution is fully resolved here. During900–1800,1800–2700,2700–3000s, source input is404.4,424.62,363.96veh/h and its10681 destination component is60.660,63.693,54.594veh/h. This gives**35.63775 expected source-generated target vehicles** during900–3000. It is**not total ramp desired demand**;52/46 bring other origins.

Both startup logs record six input1100 BEGIN/DONE writes with selected multiplier0.5. Each setting equals the selected demand table. Individual raw after-readback values are not printed for1100.

Upstream parent routes end68@4.9507/5.6762/6.3228m, before1135@7.4915m. Current recording XML retains this two-stage choice; the previous nine expanded routes were a design proposal, not an applied change. Source66 joins68 lane4 while10681 uses68 lanes1–2, so it has a lane-access issue distinct from configured quantity.

Full configured total would require resolving source/time/path cohorts into1123/1125, including upstream route eligibility and delays. Do not infer that total from139/137 observed whole-ramp crossings or the35.64 isolated-source expectation. Empty XML relFlow is interpreted as implicit1 per existing parser; no new COM readback was performed.

Evidence: ramp10681_origin_demand_partial.json. No FZP scan or source/config/process/run change.
