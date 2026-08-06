import copy
import hashlib
import math
import random
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "plant"))

from build_vissim_lane_graph import (
    build_lane_graph,
    semantic_payload as graph_semantic_payload,
    validate_lane_graph_artifact,
)
from resolve_lane_routes import (
    compile_route_proofs,
    parse_relative_flow,
    resolve_route_paths,
)
from src.vissim_strict.topology import canonical_json_sha256


def road(no, lane_count, length=100.0):
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


def connector(no, from_link, from_lane, to_link, to_lane, lane_count, from_pos, to_pos, length=20.0):
    mappings = []
    for lane_no in range(1, lane_count + 1):
        mappings.append(
            {
                "connector_lane_id": f"lane:{no}:{lane_no}",
                "from_lane_id": f"lane:{from_link}:{from_lane + lane_no - 1}",
                "to_lane_id": f"lane:{to_link}:{to_lane + lane_no - 1}",
            }
        )
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
        "lane_mapping": mappings,
    }


def manifest_fixture():
    connectors = [
        connector(100, 1, 1, 2, 1, 2, 80.0, 10.0),
        connector(101, 2, 1, 3, 1, 1, 70.0, 0.0, 10.0),
        connector(102, 2, 2, 3, 1, 1, 75.0, 0.0, 12.0),
    ]
    return {
        "compiler_version": "fixture-compiler/1",
        "topology_hash": "fixture-topology-hash",
        "validation_report": {"valid": True, "errors": []},
        "source": {"inpx_path": "fixture.inpx", "inpx_sha256": "fixture-input-hash"},
        "signal_reference": {
            "schema_version": "signal-reference-v2.1",
            "compiler_hash": "fixture-signal-compiler-hash",
        },
        "links": [road(1, 2), road(2, 2), road(3, 1)],
        "connectors": connectors,
        "signal_heads": [
            {
                "id": "signal-head:501",
                "vissim_no": "501",
                "name": "fixture-stopline",
                "lane_ref": {
                    "raw": "2 1",
                    "link_no": "2",
                    "lane_no": 1,
                    "lane_id": "lane:2:1",
                },
                "position_m": 60.0,
                "signal_group_ref": {
                    "raw": "12 3",
                    "controller_no": "12",
                    "sg_no": 3,
                },
            }
        ],
    }


VALID_ROUTES_XML = """<?xml version="1.0" encoding="UTF-8"?>
<network><vehicleRoutingDecisionsStatic>
  <vehicleRoutingDecisionStatic no="7" link="1" pos="10" routeChoiceMeth="STATIC">
    <vehRoutSta>
      <vehicleRouteStatic no="1" name="lane-one" destLink="3" destPos="50" relFlow="2 0:1 1000:3">
        <linkSeq><intObjectRef key="100"/><intObjectRef key="2"/><intObjectRef key="101"/></linkSeq>
      </vehicleRouteStatic>
      <vehicleRouteStatic no="2" name="lane-two" destLink="3" destPos="50" relFlow="2 0:1 1000:1">
        <linkSeq><intObjectRef key="100"/><intObjectRef key="2"/><intObjectRef key="102"/></linkSeq>
      </vehicleRouteStatic>
    </vehRoutSta>
  </vehicleRoutingDecisionStatic>
</vehicleRoutingDecisionsStatic></network>
"""


def route_record(start_link, start_pos, sequence, destination_link, destination_pos):
    return {
        "id": "route:test:1",
        "decision_no": "test",
        "route_no": "1",
        "decision_link_no": str(start_link),
        "decision_position_m": float(start_pos),
        "link_sequence_vissim_nos": [str(value) for value in sequence],
        "destination_link_no": str(destination_link),
        "destination_position_m": float(destination_pos),
    }


def one_lane_connector_manifest():
    return {
        **manifest_fixture(),
        "links": [road(1, 2), road(2, 1)],
        "connectors": [connector(100, 1, 1, 2, 1, 1, 80.0, 10.0)],
        "signal_heads": [],
    }


def compile_xml(xml_text, graph):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "routes.inpx"
        path.write_text(xml_text, encoding="utf-8")
        supplied_graph = copy.deepcopy(graph)
        supplied_graph["source"]["input_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        return compile_route_proofs(path, supplied_graph)


def rehash_graph(graph):
    graph["semantic_sha256"] = canonical_json_sha256(graph_semantic_payload(graph))
    return graph


class VissimLaneGraphUnitTests(unittest.TestCase):
    def setUp(self):
        self.graph = build_lane_graph(manifest_fixture())

    def test_multi_lane_connector_range_has_exact_directed_edges(self):
        self.assertEqual(self.graph["status"], "PASS")
        connector = next(item for item in self.graph["connectors"] if item["connector_no"] == "100")
        self.assertEqual(
            [
                (item["connector_lane_id"], item["from_lane_id"], item["to_lane_id"])
                for item in connector["lane_mapping"]
            ],
            [
                ("lane:100:1", "lane:1:1", "lane:2:1"),
                ("lane:100:2", "lane:1:2", "lane:2:2"),
            ],
        )
        for lane_no in (1, 2):
            edges = [
                edge
                for edge in self.graph["edges"]
                if edge["connector_no"] == "100" and edge["connector_lane_no"] == lane_no
            ]
            self.assertEqual([edge["kind"] for edge in edges], ["connector_entry", "connector_exit"])
        self.assertEqual(self.graph["signal_heads"][0]["signal_controller_no"], "12")
        self.assertEqual(self.graph["signal_heads"][0]["signal_group_no"], 3)

    def test_incomplete_swapped_and_reversed_connector_evidence_fails(self):
        missing = manifest_fixture()
        missing["connectors"][0]["lane_mapping"].pop()
        missing_graph = build_lane_graph(missing)
        self.assertEqual(missing_graph["status"], "FAIL")
        self.assertEqual(missing_graph["production_gates"]["unresolved_connector_lane_mappings"], 1)
        self.assertLess(missing_graph["production_gates"]["executable_connector_path_coverage"], 1.0)

        swapped = manifest_fixture()
        mapping = swapped["connectors"][0]["lane_mapping"][0]
        mapping["from_lane_id"], mapping["to_lane_id"] = (
            mapping["to_lane_id"], mapping["from_lane_id"]
        )
        swapped_graph = build_lane_graph(swapped)
        self.assertEqual(swapped_graph["status"], "FAIL")
        self.assertEqual(swapped_graph["production_gates"]["reverse_synthetic_edges"], 1)

        endpoint_swap = manifest_fixture()
        value = endpoint_swap["connectors"][0]
        value["from_endpoint"], value["to_endpoint"] = (
            value["to_endpoint"], value["from_endpoint"]
        )
        endpoint_graph = build_lane_graph(endpoint_swap)
        self.assertEqual(endpoint_graph["status"], "FAIL")
        self.assertGreater(
            endpoint_graph["production_gates"]["unresolved_connector_lane_mappings"], 0
        )

    def test_connector_declared_lane_nodes_and_mapping_are_one_to_one(self):
        duplicate = manifest_fixture()
        duplicate["connectors"][0]["lane_mapping"].append(
            copy.deepcopy(duplicate["connectors"][0]["lane_mapping"][0])
        )
        graph = build_lane_graph(duplicate)
        self.assertEqual(graph["status"], "FAIL")
        self.assertGreater(graph["production_gates"]["unresolved_connector_lane_mappings"], 0)

        missing_node = manifest_fixture()
        missing_node["connectors"][0]["lanes"].pop()
        graph = build_lane_graph(missing_node)
        self.assertEqual(graph["status"], "FAIL")
        self.assertGreater(graph["production_gates"]["unresolved_connector_lane_mappings"], 0)

    def test_graph_hash_ignores_manifest_iteration_order(self):
        hashes = set()
        for seed in range(10):
            value = copy.deepcopy(manifest_fixture())
            rng = random.Random(seed)
            rng.shuffle(value["links"])
            rng.shuffle(value["connectors"])
            rng.shuffle(value["signal_heads"])
            for item in value["links"] + value["connectors"]:
                rng.shuffle(item["lanes"])
            for item in value["connectors"]:
                rng.shuffle(item["lane_mapping"])
            hashes.add(build_lane_graph(value)["semantic_sha256"])
        self.assertEqual(len(hashes), 1)

    def test_position_ordering_rejects_reverse_terminal_and_reverse_connector(self):
        paths, reason = resolve_route_paths(route_record(1, 20, [], 1, 10), self.graph)
        self.assertFalse(paths)
        self.assertIn("upstream", reason)

        paths, reason = resolve_route_paths(route_record(3, 10, [101], 2, 50), self.graph)
        self.assertFalse(paths)
        self.assertIn("no forward", reason)

    def test_next_connector_upstream_of_current_position_is_rejected(self):
        paths, reason = resolve_route_paths(route_record(1, 90, [100], 2, 50), self.graph)
        self.assertFalse(paths)
        self.assertIn("no forward", reason)

    def test_explicit_and_sparse_connector_waypoints_keep_same_per_state_paths(self):
        graph = build_lane_graph(
            {
                **manifest_fixture(),
                "links": [road(1, 2), road(2, 2)],
                "connectors": [connector(100, 1, 1, 2, 1, 2, 80.0, 10.0)],
                "signal_heads": [],
            }
        )
        explicit, explicit_reason = resolve_route_paths(
            route_record(1, 10, [100], 2, 50), graph
        )
        sparse, sparse_reason = resolve_route_paths(route_record(1, 10, [], 2, 50), graph)
        self.assertIsNone(explicit_reason)
        self.assertIsNone(sparse_reason)
        self.assertEqual(len(explicit), 4)
        self.assertEqual(len(sparse), 4)
        self.assertEqual(
            {
                (
                    item["start_lane_id"],
                    item["terminal_lane_id"],
                    tuple(item["traversed_edge_ids"]),
                )
                for item in explicit
            },
            {
                (
                    item["start_lane_id"],
                    item["terminal_lane_id"],
                    tuple(item["traversed_edge_ids"]),
                )
                for item in sparse
            },
        )
        for start_lane_id in ("lane:1:1", "lane:1:2"):
            self.assertEqual(
                len([item for item in explicit if item["start_lane_id"] == start_lane_id]),
                2,
            )

        for sequence in ("<intObjectRef key=\"100\"/>", ""):
            xml = f"""<network><vehicleRoutingDecisionsStatic>
              <vehicleRoutingDecisionStatic no="7" link="1" pos="10" routeChoiceMeth="STATIC">
                <vehRoutSta><vehicleRouteStatic no="1" destLink="2" destPos="50" relFlow="1">
                  <linkSeq>{sequence}</linkSeq>
                </vehicleRouteStatic></vehRoutSta>
              </vehicleRoutingDecisionStatic>
            </vehicleRoutingDecisionsStatic></network>"""
            artifact = compile_xml(xml, graph)
            self.assertEqual(artifact["status"], "PASS")
            self.assertEqual(len(artifact["proofs"]), 4)
            self.assertEqual(
                {
                    support["normalized_path_share_within_route"]
                    for proof in artifact["proofs"]
                    for support in proof["flow_path_shares"]
                },
                {0.25},
            )

    def test_closed_nodes_and_zero_distance_forced_lane_change_are_rejected(self):
        source_closed = one_lane_connector_manifest()
        source_closed["links"][0]["lanes"][0]["closed"] = True
        paths, _ = resolve_route_paths(
            route_record(1, 10, [100], 2, 50), build_lane_graph(source_closed)
        )
        self.assertFalse(paths)

        connector_closed = one_lane_connector_manifest()
        connector_closed["connectors"][0]["lanes"][0]["closed"] = True
        paths, _ = resolve_route_paths(
            route_record(1, 10, [100], 2, 50), build_lane_graph(connector_closed)
        )
        self.assertFalse(paths)

        target_closed = one_lane_connector_manifest()
        target_closed["links"][1]["lanes"][0]["closed"] = True
        paths, _ = resolve_route_paths(
            route_record(1, 10, [100], 2, 50), build_lane_graph(target_closed)
        )
        self.assertFalse(paths)

        zero_distance = {
            **manifest_fixture(),
            "links": [road(1, 2), road(2, 2), road(3, 1)],
            "connectors": [
                connector(100, 1, 1, 2, 2, 1, 80.0, 50.0, 10.0),
                connector(101, 2, 1, 3, 1, 1, 50.0, 0.0, 10.0),
            ],
            "signal_heads": [],
        }
        paths, reason = resolve_route_paths(
            route_record(1, 10, [100, 2, 101], 3, 50),
            build_lane_graph(zero_distance),
        )
        self.assertFalse(paths)
        self.assertIn("no forward", reason)

    def test_two_legitimate_paths_to_one_terminal_are_retained_and_normalized(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "routes.inpx"
            path.write_text(VALID_ROUTES_XML, encoding="utf-8")
            graph = copy.deepcopy(self.graph)
            graph["source"]["input_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            artifact = compile_route_proofs(path, graph)
        self.assertEqual(artifact["status"], "PASS")
        self.assertEqual(len(artifact["proofs"]), 4)
        self.assertEqual({item["terminal_lane_id"] for item in artifact["proofs"]}, {"lane:3:1"})
        for route_no in ("1", "2"):
            route_proofs = [
                proof for proof in artifact["proofs"] if proof["route_no"] == route_no
            ]
            self.assertEqual(len(route_proofs), 2)
            self.assertEqual(
                {
                    support["normalized_path_share_within_route"]
                    for proof in route_proofs
                    for support in proof["flow_path_shares"]
                },
                {0.5},
            )
        routes = {item["route_no"]: item for item in artifact["routes"]}
        self.assertEqual(
            [item["normalized_route_share"] for item in routes["1"]["normalized_flow_supports"]],
            [0.5, 0.75],
        )
        self.assertEqual(
            [item["normalized_route_share"] for item in routes["2"]["normalized_flow_supports"]],
            [0.5, 0.25],
        )
        self.assertEqual(artifact["production_gates"]["unresolved_routes"], 0)

    def test_sparse_waypoints_retain_all_directed_paths_to_same_terminal(self):
        paths, reason = resolve_route_paths(route_record(1, 10, [], 3, 50), self.graph)
        self.assertIsNone(reason)
        self.assertEqual(len(paths), 8)
        self.assertEqual({item["terminal_lane_id"] for item in paths}, {"lane:3:1"})
        self.assertEqual(
            {
                tuple(
                    edge_id
                    for edge_id in item["traversed_edge_ids"]
                    if edge_id.endswith(":entry")
                )
                for item in paths
            },
            {
                (
                    "edge:connector:100:lane:1:entry",
                    "edge:connector:101:lane:1:entry",
                ),
                (
                    "edge:connector:100:lane:1:entry",
                    "edge:connector:102:lane:1:entry",
                ),
                (
                    "edge:connector:100:lane:2:entry",
                    "edge:connector:101:lane:1:entry",
                ),
                (
                    "edge:connector:100:lane:2:entry",
                    "edge:connector:102:lane:1:entry",
                ),
            },
        )

    def test_single_route_multiple_paths_have_normalized_path_shares_end_to_end(self):
        xml = """<network><vehicleRoutingDecisionsStatic>
          <vehicleRoutingDecisionStatic no="7" link="1" pos="10" routeChoiceMeth="STATIC">
            <vehRoutSta><vehicleRouteStatic no="1" destLink="3" destPos="50" relFlow="1">
              <linkSeq/>
            </vehicleRouteStatic></vehRoutSta>
          </vehicleRoutingDecisionStatic>
        </vehicleRoutingDecisionsStatic></network>"""
        artifact = compile_xml(xml, self.graph)
        self.assertEqual(artifact["status"], "PASS")
        self.assertEqual(len(artifact["proofs"]), 8)
        shares = [
            proof["flow_path_shares"][0]["normalized_flow_path_share"]
            for proof in artifact["proofs"]
        ]
        self.assertAlmostEqual(math.fsum(shares), 1.0, places=12)
        self.assertEqual(set(shares), {0.125})

    def test_invalid_relative_flow_is_rejected_and_raw_supports_are_preserved(self):
        parsed = parse_relative_flow("2 0:1.25 1000:2.5")
        self.assertEqual(parsed["raw"], "2 0:1.25 1000:2.5")
        self.assertEqual(parsed["encoding_prefix_tokens"], ["2"])
        self.assertEqual(
            [(item["time_raw"], item["value_raw"]) for item in parsed["supports"]],
            [("0", "1.25"), ("1000", "2.5")],
        )
        self.assertEqual(parse_relative_flow("")["supports"][0]["value"], 1.0)
        for raw in (None, "-1", "2 0:-0.1", "2 0:nan", "2 0:inf", "bogus-prefix 0:1"):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                parse_relative_flow(raw)

    def test_missing_relflow_fails_but_explicit_empty_preserves_default_evidence(self):
        missing = """<network><vehicleRoutingDecisionsStatic>
          <vehicleRoutingDecisionStatic no="7" link="1" pos="10" routeChoiceMeth="STATIC">
            <vehRoutSta><vehicleRouteStatic no="1" destLink="2" destPos="50">
              <linkSeq><intObjectRef key="100"/></linkSeq>
            </vehicleRouteStatic></vehRoutSta>
          </vehicleRoutingDecisionStatic>
        </vehicleRoutingDecisionsStatic></network>"""
        missing_artifact = compile_xml(missing, build_lane_graph(one_lane_connector_manifest()))
        self.assertEqual(missing_artifact["status"], "FAIL")
        self.assertIn("invalid_relative_flow", {item["code"] for item in missing_artifact["reasons"]})

        explicit_empty = missing.replace(
            'destLink="2" destPos="50"', 'destLink="2" destPos="50" relFlow=""'
        )
        empty_artifact = compile_xml(
            explicit_empty, build_lane_graph(one_lane_connector_manifest())
        )
        self.assertEqual(empty_artifact["status"], "PASS")
        flow = empty_artifact["routes"][0]["relative_flow"]
        self.assertEqual(flow["raw"], "")
        self.assertTrue(flow["attribute_present"])
        self.assertTrue(flow["defaulted"])

    def test_supplied_graph_integrity_false_passes_are_rejected(self):
        xml = """<network><vehicleRoutingDecisionsStatic>
          <vehicleRoutingDecisionStatic no="7" link="1" pos="10" routeChoiceMeth="STATIC">
            <vehRoutSta><vehicleRouteStatic no="1" destLink="2" destPos="50" relFlow="1">
              <linkSeq><intObjectRef key="100"/></linkSeq>
            </vehicleRouteStatic></vehRoutSta>
          </vehicleRoutingDecisionStatic>
        </vehicleRoutingDecisionsStatic></network>"""
        base = build_lane_graph(one_lane_connector_manifest())

        stale_hash = copy.deepcopy(base)
        stale_hash["connectors"][0]["name"] = "tampered"

        wrong_schema = copy.deepcopy(base)
        wrong_schema["schema_version"] = "wrong"
        wrong_schema["semantic_sha256"] = canonical_json_sha256(
            graph_semantic_payload(wrong_schema)
        )

        failed_status = copy.deepcopy(base)
        failed_status["status"] = "FAIL"
        failed_status["reasons"] = [{"code": "fixture", "entity_id": "graph", "detail": None}]

        missing_gate = copy.deepcopy(base)
        del missing_gate["production_gates"]["reverse_synthetic_edges"]

        noncanonical = copy.deepcopy(base)
        noncanonical["nodes"].reverse()
        noncanonical["semantic_sha256"] = canonical_json_sha256(
            graph_semantic_payload(noncanonical)
        )

        invalid_degree = copy.deepcopy(base)
        invalid_degree["edges"].insert(1, copy.deepcopy(invalid_degree["edges"][0]))
        invalid_degree["semantic_sha256"] = canonical_json_sha256(
            graph_semantic_payload(invalid_degree)
        )

        cases = {
            "stale_hash": (stale_hash, "graph_semantic_hash_mismatch"),
            "wrong_schema": (wrong_schema, "invalid_lane_graph_schema"),
            "failed_status": (failed_status, "lane_graph_status_not_pass"),
            "missing_gate": (missing_gate, "missing_lane_graph_gate"),
            "noncanonical": (noncanonical, "noncanonical_lane_graph_order"),
            "invalid_degree": (invalid_degree, "invalid_connector_node_degree"),
        }
        for name, (graph, expected_reason) in cases.items():
            with self.subTest(name=name):
                artifact = compile_xml(xml, graph)
                self.assertEqual(artifact["status"], "FAIL")
                self.assertIn(expected_reason, {item["code"] for item in artifact["reasons"]})

    def test_rehashed_full_graph_semantic_inconsistencies_are_rejected(self):
        xml = """<network><vehicleRoutingDecisionsStatic>
          <vehicleRoutingDecisionStatic no="7" link="1" pos="10" routeChoiceMeth="STATIC">
            <vehRoutSta><vehicleRouteStatic no="1" destLink="2" destPos="500" relFlow="1">
              <linkSeq><intObjectRef key="100"/></linkSeq>
            </vehicleRouteStatic></vehRoutSta>
          </vehicleRoutingDecisionStatic>
        </vehicleRoutingDecisionsStatic></network>"""
        base = build_lane_graph(one_lane_connector_manifest())

        cases = {}

        road_length = copy.deepcopy(base)
        next(node for node in road_length["nodes"] if node["id"] == "lane:2:1")[
            "length_m"
        ] = 1000.0
        cases["road_length"] = (
            rehash_graph(road_length),
            "lane_node_parent_mismatch",
        )

        connector_closed = copy.deepcopy(base)
        next(
            node for node in connector_closed["nodes"] if node["id"] == "lane:100:1"
        )["closed"] = True
        cases["connector_closed"] = (
            rehash_graph(connector_closed),
            "lane_node_parent_mismatch",
        )

        connector_length = copy.deepcopy(base)
        next(
            node for node in connector_length["nodes"] if node["id"] == "lane:100:1"
        )["length_m"] = 200.0
        cases["connector_length"] = (
            rehash_graph(connector_length),
            "lane_node_parent_mismatch",
        )

        invalid_closed_type = copy.deepcopy(base)
        invalid_closed_type["links"][0]["lanes"][0]["closed"] = 0
        next(
            node
            for node in invalid_closed_type["nodes"]
            if node["id"] == invalid_closed_type["links"][0]["lanes"][0]["id"]
        )["closed"] = 0
        cases["invalid_closed_type"] = (
            rehash_graph(invalid_closed_type),
            "invalid_lane_graph_parent_lane_universe",
        )

        orphan = copy.deepcopy(base)
        orphan["nodes"][0]["object_id"] = "link:999"
        cases["orphan"] = (rehash_graph(orphan), "lane_node_parent_mismatch")

        duplicate_link = copy.deepcopy(base)
        duplicate_link["links"].append(copy.deepcopy(duplicate_link["links"][0]))
        duplicate_link["links"].sort(key=lambda item: int(item["link_no"]))
        cases["duplicate_link"] = (
            rehash_graph(duplicate_link),
            "duplicate_lane_graph_id",
        )

        unknown_endpoint = copy.deepcopy(base)
        unknown_endpoint["edges"][0]["from_lane_id"] = "lane:999:1"
        cases["unknown_endpoint"] = (
            rehash_graph(unknown_endpoint),
            "invalid_lane_graph_edge",
        )

        unsupported_edge_kind = copy.deepcopy(base)
        unsupported_edge_kind["edges"][0]["kind"] = "bogus"
        cases["unsupported_edge_kind"] = (
            rehash_graph(unsupported_edge_kind),
            "invalid_lane_graph_edge",
        )

        reversed_edge = copy.deepcopy(base)
        reversed_edge["edges"][0]["from_lane_id"], reversed_edge["edges"][0][
            "to_lane_id"
        ] = (
            reversed_edge["edges"][0]["to_lane_id"],
            reversed_edge["edges"][0]["from_lane_id"],
        )
        cases["reversed_edge"] = (
            rehash_graph(reversed_edge),
            "invalid_lane_graph_edge",
        )

        invalid_edge_position = copy.deepcopy(base)
        invalid_edge_position["edges"][0]["from_position_m"] = -1.0
        cases["invalid_edge_position"] = (
            rehash_graph(invalid_edge_position),
            "invalid_lane_graph_edge",
        )

        invalid_stopline = build_lane_graph(manifest_fixture())
        invalid_stopline["signal_heads"][0]["position_m"] = 1000.0
        cases["invalid_stopline"] = (
            rehash_graph(invalid_stopline),
            "invalid_lane_graph_stopline",
        )

        wrong_dimensions = copy.deepcopy(base)
        wrong_dimensions["sample_dimensions"]["lane_nodes"] += 1
        cases["wrong_dimensions"] = (
            rehash_graph(wrong_dimensions),
            "invalid_lane_graph_dimension",
        )

        null_nodes = copy.deepcopy(base)
        null_nodes["nodes"] = None
        cases["null_nodes"] = (
            rehash_graph(null_nodes),
            "noncanonical_lane_graph_order",
        )

        for name, (graph, expected_reason) in cases.items():
            with self.subTest(name=name):
                artifact = compile_xml(xml, graph)
                self.assertEqual(artifact["status"], "FAIL")
                self.assertIn(expected_reason, {item["code"] for item in artifact["reasons"]})

    def test_rehashed_stopline_identity_inconsistencies_are_rejected(self):
        cases = {}
        for field in ("signal_controller_no", "signal_group_no", "head_no"):
            for label, value in (("null", None), ("empty", ""), ("nonnumeric", "bogus")):
                graph = copy.deepcopy(self.graph)
                graph["signal_heads"][0][field] = value
                cases[f"{field}_{label}"] = rehash_graph(graph)

        duplicate = copy.deepcopy(self.graph)
        duplicate_head = copy.deepcopy(duplicate["signal_heads"][0])
        duplicate["signal_heads"].append(duplicate_head)
        duplicate["sample_dimensions"]["signal_heads"] += 1
        cases["duplicate_head_identity"] = rehash_graph(duplicate)

        for name, graph in cases.items():
            with self.subTest(name=name):
                failures = validate_lane_graph_artifact(graph)
                self.assertIn(
                    "invalid_lane_graph_stopline_identity",
                    {item["code"] for item in failures},
                )
                artifact = compile_xml(VALID_ROUTES_XML, graph)
                self.assertEqual(artifact["status"], "FAIL")
                self.assertEqual(artifact["proofs"], [])
                self.assertIn(
                    "invalid_lane_graph_stopline_identity",
                    {item["code"] for item in artifact["reasons"]},
                )

    def test_first_stopline_proof_preserves_only_validated_identity(self):
        artifact = compile_xml(VALID_ROUTES_XML, self.graph)
        self.assertEqual(artifact["status"], "PASS")
        stoplines = [
            proof["first_downstream_stopline_or_terminal"]
            for proof in artifact["proofs"]
            if proof["first_downstream_stopline_or_terminal"]["kind"]
            == "signal_head_stopline"
        ]
        self.assertTrue(stoplines)
        expected_identity = {
            "signal_head_id": "signal-head:501",
            "signal_controller_no": "12",
            "signal_group_no": 3,
            "head_no": "501",
            "lane_id": "lane:2:1",
            "position_m": 60.0,
        }
        for stopline in stoplines:
            self.assertEqual(
                {key: stopline[key] for key in expected_identity},
                expected_identity,
            )
            self.assertEqual(
                set(stopline),
                {"kind", "distance_from_decision_m", *expected_identity},
            )

    def test_command_hashes_cover_transitive_behavioral_dependencies(self):
        graph_dependencies = set(self.graph["command"]["source_sha256"])
        expected_graph_dependencies = {
            "scripts/build_vissim_lane_graph.py",
            "plant/src/__init__.py",
            *{
                path.relative_to(REPO_ROOT).as_posix()
                for path in (REPO_ROOT / "plant" / "src" / "vissim_strict").rglob("*.py")
            },
        }
        self.assertEqual(graph_dependencies, expected_graph_dependencies)

        xml = """<network><vehicleRoutingDecisionsStatic>
          <vehicleRoutingDecisionStatic no="7" link="1" pos="10" routeChoiceMeth="STATIC">
            <vehRoutSta><vehicleRouteStatic no="1" destLink="2" destPos="50" relFlow="1">
              <linkSeq><intObjectRef key="100"/></linkSeq>
            </vehicleRouteStatic></vehRoutSta>
          </vehicleRoutingDecisionStatic>
        </vehicleRoutingDecisionsStatic></network>"""
        route_artifact = compile_xml(xml, build_lane_graph(one_lane_connector_manifest()))
        self.assertEqual(
            set(route_artifact["command"]["source_sha256"]),
            expected_graph_dependencies | {"scripts/resolve_lane_routes.py"},
        )


if __name__ == "__main__":
    unittest.main()
