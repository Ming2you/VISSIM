# S1 signal / SC12 independent review

## Verdicts

- Spec verdict: FAIL
- Quality verdict: FAIL

## Critical findings

1. **Headless selected controllers are silently reclassified as `model_excluded`, which opens a false-PASS path instead of failing closed.**  
   In [compiler.py](C:\tmp\vissim-pstack-controller\plant\src\vissim_strict\compiler.py) at lines 103-111, any controller with `supplyFile2` and zero signal-head references becomes `model_excluded`; then lines 174-175 skip compilation with no error. That is broader than the stated invariant that the current network has exactly one excluded controller (`SC9004`). If head provenance regresses for any real model SC, this code converts missing evidence into exclusion instead of `FAIL`/`NOT_EVALUATED`. The only coverage here is the real-network count assertion in [test_vissim_strict_compiler.py](C:\tmp\vissim-pstack-controller\plant\tests\test_vissim_strict_compiler.py) lines 26-59; there is no negative test proving that a non-`9004` headless controller is rejected.

2. **The SC12 validator can PASS while connector-lane or downstream movement semantics are corrupted.**  
   [validate_sc12_shared_lane.py](C:\tmp\vissim-pstack-controller\scripts\validate_sc12_shared_lane.py) lines 27-32 encode expectations only as source-lane ID lists, and lines 247-256 compare only `actual_from_lane_ids`. The code never validates expected `connector_lane_id` membership/count or `to_lane_id` destination semantics, even though S1-3 requires exact connector lane-range reconstruction and real movement composition. A malformed artifact that preserves the same upstream lane IDs but rewires connector-lane IDs or downstream lanes would still PASS. Tests in [test_validate_sc12_shared_lane.py](C:\tmp\vissim-pstack-controller\scripts\tests\test_validate_sc12_shared_lane.py) lines 84-100 and 136-149 only exercise `from_lane_id` mutations, so this false-PASS path is unpinned.

## Important findings

1. **`signal-reference-v2.1` still does not preserve the actual active-program schedule required by S1-2.**  
   [compiler.py](C:\tmp\vissim-pstack-controller\plant\src\vissim_strict\compiler.py) lines 142-145 reduce the INPX to a single global `present_in_inpx` / `absent_in_inpx` flag, and lines 243-248 plus 274-276 record only static `progNo` provenance. The artifact does not serialize per-controller `dailyProgLists`, any time-indexed schedule expansion, runtime start-time binding, or readback provenance. That means downstream consumers cannot reconstruct the exact active-program schedule from the compiler artifact alone, which falls short of the S1-2 requirement to preserve the time-indexed active program without fallback. Coverage in [test_vissim_strict_compiler.py](C:\tmp\vissim-pstack-controller\plant\tests\test_vissim_strict_compiler.py) lines 74-80 only checks the current network's `absent_in_inpx` case.

## Minor findings

1. **`sample_dimensions.target_connectors` changes meaning when evidence is missing.**  
   In [validate_sc12_shared_lane.py](C:\tmp\vissim-pstack-controller\scripts\validate_sc12_shared_lane.py) lines 465-469, `target_connectors` is populated with `len(source_maps)`, which is the number of connectors successfully read, not the fixed target set size. In incomplete cases the artifact reports fewer "target" connectors rather than four expected targets, which is small but schema-awkward for deterministic machine consumption.
