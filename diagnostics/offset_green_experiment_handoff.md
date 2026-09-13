# Offset/green isolation: audit and prepared experiments

Prepared 2026-09-10; original adapter, VBS, network and native SIG files were not
modified by this work. No offset production gate was changed or marked PASS.

## Findings that affect interpretation

Correction: the earlier audit incorrectly read the raw v3 plan before applying
the n7 config switches. Its SC5 150→240 and SC7 120→213 claims do not describe
the effective n7 writer plan and are withdrawn in that context.
The actual n7 path is `load_optional_json` → `install_config_switches` →
`load_signal_group_actuation_plan`, selecting
`outputs/signal_group_actuation_plan_mainline_20260825.json`, content SHA-256
`d2bf41f133ab39216dbdc6734187e286cee620f2c5b6e6946258cc14743880d7`.
All A configs and tests now use that same path and hash.

Passing the effective plan's own nominal phase-union greens through the
sequential phase/SG writer gives the following results. This is a plan-transform
audit, not a claim about an optimized n7 action or the `native-fixed` alias.
SC5 retains 150 seconds; SC7 changes 120→190; SC16 changes 150→116. Fifteen
preserve cycle length, but only SC107/108/109/1001 can match the native
mainline SG states by choosing one best offset. The other 11 have changed
within-cycle order or windows, so adjusting offset alone cannot restore them.

This is not stale native duration data: the plan's `native_cycle_sec` and
`native_green_sec` match the actual Ver2 SIGs for every SG in all 17 SCs.
SC7's SG4/8 green [0,67) overlaps SG7 green [0,90). Sequentializing the
67/90/24-second phase unions loses that 67-second overlap and inserts one
extra 3-second clearance: 120+67+3=190. SC16's native greens are [0,27),
[64,81), [84,147); the 37-second gap after 27 contains 34 more idle seconds
than the 3-second clearance retained by the synthesized plan: 150−34=116.
The source plan metadata references the older 20260814e network, but the
per-SG duration comparison itself is against the actual Ver2 programs.

A separate code defect exists in `native_fixed_control`: it hardcodes the raw
`signal_group_actuation_plan_v3.json` instead of using the selector. That alias's
green source and its runtime-selected mainline SG writer therefore differ.
The old 240/213-second values describe those raw-v3 phase inputs after writer
clamping, before any other policy guards; they do not describe live n7. The
prepared frozen-signal experiments do not call `native_fixed_control`.

The actual recorded n7 t=2100 control is a separate plan, with intentional
green allocation: 16 SCs have 150-second cycles before CSV rounding; SC109
writes 143.5 because its recorded p3=96.5 is clipped by the existing 90-second
writer limit. Three-decimal serialization gives some other SCs cycles of
149.999 or 150.001 (SC5 is 150.001). SC1001 and SC1004 remain exactly 150.
The prepared A arms reproduce those same written greens and serialization.

The compiled native `.sig` clock uses `t - native_offset`, and matches all
109,800 observed native city mainline SG seconds in the no-control `.lsa`
over [900,1800). The VBS COM writer uses `t + writer_offset`. Replaying raw
native windows therefore needs `writer_offset = (-native_offset) mod C`.
Raw windows with that sign reproduce all 122,400 tested SG-second states
exactly, including SGs without an observed LSA interval. Simply adding the
positive native offset to the current compressed plan is neither sign-correct
nor native-equivalent. SC1001's current plan is already native-equivalent at
writer offset zero, despite its native SIG offset being 75 seconds.

These are offline clock/plan comparisons, not a claim of identical vehicle
trajectories after COM takeover. `diagnostics/audit_native_signal_replay.py`
produces `diagnostics/native_signal_replay_audit.json` with all 17 SCs and SG
green/cycle values. Native city LSA is used only because those SGs are not owned
by COM; ramp aspects must instead use post-step COM readback.

Archived `urban.offset.force_native` and `commit_optimized` configuration paths
are absent from the current canonical adapter. Reusing the archived nfoffset
config alone will not execute those helpers. The still-active forced table
`offset_promotion.FORCED_ARM_TABLE_KEY` is the supported test_only mechanism.

## A: freeze the current synthesized signal plan

New helper: `evaluation/controllers/diagnostic_signal_profile.py`.
Use the combined pending integration `diagnostics/diagnostic_lever_profiles.patch`.
It includes the earlier `diagnostic_signal_profile.patch`; do not apply both.
Do not apply during a live run. The signal alias uses the existing event and
single-decision scheduler. The combined patch adds separate native-urban meter
experiments and their event-mode ownership readback.

The source is the recorded n7 action at t=2100, preserved as the small
`diagnostics/frozen_n7_2100_green_action.json`. It contains the original source
path/hash and only its green_times. The helper validates that snapshot's SHA
and the canonical content SHA of the SG plan. All 17 SC green windows remain
fixed; only the forced writer offsets change. VSL is 120 and every meter is
fully open. This is a common synthesized-plan baseline, not native no-control.

Five standalone, flattened runner configs are ready (no extends dependency):

- `diagnostics/signal_profile_config_zero.json`: all writer offsets zero.
- `diagnostics/signal_profile_config_plus10.json`: SC1001 +10, SC1004 -10.
- `diagnostics/signal_profile_config_minus10.json`: SC1001 -10, SC1004 +10.
- `diagnostics/signal_profile_config_plus20.json`: SC1001 +20, SC1004 -20.
- `diagnostics/signal_profile_config_minus20.json`: SC1001 -20, SC1004 +20.

Offsets are modulo each actual written cycle; positive COM writer offset
advances the frozen cycle. All other SCs stay at zero. This changes relative
timing, not a uniform shift of the whole network.

Run with `-Controller diagnostic-signal-profile -ControlStartSec 900
-WarmupController no-control`, without ForceStepwise. Set process environment
`RW_OFFSET_WRITER=test_only` for the runner's second gate, and
`RW_SIGNAL_WRITE_ON_CHANGE=0` when collecting complete immediate readback.
The config declares adapter `offset_writer=test_only`. Production remains
locked; the helper supplies a forced table, not optimizer-selected offsets.

Validation: `python diagnostics/test_signal_profile_experiments.py -v` has
3 tests PASS. Every CSV column/row is identical across the five A arms except
offset; all 17 signal rows and every SG window were compared, and every meter
is 10-second green. Snapshot/plan drift and unknown SCs fail. The helper and
pending adapter compile, and `git apply --check` passed. The combined
`test_lever_profiles.py` now also executes the real main function in memory
for VSL80, meter open/5-second, signal zero/green10/offset10 arms. All command
columns remain identical except the intended lever. A full live run remains
for the parent after integration.

For live validation use `scripts/analyze_actuation.py` and
`scripts/verify_signal_timing_oracle.py` on actual `signal_readback.csv`.
At each event, compare immediate state to the chosen frozen plan at t+offset;
at the next event compare post_step readback to the preceding held state.
Require unchanged green/window/cycle columns and successful readback before
interpreting TTD/TTT differences. The existing oracle deliberately keeps its
subsecond transition gate BLOCKED at 1-second resolution; do not rewrite that
status to open production.

## B: preserve actual native programs, vary only selected native offsets

Producer: `diagnostics/prepare_native_offset_network.py`.
The following new sibling INPX files have been prepared under
`network/real_world_gaepo_modi/`:

- `diagnostic_native_offset_native.inpx`: source offsets unchanged.
- `diagnostic_native_offset_zero.inpx`: native offsets of SC1001/SC1004 are zero.
- `diagnostic_native_offset_advance10.inpx`: SC1001 native -10, SC1004 +10.
- `diagnostic_native_offset_delay10.inpx`: SC1001 native +10, SC1004 -10.
- `diagnostic_native_offset_advance20.inpx`: SC1001 native -20, SC1004 +20.
- `diagnostic_native_offset_delay20.inpx`: SC1001 native +20, SC1004 -20.

The selected SIG copies are in `_diagnostic_native_offsets/<arm>/SC1001.sig`
and `SC1004.sig` alongside the source network. The new INPX changes only those
two supplyFile2 references. Each SIG changes only offset attributes of its
three programs. Every SG timeline, color, cycle, and switchpoint is preserved;
unselected references are byte-identical. Originals were re-hashed afterward.
Each arm has 14,400 exact native clock state checks over two cycles/program.
Evidence: `diagnostics/native_offset_<arm>_manifest.json`; reproducible recipes
are `diagnostics/native_offset_recipe_<arm>.json`.

These are treatments from **t=0**, so compare against the prepared native arm
with the same settings. Do not describe their warmup as identical to an arm
that changes at t=900. Native offset +10 delays the signal, the opposite sign
of a COM writer offset +10. All recipes explicitly preserve this distinction.

Use the existing `diagnostic-vsl-profile` alias with an empty VSL profile and
the same full n7 config to retain native city signals and open meters. This
also records native city ContrByCOM ownership at t=1/900/end. An unchanged
native network with `no-control` is another valid comparator if the exact
meter command/observer settings are held constant. No A adapter patch or
offset promotion gate is needed for B: VISSIM executes isolated native SIGs.
Validate city native LSA clocks against each prepared SIG, and meter COM
post-step readback against GREEN. Then compare physical TTD/TTT and spillback.

To regenerate one arm, pass its recipe to the producer with `--out-network`
set to the new sibling INPX path and `--manifest` to its manifest path. It is
idempotent for identical prepared files and refuses overwriting a different
artifact or the source. New network files are derived artifacts; retain the
small producer/recipes/manifests for versioning rather than duplicating them
as additional canonical networks.
