Actual beta0 action, 900–1050 s: prediction audit (codex_area_beta0_s13_20260910).
The model overpredicts freeway residence and underpredicts residence in the remaining protected area. These errors partly cancel in the aggregate Omega TTT. This is one observed interval, not a treatment-effect or beta comparison.
| Metric | Model | Physical measurement |
|---|---:|---:|
| Omega TTT (veh*h) | 82.674102 | 79.698750 |
| FW TTT (veh*h) | 42.774732 | 36.055972 |
| Remaining Omega TTT (veh*h) | 39.899370 | 43.642778 |
| Outward TD (veh) | 438.973090 | 469 observed + 227 terminal-inferred = 696 |
| Final Omega stock (veh) | 2210.596596 | 2083 COM; 2084 native FZP |

Physical residence uses 151 complete native FZP frames at 1 s cadence, with trapezoidal integration. Left/right rules give 79.654444 / 79.743056 veh*h; these are integration choices, not confidence bounds. Five interior disappearances are separately unresolved and receive no TD credit. Initial native/COM Omega stocks differ by two vehicles (1765/1763), and final stocks differ by one; native records precede the later paused COM phase. No final stock is treated as an exit.

| Off-ramp group | Model requested = accepted (veh) | Actual FW-to-connector entries (veh) |
|---|---:|---:|
| OR_D_W | 42.812326 | 77 (10479:32, 10491:45) |
| OR_F_W | 33.142654 | 83 (10638:42, 10645:41) |
| OR_F_E | 38.512834 | 68 (10643:23, 10682:45) |
| OR_D_E | 26.888184 | 67 (10481:35, 10483:32) |

All 295 connector entry events have a previously observed vehicle on that connector’s exact configured physical from_link. They are FW-to-off arrivals, not connector departures, sink counts, or initial stock. All four model group split ratios are 0.2. Receiving-cap blocking and later schedule rejection are both zero; the 141.356 total therefore comes from the requested split flow. Signal/direct shares only divide that already computed total once. Increasing receiver capacity cannot repair this interval’s under-request. The next narrow review is the total off-ramp route fraction and its physical entry cohort/position; no new ratio is fitted here.

| FW_E cell at1050 | Predicted speed (km/h) | Observed speed (km/h) | Predicted / observed stock (veh) |
|---|---:|---:|---:|
| 8 | 106.014 | 64.285 | 24.992 / 24 |
| 9 | 94.839 | 69.211 | 22.053 / 38 |

Direct connector10682 grows from9 to17 COM vehicles (native mean17.753, peak22); its slow residence below5km/h is0.217222veh*h. The model direct store SC1004_W_out contains several physical corridors and must not be equated with connector10682 alone. Likewise, signal OR store discharge is not automatically the same spatial boundary as the connector’s downstream join.

Each native mainline input changes from4619.8152veh/h at600s to6599.736veh/h at900s; the model reads6599.736 for each direction, matching the plant’s logged second input interval. Those rates remain unchanged through1050. Native observed appearances into the FW chains are230W+247E=477veh versus the model’s549.978 accepted entries. This difference may include actual input realization/admission; the configured profile is not lagged. Model internal Omega generation is117.616667veh (shared69, in_SC1_W and in_SC1001_W), separately added to boundary entries when checking stock closure.

The replay uses the actual last warmup action750, and its sat_est, far_rate_est and far_ramp_capacity values exactly match the live900 metadata. Earlier exploratory messages used older warmup history; the figures in this report replace those preliminary urban/total figures. All 15 model substeps assert the executed meter, green, offset and VSL vectors unchanged. Model stock and explicit flux closure pass. No optimizer search or VISSIM connection is used.

Source hashes are recorded before/after execution with no changes during the probe. Compared with the live manifest, only the later projection support data differ:16 added links all have zero vehicles at900, no existing assignment changes, and no motion equation changes. The baseline Git blob is verified against the live CRLF working-file hash. Physical FZP access reads only the selected900–1050 range by binary seek (about21.8MB of101MB), and records its byte offset and raw range SHA256.

The adjacent JSON contains accepted flows, physical entry/exit pairs, all42 cell comparisons, source hashes and complete unit definitions. The _trace.json file retains the15 ten-second model flow/state snapshots.
