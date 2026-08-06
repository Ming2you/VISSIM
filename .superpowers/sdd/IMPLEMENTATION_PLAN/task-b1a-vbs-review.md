# B1a VBS capture independent review

## Verdict

**FAIL**

Counts: **Critical 3 / Important 2 / Minor 1**

Live supported-version VISSIM COM: **NOT_EVALUATED**

## Findings

### Critical 1 - Stepwise recurring capture time is wrong

RunStepwiseMode calls RunControllerDecision stepNo before
Vissim.Simulation.RunSingleStep (VBS lines 427-434). VISSIM is still at
stepNo - 1, but WriteStateJson and ReadVerifiedVehicleTables require both COM
SimSec reads to equal stepNo (lines 3016-3025). The first recurring forced-stepwise
decision therefore exits 13 with capture_time_mismatch.

Reproducer:

    $s=Get-Content -Raw scripts\run_real_world_stackelberg_controller.vbs
    $b=[regex]::Match($s,'(?ms)^Sub RunStepwiseMode\(\).*?^End Sub$').Value
    $d=$b.IndexOf('RunControllerDecision stepNo')
    $r=$b.IndexOf('Vissim.Simulation.RunSingleStep',$b.IndexOf('For stepNo'))
    "decision_precedes_step=$($d -lt $r)"; if($d -lt $r){exit 23}

Observed: decision_precedes_step=True, exit 23. The tests do not trace run-mode
callers.

### Critical 2 - vehicle_records is emitted at the wrong JSON path

The reviewed core requirement names local_observation.vehicle_records
(task-b1a-brief-review.md:101); the repaired brief retains
local_observation.schema_version=2 and adds the nested envelope
(task-b1a-brief.md:67-71 and task-b1a-brief-rereview.md:28).

WriteStateJson closes local_observation at line 1511 and only then calls
WriteVehicleRecordsEnvelope (lines 1512-1514); the helper emits root
vehicle_records at line 1540. The behavior tests assert the same root shape at
test_b1a_vbs_capture_helpers_behavior.py:222 and :238. Core projector and manifest
code also import state.get("vehicle_records"), so the slices agree with each other
but not with the brief.

Reproducer:

    $s=Get-Content -Raw scripts\run_real_world_stackelberg_controller.vbs
    $b=[regex]::Match($s,'(?ms)^Sub WriteStateJson\(.*?^End Sub$').Value
    $o=$b.IndexOf('ts.WriteLine "  ""local_observation"": {"')
    $c=$b.IndexOf('ts.WriteLine "  },"',$o)
    $e=$b.IndexOf('WriteVehicleRecordsEnvelope ts')
    "nested=$($e -gt $o -and $e -lt $c)"; if(-not ($e -gt $o -and $e -lt $c)){exit 24}

Observed: nested=False, exit 24.

### Critical 3 - Actual VBS output is rejected by the core projector

VBS adds fullLinkStoppedCounts keys only for stopped vehicles (line 1834), so
WriteB1aCountMap omits counted links having zero stopped vehicles. The core
normalize_vehicle_records instead reconstructs an explicit zero stopped key for
every key in full_network_link_counts
(physical_projection.py:905-910) and requires exact equality.

I executed the production VBS helper emitter and passed its parsed envelope directly
to normalize_vehicle_records:

    & 'C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -B C:\tmp\b1a_vbs_core_parity.py

Observed:

    vbs_exit=0
    declared_counts={'1': 1, '1220012103': 1}
    declared_stopped={'1': 1}
    core_result=REJECT aggregate_mismatch
    reconstructed_stopped={'1': 1, '1220012103': 0}

Thus a normal mixed moving/stopped VBS snapshot cannot reach core projection PASS.
The helper test only parses its JSON and never performs this interface check.

### Important 1 - Capture failure counters are unreachable

RecordVehicleCaptureFailure increments comFailures at line 3121. Each caller then
increments observationFailures and immediately WScript.Quit 13 at lines 1470-1474
or 1624-1628. OBSERVATION_FAILURES and COM_FAILURES are printed only at lines 282
and 293, so every B1a capture failure exits without externally publishing either
counter. Publication of a new state is prevented, but counter evidence is
missing/undefined.

The end-of-run max(comFailures, signalFailures + observationFailures) is also not
an exact event count for independent generic COM and signal failures. The runner
test checks source tokens, not failure-path reachability.

### Important 2 - The B1a suite has load-bearing false PASSes

The static suite checks token presence, while the behavior harness never executes
ReadVerifiedVehicleTables or ScanVehicleState. The complete 7-test suite remained
green under each mutation:

- unconditional Exit Function at the start of ReadVerifiedVehicleTables;
- a second GetMultiAttValues("No") within the capture bracket;
- recordLinkNos(recordIndex) = laneNo;
- stopped-count map keyed by laneNo;
- removal of the double nonfinite guard;
- removal of decimal-separator normalization on the host default locale.

Reproducer examples:

    $py='C:\Users\alsrj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    & $py -B C:\tmp\b1a_mutation_review.py --full dead_reader_early_exit
    & $py -B C:\tmp\b1a_mutation_review.py --full duplicate_No_table_read
    & $py -B C:\tmp\b1a_mutation_review.py --full record_link_uses_lane
    & $py -B C:\tmp\b1a_mutation_review.py --full stopped_map_key_uses_lane
    & $py -B C:\tmp\b1a_mutation_review.py --full finite_guard_removed
    & $py -B C:\tmp\b1a_mutation_review.py --full locale_normalization_removed

Each observed 7 tests OK and FALSE_PASS. Current locale code separately passed an
added German SetLocale(1031) execution, so this is a proof gap, not a current
locale implementation failure.

### Minor 1 - Helper test fails dotted-module import

The helper uses:

    from test_b1a_vbs_verified_capture_static import SOURCE, class_body, procedure

This works under unittest discovery because scripts/tests is inserted on sys.path,
but fails as a dotted module:

    python -B -m unittest scripts.tests.test_b1a_vbs_capture_helpers_behavior -v

Observed: ModuleNotFoundError: No module named
test_b1a_vbs_verified_capture_static. The test is therefore runner-shape dependent.

## Verified areas

- Count/SimSec/No/Lane/Pos/Speed/Count/SimSec bracketing and no intervening
  simulation method are correct inside ReadVerifiedVehicleTables.
- Actual 2-D lower/upper bounds, two-column shape, matching bounds, all four COM
  keys, key=No, and snapshot uniqueness are checked.
- Empty collection handling proves both scalar counts are zero.
- The called Lane parser implements the complete anchored ASCII grammar and
  positive 32-bit bounds.
- Current Variant rejection, nonfinite guards, position tolerance, precision, and
  locale conversion are correct.
- Full control-character JSON escaping and UTF-8 BOM removal passed executable VBS
  helper tests.
- stopped is based on unrounded speed < 1.0; equality is moving.
- Record output is linear with bounded per-record string construction; the 20,000
  record qualification passed.
- Valid-row legacy masked aggregates and their explicit zero-key policy are
  unchanged.

## Test results

- B1a VBS static/helper: **7/7 PASS** outside sandbox.
- Added German comma-locale helper: **1/1 PASS**.
- Actual VBS envelope to core normalize parity: **FAIL**, reproduced above.
- Runner: **11/11 PASS**.
- Auditor: **31/31 PASS**.
- Adapter: **2/2 PASS**.
- Direct whole-file cscript was not repeated because the safety gate rejected it
  as potentially starting VISSIM. COM-free extracted VBS helpers did execute.
- Live VISSIM COM remains **NOT_EVALUATED**.

## Disposition

Do not approve. Fix the stepwise timestamp, required envelope location, stopped-map
zero-key parity, reachable failure summaries, and mutation-resistant called-path
tests before rereview.
