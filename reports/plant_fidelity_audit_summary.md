# Plant Fidelity Static Audit Summary

Generated: `2026-08-05T09:44:13.807410+00:00`

> This report uses live files supplied to the CLI. Historical `outputs/gates_*` measurements are not treated as current evidence.

## Gate Summary

| Gate | Status | Reason |
|---|---|---|
| `input_provenance` | **PASS** | all configured primary inputs were hashed |
| `network_xml` | **PASS** | network XML parsed and signal-head references are well formed |
| `signal_controller_scope` | **PASS** | raw XML active 50 / urban eligible 42 / model 41; auxiliary active 8, model excluded 1 |
| `link_partition` | **PASS** | owned/freeway/exit categories form a complete disjoint partition |
| `assignment_ties` | **FAIL** | equal-hop downstream terminal ties were found |
| `adjacency` | **PASS** | adjacency declarations match their calculated sizes |
| `storage_capacity` | **PASS** | jam density and all reported storage capacities are positive |
| `vendor_snapshot` | **PASS** | vendor snapshot commit was recorded |
| `numsim_source_match` | **PASS** | actual NumSim src matches the vendor snapshot file-for-file |
| `state_observation_contract` | **PASS** | all supplied and action-dir-discovered states contain link counts, speeds, and stopped counts |
| `action_inventory` | **PASS** | state/action JSON inventory completed |
| `runtime` | **FAIL** | actual decision wall time exceeds p95=30s or max=45s |
| `projection_diagnostics` | **PASS** | every projection record satisfies both mass identities, residual consistency, the unrepresented limit, and clipping rules |
| `runtime_provenance` | **PASS** | every action is paired to a state and each run_id has one verified runtime provenance fingerprint |
| `signal_com_readback` | **PASS** | every signal readback row has matching requested/readback states and ok=1 |
| `signal_event_timing` | **NOT_EVALUATED** | no expected signal-transition oracle is available; readback rows alone cannot establish event timing error |
| `vissim_error_log` | **PASS** | VISSIM error log contains no error/fatal lines |

## Static Scale

| Evidence | Value |
|---|---:|
| Network links | 1219 |
| Connectors | 771 |
| Raw XML active signal controllers | 50 |
| Urban eligible controllers (roles `active=true`) | 42 |
| Model signal controllers | 41 |
| Auxiliary active / artificial ramp-meter SCs | 8 / 8 |
| Model-excluded controllers | [9004] |
| SC9004 head references | 0 |
| Assignment owned / freeway / exit | 957 / 22 / 226 |
| Assignment coverage / duplicates / ties | 1205 / 0 / 33 |
| Adjacency pairs / internal pairs | 123 / 94 |
| Internal member refs / unique | 199 / 146 |
| Jam density (veh/km/lane) | 140.543 |
| Storage entries / total vehicles | 186 / 34154.900 |
| Action JSON / state JSON | 8 / 9 |
| State contract explicit / action-dir discovered | 0 / 9 |
| Projection records pass / fail | 8 / 0 |
| Runtime provenance records pass / fail | 8 / 0 |
| Run groups pass / fail / mixed | 2 / 0 / 0 |
| Signal readback files / rows | 2 / 10448 |
| Signal readback ok / mismatch / ok!=1 | 10448 / 0 / 0 |
| Signal immediate / post-step / unpaired post-step | 2432 / 8016 / 0 |
| Signal readback malformed rows / files / empty files | 0 / 0 / 0 |
| Actual decision wall p95 / max (s) | 154.746 / 154.746 |

## Provenance

- Workspace: branch `codex/plant-fidelity-audit-20260805`, commit `dc216be623abc3021963dd2735b4e485d01c6e68`, dirty `True`
- Vendor snapshot commit: `35a5c82`
- Actual NUMSIM_REPO_ROOT: `C:\tmp\VISSIM-pstack-audit\vendor\NumSim-mine`
- Actual NumSim commit: `-`
- Vendor/actual src mismatch count: `0`

## Input Hashes

| Input | Exists | SHA-256 | Path |
|---|---|---|---|
| `network` | True | `2f75c76c71bab2ac9b35b3308bb9b0dec83e1c0bacff969d85e56cb09a7ceda0` | `C:\tmp\VISSIM-pstack-audit\network\real_world_gaepo_modi\modi_eval_rw_control.inpx` |
| `signal_roles` | True | `376f1a23efab8ae4270aba09e72d3cf75915a885b24a6f32464a3ef800bb5ead` | `C:\tmp\VISSIM-pstack-audit\evaluation\real_world_modi_inventory\signal_controller_roles.csv` |
| `link_assignment` | True | `ba9c13ba9fe9e05c51866a50221a1054d73a3379315bf97c108a0552397eb01f` | `C:\tmp\VISSIM-pstack-audit\outputs\link_player_assignment_20260805.json` |
| `adjacency` | True | `a7cafe52693dfc46098f14763e37772a6f680ec56af28ac432bfcbfb907ae8ae` | `C:\tmp\VISSIM-pstack-audit\outputs\intersection_adjacency8_20260805.json` |
| `storage_capacity` | True | `f196de2c444c72b117fec7f0e16f2c81189acada686b76f3def273096d8f87d5` | `C:\tmp\VISSIM-pstack-audit\outputs\urban_storage_capacity_20260805.json` |
| `tuning` | True | `cc06538e0e75ceff4e83f505b68fa73bcdd144ea9cf76277a9f21f466be8bcd6` | `C:\tmp\VISSIM-pstack-audit\evaluation\configs\real_world_modi_pstack_distributed_core15n41_20260805.json` |
| `calibration` | True | `ea9425562c7ab5070a3a99f3a77ea4f47a46526237ab6c16618c681a21508252` | `C:\tmp\VISSIM-pstack-audit\evaluation\calibration\real_world_prediction_calibration_pshb4500fix_20260724.json` |
| `control_mapping` | True | `9a3f246d9fd4c9f939a6b9d412ac093fc04254d7c7c209f844303d6309126792` | `C:\tmp\VISSIM-pstack-audit\evaluation\real_world_modi_control_distributed_20260728\control_mapping_distributed_core15n41_20260805.json` |
| `detector_mapping` | True | `0ad49dd29b777159f8fb44d2827f5a920fdb846ba9c6e36e26c1417a7b941fed` | `C:\tmp\VISSIM-pstack-audit\evaluation\real_world_modi_control_distributed_20260728\detector_local_mapping_distributed_core15n41_20260805.json` |
| `generated_vbs_config` | True | `45c2dad782ed9b3a66f0d5df4ca41e933794978b209cc0ce0a0cc36d99c9abdf` | `C:\tmp\VISSIM-pstack-audit\evaluation\generated\real_world_modi_control_config_distributed_core15n41_20260805.vbs` |
| `adapter` | True | `b9883e64bc025d480dd6a274552fe031b9c5262fcfb7bd9b787d46c7f7908d9d` | `C:\tmp\VISSIM-pstack-audit\evaluation\controllers\vissim_stackelberg_adapter.py` |
| `vendor_snapshot` | True | `3a99f9ef4dd572790ac81a5bbdb71637fbd3e35b04e1080a55f5e33e931ce67f` | `C:\tmp\VISSIM-pstack-audit\vendor\NumSim-mine\SNAPSHOT.md` |
| `extra:main_vbs_runner` | True | `38ffd5597196a389a6875707030166b921b3ce1682b290551c33b329360a741a` | `C:\tmp\VISSIM-pstack-audit\scripts\run_real_world_stackelberg_controller.vbs` |
| `extra:watchdog` | True | `a6feb2eb4538080ab6a02511e71a4d46de97f7b61b0406a58394a6f4e4699181` | `C:\tmp\VISSIM-pstack-audit\scripts\run_real_world_single_watchdog_distributed_core15n41.ps1` |
| `extra:matrix` | True | `191deb845f4843eca9ecf534a5166de85eeaca969420c1a5b4cdd981ba98fdc6` | `C:\tmp\VISSIM-pstack-audit\scripts\run_plant_fidelity_matrix.ps1` |
| `extra:topology_ties` | True | `adcb1dff7037f87c1f68963930c5d50b30628477c00be778efd1e81e70a37721` | `C:\tmp\VISSIM-pstack-audit\reports\link_assignment_ties.json` |

Signal programs hashed: **41**

## Notes

- `PASS` means the available static evidence satisfies the implemented invariant.
- `FAIL` means available evidence contradicts an invariant or threshold.
- `NOT_EVALUATED` means the necessary path or measurement was unavailable; it is not a pass.
- Projection diagnostics pass only when state/action pairing, both mass identities, residual consistency, and clipping rules are all verified.
- Runtime provenance is validated per run ID; mixed fingerprints under one run ID fail instead of being averaged together.
