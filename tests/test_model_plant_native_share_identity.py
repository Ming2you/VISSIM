# A2 - 모델의 native share 식과 플랜트의 plan_windows 실현 분수가 같은 분수인지 실 산출물로 고정한다
"""N4-5 착지 노트의 주장을 실 산출물에서 검증 가능한 형태로 못박는다.

## 주장

    모델   share(m) = union_green(m 의 SG 들) / union_green(축의 SG 들)
           (`evaluation/controllers/native_phase_green.py:259`)

    플랜트 SG g 의 실현 녹색 = 지시 축 녹색 x |g 의 native 녹색| / |축 native 녹색 합집합|
           (`evaluation/controllers/signal_group_plan.py:236 plan_windows`)

착지 노트는 이 둘이 **같은 분수**라고 적었지만 아무도 실 산출물로 대조하지 않았다.
여기서 15 SC · SG 136 개 · 지시 축 녹색 12 점(예산면 위와 밖)을 전수로 대조한다.

## 왜 합성 픽스처를 쓰지 않는가

2 노드 픽스처는 SG 가 축마다 하나씩이라 분자와 분모가 같아져 **무엇을 넣어도 통과한다**.
그래서 입력은 전부 실물이다 - inpx 가 가리키는 `.sig`, `movement_signal_group_map_v3.json`,
`signal_group_actuation_plan_v3.json`.

`test_the_identity_is_not_structural` 이 이 검사에 이빨이 있음을 증명한다. 계획의 창 분수를
N4-5 이전 이름 규칙(축의 모든 SG 가 축 창 전체를 받는다)으로 되돌리면 같은 코드 경로에서
같은 대조가 **깨져야** 한다.

## 무엇을 고정하지 않는가

창의 **위치** 는 여기서 고정하지 않는다. 모델은 p1 을 주기 머리에 두고 러너는 major 를
주기 머리에 두므로, `major_maps_to = "p2"` 인 14 SC 에서 축 창은 `major + amber + all_red`
만큼 회전해 있다. 그것은 이 항등식과 독립인 별개 사실이라 여기서 통과·실패로 다루지 않는다.
"""

from __future__ import annotations

import hashlib
import json
import sys
import unittest
from dataclasses import replace
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from evaluation.controllers import signal_group_plan  # noqa: E402
from evaluation.controllers.fixed_signal_schedule import (  # noqa: E402
    compile_fixed_signal_schedules,
)
from evaluation.controllers.native_phase_green import union_green_seconds  # noqa: E402

NETWORK = REPO / "network" / "real_world_gaepo_modi" / "modi_eval_rw_control.inpx"
PLAN = REPO / "outputs" / "signal_group_actuation_plan_v3.json"
MOVEMENT_MAP = REPO / "outputs" / "movement_signal_group_map_v3.json"

# 부동소수 허용오차. 실측 최대차는 2.8e-15 다.
TOLERANCE = 1.0e-12

# 지시 축 녹색 (major, minor). 예산면(모델 p1+p2 = effective_green_total = 110) 위와
# 밖을 모두 넣는다. write clamp 는 [5, 90] 이므로 그 두 끝도 넣는다.
COMMANDED = (
    (55.0, 55.0), (90.0, 20.0), (20.0, 90.0), (70.0, 40.0), (40.0, 70.0),
    (57.0, 57.0), (5.0, 90.0), (90.0, 5.0), (5.0, 5.0), (90.0, 90.0),
    (33.0, 77.0), (12.5, 97.5),
)


def _merged_length(spans) -> float:
    total = 0.0
    right = float("-inf")
    for left, edge in sorted(spans):
        if edge <= left:
            continue
        if left > right:
            total += edge - left
            right = edge
        elif edge > right:
            total += edge - right
            right = edge
    return total


class ModelPlantNativeShareIdentityTests(unittest.TestCase):
    """모델 share 와 플랜트 realize 분수가 같은 분수인가."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.table = json.loads(PLAN.read_text(encoding="utf-8"))
        cls.map = json.loads(MOVEMENT_MAP.read_text(encoding="utf-8"))
        nodes = sorted(
            payload["node_id"] for payload in cls.table["controllers"].values()
        )
        schedules, errors = compile_fixed_signal_schedules(NETWORK, nodes)
        missing = sorted(set(nodes) - set(schedules))
        assert not missing, f"실 inpx 에서 스케줄을 못 만든 노드 {missing}: {errors}"
        cls.schedules = schedules
        cls.amber = float(cls.table.get("amber_sec", 3.0))
        cls.all_red = float(cls.table.get("all_red_sec", 2.0))

    def _windows_by_group(self, payload, plan, major, minor):
        windows = signal_group_plan.plan_windows(
            plan,
            major_green=major,
            minor_green=minor,
            major_maps_to=str(payload["major_maps_to"]),
            amber_sec=self.amber,
            all_red_sec=self.all_red,
        )
        grouped: dict[str, list[tuple[float, float]]] = {}
        for window in windows:
            grouped.setdefault(window.sg_no, []).append(
                (float(window.start_sec), float(window.end_sec))
            )
        return grouped

    def _commanded_by_phase(self, payload, major, minor):
        major_phase = str(payload["major_maps_to"])
        minor_phase = "p1" if major_phase == "p2" else "p2"
        return {major_phase: float(major), minor_phase: float(minor)}

    def test_the_plan_divides_by_the_same_axis_set_the_model_divides_by(self) -> None:
        """분모가 같은 SG 집합인가. 여기가 어긋나면 아래 대조는 의미가 없다.

        계획은 매핑 산출물에서 만들어지므로 집합 대조만으로는 산출물이 **낡았을 때**를
        못 잡는다. 그래서 계획이 봉인한 sha256 이 지금 파일의 sha256 과 같은지 함께 본다.
        """
        for name, path in (
            ("movement_signal_group_map_sha256", MOVEMENT_MAP),
            ("network_sha256", NETWORK),
        ):
            with self.subTest(source=name):
                self.assertEqual(
                    str(self.table["source"][name]),
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                    f"{path.name} 이 계획이 봉인한 판과 다르다 - 계획을 다시 만들어야 한다",
                )
        for payload in self.table["controllers"].values():
            node = payload["node_id"]
            mapped = self.map["controllers"][node]["phase_signal_groups"]
            for phase in signal_group_plan.MODEL_PHASES:
                with self.subTest(node=node, phase=phase):
                    self.assertEqual(
                        sorted(payload["phase_signal_groups"].get(phase, ())),
                        sorted(str(value) for value in mapped.get(phase, ())),
                        f"{node} {phase}: 계획의 축 SG 집합이 매핑 산출물과 다르다",
                    )

    def test_every_planned_signal_group_realizes_its_native_share(self) -> None:
        """SG 136 개 전부 - 실현 녹색 / 지시 축 녹색 == native 배분."""
        checked = 0
        worst = (0.0, "")
        for payload in self.table["controllers"].values():
            node = payload["node_id"]
            program = self.schedules[node].program
            plan = signal_group_plan.node_plan_from_json(payload)
            axis_native = {
                phase: union_green_seconds(program, payload["phase_signal_groups"].get(phase, ()))
                for phase in signal_group_plan.MODEL_PHASES
            }
            for major, minor in COMMANDED:
                grouped = self._windows_by_group(payload, plan, major, minor)
                commanded = self._commanded_by_phase(payload, major, minor)
                for phase in signal_group_plan.MODEL_PHASES:
                    if axis_native[phase] <= 0.0 or commanded[phase] <= 0.0:
                        continue
                    for sg_no in payload["phase_signal_groups"].get(phase, ()):
                        model = union_green_seconds(program, (sg_no,)) / axis_native[phase]
                        plant = _merged_length(grouped.get(sg_no, ())) / commanded[phase]
                        checked += 1
                        if abs(model - plant) > worst[0]:
                            worst = (
                                abs(model - plant),
                                f"{node} sg{sg_no} {phase} 지시=({major},{minor}) "
                                f"모델={model!r} 플랜트={plant!r}",
                            )
        self.assertGreaterEqual(checked, 15 * len(COMMANDED) * 8, "대조 건수가 너무 적다")
        self.assertLessEqual(worst[0], TOLERANCE, f"가장 큰 어긋남: {worst[1]}")

    def test_every_resolved_origin_realizes_its_model_share(self) -> None:
        """분자가 SG 여럿인 movement 도 같은가.

        SG 하나짜리만 보면 합집합과 합이 같아져 통과가 보장된다. 매핑 산출물에서
        SG 를 둘 이상 잡는 origin 이 실제로 있으므로 그 경우를 함께 본다.
        """
        checked = 0
        multi_group_origins = 0
        worst = (0.0, "")
        for payload in self.table["controllers"].values():
            node = payload["node_id"]
            program = self.schedules[node].program
            plan = signal_group_plan.node_plan_from_json(payload)
            entry = self.map["controllers"][node]
            axis_native = {
                phase: union_green_seconds(program, payload["phase_signal_groups"].get(phase, ()))
                for phase in signal_group_plan.MODEL_PHASES
            }
            for origin, item in (entry.get("origin_signal_groups") or {}).items():
                groups = tuple(str(value) for value in item.get("signal_groups", ()))
                if not groups:
                    continue
                axis = next(
                    (
                        phase
                        for phase in signal_group_plan.MODEL_PHASES
                        if set(groups) <= set(payload["phase_signal_groups"].get(phase, ()))
                    ),
                    "",
                )
                self.assertTrue(axis, f"{node} {origin}: SG {groups} 가 한 축에 담기지 않는다")
                if len(groups) > 1:
                    multi_group_origins += 1
                model = union_green_seconds(program, groups) / axis_native[axis]
                for major, minor in COMMANDED:
                    grouped = self._windows_by_group(payload, plan, major, minor)
                    commanded = self._commanded_by_phase(payload, major, minor)[axis]
                    if commanded <= 0.0:
                        continue
                    spans = [span for sg in groups for span in grouped.get(sg, ())]
                    plant = _merged_length(spans) / commanded
                    checked += 1
                    if abs(model - plant) > worst[0]:
                        worst = (
                            abs(model - plant),
                            f"{node} {origin} sgs={groups} 지시=({major},{minor}) "
                            f"모델={model!r} 플랜트={plant!r}",
                        )
        self.assertGreater(multi_group_origins, 0, "SG 를 둘 이상 잡는 origin 이 하나도 없다")
        self.assertGreater(checked, 0)
        self.assertLessEqual(worst[0], TOLERANCE, f"가장 큰 어긋남: {worst[1]}")

    def test_the_commanded_axis_green_is_filled_without_leak(self) -> None:
        """축 SG 들의 실현 녹색 합집합이 지시 축 창을 빈틈없이 채우는가."""
        worst = (0.0, "")
        for payload in self.table["controllers"].values():
            node = payload["node_id"]
            plan = signal_group_plan.node_plan_from_json(payload)
            for major, minor in COMMANDED:
                grouped = self._windows_by_group(payload, plan, major, minor)
                commanded = self._commanded_by_phase(payload, major, minor)
                for phase in signal_group_plan.MODEL_PHASES:
                    span = commanded[phase]
                    if span <= 0.0:
                        continue
                    spans = [
                        window
                        for sg in payload["phase_signal_groups"].get(phase, ())
                        for window in grouped.get(sg, ())
                    ]
                    gap = abs(_merged_length(spans) - span)
                    if gap > worst[0]:
                        worst = (gap, f"{node} {phase} 지시={span} 실현={_merged_length(spans)}")
        self.assertLessEqual(worst[0], TOLERANCE, f"가장 큰 결손: {worst[1]}")

    def test_the_identity_is_not_structural(self) -> None:
        """이 항등식이 무엇을 넣어도 성립하는 것이 아님을 같은 코드 경로로 증명한다.

        계획의 창 분수를 N4-5 이전 이름 규칙 - 축의 모든 SG 가 축 창 **전체**를 받는다 -
        으로 되돌리면 위 대조가 크게 깨져야 한다. 실측 최대 어긋남을 함께 못박는다.
        """
        worst = 0.0
        for payload in self.table["controllers"].values():
            node = payload["node_id"]
            program = self.schedules[node].program
            plan = signal_group_plan.node_plan_from_json(payload)
            name_rule = replace(
                plan,
                phase_segments={
                    phase: tuple(
                        (sg_no, index, 0.0, 1.0)
                        for sg_no, index, _, _ in plan.phase_segments.get(phase, ())
                        if index == 0
                    )
                    for phase in signal_group_plan.MODEL_PHASES
                },
            )
            axis_native = {
                phase: union_green_seconds(program, payload["phase_signal_groups"].get(phase, ()))
                for phase in signal_group_plan.MODEL_PHASES
            }
            grouped = self._windows_by_group(payload, name_rule, 55.0, 55.0)
            commanded = self._commanded_by_phase(payload, 55.0, 55.0)
            for phase in signal_group_plan.MODEL_PHASES:
                if axis_native[phase] <= 0.0:
                    continue
                for sg_no in payload["phase_signal_groups"].get(phase, ()):
                    if not grouped.get(sg_no):
                        continue
                    model = union_green_seconds(program, (sg_no,)) / axis_native[phase]
                    plant = _merged_length(grouped[sg_no]) / commanded[phase]
                    worst = max(worst, abs(model - plant))
        self.assertGreater(
            worst,
            0.5,
            "이름 규칙으로 되돌려도 대조가 깨지지 않는다 - 위 검사는 구조적으로 통과하는 것이다",
        )


if __name__ == "__main__":
    unittest.main()
