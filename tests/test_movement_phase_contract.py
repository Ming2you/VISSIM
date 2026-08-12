# movement 의 phase 가 상류 movement_phase_id 와 같은 4현시인지 고정한다
"""계획이 2현시로 남는 뿌리가 여기다.

계획의 `axis_green_sec` 는 `p3=0.0, p4=0.0` 인데, 그건 movement map 의
`phase_signal_groups` 에 p3/p4 가 없어서고, 그건 config 의 `urban_movements` 가
전부 `_p1`/`_p2` 라서다. 그 값은 8/5 에 상류가 2현시일 때 굳은 파생값이다.

movement 의 현시는 `approach`/`exit` **leg 키**에만 달렸다 — 링크 배정과 무관하므로
미해결 tie 승인 게이트와 직교한다. 그래서 배정을 건드리지 않고 이 필드만 고칠 수 있다.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.generate_real_world_distributed_players import (  # noqa: E402
    ensure_numsim_importable,
)


def _upstream_movement_phase_id():
    """vendor 의 규칙을 **파일 경로로** 싣는다 - `src` 라는 이름은 `plant/src` 와 겹친다."""
    import importlib.util

    source = ensure_numsim_importable() / "src" / "models" / "grid_topology.py"
    spec = importlib.util.spec_from_file_location("_upstream_grid_topology", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.movement_phase_id


movement_phase_id = _upstream_movement_phase_id()

PARENT = (
    REPO / "evaluation" / "configs"
    / "real_world_modi_pstack_distributed_core15n41_20260805.json"
)
REPAIRED = (
    REPO / "evaluation" / "configs"
    / "real_world_modi_pstack_distributed_core15n41p4_20260812.json"
)


def _network(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))["config_overrides"]["network"]


class MovementPhaseContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not REPAIRED.is_file():
            raise AssertionError(f"4현시 config 가 없다: {REPAIRED}")
        cls.parent = _network(PARENT)
        cls.fixed = _network(REPAIRED)

    def test_every_movement_phase_matches_the_upstream_rule(self) -> None:
        wrong = {
            name: (spec.get("phase"), movement_phase_id(spec["approach"], spec["exit"]))
            for name, spec in self.fixed["urban_movements"].items()
            if spec.get("phase")
            and str(spec["phase"]).rpartition("_")[2]
            != movement_phase_id(spec["approach"], spec["exit"])
        }
        self.assertEqual({}, wrong, f"상류 규칙과 어긋난 movement {len(wrong)}건")

    def test_all_four_phases_are_populated(self) -> None:
        axes = {
            str(spec["phase"]).rpartition("_")[2]
            for spec in self.fixed["urban_movements"].values()
            if spec.get("phase")
        }
        self.assertEqual({"p1", "p2", "p3", "p4"}, axes)

    def test_only_the_movement_phase_field_moved(self) -> None:
        """되돌림 증명의 반대편 - 이 파일이 부모와 다른 곳이 phase 하나뿐임을 든다.

        여기가 헐거우면 tie 승인 게이트를 우회해 다른 것까지 바꿔 놓고도 통과한다.
        """
        self.assertEqual(sorted(self.parent), sorted(self.fixed))
        for key in self.parent:
            if key != "urban_movements":
                self.assertEqual(self.parent[key], self.fixed[key], key)

        parent_mv, fixed_mv = self.parent["urban_movements"], self.fixed["urban_movements"]
        self.assertEqual(sorted(parent_mv), sorted(fixed_mv))
        for name, before in parent_mv.items():
            after = fixed_mv[name]
            self.assertEqual(sorted(before), sorted(after), name)
            for field in before:
                if field != "phase":
                    self.assertEqual(before[field], after[field], f"{name}.{field}")

    def test_the_parent_really_was_two_phase(self) -> None:
        """되돌림 증명 - 부모가 이미 4현시였다면 위 검사들은 아무것도 증명하지 않는다."""
        axes = {
            str(spec["phase"]).rpartition("_")[2]
            for spec in self.parent["urban_movements"].values()
            if spec.get("phase")
        }
        self.assertEqual({"p1", "p2"}, axes)


if __name__ == "__main__":
    unittest.main()
