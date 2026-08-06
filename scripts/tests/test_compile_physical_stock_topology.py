import copy
import hashlib
import json
import math
import random
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "plant"))

from build_vissim_lane_graph import build_lane_graph, semantic_payload as graph_semantic_payload
from compile_physical_stock_topology import (
    POSITION_TOLERANCE_M,
    compile_physical_stock_topology,
    deduplicated_visible_mass,
    evidence_identity_hashes,
    objective_evaluation,
    semantic_payload as topology_semantic_payload,
    weighted_objective,
)
from resolve_lane_routes import compile_route_proofs
from src.vissim_strict.topology import canonical_json_sha256


def road(no, lane_count=1, length=100.0):
    return {
        "id": f"link:{no}",
        "vissim_no": str(no),
        "name": f"road-{no}",
        "length_m": length,
        "geometry": [
            {"x_m": 0.0, "y_m": float(no), "z_m": 0.0},
            {"x_m": length, "y_m": float(no), "z_m": 0.0},
        ],
        "lanes": [
            {
                "id": f"lane:{no}:{lane_no}",
                "lane_no": lane_no,
                "width_m": 3.5,
                "closed": False,
            }
            for lane_no in range(1, lane_count + 1)
        ],
    }


def connector(
    no,
    from_link,
    to_link,
    *,
    lane_count=1,
    from_lane=1,
    to_lane=1,
    from_pos=80.0,
    to_pos=10.0,
    length=20.0,
):
    return {
        "id": f"connector:{no}",
        "vissim_no": str(no),
        "name": f"connector-{no}",
        "length_m": length,
        "lane_count": lane_count,
        "geometry": [
            {"x_m": from_pos, "y_m": float(from_link), "z_m": 0.0},
            {"x_m": to_pos, "y_m": float(to_link), "z_m": 0.0},
        ],
        "lanes": [
            {
                "id": f"lane:{no}:{lane_no}",
                "lane_no": lane_no,
                "width_m": 3.5,
                "closed": False,
            }
            for lane_no in range(1, lane_count + 1)
        ],
        "from_endpoint": {
            "link_no": str(from_link),
            "lane_no": from_lane,
            "position_m": from_pos,
        },
        "to_endpoint": {
            "link_no": str(to_link),
            "lane_no": to_lane,
            "position_m": to_pos,
        },
        "lane_mapping": [
            {
                "connector_lane_id": f"lane:{no}:{lane_no}",
                "from_lane_id": f"lane:{from_link}:{from_lane + lane_no - 1}",
                "to_lane_id": f"lane:{to_link}:{to_lane + lane_no - 1}",
            }
            for lane_no in range(1, lane_count + 1)
        ],
    }


def manifest(roads, connectors, signal_heads=()):
    return {
        "compiler_version": "fixture-compiler/1",
        "topology_hash": "fixture-topology",
        "validation_report": {"valid": True, "errors": []},
        "source": {"inpx_path": "fixture.inpx", "inpx_sha256": "pending"},
        "signal_reference": {
            "schema_version": "signal-reference-v2.1",
            "compiler_hash": "fixture-signal-hash",
        },
        "links": roads,
        "connectors": connectors,
        "signal_heads": list(signal_heads),
    }


def ownership(assignments, freeway=(), boundary=()):
    owner = {str(key): str(value) for key, value in assignments.items()}
    freeway_map = {str(key): str(value) for key, value in freeway}
    exits = [str(value) for value in boundary]
    return {
        "rule": "fixture exact ownership",
        "link_owner": owner,
        "freeway_bound_links": freeway_map,
        "monitor_only_exit_links": exits,
        "urban_link_count": len(owner) + len(freeway_map) + len(exits),
    }


def adjacency(*owners):
    values = {str(owner) for owner in owners}
    return {
        "adjacency": {owner: sorted(values - {owner}, key=int) for owner in sorted(values, key=int)},
        "internal_link_members": {},
    }


def capacity():
    return {
        "jam_density_veh_km_lane": 100.0,
        "jam_sample_count": 20,
        "source": "fixture-capacity",
        "ramp_queue_source": "fixture-ramp-capacity",
        "ramp_queue_max_veh_by_ramp": {
            "R_D_E": 10.0,
            "R_D_W": 11.0,
            "R_F_E": 12.0,
            "R_F_W": 13.0,
        },
    }


def compile_fixture(manifest_value, xml, ownership_value, adjacency_value):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "fixture.inpx"
        path.write_text(xml, encoding="utf-8")
        manifest_value = copy.deepcopy(manifest_value)
        manifest_value["source"]["inpx_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        graph = build_lane_graph(manifest_value)
        routes = compile_route_proofs(path, graph)
    capacity_value = capacity()
    topology = compile_physical_stock_topology(
        graph,
        routes,
        ownership_value,
        adjacency_value,
        capacity_value,
        expected_evidence_hashes=evidence_identity_hashes(
            ownership_value, adjacency_value, capacity_value
        ),
    )
    return graph, routes, topology


def route_xml(decisions):
    records = []
    for decision_no, link_no, position, routes in decisions:
        route_records = []
        for route_no, connector_no, destination, destination_position, relative_flow in routes:
            route_records.append(
                f'<vehicleRouteStatic no="{route_no}" destLink="{destination}" '
                f'destPos="{destination_position}" relFlow="{relative_flow}">'
                f'<linkSeq><intObjectRef key="{connector_no}"/></linkSeq>'
                "</vehicleRouteStatic>"
            )
        records.append(
            f'<vehicleRoutingDecisionStatic no="{decision_no}" link="{link_no}" '
            f'pos="{position}" routeChoiceMeth="STATIC"><vehRoutSta>'
            + "".join(route_records)
            + "</vehRoutSta></vehicleRoutingDecisionStatic>"
        )
    return "<network><vehicleRoutingDecisionsStatic>" + "".join(records) + "</vehicleRoutingDecisionsStatic></network>"


def serial_fixture(*, boundary=False, parallel=False):
    lane_count = 2 if parallel else 1
    roads = [road(1, lane_count), road(2, lane_count)]
    connectors = [connector(100, 1, 2, lane_count=lane_count)]
    heads = [
        {
            "id": "signal-head:501",
            "vissim_no": "501",
            "name": "duplicate-entry-stopline",
            "lane_ref": {
                "raw": "1 1",
                "link_no": "1",
                "lane_no": 1,
                "lane_id": "lane:1:1",
            },
            "position_m": 80.0 + POSITION_TOLERANCE_M / 2.0,
            "signal_group_ref": {"raw": "1 1", "controller_no": "1", "sg_no": 1},
        }
    ]
    own = ownership({1: 1, 100: 1}, boundary=[2] if boundary else [])
    if not boundary:
        own = ownership({1: 1, 2: 1, 100: 1})
    xml = route_xml([(1, 1, 10, [(1, 100, 2, 50, 1)])])
    return manifest(roads, connectors, heads), xml, own, adjacency(1)


class PhysicalStockTopologySyntheticTests(unittest.TestCase):
    def test_serial_duplicate_split_points_coalesce_and_cover_every_lane(self):
        graph, _, topology = compile_fixture(*serial_fixture())
        self.assertEqual(topology["status"], "PASS")
        self.assertEqual(
            {key: topology["production_gates"][key] for key in (
                "lane_interval_gaps",
                "lane_interval_overlaps",
                "lane_interval_missing_lanes",
                "lane_interval_nonpositive",
                "duplicate_stock_ids",
            )},
            {key: 0 for key in (
                "lane_interval_gaps",
                "lane_interval_overlaps",
                "lane_interval_missing_lanes",
                "lane_interval_nonpositive",
                "duplicate_stock_ids",
            )},
        )
        lane_one = [item for item in topology["stocks"] if item["lane_id"] == "lane:1:1"]
        self.assertEqual([(item["start_m"], item["end_m"]) for item in lane_one], [(0.0, 10.0), (10.0, 80.0), (80.0, 100.0)])
        self.assertEqual(len({item["id"] for item in topology["stocks"]}), len(topology["stocks"]))
        self.assertEqual({node["id"] for node in graph["nodes"]}, {item["lane_id"] for item in topology["stocks"]})

    def test_parallel_lane_stocks_remain_distinct(self):
        _, _, topology = compile_fixture(*serial_fixture(parallel=True))
        self.assertEqual(topology["status"], "PASS")
        connector_stocks = [item for item in topology["stocks"] if item["link_no"] == "100"]
        self.assertEqual({item["lane_no"] for item in connector_stocks}, {1, 2})
        self.assertEqual(len({item["id"] for item in connector_stocks}), len(connector_stocks))

    def test_split_shared_stock_uses_route_flow_shares_for_multiple_owners(self):
        roads = [road(1), road(2), road(3)]
        connectors = [connector(100, 1, 2), connector(101, 1, 3, from_pos=80.0)]
        xml = route_xml([(7, 1, 10, [(1, 100, 2, 50, 3), (2, 101, 3, 50, 1)])])
        own = ownership({1: 2, 2: 2, 3: 3, 100: 2, 101: 3})
        _, _, topology = compile_fixture(manifest(roads, connectors), xml, own, adjacency(2, 3))
        self.assertEqual(topology["status"], "PASS")
        shared = [
            item for item in topology["stocks"]
            if item["lane_id"] == "lane:1:1" and item["start_m"] >= 10.0 and item["end_m"] <= 80.0
        ]
        self.assertTrue(shared)
        self.assertTrue(all(
            item["control_owner_state"]["basis"]
            == "a1_local_decision_route_flow_shares"
            for item in shared
        ))
        for item in shared:
            self.assertAlmostEqual(item["control_owner_weights"]["urban:2"], 0.75)
            self.assertAlmostEqual(item["control_owner_weights"]["urban:3"], 0.25)
            self.assertEqual({membership["route_id"] for membership in item["route_memberships"]}, {"route:7:1", "route:7:2"})

    def test_unrelated_routing_decision_denominators_fail_closed(self):
        roads = [road(1), road(2), road(3)]
        connectors = [connector(100, 1, 2), connector(101, 1, 3, from_pos=80.0)]
        xml = route_xml([
            (7, 1, 10, [(1, 100, 2, 50, 3), (2, 101, 3, 50, 1)]),
            (8, 1, 10, [(1, 100, 2, 50, 1), (2, 101, 3, 50, 3)]),
        ])
        own = ownership({1: 2, 2: 2, 3: 3, 100: 2, 101: 3})
        _, _, topology = compile_fixture(
            manifest(roads, connectors), xml, own, adjacency(2, 3)
        )
        self.assertEqual(topology["status"], "FAIL")
        self.assertIn(
            "unsupported_multi_decision_owner_weights",
            {item["code"] for item in topology["reasons"]},
        )

    def test_merge_keeps_two_physical_upstreams_and_one_downstream_stock(self):
        roads = [road(1), road(2), road(3)]
        connectors = [connector(100, 1, 3), connector(101, 2, 3, to_pos=10.0)]
        xml = route_xml([
            (1, 1, 10, [(1, 100, 3, 50, 1)]),
            (2, 2, 10, [(1, 101, 3, 50, 1)]),
        ])
        own = ownership({1: 1, 2: 2, 3: 3, 100: 1, 101: 2})
        _, _, topology = compile_fixture(manifest(roads, connectors), xml, own, adjacency(1, 2, 3))
        self.assertEqual(topology["status"], "PASS")
        target = next(item for item in topology["stocks"] if item["lane_id"] == "lane:3:1" and item["start_m"] == 10.0)
        graph_incoming = [edge for edge in topology["stock_edges"] if edge["to_stock_id"] == target["id"] and edge["source_graph_edge_id"]]
        self.assertEqual(len(graph_incoming), 2)
        self.assertEqual(len({edge["from_stock_id"] for edge in graph_incoming}), 2)

    def test_boundary_modes_change_only_exact_boundary_contribution(self):
        _, _, topology = compile_fixture(*serial_fixture(boundary=True))
        self.assertEqual(topology["status"], "PASS")
        values = {item["id"]: index + 0.25 for index, item in enumerate(topology["stocks"])}
        edge_flows = {
            edge["id"]: index + 0.5
            for index, edge in enumerate(topology["stock_edges"])
        }
        boundary = math.fsum(values[item["id"]] for item in topology["stocks"] if "boundary_out" in item["roles"])
        default = weighted_objective(topology, values, "controller_default")
        with_boundary = weighted_objective(topology, values, "controller_with_boundary")
        self.assertAlmostEqual(with_boundary - default, boundary, places=12)
        self.assertAlmostEqual(weighted_objective(topology, values, "boundary_only"), boundary, places=12)
        traces = set()
        objectives = {}
        for mode in (
            "physical_total",
            "controller_default",
            "controller_with_boundary",
            "boundary_only",
        ):
            evaluation = objective_evaluation(topology, values, edge_flows, mode)
            objectives[mode] = evaluation["weighted_objective"]
            traces.add(json.dumps(
                evaluation["physical_trace"],
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8"))
        self.assertEqual(len(traces), 1)
        self.assertAlmostEqual(
            objectives["controller_with_boundary"]
            - objectives["controller_default"],
            boundary,
            places=12,
        )

    def test_visibility_iteration_deduplicates_global_mass_for_ten_orders(self):
        _, _, topology = compile_fixture(*serial_fixture(parallel=True))
        values = {item["id"]: (index + 1) / 7.0 for index, item in enumerate(topology["stocks"])}
        expected = math.fsum(values.values())
        viewers = sorted({viewer for item in topology["stocks"] for viewer in item["visible_to"]})
        for seed in range(10):
            shuffled = viewers[:]
            random.Random(seed).shuffle(shuffled)
            self.assertAlmostEqual(deduplicated_visible_mass(topology, values, shuffled), expected, places=12)

    def test_missing_parent_owner_adjacency_and_tampered_hash_fail_closed(self):
        graph, routes, topology = compile_fixture(*serial_fixture())
        self.assertEqual(topology["status"], "PASS")
        _, _, own, adj = serial_fixture()
        capacity_value = capacity()
        trusted = evidence_identity_hashes(own, adj, capacity_value)

        missing_parent = copy.deepcopy(graph)
        missing_parent["links"].pop()
        missing_parent["semantic_sha256"] = canonical_json_sha256(graph_semantic_payload(missing_parent))

        missing_owner = copy.deepcopy(own)
        del missing_owner["link_owner"]["2"]
        missing_owner["urban_link_count"] -= 1

        missing_adjacency = copy.deepcopy(adj)
        missing_adjacency["adjacency"] = {}

        stale_graph = copy.deepcopy(graph)
        stale_graph["nodes"][0]["name"] = "tampered"

        stale_routes = copy.deepcopy(routes)
        stale_routes["proofs"][0]["terminal_position_m"] += 1.0

        cases = {
            "missing_parent": (missing_parent, routes, own, adj),
            "missing_owner": (graph, routes, missing_owner, adj),
            "missing_adjacency": (graph, routes, own, missing_adjacency),
            "stale_graph": (stale_graph, routes, own, adj),
            "stale_routes": (graph, stale_routes, own, adj),
        }
        for name, (case_graph, case_routes, case_owner, case_adj) in cases.items():
            with self.subTest(name=name):
                artifact = compile_physical_stock_topology(
                    case_graph,
                    case_routes,
                    case_owner,
                    case_adj,
                    capacity_value,
                    expected_evidence_hashes=trusted,
                )
                self.assertEqual(artifact["status"], "FAIL")
                self.assertTrue(artifact["reasons"])

    def test_semantic_hash_ignores_source_file_byte_hashes(self):
        graph, routes, _ = compile_fixture(*serial_fixture())
        _, _, own, adj = serial_fixture()
        capacity_value = capacity()
        trusted = evidence_identity_hashes(own, adj, capacity_value)
        left = compile_physical_stock_topology(
            graph,
            routes,
            own,
            adj,
            capacity_value,
            source_file_sha256={"ownership": "a"},
            expected_evidence_hashes=trusted,
        )
        right = compile_physical_stock_topology(
            graph,
            routes,
            own,
            adj,
            capacity_value,
            source_file_sha256={"ownership": "b"},
            expected_evidence_hashes=trusted,
        )
        self.assertEqual(left["semantic_sha256"], right["semantic_sha256"])
        self.assertEqual(left["semantic_sha256"], canonical_json_sha256(topology_semantic_payload(left)))
        self.assertTrue({
            "scripts/build_vissim_lane_graph.py",
            "scripts/resolve_lane_routes.py",
            "scripts/compile_physical_stock_topology.py",
            "plant/src/vissim_strict/topology.py",
        }.issubset(left["command"]["source_sha256"]))

    def test_duplicate_boundary_identity_fails_closed(self):
        graph, routes, _ = compile_fixture(*serial_fixture(boundary=True))
        _, _, own, adj = serial_fixture(boundary=True)
        capacity_value = capacity()
        trusted = evidence_identity_hashes(own, adj, capacity_value)
        own["monitor_only_exit_links"].append("2")
        artifact = compile_physical_stock_topology(
            graph,
            routes,
            own,
            adj,
            capacity_value,
            expected_evidence_hashes=trusted,
        )
        self.assertEqual(artifact["status"], "FAIL")
        self.assertIn("legacy_partition_duplicate", {item["code"] for item in artifact["reasons"]})

    def test_ownership_adjacency_and_capacity_tampering_fail_trusted_hashes(self):
        graph, routes, _ = compile_fixture(*serial_fixture(boundary=True))
        _, _, own, adj = serial_fixture(boundary=True)
        capacity_value = capacity()
        trusted = evidence_identity_hashes(own, adj, capacity_value)

        swapped = copy.deepcopy(own)
        swapped["link_owner"]["2"] = swapped["link_owner"].pop("1")
        swapped["monitor_only_exit_links"] = ["1"]

        fake_adjacency = copy.deepcopy(adj)
        fake_adjacency["adjacency"]["1"].append("999")

        doubled_capacity = copy.deepcopy(capacity_value)
        doubled_capacity["jam_density_veh_km_lane"] *= 2.0

        for name, case_owner, case_adj, case_capacity in (
            ("partition_swap", swapped, adj, capacity_value),
            ("fake_adjacency", own, fake_adjacency, capacity_value),
            ("doubled_capacity", own, adj, doubled_capacity),
        ):
            with self.subTest(name=name):
                artifact = compile_physical_stock_topology(
                    graph,
                    routes,
                    case_owner,
                    case_adj,
                    case_capacity,
                    expected_evidence_hashes=trusted,
                )
                self.assertEqual(artifact["status"], "FAIL")
                self.assertEqual(artifact["stocks"], [])
                self.assertTrue({
                    "trusted_evidence_hash_mismatch",
                    "legacy_partition_identity_hash_mismatch",
                } & {item["code"] for item in artifact["reasons"]})

    def test_missing_trusted_hashes_fails_closed_with_global_contract(self):
        graph, routes, _ = compile_fixture(*serial_fixture())
        _, _, own, adj = serial_fixture()
        artifact = compile_physical_stock_topology(
            graph, routes, own, adj, capacity()
        )
        self.assertEqual(artifact["status"], "FAIL")
        self.assertEqual(artifact["stocks"], [])
        self.assertIn(
            "missing_trusted_evidence_hashes",
            {item["code"] for item in artifact["reasons"]},
        )
        self.assertTrue({
            "schema_version",
            "input_hashes",
            "command_version",
            "status",
            "reasons",
            "sample_dimensions",
            "units",
            "downstream_consumers",
        }.issubset(artifact))


if __name__ == "__main__":
    unittest.main()
