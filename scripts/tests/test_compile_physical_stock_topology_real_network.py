import copy
import hashlib
import json
import random
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "plant"))

from build_vissim_lane_graph import build_lane_graph, validate_lane_graph_artifact
from compile_physical_stock_topology import (
    PRODUCTION_PARTITION_COUNTS,
    TRUSTED_PRODUCTION_EVIDENCE_HASHES,
    TRUSTED_PRODUCTION_FILE_HASHES,
    compile_physical_stock_topology,
    deduplicated_visible_mass,
    validate_route_proofs_artifact,
)
from resolve_lane_routes import compile_route_proofs
from src.vissim_strict.compiler import compile_network


REAL_INPX = REPO_ROOT / "network" / "real_world_gaepo_modi" / "modi_eval_rw_control.inpx"
OWNERSHIP = REPO_ROOT / "outputs" / "link_player_assignment_20260805.json"
ADJACENCY = REPO_ROOT / "outputs" / "intersection_adjacency8_20260805.json"
CAPACITY = REPO_ROOT / "outputs" / "urban_storage_capacity_20260805.json"


def load_json(path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def file_sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def shuffled_mapping(value, rng):
    items = list(value.items())
    rng.shuffle(items)
    return {key: item for key, item in items}


class PhysicalStockTopologyRealNetworkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        required = (REAL_INPX, OWNERSHIP, ADJACENCY, CAPACITY)
        if not all(path.is_file() for path in required):
            raise unittest.SkipTest("production topology inputs are unavailable")
        cls.manifest = compile_network(REAL_INPX)
        cls.graph = build_lane_graph(cls.manifest)
        cls.routes = compile_route_proofs(REAL_INPX, cls.graph)
        cls.ownership = load_json(OWNERSHIP)
        cls.adjacency = load_json(ADJACENCY)
        cls.capacity = load_json(CAPACITY)
        cls.source_file_sha256 = {
            "ownership_evidence": file_sha256(OWNERSHIP),
            "adjacency_evidence": file_sha256(ADJACENCY),
            "capacity_evidence": file_sha256(CAPACITY),
        }
        cls.topology = compile_physical_stock_topology(
            cls.graph,
            cls.routes,
            cls.ownership,
            cls.adjacency,
            cls.capacity,
            source_file_sha256=cls.source_file_sha256,
            require_production_partition=True,
        )

    def test_a1_artifacts_are_revalidated_before_use(self):
        self.assertEqual(validate_lane_graph_artifact(self.graph), [])
        self.assertEqual(validate_route_proofs_artifact(self.routes, self.graph), [])
        self.assertEqual(self.graph["status"], "PASS")
        self.assertEqual(self.routes["status"], "PASS")

    def test_production_partition_stock_capacity_and_objective_gates(self):
        topology = self.topology
        self.assertEqual(topology["status"], "PASS", topology["reasons"][:5])
        self.assertEqual(topology["schema_version"], "physical-stock-topology-v2.1")
        self.assertTrue({
            "schema_version",
            "input_hashes",
            "command_version",
            "status",
            "reasons",
            "sample_dimensions",
            "units",
            "downstream_consumers",
        }.issubset(topology))
        self.assertEqual(
            topology["input_hashes"]["link_assignment_sha256"],
            TRUSTED_PRODUCTION_FILE_HASHES["ownership_evidence"],
        )
        self.assertEqual(
            topology["input_hashes"]["legacy_partition_identity_sha256"],
            TRUSTED_PRODUCTION_EVIDENCE_HASHES[
                "legacy_partition_identity_sha256"
            ],
        )
        self.assertEqual(
            topology["command_version"],
            {
                "command": "scripts/compile_physical_stock_topology.py",
                "version": "compile-physical-stock-topology/2.1.1",
                "sha256": hashlib.sha256(
                    (REPO_ROOT / "scripts" / "compile_physical_stock_topology.py").read_bytes()
                ).hexdigest(),
            },
        )
        self.assertEqual(topology["legacy_partition"]["counts"], {
            **PRODUCTION_PARTITION_COUNTS,
            "duplicate": 0,
            "missing_from_a1": 0,
        })
        self.assertEqual(topology["legacy_partition"]["remaining_a1_road_links"], 4)
        self.assertEqual(topology["legacy_partition"]["a1_connector_links"], 771)
        self.assertEqual(
            topology["legacy_partition"]["identity_sha256"],
            topology["input_hashes"]["legacy_partition_identity_sha256"],
        )
        gates = topology["production_gates"]
        for name in (
            "lane_interval_gaps",
            "lane_interval_overlaps",
            "lane_interval_missing_lanes",
            "lane_interval_nonpositive",
            "duplicate_stock_ids",
            "legacy_partition_duplicate",
            "legacy_partition_missing_from_a1",
            "legacy_partition_identity_mismatch",
            "unexplained_owner_stocks",
            "objective_policy_violations",
            "visibility_uncovered_stocks",
        ):
            self.assertEqual(gates[name], 0, name)
        self.assertLessEqual(gates["maximum_owner_weight_sum_error"], 1.0e-9)
        self.assertEqual(gates["named_ramp_capacity_count"], 4)
        self.assertEqual(
            topology["capacity_evidence"]["named_ramp_capacity_veh"],
            {"R_D_E": 93.0, "R_D_W": 128.0, "R_F_E": 128.4, "R_F_W": 145.9},
        )
        dimensions = topology["sample_dimensions"]
        self.assertEqual(dimensions["a1_lane_nodes"], 2649)
        self.assertEqual(dimensions["a1_road_links"], 448)
        self.assertEqual(dimensions["a1_connector_links"], 771)
        self.assertEqual(dimensions["stocks_by_parent_kind"]["connector"], 1435)
        self.assertEqual(
            dimensions["objective_weight_one_counts"]["controller_with_boundary"]
            - dimensions["objective_weight_one_counts"]["controller_default"],
            dimensions["objective_weight_one_counts"]["boundary_only"],
        )

    def test_capacity_formula_and_visibility_mass_are_exact(self):
        topology = self.topology
        jam = topology["capacity_evidence"]["jam_density_veh_km_lane"]
        for item in topology["stocks"]:
            self.assertAlmostEqual(
                item["capacity_prior"]["value"], item["length_m"] / 1000.0 * jam, places=12
            )
        values = {item["id"]: (index % 17 + 1) / 13.0 for index, item in enumerate(topology["stocks"])}
        self.assertAlmostEqual(deduplicated_visible_mass(topology, values), sum(values.values()), places=9)

    def test_sc12_lane_two_through_and_left_share_physical_stock_ids(self):
        lane_id = "lane:1220012103:2"
        proofs = {proof["id"]: proof for proof in self.routes["proofs"]}
        through_edge = "edge:connector:10241:lane:2:entry"
        left_edge = "edge:connector:10242:lane:1:entry"
        through_ids = set()
        left_ids = set()
        for item in self.topology["stocks"]:
            if item["lane_id"] != lane_id:
                continue
            for membership in item["route_memberships"]:
                traversed = set(proofs[membership["proof_id"]]["traversed_edge_ids"])
                if through_edge in traversed:
                    through_ids.add(item["id"])
                if left_edge in traversed:
                    left_ids.add(item["id"])
        self.assertTrue(through_ids)
        self.assertTrue(left_ids)
        self.assertEqual(through_ids, left_ids)
        stock_ids = [item["id"] for item in self.topology["stocks"] if item["lane_id"] == lane_id]
        self.assertEqual(len(stock_ids), len(set(stock_ids)))

    def test_known_multi_decision_stock_does_not_combine_denominators(self):
        item = next(
            stock
            for stock in self.topology["stocks"]
            if stock["id"]
            == "stock:70:1:67.915467926212969:180.143228351476381"
        )
        decision_nos = item["control_owner_state"].get("decision_nos", [])
        self.assertFalse({"1133", "1134", "1140"}.issubset(decision_nos))

    def test_production_evidence_tampering_fails_closed(self):
        swap = copy.deepcopy(self.ownership)
        swap["link_owner"]["10001"] = swap["link_owner"].pop("10000")
        swap["monitor_only_exit_links"].remove("10001")
        swap["monitor_only_exit_links"].append("10000")

        fake_adjacency = copy.deepcopy(self.adjacency)
        fake_adjacency["adjacency"]["1"].append(999999)

        doubled_capacity = copy.deepcopy(self.capacity)
        doubled_capacity["jam_density_veh_km_lane"] *= 2.0

        wrong_file_hashes = dict(self.source_file_sha256)
        wrong_file_hashes["ownership_evidence"] = "0" * 64

        for name, ownership, adjacency, capacity, source_hashes, expected_reason in (
            (
                "partition_swap",
                swap,
                self.adjacency,
                self.capacity,
                self.source_file_sha256,
                "legacy_partition_identity_hash_mismatch",
            ),
            (
                "fake_adjacency",
                self.ownership,
                fake_adjacency,
                self.capacity,
                self.source_file_sha256,
                "trusted_evidence_hash_mismatch",
            ),
            (
                "doubled_capacity",
                self.ownership,
                self.adjacency,
                doubled_capacity,
                self.source_file_sha256,
                "trusted_evidence_hash_mismatch",
            ),
            (
                "wrong_raw_file_hash",
                self.ownership,
                self.adjacency,
                self.capacity,
                wrong_file_hashes,
                "trusted_evidence_file_hash_mismatch",
            ),
        ):
            with self.subTest(name=name):
                artifact = compile_physical_stock_topology(
                    self.graph,
                    self.routes,
                    ownership,
                    adjacency,
                    capacity,
                    source_file_sha256=source_hashes,
                    require_production_partition=True,
                )
                self.assertEqual(artifact["status"], "FAIL")
                self.assertEqual(artifact["stocks"], [])
                self.assertIn(
                    expected_reason, {item["code"] for item in artifact["reasons"]}
                )

    def test_ten_shuffled_inputs_produce_one_semantic_hash(self):
        hashes = set()
        for seed in range(10):
            rng = random.Random(seed)
            manifest = copy.deepcopy(self.manifest)
            rng.shuffle(manifest["links"])
            rng.shuffle(manifest["connectors"])
            rng.shuffle(manifest["signal_heads"])
            for parent in manifest["links"] + manifest["connectors"]:
                rng.shuffle(parent["lanes"])
            for connector in manifest["connectors"]:
                rng.shuffle(connector["lane_mapping"])
            graph = build_lane_graph(manifest)

            owner = copy.deepcopy(self.ownership)
            owner["link_owner"] = shuffled_mapping(owner["link_owner"], rng)
            owner["freeway_bound_links"] = shuffled_mapping(owner["freeway_bound_links"], rng)
            rng.shuffle(owner["monitor_only_exit_links"])

            adjacency = copy.deepcopy(self.adjacency)
            adjacency["adjacency"] = shuffled_mapping(adjacency["adjacency"], rng)
            for neighbors in adjacency["adjacency"].values():
                rng.shuffle(neighbors)
            adjacency["internal_link_members"] = shuffled_mapping(
                adjacency["internal_link_members"], rng
            )

            capacity = copy.deepcopy(self.capacity)
            capacity["ramp_queue_max_veh_by_ramp"] = shuffled_mapping(
                capacity["ramp_queue_max_veh_by_ramp"], rng
            )
            topology = compile_physical_stock_topology(
                graph,
                self.routes,
                owner,
                adjacency,
                capacity,
                source_file_sha256=self.source_file_sha256,
                require_production_partition=True,
            )
            self.assertEqual(topology["status"], "PASS", topology["reasons"][:3])
            hashes.add(topology["semantic_sha256"])
        self.assertEqual(hashes, {self.topology["semantic_sha256"]})


if __name__ == "__main__":
    unittest.main()
