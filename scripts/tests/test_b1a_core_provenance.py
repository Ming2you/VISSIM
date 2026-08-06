from __future__ import annotations

import copy
from pathlib import Path
import random
import shutil
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
SCRIPT_ROOT = REPO / "scripts"
PLANT_ROOT = REPO / "plant"
for search_root in (SCRIPT_ROOT, PLANT_ROOT):
    if str(search_root) not in sys.path:
        sys.path.insert(0, str(search_root))

from approve_physical_stock_topology import (
    ApprovalValidationError,
    _preflight_fingerprint_sha256,
    main as approve_main,
    semantic_payload as approval_semantic_payload,
    validate_approval_artifact,
)
from build_state_manifest_v2_1 import (
    SELECTION_DOWNSTREAM_CONSUMERS,
    SELECTION_UNITS,
    main as manifest_main,
    selection_semantic_payload,
)
from build_preflight_manifest import main as preflight_main
from build_vissim_lane_graph import build_lane_graph
from compile_physical_stock_topology import (
    compile_physical_stock_topology,
    evidence_identity_hashes,
)
from resolve_lane_routes import compile_route_proofs
from src.vissim_strict.physical_projection import (
    TopologyValidationError,
    atomic_write_json,
    file_sha256,
    normalize_vehicle_records,
    project_vehicle_records,
    strict_load_json,
    topology_semantic_payload,
    validate_physical_stock_topology,
)
from src.vissim_strict.topology import canonical_json_sha256
from src.vissim_strict.run_evidence import (
    CONFIGURATION_INPUT_ROLES,
    PRODUCER_SOURCE_ROLES,
    run_manifest_semantic_sha256,
)
from validate_state_projection_v2_1 import (
    LIVE_EVIDENCE_DOWNSTREAM_CONSUMERS,
    LIVE_EVIDENCE_UNITS,
    live_evidence_semantic_payload,
    main as validate_main,
)
from scripts.tests.test_build_preflight_manifest import SyntheticPreflight


def road(no: int, length: float = 100.0, lane_count: int = 1):
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


def connector(no: int, from_link: int, to_link: int):
    return {
        "id": f"connector:{no}",
        "vissim_no": str(no),
        "name": f"connector-{no}",
        "length_m": 20.0,
        "lane_count": 1,
        "geometry": [
            {"x_m": 80.0, "y_m": float(from_link), "z_m": 0.0},
            {"x_m": 10.0, "y_m": float(to_link), "z_m": 0.0},
        ],
        "lanes": [{
            "id": f"lane:{no}:1",
            "lane_no": 1,
            "width_m": 3.5,
            "closed": False,
        }],
        "from_endpoint": {
            "link_no": str(from_link),
            "lane_no": 1,
            "position_m": 80.0,
        },
        "to_endpoint": {
            "link_no": str(to_link),
            "lane_no": 1,
            "position_m": 10.0,
        },
        "lane_mapping": [{
            "connector_lane_id": f"lane:{no}:1",
            "from_lane_id": f"lane:{from_link}:1",
            "to_lane_id": f"lane:{to_link}:1",
        }],
    }


def canonical_manifest(roads, input_hash, connectors=()):
    return {
        "compiler_version": "fixture-compiler/1",
        "topology_hash": "fixture-topology",
        "validation_report": {"valid": True, "errors": []},
        "source": {"inpx_path": "inputs/network.inpx", "inpx_sha256": input_hash},
        "signal_reference": {
            "schema_version": "signal-reference-v2.1",
            "compiler_hash": "fixture-signal-hash",
        },
        "links": list(roads),
        "connectors": list(connectors),
        "signal_heads": [],
    }


def ownership(items):
    return {
        "rule": "fixture exact ownership",
        "link_owner": {str(key): str(value) for key, value in items},
        "freeway_bound_links": {},
        "monitor_only_exit_links": [],
        "urban_link_count": len(items),
    }


def adjacency(owners):
    values = [str(value) for value in owners]
    return {
        "adjacency": {
            owner: sorted(set(values) - {owner}, key=int)
            for owner in sorted(set(values), key=int)
        },
        "internal_link_members": {},
    }


def capacity():
    return {
        "jam_density_veh_km_lane": 100.0,
        "jam_sample_count": 1,
        "source": "fixture",
        "ramp_queue_source": "fixture",
        "ramp_queue_max_veh_by_ramp": {"fixture-ramp": 1.0},
    }


def vehicle_state(run_id, sim_sec, run_manifest_path, run_manifest_hash, records=None):
    state = {
        "run_provenance": {
            "run_id": run_id,
            "manifest_path": run_manifest_path,
            "manifest_sha256": run_manifest_hash,
        },
        "sim_sec": sim_sec,
        "total_vehicles": 0 if records is None else len(records),
        "stopped_vehicles": 0 if records is None else sum(1 for item in records if item["stopped"]),
    }
    if records is None:
        return state
    counts: dict[str, int] = {}
    stopped: dict[str, int] = {}
    for item in records:
        key = str(item["link_no"])
        counts[key] = counts.get(key, 0) + 1
        if item["stopped"]:
            stopped[key] = stopped.get(key, 0) + 1
    stopped = {key: stopped.get(key, 0) for key in counts}
    state["vehicle_records"] = {
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
        "collection_count_before": len(records),
        "collection_count_after": len(records),
        "record_count": len(records),
        "unobservable_count": 0,
        "external_source_count": 0,
        "full_network_link_counts": counts,
        "full_network_link_stopped_counts": stopped,
        "records": records,
    }
    return state


class B1aProvenanceScriptTests(unittest.TestCase):
    def setUp(self):
        workspace_override = getattr(self, "workspace_root_override", None)
        if workspace_override is None:
            self.temporary = tempfile.TemporaryDirectory()
            self.root = Path(self.temporary.name).resolve()
        else:
            self.temporary = None
            self.root = Path(workspace_override).resolve()
        for relative in ("outputs", "inputs", "evaluation/runs/x", "scripts"):
            (self.root / relative).mkdir(parents=True)
        self.preflight_fixture = SyntheticPreflight(self.root)
        shutil.copy2(
            REPO / "scripts/build_preflight_manifest.py",
            self.root / "scripts/build_preflight_manifest.py",
        )
        self.inpx = self.preflight_fixture.network
        self.dummy = self.root / "inputs/dummy.txt"
        self.dummy.write_text("preflight fixture\n", encoding="utf-8")
        self.run_source_paths = {
            role: (
                self.preflight_fixture.paths[role].relative_to(self.root).as_posix(),
                self.preflight_fixture.paths[role],
            )
            for role in PRODUCER_SOURCE_ROLES
        }
        self.run_input_paths = {
            role: (
                self.preflight_fixture.paths[role].relative_to(self.root).as_posix(),
                self.preflight_fixture.paths[role],
            )
            for role in CONFIGURATION_INPUT_ROLES
            if role != "demand_profile"
        }
        input_hash = file_sha256(self.inpx)
        self.graph = build_lane_graph(canonical_manifest(
            [road(1, lane_count=2), road(3)],
            input_hash,
            [connector(2, 1, 3)],
        ))
        self.routes = compile_route_proofs(self.inpx, self.graph)
        self.own = ownership([(1, 1), (2, 1), (3, 3)])
        self.adj = adjacency([1, 3])
        self.cap = capacity()
        self.preflight_path = self.root / "outputs/preflight_manifest_v3.json"
        self.graph_path = self.root / "outputs/vissim_lane_graph_v2_1.json"
        self.routes_path = self.root / "outputs/lane_route_proofs_v2_1.json"
        self.topology_path = self.root / "outputs/physical_stock_topology_v2_1.json"
        self.approval_path = self.root / "outputs/topology_approval_v2_1.json"
        self.selection_path = self.root / "outputs/state_selection_v2_1.json"
        self.manifest_path = self.root / "outputs/state_manifest_v2_1.json"
        self.audit_path = self.root / "outputs/initial_projection_audit_v2_1.json"
        self.ownership_path = self.root / "inputs/link_assignment.json"
        self.adjacency_path = self.root / "inputs/adjacency.json"
        self.capacity_path = self.root / "inputs/storage_capacity.json"
        atomic_write_json(self.graph_path, self.graph)
        atomic_write_json(self.routes_path, self.routes)
        atomic_write_json(self.ownership_path, self.own)
        atomic_write_json(self.adjacency_path, self.adj)
        atomic_write_json(self.capacity_path, self.cap)
        self.preflight_fixture.paths.update({
            "network": self.inpx,
            "link_assignment": self.ownership_path,
            "adjacency": self.adjacency_path,
            "storage_capacity": self.capacity_path,
            "preflight_producer": self.root / "scripts/build_preflight_manifest.py",
        })
        self.topology = compile_physical_stock_topology(
            self.graph,
            self.routes,
            self.own,
            self.adj,
            self.cap,
            source_file_sha256={
                "lane_graph": file_sha256(self.graph_path),
                "lane_route_proofs": file_sha256(self.routes_path),
                "ownership_evidence": file_sha256(self.ownership_path),
                "adjacency_evidence": file_sha256(self.adjacency_path),
                "capacity_evidence": file_sha256(self.capacity_path),
            },
            expected_evidence_hashes=evidence_identity_hashes(
                self.own, self.adj, self.cap
            ),
        )
        self.assertEqual(self.graph["status"], "PASS")
        self.assertEqual(self.routes["status"], "PASS")
        self.assertEqual(self.topology["status"], "PASS")
        atomic_write_json(self.topology_path, self.topology)
        self.write_preflight()
        self.assertEqual(self.approve(), 0)

    def tearDown(self):
        if self.temporary is not None:
            self.temporary.cleanup()

    def write_preflight(self):
        arguments = [
            "--repo", str(self.root),
            "--runtime-source", str(self.preflight_fixture.runtime_source),
            "--out", str(self.preflight_path),
            "--strict",
            "--expected-model-sc-count", "1",
            "--expected-resolved-sig-count", "1",
            "--expected-auxiliary-sc-count", "1",
        ]
        for key, path in self.preflight_fixture.paths.items():
            arguments.extend(("--" + key.replace("_", "-"), str(path)))
        self.assertEqual(preflight_main(arguments), 0)

    def approve(self):
        return approve_main([
            "--workspace-root", str(self.root),
            "--preflight", "outputs/preflight_manifest_v3.json",
            "--graph", "outputs/vissim_lane_graph_v2_1.json",
            "--routes", "outputs/lane_route_proofs_v2_1.json",
            "--topology", "outputs/physical_stock_topology_v2_1.json",
            "--out", "outputs/topology_approval_v2_1.json",
        ])

    def write_selection_and_state(
        self,
        *,
        required=True,
        records_marker=True,
        records_override=None,
    ):
        bundle = validate_approval_artifact(
            self.approval_path,
            workspace_root=self.root,
            supplied_topology_path=self.topology_path,
        )
        approved = {
            "approving_manifest_path": "outputs/topology_approval_v2_1.json",
            "approving_manifest_sha256": bundle.approval_file_sha256,
            "topology_path": "outputs/physical_stock_topology_v2_1.json",
            "topology_file_sha256": file_sha256(self.topology_path),
            "topology_semantic_sha256": self.topology["semantic_sha256"],
        }
        run_manifest_path = self.root / "evaluation/runs/x/run_manifest.json"
        policy_relative, policy_path = self.run_source_paths["supported_version_policy"]
        policy = strict_load_json(policy_path)
        run_manifest = {
            "schema_version": "run-manifest-v2.1",
            "run_id": "run-13",
            "campaign_id": "campaign-x",
            "attempt": 1,
            "qualification": {"mode": "synthetic_fixture"},
            "approved_topology": approved,
            "preflight": {
                "schema_version": "preflight-v3",
                "path": "outputs/preflight_manifest_v3.json",
                "file_sha256": file_sha256(self.preflight_path),
                "fingerprint_sha256": strict_load_json(self.preflight_path)["fingerprint_sha256"],
            },
            "producer_sources": {
                role: {"path": relative, "file_sha256": file_sha256(path)}
                for role, (relative, path) in self.run_source_paths.items()
            },
            "configuration": {
                "inputs": {
                    role: (
                        {"path": None, "file_sha256": None}
                        if role == "demand_profile"
                        else {
                            "path": self.run_input_paths[role][0],
                            "file_sha256": file_sha256(self.run_input_paths[role][1]),
                        }
                    )
                    for role in CONFIGURATION_INPUT_ROLES
                },
                "simulation": {
                    "sim_period_sec": 1800,
                    "control_interval_sec": 60,
                    "seed": 13,
                    "controller": "stackelberg",
                    "control_start_sec": -1,
                    "warmup_controller": "no-control",
                    "state_log_interval_sec": 5,
                    "demand_scale": 1.0,
                    "demand_profile": None,
                    "incident_link": 0,
                    "incident_lane": 0,
                    "incident_pos_m": -1.0,
                    "incident_start_sec": -1,
                    "incident_end_sec": -1,
                    "incident_name": "",
                },
            },
            "allowed_capture_times": [900.0],
            "supported_version_policy": {
                "schema_version": "supported-vissim-versions-v2.1",
                "path": policy_relative,
                "file_sha256": file_sha256(policy_path),
                "semantic_sha256": policy["semantic_sha256"],
            },
        }
        run_manifest["semantic_sha256"] = run_manifest_semantic_sha256(run_manifest)
        atomic_write_json(run_manifest_path, run_manifest)
        run_hash = file_sha256(run_manifest_path)
        state_path = self.root / "evaluation/runs/x/state_000900.json"
        records = None
        if records_marker:
            records = records_override if records_override is not None else [{
                "veh_no": 17,
                "link_no": 1,
                "lane_no": 1,
                "position_m": 25.0,
                "speed_kph": 1.0,
                "stopped": False,
            }]
        state = vehicle_state(
            "run-13",
            900.0,
            "evaluation/runs/x/run_manifest.json",
            run_hash,
            records,
        )
        atomic_write_json(state_path, state)
        selection = {
            "schema_version": "state-selection-v2.1",
            "input_hashes": {},
            "command_version": {},
            "status": "PASS",
            "reasons": [],
            "sample_dimensions": {"entries": 1},
            "units": copy.deepcopy(SELECTION_UNITS),
            "downstream_consumers": list(SELECTION_DOWNSTREAM_CONSUMERS),
            "campaign_id": "campaign-x",
            "expected_entry_count": 1,
            "entries": [{
                "run_manifest_path": "evaluation/runs/x/run_manifest.json",
                "state_path": "evaluation/runs/x/state_000900.json",
                "run_id": "run-13",
                "sim_sec": 900.0,
                "required_vehicle_records": required,
            }],
        }
        selection["semantic_sha256"] = canonical_json_sha256(
            selection_semantic_payload(selection)
        )
        atomic_write_json(self.selection_path, selection)
        return state_path, run_manifest_path

    def build_manifest(self):
        return manifest_main([
            "--workspace-root", str(self.root),
            "--approval", "outputs/topology_approval_v2_1.json",
            "--topology", "outputs/physical_stock_topology_v2_1.json",
            "--selection", "outputs/state_selection_v2_1.json",
            "--out", "outputs/state_manifest_v2_1.json",
        ])

    def validate(self, live_evidence: Path | None = None):
        argv = [
            "--states", str(self.manifest_path),
            "--topology", str(self.topology_path),
            "--out", str(self.audit_path),
        ]
        if live_evidence is not None:
            argv.extend(["--live-evidence", str(live_evidence)])
        return validate_main(argv)

    def write_live_evidence(self, state_path: Path) -> Path:
        manifest = strict_load_json(self.manifest_path)
        state = strict_load_json(state_path)
        entry = manifest["states"][0]
        envelope = state["vehicle_records"]
        sidecar_path = state_path.with_name(
            "state_000900.physical_projection_v2_1.json"
        )
        sidecar = strict_load_json(sidecar_path)
        raw_samples = []
        for index, record in enumerate(envelope["records"]):
            lane_raw = (
                f" {record['link_no']}-{record['lane_no']} "
                if index == 0
                else f"{record['link_no']}-{record['lane_no']}"
            )
            raw_samples.append({
                "com_key": record["veh_no"],
                "no_value": record["veh_no"],
                "lane_raw": lane_raw,
                "parsed_link_no": record["link_no"],
                "parsed_lane_no": record["lane_no"],
                "position_value": record["position_m"],
                "speed_value": record["speed_kph"],
            })
        timing_samples = [1.0 + index / 1000.0 for index in range(20)]
        evidence = {
            "schema_version": "projection-live-evidence-v2.1",
            "input_hashes": {
                "state_manifest_file_sha256": file_sha256(self.manifest_path),
                "state_manifest_semantic_sha256": manifest["semantic_sha256"],
                "state_set_semantic_sha256": manifest["input_hashes"][
                    "state_set_semantic_sha256"
                ],
                "approving_manifest_sha256": manifest["approved_topology"][
                    "approving_manifest_sha256"
                ],
                "topology_file_sha256": manifest["approved_topology"][
                    "topology_file_sha256"
                ],
                "topology_semantic_sha256": manifest["approved_topology"][
                    "topology_semantic_sha256"
                ],
            },
            "command_version": {},
            "status": "PASS",
            "reasons": [],
            "sample_dimensions": {
                "states": 1,
                "nonzero_live_states": 1,
                "timing_samples": len(timing_samples),
            },
            "units": copy.deepcopy(LIVE_EVIDENCE_UNITS),
            "downstream_consumers": list(LIVE_EVIDENCE_DOWNSTREAM_CONSUMERS),
            "states": [{
                "state_path": entry["state_path"],
                "state_file_sha256": entry["state_file_sha256"],
                "run_id": entry["run_id"],
                "sim_sec": entry["sim_sec"],
                "capture_source": "live_vissim_com",
                "vissim_version": "Vissim fixture supported-version",
                "supported_vissim_version": True,
                "collection_count_before": envelope["collection_count_before"],
                "collection_count_after": envelope["collection_count_after"],
                "raw_record_count": sidecar["projection_diagnostics"][
                    "raw_record_count"
                ],
                "assigned_count": sidecar["projection_diagnostics"][
                    "unique_assigned_count"
                ],
                "stock_total": sidecar["projection_diagnostics"]["stock_total"],
                "global_residual": sidecar["projection_diagnostics"][
                    "global_residual"
                ],
                "raw_attribute_samples": raw_samples,
                "runner_utf8_without_bom": True,
                "public_projector_parsed": True,
            }],
            "performance": {
                "qualification_record_count": 20_000,
                "state_envelope_size_bytes": 2 * 1024 * 1024,
                "sidecar_size_bytes": 6 * 1024 * 1024,
                "action_reference_size_bytes": 1024,
                "decision_budget_sec": 30.0,
                "timing_scope": "live_com_capture+serialize+strict_parse+public_project+atomic_sidecar_write",
                "combined_wall_sec_samples": timing_samples,
                "p95_wall_sec": timing_samples[18],
            },
        }
        evidence["semantic_sha256"] = canonical_json_sha256(
            live_evidence_semantic_payload(evidence)
        )
        path = self.root / "outputs/projection_live_evidence_v2_1.json"
        atomic_write_json(path, evidence)
        return path

    def test_end_to_end_projection_sidecar_pass_aggregate_not_evaluated(self):
        state_path, _ = self.write_selection_and_state()
        self.assertEqual(self.build_manifest(), 0)
        manifest = strict_load_json(self.manifest_path)
        self.assertEqual(manifest["status"], "PASS")
        self.assertEqual(set(manifest["input_hashes"]), {
            "approving_manifest_sha256",
            "state_selection_file_sha256",
            "state_selection_semantic_sha256",
            "topology_file_sha256",
            "topology_semantic_sha256",
            "state_set_semantic_sha256",
        })
        self.assertEqual(self.validate(), 2)
        sidecar = strict_load_json(
            state_path.with_name("state_000900.physical_projection_v2_1.json")
        )
        audit = strict_load_json(self.audit_path)
        self.assertEqual(sidecar["status"], "PASS")
        self.assertEqual(set(sidecar["input_hashes"]), {
            "topology_file_sha256",
            "topology_semantic_sha256",
            "approving_manifest_sha256",
            "state_file_sha256",
            "vehicle_records_semantic_sha256",
        })
        self.assertEqual(sidecar["projection_diagnostics"]["global_residual"], 0)
        self.assertEqual(audit["status"], "NOT_EVALUATED")
        self.assertEqual(audit["live_gates"], {
            "supported_vissim_com_capture": "NOT_EVALUATED",
            "live_performance_p95": "NOT_EVALUATED",
        })

    def test_required_and_optional_missing_envelope_remain_distinct(self):
        state_path, _ = self.write_selection_and_state(required=False, records_marker=False)
        self.assertEqual(self.build_manifest(), 0)
        self.assertEqual(self.validate(), 2)
        sidecar_path = state_path.with_name("state_000900.physical_projection_v2_1.json")
        self.assertEqual(strict_load_json(sidecar_path)["status"], "NOT_EVALUATED")

        selection = strict_load_json(self.selection_path)
        selection["entries"][0]["required_vehicle_records"] = True
        selection["semantic_sha256"] = canonical_json_sha256(selection_semantic_payload(selection))
        atomic_write_json(self.selection_path, selection)
        self.assertEqual(self.build_manifest(), 0)
        sidecar_path.write_text('{"status":"STALE_PASS"}', encoding="utf-8")
        self.assertEqual(self.validate(), 1)
        self.assertEqual(strict_load_json(sidecar_path)["status"], "FAIL")

    def test_optional_missing_envelope_cannot_mask_state_hash_tamper(self):
        state_path, _ = self.write_selection_and_state(
            required=False, records_marker=False
        )
        self.assertEqual(self.build_manifest(), 0)
        state = strict_load_json(state_path)
        state["total_vehicles"] = 99
        atomic_write_json(state_path, state)
        sidecar_path = state_path.with_name(
            "state_000900.physical_projection_v2_1.json"
        )
        sidecar_path.write_text('{"status":"STALE_PASS"}', encoding="utf-8")
        self.audit_path.write_text('{"status":"STALE_PASS"}', encoding="utf-8")
        self.assertEqual(self.validate(), 1)
        sidecar = strict_load_json(sidecar_path)
        self.assertEqual(sidecar["status"], "FAIL")
        self.assertIn(
            "topology_trust_mismatch",
            {reason["code"] for reason in sidecar["reasons"]},
        )
        self.assertEqual(strict_load_json(self.audit_path)["status"], "FAIL")

    def test_huge_state_integer_replaces_stale_audit_and_sidecar_with_fail(self):
        state_path, _ = self.write_selection_and_state()
        state = strict_load_json(state_path)
        state["vehicle_records"]["records"][0]["speed_kph"] = 10**400
        atomic_write_json(state_path, state)
        self.assertEqual(self.build_manifest(), 0)
        sidecar_path = state_path.with_name(
            "state_000900.physical_projection_v2_1.json"
        )
        sidecar_path.write_text('{"status":"STALE_PASS"}', encoding="utf-8")
        self.audit_path.write_text('{"status":"STALE_PASS"}', encoding="utf-8")
        self.assertEqual(self.validate(), 1)
        sidecar = strict_load_json(sidecar_path)
        self.assertEqual(sidecar["status"], "FAIL")
        self.assertIn(
            "invalid_numeric_value",
            {reason["code"] for reason in sidecar["reasons"]},
        )
        self.assertEqual(strict_load_json(self.audit_path)["status"], "FAIL")

    def test_huge_topology_integer_replaces_stale_approval_with_fail(self):
        topology = strict_load_json(self.topology_path)
        topology["stocks"][0]["length_m"] = 10**400
        topology["semantic_sha256"] = canonical_json_sha256(
            topology_semantic_payload(topology)
        )
        atomic_write_json(self.topology_path, topology)
        self.approval_path.write_text('{"status":"STALE_PASS"}', encoding="utf-8")
        self.assertEqual(self.approve(), 1)
        approval = strict_load_json(self.approval_path)
        self.assertEqual(approval["status"], "FAIL")
        self.assertTrue({
            reason["code"] for reason in approval["reasons"]
        } & {"topology_structure_invalid", "topology_trust_mismatch"})

    def test_huge_selection_integer_replaces_stale_manifest_with_fail(self):
        self.write_selection_and_state()
        selection = strict_load_json(self.selection_path)
        selection["entries"][0]["sim_sec"] = 10**400
        selection["semantic_sha256"] = canonical_json_sha256(
            selection_semantic_payload(selection)
        )
        atomic_write_json(self.selection_path, selection)
        self.manifest_path.write_text('{"status":"STALE_PASS"}', encoding="utf-8")
        self.assertEqual(self.build_manifest(), 1)
        manifest = strict_load_json(self.manifest_path)
        self.assertEqual(manifest["status"], "FAIL")
        self.assertEqual(manifest["reasons"][0]["code"], "aggregate_mismatch")

    def test_valid_bound_live_evidence_reaches_pass_and_timing_tamper_fails(self):
        records = [
            {
                "veh_no": 17,
                "link_no": 1,
                "lane_no": 2,
                "position_m": 25.0,
                "speed_kph": 10.0,
                "stopped": False,
            },
            {
                "veh_no": 18,
                "link_no": 2,
                "lane_no": 1,
                "position_m": 10.0,
                "speed_kph": 0.5,
                "stopped": True,
            },
        ]
        state_path, _ = self.write_selection_and_state(records_override=records)
        self.assertEqual(self.build_manifest(), 0)
        self.assertEqual(self.validate(), 2)
        evidence_path = self.write_live_evidence(state_path)
        self.assertEqual(self.validate(evidence_path), 0)
        audit = strict_load_json(self.audit_path)
        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(audit["live_gates"], {
            "supported_vissim_com_capture": "PASS",
            "live_performance_p95": "PASS",
        })

        evidence = strict_load_json(evidence_path)
        evidence["performance"]["combined_wall_sec_samples"] = [4.0] * 20
        evidence["performance"]["p95_wall_sec"] = 4.0
        evidence["semantic_sha256"] = canonical_json_sha256(
            live_evidence_semantic_payload(evidence)
        )
        atomic_write_json(evidence_path, evidence)
        self.audit_path.write_text('{"status":"STALE_PASS"}', encoding="utf-8")
        self.assertEqual(self.validate(evidence_path), 1)
        self.assertEqual(strict_load_json(self.audit_path)["status"], "FAIL")

    def test_tampered_state_replaces_stale_sidecar_and_audit(self):
        state_path, _ = self.write_selection_and_state()
        self.assertEqual(self.build_manifest(), 0)
        self.assertEqual(self.validate(), 2)
        sidecar_path = state_path.with_name("state_000900.physical_projection_v2_1.json")
        old_sidecar_hash = file_sha256(sidecar_path)
        state = strict_load_json(state_path)
        state["vehicle_records"]["records"][0]["position_m"] = 200.0
        atomic_write_json(state_path, state)
        self.audit_path.write_text('{"status":"STALE_PASS"}', encoding="utf-8")
        self.assertEqual(self.validate(), 1)
        self.assertEqual(strict_load_json(sidecar_path)["status"], "FAIL")
        self.assertNotEqual(file_sha256(sidecar_path), old_sidecar_hash)
        self.assertEqual(strict_load_json(self.audit_path)["status"], "FAIL")

    def test_selection_tamper_and_absolute_child_path_fail_closed(self):
        state_path, _ = self.write_selection_and_state()
        self.assertEqual(self.build_manifest(), 0)
        selection = strict_load_json(self.selection_path)
        selection["campaign_id"] = "tampered-campaign"
        selection["semantic_sha256"] = canonical_json_sha256(selection_semantic_payload(selection))
        atomic_write_json(self.selection_path, selection)
        self.audit_path.write_text('{"status":"STALE_PASS"}', encoding="utf-8")
        self.assertEqual(self.validate(), 1)
        self.assertEqual(strict_load_json(self.audit_path)["status"], "FAIL")

        selection["entries"][0]["state_path"] = str(state_path)
        selection["semantic_sha256"] = canonical_json_sha256(selection_semantic_payload(selection))
        atomic_write_json(self.selection_path, selection)
        self.manifest_path.write_text('{"status":"STALE_PASS"}', encoding="utf-8")
        self.assertEqual(self.build_manifest(), 1)
        self.assertEqual(strict_load_json(self.manifest_path)["status"], "FAIL")

    def test_topology_and_graph_tamper_replace_stale_approval(self):
        graph = strict_load_json(self.graph_path)
        graph["nodes"][0]["name"] = "tampered-without-semantic-rehash"
        atomic_write_json(self.graph_path, graph)
        self.assertEqual(strict_load_json(self.approval_path)["status"], "PASS")
        self.assertEqual(self.approve(), 1)
        self.assertEqual(strict_load_json(self.approval_path)["status"], "FAIL")

    def test_independent_a2_replay_rejects_coherently_rehashed_mutation_matrix(self):
        base = copy.deepcopy(self.topology)

        def owner_view(value):
            target = next(
                stock
                for stock in value["stocks"]
                if stock["control_owner_state"]["kind"] == "controlled"
            )
            target["control_owner_weights"] = {"attacker:owner": 1.0}
            target["visible_to"] = ["attacker:owner"]

        def metadata(value):
            value["canonical_json_version"] = "attacker-canonical-json/v1"

        def input_hash(value):
            key = "ownership_evidence_semantic_sha256"
            value["input_hashes"][key] = "a" * 64
            value["source_artifacts"][key] = "a" * 64

        def command(value):
            value["command_version"]["version"] = "attacker/1"
            value["command"]["version"] = "attacker/1"
            value["command"]["source_sha256"][
                "scripts/compile_physical_stock_topology.py"
            ] = "b" * 64
            value["command_version"]["sha256"] = "b" * 64
            value["command"]["command_hash"] = canonical_json_sha256(
                value["command"]["source_sha256"]
            )

        def sample_dimension(value):
            value["sample_dimensions"]["attacker_dimension"] = 1

        def edge_position(value):
            self.assertTrue(value["stock_edges"])
            value["stock_edges"][0]["from_position_m"] += 1.0

        def membership(value):
            value["stocks"][0]["route_memberships"].append({"attacker": True})
            value["sample_dimensions"]["route_memberships"] += 1

        for name, mutate in (
            ("owner_view", owner_view),
            ("canonical_json_version", metadata),
            ("input_hash", input_hash),
            ("command", command),
            ("sample_dimension", sample_dimension),
            ("edge_position", edge_position),
            ("route_membership", membership),
        ):
            with self.subTest(name=name):
                candidate = copy.deepcopy(base)
                mutate(candidate)
                candidate["semantic_sha256"] = canonical_json_sha256(
                    topology_semantic_payload(candidate)
                )
                atomic_write_json(self.topology_path, candidate)
                self.approval_path.write_text(
                    '{"status":"STALE_PASS"}', encoding="utf-8"
                )
                self.assertEqual(self.approve(), 1)
                self.assertEqual(
                    strict_load_json(self.approval_path)["status"], "FAIL"
                )

    def test_rehashed_approval_rejects_command_and_noncanonical_root(self):
        base = strict_load_json(self.approval_path)
        for name, mutate in (
            (
                "command_version",
                lambda value: value.__setitem__(
                    "command_version", {"producer": "attacker"}
                ),
            ),
            (
                "workspace_root",
                lambda value: value.__setitem__(
                    "workspace_root_relative_to_artifact", "../outputs/.."
                ),
            ),
        ):
            with self.subTest(name=name):
                candidate = copy.deepcopy(base)
                mutate(candidate)
                candidate["semantic_sha256"] = canonical_json_sha256(
                    approval_semantic_payload(candidate)
                )
                atomic_write_json(self.approval_path, candidate)
                with self.assertRaises(ApprovalValidationError):
                    validate_approval_artifact(
                        self.approval_path,
                        workspace_root=self.root,
                        supplied_topology_path=self.topology_path,
                    )

    def test_nested_preflight_artifact_and_signal_paths_must_be_contained(self):
        base = strict_load_json(self.preflight_path)
        with tempfile.TemporaryDirectory(dir=self.root.parent) as outside_name:
            outside = Path(outside_name)
            outside_capacity = outside / "storage_capacity.json"
            shutil.copy2(self.capacity_path, outside_capacity)
            candidate = copy.deepcopy(base)
            candidate["artifacts"]["storage_capacity"]["path"] = str(
                outside_capacity
            )
            fingerprint = _preflight_fingerprint_sha256(candidate)
            candidate["fingerprint"]["sha256"] = fingerprint
            candidate["fingerprint_sha256"] = fingerprint
            atomic_write_json(self.preflight_path, candidate)
            self.approval_path.write_text('{"status":"STALE_PASS"}', encoding="utf-8")
            self.assertEqual(self.approve(), 1)
            self.assertEqual(strict_load_json(self.approval_path)["status"], "FAIL")

            outside_signal = outside / "SC1.sig"
            outside_signal.write_text("fixture signal\n", encoding="utf-8")
            candidate = copy.deepcopy(base)
            signal_hash = file_sha256(outside_signal)
            candidate["network"]["resolved_signal_programs"] = [{
                "controller_no": "1",
                "path": str(outside_signal),
                "exists": True,
                "sha256": signal_hash,
            }]
            candidate["input_hashes"]["signal_program.SC1"] = signal_hash
            candidate["sample_dimensions"].update({
                "resolved_signal_programs": 1,
                "unique_resolved_signal_programs": 1,
                "hashed_artifacts": len(candidate["input_hashes"]),
            })
            fingerprint = _preflight_fingerprint_sha256(candidate)
            candidate["fingerprint"]["sha256"] = fingerprint
            candidate["fingerprint_sha256"] = fingerprint
            atomic_write_json(self.preflight_path, candidate)
            self.assertEqual(self.approve(), 1)
            self.assertEqual(strict_load_json(self.approval_path)["status"], "FAIL")

    def test_malformed_nested_approval_record_matrix_replaces_stale_output(self):
        base_preflight = strict_load_json(self.preflight_path)
        base_graph = strict_load_json(self.graph_path)
        base_routes = strict_load_json(self.routes_path)
        base_topology = strict_load_json(self.topology_path)

        def signal_record(value, malformed):
            value["network"]["resolved_signal_programs"] = [malformed]

        def artifact_record(value, malformed):
            value["artifacts"]["network"] = malformed

        def graph_node(value, malformed):
            value["nodes"] = [malformed]

        def graph_lane_mapping(value, malformed):
            value["connectors"][0]["lane_mapping"] = [malformed]

        def route_proof(value, malformed):
            value["proofs"] = [malformed]

        def route_decision(value, malformed):
            value["routing_decisions"] = [malformed]

        def topology_stock(value, malformed):
            value["stocks"] = [malformed]

        mutations = (
            ("resolved_signal_program", "preflight", signal_record),
            ("artifact", "preflight", artifact_record),
            ("graph_node", "graph", graph_node),
            ("graph_lane_mapping", "graph", graph_lane_mapping),
            ("route_proof", "routes", route_proof),
            ("route_decision", "routes", route_decision),
            ("topology_stock", "topology", topology_stock),
        )
        malformed_values = (1, [], "malformed-record")
        for name, target, mutate in mutations:
            for malformed in malformed_values:
                with self.subTest(name=name, malformed_type=type(malformed).__name__):
                    values = {
                        "preflight": copy.deepcopy(base_preflight),
                        "graph": copy.deepcopy(base_graph),
                        "routes": copy.deepcopy(base_routes),
                        "topology": copy.deepcopy(base_topology),
                    }
                    mutate(values[target], malformed)
                    atomic_write_json(self.preflight_path, values["preflight"])
                    atomic_write_json(self.graph_path, values["graph"])
                    atomic_write_json(self.routes_path, values["routes"])
                    atomic_write_json(self.topology_path, values["topology"])
                    outputs = []
                    for _ in range(2):
                        self.approval_path.write_text(
                            '{"status":"STALE_PASS"}', encoding="utf-8"
                        )
                        self.assertEqual(self.approve(), 1)
                        approval = strict_load_json(self.approval_path)
                        self.assertEqual(approval["status"], "FAIL")
                        self.assertTrue(approval["reasons"])
                        self.assertTrue(all(
                            reason.get("code") in {
                                "topology_trust_mismatch",
                                "topology_structure_invalid",
                            }
                            for reason in approval["reasons"]
                        ))
                        outputs.append(self.approval_path.read_bytes())
                    self.assertEqual(outputs[0], outputs[1])

    def test_malformed_selection_and_state_record_matrix_replaces_stale_outputs(self):
        for malformed in (1, [], "malformed-record"):
            with self.subTest(boundary="selection", malformed_type=type(malformed).__name__):
                self.write_selection_and_state()
                selection = strict_load_json(self.selection_path)
                selection["entries"] = [malformed]
                selection["semantic_sha256"] = canonical_json_sha256(
                    selection_semantic_payload(selection)
                )
                atomic_write_json(self.selection_path, selection)
                self.manifest_path.write_text(
                    '{"status":"STALE_PASS"}', encoding="utf-8"
                )
                self.assertEqual(self.build_manifest(), 1)
                manifest = strict_load_json(self.manifest_path)
                self.assertEqual(manifest["status"], "FAIL")
                self.assertEqual(manifest["reasons"][0]["code"], "aggregate_mismatch")

            with self.subTest(boundary="state", malformed_type=type(malformed).__name__):
                state_path, _ = self.write_selection_and_state()
                state = strict_load_json(state_path)
                state["vehicle_records"]["records"] = [malformed]
                state["vehicle_records"]["record_count"] = 1
                state["vehicle_records"]["collection_count_before"] = 1
                state["vehicle_records"]["collection_count_after"] = 1
                state["total_vehicles"] = 1
                atomic_write_json(state_path, state)
                self.assertEqual(self.build_manifest(), 0)
                sidecar_path = state_path.with_name(
                    "state_000900.physical_projection_v2_1.json"
                )
                sidecar_path.write_text('{"status":"STALE_PASS"}', encoding="utf-8")
                self.audit_path.write_text('{"status":"STALE_PASS"}', encoding="utf-8")
                self.assertEqual(self.validate(), 1)
                sidecar = strict_load_json(sidecar_path)
                self.assertEqual(sidecar["status"], "FAIL")
                self.assertIn(
                    "invalid_table_shape",
                    {reason["code"] for reason in sidecar["reasons"]},
                )
                self.assertEqual(strict_load_json(self.audit_path)["status"], "FAIL")

    def test_malformed_live_and_performance_record_matrix_replaces_stale_audit(self):
        records = [
            {
                "veh_no": 17,
                "link_no": 1,
                "lane_no": 2,
                "position_m": 25.0,
                "speed_kph": 10.0,
                "stopped": False,
            },
            {
                "veh_no": 18,
                "link_no": 2,
                "lane_no": 1,
                "position_m": 10.0,
                "speed_kph": 0.5,
                "stopped": True,
            },
        ]
        state_path, _ = self.write_selection_and_state(records_override=records)
        self.assertEqual(self.build_manifest(), 0)
        self.assertEqual(self.validate(), 2)
        evidence_path = self.write_live_evidence(state_path)
        base = strict_load_json(evidence_path)

        def live_state(value, malformed):
            value["states"] = [malformed]

        def raw_sample(value, malformed):
            value["states"][0]["raw_attribute_samples"] = [malformed]

        def performance_record(value, malformed):
            value["performance"] = malformed

        def timing_record(value, malformed):
            value["performance"]["combined_wall_sec_samples"] = [malformed]

        for name, mutate in (
            ("live_state", live_state),
            ("raw_attribute_sample", raw_sample),
            ("performance", performance_record),
            ("timing_sample", timing_record),
        ):
            for malformed in (1, [], "malformed-record"):
                with self.subTest(name=name, malformed_type=type(malformed).__name__):
                    evidence = copy.deepcopy(base)
                    mutate(evidence, malformed)
                    evidence["semantic_sha256"] = canonical_json_sha256(
                        live_evidence_semantic_payload(evidence)
                    )
                    atomic_write_json(evidence_path, evidence)
                    self.audit_path.write_text(
                        '{"status":"STALE_PASS"}', encoding="utf-8"
                    )
                    self.assertEqual(self.validate(evidence_path), 1)
                    audit = strict_load_json(self.audit_path)
                    self.assertEqual(audit["status"], "FAIL")
                    self.assertTrue(audit["reasons"])

    def test_duplicate_live_path_and_identity_rows_fail_after_rehash(self):
        records = [
            {
                "veh_no": 17,
                "link_no": 1,
                "lane_no": 2,
                "position_m": 25.0,
                "speed_kph": 10.0,
                "stopped": False,
            },
            {
                "veh_no": 18,
                "link_no": 2,
                "lane_no": 1,
                "position_m": 10.0,
                "speed_kph": 0.5,
                "stopped": True,
            },
        ]
        state_path, _ = self.write_selection_and_state(records_override=records)
        self.assertEqual(self.build_manifest(), 0)
        self.assertEqual(self.validate(), 2)
        evidence_path = self.write_live_evidence(state_path)
        base = strict_load_json(evidence_path)

        variants = []
        exact_duplicate = copy.deepcopy(base["states"][0])
        variants.append(("exact", exact_duplicate, {
            "duplicate live state_path",
            "duplicate live run/time identity",
        }))
        duplicate_path = copy.deepcopy(base["states"][0])
        duplicate_path["run_id"] = "different-run"
        duplicate_path["sim_sec"] = 901.0
        variants.append(("path", duplicate_path, {"duplicate live state_path"}))
        duplicate_identity = copy.deepcopy(base["states"][0])
        duplicate_identity["state_path"] = "evaluation/runs/x/other.json"
        variants.append((
            "identity",
            duplicate_identity,
            {"duplicate live run/time identity"},
        ))
        for name, duplicate, expected_issues in variants:
            with self.subTest(name=name):
                evidence = copy.deepcopy(base)
                evidence["states"].append(duplicate)
                evidence["sample_dimensions"].update({
                    "states": 2,
                    "nonzero_live_states": 2,
                })
                evidence["semantic_sha256"] = canonical_json_sha256(
                    live_evidence_semantic_payload(evidence)
                )
                atomic_write_json(evidence_path, evidence)
                self.audit_path.write_text('{"status":"STALE_PASS"}', encoding="utf-8")
                self.assertEqual(self.validate(evidence_path), 1)
                audit = strict_load_json(self.audit_path)
                self.assertEqual(audit["status"], "FAIL")
                issue_text = repr(audit["reasons"])
                for expected in expected_issues:
                    self.assertIn(expected, issue_text)

    def test_empty_closed_selection_is_not_evaluated(self):
        selection = {
            "schema_version": "state-selection-v2.1",
            "input_hashes": {},
            "command_version": {},
            "status": "PASS",
            "reasons": [],
            "sample_dimensions": {"entries": 0},
            "units": copy.deepcopy(SELECTION_UNITS),
            "downstream_consumers": list(SELECTION_DOWNSTREAM_CONSUMERS),
            "campaign_id": "empty-campaign",
            "expected_entry_count": 0,
            "entries": [],
        }
        selection["semantic_sha256"] = canonical_json_sha256(selection_semantic_payload(selection))
        atomic_write_json(self.selection_path, selection)
        self.assertEqual(self.build_manifest(), 0)
        self.assertEqual(self.validate(), 2)
        self.assertEqual(strict_load_json(self.audit_path)["status"], "NOT_EVALUATED")

    def test_ten_compiler_input_orders_keep_a2_semantics_and_projection_topology(self):
        input_hash = file_sha256(self.inpx)
        graph = build_lane_graph(canonical_manifest([road(1), road(2), road(3)], input_hash))
        routes = compile_route_proofs(self.inpx, graph)
        hashes = set()
        stock_id_sets = set()
        projection_hashes = set()
        base = [(1, 1), (2, 2), (3, 3)]
        for seed in range(10):
            shuffled = base[:]
            random.Random(seed).shuffle(shuffled)
            own = ownership(shuffled)
            adj = adjacency([owner for _, owner in shuffled])
            cap = capacity()
            topology = compile_physical_stock_topology(
                graph,
                routes,
                own,
                adj,
                cap,
                expected_evidence_hashes=evidence_identity_hashes(own, adj, cap),
            )
            self.assertEqual(topology["status"], "PASS")
            hashes.add(topology["semantic_sha256"])
            stock_id_sets.add(tuple(item["id"] for item in topology["stocks"]))
            validated = validate_physical_stock_topology(topology, graph)
            state = vehicle_state("run-13", 900.0, "ignored", "0" * 64, [{
                "veh_no": 1,
                "link_no": 1,
                "lane_no": 1,
                "position_m": 25.0,
                "speed_kph": 10.0,
                "stopped": False,
            }])
            _, _, records_hash = normalize_vehicle_records(state, validated.tolerance_m)
            result = project_vehicle_records(validated, state, {
                "topology_file_sha256": "a" * 64,
                "topology_semantic_sha256": validated.semantic_sha256,
                "approving_manifest_sha256": "b" * 64,
                "state_file_sha256": "c" * 64,
                "vehicle_records_semantic_sha256": records_hash,
            })
            projection_hashes.add(result.ledger["normalized_projection_sha256"])
        self.assertEqual(len(hashes), 1)
        self.assertEqual(len(stock_id_sets), 1)
        self.assertEqual(len(projection_hashes), 1)


if __name__ == "__main__":
    unittest.main()
