from __future__ import annotations

import importlib.util
import hashlib
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "audit_plant_fidelity.py"
SPEC = importlib.util.spec_from_file_location("audit_plant_fidelity", MODULE_PATH)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


CORE_MODULES = (
    "src.controllers.stackelberg_mpc",
    "src.models.demand",
    "src.models.state",
    "src.models.urban_queue_model",
)


def python_tree_sha256(repo_root: Path) -> str:
    source_root = repo_root / "src"
    digest = hashlib.sha256()
    for source in sorted(
        source_root.rglob("*.py"),
        key=lambda item: item.relative_to(source_root).as_posix(),
    ):
        digest.update(source.relative_to(source_root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(source.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def prepare_provenance_assets(root: Path) -> dict[str, object]:
    numsim_root = root / "numsim"
    imported_modules: dict[str, dict[str, str]] = {}
    for index, module_name in enumerate(CORE_MODULES, start=1):
        module_path = numsim_root / (module_name.replace(".", "/") + ".py")
        module_path.parent.mkdir(parents=True, exist_ok=True)
        module_path.write_text(f"VALUE = {index}\n", encoding="utf-8")
        imported_modules[module_name] = {
            "path": str(module_path.resolve()),
            "sha256": audit.sha256_file(module_path),
        }

    network_dir = root / "network"
    network_dir.mkdir()
    network_path = network_dir / "network.inpx"
    network_path.write_text("<network/>\n", encoding="utf-8")
    signal_path = network_dir / "plan.sig"
    signal_path.write_text("signal-plan\n", encoding="utf-8")
    return {
        "numsim_root": numsim_root,
        "numsim_tree_sha256": python_tree_sha256(numsim_root),
        "imported_modules": imported_modules,
        "network_path": network_path,
        "signal_hashes": {signal_path.name: audit.sha256_file(signal_path)},
    }


def write_runtime_record(
    run_dir: Path,
    assets: dict[str, object],
    *,
    suffix: int,
    input_count: float,
    represented: float,
    exit_count: float = 0.0,
    unobservable: float = 0.0,
    unrepresented: float = 0.0,
    wall_sec: float = 1.0,
    run_id: str = "run-a",
    provenance_marker: str = "same",
) -> tuple[Path, Path]:
    run_dir.mkdir(parents=True, exist_ok=True)
    total = represented + exit_count + unobservable + unrepresented
    state_path = run_dir / f"state_{suffix:06d}.json"
    state = {
        "run_id": run_id,
        "sim_sec": suffix,
        "network_path": str(Path(assets["network_path"]).resolve()),
        "total_vehicles": total,
        "local_observation": {
            "schema_version": 2,
            "mode": "real_world_connector_local_v2",
            "scan_ok": True,
            "observed_vehicle_count": input_count,
            "unobservable_vehicle_count": unobservable,
            "link_counts": {"1": input_count},
            "link_speeds_kph": {"1": 30.0},
            "link_stopped_counts": {"1": min(1.0, input_count)},
        },
    }
    state_path.write_text(json.dumps(state), encoding="utf-8")

    network_path = Path(assets["network_path"])
    provenance = {
        "run_id": run_id,
        "workspace_root": str(run_dir.parent.resolve()),
        "workspace_git_commit": provenance_marker,
        "numsim_repo_root": str(Path(assets["numsim_root"]).resolve()),
        "numsim_src_sha256": assets["numsim_tree_sha256"],
        "imported_modules": assets["imported_modules"],
        "signal_program_sha256": assets["signal_hashes"],
        "inputs": {
            "state_json": {
                "path": str(state_path.resolve()),
                "sha256": audit.sha256_file(state_path),
                "exists": True,
            },
            "network_inpx": {
                "path": str(network_path.resolve()),
                "sha256": audit.sha256_file(network_path),
                "exists": True,
            },
        },
    }
    action = {
        "run_id": run_id,
        "metadata": {"decision_wall_sec": wall_sec},
        "projection_diagnostics": {
            "total_vehicle_count_veh": total,
            "input_link_vehicle_count_veh": input_count,
            "represented_vehicle_count_veh": represented,
            "exit_excluded_vehicle_count_veh": exit_count,
            "unobservable_vehicle_count_veh": unobservable,
            "unrepresented_vehicle_count_veh": unrepresented,
            "mass_balance_error_veh": unrepresented,
            "storage_capacity_clipped_veh": 0.0,
        },
        "run_provenance": provenance,
    }
    action_path = run_dir / f"action_{suffix:06d}.json"
    action_path.write_text(json.dumps(action), encoding="utf-8")
    return state_path, action_path


class AuditPlantFidelityTests(unittest.TestCase):
    def test_file_evidence_hashes_and_missing_is_nonfatal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            present = root / "input.txt"
            present.write_text("plant\n", encoding="utf-8")
            evidence = audit.file_evidence(present)
            self.assertTrue(evidence["is_file"])
            self.assertEqual(len(evidence["sha256"]), 64)

            missing = audit.file_evidence(root / "missing.txt")
            self.assertFalse(missing["exists"])
            self.assertEqual(missing["error"], "file not found")

    def test_network_scale_and_sc9004_head_reference(self) -> None:
        xml = """<?xml version="1.0"?>
<network>
  <links>
    <link no="1"><lanes><lane no="1"/></lanes></link>
    <link no="10"><fromLinkEndPt lane="1 1"/><toLinkEndPt lane="2 1"/></link>
  </links>
  <signalControllers>
    <signalController no="1" active="true" supplyFile2="#data#a.sig"/>
    <signalController no="9004" active="true" supplyFile2="#data#b.sig"/>
    <signalController no="9101" active="true" supplyFile2="#data#ramp.sig"/>
  </signalControllers>
  <signalHeads><signalHead no="1" sg="1 1" lane="1 1"/></signalHeads>
</network>"""
        roles = "no,active,unique_head_links\n1,true,1\n9004,true,\n9101,false,10\n"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "network.inpx"
            roles_path = root / "roles.csv"
            path.write_text(xml, encoding="utf-8")
            roles_path.write_text(roles, encoding="utf-8")
            result = audit.network_evidence(path, roles_path)
        self.assertTrue(result["available"])
        self.assertEqual(result["link_count"], 2)
        self.assertEqual(result["connector_count"], 1)
        self.assertEqual(result["raw_active_signal_controller_count"], 3)
        self.assertEqual(result["urban_eligible_signal_controller_count"], 2)
        self.assertEqual(result["model_signal_controller_count"], 1)
        self.assertEqual(result["auxiliary_active_signal_controller_ids"], ["9101"])
        self.assertEqual(result["model_excluded_signal_controllers"][0]["no"], 9004)
        self.assertEqual(result["sc9004"]["head_reference_count"], 0)
        scope_gate = audit.signal_controller_scope_gate(result)
        self.assertEqual(scope_gate["status"], "PASS")
        self.assertIn("raw XML active 3 / urban eligible 2 / model 1", scope_gate["reason"])

    def test_assignment_partition_and_equal_hop_tie(self) -> None:
        xml = """<network><links>
<link no="1"/><link no="2"/><link no="3"/>
<link no="10"><fromLinkEndPt lane="1 1"/><toLinkEndPt lane="2 1"/></link>
<link no="11"><fromLinkEndPt lane="1 1"/><toLinkEndPt lane="3 1"/></link>
</links></network>"""
        assignment = {
            "link_owner": {"1": 100, "2": 100, "3": 200},
            "freeway_bound_links": {},
            "monitor_only_exit_links": ["10", "11"],
            "urban_link_count": 5,
        }
        roles = "no,active,unique_head_links\n100,true,2\n200,true,3\n"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            network_path = root / "network.inpx"
            roles_path = root / "roles.csv"
            assignment_path = root / "assignment.json"
            network_path.write_text(xml, encoding="utf-8")
            roles_path.write_text(roles, encoding="utf-8")
            assignment_path.write_text(json.dumps(assignment), encoding="utf-8")
            result = audit.assignment_evidence(assignment_path, network_path, roles_path)
        self.assertEqual(result["coverage_count"], 5)
        self.assertEqual(result["cross_category_duplicate_count"], 0)
        self.assertEqual(result["tie_analysis"]["tie_count"], 1)
        self.assertEqual(result["tie_analysis"]["ties"][0]["link"], "1")

    def test_state_payload_totals_and_missing_fields(self) -> None:
        payload = {
            "run_id": "run-a",
            "sim_sec": 900,
            "network_path": "network.inpx",
            "total_vehicles": 5,
            "local_observation": {
                "schema_version": 2,
                "mode": "real_world_connector_local_v2",
                "scan_ok": True,
                "observed_vehicle_count": 5,
                "unobservable_vehicle_count": 0,
                "link_counts": {"1": 2, "2": 3},
                "link_speeds_kph": {"1": 10, "2": 40},
                "link_stopped_counts": {"1": 1, "2": 2},
            },
        }
        result = audit.inspect_state_payload(payload, "memory")
        self.assertEqual(result["link_vehicle_total"], 5)
        self.assertEqual(result["link_stopped_total"], 3)
        self.assertAlmostEqual(result["link_speed_count_weighted_mean_kph"], 28)
        self.assertTrue(result["has_link_speeds"])
        self.assertEqual(result["schema_status"], "PASS")

        missing = audit.inspect_state_payload({"local_observation": {"link_counts": {}}}, "memory")
        self.assertFalse(missing["has_link_speeds"])
        self.assertFalse(missing["has_link_stopped"])
        self.assertEqual(missing["schema_status"], "FAIL")

    def test_action_inventory_uses_actual_wall_time_and_aggregates_projection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = prepare_provenance_assets(root)
            run_dir = root / "run-a"
            projection_rows = ((6, 6, 0), (291, 288, 3), (100, 95, 5))
            for index, (wall, projection_values) in enumerate(zip((10.0, 20.0, 40.0), projection_rows), start=1):
                input_count, represented, unrepresented = projection_values
                write_runtime_record(
                    run_dir,
                    assets,
                    suffix=index,
                    input_count=input_count,
                    represented=represented,
                    unrepresented=unrepresented,
                    wall_sec=wall,
                )
            result = audit.action_directory_evidence(root)
            states = audit.state_evidence([Path(path) for path in result["state_files"]])
        self.assertEqual(result["action_file_count"], 3)
        self.assertEqual(result["state_file_count"], 3)
        self.assertEqual(result["decision_wall_sec"]["p95"], 40.0)
        self.assertEqual(result["projection_diagnostics_record_count"], 3)
        self.assertEqual(result["projection_diagnostics"]["input_link_vehicle_count_veh"]["sum"], 397.0)
        self.assertEqual(result["projection_contract"]["pass_count"], 3)
        self.assertEqual(result["runtime_provenance_contract"]["pass_count"], 3)
        self.assertEqual(result["run_contract"]["run_count"], 1)
        self.assertEqual(result["run_contract"]["fail_count"], 0)
        self.assertEqual(audit.projection_diagnostics_gate(result)["status"], "PASS")
        self.assertEqual(audit.runtime_provenance_gate(result)["status"], "PASS")
        states["action_dir_discovered_count"] = 3
        states["explicit_configured_count"] = 0
        self.assertEqual(audit.state_observation_contract_gate(states)["status"], "PASS")

    def test_projection_contract_rejects_missing_fields_and_unexplained_clipping(self) -> None:
        missing = audit.projection_contract_record(
            {"input_link_vehicle_count_veh": 10}, "missing.json"
        )
        self.assertEqual(missing["status"], "FAIL")
        self.assertIn("represented_vehicle_count_veh", missing["missing_required_fields"])

        clipped = audit.projection_contract_record(
            {
                "total_vehicle_count_veh": 100,
                "input_link_vehicle_count_veh": 100,
                "represented_vehicle_count_veh": 100,
                "exit_excluded_vehicle_count_veh": 0,
                "unobservable_vehicle_count_veh": 0,
                "unrepresented_vehicle_count_veh": 0,
                "mass_balance_error_veh": 0,
                "storage_capacity_clipped_veh": 2,
            },
            "clipped.json",
        )
        self.assertEqual(clipped["status"], "FAIL")
        explained = dict(
            total_vehicle_count_veh=100,
            input_link_vehicle_count_veh=100,
            represented_vehicle_count_veh=100,
            exit_excluded_vehicle_count_veh=0,
            unobservable_vehicle_count_veh=0,
            unrepresented_vehicle_count_veh=0,
            mass_balance_error_veh=0,
            storage_capacity_clipped_veh=2,
            storage_capacity_clipping_explanation="known downstream cap already accounted for",
        )
        self.assertEqual(audit.projection_contract_record(explained, "explained.json")["status"], "PASS")

    def test_projection_contract_enforces_both_mass_identities_and_nonnegative_values(self) -> None:
        valid = {
            "total_vehicle_count_veh": 10,
            "input_link_vehicle_count_veh": 8,
            "represented_vehicle_count_veh": 6,
            "exit_excluded_vehicle_count_veh": 1,
            "unobservable_vehicle_count_veh": 2,
            "unrepresented_vehicle_count_veh": 1,
            "mass_balance_error_veh": 1,
            "storage_capacity_clipped_veh": 0,
        }
        self.assertEqual(audit.projection_contract_record(valid, "valid.json")["status"], "PASS")

        bad_input = dict(valid, input_link_vehicle_count_veh=9)
        bad_input_record = audit.projection_contract_record(bad_input, "bad-input.json")
        self.assertEqual(bad_input_record["status"], "FAIL")
        self.assertTrue(any("input mass identity" in reason for reason in bad_input_record["reasons"]))

        bad_total = dict(valid, total_vehicle_count_veh=11)
        bad_total_record = audit.projection_contract_record(bad_total, "bad-total.json")
        self.assertEqual(bad_total_record["status"], "FAIL")
        self.assertTrue(any("total mass identity" in reason for reason in bad_total_record["reasons"]))

        negative = dict(valid, exit_excluded_vehicle_count_veh=-1)
        self.assertEqual(audit.projection_contract_record(negative, "negative.json")["status"], "FAIL")

    def test_legacy_incomplete_records_cannot_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = {
                "local_observation": {
                    "link_counts": {"1": 6},
                    "link_speeds_kph": {"1": 30},
                    "link_stopped_counts": {"1": 1},
                }
            }
            (root / "state_000001.json").write_text(json.dumps(state), encoding="utf-8")
            action = {
                "metadata": {
                    "decision_wall_sec": 1,
                    "projection_diagnostics": {
                        "input_link_vehicle_count_veh": 6,
                        "represented_vehicle_count_veh": 6,
                        "unrepresented_vehicle_count_veh": 0,
                        "storage_capacity_clipped_veh": 0,
                    },
                }
            }
            (root / "action_000001.json").write_text(json.dumps(action), encoding="utf-8")
            actions = audit.action_directory_evidence(root)
            states = audit.state_evidence([Path(path) for path in actions["state_files"]])

        self.assertEqual(actions["projection_contract"]["fail_count"], 1)
        self.assertEqual(actions["runtime_provenance_contract"]["fail_count"], 1)
        self.assertEqual(audit.projection_diagnostics_gate(actions)["status"], "FAIL")
        self.assertEqual(audit.runtime_provenance_gate(actions)["status"], "FAIL")
        self.assertEqual(audit.state_observation_contract_gate(states)["status"], "FAIL")

    def test_same_run_with_mixed_provenance_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = prepare_provenance_assets(root)
            run_dir = root / "run-a"
            write_runtime_record(
                run_dir,
                assets,
                suffix=1,
                input_count=8,
                represented=7,
                unrepresented=1,
                provenance_marker="first",
            )
            write_runtime_record(
                run_dir,
                assets,
                suffix=2,
                input_count=9,
                represented=8,
                unrepresented=1,
                provenance_marker="second",
            )
            actions = audit.action_directory_evidence(root)

        self.assertEqual(actions["run_contract"]["run_count"], 1)
        self.assertEqual(actions["run_contract"]["mixed_provenance_run_count"], 1)
        self.assertEqual(audit.runtime_provenance_gate(actions)["status"], "FAIL")

    def test_distinct_run_ids_are_validated_separately(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = prepare_provenance_assets(root)
            write_runtime_record(
                root / "run-a",
                assets,
                suffix=1,
                input_count=8,
                represented=7,
                unrepresented=1,
                run_id="run-a",
                provenance_marker="first",
            )
            write_runtime_record(
                root / "run-b",
                assets,
                suffix=1,
                input_count=9,
                represented=8,
                unrepresented=1,
                run_id="run-b",
                provenance_marker="second",
            )
            actions = audit.action_directory_evidence(root)

        self.assertEqual(actions["run_contract"]["run_count"], 2)
        self.assertEqual(actions["run_contract"]["fail_count"], 0)
        self.assertEqual(audit.runtime_provenance_gate(actions)["status"], "PASS")

    def test_archived_state_copy_is_accepted_by_hash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = prepare_provenance_assets(root)
            state_path, action_path = write_runtime_record(
                root / "run-a",
                assets,
                suffix=1,
                input_count=8,
                represented=7,
                unrepresented=1,
            )
            archived_state = root / "archive" / state_path.name
            archived_state.parent.mkdir()
            archived_state.write_bytes(state_path.read_bytes())
            action = json.loads(action_path.read_text(encoding="utf-8"))
            state = json.loads(archived_state.read_text(encoding="utf-8"))
            record = audit.runtime_provenance_contract_record(
                action["run_provenance"], action_path, archived_state, state
            )
            self.assertEqual(record["status"], "PASS")

            archived_state.write_text(json.dumps({**state, "total_vehicles": 999}), encoding="utf-8")
            changed = audit.runtime_provenance_contract_record(
                action["run_provenance"], action_path, archived_state, state
            )
            self.assertEqual(changed["status"], "FAIL")

    def test_runtime_provenance_detects_tree_network_and_signal_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = prepare_provenance_assets(root)
            write_runtime_record(
                root / "run-a",
                assets,
                suffix=1,
                input_count=8,
                represented=7,
                unrepresented=1,
            )
            module_path = Path(assets["imported_modules"][CORE_MODULES[0]]["path"])
            module_path.write_text("VALUE = 999\n", encoding="utf-8")
            Path(assets["network_path"]).write_text("<changed-network/>\n", encoding="utf-8")
            (Path(assets["network_path"]).parent / "plan.sig").write_text(
                "changed-signal-plan\n",
                encoding="utf-8",
            )
            actions = audit.action_directory_evidence(root)

        record = actions["runtime_provenance_contract"]["records"][0]
        self.assertEqual(record["status"], "FAIL")
        self.assertTrue(any("NumSim source tree hash mismatch" in reason for reason in record["reasons"]))
        self.assertTrue(any("imported module hash mismatch" in reason for reason in record["reasons"]))
        self.assertTrue(any("network_inpx" in reason for reason in record["reasons"]))
        self.assertTrue(any("signal program hashes" in reason for reason in record["reasons"]))

    def test_runtime_provenance_rejects_import_outside_numsim_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = prepare_provenance_assets(root)
            _, action_path = write_runtime_record(
                root / "run-a",
                assets,
                suffix=1,
                input_count=8,
                represented=7,
                unrepresented=1,
            )
            external_module = root / "external_stackelberg.py"
            external_module.write_text("VALUE = 1\n", encoding="utf-8")
            payload = json.loads(action_path.read_text(encoding="utf-8"))
            payload["run_provenance"]["imported_modules"][CORE_MODULES[0]] = {
                "path": str(external_module.resolve()),
                "sha256": audit.sha256_file(external_module),
            }
            action_path.write_text(json.dumps(payload), encoding="utf-8")
            actions = audit.action_directory_evidence(root)

        record = actions["runtime_provenance_contract"]["records"][0]
        self.assertEqual(record["status"], "FAIL")
        self.assertTrue(any("outside NUMSIM_REPO_ROOT" in reason for reason in record["reasons"]))

    def test_signal_readback_recursively_collects_files_and_passes_all_ok_rows(self) -> None:
        header = "sim_sec,sc_no,sg_no,requested_state,readback_state,ok,stage\n"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / "attempt_1" / "decisions"
            nested.mkdir(parents=True)
            (root / "signal_readback.csv").write_text(
                header + "1,9101,1,GREEN,GREEN,1,immediate\n2,9101,1,GREEN,GREEN,1,post_step\n",
                encoding="utf-8",
            )
            (nested / "signal_readback.csv").write_text(
                header + "2,1,2,RED,RED,1,immediate\n3,1,2,RED,RED,1,post_step\n",
                encoding="utf-8",
            )
            actions = audit.action_directory_evidence(root)

        trace = actions["signal_readback"]
        self.assertEqual(trace["file_count"], 2)
        self.assertEqual(trace["row_count"], 4)
        self.assertEqual(trace["ok_count"], 4)
        self.assertEqual(trace["immediate_count"], 2)
        self.assertEqual(trace["post_step_count"], 2)
        self.assertEqual(trace["mismatch_count"], 0)
        self.assertEqual(trace["problem_rows"], [])
        rows_by_parent = {Path(item["path"]).parent.name: item["row_count"] for item in trace["files"]}
        self.assertEqual(rows_by_parent[root.name], 2)
        self.assertEqual(rows_by_parent["decisions"], 2)
        self.assertEqual(audit.signal_com_readback_gate(actions)["status"], "PASS")

    def test_signal_readback_gate_distinguishes_missing_mismatch_and_malformed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            missing = audit.action_directory_evidence(root)
            self.assertEqual(audit.signal_com_readback_gate(missing)["status"], "NOT_EVALUATED")

            (root / "signal_readback.csv").write_text(
                "sim_sec,sc_no,sg_no,requested_state,readback_state,ok,stage\n"
                "10,2,1,GREEN,RED,0,immediate\n",
                encoding="utf-8",
            )
            mismatch = audit.action_directory_evidence(root)
            mismatch_trace = mismatch["signal_readback"]
            self.assertEqual(mismatch_trace["mismatch_count"], 1)
            self.assertEqual(mismatch_trace["ok_not_one_count"], 1)
            self.assertEqual(mismatch_trace["problem_rows"][0]["row_number"], 2)
            self.assertEqual(audit.signal_com_readback_gate(mismatch)["status"], "FAIL")

            (root / "signal_readback.csv").write_text(
                "sim_sec,sc_no,requested_state,readback_state,ok,stage\n"
                "10,2,GREEN,GREEN,1,immediate\n",
                encoding="utf-8",
            )
            malformed = audit.action_directory_evidence(root)
            self.assertEqual(malformed["signal_readback"]["malformed_file_count"], 1)
            self.assertEqual(audit.signal_com_readback_gate(malformed)["status"], "FAIL")

            (root / "signal_readback.csv").write_text(
                "sim_sec,sc_no,sg_no,requested_state,readback_state,ok,stage\n"
                "not-a-time,2,1,GREEN,GREEN,1,immediate\n",
                encoding="utf-8",
            )
            malformed_row = audit.action_directory_evidence(root)
            self.assertEqual(malformed_row["signal_readback"]["malformed_row_count"], 1)
            self.assertIn("sim_sec", malformed_row["signal_readback"]["problem_rows"][0]["errors"][0])
            self.assertEqual(audit.signal_com_readback_gate(malformed_row)["status"], "FAIL")

            (root / "signal_readback.csv").write_text(
                "sim_sec,sc_no,sg_no,requested_state,readback_state,ok,stage\n"
                "10,2,1,GREEN,GREEN,1,immediate\n",
                encoding="utf-8",
            )
            immediate_only = audit.action_directory_evidence(root)
            self.assertEqual(audit.signal_com_readback_gate(immediate_only)["status"], "FAIL")

    def test_signal_event_timing_requires_an_expected_transition_oracle(self) -> None:
        manifest = {
            "inputs": {"primary": {}},
            "network": {},
            "link_assignment": {},
            "adjacency": {},
            "storage_capacity": {},
            "vendor_snapshot": {},
            "actual_numsim": {},
            "state_observations": {},
            "action_directory": {"signal_readback": {}},
            "vissim_error": {},
        }
        event_gate = audit.build_gates(manifest)["signal_event_timing"]
        self.assertEqual(event_gate["status"], "NOT_EVALUATED")
        self.assertIn("expected signal-transition oracle", event_gate["reason"])

    def test_numsim_file_comparison_detects_mismatch_and_extra(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vendor = root / "vendor"
            actual = root / "actual"
            (vendor / "src").mkdir(parents=True)
            (actual / "src").mkdir(parents=True)
            (vendor / "src" / "same.py").write_text("x = 1\n", encoding="utf-8")
            (actual / "src" / "same.py").write_text("x = 1\n", encoding="utf-8")
            (vendor / "src" / "changed.py").write_text("x = 1\n", encoding="utf-8")
            (actual / "src" / "changed.py").write_text("x = 2\n", encoding="utf-8")
            (actual / "src" / "extra.py").write_text("x = 3\n", encoding="utf-8")
            result = audit.numsim_evidence(vendor, actual, "argument")
        self.assertEqual(result["matching_file_count"], 1)
        self.assertEqual(result["mismatch_count"], 2)
        self.assertEqual(result["mismatched_files"][0]["path"], "changed.py")
        self.assertEqual(result["extra_in_actual"], ["extra.py"])

    def test_markdown_has_gate_and_provenance_sections(self) -> None:
        manifest = {
            "generated_at_utc": "2026-08-05T00:00:00+00:00",
            "gates": {"network_xml": {"status": "PASS", "reason": "ok"}},
            "network": {},
            "link_assignment": {"tie_analysis": {}},
            "adjacency": {},
            "storage_capacity": {},
            "action_directory": {"decision_wall_sec": {}},
            "workspace_git": {},
            "vendor_snapshot": {},
            "actual_numsim": {},
            "inputs": {"primary": {}, "signal_program_count": 0},
        }
        markdown = audit.render_markdown(manifest)
        self.assertIn("## Gate Summary", markdown)
        self.assertIn("## Provenance", markdown)
        self.assertIn("Historical `outputs/gates_*`", markdown)
        self.assertIn("Raw XML active signal controllers", markdown)
        self.assertIn("Urban eligible controllers", markdown)
        self.assertIn("Model signal controllers", markdown)
        self.assertIn("Signal readback files / rows", markdown)
        self.assertIn("Signal readback ok / mismatch / ok!=1", markdown)
        self.assertIn("Signal readback malformed rows / files / empty files", markdown)


if __name__ == "__main__":
    unittest.main()
