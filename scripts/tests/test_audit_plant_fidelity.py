from __future__ import annotations

import importlib.util
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "audit_plant_fidelity.py"
REPO = MODULE_PATH.parents[1]
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
    def run_audit_cli(self, action_dir: Path, *arguments: str) -> tuple[subprocess.CompletedProcess[str], dict]:
        json_out = action_dir.parent / "audit.json"
        markdown_out = action_dir.parent / "audit.md"
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                str(MODULE_PATH),
                "--repo",
                str(REPO),
                "--action-dir",
                str(action_dir),
                "--json-out",
                str(json_out),
                "--markdown-out",
                str(markdown_out),
                *arguments,
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8", errors="replace",
            timeout=120,
        )
        payload = json.loads(json_out.read_text(encoding="utf-8")) if json_out.is_file() else {}
        return result, payload

    def test_cli_require_complete_returns_three_for_required_not_evaluated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            action_dir = Path(directory) / "actions"
            action_dir.mkdir()
            result, payload = self.run_audit_cli(
                action_dir,
                "--require-complete",
                "--required-gate",
                "action_inventory",
            )

        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertFalse(payload["completion_policy"]["complete"])
        self.assertEqual(payload["completion_policy"]["non_pass_gates"], ["action_inventory"])

    def test_cli_strict_returns_two_for_malformed_action(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            action_dir = Path(directory) / "actions"
            action_dir.mkdir()
            (action_dir / "action_000900.json").write_text("{", encoding="utf-8")
            result, payload = self.run_audit_cli(action_dir, "--strict")

        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(payload["gates"]["action_inventory"]["status"], "FAIL")

    def test_cli_artifact_contains_exact_command_and_global_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            action_dir = Path(directory) / "actions"
            action_dir.mkdir()
            result, payload = self.run_audit_cli(action_dir)

        self.assertEqual(result.returncode, 0, result.stderr)
        for key in ("input_hashes", "command_version", "reasons", "sample_dimensions", "units", "downstream_consumers", "artifact_evidence", "invocation", "semantic_projection_sha256"):
            self.assertIn(key, payload)
        self.assertEqual(payload["command_version"]["command"], "scripts/audit_plant_fidelity.py")
        self.assertEqual(payload["command_version"]["sha256"], audit.sha256_file(MODULE_PATH))
        self.assertEqual(payload["semantic_projection_sha256"], audit.semantic_projection_sha256(payload))

    def test_completion_policy_rejects_not_evaluated_required_gate(self) -> None:
        gates = {
            "required": {"status": "NOT_EVALUATED", "reason": "missing"},
            "optional": {"status": "FAIL", "reason": "not selected"},
        }
        policy = audit.completion_policy(gates, ["required"])
        self.assertFalse(policy["complete"])
        self.assertEqual(policy["non_pass_gates"], ["required"])
        self.assertEqual(
            audit.audit_exit_code(
                {"fail": 0},
                policy,
                strict=False,
                require_complete=True,
            ),
            3,
        )

    def test_completion_policy_defaults_to_all_gates_and_rejects_unknown(self) -> None:
        gates = {
            "a": {"status": "PASS", "reason": "ok"},
            "b": {"status": "FAIL", "reason": "bad"},
        }
        policy = audit.completion_policy(gates)
        self.assertEqual(policy["required_gates"], ["a", "b"])
        self.assertEqual(
            audit.audit_exit_code(
                {"fail": 1},
                policy,
                strict=True,
                require_complete=False,
            ),
            2,
        )
        with self.assertRaisesRegex(ValueError, "unknown required gate"):
            audit.completion_policy(gates, ["missing"])

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

    def write_vissim_error_fixture(self, root: Path, *, present: bool, text: str = "") -> tuple[Path, Path]:
        name = "baseline"
        run_id = "run-1"
        network = root / "network.inpx"
        network.write_text("<network/>\n", encoding="utf-8")
        provenance = root / f"run_provenance_{name}.json"
        provenance.write_text(
            json.dumps({"name": name, "run_id": run_id, "files": {"network": {"path": str(network.resolve())}}}),
            encoding="utf-8",
        )
        checked = "2026-08-06T00:00:00+00:00"
        source = str(network.with_suffix(".err").resolve())
        binding = f"run_id={run_id}\nrun_name={name}\nattempt=1\npresent={str(present).lower()}\nsource_path={source}\npost_exit_checked_at_utc={checked}"
        artifact = None
        err_path = root / f"vissim_network_{name}.err"
        if present:
            Path(source).write_text(text, encoding="utf-8")
            err_path.write_text(text, encoding="utf-8")
            artifact = {"path": str(err_path.resolve()), "exists": True, "sha256": audit.sha256_file(err_path)}
        marker = root / f"vissim_error_evidence_{name}.json"
        marker.write_text(
            json.dumps(
                {
                    "schema_version": "vissim-error-evidence-v2.1",
                    "run_id": run_id,
                    "run_name": name,
                    "attempt": 1,
                    "process_exit_code": 0,
                    "source_path": source,
                    "post_exit_checked_at_utc": checked,
                    "source_checked_after_process_exit": True,
                    "present": present,
                    "artifact": artifact,
                    "stale_pre_run": [],
                    "binding_text": binding,
                    "binding_sha256": hashlib.sha256(binding.encode()).hexdigest(),
                }
            ),
            encoding="utf-8",
        )
        (root / f"wall_time_profile_{name}.json").write_text(
            json.dumps(
                {
                    "schema_version": "wall-time-profile-v2.1",
                    "status": "PASS",
                    "run_id": run_id,
                    "run_name": name,
                    "attempt": 1,
                    "process_exit_code": 0,
                    "elapsed_wall_sec": 1.0,
                }
            ),
            encoding="utf-8",
        )
        return marker, err_path

    def test_vissim_error_valid_absence_marker_is_clean_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_vissim_error_fixture(root, present=False)
            evidence = audit.vissim_error_directory_evidence(root)
        self.assertTrue(evidence["evidence_complete"])
        self.assertEqual(evidence["clean_absence_count"], 1)
        self.assertEqual(audit.vissim_error_gate(evidence)["status"], "PASS")

    def test_vissim_error_fatal_present_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_vissim_error_fixture(root, present=True, text="FATAL fixture\n")
            evidence = audit.vissim_error_directory_evidence(root)
        self.assertEqual(evidence["error_line_count"], 1)
        self.assertEqual(audit.vissim_error_gate(evidence)["status"], "FAIL")

    def test_vissim_error_nonfatal_present_source_and_artifact_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_vissim_error_fixture(root, present=True, text="informational line\n")
            evidence = audit.vissim_error_directory_evidence(root)
        self.assertEqual(evidence["marker_error_count"], 0)
        self.assertEqual(audit.vissim_error_gate(evidence)["status"], "PASS")

    def test_vissim_error_malformed_stale_and_mixed_markers_fail(self) -> None:
        for mutation in ("malformed", "stale", "mixed"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                marker, _ = self.write_vissim_error_fixture(root, present=False)
                if mutation == "malformed":
                    payload = json.loads(marker.read_text(encoding="utf-8")); payload["binding_sha256"] = "0" * 64; marker.write_text(json.dumps(payload), encoding="utf-8")
                elif mutation == "stale":
                    payload = json.loads(marker.read_text(encoding="utf-8")); payload["attempt"] = 2; payload["binding_text"] = payload["binding_text"].replace("attempt=1", "attempt=2"); payload["binding_sha256"] = hashlib.sha256(payload["binding_text"].encode()).hexdigest(); marker.write_text(json.dumps(payload), encoding="utf-8")
                else:
                    (root / "vissim_network_orphan.err").write_text("", encoding="utf-8")
                evidence = audit.vissim_error_directory_evidence(root)
                self.assertGreater(evidence["marker_error_count"], 0)
                self.assertEqual(audit.vissim_error_gate(evidence)["status"], "FAIL")

    def test_vissim_error_stale_pre_run_records_fail_closed(self) -> None:
        for mutation in ("malformed", "hash_mismatch", "fatal"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                marker, _ = self.write_vissim_error_fixture(root, present=False)
                payload = json.loads(marker.read_text(encoding="utf-8"))
                archive_root = Path(str(root.resolve()) + ".pre_run_err_archive")
                archive_root.mkdir()
                archive_path = archive_root / "attempt_01_baseline.err"
                archive_path.write_text("FATAL stale\n" if mutation == "fatal" else "stale\n", encoding="utf-8")
                if mutation == "malformed":
                    stale = {"attempt": "bad", "archived_path": ""}
                else:
                    stale = {
                        "attempt": 1,
                        "source_path": payload["source_path"],
                        "archived_path": str(archive_path.resolve()),
                        "sha256": "0" * 64 if mutation == "hash_mismatch" else audit.sha256_file(archive_path),
                        "archived_at_utc": "2026-08-06T00:00:00+00:00",
                    }
                payload["stale_pre_run"] = [stale]
                marker.write_text(json.dumps(payload), encoding="utf-8")
                evidence = audit.vissim_error_directory_evidence(root)
                self.assertGreater(evidence["marker_error_count"], 0)
                self.assertEqual(audit.vissim_error_gate(evidence)["status"], "FAIL")

    def test_vissim_error_absence_marker_fails_if_source_reappears(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker, _ = self.write_vissim_error_fixture(root, present=False)
            payload = json.loads(marker.read_text(encoding="utf-8"))
            Path(payload["source_path"]).write_text("late source\n", encoding="utf-8")
            evidence = audit.vissim_error_directory_evidence(root)
        self.assertGreater(evidence["marker_error_count"], 0)
        self.assertEqual(audit.vissim_error_gate(evidence)["status"], "FAIL")

    def test_vissim_error_present_marker_requires_current_source_hash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker, _ = self.write_vissim_error_fixture(root, present=True, text="clean\n")
            payload = json.loads(marker.read_text(encoding="utf-8"))
            Path(payload["source_path"]).write_text("changed after marker\n", encoding="utf-8")
            evidence = audit.vissim_error_directory_evidence(root)
        self.assertGreater(evidence["marker_error_count"], 0)
        self.assertEqual(audit.vissim_error_gate(evidence)["status"], "FAIL")

    def test_preflight_provenance_requires_one_current_shared_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            preflight = root / "preflight.json"
            preflight.write_text(
                json.dumps(
                    {
                        "schema_version": "preflight-v3",
                        "status": "PASS",
                        "reasons": [],
                        "fingerprint_sha256": "a" * 64,
                        "runtime_source_identity": {
                            "status": "PASS",
                            "strict": True,
                            "python": {
                                "path": sys.executable,
                                "sha256": audit.sha256_file(Path(sys.executable)),
                                "version": sys.version,
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            reference = {
                "path": str(preflight.resolve()),
                "exists": True,
                "sha256": audit.sha256_file(preflight),
            }
            for index in (1, 2):
                (root / f"run_provenance_case{index}.json").write_text(
                    json.dumps(
                        {
                            "run_id": f"run-{index}",
                            "preflight_manifest": reference,
                            "preflight_fingerprint_sha256": "a" * 64,
                            "python_executable": {
                                "path": sys.executable,
                                "exists": True,
                                "sha256": audit.sha256_file(Path(sys.executable)),
                                "version": sys.version,
                                "version_triplet": list(sys.version_info[:3]),
                            },
                        }
                    ),
                    encoding="utf-8",
                )

            contract = audit.preflight_provenance_evidence(root)
            self.assertEqual(
                audit.preflight_provenance_gate({"preflight_contract": contract})["status"],
                "PASS",
            )

            payload = json.loads((root / "run_provenance_case2.json").read_text(encoding="utf-8"))
            payload["preflight_fingerprint_sha256"] = "b" * 64
            (root / "run_provenance_case2.json").write_text(json.dumps(payload), encoding="utf-8")
            failed = audit.preflight_provenance_gate(
                {"preflight_contract": audit.preflight_provenance_evidence(root)}
            )
            self.assertEqual(failed["status"], "FAIL")

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

    def test_state_sidecars_are_not_discovered_as_states(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = prepare_provenance_assets(root)
            state_path, _ = write_runtime_record(
                root / "run-a",
                assets,
                suffix=1,
                input_count=6,
                represented=6,
            )
            for sidecar_suffix in audit.STATE_SIDECAR_SUFFIXES:
                state_path.with_name(state_path.stem + sidecar_suffix).write_text(
                    json.dumps({"status": "PASS"}),
                    encoding="utf-8",
                )
            result = audit.action_directory_evidence(root)
            states = audit.state_evidence([Path(path) for path in result["state_files"]])
        self.assertEqual(result["state_file_count"], 1)
        self.assertEqual(states["missing_link_counts_count"], 0)
        states["action_dir_discovered_count"] = 1
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


def write_json(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


TIMING_CANON = {
    "schema_version": "signal-group-timing-v3",
    "status": "PASS",
    "controllers": [
        {"sc_no": 1, "cycle_sec": 160.0, "groups": [{"sg_id": "1"}, {"sg_id": "2"}]},
        {"sc_no": 5, "cycle_sec": 140.0, "groups": [{"sg_id": "1"}]},
    ],
    "unresolved": [],
    "conflicting_pairs": [{"sc_no": 1, "a": "WBL", "b": "EBT", "actually_overlaps": False}],
}

ACTUATION_PLAN = {
    "schema_version": "signal-group-actuation-plan-v3",
    "status": "PASS",
    "source": {"network_sha256": "n" * 64},
    "controllers": {"1": {"node_id": "SC1"}, "5": {"node_id": "SC5"}},
    "timing_table_disagreements": [],
    "counts": {
        "controllers": 2,
        "signal_groups": 3,
        "planned_windows": 3,
        "uncovered_signal_groups": 0,
        "conflict_pairs": 4,
        "conflict_violations": 0,
    },
}

MOVEMENT_MAP = {
    "schema_version": "movement-signal-group-map-v3",
    "status": "PASS",
    "controllers": {"SC1": {}, "SC5": {}},
    "counts": {"resolved_movements": 416, "unresolved_movements": 282},
    "unresolved_movements": {"SC1_W_to_E": "synthetic_boundary_leg"},
}

PARENT_RUNS = {
    "schema_version": "parent-run-spec-v3",
    "spec": {
        "holdout": {"demand": [0.75, 1.0, 1.25], "seeds": [47]},
        "congested": {"demand": [1.25], "seeds": [13, 29]},
        "training": {"demand": [0.75, 1.0], "seeds": [13, 29]},
    },
}


def holdout_cell(demand: float, **overrides: str) -> dict[str, object]:
    gates = {
        "paired_dynamics": "PASS",
        "spillback_detection": "PASS",
        "gradient_ranking": "PASS",
        "mass_conservation": "PASS",
        "runtime": "PASS",
    }
    gates.update(overrides)
    return {"demand": demand, "seed": 47, "gates": gates}


class N10StatusVocabularyTest(unittest.TestCase):
    def test_blocked_is_a_distinct_status_worse_than_not_evaluated(self) -> None:
        self.assertEqual(audit.STATUS_BLOCKED, "BLOCKED")
        self.assertEqual(
            audit.worst_status(["PASS", "NOT_EVALUATED", "BLOCKED"]), "BLOCKED"
        )
        self.assertEqual(
            audit.worst_status(["PASS", "BLOCKED", "FAIL", "NOT_EVALUATED"]), "FAIL"
        )
        self.assertEqual(audit.worst_status(["PASS", "PASS"]), "PASS")
        self.assertEqual(audit.worst_status([]), "NOT_EVALUATED")

    def test_strict_run_exits_two_when_a_gate_is_blocked(self) -> None:
        policy = {"complete": False, "non_pass_gates": ["spillback_detection"]}
        summary = {"fail": 0, "blocked": 1}
        self.assertEqual(
            audit.audit_exit_code(summary, policy, strict=True, require_complete=False),
            2,
        )
        self.assertEqual(
            audit.audit_exit_code(
                {"fail": 0, "blocked": 0}, policy, strict=True, require_complete=False
            ),
            0,
        )

    def test_every_gate_is_classified_into_an_n10_category(self) -> None:
        gates = audit.build_gates(
            {
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
        )
        unclassified = sorted(set(gates) - set(audit.GATE_CATEGORIES))
        self.assertEqual(unclassified, [])
        self.assertEqual(
            sorted(set(audit.GATE_CATEGORIES.values())),
            [
                "calibration",
                "mass",
                "paired_dynamics",
                "projection",
                "promotion",
                "ranking",
                "runtime",
                "signal",
                "topology",
            ],
        )


class N10SignalAndTopologyGateTest(unittest.TestCase):
    def test_canonical_topology_must_be_compiled_from_the_audited_network(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = {
                "schema_version": "vissim-strict-topology/v1",
                "topology_hash": "a" * 64,
                "source": {"inpx_sha256": "b" * 64},
                "validation_report": {"valid": True, "error_count": 0},
                "links": [{"id": "link:1"}],
                "cells": [{"id": "cell:1"}],
            }
            matched = audit.canonical_topology_evidence(
                write_json(root / "topology.json", payload)
            )
            self.assertTrue(matched["available"])
            self.assertEqual(
                audit.canonical_topology_gate(matched, {"sha256": "b" * 64})["status"],
                "PASS",
            )
            drifted = audit.canonical_topology_gate(matched, {"sha256": "c" * 64})
            self.assertEqual(drifted["status"], "FAIL")
            self.assertIn("different", drifted["reason"])

            broken = dict(payload, validation_report={"valid": False, "error_count": 2})
            self.assertEqual(
                audit.canonical_topology_gate(
                    audit.canonical_topology_evidence(
                        write_json(root / "broken.json", broken)
                    ),
                    {"sha256": "b" * 64},
                )["status"],
                "FAIL",
            )

            self.assertEqual(
                audit.canonical_topology_gate(
                    audit.canonical_topology_evidence(None), {"sha256": "b" * 64}
                )["status"],
                "NOT_EVALUATED",
            )

    def test_signal_timing_canon_fails_when_the_plan_disagrees_with_the_table(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            timing = audit.signal_timing_evidence(
                write_json(root / "timing.json", TIMING_CANON)
            )
            agreeing = audit.actuation_plan_evidence(
                write_json(root / "plan.json", ACTUATION_PLAN)
            )
            self.assertEqual(
                audit.signal_timing_canon_gate(timing, agreeing)["status"], "PASS"
            )

            disagreeing_payload = dict(
                ACTUATION_PLAN, timing_table_disagreements=["SC5", "SC6", "SC11", "SC12"]
            )
            disagreeing = audit.actuation_plan_evidence(
                write_json(root / "plan_bad.json", disagreeing_payload)
            )
            verdict = audit.signal_timing_canon_gate(timing, disagreeing)
            self.assertEqual(verdict["status"], "FAIL")
            self.assertIn("SC5", json.dumps(verdict))

            overlapping = dict(
                TIMING_CANON,
                conflicting_pairs=[{"sc_no": 1, "actually_overlaps": True}],
            )
            self.assertEqual(
                audit.signal_timing_canon_gate(
                    audit.signal_timing_evidence(
                        write_json(root / "timing_overlap.json", overlapping)
                    ),
                    agreeing,
                )["status"],
                "FAIL",
            )

            # 대조 산출물이 없으면 통과가 아니라 미평가다. 적게 낼수록 유리해지면 안 된다.
            self.assertEqual(
                audit.signal_timing_canon_gate(
                    timing, audit.actuation_plan_evidence(None)
                )["status"],
                "NOT_EVALUATED",
            )
            self.assertEqual(
                audit.signal_timing_canon_gate(
                    audit.signal_timing_evidence(None), agreeing
                )["status"],
                "NOT_EVALUATED",
            )

    def test_actuation_plan_gate_checks_violations_network_and_controller_set(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            timing = audit.signal_timing_evidence(
                write_json(root / "timing.json", TIMING_CANON)
            )
            plan = audit.actuation_plan_evidence(
                write_json(root / "plan.json", ACTUATION_PLAN)
            )
            network = {"sha256": "n" * 64}
            self.assertEqual(
                audit.signal_actuation_plan_gate(plan, timing, network)["status"], "PASS"
            )

            violated = dict(
                ACTUATION_PLAN,
                status="FAIL",
                counts=dict(ACTUATION_PLAN["counts"], conflict_violations=3),
            )
            self.assertEqual(
                audit.signal_actuation_plan_gate(
                    audit.actuation_plan_evidence(
                        write_json(root / "violated.json", violated)
                    ),
                    timing,
                    network,
                )["status"],
                "FAIL",
            )

            other_network = audit.signal_actuation_plan_gate(
                plan, timing, {"sha256": "z" * 64}
            )
            self.assertEqual(other_network["status"], "FAIL")

            partial = dict(ACTUATION_PLAN, controllers={"1": {"node_id": "SC1"}})
            self.assertEqual(
                audit.signal_actuation_plan_gate(
                    audit.actuation_plan_evidence(
                        write_json(root / "partial.json", partial)
                    ),
                    timing,
                    network,
                )["status"],
                "FAIL",
            )

    def test_movement_map_gate_rejects_unknown_unresolved_reasons(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            timing = audit.signal_timing_evidence(
                write_json(root / "timing.json", TIMING_CANON)
            )
            good = audit.movement_map_evidence(
                write_json(root / "map.json", MOVEMENT_MAP)
            )
            self.assertEqual(
                audit.movement_signal_group_map_gate(good, timing)["status"], "PASS"
            )

            unknown = dict(
                MOVEMENT_MAP,
                unresolved_movements={"SC1_W_to_E": "no_signal_group_found"},
            )
            verdict = audit.movement_signal_group_map_gate(
                audit.movement_map_evidence(write_json(root / "bad.json", unknown)),
                timing,
            )
            self.assertEqual(verdict["status"], "FAIL")
            self.assertIn("no_signal_group_found", json.dumps(verdict))

            mismatched = dict(MOVEMENT_MAP, controllers={"SC1": {}})
            self.assertEqual(
                audit.movement_signal_group_map_gate(
                    audit.movement_map_evidence(
                        write_json(root / "mismatch.json", mismatched)
                    ),
                    timing,
                )["status"],
                "FAIL",
            )


class N10MassAndCalibrationGateTest(unittest.TestCase):
    def _projection_record(self, **errors: float) -> dict[str, object]:
        record = {
            "missing_required_fields": [],
            "input_mass_balance_error_veh": 0.0,
            "total_mass_balance_error_veh": 0.0,
            "residual_consistency_error_veh": 0.0,
            "status": "PASS",
        }
        record.update(errors)
        return record

    def test_mass_conservation_is_its_own_gate(self) -> None:
        empty = audit.mass_conservation_gate({"projection_contract": {"records": []}})
        self.assertEqual(empty["status"], "NOT_EVALUATED")

        clean = audit.mass_conservation_gate(
            {"projection_contract": {"records": [self._projection_record()]}}
        )
        self.assertEqual(clean["status"], "PASS")

        broken = audit.mass_conservation_gate(
            {
                "projection_contract": {
                    "records": [
                        self._projection_record(),
                        self._projection_record(total_mass_balance_error_veh=4.0),
                    ]
                }
            }
        )
        self.assertEqual(broken["status"], "FAIL")
        self.assertEqual(broken["evidence"]["violating_record_count"], 1)

        blind = audit.mass_conservation_gate(
            {
                "projection_contract": {
                    "records": [
                        self._projection_record(),
                        {"missing_required_fields": ["mass_balance_error_veh"]},
                    ]
                }
            }
        )
        self.assertEqual(blind["status"], "FAIL")

    def test_stock_calibration_gate_delegates_to_the_n6_validator(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(
                audit.stock_calibration_gate(audit.stock_calibration_evidence(None))[
                    "status"
                ],
                "NOT_EVALUATED",
            )

            payload = {
                "split": {
                    "training_run_ids": ["a"],
                    "holdout_run_ids": ["b"],
                    "fit_source": "training",
                },
                "jam_density": {
                    "sample_count": 400,
                    "saturated_lane_groups": 40,
                    "value_veh_km_lane": 130.0,
                    "ci95_low": 125.0,
                    "ci95_high": 135.0,
                    "selection": {"speed_max_kph": 3.0, "stopped_fraction_min": 0.5},
                },
                "geometry_prior": {"jam_spacing_m": 7.5, "fitted_jam_spacing_m": 7.7},
                "per_training_seed_fit": {"13": 130.0, "29": 132.0},
                "fallback_fraction_used": 0.02,
                "queue_tail_source": "observed",
            }
            good = audit.stock_calibration_evidence(
                write_json(root / "calibration.json", payload)
            )
            self.assertEqual(good["verdict"]["status"], "PASS")
            self.assertEqual(audit.stock_calibration_gate(good)["status"], "PASS")

            thin = dict(payload, jam_density=dict(payload["jam_density"], sample_count=10))
            bad = audit.stock_calibration_evidence(
                write_json(root / "thin.json", thin)
            )
            verdict = audit.stock_calibration_gate(bad)
            self.assertEqual(verdict["status"], "FAIL")
            self.assertIn("jam_density.sample_count", json.dumps(verdict))


class N10PairedRankingAndPromotionGateTest(unittest.TestCase):
    def paired(self, root: Path, name: str, payload: dict[str, object]) -> dict[str, object]:
        return audit.paired_validation_evidence(write_json(root / name, payload))

    def test_paired_dynamics_gate_uses_the_n9_gate_table(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(
                audit.paired_dynamics_gate(audit.paired_validation_evidence(None))[
                    "status"
                ],
                "NOT_EVALUATED",
            )
            passing = self.paired(
                root,
                "ok.json",
                {"horizons": {"1": {"ttt_ape": 0.05, "speed_mape": 0.05}}},
            )
            self.assertEqual(audit.paired_dynamics_gate(passing)["status"], "PASS")

            failing = self.paired(
                root,
                "bad.json",
                {"horizons": {"1": {"ttt_ape": 0.30}}},
            )
            verdict = audit.paired_dynamics_gate(failing)
            self.assertEqual(verdict["status"], "FAIL")
            self.assertIn("ttt_ape", json.dumps(verdict))

            unmeasured = self.paired(root, "none.json", {"horizons": {}})
            self.assertEqual(audit.paired_dynamics_gate(unmeasured)["status"], "NOT_EVALUATED")

    def test_spillback_gate_blocks_congested_cells_with_too_few_positives(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            good_cell = {
                "cell_id": "d125-h5-controlled-urban",
                "congested": True,
                "positives": 12,
                "f1": 0.85,
                "onset_median_error_sec": 40.0,
                "onset_p90_error_sec": 100.0,
            }
            passing = self.paired(root, "sb_ok.json", {"spillback": {"cells": [good_cell]}})
            self.assertEqual(audit.spillback_gate(passing)["status"], "PASS")

            blocked = self.paired(
                root,
                "sb_blocked.json",
                {"spillback": {"cells": [dict(good_cell, positives=4)]}},
            )
            self.assertEqual(audit.spillback_gate(blocked)["status"], "BLOCKED")

            exempt = self.paired(
                root,
                "sb_exempt.json",
                {
                    "spillback": {
                        "cells": [dict(good_cell, congested=False, positives=2)]
                    }
                },
            )
            self.assertEqual(audit.spillback_gate(exempt)["status"], "NOT_EVALUATED")

            late = self.paired(
                root,
                "sb_late.json",
                {"spillback": {"cells": [dict(good_cell, onset_p90_error_sec=180.0)]}},
            )
            self.assertEqual(audit.spillback_gate(late)["status"], "FAIL")

    def test_gradient_ranking_needs_point_and_bootstrap_lower_bound(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(
                audit.gradient_ranking_gate(audit.ranking_evidence(None))["status"],
                "NOT_EVALUATED",
            )
            good = audit.ranking_evidence(
                write_json(
                    root / "rank_ok.json",
                    {
                        "spearman": {"point": 0.82, "ci95_low": 0.74},
                        "top_pairwise": {"point": 0.91, "ci95_low": 0.83},
                    },
                )
            )
            self.assertEqual(audit.gradient_ranking_gate(good)["status"], "PASS")

            # 점추정만 통과하고 부트스트랩 하한이 미달이면 실패다.
            weak = audit.ranking_evidence(
                write_json(
                    root / "rank_weak.json",
                    {
                        "spearman": {"point": 0.82, "ci95_low": 0.61},
                        "top_pairwise": {"point": 0.91, "ci95_low": 0.83},
                    },
                )
            )
            verdict = audit.gradient_ranking_gate(weak)
            self.assertEqual(verdict["status"], "FAIL")
            self.assertIn("ci95_low", json.dumps(verdict))

            partial = audit.ranking_evidence(
                write_json(
                    root / "rank_partial.json",
                    {"spearman": {"point": 0.82, "ci95_low": 0.74}},
                )
            )
            self.assertEqual(audit.gradient_ranking_gate(partial)["status"], "NOT_EVALUATED")

    def test_promotion_requires_all_three_holdout_demands(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            parents = audit.parent_runs_evidence(
                write_json(root / "parents.json", PARENT_RUNS)
            )
            self.assertEqual(parents["holdout_demands"], [0.75, 1.0, 1.25])
            clean_gates = {"network_xml": {"status": "PASS", "reason": "ok"}}

            complete = audit.promotion_evidence(
                write_json(
                    root / "promo.json",
                    {"cells": [holdout_cell(d) for d in (0.75, 1.0, 1.25)]},
                )
            )
            self.assertEqual(
                audit.promotion_gate(complete, parents, clean_gates)["status"], "PASS"
            )

            missing_demand = audit.promotion_evidence(
                write_json(
                    root / "promo_partial.json",
                    {"cells": [holdout_cell(d) for d in (0.75, 1.0)]},
                )
            )
            verdict = audit.promotion_gate(missing_demand, parents, clean_gates)
            self.assertEqual(verdict["status"], "NOT_EVALUATED")
            self.assertIn("1.25", json.dumps(verdict))

            self.assertEqual(
                audit.promotion_gate(
                    complete, parents, {"network_xml": {"status": "FAIL", "reason": "x"}}
                )["status"],
                "FAIL",
            )
            self.assertEqual(
                audit.promotion_gate(audit.promotion_evidence(None), parents, clean_gates)[
                    "status"
                ],
                "NOT_EVALUATED",
            )

    def test_low_demand_is_exempt_only_from_spillback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            parents = audit.parent_runs_evidence(
                write_json(root / "parents.json", PARENT_RUNS)
            )
            clean_gates = {"network_xml": {"status": "PASS", "reason": "ok"}}

            spillback_exempt = audit.promotion_evidence(
                write_json(
                    root / "exempt.json",
                    {
                        "cells": [
                            holdout_cell(0.75, spillback_detection="NOT_EVALUATED"),
                            holdout_cell(1.0, spillback_detection="NOT_EVALUATED"),
                            holdout_cell(1.25),
                        ]
                    },
                )
            )
            self.assertEqual(
                audit.promotion_gate(spillback_exempt, parents, clean_gates)["status"],
                "PASS",
            )

            # 저수요라고 spillback 외 지표를 면제하지 않는다.
            other_unmeasured = audit.promotion_evidence(
                write_json(
                    root / "not_exempt.json",
                    {
                        "cells": [
                            holdout_cell(0.75, gradient_ranking="NOT_EVALUATED"),
                            holdout_cell(1.0),
                            holdout_cell(1.25),
                        ]
                    },
                )
            )
            verdict = audit.promotion_gate(other_unmeasured, parents, clean_gates)
            self.assertEqual(verdict["status"], "NOT_EVALUATED")
            self.assertIn("gradient_ranking", json.dumps(verdict))

            # 혼잡 셀의 spillback 면제는 없다.
            congested_unmeasured = audit.promotion_evidence(
                write_json(
                    root / "congested.json",
                    {
                        "cells": [
                            holdout_cell(0.75),
                            holdout_cell(1.0),
                            holdout_cell(1.25, spillback_detection="NOT_EVALUATED"),
                        ]
                    },
                )
            )
            self.assertEqual(
                audit.promotion_gate(congested_unmeasured, parents, clean_gates)["status"],
                "NOT_EVALUATED",
            )

            blocked = audit.promotion_evidence(
                write_json(
                    root / "blocked.json",
                    {
                        "cells": [
                            holdout_cell(0.75),
                            holdout_cell(1.0),
                            holdout_cell(1.25, spillback_detection="BLOCKED"),
                        ]
                    },
                )
            )
            self.assertEqual(
                audit.promotion_gate(blocked, parents, clean_gates)["status"], "BLOCKED"
            )


class N10AuditCommandTest(unittest.TestCase):
    def run_audit(self, directory: Path, *arguments: str) -> tuple[subprocess.CompletedProcess[str], dict]:
        json_out = directory / "audit.json"
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                str(MODULE_PATH),
                "--repo",
                str(REPO),
                "--json-out",
                str(json_out),
                "--markdown-out",
                str(directory / "audit.md"),
                *arguments,
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )
        payload = json.loads(json_out.read_text(encoding="utf-8")) if json_out.is_file() else {}
        return result, payload

    def test_new_gates_default_to_not_evaluated_and_are_replayable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result, payload = self.run_audit(Path(directory))
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in (
            "canonical_topology",
            "signal_timing_canon",
            "signal_actuation_plan",
            "movement_signal_group_map",
            "mass_conservation",
            "stock_calibration",
            "paired_dynamics",
            "spillback_detection",
            "gradient_ranking",
        ):
            self.assertIn(name, payload["gates"])
            self.assertEqual(payload["gates"][name]["status"], "NOT_EVALUATED", name)
        # 승격은 감사 자신의 게이트를 물려받는다. 지금 저장소에는 assignment_ties FAIL 이 있다.
        promotion = payload["gates"]["promotion_readiness"]
        self.assertEqual(promotion["status"], "FAIL")
        self.assertEqual(promotion["evidence"]["static_gate_status"], "FAIL")
        self.assertIn("the audit's own gates are FAIL", promotion["reason"])
        self.assertIn("blocked", payload["gate_summary"])
        self.assertIn("BLOCKED", payload["policy"]["status_values"])
        # 콘솔 한 줄이 BLOCKED 를 빼면 새 상태가 관측 구멍이 된다. BLOCKED 는
        # NOT_EVALUATED 보다 나쁜데(아직 안 쟀다가 아니라 잴 수 없다) 요약에서 사라진다.
        line = audit.format_gate_summary(
            {"overall": "FAIL", "pass": 11, "fail": 2, "blocked": 3, "not_evaluated": 12}
        )
        self.assertIn("BLOCKED=3", line)
        self.assertIn("FAIL=2", line)
        self.assertIn("NOT_EVALUATED=12", line)
        for field in (
            "canonical_topology",
            "signal_timing",
            "movement_map",
            "actuation_plan",
            "parent_runs",
            "stock_calibration",
            "paired_metrics",
            "ranking_evidence",
            "promotion_evidence",
        ):
            self.assertIn(field, payload["invocation"])
        rebuilt, _ = audit.build_complete_manifest_from_invocation(payload["invocation"])
        self.assertEqual(
            audit.canonical_semantic_projection(rebuilt),
            audit.canonical_semantic_projection(payload),
        )

    def test_blocked_spillback_reaches_the_summary_and_the_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paired = write_json(
                root / "paired.json",
                {
                    "spillback": {
                        "cells": [
                            {
                                "cell_id": "d125-h5-controlled-urban",
                                "congested": True,
                                "positives": 3,
                                "f1": 0.9,
                                "onset_median_error_sec": 20.0,
                                "onset_p90_error_sec": 50.0,
                            }
                        ]
                    }
                },
            )
            result, payload = self.run_audit(
                root,
                "--paired-metrics",
                str(paired),
                "--strict",
                "--required-gate",
                "spillback_detection",
            )
        self.assertEqual(payload["gates"]["spillback_detection"]["status"], "BLOCKED")
        self.assertEqual(payload["gate_summary"]["blocked"], 1)
        self.assertEqual(result.returncode, 2, result.stderr)

    def test_repository_signal_artifacts_are_actually_wired(self) -> None:
        outputs = REPO / "outputs"
        with tempfile.TemporaryDirectory() as directory:
            _, payload = self.run_audit(
                Path(directory),
                "--canonical-topology",
                str(outputs / "canonical_topology_v3.json"),
                "--signal-timing",
                str(outputs / "signal_group_timing_v3.json"),
                "--movement-map",
                str(outputs / "movement_signal_group_map_v3.json"),
                "--actuation-plan",
                str(outputs / "signal_group_actuation_plan_v3.json"),
                "--parent-runs",
                str(outputs / "parent_runs_v3.json"),
            )
        gates = payload["gates"]
        self.assertEqual(gates["canonical_topology"]["status"], "PASS")
        self.assertEqual(gates["signal_actuation_plan"]["status"], "PASS")
        self.assertEqual(gates["movement_signal_group_map"]["status"], "PASS")
        # 정본 표가 파일명 번호로 `.sig` 를 고르던 동안 SC5/6/11/12 가 어긋나 FAIL 이었다.
        # 표가 inpx supplyFile2 를 읽게 된 뒤로 PASS 이고, 불일치 목록은 비어 있어야 한다.
        self.assertEqual(gates["signal_timing_canon"]["status"], "PASS")
        # SG 수를 박아 둔다. 파일명 매칭으로 되돌아가면 128 이 되어 여기서 걸린다.
        self.assertEqual(gates["signal_timing_canon"]["evidence"]["signal_group_count"], 136)

    def test_markdown_carries_the_gate_category_column(self) -> None:
        manifest = {
            "generated_at_utc": "2026-08-09T00:00:00+00:00",
            "gates": {"promotion_readiness": {"status": "NOT_EVALUATED", "reason": "no runs"}},
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
        self.assertIn("| Gate | Category | Status | Reason |", markdown)
        self.assertIn("promotion", markdown)


if __name__ == "__main__":
    unittest.main()
