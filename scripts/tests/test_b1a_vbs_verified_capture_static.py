from __future__ import annotations

import re
import unittest
from pathlib import Path


VBS_PATH = Path(__file__).resolve().parents[1] / "run_real_world_stackelberg_controller.vbs"
SOURCE = VBS_PATH.read_text(encoding="utf-8")


def _without_vbs_comment(line: str) -> str:
    in_string = False
    index = 0
    while index < len(line):
        char = line[index]
        if char == '"':
            if in_string and index + 1 < len(line) and line[index + 1] == '"':
                index += 2
                continue
            in_string = not in_string
        elif char == "'" and not in_string:
            return line[:index]
        index += 1
    return line


def _code_shape(code: str) -> str:
    shaped: list[str] = []
    in_string = False
    index = 0
    while index < len(code):
        char = code[index]
        if char == '"':
            if in_string and index + 1 < len(code) and code[index + 1] == '"':
                shaped.extend((" ", " "))
                index += 2
                continue
            in_string = not in_string
            shaped.append(" ")
        elif in_string:
            shaped.append(" ")
        else:
            shaped.append(char.lower())
        index += 1
    return " ".join("".join(shaped).split())


def _procedure_matches(source: str, name: str) -> list[str]:
    lines = source.splitlines(keepends=True)
    matches: list[str] = []
    declaration = re.compile(
        rf"^(?:public\s+|private\s+)?(sub|function)\s+{re.escape(name)}\b",
        re.IGNORECASE,
    )
    any_declaration = re.compile(
        r"^(?:public\s+|private\s+)?(sub|function)\s+([a-z_]\w*)\b",
        re.IGNORECASE,
    )
    index = 0
    while index < len(lines):
        code = _code_shape(_without_vbs_comment(lines[index])).strip()
        match = declaration.match(code)
        if not match:
            index += 1
            continue
        kind = match.group(1).lower()
        end_pattern = re.compile(rf"^end\s+{kind}$", re.IGNORECASE)
        end_index = index + 1
        while end_index < len(lines):
            end_code = _code_shape(_without_vbs_comment(lines[end_index])).strip()
            if any_declaration.match(end_code):
                raise AssertionError(f"unterminated VBS procedure {name}")
            if end_pattern.match(end_code):
                matches.append("".join(lines[index : end_index + 1]))
                index = end_index
                break
            end_index += 1
        else:
            raise AssertionError(f"unterminated VBS procedure {name}")
        index += 1
    return matches


def procedure(source: str, name: str) -> str:
    matches = _procedure_matches(source, name)
    if not matches:
        raise AssertionError(f"missing VBS procedure {name}")
    if len(matches) != 1:
        raise AssertionError(f"expected one VBS procedure {name}, found {len(matches)}")
    return matches[0]


def _logical_statements(body: str) -> list[str]:
    statements: list[str] = []
    pending: list[str] = []
    for physical_line in body.splitlines():
        code = _without_vbs_comment(physical_line).rstrip()
        continuation = bool(re.search(r"\s_\s*$", _code_shape(code)))
        if continuation:
            code = re.sub(r"\s_\s*$", "", code)
        pending.append(code.strip())
        if not continuation:
            statement = " ".join(part for part in pending if part)
            if statement:
                statements.append(statement)
            pending = []
    if pending:
        statements.append(" ".join(part for part in pending if part))
    return statements


def reachable_statements(source: str, name: str) -> list[str]:
    statements = _logical_statements(procedure(source, name))
    reachable: list[str] = []
    frames: list[dict[str, object]] = []
    terminated = False

    def current_active() -> bool:
        return not terminated and (not frames or bool(frames[-1]["active"]))

    for statement in statements:
        shape = _code_shape(statement)

        close_kind = None
        if shape == "end if":
            close_kind = "if"
        elif shape == "end select":
            close_kind = "select"
        elif shape == "end with":
            close_kind = "with"
        elif re.match(r"^next(?:\s|$)", shape):
            close_kind = "for"
        elif re.match(r"^loop(?:\s|$)", shape):
            close_kind = "do"
        elif shape == "wend":
            close_kind = "while"

        if close_kind is not None:
            if not frames or frames[-1]["kind"] != close_kind:
                raise AssertionError(f"unbalanced {close_kind} block in VBS procedure {name}")
            frames.pop()
            if current_active():
                reachable.append(statement)
            continue

        if re.match(r"^else(?:if\b.*\bthen)?$", shape):
            if not frames or frames[-1]["kind"] != "if":
                raise AssertionError(f"unbalanced Else in VBS procedure {name}")
            frame = frames[-1]
            parent_active = bool(frame["parent_active"])
            condition = frame["condition"]
            if shape == "else":
                frame["active"] = parent_active and condition is not True
            else:
                frame["active"] = parent_active and condition is not True
                frame["condition"] = None
            if current_active():
                reachable.append(statement)
            continue

        active = current_active()
        if active:
            reachable.append(statement)

        block_kind = None
        condition: bool | None = None
        if_match = re.match(r"^if\s+(.+)\s+then$", shape)
        if if_match:
            block_kind = "if"
            expression = if_match.group(1).strip()
            if expression in {"false", "not true"}:
                condition = False
            elif expression in {"true", "not false"}:
                condition = True
        elif re.match(r"^select\s+case\b", shape):
            block_kind = "select"
        elif re.match(r"^for(?:\s+each)?\b", shape):
            block_kind = "for"
        elif re.match(r"^do(?:\s|$)", shape):
            block_kind = "do"
        elif re.match(r"^while\b", shape):
            block_kind = "while"
        elif re.match(r"^with\b", shape):
            block_kind = "with"

        if block_kind is not None:
            frames.append(
                {
                    "kind": block_kind,
                    "parent_active": active,
                    "condition": condition,
                    "active": active and condition is not False,
                }
            )
        elif active and not frames and shape in {"exit function", "exit sub"}:
            terminated = True

    if frames:
        raise AssertionError(f"unclosed control-flow block in VBS procedure {name}")
    return reachable


def reachable_procedure(source: str, name: str) -> str:
    return "\n".join(reachable_statements(source, name))


def class_body(source: str, name: str) -> str:
    match = re.search(
        rf"(?ims)^Class\s+{re.escape(name)}\s*$.*?^End Class\s*$",
        source,
    )
    if not match:
        raise AssertionError(f"missing VBS class {name}")
    return match.group(0)


def assert_called_capture_contract(source: str) -> None:
    writer = reachable_procedure(source, "WriteStateJson")
    scan = reachable_procedure(source, "ScanVehicleState")
    reader = reachable_procedure(source, "ReadVerifiedVehicleTables")
    envelope = reachable_procedure(source, "WriteVehicleRecordsEnvelope")

    assert re.search(r"(?i)\bScanVehicleState\s+simSec\b", writer)
    assert re.search(r"(?i)\bWriteVehicleRecordsEnvelope\s+ts\b", writer)
    assert re.search(r"(?i)\bok\s*=\s*ReadVerifiedVehicleTables\(", scan)
    assert re.search(r"(?i)\bParseB1aLaneId\(", scan)
    assert re.search(r"(?i)\bTryPositiveLongVariant\(noArray\(row, keyCol\)", scan)
    assert "noKey <> laneKey" in scan
    assert "noKey <> posKey" in scan
    assert "noKey <> speedKey" in scan
    # GetMultiAttValues 의 key 열은 컨테이너의 **순차 행 인덱스**이지 객체 키가 아니다.
    # 차량번호와 같다고 가정하면 차량이 네트워크를 드나드는 순간 오탐한다 -
    # 2026-08-07 실 런에서 sim_sec 1 은 veh_no 1..6 으로 통과했고 sim_sec 90 의 row 7 에서
    # com_row_key_mismatch 로 매 시도가 죽었다. 요구할 것은 네 배열의 행 정렬뿐이고,
    # 차량번호는 value 열에서 읽어 아래 snapshotIds 로 유일성을 본다.
    assert "noKey <> vehNo" not in scan
    assert re.search(r"(?i)\bTryPositiveLongVariant\(noArray\(row, valueCol\), vehNo\)", scan)
    assert "snapshotIds.Exists(key)" in scan
    assert "recordVehNos(recordIndex) = vehNo" in scan
    assert "recordLinkNos(recordIndex) = linkNo" in scan
    assert "recordLaneNos(recordIndex) = laneNo" in scan
    assert "isStopped = (speed < B1A_STOPPED_THRESHOLD_KPH)" in scan
    assert "AddDictNumber fullLinkCounts, key, 1.0" in scan
    assert "If Not fullLinkStoppedCounts.Exists(key) Then fullLinkStoppedCounts.Add key, 0.0" in scan
    scan_shapes = [_code_shape(item) for item in reachable_statements(source, "ScanVehicleState")]
    stopped_updates = [
        item for item in scan_shapes
        if re.search(r"\badddictnumber\s+fulllinkstoppedcounts\s*,", item)
    ]
    assert stopped_updates == [
        "if isstopped then adddictnumber fulllinkstoppedcounts, key, 1.0"
    ]
    assert "B1aCountMapTotal(fullLinkCounts) <> total" in scan
    assert "B1aCountMapTotal(fullLinkStoppedCounts) <> stopped" in scan

    ordered_reads = [
        'rawCountBefore = Vissim.Net.Vehicles.Count',
        'rawTimeBefore = Vissim.Simulation.AttValue("SimSec")',
        'GetMultiAttValues("No")',
        'GetMultiAttValues("Lane")',
        'GetMultiAttValues("Pos")',
        'GetMultiAttValues("Speed")',
        'rawCountAfter = Vissim.Net.Vehicles.Count',
        'rawTimeAfter = Vissim.Simulation.AttValue("SimSec")',
    ]
    assert all(token in reader for token in ordered_reads)
    positions = [reader.index(token) for token in ordered_reads]
    assert positions == sorted(positions)
    assert reader.index(ordered_reads[0]) < reader.index("Exit Function")
    for attribute in ("No", "Lane", "Pos", "Speed"):
        assert reader.count(f'GetMultiAttValues("{attribute}")') == 1
    assert not re.search(r"(?i)Simulation\.(RunSingleStep|RunContinuous|RunMultiRun)", reader)
    assert "collectionCountBefore <> collectionCountAfter" in reader
    assert "captureSimSecBefore <> expectedTime" in reader
    assert "captureSimSecAfter <> expectedTime" in reader
    assert "TryExact2DTableBounds(noArray" in reader
    assert "table_bounds_mismatch" in reader
    assert "row_count_mismatch" in reader
    assert "IsB1aEmptyTableResult(noArray)" in reader
    assert "nonempty_table_for_zero_collection" in reader

    fields = (
        "schema_version",
        "complete",
        "paused_at_sim_sec",
        "capture_sim_sec_before",
        "capture_sim_sec_after",
        "source_attributes",
        "stopped_threshold_kph",
        "collection_count_before",
        "collection_count_after",
        "record_count",
        "unobservable_count",
        "external_source_count",
        "full_network_link_counts",
        "full_network_link_stopped_counts",
        "records",
    )
    for field in fields:
        assert f'""{field}""' in envelope or f'"{field}"' in envelope
    assert '""vissim-vehicle-records-v2.1""' in envelope
    assert "JsonDoubleInvariant(recordPositions(i))" in envelope
    assert "JsonDoubleInvariant(recordSpeeds(i))" in envelope
    finite = reachable_procedure(source, "TryB1aFiniteDouble")
    finite_shapes = [_code_shape(item) for item in reachable_statements(source, "TryB1aFiniteDouble")]
    probe = "probe = parsed * 0.0"
    guard = "if parsed <> parsed or probe <> probe then exit function"
    success = "tryb1afinitedouble = true"
    assert finite_shapes.count(probe) == 1
    assert finite_shapes.count(guard) == 1
    assert finite_shapes.count(success) == 1
    assert finite_shapes.index(probe) < finite_shapes.index(guard) < finite_shapes.index(success)
    assert "If parsed <> parsed Or probe <> probe Then Exit Function" in finite
    formatter = reachable_procedure(source, "JsonDoubleInvariant")
    assert 'If JSON_DECIMAL_SEPARATOR <> "." Then text = Replace(text, JSON_DECIMAL_SEPARATOR, ".")' in formatter


class B1aVbsVerifiedCaptureStaticTests(unittest.TestCase):
    def test_called_path_satisfies_capture_contract(self) -> None:
        assert_called_capture_contract(SOURCE)

    def test_dead_parser_decoy_cannot_create_a_false_pass(self) -> None:
        mutant = SOURCE.replace(
            "If Not ParseB1aLaneId(laneArray(row, valueCol), linkNo, laneNo) Then",
            "If Not DeadLaneParser(laneArray(row, valueCol), linkNo, laneNo) Then",
            1,
        )
        mutant += '\nFunction DeadLaneParser(value, linkNo, laneNo)\n'
        mutant += "' ParseB1aLaneId GetMultiAttValues(\"Lane\") vehicle_records\n"
        mutant += "DeadLaneParser = True\nEnd Function\n"
        with self.assertRaises(AssertionError):
            assert_called_capture_contract(mutant)

    def test_dead_reader_decoy_cannot_create_a_false_pass(self) -> None:
        mutant = SOURCE.replace(
            "ok = ReadVerifiedVehicleTables(expectedSimSec,",
            "ok = DeadVerifiedVehicleTables(expectedSimSec,",
            1,
        )
        mutant += "\n' ReadVerifiedVehicleTables Count SimSec No Lane Pos Speed\n"
        with self.assertRaises(AssertionError):
            assert_called_capture_contract(mutant)

    def test_listed_load_bearing_mutations_are_rejected(self) -> None:
        mutations = {
            "dead_reader_early_exit": SOURCE.replace(
                "    ReadVerifiedVehicleTables = False\n",
                "    ReadVerifiedVehicleTables = False\n    Exit Function\n",
                1,
            ),
            "duplicate_no_read": SOURCE.replace(
                '    noArray = Vissim.Net.Vehicles.GetMultiAttValues("No")\n',
                '    noArray = Vissim.Net.Vehicles.GetMultiAttValues("No")\n'
                '    noArray = Vissim.Net.Vehicles.GetMultiAttValues("No")\n',
                1,
            ),
            "record_link_uses_lane": SOURCE.replace(
                "        recordLinkNos(recordIndex) = linkNo\n",
                "        recordLinkNos(recordIndex) = laneNo\n",
                1,
            ),
            "stopped_map_uses_lane": SOURCE.replace(
                "If isStopped Then AddDictNumber fullLinkStoppedCounts, key, 1.0",
                "If isStopped Then AddDictNumber fullLinkStoppedCounts, CStr(laneNo), 1.0",
                1,
            ),
            "finite_guard_removed": SOURCE.replace(
                "    If parsed <> parsed Or probe <> probe Then Exit Function\n",
                "",
                1,
            ),
            "locale_normalization_removed": SOURCE.replace(
                '    If JSON_DECIMAL_SEPARATOR <> "." Then text = Replace(text, JSON_DECIMAL_SEPARATOR, ".")\n',
                "",
                1,
            ),
        }
        for name, mutant in mutations.items():
            with self.subTest(name=name), self.assertRaises(AssertionError):
                assert_called_capture_contract(mutant)

    def test_dead_control_flow_decoys_are_rejected(self) -> None:
        mutations = {
            "stopped_map_dead_decoy": SOURCE.replace(
                "        If isStopped Then AddDictNumber fullLinkStoppedCounts, key, 1.0\n",
                "        If False Then\n"
                "            If isStopped Then AddDictNumber fullLinkStoppedCounts, key, 1.0\n"
                "        End If\n"
                "        If isStopped Then AddDictNumber fullLinkStoppedCounts, CStr(laneNo), 1.0\n",
                1,
            ),
            "finite_guard_dead_decoy": SOURCE.replace(
                "    If parsed <> parsed Or probe <> probe Then Exit Function\n",
                "    If False Then\n"
                "        If parsed <> parsed Or probe <> probe Then Exit Function\n"
                "    End If\n",
                1,
            ),
        }
        for name, mutant in mutations.items():
            self.assertNotEqual(mutant, SOURCE, name)
            with self.subTest(name=name), self.assertRaises(AssertionError):
                assert_called_capture_contract(mutant)

    def test_all_run_modes_capture_after_reaching_the_labeled_epoch(self) -> None:
        stepwise = procedure(SOURCE, "RunStepwiseMode")
        self.assertLess(stepwise.index("Vissim.Simulation.RunSingleStep"), stepwise.index("RunControllerDecision 1"))
        recurring = stepwise[stepwise.index("For stepNo = 2") :]
        self.assertLess(recurring.index("Vissim.Simulation.RunSingleStep"), recurring.index("RunControllerDecision stepNo"))
        self.assertLess(recurring.index("RunControllerDecision stepNo"), recurring.index("ApplyRuntimeSignals stepNo"))

        continuous = procedure(SOURCE, "RunContinuousStaticMode")
        self.assertLess(continuous.index("Vissim.Simulation.RunSingleStep"), continuous.index("RunControllerDecision 1"))
        continuous_loop = continuous[continuous.index("Do While") :]
        self.assertLess(continuous_loop.index("RunContinuousTo CLng(targetSec)"), continuous_loop.index("RunControllerDecision CLng(currentSec)"))

        event = procedure(SOURCE, "RunEventContinuousMode")
        self.assertLess(event.index("Vissim.Simulation.RunSingleStep"), event.index("RunControllerDecision 1"))
        event_loop = event[event.index("Do While") :]
        self.assertLess(event_loop.index("RunContinuousTo CLng(targetSec)"), event_loop.index("RunControllerDecision CLng(currentSec)"))

        decision = procedure(SOURCE, "RunControllerDecision")
        self.assertIn("WriteStateJson simSec, stateJsonPath", decision)
        self.assertIn('"action_" & Pad6(simSec)', decision)

    def test_vehicle_records_normatively_remains_a_root_sibling(self) -> None:
        writer = procedure(SOURCE, "WriteStateJson")
        local_open = writer.index('ts.WriteLine "  ""local_observation"": {"')
        local_close = writer.index('ts.WriteLine "  },"', local_open)
        envelope_call = writer.index("WriteVehicleRecordsEnvelope ts")
        self.assertLess(local_open, local_close)
        self.assertLess(local_close, envelope_call)

    def test_failure_precedes_any_state_publication(self) -> None:
        writer = procedure(SOURCE, "WriteStateJson")
        self.assertLess(writer.index("If Not scanOk Then"), writer.index("EnsureParentFolder tempPath"))
        failure = writer[writer.index("If Not scanOk Then") : writer.index("End If", writer.index("If Not scanOk Then"))]
        self.assertIn("AbortVehicleObservation simSec", failure)
        logger = procedure(SOURCE, "LogStateCsv")
        self.assertIn("AbortVehicleObservation simSec", logger)
        abort = procedure(SOURCE, "AbortVehicleObservation")
        ordered = [
            "observationFailures = observationFailures + 1",
            'WScript.Echo "OBSERVATION_FAILURES=" & CStr(observationFailures)',
            'WScript.Echo "COM_FAILURES=" & CStr(comFailures)',
            "WScript.Quit 13",
        ]
        positions = [abort.index(token) for token in ordered]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn("comFailures = comFailures +", abort)
        capture_failure = procedure(SOURCE, "RecordVehicleCaptureFailure")
        self.assertEqual(capture_failure.count("comFailures = comFailures + 1"), 1)
        self.assertNotIn("If comFailures < signalFailures + observationFailures Then", SOURCE)

    def test_streaming_and_escape_helpers_are_on_the_emission_path(self) -> None:
        envelope = procedure(SOURCE, "WriteVehicleRecordsEnvelope")
        writer_class = class_body(SOURCE, "Utf8LineWriter")
        escape = procedure(SOURCE, "JsonEscape")
        self.assertIn("For i = 0 To collectionCountBefore - 1", envelope)
        self.assertIn("textStream.WriteText", writer_class)
        self.assertNotIn("buf = buf &", writer_class)
        self.assertIn("textStream.Position = 3", writer_class)
        for token in (r'"\b"', r'"\t"', r'"\n"', r'"\f"', r'"\r"', r'"\u"'):
            self.assertIn(token, escape)
        self.assertIn("ReDim pieces(Len(text) - 1)", escape)

    def test_legacy_masked_observation_contract_remains_separate(self) -> None:
        writer = procedure(SOURCE, "WriteStateJson")
        self.assertIn('""schema_version"": 2', writer)
        self.assertIn('""global_vehicle_scan_masked"": true', writer)
        self.assertIn("LocalObservationLinkCountsJson(localCounts)", writer)
        self.assertIn("WriteVehicleRecordsEnvelope", writer)

    def test_required_mode_wraps_called_capture_in_atomic_sidecar_transaction(self) -> None:
        writer = procedure(SOURCE, "WriteStateJson")
        ordered = [
            "ValidateB1aCaptureTime simSec",
            "captureStartNs = ReadRequiredMonotonicClock()",
            "tempPath = UniqueSiblingPath(finalPath, \"state\")",
            "ScanVehicleState simSec",
            "ts.TargetPath = tempPath",
            "ValidateB1aStateRunBinding tempPath, simSec, True",
            "fso.MoveFile tempPath, finalPath",
            "ValidateB1aStateRunBinding finalPath, simSec, False",
            "captureEndNs = ReadRequiredMonotonicClock()",
            "PublishB1aVehicleCaptureEvidence simSec, finalPath, captureStartNs, captureEndNs",
        ]
        positions = [writer.index(token) for token in ordered]
        self.assertEqual(positions, sorted(positions))
        provenance = procedure(SOURCE, "WriteB1aStateRunProvenance")
        self.assertIn('If b1aRequired Then', provenance)
        self.assertIn('""manifest_sha256"": """ & JsonEscape(runManifestSha256)', provenance)
        self.assertIn('""run_provenance"": {""run_id"": """ & JsonEscape(runId) & """, ""manifest_path"": """ & JsonEscape(runManifestPath) & """},', provenance)
        self.assertNotIn("projection_timing_v2_1", SOURCE)
        self.assertNotIn("--projection-only", writer)

    def test_required_mode_uses_pinned_state_manifest_builder_and_monotonic_helper(self) -> None:
        startup = procedure(SOURCE, "ValidateB1aRequiredStartup")
        binding = procedure(SOURCE, "ValidateB1aRunBinding")
        state_binding = procedure(SOURCE, "ValidateB1aStateRunBinding")
        helper = procedure(SOURCE, "ReadRequiredMonotonicClock")
        publisher = procedure(SOURCE, "PublishB1aVehicleCaptureEvidence")
        timeout_runner = procedure(SOURCE, "RunCapture3Timeout")
        self.assertIn("stateManifestBuilderPath", startup)
        self.assertIn("monotonicClockHelperPath", startup)
        self.assertIn("--validate-run-binding", binding)
        self.assertIn("--capture-time", binding)
        self.assertIn("RunCapture3Timeout(cmd, B1A_PYTHON_HELPER_TIMEOUT_SEC", binding)
        self.assertIn("IsB1aPassLine(outText, \"status=PASS run_id=\")", binding)
        self.assertIn("--validate-state-run-binding", state_binding)
        self.assertIn("--state", state_binding)
        self.assertIn("CleanupUniqueB1aTemp statePath", state_binding)
        self.assertIn("IsB1aPassLine(outText, \"status=PASS state=\")", state_binding)
        self.assertIn("RunCapture3Timeout(cmd, 5", helper)
        self.assertIn("python_perf_counter_ns=", helper)
        self.assertIn("--produce-vehicle-capture", publisher)
        self.assertIn("RunCapture3Timeout(cmd, B1A_PYTHON_HELPER_TIMEOUT_SEC", publisher)
        self.assertIn("IsB1aPassLine(outText, \"status=PASS vehicle_capture=\")", publisher)
        self.assertIn(".vehicle_capture_v2_1.json", publisher)
        self.assertIn('""raw_attribute_rows"": [', publisher)
        self.assertIn("TerminateExecTree exec", timeout_runner)
        self.assertIn("taskkill /PID", SOURCE)


if __name__ == "__main__":
    unittest.main()
