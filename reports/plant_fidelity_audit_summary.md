# Plant Fidelity Static Audit Summary

Generated: `2026-08-10T13:29:59.846414+00:00`

> This report uses live files supplied to the CLI. Historical `outputs/gates_*` measurements are not treated as current evidence.

## Gate Summary

| Gate | Category | Status | Reason |
|---|---|---|---|
| `input_provenance` | runtime | **PASS** | all configured primary inputs were hashed |
| `network_xml` | topology | **PASS** | network XML parsed and signal-head references are well formed |
| `signal_controller_scope` | signal | **PASS** | raw XML active 50 / urban eligible 42 / model 41; auxiliary active 8, model excluded 1 |
| `link_partition` | topology | **PASS** | owned/freeway/exit categories form a complete disjoint partition |
| `assignment_ties` | topology | **FAIL** | equal-hop downstream terminal ties were found |
| `adjacency` | topology | **PASS** | adjacency declarations match their calculated sizes |
| `storage_capacity` | topology | **PASS** | jam density and all reported storage capacities are positive |
| `canonical_topology` | topology | **PASS** | canonical topology matches the audited network and its compiler report is clean |
| `vendor_snapshot` | runtime | **PASS** | vendor snapshot commit was recorded |
| `numsim_source_match` | runtime | **NOT_EVALUATED** | NUMSIM_REPO_ROOT was not provided by argument or environment |
| `state_observation_contract` | projection | **NOT_EVALUATED** | no state JSON was supplied or discovered under --action-dir |
| `action_inventory` | runtime | **NOT_EVALUATED** | no action directory was supplied or it does not exist |
| `runtime` | runtime | **NOT_EVALUATED** | no actual metadata.decision_wall_sec samples were found |
| `projection_diagnostics` | projection | **NOT_EVALUATED** | no projection_diagnostics records were found |
| `mass_conservation` | mass | **NOT_EVALUATED** | no projection_diagnostics record was available for a mass identity check |
| `runtime_provenance` | runtime | **NOT_EVALUATED** | no action JSON was available for runtime provenance validation |
| `preflight_provenance` | runtime | **NOT_EVALUATED** | no run provenance manifest references a preflight-v3 artifact |
| `signal_com_readback` | signal | **NOT_EVALUATED** | no signal_readback.csv files were found under --action-dir |
| `signal_event_timing` | signal | **NOT_EVALUATED** | no expected signal-transition oracle is available; readback rows alone cannot establish event timing error |
| `signal_timing_canon` | signal | **PASS** | canonical timing table is resolved, conflict-free, and agrees with the inpx supply file |
| `signal_actuation_plan` | signal | **PASS** | actuation plan covers every signal group without conflict violations |
| `movement_signal_group_map` | signal | **PASS** | every unresolved movement is an accepted synthetic boundary leg and the controller set matches |
| `stock_calibration` | calibration | **NOT_EVALUATED** | no physical stock calibration artifact was supplied |
| `paired_dynamics` | paired_dynamics | **NOT_EVALUATED** | no paired validation metrics artifact was supplied |
| `spillback_detection` | paired_dynamics | **NOT_EVALUATED** | no paired validation metrics artifact was supplied |
| `gradient_ranking` | ranking | **NOT_EVALUATED** | no gradient ranking artifact was supplied |
| `vissim_error_log` | runtime | **PASS** | VISSIM error log contains no error/fatal lines |
| `promotion_readiness` | promotion | **FAIL** | the audit's own gates are FAIL; no holdout promotion evidence artifact was supplied |

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
| Action JSON / state JSON | 0 / 0 |
| State contract explicit / action-dir discovered | 0 / 0 |
| Projection records pass / fail | 0 / 0 |
| Runtime provenance records pass / fail | 0 / 0 |
| Run groups pass / fail / mixed | 0 / 0 / 0 |
| Signal readback files / rows | 0 / 0 |
| Signal readback ok / mismatch / ok!=1 | 0 / 0 / 0 |
| Signal immediate / post-step / unpaired post-step | 0 / 0 / 0 |
| Signal readback malformed rows / files / empty files | 0 / 0 / 0 |
| Actual decision wall p95 / max (s) | - / - |
| Canonical topology cells / links | 5844 / 448 |
| Timing canon controllers / signal groups | 15 / 136 |
| Timing table disagreements | [] |
| Paired H gates measured | - |
| Spillback cells evaluated / blocked / exempt | - / - / - |
| Holdout promotion cells supplied | - |

## Provenance

- Workspace: branch `plant-fidelity-v2-1`, commit `39c8feff61a6b0aad3b3294c366c9a9426f0ed80`, dirty `True`
- Vendor snapshot commit: `5a2fe7dd7f4ecc9b53c7b59767f0a12441ce853c`
- Actual NUMSIM_REPO_ROOT: `-`
- Actual NumSim commit: `-`
- Vendor/actual src mismatch count: `-`

## Input Hashes

| Input | Exists | SHA-256 | Path |
|---|---|---|---|
| `network` | True | `f3ce390f281c2bd60a367435dd5567767edafb4681cb66a2c566a480aa74d635` | `C:\Users\alsrj\Desktop\학술\찐찐막\Claude\VISSIM\network\real_world_gaepo_modi\modi_eval_rw_control.inpx` |
| `signal_roles` | True | `376f1a23efab8ae4270aba09e72d3cf75915a885b24a6f32464a3ef800bb5ead` | `C:\Users\alsrj\Desktop\학술\찐찐막\Claude\VISSIM\evaluation\real_world_modi_inventory\signal_controller_roles.csv` |
| `link_assignment` | True | `ba9c13ba9fe9e05c51866a50221a1054d73a3379315bf97c108a0552397eb01f` | `C:\Users\alsrj\Desktop\학술\찐찐막\Claude\VISSIM\outputs\link_player_assignment_20260805.json` |
| `adjacency` | True | `a7cafe52693dfc46098f14763e37772a6f680ec56af28ac432bfcbfb907ae8ae` | `C:\Users\alsrj\Desktop\학술\찐찐막\Claude\VISSIM\outputs\intersection_adjacency8_20260805.json` |
| `storage_capacity` | True | `f196de2c444c72b117fec7f0e16f2c81189acada686b76f3def273096d8f87d5` | `C:\Users\alsrj\Desktop\학술\찐찐막\Claude\VISSIM\outputs\urban_storage_capacity_20260805.json` |
| `tuning` | True | `e5f8adcb2cba949cad6e2b7e8d98c80710925632e66ec17bc8472c96343c4fd4` | `C:\Users\alsrj\Desktop\학술\찐찐막\Claude\VISSIM\evaluation\configs\real_world_modi_pstack_distributed_core15n41_20260805.json` |
| `calibration` | True | `ea9425562c7ab5070a3a99f3a77ea4f47a46526237ab6c16618c681a21508252` | `C:\Users\alsrj\Desktop\학술\찐찐막\Claude\VISSIM\evaluation\calibration\real_world_prediction_calibration_pshb4500fix_20260724.json` |
| `control_mapping` | True | `9a3f246d9fd4c9f939a6b9d412ac093fc04254d7c7c209f844303d6309126792` | `C:\Users\alsrj\Desktop\학술\찐찐막\Claude\VISSIM\evaluation\real_world_modi_control_distributed_20260728\control_mapping_distributed_core15n41_20260805.json` |
| `detector_mapping` | True | `0ad49dd29b777159f8fb44d2827f5a920fdb846ba9c6e36e26c1417a7b941fed` | `C:\Users\alsrj\Desktop\학술\찐찐막\Claude\VISSIM\evaluation\real_world_modi_control_distributed_20260728\detector_local_mapping_distributed_core15n41_20260805.json` |
| `generated_vbs_config` | True | `34db527b8677e8d9a1a5abbe573340dec3953f7fd5f570df90962e1d11152ec2` | `C:\Users\alsrj\Desktop\학술\찐찐막\Claude\VISSIM\evaluation\generated\real_world_modi_control_config_distributed_core15n41_20260805.vbs` |
| `adapter` | True | `270478bcfa7e5b45472a36397a5dc498b4a38523516f13c9d6bb3c0958fb09ea` | `C:\Users\alsrj\Desktop\학술\찐찐막\Claude\VISSIM\evaluation\controllers\vissim_stackelberg_adapter.py` |
| `vendor_snapshot` | True | `e27a7558d5baeebd071631504ae0623a9cf4b50fc0a4372bd060bb81a0692db0` | `C:\Users\alsrj\Desktop\학술\찐찐막\Claude\VISSIM\vendor\NumSim-mine\SNAPSHOT.md` |

Signal programs hashed: **41**

## Notes

- `PASS` means the available static evidence satisfies the implemented invariant.
- `FAIL` means available evidence contradicts an invariant or threshold.
- `NOT_EVALUATED` means the necessary path or measurement was unavailable; it is not a pass.
- `BLOCKED` means the measurement is structurally impossible with the evidence at hand; it is worse than `NOT_EVALUATED`.
- Promotion needs every holdout demand to clear every promotion gate; low demand exempts spillback only.
- Projection diagnostics pass only when state/action pairing, both mass identities, residual consistency, and clipping rules are all verified.
- Runtime provenance is validated per run ID; mixed fingerprints under one run ID fail instead of being averaged together.
