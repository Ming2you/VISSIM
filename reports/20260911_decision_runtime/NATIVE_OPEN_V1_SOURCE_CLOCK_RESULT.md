# Native open v1: direct source-clock equivalence fails by one second

Run `codex_native_clock_fw080_u050_open_v1`, selected 80% freeway / 50% urban demand, completed 1050 seconds. The wrapper observed owned PID34744 gone. The existing native command-execution gate passes; that does not establish equivalence to the original fixed-time timeline.

Actual LDP frames were compared separately to `.sig` at the same timestamp and at signed lag variants. Lag −1 means compare LDP(t) to source(t−1); it is not relabeled as a direct match.

| Evidence / interval | Samples | Source(t−1) mismatches | Strict source(t) mismatches | Source(t+1) mismatches |
|---|---:|---:|---:|---:|
| Native before COM, LDP850–900 | 6,936 | 142 | **0** | 142 |
| After COM, LDP901–1050 | 20,400 | **0** | **370** | 741 |
| Requested inclusive boundary, LDP900–1050 | 20,536 | 20 | **370** | 741 |
| Selected NC LSA vs `.sig`, t850–1050, observable SGs | 24,522 | 512 | **0** | 513 |
| After COM LDP vs selected NC LSA, t901–1050 | 18,300 | **0** | **370** | 741 |

The NC LSA omits 14 permanent-red SGs, which are explicitly unobserved in that comparison; source `.sig` and LDP comparisons include all 136 owned urban SGs. The native program agrees with same-time source before COM. After COM starts at 900, the LDP states consistently match the previous source second. This is a measured one-second clock delay, not a plotting assumption.

Example: SC7 SG4 should enter AMBER at source t908 while SG7 remains GREEN. LDP908 still records SG4 GREEN; LDP909 records AMBER. At source t911 SG4 is RED, while LDP911 remains AMBER and LDP912 is RED. The own-AMBER behavior is present, but shifted by one second.

Actual immediate COM readbacks match source(t): 0/506 mismatches in t900–1050. Their next-step/post records match source(t−1): 0/618 mismatches, versus 20 at strict source(t). The immediate samples alone also happen to match source(t+1) because unchanged plateaus include the next second; they do not prove a forward shift. Complete LDP frames distinguish the lag.

Existing postcheck evidence remains separate:

- Signal readbacks: 1,196 rows checked, PASS; 514 required initial/changed immediate writes, PASS.
- LDP: 151,200 owned urban/meter samples over t1–1050, PASS against the recorded command clock.
- Native LSA: 5,681 native events; 494 of 514 required actual COM events missing, **FAIL**. Command/LDP agreement does not fill this missing LSA coverage.

Detailed signed variants, examples and source/LDP pins are in `native_open_v1_source_clock_comparison.json`. Analysis read about 0.7 seconds of small LDP/LSA/receipt material and did not read FZP, run a model, modify production code or alter any run artifact.
