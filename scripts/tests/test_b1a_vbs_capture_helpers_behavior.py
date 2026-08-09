from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

try:
    from .test_b1a_vbs_verified_capture_static import SOURCE, class_body, procedure
except ImportError:
    from scripts.tests.test_b1a_vbs_verified_capture_static import SOURCE, class_body, procedure


ROOT = Path(__file__).resolve().parents[2]
PLANT_SRC = ROOT / "plant" / "src"
if str(PLANT_SRC) not in sys.path:
    sys.path.insert(0, str(PLANT_SRC))

from vissim_strict.physical_projection import normalize_vehicle_records


CSCRIPT = shutil.which("cscript.exe") or shutil.which("cscript")


def harness_source(source: str | None = None) -> str:
    if source is None:
        source = SOURCE
    names = (
        "ParseB1aLaneId",
        "TrimB1aHorizontalWhitespace",
        "ParseB1aPositiveLongText",
        "TryPositiveLongVariant",
        "TryNonnegativeLongVariant",
        "TryB1aLongVariant",
        "TryFiniteNonnegativeDouble",
        "TryB1aPosition",
        "TryB1aSpeed",
        "TryB1aFiniteDouble",
        "TryExact2DTableBounds",
        "IsB1aEmptyTableResult",
        "RecordVehicleCaptureFailure",
        "ReadVerifiedVehicleTables",
        "AddDictNumber",
        "B1aCountMapTotal",
        "ChainPosCsv",
        "SegmentIndexCsv",
        "InCsvInt",
        "PerfNow",
        "PerfAdd",
        "ScanVehicleState",
        "JsonEscape",
        "JsonBoolean",
        "JsonDoubleInvariant",
        "B1aSignificantDigitCount",
        "WriteVehicleRecordsEnvelope",
        "WriteB1aCountMap",
        "QuickSortB1aLongKeys",
    )
    helpers = "\n\n".join(procedure(source, name) for name in names)
    writer = class_body(source, "Utf8LineWriter")
    return rf'''Option Explicit
Const B1A_POSITION_TOLERANCE_M = 0.000001
Const B1A_STOPPED_THRESHOLD_KPH = 1.0
Dim JSON_DECIMAL_SEPARATOR, failures, comFailures, Vissim
Dim RW_PERF_ENABLED, perfSum, perfCnt
Dim RW_FW_E_CHAIN_LINKS, RW_FW_E_CHAIN_OFFSETS_M, RW_FW_W_CHAIN_LINKS, RW_FW_W_CHAIN_OFFSETS_M
Dim RW_FW_E_SEG_BOUNDS, RW_FW_W_SEG_BOUNDS, RW_RAMP_METER_CONNECTORS, RW_CLASSIFY_UNMATCHED_AS_URBAN
JSON_DECIMAL_SEPARATOR = Mid(FormatNumber(1.5, 1, -1, 0, 0), 2, 1)
failures = 0
comFailures = 0
RW_PERF_ENABLED = False
Set perfSum = CreateObject("Scripting.Dictionary")
Set perfCnt = CreateObject("Scripting.Dictionary")
RW_FW_E_CHAIN_LINKS = "": RW_FW_E_CHAIN_OFFSETS_M = ""
RW_FW_W_CHAIN_LINKS = "": RW_FW_W_CHAIN_OFFSETS_M = ""
RW_FW_E_SEG_BOUNDS = "0,1": RW_FW_W_SEG_BOUNDS = "0,1"
RW_RAMP_METER_CONNECTORS = ""
RW_CLASSIFY_UNMATCHED_AS_URBAN = True

Class FakeVehicles
    Public Count, NoReadCount, LaneReadCount, PosReadCount, SpeedReadCount
    Private noRows, laneRows, posRows, speedRows

    Private Sub Class_Initialize()
        Count = 2
        NoReadCount = 0: LaneReadCount = 0: PosReadCount = 0: SpeedReadCount = 0
        ReDim noRows(1, 1): ReDim laneRows(1, 1): ReDim posRows(1, 1): ReDim speedRows(1, 1)
        noRows(0, 0) = 9: noRows(0, 1) = 9
        noRows(1, 0) = 3: noRows(1, 1) = 3
        laneRows(0, 0) = 9: laneRows(0, 1) = "1220012103-2"
        laneRows(1, 0) = 3: laneRows(1, 1) = "101-7"
        posRows(0, 0) = 9: posRows(0, 1) = CDbl(123.456789012345)
        posRows(1, 0) = 3: posRows(1, 1) = CDbl(-0.000001)
        speedRows(0, 0) = 9: speedRows(0, 1) = CDbl(1)
        speedRows(1, 0) = 3: speedRows(1, 1) = CDbl(0.999999999999)
    End Sub

    Public Function GetMultiAttValues(attributeName)
        Select Case CStr(attributeName)
            Case "No"
                NoReadCount = NoReadCount + 1
                GetMultiAttValues = noRows
            Case "Lane"
                LaneReadCount = LaneReadCount + 1
                GetMultiAttValues = laneRows
            Case "Pos"
                PosReadCount = PosReadCount + 1
                GetMultiAttValues = posRows
            Case "Speed"
                SpeedReadCount = SpeedReadCount + 1
                GetMultiAttValues = speedRows
            Case Else
                Err.Raise 5, "FakeVehicles", "unknown attribute"
        End Select
    End Function
End Class

Class FakeNet
    Public Vehicles
    Private Sub Class_Initialize()
        Set Vehicles = New FakeVehicles
    End Sub
End Class

Class FakeSimulation
    Public SimSec
    Private Sub Class_Initialize()
        SimSec = CDbl(900)
    End Sub
    Public Function AttValue(attributeName)
        If CStr(attributeName) <> "SimSec" Then Err.Raise 5, "FakeSimulation", "unknown attribute"
        AttValue = SimSec
    End Function
End Class

Class FakeVissim
    Public Net, Simulation
    Private Sub Class_Initialize()
        Set Net = New FakeNet
        Set Simulation = New FakeSimulation
    End Sub
End Class

Set Vissim = New FakeVissim

{writer}

{helpers}

Sub Check(condition, label)
    If Not CBool(condition) Then
        failures = failures + 1
        WScript.Echo "FAIL=" & CStr(label)
    End If
End Sub

Dim accepted, rejected, item, linkNo, laneNo, parsed
accepted = Array("1-1", "1220012103-2", " 1220012103-2 ", vbTab & "1-1" & vbTab)
For Each item In accepted
    linkNo = 0: laneNo = 0
    Check ParseB1aLaneId(item, linkNo, laneNo), "lane_accept:" & CStr(item)
Next
rejected = Array("1", "1/2", "1-2-3", "x1-2", "1 - 2", "+1-2", "1.0-2", "0-1", _
    "1-0", "2147483648-1", "1-2147483648", "1--2", "1" & vbCr & "-2")
For Each item In rejected
    linkNo = 0: laneNo = 0
    Check Not ParseB1aLaneId(item, linkNo, laneNo), "lane_reject:" & CStr(item)
Next

Check TryPositiveLongVariant(CLng(1), parsed), "positive_long"
Check Not TryPositiveLongVariant(True, parsed), "reject_bool_id"
Check Not TryPositiveLongVariant("1", parsed), "reject_string_id"
Check Not TryPositiveLongVariant(CDbl(1.5), parsed), "reject_fraction_id"
Check TryB1aPosition(CDbl(-0.000001), parsed), "position_at_negative_tolerance"
Check Not TryB1aPosition(CDbl(-0.0000011), parsed), "position_below_negative_tolerance"
Check TryB1aSpeed(CDbl(0), parsed), "zero_speed"
Check Not TryB1aSpeed(CDbl(-0.000001), parsed), "negative_speed"
Check Not TryB1aSpeed("1.0", parsed), "reject_string_speed"

Dim exactTable(1, 1), wideTable(1, 2), oneDimensional(1), emptyTable
Dim rowLower, rowUpper, colLower, colUpper
Check TryExact2DTableBounds(exactTable, rowLower, rowUpper, colLower, colUpper), "exact_2d_shape"
Check rowLower = 0 And rowUpper = 1 And colLower = 0 And colUpper = 1, "exact_2d_bounds"
Check Not TryExact2DTableBounds(wideTable, rowLower, rowUpper, colLower, colUpper), "reject_wide_shape"
Check Not TryExact2DTableBounds(oneDimensional, rowLower, rowUpper, colLower, colUpper), "reject_1d_shape"
Check IsB1aEmptyTableResult(emptyTable), "explicit_empty_shape"
Check Not IsB1aEmptyTableResult(exactTable), "nonempty_shape_not_empty"

Dim controls, escaped, code
controls = ""
For code = 0 To 31
    controls = controls & Chr(code)
Next
escaped = JsonEscape(controls & Chr(34) & "\")
Check InStr(escaped, "\b") > 0, "escape_backspace"
Check InStr(escaped, "\t") > 0, "escape_tab"
Check InStr(escaped, "\n") > 0, "escape_lf"
Check InStr(escaped, "\f") > 0, "escape_form_feed"
Check InStr(escaped, "\r") > 0, "escape_cr"
Check InStr(escaped, "\u0000") > 0, "escape_nul"
Check InStr(escaped, "\u001F") > 0, "escape_unit_separator"
Check InStr(escaped, "\\") > 0, "escape_backslash"
Check InStr(escaped, "\" & Chr(34)) > 0, "escape_quote"
WScript.Echo "DOUBLE=" & JsonDoubleInvariant(CDbl(1.23456789012345))
WScript.Echo "SMALL=" & JsonDoubleInvariant(CDbl(0.00000000000000000001))

Dim originalLocale, germanDouble
originalLocale = GetLocale()
SetLocale 1031
JSON_DECIMAL_SEPARATOR = Mid(FormatNumber(1.5, 1, -1, 0, 0), 2, 1)
germanDouble = JsonDoubleInvariant(CDbl(1.5))
Check InStr(germanDouble, ".") > 0, "german_decimal_point"
Check InStr(germanDouble, ",") = 0, "german_no_decimal_comma"
WScript.Echo "GERMAN_DOUBLE=" & germanDouble
SetLocale originalLocale
JSON_DECIMAL_SEPARATOR = Mid(FormatNumber(1.5, 1, -1, 0, 0), 2, 1)

Dim total, urban, freeway, ramp, boundary, other, meanSpeed, freewayMeanSpeed, stopped
Dim countE(7), speedE(7), stoppedE(7), countW(7), speedW(7), stoppedW(7)
Dim linkCounts, linkStopped, linkSpeedSums, linkQueueTails, scanOk
Dim collectionCountBefore, collectionCountAfter, captureSimSecBefore, captureSimSecAfter
Dim recordVehNos, recordLinkNos, recordLaneNos, recordPositions, recordSpeeds, recordStopped, recordLaneRaw
Dim fullLinkCounts, fullLinkStoppedCounts
ScanVehicleState 900, total, urban, freeway, ramp, boundary, other, meanSpeed, freewayMeanSpeed, stopped, _
    countE, speedE, stoppedE, countW, speedW, stoppedW, linkCounts, linkStopped, linkSpeedSums, linkQueueTails, scanOk, _
    collectionCountBefore, collectionCountAfter, captureSimSecBefore, captureSimSecAfter, _
    recordVehNos, recordLinkNos, recordLaneNos, recordPositions, recordSpeeds, recordStopped, recordLaneRaw, _
    fullLinkCounts, fullLinkStoppedCounts
Check scanOk, "called_scan_ok"
Check comFailures = 0, "called_scan_no_com_failures"
Check Vissim.Net.Vehicles.NoReadCount = 1, "called_reader_one_No"
Check Vissim.Net.Vehicles.LaneReadCount = 1, "called_reader_one_Lane"
Check Vissim.Net.Vehicles.PosReadCount = 1, "called_reader_one_Pos"
Check Vissim.Net.Vehicles.SpeedReadCount = 1, "called_reader_one_Speed"
Check total = 2 And urban = 2, "called_scan_totals"
Check collectionCountBefore = 2 And collectionCountAfter = 2, "called_scan_collection_counts"
Check captureSimSecBefore = 900 And captureSimSecAfter = 900, "called_scan_times"
Check recordVehNos(0) = 9 And recordVehNos(1) = 3, "called_scan_vehicle_numbers"
Check recordLinkNos(0) = 1220012103 And recordLinkNos(1) = 101, "called_scan_link_numbers"
Check recordLaneNos(0) = 2 And recordLaneNos(1) = 7, "called_scan_lane_numbers"
Check recordLaneRaw(0) = "1220012103-2" And recordLaneRaw(1) = "101-7", "called_scan_raw_lanes"
Check recordStopped(0) = False And recordStopped(1) = True, "called_scan_stopped_flags"
Check fullLinkCounts("1220012103") = 1 And fullLinkCounts("101") = 1, "called_scan_link_counts"
Check fullLinkStoppedCounts.Exists("1220012103"), "called_scan_moving_zero_key"
Check fullLinkStoppedCounts("1220012103") = 0 And fullLinkStoppedCounts("101") = 1, "called_scan_stopped_counts"

Dim stream
Set stream = New Utf8LineWriter
stream.TargetPath = WScript.Arguments(0)
stream.WriteLine "{{"
stream.WriteLine "  ""local_observation"": {{""schema_version"": 2}},"
WriteVehicleRecordsEnvelope stream, CDbl(900), collectionCountBefore, collectionCountAfter, _
    captureSimSecBefore, captureSimSecAfter, recordVehNos, recordLinkNos, recordLaneNos, _
    recordPositions, recordSpeeds, recordStopped, fullLinkCounts, fullLinkStoppedCounts
stream.WriteLine "  ""tail"": true"
stream.WriteLine "}}"
stream.Close

Dim noRecords, emptyCounts, emptyStoppedCounts
Set emptyCounts = CreateObject("Scripting.Dictionary")
Set emptyStoppedCounts = CreateObject("Scripting.Dictionary")
Set stream = New Utf8LineWriter
stream.TargetPath = WScript.Arguments(1)
stream.WriteLine "{{"
stream.WriteLine "  ""local_observation"": {{""schema_version"": 2}},"
WriteVehicleRecordsEnvelope stream, CDbl(0), 0, 0, CDbl(0), CDbl(0), noRecords, noRecords, noRecords, _
    noRecords, noRecords, noRecords, emptyCounts, emptyStoppedCounts
stream.WriteLine "  ""tail"": true"
stream.WriteLine "}}"
stream.Close

Dim bigVehNos, bigLinkNos, bigLaneNos, bigPositions, bigSpeeds, bigStoppedFlags
Dim bigIndex, bigLink, bigKey, bigCounts, bigStoppedCounts
ReDim bigVehNos(19999): ReDim bigLinkNos(19999): ReDim bigLaneNos(19999)
ReDim bigPositions(19999): ReDim bigSpeeds(19999): ReDim bigStoppedFlags(19999)
Set bigCounts = CreateObject("Scripting.Dictionary")
Set bigStoppedCounts = CreateObject("Scripting.Dictionary")
For bigIndex = 0 To 19999
    bigLink = (bigIndex Mod 10) + 1
    bigKey = CStr(bigLink)
    bigVehNos(bigIndex) = bigIndex + 1
    bigLinkNos(bigIndex) = bigLink
    bigLaneNos(bigIndex) = (bigIndex Mod 3) + 1
    bigPositions(bigIndex) = CDbl(bigIndex) / 10.0
    If (bigIndex Mod 3) = 0 Then
        bigSpeeds(bigIndex) = 0.5
        bigStoppedFlags(bigIndex) = True
    Else
        bigSpeeds(bigIndex) = 10.0
        bigStoppedFlags(bigIndex) = False
    End If
    If Not bigCounts.Exists(bigKey) Then
        bigCounts.Add bigKey, 0
        bigStoppedCounts.Add bigKey, 0
    End If
    bigCounts(bigKey) = CLng(bigCounts(bigKey)) + 1
    If bigStoppedFlags(bigIndex) Then
        bigStoppedCounts(bigKey) = CLng(bigStoppedCounts(bigKey)) + 1
    End If
Next
Set stream = New Utf8LineWriter
stream.TargetPath = WScript.Arguments(2)
stream.WriteLine "{{"
stream.WriteLine "  ""local_observation"": {{""schema_version"": 2}},"
WriteVehicleRecordsEnvelope stream, CDbl(900), 20000, 20000, CDbl(900), CDbl(900), _
    bigVehNos, bigLinkNos, bigLaneNos, bigPositions, bigSpeeds, bigStoppedFlags, bigCounts, bigStoppedCounts
stream.WriteLine "  ""tail"": true"
stream.WriteLine "}}"
stream.Close

If failures > 0 Then WScript.Quit 1
WScript.Echo "PASS"
'''


def failure_harness_source() -> str:
    abort = procedure(SOURCE, "AbortVehicleObservation")
    record = procedure(SOURCE, "RecordVehicleCaptureFailure")
    return f'''Option Explicit
Dim observationFailures, comFailures
observationFailures = 0
comFailures = 0

{record}

{abort}

RecordVehicleCaptureFailure "invalid_table_shape", "test=failure_path"
AbortVehicleObservation 900
'''


@unittest.skipUnless(CSCRIPT, "Windows Script Host is required")
class B1aVbsCaptureHelpersBehaviorTests(unittest.TestCase):
    def test_capture_abort_publishes_exact_counters_before_exit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            harness = Path(temp_dir) / "b1a_vbs_capture_abort_harness.vbs"
            harness.write_text(failure_harness_source(), encoding="ascii")
            result = subprocess.run(
                [CSCRIPT, "//nologo", str(harness)],
                check=False,
                capture_output=True,
                text=True, errors="replace",
                timeout=30,
            )
            self.assertEqual(result.returncode, 13, result.stdout + result.stderr)
            self.assertEqual(
                result.stdout.splitlines(),
                [
                    "ERROR=B1A_VEHICLE_CAPTURE_FAILED reason=invalid_table_shape test=failure_path",
                    "ERROR=VEHICLE_OBSERVATION_SCAN_FAILED sim_sec=900",
                    "OBSERVATION_FAILURES=1",
                    "COM_FAILURES=1",
                ],
            )

    def test_stopped_map_dead_decoy_fails_executable_fake_com(self) -> None:
        mutant = SOURCE.replace(
            "        If isStopped Then AddDictNumber fullLinkStoppedCounts, key, 1.0\n",
            "        If False Then\n"
            "            If isStopped Then AddDictNumber fullLinkStoppedCounts, key, 1.0\n"
            "        End If\n"
            "        If isStopped Then AddDictNumber fullLinkStoppedCounts, CStr(laneNo), 1.0\n",
            1,
        )
        self.assertNotEqual(mutant, SOURCE)
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            harness = root / "b1a_vbs_stopped_map_dead_decoy.vbs"
            harness.write_text(harness_source(mutant), encoding="ascii")
            result = subprocess.run(
                [
                    CSCRIPT,
                    "//nologo",
                    str(harness),
                    str(root / "nonzero.json"),
                    str(root / "zero.json"),
                    str(root / "qualification_20000.json"),
                ],
                check=False,
                capture_output=True,
                text=True, errors="replace",
                timeout=30,
            )
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("FAIL=called_scan_stopped_counts", result.stdout)

    def test_helpers_and_zero_nonzero_envelopes_execute_without_com(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            harness = root / "b1a_vbs_capture_helpers_harness.vbs"
            nonzero_path = root / "nonzero.json"
            zero_path = root / "zero.json"
            qualification_path = root / "qualification_20000.json"
            harness.write_text(harness_source(), encoding="ascii")
            started = time.perf_counter()
            result = subprocess.run(
                [
                    CSCRIPT,
                    "//nologo",
                    str(harness),
                    str(nonzero_path),
                    str(zero_path),
                    str(qualification_path),
                ],
                check=False,
                capture_output=True,
                text=True, errors="replace",
                timeout=30,
            )
            elapsed = time.perf_counter() - started
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("PASS", result.stdout)

            nonzero_bytes = nonzero_path.read_bytes()
            zero_bytes = zero_path.read_bytes()
            self.assertFalse(nonzero_bytes.startswith(b"\xef\xbb\xbf"))
            self.assertFalse(zero_bytes.startswith(b"\xef\xbb\xbf"))
            nonzero = json.loads(nonzero_bytes.decode("utf-8"))
            zero = json.loads(zero_bytes.decode("utf-8"))

            self.assertIn("vehicle_records", nonzero)
            self.assertNotIn("vehicle_records", nonzero["local_observation"])
            records = nonzero["vehicle_records"]
            self.assertEqual(records["schema_version"], "vissim-vehicle-records-v2.1")
            self.assertEqual(records["collection_count_before"], 2)
            self.assertEqual(records["collection_count_after"], 2)
            self.assertEqual(records["record_count"], 2)
            self.assertEqual(records["unobservable_count"], 0)
            self.assertEqual(records["external_source_count"], 0)
            self.assertEqual(records["full_network_link_counts"], {"101": 1, "1220012103": 1})
            self.assertEqual(records["full_network_link_stopped_counts"], {"101": 1, "1220012103": 0})
            self.assertEqual([item["veh_no"] for item in records["records"]], [9, 3])
            self.assertFalse(records["records"][0]["stopped"])
            self.assertTrue(records["records"][1]["stopped"])
            self.assertEqual(set(records["records"][0]), {
                "veh_no", "link_no", "lane_no", "position_m", "speed_kph", "stopped"
            })
            normalized, normalized_records, normalized_hash = normalize_vehicle_records(
                {
                    "run_provenance": {"run_id": "run-13"},
                    "sim_sec": 900.0,
                    "total_vehicles": 2,
                    # veh 3 만 stopped 다. 루트 두 카운트는 실제 생산자
                    # (run_real_world_stackelberg_controller.vbs:1517,1525)가 나란히 쓴다.
                    "stopped_vehicles": 1,
                    "vehicle_records": records,
                },
                1.0e-6,
            )
            self.assertEqual(normalized["full_network_link_stopped_counts"], {"101": 1, "1220012103": 0})
            self.assertEqual([item["veh_no"] for item in normalized_records], [3, 9])
            self.assertEqual(len(normalized_hash), 64)

            empty = zero["vehicle_records"]
            self.assertEqual(empty["collection_count_before"], 0)
            self.assertEqual(empty["collection_count_after"], 0)
            self.assertEqual(empty["record_count"], 0)
            self.assertEqual(empty["full_network_link_counts"], {})
            self.assertEqual(empty["full_network_link_stopped_counts"], {})
            self.assertEqual(empty["records"], [])

            qualification_bytes = qualification_path.read_bytes()
            self.assertFalse(qualification_bytes.startswith(b"\xef\xbb\xbf"))
            self.assertLessEqual(len(qualification_bytes), 8 * 1024 * 1024)
            qualification = json.loads(qualification_bytes.decode("utf-8"))["vehicle_records"]
            self.assertEqual(qualification["record_count"], 20_000)
            self.assertEqual(len(qualification["records"]), 20_000)
            self.assertEqual(sum(qualification["full_network_link_counts"].values()), 20_000)
            self.assertLessEqual(elapsed, 3.0)

            for label in ("DOUBLE=", "SMALL=", "GERMAN_DOUBLE="):
                line = next(line for line in result.stdout.splitlines() if line.startswith(label))
                token = line[len(label) :]
                self.assertIn(".", token)
                self.assertTrue(isinstance(json.loads(token), float))
                mantissa = token.upper().split("E", 1)[0]
                significant = mantissa.lstrip("-0.").replace(".", "")
                self.assertGreaterEqual(len(significant), 15)


if __name__ == "__main__":
    unittest.main()
