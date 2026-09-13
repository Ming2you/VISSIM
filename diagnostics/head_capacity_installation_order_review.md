# Physical-head floor installation and final service audit

The actual v2 snapshot at 1050 s confirms an installation-order problem: two of 29 recorded group floors are allocated to members that are later reset or removed. The resulting final capacities are then consumed consistently by both global and local models. At 300 s the five recorded floors all survive; those earlier results alone did not cover the affected groups.

Evidence: `head_capacity_installation_order_v2_300.json`, produced by `audit_head_capacity_installation_order.py`. It uses the actual v2 `state_000300.json`, previous `action_000150.json`, and `contract_candidate_configs_v2/n7_area_beta0.json`. Both arms only configure/project, construct the actual Wu follower's static models, and reinstall runtime hooks on a pickled cfg. No endpoint, search, traffic step, action write, or VISSIM call occurs. Runtime/input bytes remained unchanged. The measured execution after source pinning took 11.73 s.

## Actual 300 s results

All rates below are veh/h of GREEN service. The final column is a **group sum**, not a new physical resource estimate.

| Physical group | Seed group sum | Installed floor | Final global/local/worker sum |
|---|---:|---:|---:|
| SC16 `1210009503 / p1` | 619.591837 | 619.591837 | 619.591837 |
| SC7 `1220007502 / p1` | 983.737916 | 983.737916 | 983.737916 |
| SC1 `1220008201 / p3` | 826.122449 | 1045.161290 | 1045.161290 |
| SC5 `1220014100 / p1` | 619.591837 | 619.591837 | 619.591837 |
| SC108 `176 / p3` | 1032.653061 | 1032.653061 | 1032.653061 |

`groups_updated=5` means five two-window floor decisions, not five increases. Only SC1's aggregate increases. Several other groups redistribute the unchanged seed total by the current movement beta: SC108's two members change from 826.122449/206.530612 to 1011.681639/20.971423. This is the present observer's group allocation, not a demonstrated independent capacity of each turn.

There are 105 eligible geometry groups, 86 with legacy model members, and 19 without. The actual global and fresh-local neutral-capacity maps match on every common movement; worker reinstallation changes neither caps nor specs and reproduces those maps. This checks installed scalar consumption, not future queue/service accuracy or a solved policy.

## Exact ordering and potential losses

The current shared initializer performs lane capacities, native signal structure, then measured/head capacity installation (`runtime_setup.py:90–101`). Later it prunes physical topology (`:116–125`), configures route corridors (`:129–136`), compiles the shared local service pool (`:138–139`), applies input signal authority (`:140–147`), and builds state/installs the remaining runtime hooks. The observer's per-member assignment is `signal_head_observation.py:221–222`.

`route_choice_corridor._configure_one` explicitly uses a separately pinned resource prior or `connector_lanes * initial_per_lane` (`:425`). It then replaces the retained cap and removes the alias (`:431`), and copies that rate to `turns[keep].service_veh_h`. The initial per-lane value comes from the earlier lane installer, not from a head floor.

| Mapped group | Retained physical turn | Artificial installed member rate | Final rate | Interpretation |
|---|---|---:|---:|---|
| `46 / p2` | `10627`, `SC1004_N_SC1003_to_E_SC1005` | 414.061224 | 206.530612 | Valid single-head lane-4 resource, later reset |
| `183 / p3` | `10619`, `SC107_E_SC108_to_W_SC1005` | 1653.244898 | 826.122449 | Four SG6 lanes, later reset; existing member set also includes a pre-head bypass |
| `1220043200 / p2` | `10610`, `SC107_N_SC1_to_W_SC1005` | 414.061224 | 206.530612 | Reset exists, but this member should not inherit those measured heads at all |

The artificial arm sets each private installed member to `2 * current_cap + 1` after the real observer returns. It supplies no fabricated raw window, prior action, capacity estimate, or trajectory. It establishes the overwrite path only. None of these three groups receives a floor at 300 s. The real 1050 s replay below subsequently confirms the `183/p3` overwrite with an actual carried floor.

The lane distinction matters. `1220043200/p2` observes SG7 heads on lanes 2/3, whose connector is `10103`; `10610` leaves lane 1 without either head. On road 183, SG6 heads cover lanes 1–4 at about 64 m and `10619` starts at 69.555 m. The current member `SC107_E_SC108_to_N_SC1` follows `10600`, which leaves lane 1 at 53.238 m before those heads. Blindly preserving the legacy beta-distributed values would therefore preserve a physical misassignment.

Other topology effects are distinct from a rate reset:

- `area_dynamic_routes.configure` removes impossible U-turn aliases in `1220000201/p3` and `52/p3`; it does not transfer their allocated capacities to a physical replacement. It also changes retained betas and zeros `1220000201/p4` betas. The observation stage still uses the pre-repair member set. Removed impossible movements should remain removed; their old allocations are not valid lost traffic capacity by themselves.
- Two physical groups, `1210012001/p3` and `1220012001/p3`, map to the same two SC11 movement names. The distributor writes the dict in group order, rather than defining a shared physical resource. At 300 s neither is updated. This is a separate group-identity ambiguity to resolve before treating arbitrary group floors as independent additions.
- Native-input signal-authority repair keeps its verified movement capacity and removes unsupported siblings (`physical_movement_routes.py:414–433`). No observed mapped-member rate reset was found in the current native-input or SC2001 configuration calls.

## Final consumers

Global ordinary urban service calls `_movement_capacity_flow`, then multiplies by the actual phase fraction and urban time step (`urban_flow_accounting.py:435–449`). The canonical function returns the per-member cap for internal movements; perimeter allocations can further throttle their ceiling (`vendor/.../urban_queue_model.py:730–764`). Receiver/storage limits remain separate.

The actual Wu constructor builds each local model after runtime configuration. `local_signal_plant.build_local_model:80–90` caches the same canonical function with empty allocation. Local service multiplies the cached cap by the green fraction and time step. The opt-in SC1004 pool checks that the final movement map, route service, and local cached cap agree; green, offset, and phase-refinement use that pool. These consistency checks cannot recover a floor already discarded by route configuration.

Worker setup does not rerun measured capacities or topology construction. It receives the completed cfg and reinstalls functions. The audit tests pickle plus worker reinstallation in the same Python process; it does not claim a new worker subprocess or full candidate solve.

## Smallest future repair to review — not implemented

1. Preserve the observer's validated **physical-head group floor and provenance** independently of its provisional member-cap allocation. Include exact link/lane/head/SC/SG and the two accepted windows; do not reconstruct the floor by summing later alias caps.
2. At each topology owner's final service assignment, consume only floors with a proven head-to-connector resource join. For `46/SG7`, the one lane-4 head uniquely feeds `10627`; its two future-destination aliases should become one service resource before applying one floor. For `183/SG6`, the four post-head lanes feed `10619`; exclude pre-head `10600`. Do not apply lane-2/3 SG7 observations to unsignalled `10610`.
3. Update the existing canonical resource's `service_veh_h` and its required capmap views together before the local pool is compiled. For `10634`, retain one shared resource and one accepted budget; its three source aliases are views and must not add three floors or multiply the aggregate by lanes. Its current offline prior remains separately sourced.
4. Ordinary unaffected groups may retain the current path. Repaired/deleted/duplicate group mappings need explicit physical membership reconciliation or an unapplied-floor diagnostic, not an automatic whole-cap-map reinstallation after all configuration.
5. Add assertions that every applied floor reaches its intended final resource and global/local/worker consumer, with a recorded reason for ineligible or unapplied groups. Keep physical receiving/storage constraints unchanged. Validate one actual affected two-window group before interpreting the repair as an operating improvement.

## Completed 1050 s actual audit

`head_capacity_installation_order_v2_1050.json` uses the completed v2 run's exact `state_001050.json`, previous `action_000900.json`, and original v2 beta0 config. The actual shared initialization succeeds and takes 9.61 s after pinning. No artificial perturbation is used in this run. `source_changes=[]`; every surviving mapped member has global, local, and worker consumer values, with no disagreement or worker cap/spec change.

The observer records 28 carried and 16 updated groups, with overlap; there are 29 distinct floor keys. Of these, 27 retain their recorded group sum through final consumption. The two exceptions are:

| Physical group | Recorded floor / initially allocated total | Later change | Final unique member sum |
|---|---:|---|---:|
| `183 / p3`, SC107 | 1445.714286 | Choice merge resets retained W member 976.322139→826.122449; its removed future-destination alias had 422.723475 | 872.791121, including unchanged pre-head N member 46.668672 |
| `52 / p3`, SC1004 | 1040.000000 | Physical topology repair removes two impossible aliases allocated 202.283569 and 346.657422 | 491.059010 from retained members 144.401588 and 346.657422 |

Both values were already carried in the previous 900 s action. The `183` floor is the **inherited seed-group sum**, not a measured 1445.714 veh/h discharge claim: its current head candidate is 1061.538462, and its legacy seed includes destination aliases and the pre-head member described above. Therefore 1445.714 must not be copied blindly into one physical connector as a purported measured lower bound. The `52` carried floor is 1040, slightly above the seed sum 1032.653061; correcting impossible topology remains necessary, but capacity allocation before that correction is inconsistent with the final physical member set.

The complete 34-row actual floor table across 300/1050 is `head_capacity_installation_order_floors.csv`. Merged aliases are deduplicated by final target when calculating final group sums. The artificial 300 s arm remains separate in its original JSON.

Reproduction, without dynamics or a solver:

```powershell
python -m diagnostics.audit_head_capacity_installation_order --config diagnostics/contract_candidate_configs_v2/n7_area_beta0.json --state evaluation/runs/codex_contract_observed_nc_s13_1050_v2_20260910/decisions_codex_contract_observed_nc_s13_1050_v2_20260910/state_001050.json --previous evaluation/runs/codex_contract_observed_nc_s13_1050_v2_20260910/decisions_codex_contract_observed_nc_s13_1050_v2_20260910/action_000900.json --out diagnostics/head_capacity_installation_order_v2_1050_new.json
```

The first failed v1 smoke remains a failure; replaying its 150 s raw with the corrected current serializer did not establish success of that original run. Source pinning additionally hashes transitive historical evidence files, including FZP bytes; this audit does not parse or rescan their vehicle frames. No production code, active config, membership, calibration, or action was changed.
