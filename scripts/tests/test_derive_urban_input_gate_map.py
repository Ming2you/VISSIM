# 유입-게이트 대장 생성기의 방위 규칙과 상태 분류를 검사한다
"""`scripts/derive_urban_input_gate_map.py` 의 두 판정만 본다.

- `leg_from_name` — 진행방향 접미사에서 진입 leg (이름이 정본)
- `gate_on_leg` — 그 leg 에 boundary 게이트가 있는가, 없으면 사유는 무엇인가

산출된 대장 자체가 실 격자와 맞는지는 `tests/test_demand_contract.py` 가 본다.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.derive_urban_input_gate_map import build_rows, gate_on_leg, leg_from_name

GRID = {
    "SC1": {
        "S": {"type": "boundary", "in": "in_SC1_S", "out": "out_SC1_S"},
        "N_SC2": {"type": "grid", "neighbor": "SC2"},
        "E_R": {"type": "ramp"},
    }
}


class LegFromNameTests(unittest.TestCase):
    def test_travel_direction_suffix_gives_the_opposite_leg(self) -> None:
        self.assertEqual("S", leg_from_name("우리은행포이_NB"))
        self.assertEqual("N", leg_from_name("매봉터널_SB"))
        self.assertEqual("W", leg_from_name("대치역_EB"))
        self.assertEqual("E", leg_from_name("경기여고_WB"))

    def test_suffix_followed_by_a_parenthetical_still_counts(self) -> None:
        self.assertEqual("S", leg_from_name("구룡터널_NB(터널직진)"))

    def test_name_without_a_direction_suffix_is_undecided(self) -> None:
        self.assertIsNone(leg_from_name(""))
        self.assertIsNone(leg_from_name("Dummy Link 1"))
        # 접미사처럼 보이지만 단어의 일부인 것은 잡지 않는다.
        self.assertIsNone(leg_from_name("개포_NBX"))


class GateOnLegTests(unittest.TestCase):
    def test_boundary_leg_returns_the_declared_gate_name(self) -> None:
        self.assertEqual(("in_SC1_S", "mapped"), gate_on_leg("SC1", "S", GRID))

    def test_grid_and_ramp_legs_report_the_occupant(self) -> None:
        self.assertEqual(("", "leg_occupied_by_grid_neighbour"), gate_on_leg("SC1", "N", GRID))
        self.assertEqual(("", "leg_occupied_by_ramp"), gate_on_leg("SC1", "E", GRID))

    def test_absent_leg_and_absent_node_are_told_apart(self) -> None:
        self.assertEqual(("", "leg_absent_at_node"), gate_on_leg("SC1", "W", GRID))
        self.assertEqual(("", "node_absent_from_model"), gate_on_leg("SC9", "S", GRID))
        self.assertEqual(("", "leg_undetermined"), gate_on_leg("SC1", None, GRID))


class BuildRowsTests(unittest.TestCase):
    def _alignment(self, **overrides):
        vi = {
            "vehicle_input_no": "1",
            "link": "364",
            "name": "가_NB",
            "role": "urban_input",
            "entry_class": "named",
            "volumes_vph": [100.0, 150.0],
            "model_node": "SC1",
            "leg": {"link_geometry": "E"},
        }
        vi.update(overrides)
        return {"vehicle_inputs": [vi]}

    def test_named_input_uses_the_name_not_the_geometry(self) -> None:
        row = build_rows(self._alignment(), {"config_overrides": {"network": {"grid_node_legs": GRID}}})[0]
        self.assertEqual(("in_SC1_S", "mapped", "S", "name_suffix"),
                         (row["gate"], row["status"], row["leg"], row["leg_source"]))

    def test_unnamed_input_falls_back_to_geometry(self) -> None:
        alignment = self._alignment(name="", entry_class="unnamed",
                                    leg={"link_geometry": "S"})
        row = build_rows(alignment, {"config_overrides": {"network": {"grid_node_legs": GRID}}})[0]
        self.assertEqual(("in_SC1_S", "mapped", "S", "link_geometry"),
                         (row["gate"], row["status"], row["leg"], row["leg_source"]))

    def test_dummy_is_internal_and_freeway_is_excluded(self) -> None:
        cfg = {"config_overrides": {"network": {"grid_node_legs": GRID}}}
        dummy = build_rows(self._alignment(name="Dummy Link 1", entry_class="dummy"), cfg)[0]
        self.assertEqual(("", "internal"), (dummy["gate"], dummy["status"]))
        freeway = build_rows(self._alignment(link="26"), cfg)[0]
        self.assertEqual(("", "freeway_excluded"), (freeway["gate"], freeway["status"]))


if __name__ == "__main__":
    unittest.main()
