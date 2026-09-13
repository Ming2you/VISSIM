# Physical actuator ownership, current all-lever configuration

The physical write addresses have **19 owners: 17 urban signal controllers and FW_E/FW_W**. There is no duplicate DSD owner, urban/ramp SC overlap, urban/ramp head overlap, or cross-owner link/lane overlap among the controlled heads. The actual v3 CSV and the current v4 profile CSV both use the same 66 VSL action keys as the mapping and generated VBS contract.

This does **not** certify a simultaneous full-green/offset/VSL/meter GNE. Physical ownership and the optimizer's update order are separate. Current `phase_price.in_gne` is absent; the recorded v4 action reports `phase_vector_green_enabled=0`. The stage and price analysis is in `follower_game_structure_review.md`.

Two physical-contract qualifications remain: four VSL rows carry the wrong physical **link label**, although their DSD IDs address the correct owner and cell; five plan-active green phases have **no physical signal heads**. One of those phases still gates a positive model queue. Neither finding authorizes silently deleting a variable or changing service authority.

## Evidence and scope

The machine-readable companion `physical_actuator_ownership_audit.json` contains 25 source SHA256 values, every DSD, every controlled urban/ramp head, per-phase SG membership, and each identity comparison. Sources were unchanged during the static audit. Only JSON/CSV/XML/text were read; no controller imports, model rollout, benchmark, VISSIM, COM, configuration generation, or Git mutation occurred.

- Current configuration: `diagnostics/contract_candidate_configs_v4/n7_area_beta300.json` (`f3e48ac4df925c59aa18e1c40431d835e41b915f37c5a5af1d5d4dec38aa830b`).
- Current recorded profile action: `diagnostics/area_production_preflight/wu-link_t900_beta300_20260910T032525335593Z/action.{json,csv}`.
- Completed actual action: `evaluation/runs/codex_contract_beta300_s13_1050_v3_20260910/decisions_codex_contract_beta300_s13_1050_v3_20260910/action_000900.{json,csv}`; run ID `61b50c6f7a8642109b8d31ec18e20ff8`.
- INPX: `network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx`, SHA `085a10c71874e897083c97097af8fa3f1f08da1ef7416fef2f7cfbedabdfc317`.
- Mapping: `evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json`, SHA `d0a7bb9ff830f84c519608b2e77379f7bbe65606567cf2b9488b2c47759cde64`.
- Selected plan: `outputs/signal_group_actuation_plan_mainline_20260825.json`; `urban.plan.mainline_only=true` selects this file. The generated SG VBS, rather than a builtin default count, defines the expected rows.

The actual v3 run is not relabeled as a v4 run: its recorded tuning SHA is `35f124ef388fe18dc60dbac3599f2e28175ab71e21b4fd2a6a38d59aa0ad6141`, and its adapter SHA is retained in the JSON. The mapping/network/generated mapping hashes agree with its provenance. The current v4 profile CSV confirms the current writer's address set. This audit does not reuse historical `intent_only` offset findings as present behavior.

## Unique owner table

Each urban row owns the entire `SCx_p1..p4` vector and `offsets[SCx]`. Live phases share the controller's cycle budget; the five empty phases remain zero. A `signal_sg` row is a derived window from this owner's vector, not an independent strategy or second owner. Native SGs above 8 are excluded by the current VBS mainline gate.

| Owner | Model live phases | Derived SG windows | Controlled physical heads | Qualification |
|---|---|---:|---:|---|
| SC1 | p1,p2,p3,p4 | 8 | 13 | p4 has no heads |
| SC5 | p1,p2,p3,p4 | 8 | 15 | Native midblock SG10/14/20/24 excluded |
| SC6 | p1,p2,p3,p4 | 8 | 18 | |
| SC7 | p1,p2,p4 | 4 | 6 | p3=0; native midblock SG12/16 excluded |
| SC11 | p1,p2,p3,p4 | 8 | 10 | p2 has no heads |
| SC12 | p1,p2,p3,p4 | 8 | 12 | |
| SC16 | p1,p2,p3 | 6 | 10 | p4=0 |
| SC101 | p1,p2,p3,p4 | 8 | 20 | |
| SC105 | p1,p2,p3,p4 | 8 | 12 | p4 has no heads; its actual phase ordering remains the selected plan's ordering |
| SC107 | p2,p3,p4 | 6 | 16 | p1=0 |
| SC108 | p1,p3,p4 | 6 | 16 | p2=0 |
| SC109 | p2,p3,p4 | 4 | 12 | p1=0 |
| SC1001 | p1,p2,p3,p4 | 8 | 12 | Urban/off-ramp stopline service, separate from downstream meters |
| SC1002 | p1,p2,p3,p4 | 8 | 12 | |
| SC1003 | p1,p2,p3,p4 | 8 | 9 | p3 has no heads |
| SC1004 | p1,p2,p3,p4 | 8 | 17 | Urban/off-ramp stopline service, separate from downstream meters |
| SC1005 | p1,p2,p3,p4 | 8 | 6 | p1 has no heads and still gates a populated model movement |
| FW_E | VSL heads 0/5/10; meter R_D_E/R_F_E | 34 DSD objects; 4 meter SGs | 5 meter heads | VSL head15 fixed recovery setting |
| FW_W | VSL heads 0/5/10; meter R_D_W/R_F_W | 32 DSD objects; 4 meter SGs | 5 meter heads | VSL head15 fixed recovery setting |

Totals: 63 plan-active phases, 5 empty phases, 122 derived SG rows, 216 urban heads; 66 VSL objects, 8 meter SGs and 10 meter heads. Actual action CSV has 213 rows = 66 VSL + 17 signal + 122 signal_sg + 8 ramp_meter.

The code basis is `LinkAgentWuFollower` (`priced_wu_link_controller.py:96`), `enable_metering_in_gne` and its overridden `_solve_freeway_segment_agents` (`:141–171`), and `WuFaithfulFollower._solve_freeway_agent_metered` (`wu_faithful_follower.py:3268`, owned-ramp filter `:3297`). Although this compatibility path sets `segment_agents=True`, its override dispatches a **link** solver; it does not create 42 physical owners. `local_signal_plant.py:62–88` builds each urban model from its own phase/movement map; urban green and offset writes are indexed by that signal (`wu_faithful_follower.py:4569–4595`).

## VSL projection and native writes

| Owner | Zone | Model cells | Effective strategy key | Physical sign sites | DSD count | Freedom |
|---|---:|---|---|---|---:|---|
| FW_E | 0 | 0–4 | FW_E__seg0 | S0,S2 | 12 | free |
| FW_E | 1 | 5–9 | FW_E__seg5 | S5,S7 | 8 | free |
| FW_E | 2 | 10–14 | FW_E__seg10 | S10,S13 | 8 | free |
| FW_E | 3 | 15–20 | FW_E__seg15 | S15,S18 | 6 | fixed recovery |
| FW_W | 0 | 0–4 | FW_W__seg0 | S0,S2 | 9 | free |
| FW_W | 1 | 5–9 | FW_W__seg5 | S5,S7 | 7 | free |
| FW_W | 2 | 10–14 | FW_W__seg10 | S10,S13 | 8 | free |
| FW_W | 3 | 15–20 | FW_W__seg15 | S15,S18 | 8 | fixed recovery |

`install_freeway_vsl_zones` (`adapter:8411–8517`) projects reads and local VSL requests to a zone head. Candidate generation (`:8556–8608`) restricts free decisions to heads 0/5/10 and holds the recovery zone to the maximum setting. `link_predictor.py:514–516` returns the expanded 21-cell vector plus a direction fallback key. `write_action_csv` (`adapter:11865–11884`) reads the projected model coordinate and emits each mapped DSD.

Thus the 44 serialized VSL entries are not 44 independent choices: 6 free zone heads, 2 fixed heads, 34 inherited non-head cells, and 2 direction fallback keys. All 6 free heads have physical sites. The 26 cells without a direct sign are spatial model state/aliases, not unmapped independent actuators. The 52 DSDs in free zones and 14 in the fixed recovery zones are distinct objects.

S0 includes existing signs about 12 m into the road and newly installed signs at 40 m, on the same lanes. Those are different DSD IDs at different positions under the **same** owner, not duplicate assignments of one object. DSD names are historical labels and do not define owner/cell.

**Four address-label mismatches:** CSV/mapping S13 says link119 for DSD63–66, but INPX binds them to **link2 lanes1–4 at 3998.665994 m**. Native chain position is 6733.192994 m, within declared E cell13 `[6675.827,7189.352)` and zone head10. The VBS looks up DSD by ID, so the actual owner/zone remains correct. The label mismatch must be corrected by a separately reviewed mapping/generated-contract change; diagnostics must not locate this sign on link119 from the CSV label. All other 62 DSD native link/lane bindings match, and all 66 native positions belong to the declared owner/cell.

`ApplyActionCsv` (`VBS:1208–1230`) sets each DSD's `DesSpeedDistr(10/20/30/70)` assignment and checks all four; its recorded composite readback shows classes10/70. It does not mutate the global speed-distribution object. Sharing a distribution ID such as120 therefore does not make other DSDs another owner's write target.

## Meter ownership and shared traffic

| FW owner | Model strategy | Physical meter | SC/SG | Connector/head lanes | Physical merge cell | Model group merge cell |
|---|---|---|---|---|---:|---:|
| FW_W | R_D_W | RM_C10480 | 9101/1 | 10480 lane1 | 6 | 7 |
| FW_W | R_D_W | RM_C10482 | 9102/1 | 10482 lanes1–2 | 7 | 7 |
| FW_W | R_F_W | RM_C10646 | 9103/1 | 10646 lane1 | 11 | 13 |
| FW_W | R_F_W | RM_C10644 | 9104/1 | 10644 lane1 | 13 | 13 |
| FW_E | R_F_E | RM_C10639 | 9105/1 | 10639 lane1 | 8 | 9 |
| FW_E | R_F_E | RM_C10681 | 9106/1 | 10681 lanes1–2 | 9 | 9 |
| FW_E | R_D_E | RM_C10490 | 9107/1 | 10490 lane1 | 13 | 14 |
| FW_E | R_D_E | RM_C10484 | 9108/1 | 10484 lane1 | 14 | 14 |

The four model ramp rates are split into eight physical greens by the canonical measured-table realization (`adapter:10497–10647`). They are **not eight independently chosen follower variables**. Integer green/service conversion, receiving constraints and spillback guards can change the realized values but do not transfer ownership. The different physical versus aggregate merge cells are a model spatial-resolution limitation, not a duplicate meter writer.

Urban agents may gate vehicles before those same vehicles reach a freeway-owned meter, or share finite ramp storage and receiving capacity. Those are serial physical gates and coupled constraints. No meter SC/SG, head ID, or meter link/lane is also addressed by a selected urban signal. In particular, SC1001/SC1004 off-ramp phases are not SC910x ramp-meter actuators.

## Plan-active phases without heads: model-service distinction

The initial 5 empty phases (`SC7_p3`, `SC16_p4`, `SC107_p1`, `SC108_p2`, `SC109_p1`) are zero in both recorded actions. Separately, the following **active plan** phases have zero `signalHead` objects anywhere for their SG set. Their positive greens were written in actual v3 and retained in the current v4 profile.

| Phase | Planned SGs | Actual/profile green s | Model correspondence after declared corrections | Interpretation |
|---|---|---:|---|---|
| SC1_p4 | 1,5 | 22.667 | Shared-road turns corrected to p3; new physical proof moves `SC1_E_to_S_SC107` to p3. `SC1_W_to_N_SC101` remains a signal-gated physical `no_match` declaration. | Cannot certify globally unused; unresolved synthetic source/turn remains. Historical1200 queue0 is not a future zero-flow guarantee. |
| SC11_p2 | 3,7 | 22.667 | South turn corrected to p1 by legacy proof; north turn corrected to p1 by new physical proof. | No remaining directly served modeled turn found for p2 after these corrections; retained timing allocation. |
| SC105_p4 | 1,5 | 22.667 | Shared E/W turns corrected to p3; `SC105_E_to_S_SC1005` remains signal-gated physical `no_match`. | Same unresolved-source caveat; historical1200 queue0 does not prove permanent inactivity. |
| SC1003_p3 | 2,6 | 22.667 | Its sole configured turn `SC1003_E_SC105_to_N_SC1001` is corrected to p4. | Timing allocation, with no direct physical or remaining modeled p3 service found. |
| SC1005_p1 | 4,8 | 64.000 | `SC1005_N_SC105_to_W_SC1004` remains in p1, positive beta/capacity. Latest v4 raw900 projection assigns **4 veh** from physical403 to this movement queue, plus3 to its origin storage and2 to the other movement. | **Populated model service has no corresponding p1 head.** This is a physical-authority mismatch requiring follow-up, not merely an unused parameter. |

The SC1005 physical path is `403 → 10565 → 58`. Connector10565 starts on **403 lane1 at276.662179 m**. Road403's selected heads are SG7/p2 on **lanes2 and3** at271.920135/271.773668 m; there is no p1 SG4/8 head. The existing authority audit classifies this as partial lane/path control, not an unambiguous all-vehicle p2 service. A vehicle can change lanes before a branch, and yielding/conflict service remains relevant. Neither forcing this movement to p2 nor declaring it always-green follows from this audit.

Current action metadata confirms the three new physical phase corrections and the legacy correction list. The prior authority audit supplies the merged spec and local queue/capacity evidence; its stale two corrected phase mismatches are not counted as current defects. The remaining SC1005 phase is unchanged by the current phase proof. `local_signal_plant.py:80–91` derives `phase_of` and `cap_flow_of` from these specs; the service path uses this phase (`local_signal_service.py:341–348`; the global urban phase fraction uses the spec). This audit confirms positive **queue and service eligibility**, not a newly measured accepted-flow total: no new endpoint was run. A saved current-state/local-model dump and accepted-transfer trace should quantify the consequence before a service change.

## Constraints for the subsequent all-lever game

1. Preserve the same 17 urban owners, each controlling its entire feasible phase vector and offset; do not create separate competing phase/offset owners for one SC.
2. Preserve FW_E/FW_W ownership of three free VSL zones and two model meter rates each. Expanded cell values, recovery values, DSD rows and realized per-meter greens are derived values rather than extra players.
3. Keep physical realization inside candidate scoring, with a final duplicate-address/unknown-address check. Unique ownership alone does not prove output feasibility or local/global dynamics parity.
4. Preserve the five explicit zero phases. Review the headless but active phases as timing/service contracts; do not delete them just because they lack heads. SC1005's populated p1 queue is the priority authority check.
5. Correct the four S13 metadata addresses only through a reviewed mapping/VBS-contract update. Keep native DSD IDs and correct chain/cell ownership; do not move or recreate a sign merely to fit a mislabeled road.

No unresolved cross-owner write conflict was found in the current mapping. The remaining uncertainties concern service authority, model aggregation and optimizer strategy scope, not competing writers for the same physical object.
