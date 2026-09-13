# Startup demand / GUI independent review

**Six fake-object regressions PASS (10 short cscript cases, 1.219 s), source unchanged at `30a279cbcc111a7374af023decf65456ccf6c46e005dc7ab6639bc8b5f69cdb0`.** No VISSIM was created, simulation step executed, or production file edited by this reviewer. Parent owns the actual startup test.

The original network and all three flat experimental arms contain identical vehicle-input data: **34 inputs × 6 intervals, all 204 `cont=false`**. Input1097, link256, has volumes `112,160,168,144,112,80`; its role is `urban_input`, profile multiplier is1 and run scale is1. Therefore interval `1-5` is expected to be112. The preserved r03 line is:

```text
ERROR=DEMAND_INTERVAL_SET_FAILED no=1097 time_int=1-5 target=0.000000 err=
```

The zero target is consistent with an earlier failed Volume read, but the old logging cannot uniquely establish that cause. **Do not read this as an intended same-value zero assignment.**

## What the fake tests establish

The old source is read byte-exactly from `fixtures/startup_gui_original_vbs_v1.zip` (original VBS SHA71ec5f8d…). The actual old/new demand functions and unchanged QuickMode/SuspendUpdateGUI block are extracted into scripts whose objects are implemented entirely in VBScript. The normal fixture uses input1097's six volumes and factors1 and0.8333.

- Every normal `TimeInt`/`Volume` read and Volume write occurs in the same order with identical targets, readbacks and totals. All six intervals are still written, including equal values. No `Cont` setter or same-value skip was added.
- The unchanged GUI block precedes the first demand write in the new startup order; in the old order it follows the demand writes. This proves the call order, not native GUI performance.
- An original Volume read exception is swallowed by `SafeAtt`, becomes empty, and `ToDbl` converts it to0. The old routine then attempts an unintended zero write. This path is reproduced.
- The new strict helper rejects a before-read exception **before writing that interval**; after-read, empty and nonnumeric failures also stop. Setter and read exceptions retain their immediate number/description (sentinels513/514/515).
- **Correction to the initial diagnostic hypothesis:** a normal setter error description survives `Num(target)` in the actual old routine. The native blank `err=` is not explained by Num in this test. The preserved intermediate failed assertion records this correction; production was not changed to fit it.

## What equal-value writes do not prove

PTV documents `Cont` as inheriting preceding volume and joining interval settings; independently editable intervals have it disabled. This explains why the present XML is expected to permit independent writes, but does not promise that calling the COM Volume setter with the same value preserves every internal state. [PTV Vissim2020 vehicle-input attributes](https://cgi.ptvgroup.com/vision-help/VISSIM_2020_ENG/Content/5_Netzbearbeiten/Fzgverkehr_Zufluss_Attr.htm)

The historical `probe_vehicle_input_time_interval_api.vbs` reads indexed/subcontainer Volume and Cont, then doubles input1099's Volume and checks Volume readback. It does **not** compare Cont/VolType/VehComp before and after that setter, test equal-value writes, or inspect internal stochastic scheduling. Neither a change nor preservation of those properties is established by that probe. The current patch retains the old writes, so it does not depend on an unproven skip-equivalence assumption. If parent later evaluates skipping equal values, native before/after `TimeInt,Volume,Cont,VolType,VehComp` and a matched physical run remain the appropriate separate check.

The GUI block still uses the existing optional-error behavior, so a `GUI_SUSPEND_REQUESTED` stage is a request marker, not an independently verified successful native suspension. New demand read/write stage observations should distinguish the actual startup fault without changing demanded values.

## Evidence and limits

- `startup_demand_gui_review.json`: exact source/input/arm hashes and complete input rows, actual failure line, limits and test history.
- `startup_demand_gui_validation_20260910T073057861796Z/`: successful evidence JSON, all generated fake scripts and raw outputs.
- `startup_demand_gui_validation_20260910T072901808570Z/`: initial sandbox denied Windows Script Host settings before script execution.
- `startup_demand_gui_validation_20260910T073004081852Z/`: five passing tests plus the disproved Num-error-clearing expectation, retained unchanged.
- `test_startup_demand_gui.py`: source-pinned six-test regression. It does not claim full VBS compilation or real LoadNet/startup validation.

All test cscript children were awaited to termination. No further cscript/model/COM execution is pending from this reviewer.
