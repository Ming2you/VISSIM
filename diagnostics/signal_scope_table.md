# Signal scope and exact plan provenance

The table separates three different clocks: the original Ver2 native program, the nominal phase-union plan when passed through the current sequential writer, and the actual archived n7 t=2100 action CSV. They are not interchangeable baselines.

Effective n7 plan: `outputs\signal_group_actuation_plan_mainline_20260825.json`. The config loader and `install_config_switches` are applied before selecting it. Content SHA-256: `d2bf41f133ab39216dbdc6734187e286cee620f2c5b6e6946258cc14743880d7`.

| SC | Native C [s] | Nominal synthesized C [s] | Actual n7 CSV C [s] | Native green/cycle data mismatches | Best offset-only nominal/native residual [SG·s/cycle] |
|---|---:|---:|---:|---:|---:|
| 1 | 150 | 150 | 150 | 0 | 198 |
| 5 | 150 | 150 | 150.001 | 0 | 214 |
| 6 | 150 | 150 | 150.001 | 0 | 198 |
| 7 | 120 | 190 | 150 | 0 | different cycles |
| 11 | 150 | 150 | 150.001 | 0 | 306 |
| 12 | 150 | 150 | 150.001 | 0 | 222 |
| 16 | 150 | 116 | 150 | 0 | different cycles |
| 101 | 150 | 150 | 150.001 | 0 | 246 |
| 105 | 150 | 150 | 150.001 | 0 | 198 |
| 107 | 150 | 150 | 150 | 0 | 0 |
| 108 | 150 | 150 | 150 | 0 | 0 |
| 109 | 150 | 150 | 143.5 | 0 | 0 |
| 1001 | 150 | 150 | 150 | 0 | 0 |
| 1002 | 150 | 150 | 150.001 | 0 | 214 |
| 1003 | 150 | 150 | 150.001 | 0 | 214 |
| 1004 | 150 | 150 | 150 | 0 | 214 |
| 1005 | 150 | 150 | 150.001 | 0 | 214 |

SC7 has native overlapping green windows: SG4/8 [0,67) and SG7 [0,90). The phase-union writer serializes them, adds another 3-second clearance, and produces 120+67+3=190 seconds. SC16 has native SG2/6 [0,27), SG3/7 [64,81), SG4/8 [84,147); the 37-second gap after 27 becomes 3 seconds, removing 34 seconds. All plan native-green durations and native-cycle declarations match the actual Ver2 SIG files; those two distortions are consequences of the conversion, not mismatched duration source data.

The n7 controller reallocates greens. Its unrounded cycles are 150 seconds except SC109, where the writer clips recorded p3=96.5 to 90 and yields 143.5. CSV precision causes the +0.001 differences in the table. The actual archived CSV, rather than an assumed nominal cycle, is the source of the actual-n7-CSV column.

Archived CSV: `evaluation\runs\codex_n7_s13_6056c94_20260909\decisions_codex_n7_s13_6056c94_20260909\action_002100.csv`; SHA-256 `3e44fd3d5b20672d17d87820cb09e12505fec4502c0f5b613a436e5025e852fe`.

The `native-fixed` alias has a separate source-path defect: `native_fixed_control`
reads raw `outputs/signal_group_actuation_plan_v3.json` directly, while the SG
writer follows the n7 mainline selector. Its raw green inputs after writer
clamping would produce SC5=240 and SC7=213 before other policy guards. Those
numbers are neither the effective-plan nominal column above nor actual n7.
The table deliberately labels the nominal transform by its source; the frozen
A experiment bypasses this legacy helper. No fix is applied during the live run.

## Current experimental scope

- VSL and the one-meter test retain native urban ownership. The one-meter test changes only RM_C10639 green seconds and its required proportional CSV rate encoding; 450 is not measured discharge. Actual meter readback must show GREEN/AMBER/RED transitions.
- The green and relative-offset arms use the common frozen n7 signal baseline. SC1004 p1−10/p3+10 conserves its actual 150-second cycle; selected SC1001/SC1004 offsets likewise use exactly 150 seconds. No offset production gate was promoted.
- A uniform shift of every signal is not used as an interaction experiment. Opposing SC1001/SC1004 shifts change their relative timing.
- Original native programs cannot generally be reconstructed merely by restoring native offset on the nominal sequential plan. Four SCs have zero residual with one offset; the others have an order/window mismatch or a different cycle.
- Native B experiments use isolated network/SIG copies and alter selected program offsets from t=0. Their comparator is the prepared native arm; their warmup differs from interventions beginning at 900.
- Native LSA is evidence for native-owned SGs. COM-controlled meter and signal conclusions require actual immediate and post_step readback. A scheduler mock proves the selected execution path and call order, not live actuation.
- Control authority is not performance benefit. Traffic conclusions require paired physical TTD/TTT and congestion/spillback observations, with identical seed, demand, network and observer behavior.
- This audit corrects the earlier raw-v3 plan selection mistake. The archived source plan status PASS is not treated as proof of native behavioral equivalence.
