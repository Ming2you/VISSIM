# 모델이 세우지 않는 저류(유령 *_out)를 생성기가 만들지 못하게 고정하는 검사
"""`urban_link_storage_veh` 의 모든 `*_out` 키는 실재하는 boundary leg 이 뒷받침해야 한다.

왜 문제인가. 모델은 `urban_link_storage_veh` 의 **모든 키에 스톡을 세우지만**
(`urban_queue_model.ensure_urban_state:391`), 그 스톡을 채우고 비우는 것은 leg 에서
유도된 movement 뿐이다. leg 이 없는 `SC{n}_{방위}_out` 은

  - 어느 movement 의 `receiving_link` 도 아니라 `sink_storage_links` 에 안 들어가고
    (`urban_queue_model.py:169-176`) 유한 출구용량 게이트가 비우지 않는다,
  - 어느 approach 의 origin 도 아니라 arrival 이 들어오지도 않는다,
  - 그런데 `state.total_urban_vehicles(net)` 는 저류 키 전수를 더하고
    (`models/state.py:1129-1132`), `boundary_leg_vehicles` 는 movement 가 참조하는
    boundary 저류만 빼므로(`:1209-1221`) 유령 점유는 리더 목적함수 base 와
    `protected_accumulation_veh` 에 그대로 남는다.

즉 어댑터가 관측 차량을 유령에 적재하면 그 차량은 **예측 지평 내내 얼지만 계상은 된다.**
2026-08-11 실측(capture_n41_20260805 상태 51개): 생산 격자에서 링크 218개 · 평균 360.9 대
(전 관측 2,652 대의 13.6%)가 유령으로 들어갔다.
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/generate_real_world_distributed_players.py"
SPEC = importlib.util.spec_from_file_location("generate_real_world_distributed_players", MODULE_PATH)
assert SPEC and SPEC.loader
generator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(generator)


class _VendorSrcIsolation(unittest.TestCase):
    """생성기가 임포트하는 vendor/NumSim-mine 의 `src` 바인딩을 호출 구간에서만 걷어낸다.

    이유는 `test_boundary_gate_alignment._VendorSrcIsolation` 과 같다 — 전 스위트 동시
    실행에서 `plant/src` 가 `sys.modules["src"]` 를 선점한다.
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


def _rows(*sc_numbers: int) -> list[dict[str, str]]:
    return [{"no": str(sc), "name": f"SC{sc}", "role": "urban"} for sc in sc_numbers]


ADJACENCY = {"1": {"E_2": 2}, "2": {"W_1": 1}}
# 유도 용량 대장은 배정 스크립트의 8방위 링크 기하로 이름을 짓는다
# (`derive_urban_storage_capacity.py:124`). 격자에 그 방위 게이트가 있는지는 안 본다.
CAPACITY = {
    "SC1_S_out": 111.0,     # 게이트 있음 -> 받아야 한다
    "SC1_NE_out": 222.0,    # 게이트 없음 -> 유령
    "SC2_SW_out": 333.0,    # 게이트 없음 -> 유령
    "SC1_to_SC2": 444.0,    # 내부 구간 -> 받아야 한다
    "SC2_to_SC1": 555.0,
}


def _out_storage_names(override: dict) -> set[str]:
    return {k for k in override["urban_link_storage_veh"] if str(k).endswith("_out")}


def _leg_out_links(override: dict) -> set[str]:
    return {
        spec["out_link"]
        for legs in override["grid_node_legs"].values()
        for spec in legs.values()
        if spec.get("type") == "boundary"
    }


class StorageKeysAreBackedByALegTests(_VendorSrcIsolation):
    def _override(self, boundary_gates):
        return generator.build_network_override(
            _rows(1, 2),
            include_freeway_interface_coupling=False,
            adjacency_legs=ADJACENCY,
            storage_capacity=CAPACITY,
            boundary_gates=boundary_gates,
        )

    def test_out_storage_exists_only_where_a_boundary_leg_exists(self) -> None:
        override = self._override({"SC1": ["S"]})
        self.assertEqual(_leg_out_links(override), _out_storage_names(override))
        self.assertNotIn("SC1_NE_out", override["urban_link_storage_veh"])
        self.assertNotIn("SC2_SW_out", override["urban_link_storage_veh"])

    def test_a_gated_bearing_still_takes_its_measured_capacity(self) -> None:
        override = self._override({"SC1": ["S"]})
        self.assertAlmostEqual(111.0, override["urban_link_storage_veh"]["SC1_S_out"])

    def test_internal_segments_are_untouched(self) -> None:
        override = self._override({"SC1": ["S"]})
        storage = override["urban_link_storage_veh"]
        self.assertAlmostEqual(444.0, storage["SC1_to_SC2"])
        self.assertAlmostEqual(555.0, storage["SC2_to_SC1"])

    def test_adding_the_gate_is_what_admits_the_storage(self) -> None:
        """음성 대조 — 같은 용량 대장이라도 게이트가 생기면 그 이름이 살아난다."""
        without = self._override({"SC1": ["S"]})
        with_gate = self._override({"SC1": ["S", "NE"], "SC2": ["SW"]})
        self.assertNotIn("SC1_NE_out", without["urban_link_storage_veh"])
        self.assertAlmostEqual(222.0, with_gate["urban_link_storage_veh"]["SC1_NE_out"])
        self.assertAlmostEqual(333.0, with_gate["urban_link_storage_veh"]["SC2_SW_out"])

    def test_every_storage_key_is_a_model_object(self) -> None:
        """leg·movement 어느 쪽도 참조하지 않는 저류가 하나도 없어야 한다."""
        override = self._override({"SC1": ["S"], "SC2": ["N"]})
        referenced = set(_leg_out_links(override))
        for spec in override["urban_movements"].values():
            for key in ("receiving_link", "origin", "destination"):
                value = str(spec.get(key) or "")
                if value:
                    referenced.add(value)
        for node, legs in override["grid_node_legs"].items():
            for leg_key, spec in legs.items():
                if spec.get("type") == "grid":
                    referenced.add(f"{node}_to_{spec['node']}")
                    referenced.add(f"{spec['node']}_to_{node}")
        orphans = sorted(set(override["urban_link_storage_veh"]) - referenced)
        self.assertEqual([], orphans, f"모델이 세우지 않는 저류: {orphans}")


class UnroutableLinksAreCountedNotSprayedTests(_VendorSrcIsolation):
    """권위 라우팅이 저류를 못 찾으면 방위 살포를 남기지 말고 명시적으로 계상해야 한다."""

    def _mapping(self):
        override = generator.build_network_override(
            _rows(1, 2),
            include_freeway_interface_coupling=False,
            adjacency_legs=ADJACENCY,
            storage_capacity=CAPACITY,
            boundary_gates={"SC1": ["S"]},
        )
        assignment = {
            # 링크 900 은 SC1 의 NE 접근 — 그 방위에 게이트가 없다(유령이던 자리).
            "link_owner": {"900": 1, "901": 1},
            "link_leg": {"900": "NE", "901": "S"},
            "link_upstream": {},
            "freeway_bound_links": {},
            "monitor_only_exit_links": [],
        }
        detector = generator.build_detector_mapping(
            {"observable_links": [], "link_to_origins": {}, "link_to_movements": {},
             "ramp_link_to_queues": {}, "agents": {}, "guardrails": {}},
            _rows(1, 2),
            [],
            override,
            "test2",
            {1: {"900": {"NS"}, "901": {"NS"}}, 2: {}},
            {"900": 1, "901": 1},
            link_assignment=assignment,
        )
        return override, detector

    def test_a_link_with_no_model_storage_gets_no_origin(self) -> None:
        _, detector = self._mapping()
        self.assertEqual([], detector["link_to_origins"].get("900"),
                         "저류를 못 찾은 링크에 방위 살포가 남아 있다")

    def test_the_routed_link_still_reaches_its_gate(self) -> None:
        _, detector = self._mapping()
        self.assertEqual(["SC1_S_out"], detector["link_to_origins"].get("901"))

    def test_unrouted_links_are_listed_with_the_name_they_wanted(self) -> None:
        _, detector = self._mapping()
        ledger = detector["link_partition"]["unrouted_links"]
        self.assertEqual({"900": "SC1_NE_out"}, ledger)

    def test_no_origin_ever_names_a_non_storage(self) -> None:
        override, detector = self._mapping()
        storages = set(override["urban_link_storage_veh"])
        dangling = sorted(
            f"{link}->{origin}"
            for link, origins in detector["link_to_origins"].items()
            for origin in origins
            if origin not in storages
        )
        self.assertEqual([], dangling, f"모델에 없는 저류를 가리키는 origin: {dangling}")


class ShippedConfigsCarryNoGhostStorageTests(unittest.TestCase):
    """산출된 config 자체에도 같은 불변식을 건다 — 손으로 고친 것도 잡힌다.

    아직 닫히지 않은 것은 `KNOWN_OPEN` 에 **개수까지** 적는다. 개수를 적어 두면
    (a) 늘어나면 실패하고 (b) 고쳐서 0 이 되면 "목록에서 빼라" 고 실패한다.
    """

    # 2026-08-11 실측. 열려 있는 이유가 서로 다르다.
    #   core15n41/full_20260805 — 생산 계열. 배정 승인 매니페스트가 미서명이라
    #       `--link-assignment-json` 재생성이 가드에 막힌다. 승인 후 재생성하면 닫힌다.
    #   v6/v7_urban* — 상류 default.yaml 의 장난감 격자 이름(A_top_out 등)이
    #       config override 에 그대로 실려 있다. 실 격자와 무관하고 관측이 닿지 않는다.
    KNOWN_OPEN = {
        "real_world_modi_pstack_distributed_core15full_20260805.json": 56,
        "real_world_modi_pstack_distributed_core15n41_20260805.json": 56,
        "real_world_modi_pstack_v6_urban15_20260804.json": 7,
        "real_world_modi_pstack_v7_urban36_20260804.json": 7,
    }

    def _ghosts(self, network) -> list[str]:
        legs = network.get("grid_node_legs") or {}
        gates = {
            str(spec["out_link"])
            for node_legs in legs.values()
            for spec in node_legs.values()
            if spec.get("type") == "boundary"
        }
        return sorted(
            key for key in (network.get("urban_link_storage_veh") or {})
            if str(key).endswith("_out") and str(key) not in gates
        )

    def test_no_config_grows_a_new_ghost_storage(self) -> None:
        import json

        checked = 0
        for path in sorted((ROOT / "evaluation/configs").glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            network = (payload.get("config_overrides") or {}).get("network") or {}
            if not network.get("urban_link_storage_veh") or not network.get("grid_node_legs"):
                continue
            checked += 1
            ghosts = self._ghosts(network)
            expected = self.KNOWN_OPEN.get(path.name, 0)
            self.assertEqual(
                expected, len(ghosts),
                f"{path.name}: leg 없는 *_out 저류 {len(ghosts)}개 (기대 {expected}개) {ghosts[:6]}",
            )
        self.assertGreaterEqual(checked, 10, "검사 대상 config 를 못 찾았다")

    def test_the_two_promotion_candidates_are_clean(self) -> None:
        import json

        for name in (
            "real_world_modi_pstack_distributed_core15n41gated_20260811.json",
            "real_world_modi_pstack_distributed_core15n41ungated_20260811.json",
        ):
            payload = json.loads((ROOT / "evaluation/configs" / name).read_text(encoding="utf-8"))
            network = payload["config_overrides"]["network"]
            self.assertEqual([], self._ghosts(network), name)


if __name__ == "__main__":
    unittest.main()
