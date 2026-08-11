# v3 N4-5 A1 - 실 계획(15 SC / 136 SG)을 러너 VBS 에 그대로 먹여 두 구동 방식을 실측 대조한다
"""합성 픽스처가 아니라 **실 산출물**로 SG 단위 구동을 검증한다.

`test_signal_group_plan_vbs_behavior` 는 SG 2~3개짜리 손으로 만든 픽스처를 쓴다.
그것은 함수의 분기를 고정하지만, 실제 개포동 15 SC / 136 SG 계획에서 무슨 일이
일어나는지는 말하지 않는다. 직전 회차에 2노드 픽스처가 실 산출물 위반을 못 보고
통과한 전례가 있다.

여기서는

  1. `outputs/signal_group_actuation_plan_v3.json` 의 15 SC 전부에 대해
  2. 러너에서 떼어낸 **진짜** `SignalGroupStateFromPlan` / `AnySignalGroupGreenAt` /
     `SignalStateForGroup` 을 cscript 로 돌려
  3. 주기 전체를 조각으로 잘라 상태를 재고

두 구동 방식을 같은 자로 잰다.

    plan       러너가 sgplan 형제 파일을 받은 경우 - SG 별 창으로 구동
    name_rule  형제 파일이 없을 때 남는 경로 - 이름 부분문자열로 축 상태를 물려줌

`name_rule` 쪽은 **양성 대조**다. 같은 harness 가 알려진 나쁜 수치를 내놓아야
"검사가 아무것도 재지 않게 되는" 경우를 배제할 수 있다.

## 조각내기가 왜 정확한가

`SignalGroupStateFromPlan` 은 창 시작·창 끝·창 끝+amber(주기 wrap 포함)에서만 값이 바뀌는
구간상수 함수다. 그 점들을 전부 모아 정렬하면 각 구간 안에서는 상태가 상수이므로,
구간 중점 한 번만 물어보면 그 구간 길이만큼의 녹색·황색을 정확히 적을 수 있다.
표본 간격을 좁히는 방식과 달리 반올림 오차가 없다.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from evaluation.controllers import plant_cycle, signal_group_plan

try:
    from .test_b1a_vbs_verified_capture_static import SOURCE, procedure
except ImportError:  # 모듈을 직접 돌릴 때
    from scripts.tests.test_b1a_vbs_verified_capture_static import SOURCE, procedure


ROOT = Path(__file__).resolve().parents[2]
PLAN_PATH = ROOT / "outputs" / "signal_group_actuation_plan_v3.json"
TIMING_PATH = ROOT / "outputs" / "signal_group_timing_v3.json"
SGPLAN_VBS = (
    ROOT
    / "evaluation"
    / "generated"
    / "real_world_modi_control_config_distributed_core15n41_20260805_sgplan.vbs"
)
NETWORK = ROOT / "network" / "real_world_gaepo_modi" / "modi_eval_rw_control.inpx"

CSCRIPT = shutil.which("cscript.exe") or shutil.which("cscript")

# 러너 Const 와 같은 값이어야 한다 - 그래서 베끼지 않고 러너 원문에서 읽는다.
AMBER_SEC, ALL_RED_SEC = plant_cycle.runner_clearance_sec()

PROCEDURES = (
    "ParseSignalGroupPlanConfig",
    "SignalGroupPlanKey",
    "SignalGroupPlanWindows",
    "SignalGroupStateFromPlan",
    "AnySignalGroupGreenAt",
    "SignalStateForGroup",
    "FMod",
)

# 지시 축 녹색 두 지점. native 는 "모델이 예측하는 그 배분", asym 은 그 성질이 특정
# 지시값의 우연이 아님을 보는 두 번째 점이다.
OPERATING_POINTS = ("native", "asym80_35")


def _name_axis(name: str) -> str | None:
    """러너 `SignalStateForGroup` 의 이름 판정을 그대로 미러링한다."""
    upper = str(name).upper()
    if "EB" in upper or "WB" in upper:
        return "major"
    if "NB" in upper or "SB" in upper:
        return "minor"
    return None


class RealPlanActuationTests(unittest.TestCase):
    """실 계획으로 러너 프로시저를 돌려 얻은 수치를 고정한다."""

    plan: dict
    names: dict[str, dict[str, str]]

    @classmethod
    def setUpClass(cls) -> None:
        if not CSCRIPT:
            raise unittest.SkipTest("Windows Script Host is required")
        for path in (PLAN_PATH, TIMING_PATH, SGPLAN_VBS, NETWORK):
            if not path.is_file():
                raise unittest.SkipTest(f"artifact missing: {path}")
        cls.plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
        root = ET.parse(NETWORK).getroot()
        cls.names = {
            str(controller.get("no", "")): {
                str(group.get("no", "")): str(group.get("name", ""))
                for group in controller.findall("./sgs/signalGroup")
            }
            for controller in root.findall(".//signalControllers/signalController")
        }
        cls._measured: dict[tuple[str, str], dict] = {}

    # ------------------------------------------------------------------ 준비

    def _commanded(self, sc_no: str, point: str) -> tuple[float, float]:
        node = self.plan["controllers"][sc_no]
        major_phase = str(node["major_maps_to"])
        minor_phase = "p1" if major_phase == "p2" else "p2"
        if point == "native":
            return (
                float(node["axis_green_sec"][major_phase]),
                float(node["axis_green_sec"][minor_phase]),
            )
        return 80.0, 35.0

    def _windows(self, sc_no: str, major: float, minor: float):
        node = self.plan["controllers"][sc_no]
        return signal_group_plan.plan_windows(
            signal_group_plan.node_plan_from_json(node),
            major_green=major,
            minor_green=minor,
            major_maps_to=str(node["major_maps_to"]),
            amber_sec=AMBER_SEC,
            all_red_sec=ALL_RED_SEC,
        )

    def _forbidden_pairs(self) -> set[tuple[str, str, str]]:
        """계약이 금지한 쌍. sgplan 형제 파일의 `RW_SIGNAL_SG_CONFLICTS` 와 같은 집합이다."""
        pairs = set()
        for sc_no, node in self.plan["controllers"].items():
            for first, second in node["conflict_pairs"]:
                low, high = sorted((first, second), key=int)
                pairs.add((sc_no, low, high))
        return pairs

    def _name_rule_pairs(self) -> set[tuple[str, str, str]]:
        """이름 규칙이 만드는 동시녹색 쌍 - 같은 이름 축인데 native 에서는 안 겹치는 쌍.

        `derive_signal_group_timing.py` 의 정의와 같되 **sg_id 공간**에서 센다. 그 표는
        SG 이름을 키로 쓰는데 SC5 는 24 SG 가 8개 이름을 세 번씩 쓰므로 이름 키로는
        창이 덮어써지고 쌍이 중복으로 세어진다(표의 222 는 그래서 sg_id 로는 122 쌍이다).
        """
        timing = json.loads(TIMING_PATH.read_text(encoding="utf-8"))
        pairs = set()
        for controller in timing["controllers"]:
            sc_no = str(controller["sc_no"])
            rows = [
                (
                    str(group["sg_id"]),
                    _name_axis(group["name"]),
                    [tuple(window) for window in group["green_windows"]],
                )
                for group in controller["groups"]
            ]
            rows = [row for row in rows if row[1] is not None]
            for index, (first, first_axis, first_windows) in enumerate(rows):
                for second, second_axis, second_windows in rows[index + 1 :]:
                    if first_axis != second_axis:
                        continue
                    overlaps = any(
                        min(a1, b1) - max(a0, b0) > 1.0e-9
                        for a0, a1 in first_windows
                        for b0, b1 in second_windows
                    )
                    if not overlaps:
                        low, high = sorted((first, second), key=int)
                        pairs.add((sc_no, low, high))
        return pairs

    # ------------------------------------------------------------------ 실행

    def _run(self, source: str, body: str) -> str:
        helpers = "\n\n".join(procedure(source, name) for name in PROCEDURES)
        script = f'''Option Explicit
Const AMBER_SEC = {AMBER_SEC:g}
Const ALL_RED_SEC = {ALL_RED_SEC:g}
Dim sgPlanEnabled, sgPlanExpected, sgPlanConflicts, sgPlanWindows, sgPlanCycle, sgPlanGroups
Dim RW_SIGNAL_SG_PLAN_SCHEMA, RW_SIGNAL_SG_PLAN_SOURCE_SHA256
Dim RW_SIGNAL_SG_EXPECTED, RW_SIGNAL_SG_CONFLICTS
Dim signalNameRuleFallbacks
signalNameRuleFallbacks = 0
sgPlanEnabled = False
Set sgPlanExpected = CreateObject("Scripting.Dictionary")
Set sgPlanConflicts = CreateObject("Scripting.Dictionary")
Set sgPlanWindows = CreateObject("Scripting.Dictionary")
Set sgPlanCycle = CreateObject("Scripting.Dictionary")
Set sgPlanGroups = CreateObject("Scripting.Dictionary")

{helpers}

Sub ProbePlan(scNo, sgNo, pos)
    WScript.Echo "P|" & CStr(scNo) & "|" & CStr(sgNo) & "|" & _
        SignalGroupStateFromPlan(CLng(scNo), CLng(sgNo), CDbl(pos), _
            CDbl(sgPlanCycle(CStr(CLng(scNo)))))
End Sub

Sub ProbeName(scNo, sgNo, sgName, majorState, minorState)
    WScript.Echo "N|" & CStr(scNo) & "|" & CStr(sgNo) & "|" & _
        CStr(SignalStateForGroup(CLng(sgNo), CStr(sgName), CStr(majorState), CStr(minorState)))
End Sub

{body}
WScript.Echo "HARNESS_DONE"
'''
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "real_plan_harness.vbs"
            path.write_text(script, encoding="utf-8")
            result = subprocess.run(
                [CSCRIPT, "//nologo", str(path)],
                check=False,
                capture_output=True,
                text=True,
                errors="replace",
                timeout=600,
            )
        self.assertEqual(result.returncode, 0, result.stdout[-4000:] + result.stderr[-2000:])
        self.assertIn("HARNESS_DONE", result.stdout)
        return result.stdout

    def _measure(self, point: str, source: str | None = None) -> dict[str, dict]:
        """두 구동 방식을 같은 실행 안에서 재고 집계를 돌려준다."""
        # 돌연변이가 여럿이므로 캐시 키에 **원본 자체**를 넣는다. "mutant" 한 글자로
        # 묶으면 서로 다른 돌연변이가 앞의 결과를 돌려받는다(실제로 그렇게 물렸다).
        key = (point, hashlib.sha256((SOURCE if source is None else source).encode()).hexdigest())
        if key in self._measured:
            return self._measured[key]

        contract = "\n".join(
            line for line in SGPLAN_VBS.read_text(encoding="utf-8").splitlines()
            if not line.startswith("'")
        )
        body = [contract, "ParseSignalGroupPlanConfig"]
        layout: list[tuple[str, str, list[tuple[float, float]]]] = []
        per_sc: dict[str, dict] = {}

        for sc_no in sorted(self.plan["controllers"], key=int):
            node = self.plan["controllers"][sc_no]
            major, minor = self._commanded(sc_no, point)
            cycle = signal_group_plan.plan_cycle_sec(major, minor, AMBER_SEC, ALL_RED_SEC)
            windows = self._windows(sc_no, major, minor)
            spec: dict[str, list[str]] = {}
            for window in windows:
                spec.setdefault(window.sg_no, []).append(
                    f"{window.start_sec:.9f}|{window.end_sec:.9f}"
                )
            for sg_no, parts in spec.items():
                body.append(
                    f'sgPlanWindows("{int(sc_no)}-{int(sg_no)}") = "{";".join(parts)};"'
                )
            body.append(f'sgPlanCycle("{int(sc_no)}") = {cycle:.9f}')
            per_sc[sc_no] = {
                "major": major,
                "minor": minor,
                "cycle": cycle,
                "windows": windows,
                "sgs": sorted(node["window_counts"], key=int),
            }

        for sc_no in sorted(self.plan["controllers"], key=int):
            info = per_sc[sc_no]
            cells = _cells(_plan_boundaries(info["windows"], info["cycle"]))
            for middle, _ in cells:
                for sg_no in info["sgs"]:
                    body.append(f"ProbePlan {int(sc_no)}, {int(sg_no)}, {middle:.9f}")
            layout.append(("P", sc_no, cells))

        for sc_no in sorted(self.plan["controllers"], key=int):
            info = per_sc[sc_no]
            cells = _cells(_axis_boundaries(info["major"], info["minor"], info["cycle"]))
            for middle, _ in cells:
                major_state, minor_state = _axis_states(middle, info["major"], info["minor"])
                for sg_no in info["sgs"]:
                    name = self.names.get(sc_no, {}).get(str(sg_no), "").replace('"', "")
                    body.append(
                        f'ProbeName {int(sc_no)}, {int(sg_no)}, "{name}", '
                        f'"{major_state}", "{minor_state}"'
                    )
            layout.append(("N", sc_no, cells))

        output = self._run(SOURCE if source is None else source, "\n".join(body))
        forbidden = self._forbidden_pairs()
        name_rule_pairs = self._name_rule_pairs()
        summary = {}
        for tag, prefix in (("plan", "P|"), ("name_rule", "N|")):
            lines = [line for line in output.splitlines() if line.startswith(prefix)]
            summary[tag] = _summarise(
                tag, lines, layout, per_sc, self.plan, forbidden, name_rule_pairs
            )
        self._measured[key] = summary
        return summary

    # ------------------------------------------------------------------ 검사

    def test_plan_driving_creates_no_forbidden_simultaneous_green(self) -> None:
        for point in OPERATING_POINTS:
            with self.subTest(point=point):
                measured = self._measure(point)
                self.assertEqual(measured["plan"]["cogreen_forbidden_pairs"], 0)
                self.assertEqual(measured["plan"]["cogreen_name_rule_pairs"], 0)
                self.assertEqual(measured["plan"]["forbidden_pair_total"], 312)
                self.assertEqual(measured["plan"]["name_rule_pair_total"], 214)

    def test_the_name_rule_path_really_does_create_them(self) -> None:
        """양성 대조. 같은 harness·같은 산출물로 알려진 나쁜 수치가 나와야 한다.

        이것이 없으면 위 검사는 "harness 가 아무것도 재지 않아도" 통과한다.
        """
        for point in OPERATING_POINTS:
            with self.subTest(point=point):
                measured = self._measure(point)
                self.assertEqual(measured["name_rule"]["cogreen_forbidden_pairs"], 93)
                self.assertEqual(measured["name_rule"]["cogreen_name_rule_pairs"], 214)
                self.assertGreater(measured["name_rule"]["cogreen_sec_per_cycle"], 1000.0)

    def test_plan_driving_reproduces_the_model_native_share_exactly(self) -> None:
        """실현 녹색 / 모델이 예측하는 녹색 = 1. 이름 규칙에서는 최악 7.8~13.4 배다."""
        for point in OPERATING_POINTS:
            with self.subTest(point=point):
                measured = self._measure(point)
                plan = measured["plan"]
                self.assertEqual(plan["scored_signal_groups"], 116)
                self.assertEqual(plan["signal_groups_off_by_1pct"], 0)
                self.assertAlmostEqual(plan["worst_green_ratio"], 1.0, places=6)
                self.assertAlmostEqual(plan["min_green_ratio"], 1.0, places=6)
        native = self._measure("native")["name_rule"]
        asym = self._measure("asym80_35")["name_rule"]
        self.assertEqual(native["signal_groups_off_by_1pct"], 106)
        self.assertAlmostEqual(native["worst_green_ratio"], 7.8333, places=3)
        self.assertAlmostEqual(asym["worst_green_ratio"], 13.4286, places=3)

    def test_amber_never_covers_another_groups_green_in_the_real_plan(self) -> None:
        for point in OPERATING_POINTS:
            with self.subTest(point=point):
                self.assertEqual(self._measure(point)["plan"]["amber_over_green_cells"], 0)

    def test_ignoring_the_planned_window_bounds_breaks_the_real_plan(self) -> None:
        """되돌림 증명. 창 경계 판정을 빼면 위 두 검사가 실 계획에서 깨져야 한다.

        빼면 모든 SG 가 주기 내내 녹색이 되고, 금지 쌍 312개가 **전부** 동시녹색이 되며
        116개 SG 전부가 모델이 예측한 녹색과 어긋난다. 이 수치가 나오지 않으면 위
        검사들은 harness 가 아무것도 재지 않아도 통과하는 것이다.
        """
        mutant = SOURCE.replace(
            "            If position >= startSec And position < endSec Then",
            "            If position >= 0 Then",
        )
        self.assertNotEqual(mutant, SOURCE, "mutation target line not found")
        measured = self._measure("native", source=mutant)["plan"]
        self.assertEqual(measured["cogreen_forbidden_pairs"], 312)
        self.assertEqual(measured["signal_groups_off_by_1pct"], 116)

    def test_removing_the_amber_suppression_breaks_the_real_plan(self) -> None:
        """되돌림 증명. 방어를 빼면 실 계획에서 amber 가 남의 녹색을 덮어야 한다.

        합성 픽스처가 아니라 15 SC 전부에서 실제로 일어나는 것을 확인한다.
        """
        mutant = SOURCE.replace(
            "If Not AnySignalGroupGreenAt(scNo, position, cycleSec) Then", "If True Then"
        )
        self.assertNotEqual(mutant, SOURCE, "mutation target line not found")
        measured = self._measure("native", source=mutant)
        self.assertGreater(measured["plan"]["amber_over_green_cells"], 0)


# ---------------------------------------------------------------- 순수 계산부


def _plan_boundaries(windows, cycle: float) -> list[float]:
    points = {0.0, cycle}
    for window in windows:
        points.add(window.start_sec)
        points.add(window.end_sec)
        amber_end = window.end_sec + AMBER_SEC
        points.add(amber_end if amber_end <= cycle else amber_end - cycle)
    return sorted(value for value in sorted(points) if 0.0 <= value <= cycle)


def _axis_boundaries(major: float, minor: float, cycle: float) -> list[float]:
    points = {
        0.0,
        major,
        major + AMBER_SEC,
        major + AMBER_SEC + ALL_RED_SEC,
        major + AMBER_SEC + ALL_RED_SEC + minor,
        major + AMBER_SEC + ALL_RED_SEC + minor + AMBER_SEC,
        cycle,
    }
    return sorted(value for value in sorted(points) if 0.0 <= value <= cycle)


def _cells(points: list[float]) -> list[tuple[float, float]]:
    return [
        ((low + high) / 2.0, high - low)
        for low, high in zip(points, points[1:])
        if high - low > 1.0e-9
    ]


def _axis_states(pos: float, major: float, minor: float) -> tuple[str, str]:
    """러너 `ApplyRuntimeSignals` 의 축 스케줄 그대로."""
    if pos < major:
        return "GREEN", "RED"
    if pos < major + AMBER_SEC:
        return "AMBER", "RED"
    if pos < major + AMBER_SEC + ALL_RED_SEC:
        return "RED", "RED"
    if pos < major + AMBER_SEC + ALL_RED_SEC + minor:
        return "RED", "GREEN"
    if pos < major + AMBER_SEC + ALL_RED_SEC + minor + AMBER_SEC:
        return "RED", "AMBER"
    return "RED", "RED"


def _summarise(tag, lines, layout, per_sc, plan, forbidden, name_rule_pairs) -> dict:
    wanted = "P" if tag == "plan" else "N"
    index = 0
    green_sec: dict[tuple[str, str], float] = {}
    cogreen: set[tuple[str, str, str]] = set()
    cogreen_named: set[tuple[str, str, str]] = set()
    cogreen_sec = 0.0
    amber_over_green_cells = 0
    for kind, sc_no, cells in layout:
        if kind != wanted:
            continue
        info = per_sc[sc_no]
        for _, span in cells:
            states = {}
            for sg_no in info["sgs"]:
                parts = lines[index].split("|")
                assert parts[1] == str(int(sc_no)) and parts[2] == str(int(sg_no))
                states[sg_no] = parts[3]
                index += 1
            greens = [sg for sg in info["sgs"] if states[sg] == "GREEN"]
            if greens and any(states[sg] == "AMBER" for sg in info["sgs"]):
                amber_over_green_cells += 1
            for sg_no in greens:
                green_sec[(sc_no, sg_no)] = green_sec.get((sc_no, sg_no), 0.0) + span
            hit = False
            for position, first in enumerate(greens):
                for second in greens[position + 1 :]:
                    low, high = sorted((first, second), key=int)
                    if (sc_no, low, high) in forbidden:
                        cogreen.add((sc_no, low, high))
                        hit = True
                    if (sc_no, low, high) in name_rule_pairs:
                        cogreen_named.add((sc_no, low, high))
            if hit:
                cogreen_sec += span
    assert index == len(lines), (index, len(lines), tag)

    ratios: list[float] = []
    for sc_no in sorted(plan["controllers"], key=int):
        node = plan["controllers"][sc_no]
        info = per_sc[sc_no]
        major_phase = str(node["major_maps_to"])
        minor_phase = "p1" if major_phase == "p2" else "p2"
        for phase, commanded in ((major_phase, info["major"]), (minor_phase, info["minor"])):
            union = float(node["axis_green_sec"][phase])
            if union <= 0.0:
                continue
            for sg_no in node["phase_signal_groups"][phase]:
                native = float(node["native_green_sec"].get(sg_no, 0.0))
                if native <= 0.0:
                    continue
                expected = commanded * native / union
                ratios.append(green_sec.get((sc_no, sg_no), 0.0) / expected)
    return {
        "cogreen_forbidden_pairs": len(cogreen),
        "cogreen_name_rule_pairs": len(cogreen_named),
        "forbidden_pair_total": len(forbidden),
        "name_rule_pair_total": len(name_rule_pairs),
        "cogreen_sec_per_cycle": round(cogreen_sec, 6),
        "amber_over_green_cells": amber_over_green_cells,
        "scored_signal_groups": len(ratios),
        "worst_green_ratio": max(ratios),
        "min_green_ratio": min(ratios),
        "signal_groups_off_by_1pct": sum(1 for value in ratios if abs(value - 1.0) > 0.01),
    }


if __name__ == "__main__":
    unittest.main()
