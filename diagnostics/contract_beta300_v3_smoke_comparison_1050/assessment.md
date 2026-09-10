# Corrected beta300: first live interval passes, with mixed spatial effects

The corrected controller ran VISSIM to 1050 seconds and completed both live decisions at 900 and 1050. The first command matches the offline full-MPC command CSV byte for byte. Actual signal application, persistence and the first controlled head-observation window pass. This establishes the live connection. It does not establish a successful congestion-control policy.

The reference is the completed **1050-second** native NC v2 run with the same network and seed13. The two OFF observation/mode controls reproduce its entire 1,992,241-row trajectory. The older 5400-second NC prefix has a small late difference and is not substituted for this matched-length comparison.

| Actual physical metric, 900–1050s | NC | Corrected beta300 | Difference |
|---|---:|---:|---:|
| Ω TTT [veh h] | 80.158611 | 79.808750 | −0.349861 (−0.44%) |
| TTD: observed outward crossings [veh] | 481 | 503 | +22 |
| TTD: terminal-inferred exits [veh] | 227 | 227 | 0 |
| TTD: observed + terminal [veh] | 708 | 730 | +22 |
| Observed boundary-entry events | 319 | 295 | −24 |
| Vehicles appearing inside Ω | 697 | 697 | 0 |
| Unresolved inside disappearances | 10 | 9 | −1 |
| Final Ω stock [veh] | 2063 | 2018 | −45 |

Both sampled stock ledgers close exactly. The stock difference is consistent with 24 fewer observed entries, 22 additional exits and one fewer unresolved disappearance. Lower residence therefore cannot be attributed only to faster evacuation. These are sampled crossing events; they are not a unique admitted-demand total. Interior disappearances receive no TTD reward.

Across the full 0–1050 run, Ω TTT is375.806250→375.456389 veh h and total TTD is3399→3421. Full-run unique counted IDs are3359→3382, with repeat exit events40→39. One-second FZP observation is complete in both runs with no missing frame gap.

## Queue movement and local discharge

The six-panel `queue_comparison.png` shows individual 30-second stopped-stock samples; reference means NC and target means beta300. No smoothing is applied. The road metrics below integrate the same sampled stopped counts, not continuous queue length.

| Physical road | Stopped residence NC→control [veh h] | What the samples show |
|---|---:|---|
| 127 | 3.087500→1.687500 | Early queue reduction, followed by accumulation again near the interval end. |
| 71 | 0.712500→0.462500 | Smaller integrated queue, but the final stopped stock is15 versus5 in NC. |
| 420 | 0.008333→0.066667 | Final stopped stock rises to16 versus0 in NC. |
| 10682 | 0.070833→0.133333 | More stopped residence despite lower total arrivals and exits. |
| 10639 | 0→0 | No stopped vehicles in these samples; passage counts are unchanged. |
| 40 | 0.104167→0.104167 | Same integrated stopped stock with a different timing pattern. |

All six listed roads are inside Ω. Over900–1050, physical10682 entries are55→45 and exits43→37;10639 entries4→4 and exits6→6. These direct connector observations remain separate from Ω boundary exits. Empty connector-passage summaries in the generic report are not zeros: that older summary excludes the final150-second bin. The bounded `focus_900_1050.json` records the actual counts for this interval.

At127, SC1001/SG2 GREEN exposure increases from45 to66 seconds and GREEN-qualified crossings across lanes1–2 increase45→62. At71, SC1004/SG2 receives45→71 GREEN seconds, yet qualified crossings across lanes1–3 fall22→17. More GREEN alone therefore does not explain the smaller integrated71 queue. Upstream arrivals, route choice, receiving space and the timing of the GREEN windows need to be inspected together. These qualified online stopline counts exclude unresolved transitions and are not a complete connector-throughput census.

E8 minimum nonempty sampled speed falls93.144→64.285km/h; E9 falls63.130→57.937km/h. E8 peak stock remains25 vehicles; E9 peak stock rises36→38. Neither has a sustained below30km/h episode in this short interval. The heatmap shows the early speed change, not validation of congestion onset or its long upstream propagation. Longer simulation is necessary for that judgment.

VSL stays120km/h and all four meter rates stay1800veh/h at the first action, matching the physical NC speed/all-green meter commands. The implemented changes in this first interval are urban GREEN and offset commands. Their joint effect is observed; this run does not isolate green from offset or establish a VSL benefit.

## Validation and limits

- Run `codex_contract_beta300_s13_1050_v3_20260910` finished normally in801s, with1050 simulation steps. Observation, signal, action-format and COM failure counters are all zero. The separate startup300s limit did not fire.
- `beta300_preflight_live900_comparison.json` records exact offline/live command CSV and all four action vectors, physical state, head counts and carried floors. Run/configuration provenance remains distinct.
- `beta300_controlled_head_window900_1050.json` verifies the actual first controlled window:107 SGs, 32,100 immediate/post-step rows, exact GREEN exposure and no cadence/readback mismatch. Eighteen native heads have independent LSA coverage; SC5/SG18 has no native LSA change row and is compared only with its pinned zero-GREEN program.
- Native runtime capture contains9 lane-change removals (4 inside/5 outside), compared with10 (5/5) in the matched NC. Native error records and unresolved FZP disappearances are separate definitions; this report does not subtract one census from the other or reward removals.
- Same displayed timestamp does not make paused COM and FZP inventories identical. At900, two terminal vehicles are retained in the FZP end frame after disappearing from COM. The root/peer terminal audit records this timing boundary. It does not change the observed-versus-inferred exit definitions or the exact offline/live raw-state match.

The main remaining diagnoses are physical head-service ownership and preservation of already-selected downstream exit routes. Their proposed corrections are separate from this completed v3 run. A long-horizon improvement or a final reward coefficient has not yet been selected.
