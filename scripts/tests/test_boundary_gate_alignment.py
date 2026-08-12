# VISSIM 유입이 있는 (노드, 방위)에만 경계 leg 을 심는 생성기 경로를 고정하는 검사
from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/generate_real_world_distributed_players.py"
SPEC = importlib.util.spec_from_file_location("generate_real_world_distributed_players", MODULE_PATH)
assert SPEC and SPEC.loader
generator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generator)

REAL_ALIGNMENT = ROOT / "outputs/boundary_input_alignment_20260811.json"


class _VendorSrcIsolation(unittest.TestCase):
    """생성기는 vendor/NumSim-mine 의 `src.models` 를 임포트한다.

    전 스위트를 한 프로세스에서 돌리면 `scripts/tests/test_b1a_*` 가 임포트 시점에
    `plant` 를 sys.path 에 넣어 `sys.modules["src"]` 를 plant/src 로 선점한다.
    그러면 `src.models` 가 없어 ModuleNotFoundError 가 난다. 단독 실행에서는 안 난다.
    호출 구간에서만 바인딩을 걷어내고 tearDown 에서 원상복구해 다른 검사에 번지지 않게 한다.
    """

    def setUp(self) -> None:
        super().setUp()
        self._saved_src = {
            name: mod for name, mod in sys.modules.items()
            if name == "src" or name.startswith("src.")
        }
        self._saved_path = list(sys.path)
        for name in self._saved_src:
            del sys.modules[name]

    def tearDown(self) -> None:
        sys.path[:] = self._saved_path
        for name in [n for n in sys.modules if n == "src" or n.startswith("src.")]:
            del sys.modules[name]
        sys.modules.update(self._saved_src)
        super().tearDown()


def _vehicle_input(no: str, node: str, name: str, geometry_leg: str | None,
                   role: str = "urban_input", entry_class: str = "named",
                   volumes: list[float] | None = None) -> dict[str, object]:
    return {
        "vehicle_input_no": no,
        "name": name,
        "role": role,
        "entry_class": entry_class,
        "model_node": node,
        "volumes_vph": volumes if volumes is not None else [100.0, 150.0],
        "leg": {"link_geometry": geometry_leg, "assignment": geometry_leg},
    }


def _rows(*sc_numbers: int) -> list[dict[str, str]]:
    return [{"no": str(sc), "name": f"SC{sc}", "role": "urban"} for sc in sc_numbers]


class BoundaryGatePlanTests(unittest.TestCase):
    """(b) 이름 접미사가 기하보다 우선한다."""

    def test_name_suffix_beats_link_geometry(self) -> None:
        payload = {"vehicle_inputs": [
            # 진행방향 NB -> 접근 leg 은 S. 기하 추정은 SE 라고 말한다.
            _vehicle_input("114", "SC9001", "우리은행포이_NB", "SE"),
        ]}
        plan, evidence = generator.boundary_gate_plan_from_alignment(payload)
        self.assertEqual({"SC9001": ["S"]}, plan)
        self.assertEqual("name_suffix", evidence[0]["source"])

    def test_geometry_is_used_only_when_the_name_has_no_travel_suffix(self) -> None:
        payload = {"vehicle_inputs": [
            _vehicle_input("1100", "SC1004", "", "SE", entry_class="unnamed"),
        ]}
        plan, evidence = generator.boundary_gate_plan_from_alignment(payload)
        self.assertEqual({"SC1004": ["SE"]}, plan)
        self.assertEqual("link_geometry", evidence[0]["source"])

    def test_every_travel_suffix_maps_to_its_opposite_approach_leg(self) -> None:
        payload = {"vehicle_inputs": [
            _vehicle_input("1", "SC1", "a_NB", None),
            _vehicle_input("2", "SC2", "b_SB", None),
            _vehicle_input("3", "SC3", "c_EB", None),
            _vehicle_input("4", "SC4", "d_WB", None),
        ]}
        plan, _ = generator.boundary_gate_plan_from_alignment(payload)
        self.assertEqual({"SC1": ["S"], "SC2": ["N"], "SC3": ["W"], "SC4": ["E"]}, plan)

    def test_dummy_and_freeway_inputs_are_not_gates(self) -> None:
        payload = {"vehicle_inputs": [
            _vehicle_input("1083", "SC108", "Dummy link 1", "S", entry_class="dummy"),
            _vehicle_input("1098", "SC1001", "경부_EB", "W",
                           role="freeway_feeder_input_candidate", entry_class="freeway"),
            _vehicle_input("282", "SC16", "경기여고_WB", "E"),
        ]}
        plan, _ = generator.boundary_gate_plan_from_alignment(payload)
        self.assertEqual({"SC16": ["E"]}, plan)

    def test_real_alignment_yields_the_twenty_two_measured_entry_points(self) -> None:
        payload = json.loads(REAL_ALIGNMENT.read_text(encoding="utf-8"))
        plan, evidence = generator.boundary_gate_plan_from_alignment(payload)
        pairs = {(node, leg) for node, legs in plan.items() for leg in legs}
        self.assertEqual(22, len(evidence))
        self.assertEqual(22, len(pairs))
        self.assertIn(("SC1004", "SE"), pairs)
        self.assertIn(("SC1004", "SW"), pairs)
        self.assertIn(("SC13", "S"), pairs)
        # SC1 은 '구룡터널_NB(터널직진)' 다. 괄호가 붙어도 접미사가 잡혀야 한다.
        self.assertIn(("SC1", "S"), pairs)
        self.assertNotIn(("SC1", "SE"), pairs)
        self.assertNotIn(("SC9001", "SE"), pairs)


class MeasuredAdjacencyBeatsSymmetryTests(_VendorSrcIsolation):
    """양쪽 방위가 실측된 인접은 대칭화가 덮지 말아야 한다.

    실 도로망의 방위는 서로 정반대가 아니다. SC1001-SC1004 를 잇는 램프 회랑은 굽어서
    한쪽 접근이 W, 반대쪽이 SW 다(`link_player_assignment.link_leg` 의 링크 32/71).
    `derive_intersection_adjacency.py` 는 접근로 기하로 그 둘을 각각 맞게 낸다.

    생성기의 관대 대칭화는 **역방향이 없을 때** 정반대 방위를 합성하라는 것이지,
    있는 실측을 밀어내라는 것이 아니다. dict 순회 순서상 SC1001 을 먼저 처리하면
    SC1004 의 `SW_SC1001` 자리를 합성값 `E_SC1001` 이 선점한다.
    """

    ADJACENCY = {"1001": {"W_1004": 1004}, "1004": {"SW_1001": 1001}}

    def _legs(self, adjacency):
        override = generator.build_network_override(
            _rows(1001, 1004),
            include_freeway_interface_coupling=False,
            adjacency_legs=adjacency,
            boundary_gates={},
        )
        return {
            node: {k for k, spec in legs.items() if spec.get("type") == "grid"}
            for node, legs in override["grid_node_legs"].items()
        }

    def test_both_measured_bearings_survive(self) -> None:
        legs = self._legs(self.ADJACENCY)
        self.assertEqual({"W_SC1004"}, legs["SC1001"])
        self.assertEqual({"SW_SC1001"}, legs["SC1004"])

    def test_the_order_of_the_input_does_not_change_the_result(self) -> None:
        """되돌림 증명 - 순회 순서에 기대면 뒤집어 넣었을 때 답이 달라진다."""
        reversed_input = {"1004": {"SW_1001": 1001}, "1001": {"W_1004": 1004}}
        self.assertEqual(self._legs(self.ADJACENCY), self._legs(reversed_input))

    def test_a_one_sided_adjacency_still_gets_the_opposite_bearing(self) -> None:
        """대칭화 자체는 살아 있어야 한다 - 한쪽만 있으면 정반대를 만든다."""
        legs = self._legs({"1001": {"W_1004": 1004}})
        self.assertEqual({"W_SC1004"}, legs["SC1001"])
        self.assertEqual({"E_SC1001"}, legs["SC1004"])


class BoundaryGateOverrideTests(_VendorSrcIsolation):
    """(a) 정렬 입력이 주어지면 경계 leg 집합이 그것과 정확히 같다."""

    ADJACENCY = {"1": {"E_2": 2}, "2": {"W_1": 1}}

    def _boundary_legs(self, override: dict) -> set[str]:
        return {
            f"{node}_{str(key).split('_', 1)[0]}"
            for node, legs in override["grid_node_legs"].items()
            for key, spec in legs.items()
            if spec.get("type") == "boundary"
        }

    def test_boundary_legs_equal_the_plan_exactly(self) -> None:
        override = generator.build_network_override(
            _rows(1, 2),
            include_freeway_interface_coupling=False,
            adjacency_legs=self.ADJACENCY,
            boundary_gates={"SC1": ["S"], "SC2": ["NE"]},
        )
        self.assertEqual({"SC1_S", "SC2_NE"}, self._boundary_legs(override))
        self.assertEqual(["in_SC1_S", "in_SC2_NE"], sorted(override["boundary_in_links"]))
        self.assertEqual(["out_SC1_S", "out_SC2_NE"], sorted(override["boundary_out_links"]))

    def test_diagonal_gate_becomes_a_real_boundary_movement(self) -> None:
        override = generator.build_network_override(
            _rows(1, 2),
            include_freeway_interface_coupling=False,
            adjacency_legs=self.ADJACENCY,
            boundary_gates={"SC1": ["SE"]},
        )
        self.assertEqual({"type": "boundary", "in": "in_SC1_SE", "out": "out_SC1_SE",
                          "out_link": "SC1_SE_out"}, override["grid_node_legs"]["SC1"]["SE"])
        origins = {spec["origin"] for spec in override["urban_movements"].values()
                   if spec.get("kind") == "boundary_in"}
        self.assertIn("in_SC1_SE", origins)

    def test_gate_on_a_grid_occupied_bearing_is_merged_beside_the_grid_leg(self) -> None:
        override = generator.build_network_override(
            _rows(1, 2),
            include_freeway_interface_coupling=False,
            adjacency_legs=self.ADJACENCY,
            boundary_gates={"SC1": ["E"]},
        )
        legs = override["grid_node_legs"]["SC1"]
        at_e = {key: spec["type"] for key, spec in legs.items() if str(key).split("_", 1)[0] == "E"}
        self.assertEqual({"E_SC2": "grid", "E": "boundary"}, at_e)
        # 병합된 두 접근로는 같은 방위이므로 같은 phase 로 서비스된다. 4현시에서 E 는
        # minor 축이고 이 픽스처의 movement 는 직진뿐이라 p3 다(좌회전이 생기면 p4 가
        # 섞여 이 검사가 깨진다 - 그게 이 assertEqual 이 드는 것이다).
        phases = {
            spec["phase"]
            for spec in override["urban_movements"].values()
            if spec["intersection"] == "SC1" and spec["approach"] in {"E", "E_SC2"}
        }
        self.assertEqual({"SC1_p3"}, phases)

    def test_gate_on_a_ramp_bearing_fails_closed(self) -> None:
        # 램프 leg 는 맨 방위 키를 쓴다. 게이트를 그냥 대입하면 램프 결합이 조용히 사라진다.
        with self.assertRaises(SystemExit):
            generator.build_network_override(
                _rows(1001, 2),
                include_freeway_interface_coupling=True,
                ramp_interface_sc={"R_D_W": "SC1001", "R_D_E": "SC1001"},
                adjacency_legs={"1001": {"E_2": 2}, "2": {"W_1001": 1001}},
                boundary_gates={"SC1001": ["S"]},
            )

    def test_node_outside_the_model_fails_closed(self) -> None:
        with self.assertRaises(SystemExit):
            generator.build_network_override(
                _rows(1, 2),
                include_freeway_interface_coupling=False,
                adjacency_legs=self.ADJACENCY,
                boundary_gates={"SC1": ["S"], "SC99": ["N"]},
            )

    def test_without_the_plan_every_free_cardinal_stays_a_gate(self) -> None:
        override = generator.build_network_override(
            _rows(1, 2),
            include_freeway_interface_coupling=False,
            adjacency_legs=self.ADJACENCY,
        )
        self.assertEqual(
            {"SC1_N", "SC1_S", "SC1_W", "SC2_N", "SC2_S", "SC2_E"},
            self._boundary_legs(override),
        )


if __name__ == "__main__":
    unittest.main()
