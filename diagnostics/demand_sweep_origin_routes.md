# E8 direct offramp: preserve other configured demand while reducing 1130:3 by 20%

The first candidate changes only the desired demand of **input1098 → decision1130 route3 → 10682 → 121 → 10773 → 123**. Set input1098's total demand to **16/17 of its current profiled value** and change only route1130:3's relative-flow weight from **4 to 3.2**. Keep sibling weights **1.6 and 8**. This preserves the two non-target source-route expected demand rates exactly and reduces the target rate by 20% in every source-generation time window.

Prepared files are `demand_sweep_origin_routes.input_override.csv` (six absolute vph rows for the model-free fast NC driver), `demand_sweep_origin_routes.route_override.json` (one-attribute network preparation specification), `demand_sweep_origin_routes.csv` (before/after table with exact rational values), and `demand_sweep_origin_routes.json` (source proof, all 204 input interval values and checks). `demand_sweep_origin_routes.py` uses only the standard library. No network was generated, no existing input was changed, and no COM, model, traffic simulation or FZP scan was performed.

## Why this source has an isolated first decision

The pinned flat baseline network SHA is `085a10c71874e897083c97097af8fa3f1f08da1ef7416fef2f7cfbedabdfc317`.

| Item | Actual baseline XML |
|---|---|
| Source | VehicleInput1098 is the only input on link74. There are no incoming connectors to74. |
| First choice | Decision1130 is the only static decision on74, at35.477974611945m. |
| First physical branch/continuation | The only outgoing connector is10699, leaving74 at2694.978300566156m, well after the decision. No earlier alternative origin or connector branch was found. |
| Eligibility | `allVehTypes=true`, `routeChoiceMeth=STATIC`, `combineStaRoutDec=true`. All three route formulas are empty. No PT lines or parking lots are present in this network. |
| Composition | Input1098 uses composition1 in all six intervals: type100 share.806, type150 share.1, type200 share.094. These proportions and speed distributions remain unchanged. |
| Relative-flow time domain | All three weights use the single static-routing interval `2 0`, beginning at0. No time-varying routing factor is introduced. |

The original source routing is:

| Route | Weight / probability | Ordered physical route | Exact route endpoint |
|---|---:|---|---|
| 1130:1 | 1.6 / 2/17 | 74→10699→2→10643 | 10643@15.593970864061m |
| 1130:2 | 8 / 10/17 | 74→10699→2 | 2@2268.325676212646m |
| **1130:3** | **4 / 5/17** | **74→10699→2→10682→121→10773→123** | **123@295.923507352863m** |

Keep every route ID, path, endpoint, vehicle composition, class eligibility, Combine/LookAhead setting, signal program and geometry unchanged. The route override specifies exactly `relFlow="2 0:4"` → `relFlow="2 0:3.2"` within1130:3; it is not an instruction to multiply every occurrence of weight4 elsewhere. Prepared network validation must preserve all other XML bytes.

## Input and branch arithmetic

For source input Q, target weight w, sibling sum b and desired target multiplier α:

`Q' = Q (b + αw)/(b+w)`, `w' = αw`; all sibling weights stay unchanged.

Then `Q' w'/(b+αw) = α Qw/(b+w)` and each sibling j has `Q' w_j/(b+αw) = Qw_j/(b+w)`. Here b=9.6, w=4, α=.8, so Q'/Q=12.8/13.6=16/17. New probabilities are signal .125, through .625, direct .25. They are conditional probabilities at the source's first eligible decision, not spatial off-ramp split ratios.

The actual demand profile is `evaluation/configs/demand_profiles/ver2_fdsweep_x15_20260907.csv`, with DemandScale1 and the input1098 role `freeway_feeder_input_candidate` multiplier **.8333**, not exact5/6. Volumes come from the current INPX, not the stale informational volume columns in `vehicle_input_roles.csv`. The native runner applies role or `no:<input>` overrides to every input interval at VBS4232–4259.

All figures below are **desired source-cohort veh/h**. They are not the target ramp's arrival rate during the same clock interval and not accepted service. Congestion, finite input admission and travel time can delay or prevent arrival.

| Generation window s | Q before | Q after | Signal1130:1, unchanged | Through1130:2, unchanged | Direct1130:3 before | Direct after |
|---|---:|---:|---:|---:|---:|---:|
| 0–900 | 4619.815200 | 4348.061365 | 543.507671 | 2717.538353 | 1358.769176 | 1087.015341 |
| 900–1800 | 6599.736000 | 6211.516235 | 776.439529 | 3882.197647 | 1941.098824 | 1552.879059 |
| 1800–2700 | 6929.722800 | 6522.092047 | 815.261506 | 4076.307529 | 2038.153765 | 1630.523012 |
| 2700–3600 | 5939.762400 | 5590.364612 | 698.795576 | 3493.977882 | 1746.988941 | 1397.591153 |
| 3600–4500 | 4619.815200 | 4348.061365 | 543.507671 | 2717.538353 | 1358.769176 | 1087.015341 |
| 4500–5400 | 3299.868000 | 3105.758118 | 388.219765 | 1941.098824 | 970.549412 | 776.439529 |

The CSV contains the **final absolute** Q-after values. Do not multiply them by .8333 again. The remaining198 rows (33 inputs×6 intervals) are unchanged. Exact Fraction arithmetic verifies sibling preservation and target×.8 before decimal serialization; the CSV retains17 significant digits. Native readback must verify the actual loaded six values and all198 unchanged targets with explicit numeric tolerance before simulation.

Changing only route3's weight would redistribute its removed share into signal/through demand; changing only input1098 would also reduce both siblings. Both operations are necessary. The input reduction intentionally begins at0, including warmup. This is a paired desired-demand intervention, not removal of particular observed queued vehicles.

## Other ramps and the excluded 66 proposal

The initially broader request exposed the following distinct trees. They are not combined with this first candidate.

| Physical target | Native demand lineage / limit |
|---|---|
| 10639 | Input1101 is the isolated source on69. Decision1134 at48.857m has weights12:1:3:.25; route3 has conditional probability12/65 and explicit69→10637→70→10639→2 path ending2@2306.235m. Its own source-demand-only thinning can use the same formula in a separate experiment. Link70 also receives10638 traffic, but1133:2 explicitly routes that cohort onward70→10776→126 rather than automatically making it10639 demand. Do not use total70 stock as10639 desired demand. |
| 10681 | Decision1135 on68 has weights3:1:1 to10646/123/10681. Its three incoming prefixes are52→10629→68,66→10633→68 and46→10625→68. Their local parent probabilities for the68 branch are10/12,6/8 and6/8, respectively; conditional products for10681 are1/6,.15,.15 **of eligible traffic at those parent decisions**, not known absolute input rates. |
| 46 and52 upstream | Neither is an isolated source input. 46 receives39→10495 and425→10497;52 receives58→10498 and1220000102→10501. A shared1135 weight reduction needs coordinated upstream source/branch changes or explicit origin/path-conditioned selection to preserve all non-target desired OD. No complete34-input multi-decision mapping is certified here; this work is deferred rather than filled with observed counts or equal splits. |
| **Excluded: input1100 /66→68** | Source66 has isolated input1100 and1124 weights6:1:1, but its68 branch subsequently includes10646,123 and10681 destinations. Reducing the entire1124:1 turn would also reduce non-target city/other-destination traffic. It violates the selected ramp-only experiment scope and is explicitly excluded. |

Similarly,123 receives traffic from both the targeted1130:3 direct exit and1135:3 via10773, plus10645 joining farther downstream. The proposed edit does not change those other source decisions. A count on123 is not an isolated target-demand measurement.

## Execution and inference boundaries

Use the existing model-free fast NC driver with the prepared INPX and paired absolute input CSV. The current model `native_demand_forecast._totals` requires two symmetric freeway source rates; reducing only1098 breaks that model prerequisite. Do not remove fields or bypass that guard to call this an otherwise identical model run.

Keep native signals, LCD/geometry, seed, vehicle types, simulation duration and physical controls fixed. Before starting, verify the prepared network changed only the target relative-flow attribute, all204 native input readbacks match, and routing weights/eligibility/path endpoints match the specification. This producer provides no runtime approval or COM validation result.

Configured expected non-target source-route demand is conserved; realized non-target flows, queue admission and completion are free to change as congestion changes. Input volumes are STOCHASTIC. Q and branch probability changes alter random draw timing/counts, so same seed does not imply identical realized OD IDs or counts. Compare source generated/admitted vehicles, route selections, target arrivals, accepted discharges, remaining stock and deletion separately. Recovery of E8/66 or network throughput must come from the subsequent run; it is not implied by the algebra or by prior observed passage counts. No capacity or recovery threshold is calibrated here.

## Separate bounded follow-up: only the two on-ramp destinations from66

**10646 enters FW_W, not FW_E.** Its actual connector leaves121lane1@233.019984m and joins120lane1@2252.998293m. The current control mapping places120 in `[26,10771,120]` (FW_W), and10646 in R_F_W. By contrast10681 joins2lane1@2165.428753m, in FW_E/R_F_E. These labels do not change the native network.

For the isolated input1100/source66, original1124:1 has probability6/8 and shared1135 splits3:1:1. Thus the source-cohort desired probabilities are10646=.45,10681=.15,city123=.15,1124:2→47=.125 and1124:3→56=.125. Reducing **both on-ramp destinations** by α while retaining city123/47/56 is structurally possible with a narrowly expanded1124 plus its paired input adjustment:

| New1124 branch (proposed unused ID) | Complete path | New weight | Destination position m |
|---|---|---:|---:|
| 4, inherited1135:2 | 66→10633→68→10772→121→10646→120 | 3.6α | 120@2272.297795512164 |
| 5, inherited1135:3 | 66→10633→68→10772→121→10773→123 | **1.2 unchanged** | 123@179.069732129097 |
| 6, inherited1135:4 | 66→10633→68→10681→2 | 1.2α | 2@2289.198499870484 |

Replace original1124:1 by these three complete routes, retain1124:2 and:3 at weight1 each, and set input1100 `Q'=Q(.4+.6α)`. The five resulting weights total3.2+4.8α instead of8. At α=.8, Q'=0.88Q; for the900–1800 source period Q808.8→711.744vph,10646 desired363.96→291.168,10681 desired121.32→97.056, while city123121.32 and47/56101.1 each remain unchanged. Weight changes without the Q adjustment cannot remove demand while preserving siblings.

**Keep1123,1125 and1135 unchanged.** Other-origin46/52 vehicles still use1135. The expanded66 vehicles carry a complete selected route beyond68@7.491513, so the ordinary static-routing rule does not select a new route at that intermediate point before the current destination. This is supported by the [PTV2020 routing applicability rule](https://cgi.ptvgroup.com/vision-help/VISSIM_2020_ENG/Content/5_Netzbearbeiten/Fzgverkehr_Routen_RoutenEntsch_mod.htm). Existing Combine=true and LookAhead=true must remain; Combine joins subsequent routes for anticipatory lane choice and does not establish that an intermediate decision overwrites an already complete route. See [PTV2020 Combine description](https://cgi.ptvgroup.com/vision-help/VISSIM_2020_ENG/Content/5_Netzbearbeiten/Fzgverkehr_Routen_statische_RoutenEntsch_Attr.htm).

This is an unapplied structural proposal, not native execution validation. It must verify actual1124 child selection and continued destination through1135 without reassignment; conserve47/56/123 expected source demand; and retain66→10633's mandatory lane4 entry to68lane4. Because expansion changes route-information timing and RNG consumption, an expanded **α=1 control arm** is needed to distinguish demand reduction from routing-structure effects. Existing Combine may already supply advance information, so an improvement from expansion is not assumed. This follow-up does not change or delay the first1130:3 candidate and does not authorize reducing the whole66→68 turn.
