# Prepared VSL, meter, green and offset authority experiments

`diagnostics/diagnostic_lever_profiles.patch` is the combined integration patch.
It contains the previous signal-profile integration plus the explicit physical
meter contract and runner ownership checks. Apply this patch once; do not also
apply `diagnostic_signal_profile.patch`. It was prepared against the canonical
adapter after the existing VSL-profile integration, with no live source changes.

The experiments establish whether each physical command is applied and changes
traffic. The selected settings are not predictions of better performance.

| Lever | Controller | Baseline and treatment |
|---|---|---|
| VSL | `diagnostic-vsl-profile` | Existing E zone 0/5 profile 120 versus 80/100; native urban, all meters 10 |
| Meter | `diagnostic-ramp-profile` | `ramp_profile_config_open.json` versus `ramp_profile_config_c10639_g5.json` |
| Green | `diagnostic-signal-profile` | `signal_profile_config_zero.json` versus `signal_profile_config_sc1004_green10.json` |
| Relative offset | `diagnostic-signal-profile` | Same zero config versus existing plus/minus 10/20 configs |

All listed config paths are under `diagnostics/`. New meter and green configs
are flattened full n7 configurations, so the wrapper and adapter see the same
observation settings without depending on the wrapper's missing extends resolver.
Existing active VSL overlays were not changed by this work.

## Physical meter contract

The configuration key is `diagnostic.physical_meter_green_sec`, a mapping from
actual mapped physical meter ID to integer green seconds in [0,10]. Unspecified
meters are 10 seconds. The helper validates IDs, positive physical capacities,
unique positive SC/SG addresses, model ramp identities and the 10-second cycle.

The new physical writer branch reads the explicit actuation contract
`allocation=diagnostic_profile` and `diagnostic_green_sec`. It runs before the
measured allocator. It does not populate or reuse the allocator's diagnostic
cache and does not run a policy, spillback guard, optimizer or rate write-back.

The treatment changes only RM_C10639 / SC9105 to 5 seconds. RM_C10681, the other
R_F_E branch, stays 10. Both R_F_W branches RM_C10644 and RM_C10646 also stay 10;
the remaining four meters stay 10. All physical VSLs are 120 and all urban SGs
remain under native control.

The CSV requires `rate_vph = green_sec * physical_capacity_vph / 10`.
With the mapping capacity 900, the treatment writes **450 as a command encoding**.
It is not measured throughput, a discharge estimate, or a promise of 450 veh/h.
Observed departures must be calculated independently from actual vehicles.

Unlike the all-open VSL alias, the new meter alias uses the existing event
scheduler. The actual runner has 1-second ramp amber, so 5-second green means
GREEN at cycle positions [0,5), AMBER [5,6), RED [6,10). Starting at t=900, the
first sequence is 900 GREEN, 905 AMBER, 906 RED, 910 GREEN. Reusing the static
VSL alias for this treatment would omit those transitions; the adapter rejects
that combination explicitly.

The runner patch includes the meter alias in urban-row suppression and native
ownership validation at 1, control start, and completion. The normal physical
meter write/readback and event post-step validation paths remain in use.

Use `-Controller diagnostic-ramp-profile -ControlStartSec 900
-WarmupController no-control`, with `RW_SIGNAL_READBACK_SEC=1` to observe amber
and red persistence. `RW_SIGNAL_WRITE_ON_CHANGE=0` records every requested state
for all eight meters. Compare treatment to the all-open meter alias/config when
isolating scheduler and observer effects; comparison to pure no-control should
also account for their observation schedule. The parent controls live runs.

## Green and offset contract

The inactive `diagnostic_signal_profile.py` now accepts
`diagnostic.signal_profile.green_delta_sec`. Changes apply to the frozen,
already writer-clamped n7 greens. They must retain the same live phases, keep
every changed green within [5,90], and conserve the written cycle per SC.

The green arm moves 10 seconds from SC1004 p1 (20→10) to p3
(68.06376811594205→78.06376811594205). p2 and p4 are unchanged. The physical
signal row changes only p1/p3; derived SG windows change only for SC1004. Cycle,
offsets, other SCs, VSLs, and all eight meter commands remain identical.

The common signal baseline freezes the recorded n7 t=2100 plan. It is not
native no-control. The offset arms vary SC1001 and SC1004 in opposing directions,
leaving greens fixed. The writer uses `t + offset`, so a positive offset advances
the written cycle. Supply `RW_OFFSET_WRITER=test_only`; no production promotion
gate was opened. Use actual COM readback for controlled SGs, not native LSA.

All profile hashes now use the actual runtime selector: resolved n7 tuning,
`install_config_switches`, then `load_signal_group_actuation_plan`. This selects
the mainline_20260825 plan, not the raw v3 plan used in the superseded audit.
`offset_green_experiment_handoff.md` documents the corrected source and precise
SC7 overlap / SC16 idle-gap transformation findings. Native B network/SIG copies
were unaffected by the plan-selection correction.

## Completed verification

- `test_lever_profiles.py`: three Python tests PASS, including six isolated calls
  to the actual adapter main function with forbidden optimizer/policy/cache paths.
  The output command columns differ only by the requested lever. Runtime timing
  and descriptive CSV metadata are excluded from command equality.
- Its fourth test runs the actual VBS event functions in an offline mock and PASS:
  it applies each 900/905/906/910 transition, holds the other seven meters green,
  calls native ownership checks, and checks the preceding held state before the
  next event's write. Windows Script Host requires running this mock outside the
  sandbox to read its settings. It creates no VISSIM COM object.
- `test_signal_profile_experiments.py`: 3 PASS using the corrected effective plan;
  all five relative-offset arms differ only in offset columns.
- Parameter verification PASS for meter open, meter g5, green10 and gated FW-count
  corrected configs. Combined patch `git apply --check` PASS.

These are offline validation results. A live control claim requires the run's
COM immediate/post_step readbacks to match the expected states, plus native urban
ownership checks. Traffic benefits require paired physical TTD/TTT measurements.
