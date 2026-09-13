# Native open v2: same-time source clock matches

`codex_native_clock_fw080_u050_open_v2` completed1050 seconds and owned PID50492 exited. A bounded read of actual LDP and COM readbacks took about0.62 seconds; no FZP/model access or production edits.

| Actual evidence | Samples | source(t−1) mismatches | Strict source(t) mismatches | source(t+1) mismatches |
|---|---:|---:|---:|---:|
| LDP850–900, before control | 6,936 | 142 | **0** | 142 |
| LDP901–1050, after control | 20,400 | 370 | **0** | 371 |
| LDP900–1050, including first boundary | 20,536 | 390 | **0** | 371 |
| Actual post-step readbacks900–1050 | 622 | 370 | **0** | 3 |
| Actual immediate writes900–1050 | 507 | 391 | 371 | **0** |

The native-only pre-step advance corrects the measured v1 lag: post-step frames now match the original `.sig` at the same actual timestamp. Immediate writes select the next recorded frame, as intended. SC7 SG4 now records AMBER at t908 and RED at t911, exactly matching the native source while SG7 remains GREEN.

The existing command/LDP execution gate passes. Native LSA still fails independently: 5,681 events, with495 of515 actual COM events absent. Same-time clock equality does not repair LSA coverage or prove identical vehicle trajectories. Root owns the separate trajectory comparison and subsequent meter experiment.

All signed variants, examples and LDP/source program SHA256 pins are preserved in `native_open_v2_source_clock_comparison.json`. The v1 direct clock failure remains unchanged.
