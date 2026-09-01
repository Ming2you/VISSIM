# Environment review report before detector installation

Date: 2026-06-25  
Reviewed environment summary: `evaluation/environment_setup_summary.md`

## Outcome

Detector installation can proceed after the current environment review.

No blocking failure was found, provided that detector objects are added only to an evaluation copy
such as `modi_eval_control.inpx/.layx`, not to the user-edited source `modi.inpx/.layx`.

## Sub-agent review result

Independent reviewer: `Ramanujan`

PASS:

- The environment summary matches the inspected artifacts.
- `scripts/run_global_state_smoke.vbs` does not call `SaveNet` or `SaveNetAs`.
- The explicit step-count loop with `SimPeriod = requested + 1` is a reasonable workaround for Vissim's final-period reset behavior.
- The 180-second smoke summary supports successful load/step/global-state logging.
- Ramp metering as `SignalHead` and VSL as `DesSpeedDecision` are plausible Vissim implementation choices.

WARN items from review:

- Global state groups were hardcoded in the smoke runner.
- Freeway demand classification depended on names containing `VI_FW_`.
- Smoke proves loading/stepping/logging, not route realism.
- Current controller mode is still `GLOBAL_NOOP`.
- Dedicated `Detector` objects are still missing.

FAIL:

- No blocking failure before detector installation.

## Fixes applied after review

Two non-blocking warnings were fixed before detector installation:

1. Added `scripts/generate_global_state_config.py`.
2. Generated:
   - `evaluation/generated/global_state_config.vbs`
   - `evaluation/generated/global_state_config.json`
3. Updated `scripts/run_global_state_smoke.vbs` to load the generated config automatically.
4. Updated demand classification to use freeway input link numbers (`33,34`) rather than only the `VI_FW_` name convention.

The smoke runner still has embedded fallback defaults, but the normal path is now generated from
`network_mapping.json` and `inventory.json`.

## Fresh Vissim smoke verification

Fresh 60-second smoke before patch:

- Output: `evaluation/runs/environment_review_smoke/global_state_60s.csv`
- Summary: `evaluation/runs/environment_review_smoke/summary_60s.json`
- Result: PASS
- Rows: 13
- Last second: 60
- Vehicles generated: yes
- Final total vehicles: 8
- Max stopped vehicles: 0
- Source INPX timestamp unchanged: yes

Fresh 30-second smoke after generated-config patch:

- Output: `evaluation/runs/environment_review_smoke/global_state_30s_after_patch.csv`
- Summary: `evaluation/runs/environment_review_smoke/summary_30s_after_patch.json`
- Result: PASS
- Rows: 7
- Last second: 30
- Vehicles generated: yes
- Final total vehicles: 4
- Max stopped vehicles: 0
- Generated config loaded: yes
- Source INPX timestamp unchanged: yes

Observed Vissim output included:

```text
CONFIG_LOADED=...\evaluation\generated\global_state_config.vbs
STAGE=NET_LOADED
LINKS=108
VEHICLE_INPUTS=9
GLOBAL_STATE_GROUPS=urban(5,6,7,8,11,12,13,14,19,20,23,24,27,28),freeway(33,34),ramp(25,26,31,32),boundary(1,2,3,4,9,10,15,16,17,18,21,22,29,30)
FREEWAY_INPUT_LINKS=33,34
STAGE=SIM_DONE
SIM_SEC=30
SIM_STEPS=30
```

## Remaining limitations

These are expected and do not block detector installation:

- Route decisions and static routes are still absent.
- Signal controllers and signal heads are still absent.
- Ramp metering and VSL actuation are not installed yet.
- The controller is still observe-only (`GLOBAL_NOOP`).
- Hysteresis/congestion evaluation requires later demand and routing work.

## Detector installation decision

Proceed with detector installation next, with this guardrail:

1. Create or overwrite only an evaluation copy, e.g. `modi_eval_control.inpx/.layx`.
2. Add detector/DCP/QC expansions to that copy.
3. Rerun inventory on the evaluation copy.
4. Rerun low-demand smoke on the evaluation copy.
5. Confirm the source `modi.inpx` timestamp remains unchanged.
