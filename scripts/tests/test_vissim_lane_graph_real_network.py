import copy
import hashlib
import math
import random
import sys
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "plant"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from build_vissim_lane_graph import build_lane_graph
from resolve_lane_routes import compile_route_proofs
from src.vissim_strict.compiler import compile_network


REAL_INPX = REPO_ROOT / "network" / "real_world_gaepo_modi" / "modi_eval_rw_control.inpx"


def _local_name(tag):
    return tag.rsplit("}", 1)[-1]


def _shuffle_route_xml(source, destination, seed):
    tree = ET.parse(source)
    root = tree.getroot()
    rng = random.Random(seed)
    for parent in root.iter():
        route_indices = [
            index
            for index, child in enumerate(list(parent))
            if _local_name(child.tag) == "vehicleRouteStatic"
        ]
        route_children = [parent[index] for index in route_indices]
        rng.shuffle(route_children)
        for index, child in zip(route_indices, route_children):
            parent[index] = child
    for parent in root.iter():
        decision_indices = [
            index
            for index, child in enumerate(list(parent))
            if _local_name(child.tag) == "vehicleRoutingDecisionStatic"
        ]
        decision_children = [parent[index] for index in decision_indices]
        rng.shuffle(decision_children)
        for index, child in zip(decision_indices, decision_children):
            parent[index] = child
    tree.write(destination, encoding="utf-8", xml_declaration=True)


class VissimLaneGraphRealNetworkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not REAL_INPX.is_file():
            raise unittest.SkipTest(f"real network not found: {REAL_INPX}")
        cls.manifest = compile_network(REAL_INPX)
        cls.graph = build_lane_graph(cls.manifest)
        cls.proofs = compile_route_proofs(REAL_INPX, cls.graph)

    def test_real_network_production_gates(self):
        self.assertTrue(self.manifest["validation_report"]["valid"])
        self.assertEqual(self.manifest["signal_reference"]["schema_version"], "signal-reference-v2.1")
        self.assertEqual(self.graph["status"], "PASS")
        self.assertEqual(self.proofs["status"], "PASS")
        self.assertEqual(self.graph["sample_dimensions"]["road_links"], 448)
        self.assertEqual(self.graph["sample_dimensions"]["connector_links"], 771)
        self.assertEqual(self.graph["sample_dimensions"]["connector_lanes"], 1396)
        self.assertEqual(self.graph["sample_dimensions"]["directed_edges"], 2792)
        self.assertEqual(self.graph["sample_dimensions"]["signal_heads"], 541)
        self.assertEqual(self.proofs["sample_dimensions"]["active_static_routing_decisions"], 130)
        self.assertEqual(self.proofs["sample_dimensions"]["active_static_routes"], 339)
        self.assertEqual(self.proofs["production_gates"]["unresolved_routes"], 0)
        self.assertEqual(self.proofs["production_gates"]["reverse_synthetic_edges"], 0)
        self.assertEqual(self.proofs["production_gates"]["executable_connector_path_coverage"], 1.0)
        self.assertLessEqual(
            self.proofs["production_gates"]["maximum_normalized_flow_share_error"], 1.0e-9
        )

    def test_every_connector_lane_has_exact_entry_and_exit_edges(self):
        incident = defaultdict(list)
        for edge in self.graph["edges"]:
            connector_lane_id = f"lane:{edge['connector_no']}:{edge['connector_lane_no']}"
            incident[connector_lane_id].append(edge["kind"])
        connector_lane_ids = {
            f"lane:{connector['connector_no']}:{lane_no}"
            for connector in self.graph["connectors"]
            for lane_no in range(1, connector["lane_count"] + 1)
        }
        declared_connector_node_ids = {
            node["id"] for node in self.graph["nodes"] if node["object_kind"] == "connector"
        }
        self.assertEqual(declared_connector_node_ids, connector_lane_ids)
        self.assertEqual(set(incident), connector_lane_ids)
        self.assertTrue(
            all(sorted(incident[lane_id]) == ["connector_entry", "connector_exit"] for lane_id in connector_lane_ids)
        )

    def test_sc12_shared_lane_mapping_is_unchanged(self):
        connectors = {item["connector_no"]: item for item in self.graph["connectors"]}
        expected = {
            "10241": [
                ("lane:10241:1", "lane:1220012103:1", "lane:1220013700:1"),
                ("lane:10241:2", "lane:1220012103:2", "lane:1220013700:2"),
            ],
            "10242": [("lane:10242:1", "lane:1220012103:2", "lane:1220015100:3")],
            "10238": [
                ("lane:10238:1", "lane:1220013600:1", "lane:1220012003:1"),
                ("lane:10238:2", "lane:1220013600:2", "lane:1220012003:2"),
            ],
            "10240": [("lane:10240:1", "lane:1220013600:2", "lane:1220012600:3")],
        }
        actual = {
            connector_no: [
                (item["connector_lane_id"], item["from_lane_id"], item["to_lane_id"])
                for item in connectors[connector_no]["lane_mapping"]
            ]
            for connector_no in expected
        }
        self.assertEqual(actual, expected)

    def test_ten_shuffled_compiles_have_one_graph_and_route_hash(self):
        graph_hashes = set()
        route_hashes = set()
        shuffled_input_hashes = set()
        with tempfile.TemporaryDirectory() as directory:
            for seed in range(10):
                manifest = copy.deepcopy(self.manifest)
                rng = random.Random(seed)
                rng.shuffle(manifest["links"])
                rng.shuffle(manifest["connectors"])
                rng.shuffle(manifest["signal_heads"])
                for item in manifest["links"] + manifest["connectors"]:
                    rng.shuffle(item["lanes"])
                for connector in manifest["connectors"]:
                    rng.shuffle(connector["lane_mapping"])
                graph = build_lane_graph(manifest)
                graph_hashes.add(graph["semantic_sha256"])

                shuffled_inpx = Path(directory) / f"routes-shuffled-{seed}.inpx"
                _shuffle_route_xml(REAL_INPX, shuffled_inpx, seed)
                shuffled_input_hash = hashlib.sha256(shuffled_inpx.read_bytes()).hexdigest()
                shuffled_input_hashes.add(shuffled_input_hash)
                graph["source"]["input_sha256"] = shuffled_input_hash
                route_hashes.add(
                    compile_route_proofs(shuffled_inpx, graph)["semantic_sha256"]
                )

        self.assertEqual(graph_hashes, {self.graph["semantic_sha256"]})
        self.assertEqual(route_hashes, {self.proofs["semantic_sha256"]})
        self.assertEqual(len(shuffled_input_hashes), 10)

    def test_route_command_hash_covers_transitive_behavioral_dependencies(self):
        dependencies = set(self.proofs["command"]["source_sha256"])
        self.assertTrue(
            {
                "scripts/resolve_lane_routes.py",
                "scripts/build_vissim_lane_graph.py",
                "plant/src/vissim_strict/compiler.py",
                "plant/src/vissim_strict/topology.py",
                "plant/src/vissim_strict/contraction.py",
                "plant/src/vissim_strict/signal_program.py",
            }.issubset(dependencies)
        )

    def test_normalized_proof_shares_sum_to_one_per_decision_support(self):
        totals = defaultdict(list)
        for proof in self.proofs["proofs"]:
            for support in proof["flow_path_shares"]:
                totals[(proof["decision_no"], support["time_ms"])].append(
                    support["normalized_flow_path_share"]
                )
        self.assertTrue(totals)
        self.assertLessEqual(
            max(abs(math.fsum(shares) - 1.0) for shares in totals.values()), 1.0e-9
        )


if __name__ == "__main__":
    unittest.main()
