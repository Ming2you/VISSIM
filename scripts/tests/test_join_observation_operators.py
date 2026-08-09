# v3 N3-1a W2 - 관측 연산자(측정소/큐카운터)를 링크에 조인하는 모듈의 항등식·계수 고정 테스트
from __future__ import annotations

import json
import sys
import unittest
from collections import Counter
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
for _search_root in (REPO / "scripts",):
    if str(_search_root) not in sys.path:
        sys.path.insert(0, str(_search_root))

from join_observation_operators import (  # noqa: E402
    UNRESOLVED_NOT_IN_TOPOLOGY,
    UNRESOLVED_ON_CONNECTOR,
    UNRESOLVED_UNSUPPORTED_KIND,
    join_observation_operators,
    summarize_join,
)


TOPOLOGY_PATH = REPO / "evaluation" / "strict_plant_20260731" / "canonical_topology.json"


def _road_link(vissim_no: str) -> dict:
    return {"id": f"link:{vissim_no}", "kind": "road", "source": {"vissim_no": vissim_no}}


def _connector(vissim_no: str) -> dict:
    return {"id": f"connector:{vissim_no}", "kind": "connector", "source": {"vissim_no": vissim_no}}


def _dcp(vissim_no: str, link_no: str) -> dict:
    return {
        "id": f"observation:data-collection:{vissim_no}",
        "kind": "data_collection_point",
        "vissim_no": vissim_no,
        "position_m": 10.0,
        "lane_ref": {"link_no": link_no, "lane_no": 1},
    }


def _ttm(vissim_no: str, start_link_no: str, end_link_no: str) -> dict:
    return {
        "id": f"observation:travel-time:{vissim_no}",
        "kind": "travel_time_measurement",
        "vissim_no": vissim_no,
        "start": {"link_no": start_link_no, "position_m": 1.0},
        "end": {"link_no": end_link_no, "position_m": 2.0},
    }


def _queue(vissim_no: str, link_no: str) -> dict:
    return {
        "id": f"observation:queue-counter:{vissim_no}",
        "kind": "queue_counter",
        "vissim_no": vissim_no,
        "link_no": link_no,
        "position_m": 3.0,
    }


def _synthetic_topology() -> dict:
    """도로링크 1개 + 커넥터 1개 위에 3종 관측 연산자 6개를 올린 최소 지형."""
    return {
        "links": [_road_link("1")],
        "connectors": [_connector("900")],
        "observation_operators": [
            _dcp("1", "1"),  # 해석됨
            _dcp("2", "900"),  # 커넥터 위
            _dcp("3", "555"),  # 지형에 없음
            _ttm("10", "1", "1"),  # 해석됨
            _ttm("11", "1", "900"),  # 종점이 커넥터
            _queue("20", "900"),  # 커넥터 위
        ],
    }


class SyntheticJoinTests(unittest.TestCase):
    """항등식과 미해석 사유 분류를 합성 지형으로 못 박는다."""

    def setUp(self) -> None:
        self.topology = _synthetic_topology()
        self.result = join_observation_operators(self.topology)

    def test_resolved_plus_unresolved_equals_total(self) -> None:
        total = len(self.topology["observation_operators"])
        self.assertEqual(len(self.result.resolved) + len(self.result.unresolved), total)
        self.assertEqual(self.result.total, total)

    def test_no_operator_is_dropped_or_double_counted(self) -> None:
        """잔차로 균형 맞추기 금지 - id 집합이 정확히 분할돼야 한다."""
        expected = {item["id"] for item in self.topology["observation_operators"]}
        resolved_ids = {item["id"] for item in self.result.resolved}
        unresolved_ids = {item["id"] for item in self.result.unresolved}
        self.assertEqual(resolved_ids | unresolved_ids, expected)
        self.assertEqual(resolved_ids & unresolved_ids, set())
        self.assertEqual(len(resolved_ids), len(self.result.resolved))
        self.assertEqual(len(unresolved_ids), len(self.result.unresolved))

    def test_resolved_entries_carry_road_link_ids(self) -> None:
        by_id = {item["id"]: item for item in self.result.resolved}
        self.assertEqual(sorted(by_id), ["observation:data-collection:1", "observation:travel-time:10"])
        self.assertEqual(by_id["observation:data-collection:1"]["link_ids"], ["link:1"])
        self.assertEqual(by_id["observation:travel-time:10"]["link_ids"], ["link:1", "link:1"])
        endpoints = by_id["observation:travel-time:10"]["endpoints"]
        self.assertEqual([point["role"] for point in endpoints], ["start", "end"])
        self.assertEqual(endpoints[0]["link_id"], "link:1")
        self.assertEqual(endpoints[0]["position_m"], 1.0)

    def test_unresolved_entries_are_explicitly_accounted_with_reasons(self) -> None:
        by_id = {item["id"]: item for item in self.result.unresolved}
        self.assertEqual(
            sorted(by_id),
            [
                "observation:data-collection:2",
                "observation:data-collection:3",
                "observation:queue-counter:20",
                "observation:travel-time:11",
            ],
        )
        for item in by_id.values():
            self.assertTrue(item["reasons"], f"{item['id']} 에 사유가 없다")

        connector_case = by_id["observation:data-collection:2"]["reasons"]
        self.assertEqual(len(connector_case), 1)
        self.assertEqual(connector_case[0]["reason"], UNRESOLVED_ON_CONNECTOR)
        self.assertEqual(connector_case[0]["link_no"], "900")
        self.assertEqual(connector_case[0]["connector_id"], "connector:900")

        missing_case = by_id["observation:data-collection:3"]["reasons"]
        self.assertEqual(missing_case[0]["reason"], UNRESOLVED_NOT_IN_TOPOLOGY)

        travel_time_case = by_id["observation:travel-time:11"]["reasons"]
        self.assertEqual(len(travel_time_case), 1, "해석된 시점까지 사유로 세면 안 된다")
        self.assertEqual(travel_time_case[0]["role"], "end")
        self.assertEqual(travel_time_case[0]["reason"], UNRESOLVED_ON_CONNECTOR)

    def test_unknown_operator_kind_is_counted_not_dropped(self) -> None:
        topology = _synthetic_topology()
        topology["observation_operators"].append(
            {"id": "observation:mystery:1", "kind": "pedestrian_counter", "vissim_no": "1"}
        )
        result = join_observation_operators(topology)
        self.assertEqual(result.total, len(topology["observation_operators"]))
        unknown = [item for item in result.unresolved if item["id"] == "observation:mystery:1"]
        self.assertEqual(len(unknown), 1)
        self.assertEqual(unknown[0]["reasons"][0]["reason"], UNRESOLVED_UNSUPPORTED_KIND)

    def test_summary_counts_match_the_result(self) -> None:
        summary = summarize_join(self.result)
        self.assertEqual(summary["total"], 6)
        self.assertEqual(summary["resolved"], 2)
        self.assertEqual(summary["unresolved"], 4)
        self.assertEqual(summary["by_kind"]["data_collection_point"], {"total": 3, "resolved": 1, "unresolved": 2})
        self.assertEqual(summary["by_kind"]["travel_time_measurement"], {"total": 2, "resolved": 1, "unresolved": 1})
        self.assertEqual(summary["by_kind"]["queue_counter"], {"total": 1, "resolved": 0, "unresolved": 1})
        self.assertEqual(
            summary["unresolved_reasons"],
            {UNRESOLVED_ON_CONNECTOR: 3, UNRESOLVED_NOT_IN_TOPOLOGY: 1},
        )


@unittest.skipUnless(TOPOLOGY_PATH.exists(), f"canonical topology 없음: {TOPOLOGY_PATH}")
class RealTopologyJoinTests(unittest.TestCase):
    """실측 개포동 canonical topology 로 계수를 고정한다."""

    topology: dict

    @classmethod
    def setUpClass(cls) -> None:
        cls.topology = json.loads(TOPOLOGY_PATH.read_text(encoding="utf-8"))
        cls.result = join_observation_operators(cls.topology)

    def test_operator_and_link_table_sizes_are_pinned(self) -> None:
        self.assertEqual(len(self.topology["links"]), 448)
        self.assertEqual(len(self.topology["connectors"]), 770)
        self.assertEqual(len(self.topology["observation_operators"]), 479)

    def test_identity_holds_on_the_real_network(self) -> None:
        self.assertEqual(
            len(self.result.resolved) + len(self.result.unresolved),
            len(self.topology["observation_operators"]),
        )

    def test_counts_are_pinned(self) -> None:
        summary = summarize_join(self.result)
        self.assertEqual(summary["total"], 479)
        self.assertEqual(summary["resolved"], 459)
        self.assertEqual(summary["unresolved"], 20)
        self.assertEqual(
            summary["by_kind"]["data_collection_point"],
            {"total": 198, "resolved": 192, "unresolved": 6},
        )
        self.assertEqual(
            summary["by_kind"]["travel_time_measurement"],
            {"total": 191, "resolved": 182, "unresolved": 9},
        )
        self.assertEqual(
            summary["by_kind"]["queue_counter"],
            {"total": 90, "resolved": 85, "unresolved": 5},
        )

    def test_every_unresolved_endpoint_is_a_connector(self) -> None:
        reasons = Counter(
            reason["reason"] for item in self.result.unresolved for reason in item["reasons"]
        )
        self.assertEqual(reasons, Counter({UNRESOLVED_ON_CONNECTOR: 20}))

    def test_all_unresolved_travel_time_failures_are_on_the_end_endpoint(self) -> None:
        roles = Counter(
            reason["role"]
            for item in self.result.unresolved
            if item["kind"] == "travel_time_measurement"
            for reason in item["reasons"]
        )
        self.assertEqual(roles, Counter({"end": 9}))

    def test_resolved_link_ids_exist_in_the_link_table(self) -> None:
        link_ids = {link["id"] for link in self.topology["links"]}
        for item in self.result.resolved:
            for link_id in item["link_ids"]:
                self.assertIn(link_id, link_ids, f"{item['id']} 가 링크 테이블 밖을 가리킨다")


if __name__ == "__main__":
    unittest.main()
