from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import random
import sys
import tempfile
import time
import unittest


PLANT_ROOT = Path(__file__).resolve().parents[1]
if str(PLANT_ROOT) not in sys.path:
    sys.path.insert(0, str(PLANT_ROOT))

from src.vissim_strict.physical_projection import (
    POSITION_TOLERANCE_M,
    OBJECTIVE_POLICIES,
    ProjectionError,
    TOPOLOGY_DOWNSTREAM_CONSUMERS,
    TOPOLOGY_UNITS,
    TopologyValidationError,
    atomic_write_json,
    file_sha256,
    normalize_vehicle_records,
    project_vehicle_records,
    strict_json_loads,
    strict_load_json,
    topology_semantic_payload,
    validate_physical_stock_topology,
    write_projection_sidecar,
)
from src.vissim_strict.topology import canonical_json_sha256


def stock(
    link_no: int,
    lane_no: int,
    start: float,
    end: float,
    *,
    roles: list[str] | None = None,
    owners: dict[str, float] | None = None,
    owner_kind: str = "controlled",
) -> dict[str, object]:
    roles = ["urban"] if roles is None else roles
    owners = {"urban:1": 1.0} if owners is None else owners
    boundary = "boundary_out" in roles
    identifier = f"stock:{link_no}:{lane_no}:{start:g}:{end:g}"
    visible = sorted(owners)
    if owner_kind == "external":
        visible = ["external:boundary-out"]
        owners = {}
    elif owner_kind == "uncontrolled":
        visible = ["uncontrolled:no-owner-evidence"]
        owners = {}
    owner_state = (
        {"kind": "controlled", "basis": "fixture"}
        if owner_kind == "controlled"
        else {"kind": owner_kind, "reason": "fixture"}
    )
    return {
        "id": identifier,
        "lane_id": f"lane:{link_no}:{lane_no}",
        "link_no": str(link_no),
        "lane_no": lane_no,
        "parent_kind": "link",
        "start_m": start,
        "end_m": end,
        "length_m": end - start,
        "roles": sorted(roles),
        "control_owner_state": owner_state,
        "control_owner_weights": owners,
        "visible_to": visible,
        "objective_weights": {
            "physical_total": 1,
            "controller_default": 0 if boundary else 1,
            "controller_with_boundary": 1,
            "boundary_only": 1 if boundary else 0,
        },
        "route_memberships": [],
    }


def topology_fixture(*, boundary: bool = False, multi_owner: bool = False):
    roles = ["boundary_out"] if boundary else ["urban"]
    owner_kind = "external" if boundary else "controlled"
    owners = {"urban:1": 0.25, "urban:2": 0.75} if multi_owner else None
    stocks = [
        stock(1, 1, 0.0, 50.0, roles=roles, owners=owners, owner_kind=owner_kind),
        stock(1, 1, 50.0, 100.0, roles=roles, owners=owners, owner_kind=owner_kind),
    ]
    role_counts = {role: len(stocks) for role in roles}
    default_count = 0 if boundary else len(stocks)
    topology = {
        "schema_version": "physical-stock-topology-v2.1",
        "canonical_json_version": "canonical-json/v1",
        "input_hashes": {
            "lane_graph_semantic_sha256": "1" * 64,
            "lane_route_proofs_semantic_sha256": "2" * 64,
            "ownership_evidence_semantic_sha256": "3" * 64,
            "adjacency_evidence_semantic_sha256": "4" * 64,
            "capacity_evidence_semantic_sha256": "5" * 64,
            "legacy_partition_identity_sha256": "6" * 64,
        },
        "command_version": {
            "command": "scripts/compile_physical_stock_topology.py",
            "version": "fixture/1",
            "sha256": "7" * 64,
        },
        "source_artifacts": {
            "lane_graph_semantic_sha256": "1" * 64,
            "lane_route_proofs_semantic_sha256": "2" * 64,
            "ownership_evidence_semantic_sha256": "3" * 64,
            "adjacency_evidence_semantic_sha256": "4" * 64,
            "capacity_evidence_semantic_sha256": "5" * 64,
            "legacy_partition_identity_sha256": "6" * 64,
        },
        "command": {
            "version": "fixture/1",
            "source_sha256": {
                "scripts/compile_physical_stock_topology.py": "7" * 64,
            },
            "command_hash": canonical_json_sha256({
                "scripts/compile_physical_stock_topology.py": "7" * 64,
            }),
            "semantic_hash_scope": "schema, semantic input hashes, policies, partition, capacity evidence, stocks, stock edges",
        },
        "status": "PASS",
        "reasons": [],
        "units": copy.deepcopy(TOPOLOGY_UNITS),
        "downstream_consumers": list(TOPOLOGY_DOWNSTREAM_CONSUMERS),
        "policies": {
            "stock_identity": "fixture",
            "position_tolerance_m": POSITION_TOLERANCE_M,
            "owner_weight_support": "fixture",
            "visibility": "fixture",
            "objective_weights": copy.deepcopy(OBJECTIVE_POLICIES),
        },
        "legacy_partition": {},
        "capacity_evidence": {},
        "sample_dimensions": {
            "a1_lane_nodes": 1,
            "a1_road_links": 1,
            "a1_connector_links": 0,
            "stocks": 2,
            "stock_edges": 1,
            "route_memberships": 0,
            "stocks_by_parent_kind": {"link": 2},
            "stocks_by_role": role_counts,
            "objective_weight_one_counts": {
                "physical_total": 2,
                "controller_default": default_count,
                "controller_with_boundary": 2,
                "boundary_only": 2 if boundary else 0,
            },
        },
        "production_gates": {
            "lane_interval_gaps": 0,
            "lane_interval_overlaps": 0,
            "lane_interval_missing_lanes": 0,
            "lane_interval_nonpositive": 0,
            "duplicate_stock_ids": 0,
            "legacy_partition_duplicate": 0,
            "legacy_partition_missing_from_a1": 0,
            "legacy_partition_identity_mismatch": 0,
            "maximum_owner_weight_sum_error": 0.0,
            "unexplained_owner_stocks": 0,
            "objective_policy_violations": 0,
            "visibility_uncovered_stocks": 0,
            "named_ramp_capacity_count": 0,
        },
        "stocks": stocks,
        "stock_edges": [{
            "id": "stock-edge:fixture",
            "from_stock_id": stocks[0]["id"],
            "to_stock_id": stocks[1]["id"],
            "from_link_no": "1",
            "from_lane_no": 1,
            "from_position_m": 50.0,
            "to_link_no": "1",
            "to_lane_no": 1,
            "to_position_m": 50.0,
        }],
    }
    topology["semantic_sha256"] = canonical_json_sha256(topology_semantic_payload(topology))
    graph = {
        "nodes": [{
            "id": "lane:1:1",
            "link_no": "1",
            "lane_no": 1,
            "length_m": 100.0,
            "object_kind": "link",
        }],
        "links": [{}],
        "connectors": [],
    }
    return topology, graph


def state_fixture(records: list[dict[str, object]], *, run_id="run-13", sim_sec=900.0):
    counts: dict[str, int] = {}
    stopped: dict[str, int] = {}
    for record in records:
        key = str(record["link_no"])
        counts[key] = counts.get(key, 0) + 1
        if record["stopped"]:
            stopped[key] = stopped.get(key, 0) + 1
    stopped = {key: stopped.get(key, 0) for key in counts}
    count = len(records)
    return {
        "run_provenance": {"run_id": run_id},
        "sim_sec": sim_sec,
        "total_vehicles": count,
        "vehicle_records": {
            "schema_version": "vissim-vehicle-records-v2.1",
            "complete": True,
            "paused_at_sim_sec": sim_sec,
            "capture_sim_sec_before": sim_sec,
            "capture_sim_sec_after": sim_sec,
            "source_attributes": {
                "vehicle_number": "No",
                "lane": "Lane",
                "position": "Pos",
                "speed": "Speed",
            },
            "stopped_threshold_kph": 1.0,
            "collection_count_before": count,
            "collection_count_after": count,
            "record_count": count,
            "unobservable_count": 0,
            "external_source_count": 0,
            "full_network_link_counts": counts,
            "full_network_link_stopped_counts": stopped,
            "records": records,
        },
    }


def record(veh_no: int, position: float, *, speed: float = 10.0):
    return {
        "veh_no": veh_no,
        "link_no": 1,
        "lane_no": 1,
        "position_m": position,
        "speed_kph": speed,
        "stopped": speed < 1.0,
    }


def hash_context(validated, state):
    _, _, records_hash = normalize_vehicle_records(state, validated.tolerance_m)
    exact_state = hashlib.sha256(
        json.dumps(state, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "topology_file_sha256": "a" * 64,
        "topology_semantic_sha256": validated.semantic_sha256,
        "approving_manifest_sha256": "b" * 64,
        "state_file_sha256": exact_state,
        "vehicle_records_semantic_sha256": records_hash,
    }


class PhysicalProjectionCoreTests(unittest.TestCase):
    def setUp(self):
        topology, graph = topology_fixture()
        self.validated = validate_physical_stock_topology(topology, graph)

    def assignment(self, position: float):
        state = state_fixture([record(1, position)])
        return project_vehicle_records(
            self.validated, state, hash_context(self.validated, state)
        ).ledger["vehicle_assignments"][0]

    def test_internal_boundaries_are_exact_and_outer_endpoints_snap_only_outside(self):
        tol = POSITION_TOLERANCE_M
        upstream = [50.0 - 2 * tol, 50.0 - tol, 50.0 - tol / 2]
        downstream = [50.0, 50.0 + tol / 2, 50.0 + tol, 100.0 - tol, 100.0]
        for position in upstream:
            with self.subTest(position=position):
                self.assertEqual(self.assignment(position)["stock_id"], "stock:1:1:0:50")
        for position in downstream:
            with self.subTest(position=position):
                self.assertEqual(self.assignment(position)["stock_id"], "stock:1:1:50:100")
        self.assertEqual(self.assignment(100.0)["assignment_status"], "exact_interval")
        snapped_end = self.assignment(100.0 + tol)
        self.assertEqual(snapped_end["stock_id"], "stock:1:1:50:100")
        self.assertEqual(snapped_end["assignment_status"], "outer_endpoint_tolerance_snap")
        snapped_start = self.assignment(-tol)
        self.assertEqual(snapped_start["stock_id"], "stock:1:1:0:50")
        self.assertEqual(snapped_start["assignment_status"], "outer_endpoint_tolerance_snap")
        for position in (-tol - 1e-12, 100.0 + tol + 1e-12):
            state = state_fixture([record(1, position)])
            with self.subTest(position=position), self.assertRaises(ProjectionError) as raised:
                project_vehicle_records(self.validated, state, hash_context(self.validated, state))
            self.assertIn("position_out_of_range", {item["code"] for item in raised.exception.reasons})

    def test_vehicle_identity_and_all_aggregate_maps_fail_closed(self):
        duplicate = state_fixture([record(7, 10.0), record(7, 20.0)])
        with self.assertRaises(ProjectionError) as raised:
            normalize_vehicle_records(duplicate, self.validated.tolerance_m)
        self.assertIn("duplicate_vehicle_in_snapshot", {item["code"] for item in raised.exception.reasons})

        cases = []
        bad_stopped = state_fixture([record(1, 10.0, speed=1.0)])
        bad_stopped["vehicle_records"]["records"][0]["stopped"] = True
        cases.append(bad_stopped)
        bad_count = state_fixture([record(1, 10.0)])
        bad_count["vehicle_records"]["collection_count_after"] = 2
        cases.append(bad_count)
        bad_map = state_fixture([record(1, 10.0)])
        bad_map["vehicle_records"]["full_network_link_counts"] = {"1": 2}
        cases.append(bad_map)
        nonzero_external = state_fixture([record(1, 10.0)])
        nonzero_external["vehicle_records"]["external_source_count"] = 1
        cases.append(nonzero_external)
        wrong_total = state_fixture([record(1, 10.0)])
        wrong_total["total_vehicles"] = 2
        cases.append(wrong_total)
        for state in cases:
            with self.subTest(case=cases.index(state)), self.assertRaises(ProjectionError):
                normalize_vehicle_records(state, self.validated.tolerance_m)

    def test_same_vehicle_later_and_cross_run_is_valid(self):
        hashes = []
        for run_id, sim_sec in (("run-a", 1.0), ("run-a", 2.0), ("run-b", 1.0)):
            state = state_fixture([record(7, 25.0)], run_id=run_id, sim_sec=sim_sec)
            result = project_vehicle_records(
                self.validated, state, hash_context(self.validated, state)
            )
            self.assertEqual(result.status, "PASS")
            hashes.append(result.ledger["normalized_projection_sha256"])
        self.assertEqual(len(hashes), 3)

    def test_invalid_run_time_unknown_lane_and_numeric_types_fail_closed(self):
        invalid_run = state_fixture([record(1, 10.0)], run_id=" invalid ")
        with self.assertRaises(ProjectionError):
            normalize_vehicle_records(invalid_run, self.validated.tolerance_m)

        mismatched_time = state_fixture([record(1, 10.0)])
        mismatched_time["vehicle_records"]["capture_sim_sec_after"] = 901.0
        with self.assertRaises(ProjectionError) as raised:
            normalize_vehicle_records(mismatched_time, self.validated.tolerance_m)
        self.assertIn("com_count_changed", {item["code"] for item in raised.exception.reasons})

        unknown_lane = state_fixture([record(1, 10.0)])
        unknown_lane["vehicle_records"]["records"][0]["link_no"] = 2
        unknown_lane["vehicle_records"]["full_network_link_counts"] = {"2": 1}
        unknown_lane["vehicle_records"]["full_network_link_stopped_counts"] = {"2": 0}
        with self.assertRaises(ProjectionError) as raised:
            project_vehicle_records(
                self.validated,
                unknown_lane,
                hash_context(self.validated, unknown_lane),
            )
        self.assertIn("unknown_lane", {item["code"] for item in raised.exception.reasons})

        invalid_numeric = state_fixture([record(1, 10.0)])
        invalid_numeric["vehicle_records"]["records"][0]["speed_kph"] = "10.0"
        with self.assertRaises(ProjectionError) as raised:
            normalize_vehicle_records(invalid_numeric, self.validated.tolerance_m)
        self.assertIn("invalid_numeric_value", {item["code"] for item in raised.exception.reasons})

    def test_ten_record_orders_share_normalized_hash_but_exact_ledger_hash_tracks_bytes(self):
        records = [record(index + 1, float(index % 100)) for index in range(20)]
        normalized_record_hashes = set()
        normalized_projection_hashes = set()
        ledger_hashes = set()
        for seed in range(10):
            shuffled = copy.deepcopy(records)
            random.Random(seed).shuffle(shuffled)
            state = state_fixture(shuffled)
            context = hash_context(self.validated, state)
            _, _, normalized = normalize_vehicle_records(state, self.validated.tolerance_m)
            result = project_vehicle_records(self.validated, state, context)
            normalized_record_hashes.add(normalized)
            normalized_projection_hashes.add(result.ledger["normalized_projection_sha256"])
            ledger_hashes.add(result.ledger["semantic_sha256"])
        self.assertEqual(len(normalized_record_hashes), 1)
        self.assertEqual(len(normalized_projection_hashes), 1)
        self.assertEqual(len(ledger_hashes), 10)

    def test_boundary_and_multi_owner_views_close_without_role_or_visibility_sums(self):
        for kwargs in ({"boundary": True}, {"multi_owner": True}):
            topology, graph = topology_fixture(**kwargs)
            validated = validate_physical_stock_topology(topology, graph)
            state = state_fixture([record(1, 25.0), record(2, 75.0)])
            ledger = project_vehicle_records(validated, state, hash_context(validated, state)).ledger
            views = ledger["view_summaries"]
            objectives = views["objective_views"]
            self.assertEqual(objectives["physical_total"], 2)
            self.assertEqual(objectives["controller_with_boundary"], 2)
            self.assertEqual(objectives["controller_default"] + objectives["boundary_only"], 2)
            self.assertAlmostEqual(sum(views["owner_partition"].values()), 2.0)

    def test_topology_hash_interval_and_normalized_key_tampering_fail(self):
        topology, graph = topology_fixture()
        stale = copy.deepcopy(topology)
        stale["stocks"][0]["end_m"] = 49.0
        with self.assertRaises(TopologyValidationError) as raised:
            validate_physical_stock_topology(stale, graph)
        self.assertIn("topology_trust_mismatch", {item["code"] for item in raised.exception.reasons})

        malformed = copy.deepcopy(topology)
        malformed["stocks"][0]["link_no"] = "01"
        malformed["semantic_sha256"] = canonical_json_sha256(topology_semantic_payload(malformed))
        with self.assertRaises(TopologyValidationError) as raised:
            validate_physical_stock_topology(malformed, graph)
        self.assertIn("topology_structure_invalid", {item["code"] for item in raised.exception.reasons})

    def test_strict_json_and_atomic_sidecar_replacement(self):
        with self.assertRaises(ValueError):
            strict_json_loads('{"x":NaN}')
        with self.assertRaises(ValueError):
            strict_json_loads('{"x":1,"x":2}')
        state = state_fixture([record(1, 25.0)])
        result = project_vehicle_records(
            self.validated, state, hash_context(self.validated, state)
        )
        with self.assertRaises(TypeError):
            result.ledger["status"] = "FAIL"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.physical_projection_v2_1.json"
            path.write_text('{"status":"STALE_PASS"}', encoding="utf-8")
            write_projection_sidecar(path, result)
            payload = strict_json_loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "PASS")
            self.assertEqual(path.read_bytes()[:3], b'{"c')

    def test_synthetic_20000_record_serialize_parse_project_write_meets_limits(self):
        records = [record(index + 1, float(index % 100)) for index in range(20_000)]
        state = state_fixture(records)
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "state.json"
            sidecar_path = Path(directory) / "state.physical_projection_v2_1.json"
            started = time.perf_counter()
            atomic_write_json(state_path, state)
            parsed_state = strict_load_json(state_path)
            _, _, records_hash = normalize_vehicle_records(
                parsed_state, self.validated.tolerance_m
            )
            context = {
                "topology_file_sha256": "a" * 64,
                "topology_semantic_sha256": self.validated.semantic_sha256,
                "approving_manifest_sha256": "b" * 64,
                "state_file_sha256": file_sha256(state_path),
                "vehicle_records_semantic_sha256": records_hash,
            }
            result = project_vehicle_records(self.validated, parsed_state, context)
            write_projection_sidecar(sidecar_path, result)
            elapsed = time.perf_counter() - started
            state_size = state_path.stat().st_size
            sidecar_size = sidecar_path.stat().st_size
        self.assertLessEqual(state_size, 8 * 1024 * 1024)
        self.assertLessEqual(sidecar_size, 16 * 1024 * 1024)
        self.assertLessEqual(elapsed, 3.0)
        self.assertEqual(result.ledger["projection_diagnostics"]["global_residual"], 0)


if __name__ == "__main__":
    unittest.main()
