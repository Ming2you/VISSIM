# N4-0 - action CSV v4 검증기를 러너에서 떼어 cscript 로 실제 실행한다
"""정적 문자열 검사는 "그 줄이 있다"까지만 말한다. 여기서는
`run_real_world_stackelberg_controller.vbs` 에서 검증 프로시저를 그대로 뽑아 cscript 로
돌려 **행이 실제로 거부되는지** 본다. 되돌림 증명도 같이 넣는다 - 판정 줄을 빼면
이 검사가 FAIL 해야 한다.

행은 실 산출물에서 만든다. 어댑터가 실 계획(15 SC · SG 136 · 창 118)으로 쓴 CSV 를
그대로 러너 검증기에 먹인다 - 손으로 지어낸 행이 아니다.
"""

from __future__ import annotations

import csv
import io
import json
import shutil
import subprocess
import tempfile
import types
import unittest
from pathlib import Path

from evaluation.controllers import action_csv_schema, plant_cycle, signal_group_plan
from evaluation.controllers import vissim_stackelberg_adapter as adapter

try:
    from .test_b1a_vbs_verified_capture_static import SOURCE, procedure
except ImportError:
    from scripts.tests.test_b1a_vbs_verified_capture_static import SOURCE, procedure


CSCRIPT = shutil.which("cscript.exe") or shutil.which("cscript")
ROOT = Path(__file__).resolve().parents[2]
PLAN_PATH = ROOT / "outputs" / "signal_group_actuation_plan_v3.json"

# 상수는 러너 원문에서 읽는다. 베껴 두면 러너가 바뀐 뒤에도 옛 값으로만 돈다.
AMBER_SEC, ALL_RED_SEC = plant_cycle.runner_clearance_sec()

VALIDATOR_PROCEDURES = (
    "ActionCsvHeaderValid",
    "PhaseGreenText",
    "PhaseGreenSum",
    "LivePhaseCount",
    "SignalCycleFromPhases",
    "SignalActionValuesValid",
    "SignalSgRowValid",
    "RampActionValid",
    "IsCanonicalNonNegativeInt",
    "IsCanonicalCsvInt",
    "IsFiniteNumberInRange",
    "InCsvInt",
    "DictValue",
)

# 러너가 보는 통제 SC 목록. 2026-08-19 에 SC7·SC16 을 player 로 복원해 17 개가 됐다.
# 여기서 검사하는 행이 계획에서 나오므로 목록도 계획에서 읽는다 - 박아 두면 계획이
# 늘어날 때마다 SC7·SC16 행이 IsCanonicalCsvInt 에서 통째로 거부된다.
SIGNAL_SCS = ",".join(
    sorted(
        (json.loads(PLAN_PATH.read_text(encoding="utf-8"))["controllers"]
         if PLAN_PATH.is_file() else {}),
        key=int,
    )
)


def harness_source(source: str | None = None, body: str = "") -> str:
    if source is None:
        source = SOURCE
    helpers = "\n\n".join(procedure(source, name) for name in VALIDATOR_PROCEDURES)
    return f'''Option Explicit
Const AMBER_SEC = {AMBER_SEC:g}
Const ALL_RED_SEC = {ALL_RED_SEC:g}
Const RAMP_CYCLE_SEC = 10
Dim RW_SIGNAL_SCS, RW_RAMP_METER_IDS, RW_RAMP_METER_SCS, RW_RAMP_METER_CAPACITIES_VPH
Dim sgPlanExpected, failures
RW_SIGNAL_SCS = "{SIGNAL_SCS}"
RW_RAMP_METER_IDS = "D,F"
RW_RAMP_METER_SCS = "6,7"
RW_RAMP_METER_CAPACITIES_VPH = "1800,1800"
Set sgPlanExpected = CreateObject("Scripting.Dictionary")
failures = 0

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


def run_vbs(script_text: str) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "harness.vbs"
        path.write_text(script_text, encoding="utf-8")
        return subprocess.run(
            [CSCRIPT, "//nologo", "//E:vbscript", str(path)],
            capture_output=True,
            text=True,
            timeout=180,
        )


def real_action_csv_rows() -> tuple[list[str], list[list[str]]]:
    """실 계획 15 SC 로 어댑터가 쓴 action CSV 를 그대로 읽어 온다."""
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    mapping = {
        "segments": [],
        "signals": [
            {
                "id": f"SC{sc_no}",
                "sc_no": int(sc_no),
                "major_maps_to": str(node.get("major_maps_to", "p2")),
            }
            for sc_no, node in sorted(plan["controllers"].items(), key=lambda kv: int(kv[0]))
        ],
    }
    # 비워 두면 어댑터가 기본값으로 떨어져 두 현시만 지시하고, 4현시 계획과 부딪혀
    # `signal_group_action_rows` 가 죽는다. SC 마다 **켤 수 있는 현시**에만 고르게 싣는다 -
    # SC107·108·109 는 셋, 나머지는 넷이다. 현시 수를 여기 적지 않는다.
    green_times: dict[str, float] = {}
    for sc_no in plan["controllers"]:
        live = adapter.plan_live_phases(plan, int(sc_no))
        each = (150.0 - 3.0 * len(live)) / float(len(live))
        # 죽은 현시는 **명시적으로 0** 을 넣는다. 키를 빼면 어댑터가 기본값을 채워 넣어
        # SC107 이 네 현시를 지시하게 되고 계획(셋)과 어긋나 죽는다.
        for phase in signal_group_plan.MODEL_PHASES:
            green_times[f"SC{int(sc_no)}_{phase}"] = each if phase in live else 0.0
    control = types.SimpleNamespace(
        green_times=green_times, offsets={}, ramp_metering={}, diagnostics={}
    )
    cfg = types.SimpleNamespace(
        network=types.SimpleNamespace(ramp_capacity_veh_h={}),
        freeway_follower=types.SimpleNamespace(vsl_set=[60.0, 80.0, 100.0]),
    )
    buffer = io.StringIO()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "action.csv"
        adapter.write_action_csv(
            path,
            control,
            cfg,
            mapping,
            lambda control_arg, link, index, cfg_arg: 80.0,
            {"controller_status": "ok"},
            {},
            signal_group_plan_table=plan,
        )
        buffer.write(path.read_text(encoding="utf-8"))
    buffer.seek(0)
    rows = list(csv.reader(buffer))
    return rows[0], rows[1:]


def vbs_string(value: str) -> str:
    return '"' + str(value).replace('"', '""') + '"'


def parts_literal(row: list[str]) -> str:
    return "Split(" + vbs_string(",".join(row)) + ", \",\")"


@unittest.skipUnless(CSCRIPT, "cscript is unavailable")
@unittest.skipUnless(PLAN_PATH.is_file(), "actuation plan artifact is not built")
class ActionCsvValidatorBehaviorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.header, cls.rows = real_action_csv_rows()
        cls.signal_rows = [row for row in cls.rows if row[0] == "signal"]
        cls.sg_rows = [row for row in cls.rows if row[0] == "signal_sg"]
        # 2026-08-19: SC7·SC16 복원으로 계획이 15 -> 17 SC. 숫자를 다시 박지 않고 계획에서 읽는다.
        plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
        assert len(cls.signal_rows) == plan["counts"]["controllers"], len(cls.signal_rows)
        assert len(cls.sg_rows) == plan["counts"]["planned_windows"], len(cls.sg_rows)

    def _run(self, body: str, source: str | None = None) -> subprocess.CompletedProcess:
        return run_vbs(harness_source(source, body))

    def test_the_real_header_and_every_real_row_pass_the_runner_validators(self) -> None:
        lines = [
            f'Check "header", ActionCsvHeaderValid({parts_literal(self.header)}), True',
        ]
        # sgPlanExpected 는 config 에서 오는 계약이다. 실 행에서 그대로 만든다.
        counts: dict[str, int] = {}
        for row in self.sg_rows:
            counts[f"{int(row[3])}-{int(row[2])}"] = counts.get(
                f"{int(row[3])}-{int(row[2])}", 0
            ) + 1
        for key, value in sorted(counts.items()):
            lines.append(f'sgPlanExpected.Add "{key}", {value}')
        for index, row in enumerate(self.signal_rows):
            lines.append(
                f'Check "signal_{index}", SignalActionValuesValid({parts_literal(row)}), True'
            )
        lines.append('Dim seenSg, pendWin, pendCnt, pendCyc, pendOff')
        lines.append('Set seenSg = CreateObject("Scripting.Dictionary")')
        lines.append('Set pendWin = CreateObject("Scripting.Dictionary")')
        lines.append('Set pendCnt = CreateObject("Scripting.Dictionary")')
        lines.append('Set pendCyc = CreateObject("Scripting.Dictionary")')
        lines.append('Set pendOff = CreateObject("Scripting.Dictionary")')
        for index, row in enumerate(self.sg_rows):
            lines.append(
                f'Check "sg_{index}", SignalSgRowValid({parts_literal(row)}, seenSg, '
                "pendWin, pendCnt, pendCyc, pendOff), True"
            )
        result = self._run("\n".join(lines))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS", result.stdout)

    def test_the_runner_cycle_equals_the_adapter_plan_cycle_on_every_real_sc(self) -> None:
        """`signal` 행의 현시 4값으로 러너가 만든 주기 == `signal_sg` 행의 green_sec.

        여기가 어긋나면 실 런에서 SIGNAL_SG_PLAN_CYCLE_STALE 로 그 SC 가 통째로 거부된다.
        정적 검사로는 안 잡히는 자리라 VBS 를 실제로 돌려서 잰다.
        """
        plan_cycle_by_sc = {int(row[3]): float(row[13]) for row in self.sg_rows}
        lines = []
        for row in self.signal_rows:
            sc_no = int(row[3])
            lines.append(
                f'Check "cycle_{sc_no}", SignalCycleFromPhases(PhaseGreenText('
                f'{parts_literal(row)})), {plan_cycle_by_sc[sc_no]:g}'
            )
        result = self._run("\n".join(lines))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_four_live_phases_bite_clearance_four_times_in_the_runner(self) -> None:
        """러너가 clearance 를 상수 2회가 아니라 현시 수만큼 문다.

        지금 계획은 2현시라 실 행으로는 계수 4 를 못 만든다. 그래서 여기서만 현시 넷을
        직접 넣어 러너 산술을 잰다 - 러너의 실제 프로시저를 돌린 값이다.
        """
        clearance = AMBER_SEC + ALL_RED_SEC
        body = "\n".join([
            f'Check "live4", LivePhaseCount("45|24|45|24"), 4',
            f'Check "live2", LivePhaseCount("45|24|0|0"), 2',
            f'Check "cycle4", SignalCycleFromPhases("45|24|45|24"), {138 + 4 * clearance:g}',
            f'Check "cycle2", SignalCycleFromPhases("69|69|0|0"), {138 + 2 * clearance:g}',
        ])
        result = self._run(body)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_a_v3_header_is_rejected(self) -> None:
        legacy = list(action_csv_schema.LEGACY_ACTION_CSV_FIELDS)
        body = f'Check "legacy_header", ActionCsvHeaderValid({parts_literal(legacy)}), False'
        result = self._run(body)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_a_signal_row_with_a_blank_phase_column_is_rejected(self) -> None:
        """빈 칸은 `signal_sg` 의 판별자다. `signal` 행에 오면 거부된다."""
        row = list(self.signal_rows[0])
        row[10] = ""
        body = f'Check "blank_phase", SignalActionValuesValid({parts_literal(row)}), False'
        result = self._run(body)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_a_single_live_phase_is_rejected(self) -> None:
        row = list(self.signal_rows[0])
        row[7] = "60"
        row[8] = "0"
        row[9] = "0"
        row[10] = "0"
        row[11] = "0"
        body = f'Check "one_phase", SignalActionValuesValid({parts_literal(row)}), False'
        result = self._run(body)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_a_phase_green_outside_the_write_clamp_is_rejected(self) -> None:
        low, high = plant_cycle.SIGNAL_GREEN_WRITE_CLAMP_SEC
        row = list(self.signal_rows[0])
        under = list(row)
        under[7] = f"{low - 0.5:g}"
        over = list(row)
        over[7] = f"{high + 0.5:g}"
        body = "\n".join([
            f'Check "under_clamp", SignalActionValuesValid({parts_literal(under)}), False',
            f'Check "over_clamp", SignalActionValuesValid({parts_literal(over)}), False',
        ])
        result = self._run(body)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_a_signal_sg_row_that_fills_the_blank_columns_is_rejected(self) -> None:
        row = list(self.sg_rows[0])
        row[9] = "0"
        body = "\n".join([
            'Dim seenSg, pendWin, pendCnt, pendCyc, pendOff',
            'Set seenSg = CreateObject("Scripting.Dictionary")',
            'Set pendWin = CreateObject("Scripting.Dictionary")',
            'Set pendCnt = CreateObject("Scripting.Dictionary")',
            'Set pendCyc = CreateObject("Scripting.Dictionary")',
            'Set pendOff = CreateObject("Scripting.Dictionary")',
            f'sgPlanExpected.Add "{int(row[3])}-{int(row[2])}", 1',
            f'Check "filled_blank", SignalSgRowValid({parts_literal(row)}, seenSg, '
            "pendWin, pendCnt, pendCyc, pendOff), False",
        ])
        result = self._run(body)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_removing_the_blank_column_check_breaks_this_suite(self) -> None:
        """되돌림 증명 - 판별자 두 줄을 빼면 위 거부가 사라진다."""
        broken = SOURCE.replace(
            '    If Trim(CStr(parts(9))) <> "" Then Exit Function\n'
            '    If Trim(CStr(parts(10))) <> "" Then Exit Function\n',
            "",
            1,
        )
        self.assertNotEqual(broken, SOURCE, "되돌릴 줄을 못 찾았다")
        row = list(self.sg_rows[0])
        row[9] = "0"
        body = "\n".join([
            'Dim seenSg, pendWin, pendCnt, pendCyc, pendOff',
            'Set seenSg = CreateObject("Scripting.Dictionary")',
            'Set pendWin = CreateObject("Scripting.Dictionary")',
            'Set pendCnt = CreateObject("Scripting.Dictionary")',
            'Set pendCyc = CreateObject("Scripting.Dictionary")',
            'Set pendOff = CreateObject("Scripting.Dictionary")',
            f'sgPlanExpected.Add "{int(row[3])}-{int(row[2])}", 1',
            f'Check "filled_blank", SignalSgRowValid({parts_literal(row)}, seenSg, '
            "pendWin, pendCnt, pendCyc, pendOff), False",
        ])
        result = self._run(body, source=broken)
        self.assertNotEqual(
            result.returncode, 0,
            "판별자를 빼도 통과했다 - 이 검사는 아무것도 지키지 않는다\n"
            + result.stdout + result.stderr,
        )

    def test_replacing_the_live_phase_count_with_a_constant_breaks_this_suite(self) -> None:
        """되돌림 증명 - clearance 계수를 v3 의 상수 2 로 되돌리면 주기가 어긋난다."""
        broken = SOURCE.replace(
            "    SignalCycleFromPhases = PhaseGreenSum(phaseText) + _\n"
            "        LivePhaseCount(phaseText) * (AMBER_SEC + ALL_RED_SEC)\n",
            "    SignalCycleFromPhases = PhaseGreenSum(phaseText) + _\n"
            "        2 * (AMBER_SEC + ALL_RED_SEC)\n",
            1,
        )
        self.assertNotEqual(broken, SOURCE, "되돌릴 줄을 못 찾았다")
        clearance = AMBER_SEC + ALL_RED_SEC
        body = (
            f'Check "cycle4", SignalCycleFromPhases("45|24|45|24"), {138 + 4 * clearance:g}'
        )
        result = self._run(body, source=broken)
        self.assertNotEqual(
            result.returncode, 0,
            "상수 2 로 되돌려도 통과했다 - 4현시 주기를 재지 않는 검사다\n"
            + result.stdout + result.stderr,
        )


if __name__ == "__main__":
    unittest.main()
