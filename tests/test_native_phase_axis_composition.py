# SC1001/SC1004 의 모델 phase 축이 실 .sig 의 현시 구조와 같은 것을 재는지 고정한다
"""141.0 초와 72.0 초 중 무엇이 실망의 phase 인지 못박는 검사.

`native_phase_green.build_native_phase_share_table` 는 movement 의 녹색배분을

    share(m) = union_green(m 의 SG) / union_green(**축의 SG**)

로 만든다. 분모인 "축의 SG 집합" 은 `movement_signal_group_map_v3.json` 의
`phase_signal_groups` 에서 온다. 그 표가 SC1001/SC1004 의 p1 을
SG{2,3,4,5,7,8} = 141.0 s 로 잡고 있는데, 배정 혈통(`--link-assignment-json`)이
빠지면 이름 규칙 폴백으로 떨어져 SG{3,4,7,8} = 72.0 s 가 된다.

여기서 두 부류를 나눈다.

- `PlantAxisInvariantTests` — `.sig` 원본과 `.inpx` 신호두 기하만으로 실망의 축을
  세운다. 어떤 생성 산출물도 근거로 쓰지 않는다. 깨지면 망이 바뀐 것이다.
- `AxisCompositionKnownMismatchTests` — 지금 **깨져 있는** 것. 일부러 FAIL 한다.
  모델 격자 leg 방위가 물리 접근 leg 과 어긋나서 p1 이 두 축의 합집합이 된다.
"""

from __future__ import annotations

import json
import math
import sys
import unittest
import xml.etree.ElementTree as ET
from functools import lru_cache
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from evaluation.controllers.fixed_signal_schedule import NS_AXIS  # noqa: E402
from evaluation.controllers.native_phase_green import union_green_seconds  # noqa: E402
from plant.src.vissim_strict.signal_program import parse_sig  # noqa: E402

NETWORK_INPX = REPO / "network/real_world_gaepo_modi/modi_eval_rw_control.inpx"
ROLES_CSV = REPO / "evaluation/real_world_modi_inventory/signal_controller_roles.csv"
MOVEMENT_SG_MAP = REPO / "outputs/movement_signal_group_map_v3.json"
LINK_ASSIGNMENT = REPO / "outputs/link_player_assignment_20260805.json"
TUNING_JSON = REPO / "evaluation/configs/real_world_modi_pstack_distributed_core15n41_20260805.json"

# 프리웨이 인터페이스 두 교차로. 여기서만 격자 leg 방위와 물리 접근 방위가 갈린다.
INTERFACE_NODES = ("1001", "1004")

LEG8 = ("E", "NE", "N", "NW", "W", "SW", "S", "SE")


def bearing_leg(dx: float, dy: float) -> str:
    return LEG8[int((math.degrees(math.atan2(dy, dx)) % 360.0 + 22.5) // 45.0) % 8]


@lru_cache(maxsize=1)
def _network_root():
    return ET.parse(NETWORK_INPX).getroot()


@lru_cache(maxsize=1)
def _link_start_points() -> dict[str, tuple[float, float]]:
    out: dict[str, tuple[float, float]] = {}
    for link in _network_root().iter("link"):
        no = link.get("no")
        points = [(float(p.get("x")), float(p.get("y"))) for p in link.iter("linkPolyPoint")]
        if no and points:
            out[str(no)] = points[0]
    return out


@lru_cache(maxsize=1)
def _centroids() -> dict[str, tuple[float, float]]:
    import csv

    out: dict[str, tuple[float, float]] = {}
    with ROLES_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                xy = json.loads(row.get("centroid_xy") or "[]")
            except json.JSONDecodeError:
                continue
            if len(xy) == 2:
                out[str(row["no"])] = (float(xy[0]), float(xy[1]))
    return out


@lru_cache(maxsize=1)
def _head_links_by_group() -> dict[str, dict[str, frozenset[str]]]:
    """SC -> SG -> 그 SG 의 신호두가 붙은 링크들. `.inpx` 선언이 유일한 근거다."""
    out: dict[str, dict[str, set[str]]] = {}
    for head in _network_root().iter("signalHead"):
        sg_ref = str(head.get("sg", "")).split()
        lane_ref = str(head.get("lane", "")).split()
        if len(sg_ref) >= 2 and lane_ref:
            out.setdefault(sg_ref[0], {}).setdefault(sg_ref[1], set()).add(lane_ref[0])
    return {
        sc: {sg: frozenset(links) for sg, links in groups.items()}
        for sc, groups in out.items()
    }


@lru_cache(maxsize=None)
def _program(sc_no: str):
    """`.inpx` 의 supplyFile2 / progNo 가 가리키는 실 프로그램."""
    for controller in _network_root().findall(".//signalControllers/signalController"):
        if str(controller.get("no")) != str(sc_no):
            continue
        raw = str(controller.get("supplyFile2", "")).strip()
        if raw.lower().startswith("#data#"):
            raw = raw[6:]
        return parse_sig(NETWORK_INPX.parent / raw, int(controller.get("progNo", "1")))
    raise AssertionError(f"SC{sc_no} not in {NETWORK_INPX}")


def physical_axis_groups(sc_no: str) -> dict[str, frozenset[str]]:
    """SG 를 **물리 접근 방위**로 축에 나눈다. SG 이름은 쓰지 않는다.

    신호두가 붙은 링크의 시작점이 교차로 중심에서 어느 방위인가 — 그것이 접근 leg 이고,
    `fixed_signal_schedule.NS_AXIS` 가 그 방위를 모델 축(p1/p2)에 배정한다.
    """
    centroid = _centroids()[sc_no]
    starts = _link_start_points()
    axes: dict[str, set[str]] = {"p1": set(), "p2": set()}
    for sg_id, links in _head_links_by_group()[sc_no].items():
        legs = set()
        for link in links:
            point = starts.get(link)
            if point is None:
                continue
            legs.add(bearing_leg(point[0] - centroid[0], point[1] - centroid[1]))
        assert legs, f"SC{sc_no} SG{sg_id} has no head link geometry"
        phases = {"p1" if leg in NS_AXIS else "p2" for leg in legs}
        assert len(phases) == 1, f"SC{sc_no} SG{sg_id} straddles axes: {sorted(legs)}"
        axes[next(iter(phases))].add(sg_id)
    return {phase: frozenset(groups) for phase, groups in axes.items()}


def green_windows(program, group_ids) -> list[tuple[float, float]]:
    spans: list[tuple[float, float]] = []
    for group_id in group_ids:
        timeline = program.sg_timelines.get(str(group_id))
        if timeline is None:
            continue
        for interval in timeline.intervals:
            if interval.state == "GREEN":
                spans.append((interval.start_sec, interval.end_sec))
    return spans


def overlap_seconds(left, right) -> float:
    total = 0.0
    for a0, a1 in left:
        for b0, b1 in right:
            total += max(0.0, min(a1, b1) - max(a0, b0))
    return total


class PlantAxisInvariantTests(unittest.TestCase):
    """`.sig` + `.inpx` 만으로 세운 실망의 축. 생성 산출물을 근거로 쓰지 않는다."""

    def test_physical_axes_are_conflict_free_in_the_real_program(self) -> None:
        """두 축이 동시에 녹색인 시간이 0 이다. 이것이 '축 = 현시' 의 정의다."""
        for sc_no in INTERFACE_NODES:
            with self.subTest(sc=sc_no):
                axes = physical_axis_groups(sc_no)
                program = _program(sc_no)
                self.assertEqual(
                    0.0,
                    overlap_seconds(
                        green_windows(program, axes["p1"]),
                        green_windows(program, axes["p2"]),
                    ),
                    f"SC{sc_no}: p1{sorted(axes['p1'])} 과 p2{sorted(axes['p2'])} 가 겹친다",
                )

    def test_the_real_axis_green_is_72_and_69_seconds(self) -> None:
        """p1(NS)=72.0 s, p2(EW)=69.0 s. 주기 150 s, 청산 9 s."""
        for sc_no in INTERFACE_NODES:
            with self.subTest(sc=sc_no):
                axes = physical_axis_groups(sc_no)
                program = _program(sc_no)
                self.assertEqual(150.0, program.cycle_length_sec)
                self.assertAlmostEqual(72.0, union_green_seconds(program, axes["p1"]), places=6)
                self.assertAlmostEqual(69.0, union_green_seconds(program, axes["p2"]), places=6)

    def test_141_seconds_is_the_union_of_both_axes_not_a_phase(self) -> None:
        """141.0 s = 72 + 69. 한 현시가 주기의 94% 를 먹을 수는 없다."""
        for sc_no in INTERFACE_NODES:
            with self.subTest(sc=sc_no):
                axes = physical_axis_groups(sc_no)
                program = _program(sc_no)
                both = axes["p1"] | axes["p2"]
                self.assertAlmostEqual(141.0, union_green_seconds(program, both), places=6)
                self.assertAlmostEqual(
                    union_green_seconds(program, both),
                    union_green_seconds(program, axes["p1"])
                    + union_green_seconds(program, axes["p2"]),
                    places=6,
                    msg="두 축이 겹치지 않으므로 합집합 = 합",
                )


class AxisCompositionKnownMismatchTests(unittest.TestCase):
    """지금 깨져 있는 것. xfail 로 감추지 않는다.

    원인은 하나다 — `derive_intersection_adjacency.py` 가 격자 leg 방위를 두 교차로
    **중심 사이 방위각**으로 정하는데(:183), SC1001-SC1004 를 잇는 도로는 램프
    회랑이라 굽는다. 배정 산출물은 같은 링크의 물리 접근 방위를 이미 알고 있다
    (`link_leg["32"] = "W"`, `link_leg["71"] = "SW"`).
    """

    def test_map_axis_matches_the_plant_axis(self) -> None:
        """`movement_signal_group_map_v3.json` 의 p1/p2 가 실망의 축과 같아야 한다."""
        table = json.loads(MOVEMENT_SG_MAP.read_text(encoding="utf-8"))["controllers"]
        for sc_no in INTERFACE_NODES:
            with self.subTest(sc=sc_no):
                axes = physical_axis_groups(sc_no)
                mapped = table[f"SC{sc_no}"]["phase_signal_groups"]
                for phase in ("p1", "p2"):
                    self.assertEqual(
                        sorted(axes[phase], key=int),
                        sorted(mapped.get(phase, ()), key=int),
                        f"SC{sc_no} {phase}",
                    )

    def test_grid_leg_bearing_matches_the_physical_approach_bearing(self) -> None:
        """격자 leg 방위가 배정 산출물의 물리 접근 방위와 같아야 한다."""
        assignment = json.loads(LINK_ASSIGNMENT.read_text(encoding="utf-8"))
        legs = json.loads(TUNING_JSON.read_text(encoding="utf-8"))
        legs = legs["config_overrides"]["network"]["grid_node_legs"]
        # (소유 SC, 상류 SC) -> 그 접근을 나르는 정지선 링크의 물리 leg
        for owner, upstream, link in (("1001", "1004", "32"), ("1004", "1001", "71")):
            with self.subTest(sc=owner):
                self.assertEqual(owner, str(assignment["link_owner"][link]))
                self.assertEqual(upstream, str(assignment["link_upstream"][link]))
                physical = assignment["link_leg"][link]
                keys = [
                    key
                    for key, leg in legs[f"SC{owner}"].items()
                    if leg.get("type") == "grid" and leg.get("node") == f"SC{upstream}"
                ]
                self.assertEqual(1, len(keys), f"SC{owner} -> SC{upstream} leg keys {keys}")
                self.assertEqual(physical, keys[0].split("_", 1)[0])


if __name__ == "__main__":
    unittest.main()
