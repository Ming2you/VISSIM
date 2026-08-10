# v3 N4-2 - movement <-> (SC, SG번호) 유도가 토폴로지 근거로만 이뤄지는지 고정한다
from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
TOPOLOGY = REPO / "outputs" / "canonical_topology_v3.json"
TIMING = REPO / "outputs" / "signal_group_timing_v3.json"
CONFIG = (
    REPO
    / "evaluation"
    / "configs"
    / "real_world_modi_pstack_distributed_core15n41_20260805.json"
)
DETECTOR_MAPPING = (
    REPO
    / "evaluation"
    / "real_world_modi_control_distributed_20260728"
    / "detector_local_mapping_distributed_core15n41_20260805.json"
)


def _topology(links_with_heads, connectors):
    """최소 토폴로지 조각. signal_heads / connectors 두 절만 쓴다."""
    heads = []
    for index, (link_no, controller_no, sg_no) in enumerate(links_with_heads, start=1):
        heads.append(
            {
                "id": f"signal-head:{index}",
                "lane_ref": {"link_no": str(link_no), "lane_no": 1},
                "signal_group_ref": {"controller_no": str(controller_no), "sg_no": int(sg_no)},
            }
        )
    return {
        "compiler_version": "test",
        "source": {"inpx_path": "test.inpx", "inpx_sha256": "0" * 64},
        "signal_heads": heads,
        "connectors": [
            {
                "from_endpoint": {"link_no": str(a)},
                "to_endpoint": {"link_no": str(b)},
                "source": {"vissim_no": str(c)},
            }
            for a, c, b in connectors
        ],
    }


class OriginResolutionTests(unittest.TestCase):
    """요구 1 - origin 은 링크 위 신호두로 잡고, 못 잡으면 커넥터를 따라간다."""

    def test_origin_link_head_resolves_without_following_connectors(self) -> None:
        from scripts.derive_movement_signal_group_map import resolve_origin_signal_groups

        topology = _topology([("100", "1001", 2), ("100", "1001", 5)], [])
        result = resolve_origin_signal_groups(
            "SC1001", ("100",), topology=topology, max_hops=12
        )
        self.assertEqual(result.signal_groups, ("2", "5"))
        self.assertEqual(result.method, "origin_link_head")
        self.assertEqual(result.hops, 0)
        self.assertEqual(result.links, ("100",))

    def test_connector_chain_resolves_and_records_hop_count(self) -> None:
        from scripts.derive_movement_signal_group_map import resolve_origin_signal_groups

        # 200 -(9001)-> 201 -(9002)-> 202(신호두 SC1001 SG 3)
        topology = _topology(
            [("202", "1001", 3)],
            [("200", "9001", "201"), ("201", "9002", "202")],
        )
        result = resolve_origin_signal_groups(
            "SC1001", ("200",), topology=topology, max_hops=12
        )
        self.assertEqual(result.signal_groups, ("3",))
        self.assertEqual(result.method, "connector_chain")
        self.assertEqual(result.hops, 4)
        self.assertEqual(result.links, ("202",))

    def test_connector_chain_stops_at_a_foreign_signal_head(self) -> None:
        """다른 교차로를 통과해서까지 귀속시키지 않는다 - 그러면 아무 movement 나 이어진다."""
        from scripts.derive_movement_signal_group_map import resolve_origin_signal_groups

        topology = _topology(
            [("201", "2002", 1), ("202", "1001", 3)],
            [("200", "9001", "201"), ("201", "9002", "202")],
        )
        result = resolve_origin_signal_groups(
            "SC1001", ("200",), topology=topology, max_hops=12
        )
        self.assertIsNone(result.signal_groups)
        self.assertEqual(result.reason, "no_signal_head_downstream")

    def test_hop_budget_is_enforced(self) -> None:
        from scripts.derive_movement_signal_group_map import resolve_origin_signal_groups

        topology = _topology(
            [("202", "1001", 3)],
            [("200", "9001", "201"), ("201", "9002", "202")],
        )
        result = resolve_origin_signal_groups(
            "SC1001", ("200",), topology=topology, max_hops=3
        )
        self.assertIsNone(result.signal_groups)
        self.assertEqual(result.reason, "no_signal_head_downstream")

    def test_origin_without_any_link_is_named_not_guessed(self) -> None:
        from scripts.derive_movement_signal_group_map import resolve_origin_signal_groups

        topology = _topology([("100", "1001", 2)], [])
        result = resolve_origin_signal_groups(
            "SC1001", (), topology=topology, max_hops=12
        )
        self.assertIsNone(result.signal_groups)
        self.assertEqual(result.reason, "origin_link_unknown")


class SignalGroupPhaseTests(unittest.TestCase):
    """요구 2 - (SC, SG) -> 모델 phase 는 이름이 아니라 토폴로지가 먼저다."""

    def test_origin_movement_phase_beats_the_signal_group_name(self) -> None:
        from scripts.derive_movement_signal_group_map import derive_signal_group_phase

        # SG 2 는 이름이 EBT 라 이름 규칙이면 p2 다. 그런데 그 신호두가 붙은 링크 32 는
        # 모델에서 leg S 인 origin 이라 movement phase 는 p1 이다. 토폴로지가 이긴다.
        table = derive_signal_group_phase(
            group_names={"2": "EBT", "6": "WBT"},
            head_links_by_group={"2": ("32",), "6": ("29",)},
            link_to_origins={"32": ["SC1004_to_SC1001"], "29": ["SC1002_to_SC1001"]},
            origin_phases={"SC1004_to_SC1001": {"p1"}, "SC1002_to_SC1001": {"p2"}},
        )
        self.assertEqual(table["2"]["phase"], "p1")
        self.assertEqual(table["2"]["method"], "origin_movement")
        # 되돌림 증명 - origin 근거를 빼면 이름 규칙이 p2 를 준다.
        without_origin = derive_signal_group_phase(
            group_names={"2": "EBT", "6": "WBT"},
            head_links_by_group={"2": ("32",), "6": ("29",)},
            link_to_origins={},
            origin_phases={},
        )
        self.assertEqual(without_origin["2"]["phase"], "p2")
        self.assertEqual(without_origin["2"]["method"], "signal_group_name")

    def test_conflicting_origin_phases_fall_back_and_are_marked(self) -> None:
        from scripts.derive_movement_signal_group_map import derive_signal_group_phase

        table = derive_signal_group_phase(
            group_names={"2": "EBT"},
            head_links_by_group={"2": ("32", "33")},
            link_to_origins={"32": ["a"], "33": ["b"]},
            origin_phases={"a": {"p1"}, "b": {"p2"}},
        )
        self.assertEqual(table["2"]["method"], "signal_group_name_after_conflict")
        self.assertEqual(table["2"]["phase"], "p2")

    def test_nameless_signal_group_without_topology_is_unassigned(self) -> None:
        from scripts.derive_movement_signal_group_map import derive_signal_group_phase

        table = derive_signal_group_phase(
            group_names={"9": "보행"},
            head_links_by_group={},
            link_to_origins={},
            origin_phases={},
        )
        self.assertEqual(table["9"]["phase"], "")
        self.assertEqual(table["9"]["method"], "unassigned")


class RealNetworkDerivationTests(unittest.TestCase):
    """요구 3 - 실 네트워크에서 미해결이 사유별로 남김없이 계상된다."""

    @classmethod
    def setUpClass(cls) -> None:
        from scripts.derive_movement_signal_group_map import derive

        cls.payload = derive(
            topology_path=TOPOLOGY,
            timing_path=TIMING,
            config_path=CONFIG,
            detector_mapping_path=DETECTOR_MAPPING,
        )

    def test_every_phase_movement_is_accounted_exactly_once(self) -> None:
        counts = self.payload["counts"]
        self.assertEqual(counts["phase_movements"], 698)
        self.assertEqual(
            counts["resolved_movements"] + counts["unresolved_movements"],
            counts["phase_movements"],
        )
        self.assertEqual(
            sum(counts["unresolved_by_reason"].values()), counts["unresolved_movements"]
        )

    def test_off_ramp_origins_resolve_through_the_connector_chain(self) -> None:
        controllers = self.payload["controllers"]
        d_side = controllers["SC1001"]["origin_signal_groups"]
        f_side = controllers["SC1004"]["origin_signal_groups"]
        for origin in ("OR_D_W", "OR_D_E"):
            self.assertEqual(d_side[origin]["signal_groups"], ["2", "5"], origin)
            self.assertEqual(d_side[origin]["method"], "connector_chain", origin)
        for origin in ("OR_F_W", "OR_F_E"):
            self.assertEqual(f_side[origin]["signal_groups"], ["2", "5"], origin)
            self.assertEqual(f_side[origin]["method"], "connector_chain", origin)

    def test_merged_corridor_origin_resolves(self) -> None:
        # SC2005_to_SC1002 는 SC1002 에 자기 신호두가 없다. 링크 316 이 SC101 회랑에
        # 합류해 링크 329(SG 1,6)로 들어가므로 커넥터 추적으로만 잡힌다.
        entry = self.payload["controllers"]["SC1002"]["origin_signal_groups"][
            "SC2005_to_SC1002"
        ]
        self.assertEqual(entry["signal_groups"], ["1", "6"])
        self.assertEqual(entry["method"], "connector_chain")
        self.assertGreater(entry["hops"], 4)

    def test_unresolved_are_only_synthetic_boundary_legs(self) -> None:
        reasons = self.payload["counts"]["unresolved_by_reason"]
        self.assertEqual(set(reasons), {"synthetic_boundary_leg"})
        self.assertEqual(reasons["synthetic_boundary_leg"], 282)

        # 수치를 상수로만 두지 않는다 - 남은 미해결이 전부 모델이 심은 경계 게이트인지
        # config 의 grid_node_legs 로 직접 확인한다.
        network = json.loads(CONFIG.read_text(encoding="utf-8"))["config_overrides"]["network"]
        boundary = {
            str(leg.get("in", ""))
            for legs in network["grid_node_legs"].values()
            for leg in legs.values()
            if str(leg.get("type", "")) == "boundary"
        }
        movements = network["urban_movements"]
        for name in self.payload["unresolved_movements"]:
            self.assertIn(str(movements[name]["origin"]), boundary, name)

    def test_resolution_methods_are_all_accounted(self) -> None:
        methods = self.payload["counts"]["resolved_by_method"]
        self.assertEqual(
            methods,
            {"connector_chain": 53, "origin_link_head": 333, "shared_leg_bearing": 30},
        )
        self.assertEqual(self.payload["counts"]["resolved_movements"], 416)

    def test_timing_table_disagreement_is_reported_not_hidden(self) -> None:
        # outputs/signal_group_timing_v3.json 의 `.sig` 선택은 파일명 끝자리 숫자다.
        # 파일명 번호와 컨트롤러 번호가 어긋난 SC 가 있어 SG 목록이 실물과 다르다.
        self.assertEqual(
            self.payload["counts"]["timing_cross_check_disagreements"],
            ["SC11", "SC12", "SC5", "SC6"],
        )
        sc5 = self.payload["controllers"]["SC5"]["timing_cross_check"]
        self.assertEqual(sc5["inpx_signal_groups"], 24)
        self.assertEqual(sc5["timing_signal_groups"], 8)
        self.assertNotEqual(sc5["inpx_supply_file"], sc5["timing_sig_file"])

    def test_signal_group_phase_uses_topology_for_the_mismatched_legs(self) -> None:
        # SC1001 링크 32(SG 2,5)는 이름이 EBT/EBL 이라 이름 규칙이면 p2 다.
        # 모델은 그 접근로를 S_SC1004 로 보므로 p1 이어야 한다.
        phases = self.payload["controllers"]["SC1001"]["signal_group_phase"]
        self.assertEqual(phases["2"]["phase"], "p1")
        self.assertEqual(phases["5"]["phase"], "p1")
        self.assertEqual(phases["2"]["method"], "origin_movement")
        self.assertEqual(phases["6"]["phase"], "p2")

    def test_artifact_records_its_inputs(self) -> None:
        source = self.payload["source"]
        for key in (
            "topology_compiler_version",
            "inpx_sha256",
            "timing_sha256",
            "config_sha256",
            "detector_mapping_sha256",
        ):
            self.assertTrue(str(source.get(key, "")), key)

    def test_written_artifact_round_trips(self) -> None:
        import tempfile

        from scripts.derive_movement_signal_group_map import main

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "map.json"
            code = main(
                [
                    "--topology", str(TOPOLOGY),
                    "--timing", str(TIMING),
                    "--config", str(CONFIG),
                    "--detector-mapping", str(DETECTOR_MAPPING),
                    "--out", str(out),
                ]
            )
            self.assertEqual(code, 0)
            written = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(written["schema_version"], "movement-signal-group-map-v3")
        self.assertEqual(written["counts"], self.payload["counts"])


if __name__ == "__main__":
    unittest.main()
