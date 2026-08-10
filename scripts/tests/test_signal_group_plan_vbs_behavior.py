# v3 N4-5 - 러너의 SG 계획 구동 로직을 cscript 로 실제 실행해 고정한다
"""이름 규칙 대신 전달받은 SG 타이밍으로 구동하는가 - VBS 를 정말로 돌려서 본다.

정적 문자열 검사만으로는 "그 함수가 있다"까지만 말할 수 있다. 여기서는
`run_real_world_stackelberg_controller.vbs` 에서 프로시저를 그대로 뽑아 cscript 로
실행한다(기존 `test_b1a_vbs_capture_helpers_behavior` 와 같은 방식). 되돌림 증명도
같이 넣는다 - 판정 줄을 빼면 이 검사가 FAIL 해야 한다.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

try:
    from .test_b1a_vbs_verified_capture_static import SOURCE, procedure
except ImportError:
    from scripts.tests.test_b1a_vbs_verified_capture_static import SOURCE, procedure


CSCRIPT = shutil.which("cscript.exe") or shutil.which("cscript")

PLAN_PROCEDURES = (
    "ParseSignalGroupPlanConfig",
    "SignalGroupPlanKey",
    "SignalGroupPlanWindows",
    "SignalGroupStateFromPlan",
    "SignalGroupPlanCoGreenReason",
    "FMod",
)


def harness_source(source: str | None = None, body: str = "") -> str:
    if source is None:
        source = SOURCE
    helpers = "\n\n".join(procedure(source, name) for name in PLAN_PROCEDURES)
    return f'''Option Explicit
Const AMBER_SEC = 3
Const ALL_RED_SEC = 2
Dim sgPlanEnabled, sgPlanExpected, sgPlanConflicts, sgPlanWindows, sgPlanCycle, sgPlanGroups
Dim RW_SIGNAL_SG_PLAN_SCHEMA, RW_SIGNAL_SG_EXPECTED, RW_SIGNAL_SG_CONFLICTS
Dim failures
failures = 0
sgPlanEnabled = False
Set sgPlanExpected = CreateObject("Scripting.Dictionary")
Set sgPlanConflicts = CreateObject("Scripting.Dictionary")
Set sgPlanWindows = CreateObject("Scripting.Dictionary")
Set sgPlanCycle = CreateObject("Scripting.Dictionary")
Set sgPlanGroups = CreateObject("Scripting.Dictionary")

{helpers}

Sub Check(label, actual, expected)
    If CStr(actual) <> CStr(expected) Then
        failures = failures + 1
        WScript.Echo "FAIL " & label & " actual=" & CStr(actual) & " expected=" & CStr(expected)
    Else
        WScript.Echo "OK " & label
    End If
End Sub

{body}

If failures > 0 Then WScript.Quit 1
WScript.Echo "PASS"
'''


STATE_BODY = '''
RW_SIGNAL_SG_PLAN_SCHEMA = 1
RW_SIGNAL_SG_EXPECTED = "7:1:1,7:2:1,7:3:0"
RW_SIGNAL_SG_CONFLICTS = "7:1-2"
ParseSignalGroupPlanConfig
Check "enabled", sgPlanEnabled, True
Check "expected_count", sgPlanExpected.Count, 3
Check "expected_1", sgPlanExpected("7-1"), 1
Check "expected_3", sgPlanExpected("7-3"), 0
Check "conflict", sgPlanConflicts.Exists("7-1-2"), True
Check "conflict_absent", sgPlanConflicts.Exists("7-1-3"), False

sgPlanWindows("7-1") = "0|20;"
sgPlanWindows("7-2") = "25|40;"
sgPlanCycle("7") = 50

Check "green_start", SignalGroupStateFromPlan(7, 1, 0.0, 50.0), "GREEN"
Check "green_mid", SignalGroupStateFromPlan(7, 1, 19.999, 50.0), "GREEN"
Check "amber_after", SignalGroupStateFromPlan(7, 1, 20.0, 50.0), "AMBER"
Check "amber_end", SignalGroupStateFromPlan(7, 1, 22.999, 50.0), "AMBER"
Check "red_after_amber", SignalGroupStateFromPlan(7, 1, 23.0, 50.0), "RED"
Check "red_before", SignalGroupStateFromPlan(7, 2, 24.999, 50.0), "RED"
Check "second_green", SignalGroupStateFromPlan(7, 2, 39.999, 50.0), "GREEN"
Check "unplanned_group_is_red", SignalGroupStateFromPlan(7, 3, 10.0, 50.0), "RED"

' 주기 끝에 닿는 창의 amber 는 주기 머리로 감긴다.
sgPlanWindows("7-4") = "45|50;"
Check "amber_wraps", SignalGroupStateFromPlan(7, 4, 1.0, 50.0), "AMBER"
Check "amber_wrap_end", SignalGroupStateFromPlan(7, 4, 3.0, 50.0), "RED"
'''

COGREEN_BODY = '''
RW_SIGNAL_SG_PLAN_SCHEMA = 1
RW_SIGNAL_SG_EXPECTED = "7:1:1,7:2:1"
RW_SIGNAL_SG_CONFLICTS = "7:1-2"
ParseSignalGroupPlanConfig

Dim sgNos(2), states(2)
sgNos(0) = 1: states(0) = "GREEN"
sgNos(1) = 2: states(1) = "GREEN"
Check "cogreen_blocked", SignalGroupPlanCoGreenReason(7, sgNos, states, 2) <> "", True

states(1) = "AMBER"
Check "amber_is_not_cogreen", SignalGroupPlanCoGreenReason(7, sgNos, states, 2), ""

states(1) = "GREEN"
sgNos(1) = 3
Check "unlisted_pair_allowed", SignalGroupPlanCoGreenReason(7, sgNos, states, 2), ""
'''


CONTRACT_PROCEDURES = (
    "ParseSignalGroupPlanConfig",
    "SignalGroupPlanKey",
    "SignalSgRowValid",
    "SignalGroupPlanExpectedRowCount",
    "SignalGroupPlanRejectReason",
    "SignalGroupPlanWindowConflictReason",
    "IsCanonicalNonNegativeInt",
    "IsCanonicalCsvInt",
    "IsFiniteNumberInRange",
    "InCsvInt",
    "DictValue",
)


def contract_harness_source(source: str | None = None, body: str = "") -> str:
    if source is None:
        source = SOURCE
    helpers = "\n\n".join(procedure(source, name) for name in CONTRACT_PROCEDURES)
    return f'''Option Explicit
Const AMBER_SEC = 3
Const ALL_RED_SEC = 2
Dim sgPlanEnabled, sgPlanExpected, sgPlanConflicts, sgPlanGroups
Dim RW_SIGNAL_SG_PLAN_SCHEMA, RW_SIGNAL_SG_EXPECTED, RW_SIGNAL_SG_CONFLICTS, RW_SIGNAL_SCS
Dim seenSg, pendWindows, pendCounts, pendCycle, pendOffset, rowCycle, rowOffset
Dim failures
failures = 0
sgPlanEnabled = False
RW_SIGNAL_SCS = "7"
Set sgPlanExpected = CreateObject("Scripting.Dictionary")
Set sgPlanConflicts = CreateObject("Scripting.Dictionary")
Set sgPlanGroups = CreateObject("Scripting.Dictionary")

{helpers}

Sub ResetPending
    Set seenSg = CreateObject("Scripting.Dictionary")
    Set pendWindows = CreateObject("Scripting.Dictionary")
    Set pendCounts = CreateObject("Scripting.Dictionary")
    Set pendCycle = CreateObject("Scripting.Dictionary")
    Set pendOffset = CreateObject("Scripting.Dictionary")
    Set rowCycle = CreateObject("Scripting.Dictionary")
    Set rowOffset = CreateObject("Scripting.Dictionary")
End Sub

Function Row(sgNo, windowIndex, startSec, endSec, offsetSec, cycleSec)
    Row = Split("signal_sg,SC7_SG" & CStr(sgNo) & "_W" & CStr(windowIndex) & "," & CStr(sgNo) & _
        ",7," & CStr(windowIndex) & ",0,0," & CStr(startSec) & "," & CStr(endSec) & "," & _
        CStr(offsetSec) & ",0," & CStr(cycleSec) & ",ok", ",")
End Function

Function Accept(sgNo, windowIndex, startSec, endSec, offsetSec, cycleSec)
    Accept = SignalSgRowValid(Row(sgNo, windowIndex, startSec, endSec, offsetSec, cycleSec), _
        seenSg, pendWindows, pendCounts, pendCycle, pendOffset)
End Function

Sub Check(label, actual, expected)
    If CStr(actual) <> CStr(expected) Then
        failures = failures + 1
        WScript.Echo "FAIL " & label & " actual=" & CStr(actual) & " expected=" & CStr(expected)
    Else
        WScript.Echo "OK " & label
    End If
End Sub

Sub CheckContains(label, actual, needle)
    If InStr(1, CStr(actual), CStr(needle), vbTextCompare) <= 0 Then
        failures = failures + 1
        WScript.Echo "FAIL " & label & " actual=" & CStr(actual) & " needle=" & CStr(needle)
    Else
        WScript.Echo "OK " & label
    End If
End Sub

{body}

If failures > 0 Then WScript.Quit 1
WScript.Echo "PASS"
'''


CONTRACT_BODY = '''
RW_SIGNAL_SG_PLAN_SCHEMA = 1
RW_SIGNAL_SG_EXPECTED = "7:1:1,7:2:1,7:3:0"
RW_SIGNAL_SG_CONFLICTS = "7:1-2"
ParseSignalGroupPlanConfig
Check "expected_rows", SignalGroupPlanExpectedRowCount(), 2

ResetPending
Check "accept_1", Accept(1, 0, 0, 20, 4, 50), True
Check "accept_2", Accept(2, 0, 25, 40, 4, 50), True
rowCycle("7") = 50.0
rowOffset("7") = 4.0
Check "clean_plan", SignalGroupPlanRejectReason(pendWindows, pendCounts, pendCycle, rowCycle, rowOffset), ""

' 창이 하나 모자라면 전량 거부다.
ResetPending
Check "accept_only_one", Accept(1, 0, 0, 20, 4, 50), True
rowCycle("7") = 50.0
CheckContains "missing_window", _
    SignalGroupPlanRejectReason(pendWindows, pendCounts, pendCycle, rowCycle, rowOffset), "window_count"

' 축 지시가 만드는 주기와 창의 주기가 다르면 거부다.
ResetPending
Check "accept_c1", Accept(1, 0, 0, 20, 4, 50), True
Check "accept_c2", Accept(2, 0, 25, 40, 4, 50), True
rowCycle("7") = 90.0
CheckContains "cycle_mismatch", _
    SignalGroupPlanRejectReason(pendWindows, pendCounts, pendCycle, rowCycle, rowOffset), "cycle_mismatch"

' signal 행이 아예 없는 SC 의 창은 거부다.
ResetPending
Check "accept_n1", Accept(1, 0, 0, 20, 4, 50), True
Check "accept_n2", Accept(2, 0, 25, 40, 4, 50), True
CheckContains "no_signal_row", _
    SignalGroupPlanRejectReason(pendWindows, pendCounts, pendCycle, rowCycle, rowOffset), "no_signal_row"

' 금지 쌍이 겹치는 창을 실어 오면 거부다 - 이것이 N4-5 요구 3이다.
ResetPending
Check "accept_x1", Accept(1, 0, 0, 30, 4, 50), True
Check "accept_x2", Accept(2, 0, 20, 40, 4, 50), True
rowCycle("7") = 50.0
CheckContains "cogreen_rejected", _
    SignalGroupPlanRejectReason(pendWindows, pendCounts, pendCycle, rowCycle, rowOffset), "cogreen"

' 행 자체가 계약을 어기면 그 행은 유효하지 않다.
ResetPending
Check "reject_unknown_sg", Accept(9, 0, 0, 20, 4, 50), False
Check "reject_zero_length", Accept(1, 0, 20, 20, 4, 50), False
Check "reject_beyond_cycle", Accept(1, 0, 0, 60, 4, 50), False
ResetPending
Check "accept_dup_first", Accept(1, 0, 0, 20, 4, 50), True
Check "reject_duplicate", Accept(1, 0, 0, 20, 4, 50), False
ResetPending
Check "accept_off_first", Accept(1, 0, 0, 20, 4, 50), True
Check "reject_offset_split", Accept(2, 0, 25, 40, 9, 50), False
ResetPending
Check "accept_cyc_first", Accept(1, 0, 0, 20, 4, 50), True
Check "reject_cycle_split", Accept(2, 0, 25, 40, 4, 70), False

' id 가 (sc, sg, 창) 과 어긋나면 거부다.
ResetPending
Dim badId
badId = Split("signal_sg,SC7_SG2_W0,1,7,0,0,0,0,20,4,0,50,ok", ",")
Check "reject_id_mismatch", _
    SignalSgRowValid(badId, seenSg, pendWindows, pendCounts, pendCycle, pendOffset), False
'''


EVENT_PROCEDURES = (
    "ParseSignalGroupPlanConfig",
    "SignalGroupPlanKey",
    "SignalGroupPlanWindows",
    "SignalGroupStateFromPlan",
    "SignalCompositeStateAt",
    "NextSignalTransitionAfter",
    "MaxSignalCycleSec",
    "DictValue",
    "FMod",
)


def event_harness_source(source: str | None = None, body: str = "") -> str:
    if source is None:
        source = SOURCE
    helpers = "\n\n".join(procedure(source, name) for name in EVENT_PROCEDURES)
    return f'''Option Explicit
Const AMBER_SEC = 3
Const ALL_RED_SEC = 2
Dim sgPlanEnabled, sgPlanExpected, sgPlanConflicts, sgPlanWindows, sgPlanCycle, sgPlanGroups
Dim RW_SIGNAL_SG_PLAN_SCHEMA, RW_SIGNAL_SG_EXPECTED, RW_SIGNAL_SG_CONFLICTS
Dim sigMajor, sigMinor, sigOffset, simPeriod
Dim failures
failures = 0
simPeriod = 10000
sgPlanEnabled = False
Set sgPlanExpected = CreateObject("Scripting.Dictionary")
Set sgPlanConflicts = CreateObject("Scripting.Dictionary")
Set sgPlanWindows = CreateObject("Scripting.Dictionary")
Set sgPlanCycle = CreateObject("Scripting.Dictionary")
Set sgPlanGroups = CreateObject("Scripting.Dictionary")
Set sigMajor = CreateObject("Scripting.Dictionary")
Set sigMinor = CreateObject("Scripting.Dictionary")
Set sigOffset = CreateObject("Scripting.Dictionary")

{helpers}

Sub Check(label, actual, expected)
    If CStr(actual) <> CStr(expected) Then
        failures = failures + 1
        WScript.Echo "FAIL " & label & " actual=" & CStr(actual) & " expected=" & CStr(expected)
    Else
        WScript.Echo "OK " & label
    End If
End Sub

{body}

If failures > 0 Then WScript.Quit 1
WScript.Echo "PASS"
'''


EVENT_BODY = '''
' 축은 major=20, minor=20 이라 주기 50 이다. 계획은 major 창을 SG1(0-12)과
' SG2(12-20)로 쪼갠다. sec 12 는 축 전이가 아니라 **축 안의** 전이다.
RW_SIGNAL_SG_PLAN_SCHEMA = 1
RW_SIGNAL_SG_EXPECTED = "7:1:1,7:2:1,7:3:1"
RW_SIGNAL_SG_CONFLICTS = "7:1-2"
ParseSignalGroupPlanConfig
Check "groups_listed", sgPlanGroups("7"), "1,2,3"

sigMajor("7") = 20.0
sigMinor("7") = 20.0
sigOffset("7") = 0.0
sgPlanWindows("7-1") = "0|12;"
sgPlanWindows("7-2") = "12|20;"
sgPlanWindows("7-3") = "25|45;"
sgPlanCycle("7") = 50.0

Check "composite_changes_inside_axis", _
    (SignalCompositeStateAt(11) <> SignalCompositeStateAt(12)), True
Check "event_breaks_at_intra_axis_edge", NextSignalTransitionAfter(10), 12

' 계획을 끄면 예전 축 전이만 남는다 - sec 12 는 더 이상 이벤트가 아니다.
sgPlanEnabled = False
Check "legacy_has_no_intra_axis_event", NextSignalTransitionAfter(10), 20
'''


@unittest.skipUnless(CSCRIPT, "Windows Script Host is required")
class SignalGroupPlanEventSchedulingTests(unittest.TestCase):
    def _run(self, source: str, body: str) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as temp_dir:
            harness = Path(temp_dir) / "sg_event_harness.vbs"
            harness.write_text(event_harness_source(source, body), encoding="utf-8")
            return subprocess.run(
                [CSCRIPT, "//nologo", str(harness)],
                check=False,
                capture_output=True,
                text=True,
                errors="replace",
                timeout=60,
            )

    def test_event_scheduler_breaks_at_intra_axis_signal_group_edges(self) -> None:
        """계획이 켜지면 SG 창 경계도 이벤트다. 아니면 상태가 늦게 쓰인다."""
        result = self._run(SOURCE, EVENT_BODY)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS", result.stdout)


@unittest.skipUnless(CSCRIPT, "Windows Script Host is required")
class SignalGroupPlanContractVbsTests(unittest.TestCase):
    def _run(self, source: str, body: str) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as temp_dir:
            harness = Path(temp_dir) / "sg_contract_harness.vbs"
            harness.write_text(contract_harness_source(source, body), encoding="utf-8")
            return subprocess.run(
                [CSCRIPT, "//nologo", str(harness)],
                check=False,
                capture_output=True,
                text=True,
                errors="replace",
                timeout=60,
            )

    def test_action_csv_signal_group_contract_is_all_or_nothing(self) -> None:
        result = self._run(SOURCE, CONTRACT_BODY)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS", result.stdout)

    def test_dropping_the_window_conflict_scan_makes_the_contract_fail(self) -> None:
        """되돌림 증명. 동시녹색 검사를 빼면 위 계약 검사가 깨져야 한다."""
        mutant = SOURCE.replace(
            "    SignalGroupPlanRejectReason = SignalGroupPlanWindowConflictReason(pendingWindows)",
            "    SignalGroupPlanRejectReason = \"\"",
        )
        self.assertNotEqual(mutant, SOURCE, "mutation target line not found")
        result = self._run(mutant, CONTRACT_BODY)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("FAIL cogreen_rejected", result.stdout)

    def test_dropping_the_window_count_check_makes_the_contract_fail(self) -> None:
        """되돌림 증명. 창 수 대조를 빼면 부족한 계획이 통과해 버린다."""
        mutant = SOURCE.replace(
            "        If actualCount <> expectedCount Then",
            "        If False Then",
        )
        self.assertNotEqual(mutant, SOURCE, "mutation target line not found")
        result = self._run(mutant, CONTRACT_BODY)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("FAIL missing_window", result.stdout)


@unittest.skipUnless(CSCRIPT, "Windows Script Host is required")
class SignalGroupPlanVbsBehaviorTests(unittest.TestCase):
    def _run(self, source: str, body: str) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as temp_dir:
            harness = Path(temp_dir) / "sg_plan_harness.vbs"
            # 러너 원본과 같은 바이트 모양(BOM 없는 UTF-8)으로 쓴다. 주석의 한글은
            # cscript 가 ANSI 로 읽어 깨지지만 실행에는 영향이 없다.
            harness.write_text(harness_source(source, body), encoding="utf-8")
            return subprocess.run(
                [CSCRIPT, "//nologo", str(harness)],
                check=False,
                capture_output=True,
                text=True,
                errors="replace",
                timeout=60,
            )

    def test_plan_drives_signal_group_state_without_the_name_rule(self) -> None:
        result = self._run(SOURCE, STATE_BODY)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS", result.stdout)

    def test_co_green_of_a_declared_conflict_pair_is_reported(self) -> None:
        result = self._run(SOURCE, COGREEN_BODY)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS", result.stdout)

    def test_removing_the_conflict_lookup_makes_the_co_green_check_fail(self) -> None:
        """되돌림 증명. 충돌 조회를 지우면 위 검사가 반드시 깨져야 한다."""
        mutant = SOURCE.replace(
            "                    If sgPlanConflicts.Exists(pairKey) Then",
            "                    If False Then",
        )
        self.assertNotEqual(mutant, SOURCE, "mutation target line not found")
        result = self._run(mutant, COGREEN_BODY)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("FAIL cogreen_blocked", result.stdout)

    def test_removing_the_amber_tail_makes_the_state_check_fail(self) -> None:
        """되돌림 증명. amber 구간을 지우면 상태 판정 검사가 깨져야 한다."""
        mutant = SOURCE.replace(
            '                SignalGroupStateFromPlan = "AMBER"',
            '                SignalGroupStateFromPlan = "RED"',
        )
        self.assertNotEqual(mutant, SOURCE, "mutation target line not found")
        result = self._run(mutant, STATE_BODY)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("FAIL amber_after", result.stdout)


if __name__ == "__main__":
    unittest.main()
