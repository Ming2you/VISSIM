from __future__ import annotations

import csv
import copy
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "validate_baseline_snapshot.py"
SPEC = importlib.util.spec_from_file_location("validate_baseline_snapshot", SCRIPT)
assert SPEC and SPEC.loader
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)

REPO = SCRIPT.parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


verifier = load_module("verify_runtime_source_fixture", SCRIPT.with_name("verify_runtime_source.py"))
preflight_builder = load_module("build_preflight_manifest_fixture", SCRIPT.with_name("build_preflight_manifest.py"))
auditor = load_module("audit_plant_fidelity_fixture", SCRIPT.with_name("audit_plant_fidelity.py"))
SOURCE_ROOT = (REPO / "vendor" / "NumSim-mine").resolve()
SOURCE_IDENTITY = verifier.inspect_source_root(SOURCE_ROOT)


class BaselineFixture:
    name = "fixed_nocontrol_nominal_d1p00_seed13"
    run_id = "0123456789abcdef0123456789abcdef"
    signals = [f"SC{i}" for i in range(1, 16)]
    ramps = ["R_D_W", "R_F_W", "R_D_E", "R_F_E"]

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace
        self.root = workspace / "baseline"
        self.evidence_dir = workspace / "evidence"
        self.network_dir = self.evidence_dir / "network"
        self.root.mkdir()
        self.evidence_dir.mkdir()
        self.network_dir.mkdir()
        self.decision_dir = self.root / f"decisions_{self.name}"
        self.decision_dir.mkdir(parents=True)
        self.provenance_path = self.root / f"run_provenance_{self.name}.json"
        self.runlog_path = self.root / f"runlog_{self.name}.txt"
        self.runtime_source_path = self.evidence_dir / "runtime-source.json"
        self.preflight_path = self.evidence_dir / "preflight.json"
        self.audit_path = self.evidence_dir / "audit.json"
        self.python_path = Path(sys.executable).resolve()
        self.write_complete()

    @staticmethod
    def sha(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    @staticmethod
    def write_json(path: Path, payload: object) -> None:
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @staticmethod
    def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

    @staticmethod
    def evidence(path: Path) -> dict[str, object]:
        return {
            "path": str(path.resolve()),
            "exists": path.is_file(),
            "size_bytes": path.stat().st_size if path.is_file() else None,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "",
            "last_write_time_utc": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat() if path.is_file() else "",
        }

    def runtime_imports(self) -> dict[str, object]:
        modules: dict[str, dict[str, str]] = {}
        for module_name in validator.EXPECTED_RUNTIME_IMPORTS:
            relative = Path(*module_name.split("."))
            candidate = SOURCE_ROOT / relative
            module_path = candidate / "__init__.py" if candidate.is_dir() else candidate.with_suffix(".py")
            data = module_path.read_bytes()
            normalised = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
            modules[module_name] = {
                "path": str(module_path.resolve()),
                "relative_path": module_path.relative_to(SOURCE_ROOT).as_posix(),
                "checkout_sha256": hashlib.sha256(data).hexdigest(),
                "normalised_sha256": hashlib.sha256(normalised).hexdigest(),
            }
        return {
            "ok": True,
            "returncode": 0,
            "stdout": "",
            "stderr": "",
            "adapter_default_root": str(SOURCE_ROOT),
            "adapter_path": str((REPO / "evaluation" / "controllers" / "vissim_stackelberg_adapter.py").resolve()),
            "modules": modules,
            "external_modules": [],
        }

    def copy_network_inputs(self) -> Path:
        source_dir = REPO / "network" / "real_world_gaepo_modi"
        network_path = self.network_dir / "modi_eval_rw_control.inpx"
        shutil.copy2(source_dir / network_path.name, network_path)
        for signal_path in source_dir.glob("*.sig"):
            shutil.copy2(signal_path, self.network_dir / signal_path.name)
        self.network_path = network_path.resolve()
        return network_path

    def write_manifests(self) -> tuple[dict[str, object], list[dict[str, object]]]:
        python_hash = self.sha(self.python_path)
        anchor_path = SOURCE_ROOT / "UPSTREAM_TREE.json"
        anchor = json.loads(anchor_path.read_text(encoding="utf-8"))
        imports = self.runtime_imports()
        runtime = {
            "schema_version": "runtime-source-v2.1",
            "status": "PASS",
            "strict": True,
            "reasons": [],
            "input_hashes": {
                "gitattributes_sha256": validator._sha256_file(REPO / ".gitattributes"),
                "upstream_tree_anchor_sha256": self.sha(anchor_path),
                "upstream_tree_anchor_semantic_sha256": validator.EXPECTED_ANCHOR_SEMANTIC_SHA256,
                "adapter_sha256": self.sha(REPO / "evaluation" / "controllers" / "vissim_stackelberg_adapter.py"),
                "canonical_snapshot_sha256": SOURCE_IDENTITY["snapshot_checkout_sha256"],
                "canonical_python_tree_normalised_sha256": SOURCE_IDENTITY["normalised_tree_sha256"],
                "selected_snapshot_sha256": SOURCE_IDENTITY["snapshot_checkout_sha256"],
                "selected_python_tree_normalised_sha256": SOURCE_IDENTITY["normalised_tree_sha256"],
                "python_executable_sha256": python_hash,
            },
            "command_version": {
                "command": "scripts/verify_runtime_source.py",
                "version": "runtime-source-v2.1",
                "sha256": self.sha(SCRIPT.with_name("verify_runtime_source.py")),
            },
            "expected_snapshot_commit": validator.EXPECTED_NUMSIM_COMMIT,
            "trust_anchor": {
                "path": str(anchor_path.resolve()),
                "checkout_sha256": self.sha(anchor_path),
                "semantic_sha256": validator.EXPECTED_ANCHOR_SEMANTIC_SHA256,
                "schema_version": anchor["schema_version"],
                "upstream_repository": anchor["upstream_repository"],
                "commit": anchor["commit"],
                "root_tree": anchor["root_tree"],
                "src_tree": anchor["src_tree"],
                "object_format": anchor["object_format"],
                "python_file_count": anchor["python_file_count"],
            },
            "selected_is_canonical": True,
            "python": {"executable": str(self.python_path), "rw_python_exe": str(self.python_path), "executable_sha256": python_hash, "version": sys.version},
            "canonical": copy.deepcopy(SOURCE_IDENTITY),
            "selected": copy.deepcopy(SOURCE_IDENTITY),
            "imports": {"canonical": copy.deepcopy(imports), "selected": copy.deepcopy(imports)},
            "checks": [
                {"id": identifier, "status": "PASS", "expected": True, "actual": True}
                for identifier in validator.RUNTIME_REQUIRED_CHECK_IDS
            ],
        }
        self.write_json(self.runtime_source_path, runtime)
        network_path = self.copy_network_inputs()
        assignment_path = self.evidence_dir / "link_assignment.json"
        self.write_json(
            assignment_path,
            {
                "link_owner": {},
                "freeway_bound_links": {},
                "monitor_only_exit_links": [],
                "urban_link_count": 0,
            },
        )
        post_run_producer = self.evidence_dir / "build_run_artifact_manifest_v2_2.py"
        live_replay_builder = self.evidence_dir / "build_projection_live_evidence_v2_2.py"
        post_run_producer.write_text("# synthetic fixture source\n", encoding="utf-8")
        live_replay_builder.write_text("# synthetic fixture source\n", encoding="utf-8")
        preflight = preflight_builder.build_manifest(
            REPO,
            self.runtime_source_path,
            path_overrides={
                "network": network_path,
                "link_assignment": assignment_path,
                "post_run_artifact_producer": post_run_producer,
                "live_replay_builder": live_replay_builder,
            },
            signal_dir=self.network_dir,
            python_executable=self.python_path,
        )
        self.assert_preflight_pass(preflight)
        self.write_json(self.preflight_path, preflight)
        artifacts = preflight["artifacts"]
        signals = preflight["network"]["resolved_signal_programs"]
        return artifacts, signals

    @staticmethod
    def assert_preflight_pass(preflight: dict[str, object]) -> None:
        if preflight.get("status") != "PASS":
            failed = [item["id"] for item in preflight.get("checks", []) if item.get("status") != "PASS"]
            raise AssertionError(f"fixture preflight is not complete PASS: {failed}")

    def state_payload(self, sim_sec: int) -> dict[str, object]:
        return {
            "sim_sec": sim_sec,
            "sim_period_sec": 3600,
            "control_interval_sec": 60,
            "network_path": str(self.network_path),
            "total_vehicles": 0,
            "urban_vehicles": 0,
            "boundary_vehicles": 0,
            "stopped_vehicles": 0,
            "local_observation": {
                "schema_version": 2,
                "mode": "real_world_connector_local_v2",
                "scan_ok": True,
                "observed_vehicle_count": 0,
                "unobservable_vehicle_count": 0,
                "link_counts": {"1": 0},
                "link_speeds_kph": {"1": 0.0},
                "link_stopped_counts": {"1": 0},
            },
            "run_provenance": {
                "run_id": self.run_id,
                "manifest_path": str(self.provenance_path.resolve()),
            },
        }

    def action_payload(self, sim_sec: int) -> dict[str, object]:
        model = self.contract["model"]
        signals = model["signals"]
        green = {f"{signal}_{phase}": model["phase_green_sec"] for signal in signals for phase in ("p1", "p2")}
        state_path = self.decision_dir / f"state_{sim_sec:06d}.json"
        imported_modules: dict[str, dict[str, str]] = {}
        for module_name in auditor.CORE_RUNTIME_MODULES:
            relative = Path(*module_name.split("."))
            candidate = SOURCE_ROOT / relative
            module_path = candidate / "__init__.py" if candidate.is_dir() else candidate.with_suffix(".py")
            imported_modules[module_name] = {"path": str(module_path.resolve()), "sha256": self.sha(module_path)}
        runtime_inputs = {
            "state_json": {"path": str(state_path.resolve()), "sha256": self.sha(state_path)},
            "network_inpx": {"path": str(self.network_path), "sha256": self.sha(self.network_path)},
            "run_manifest_json": {"path": str(self.provenance_path.resolve()), "sha256": self.sha(self.provenance_path)},
        }
        return {
            "N_P_star": 0.0,
            "N_UF_star": 0.0,
            "ramp_metering": model["ramp_capacity_vph"],
            "vsl": {link: model["vsl_kph"] for link in model["freeway_links"]},
            "green_times": green,
            "offsets": {signal: 0.0 for signal in signals},
            "inflow_outflow_allocation": {},
            "diagnostics": {"no_control_active": 1.0},
            "metadata": {"controller": "NoControl", "controller_variant": "no-control", "controller_status": "ok", "sim_sec": sim_sec, "decision_wall_sec": 0.1},
            "projection_diagnostics": {
                "total_vehicle_count_veh": 0,
                "input_link_vehicle_count_veh": 0,
                "represented_vehicle_count_veh": 0,
                "exit_excluded_vehicle_count_veh": 0,
                "unobservable_vehicle_count_veh": 0,
                "unrepresented_vehicle_count_veh": 0,
                "mass_balance_error_veh": 0,
                "storage_capacity_clipped_veh": 0,
            },
            "run_provenance": {
                "run_id": self.run_id,
                "workspace_root": str(REPO.resolve()),
                "workspace_git_commit": "synthetic-fixture",
                "numsim_repo_root": str(SOURCE_ROOT),
                "numsim_src_sha256": auditor._numsim_python_tree_sha256(SOURCE_ROOT),
                "imported_modules": imported_modules,
                "signal_program_sha256": {
                    path.name: self.sha(path)
                    for path in sorted(self.network_dir.glob("*.sig"), key=lambda item: item.name)
                },
                "inputs": runtime_inputs,
            },
        }

    def physical_rows(self) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for expected in self.contract["physical_vsl_rows"].values():
            rows.append({"kind": "vsl", **expected, "metadata": "fixture"})
        for ramp_id, expected in self.contract["physical_ramp_rows"].items():
            rows.append({
                "kind": "ramp_meter",
                "id": ramp_id,
                "sc_no": expected["sc_no"],
                "rate_vph": expected["rate_vph"],
                "green_sec": expected["green_sec"],
                "metadata": f"fixture;model_ramp_key={expected['model_ramp_key']}",
            })
        return rows

    def write_complete(self) -> None:
        artifacts, signals = self.write_manifests()
        preserved = self.root / f"generated_vbs_config_{self.name}.vbs"
        preserved.write_bytes(Path(str(artifacts["generated_vbs"]["path"])).read_bytes())
        preflight_hash = self.sha(self.preflight_path)
        preflight = json.loads(self.preflight_path.read_text(encoding="utf-8"))
        provenance = {
            "schema_version": 1,
            "run_id": self.run_id,
            "name": self.name,
            "seed": 13,
            "sim_period_sec": 3600,
            "control_interval_sec": 60,
            "control_start_sec": 900,
            "warmup_controller": "no-control",
            "state_log_interval_sec": 5,
            "demand_scale": 1.0,
            "demand_profile": "",
            "controller": "no-control",
            "audit_anchors_sec": "900,1500,2100,2700",
            "python_executable": {"path": str(self.python_path), "exists": True, "sha256": self.sha(self.python_path), "version": sys.version, "version_triplet": list(sys.version_info[:3])},
            "preflight_manifest": {"path": str(self.preflight_path.resolve()), "exists": True, "sha256": preflight_hash},
            "preflight_fingerprint_sha256": preflight["fingerprint_sha256"],
            "files": {
                "network": artifacts["network"], "tuning": artifacts["tuning"], "calibration": artifacts["calibration"], "control_mapping": artifacts["control_mapping"], "adapter": artifacts["adapter"], "main_vbs_runner": artifacts["runner"], "watchdog_wrapper": artifacts["watchdog"], "generated_vbs_config": artifacts["generated_vbs"],
                "preserved_generated_vbs_config": {"path": str(preserved.resolve()), "exists": True, "sha256": self.sha(preserved)},
                "numsim_default_yaml": self.evidence(SOURCE_ROOT / "src" / "config" / "default.yaml"),
            },
            "signal_programs": signals,
        }
        self.write_json(self.provenance_path, provenance)
        self.contract, contract_reasons = validator._derive_no_control_contract(provenance, preflight)
        if contract_reasons:
            raise AssertionError(f"fixture no-control contract failed: {contract_reasons}")
        self.runlog_path.write_text("\n".join([
            "RUN_MODE=CONTINUOUS_STATIC controller=no-control", f"PYTHON={self.python_path}", f"PYTHON_VERSION={sys.version}", "VERSION=2020.00 - 14 [95957]", "INCIDENT=DISABLED", "DEMAND=ORIGINAL_INPX_UNCHANGED", "WARMUP_CONTROLLER sim_sec=1 controller=no-control", "CONTROLLER_DECISION sim_sec=1 wall_sec=0.1 result=exit=0", "CONTROLLER_DECISION sim_sec=900 wall_sec=0.1 result=exit=0", "DECISIONS_OK=2", "DECISIONS_FAILED=0", "OBSERVATION_FAILURES=0", "SIGNAL_FAILURES=0", "ACTION_FORMAT_FAILURES=0", "COM_FAILURES=0", "STAGE=SIM_DONE", "SIM_SEC=3600",
        ]) + "\n", encoding="utf-8")
        (self.root / f"runlog_{self.name}.txt.err").write_text("", encoding="utf-8")
        state_rows = [
            {
                "sim_sec": sec,
                "total_vehicles": 0,
                "urban_vehicles": 0,
                "freeway_vehicles": 0,
                "ramp_vehicles": 0,
                "boundary_vehicles": 0,
                "other_vehicles": 0,
                "mean_speed_kph": 0.0,
                "freeway_mean_speed_kph": 0.0,
                "stopped_vehicles": 0,
                "controller_mode": "VISSIM_REAL_WORLD_NO-CONTROL",
                "controller_status": "ok",
                "decision_wall_sec": 0.1,
            }
            for sec in validator.EXPECTED_STATE_TIMES
        ]
        self.write_csv(self.root / f"state_{self.name}.csv", list(validator.STATE_CSV_HEADER), state_rows)
        action_header = ["kind", "id", "dsd_no", "sc_no", "link", "lane", "speed_kph", "major_green", "minor_green", "offset", "rate_vph", "green_sec", "metadata"]
        rows = self.physical_rows()
        cumulative: list[dict[str, object]] = []
        for sim_sec in (1, 900):
            suffix = f"{sim_sec:06d}"
            self.write_json(self.decision_dir / f"state_{suffix}.json", self.state_payload(sim_sec))
            self.write_json(self.decision_dir / f"action_{suffix}.json", self.action_payload(sim_sec))
            self.write_csv(self.decision_dir / f"action_{suffix}.csv", action_header, rows)
            cumulative.extend({
                "sim_sec": sim_sec,
                **row,
                "readback": "5|5" if row["kind"] == "vsl" else "GREEN",
            } for row in rows)
        cumulative_header = ["sim_sec", *action_header, "readback"]
        self.write_csv(self.root / f"action_{self.name}.csv", cumulative_header, cumulative)
        for sim_sec in (900, 1500, 2100, 2700):
            self.write_json(self.decision_dir / f"anchor_{sim_sec:06d}.json", self.state_payload(sim_sec))
        self.write_csv(self.decision_dir / "signal_readback.csv", ["sim_sec", "sc_no", "sg_no", "requested_state", "readback_state", "ok", "stage"], [])
        self.started = datetime.now(timezone.utc) - timedelta(seconds=10)
        self.finished = datetime.now(timezone.utc)
        self.write_json(self.root / f"wall_time_profile_{self.name}.json", {"schema_version": "wall-time-profile-v2.1", "status": "PASS", "run_id": self.run_id, "run_name": self.name, "attempt": 1, "process_exit_code": 0, "started_at_utc": self.started.isoformat(), "finished_at_utc": self.finished.isoformat(), "elapsed_wall_sec": (self.finished - self.started).total_seconds()})
        checked = self.finished.isoformat()
        source_path = str((Path(str(artifacts["network"]["path"]))).with_suffix(".err").resolve())
        binding = f"run_id={self.run_id}\nrun_name={self.name}\nattempt=1\npresent=false\nsource_path={source_path}\npost_exit_checked_at_utc={checked}"
        self.write_json(self.root / f"vissim_error_evidence_{self.name}.json", {"schema_version": "vissim-error-evidence-v2.1", "run_id": self.run_id, "run_name": self.name, "attempt": 1, "process_exit_code": 0, "source_path": source_path, "post_exit_checked_at_utc": checked, "source_checked_after_process_exit": True, "present": False, "artifact": None, "stale_pre_run": [], "binding_text": binding, "binding_sha256": hashlib.sha256(binding.encode()).hexdigest()})
        self.write_run_artifact_manifest()
        self.write_audit(preflight, preflight_hash)

    def write_run_artifact_manifest(self) -> None:
        output_paths = {
            "state_csv": self.root / f"state_{self.name}.csv",
            "cumulative_action_csv": self.root / f"action_{self.name}.csv",
            "stdout_runlog": self.runlog_path,
            "stderr_runlog": self.root / f"runlog_{self.name}.txt.err",
            "signal_readback_csv": self.decision_dir / "signal_readback.csv",
            "generated_vbs_config_copy": self.root / f"generated_vbs_config_{self.name}.vbs",
            "vissim_error_evidence": self.root / f"vissim_error_evidence_{self.name}.json",
            "wall_time_profile": self.root / f"wall_time_profile_{self.name}.json",
        }
        decision_paths = sorted(
            [
                *(self.decision_dir / f"state_{sec:06d}.json" for sec in validator.EXPECTED_DECISIONS),
                *(self.decision_dir / f"action_{sec:06d}.json" for sec in validator.EXPECTED_DECISIONS),
                *(self.decision_dir / f"action_{sec:06d}.csv" for sec in validator.EXPECTED_DECISIONS),
                *(self.decision_dir / f"anchor_{sec:06d}.json" for sec in validator.EXPECTED_ANCHORS),
            ],
            key=lambda path: path.name,
        )
        finalized = datetime.now(timezone.utc)
        self.write_json(
            self.root / f"run_artifact_manifest_{self.name}.json",
            {
                "schema_version": "run-artifact-manifest-v2.1",
                "status": "PASS",
                "run_id": self.run_id,
                "run_name": self.name,
                "attempt": 1,
                "process_exit_code": 0,
                "finalized_at_utc": finalized.isoformat(),
                "run_window": {
                    "started_at_utc": self.started.isoformat(),
                    "finished_at_utc": self.finished.isoformat(),
                    "filesystem_mtime_tolerance_sec": validator.FILESYSTEM_MTIME_TOLERANCE_SEC,
                },
                "artifact_roles": {
                    "simulation_output_keys": ["state_csv", "cumulative_action_csv", "stdout_runlog", "stderr_runlog", "signal_readback_csv"],
                    "post_exit_evidence_keys": ["vissim_error_evidence", "wall_time_profile"],
                    "pre_run_input_keys": ["generated_vbs_config_copy"],
                    "decision_artifacts": "simulation_output",
                },
                "run_provenance": self.evidence(self.provenance_path),
                "output_artifacts": {key: self.evidence(path) for key, path in output_paths.items()},
                "decision_artifacts": [self.evidence(path) for path in decision_paths],
            },
        )

    def write_audit(self, preflight: dict[str, object], preflight_hash: str) -> None:
        artifacts = preflight["artifacts"]
        arguments = [
            "--repo", str(REPO),
            "--network", str(artifacts["network"]["path"]),
            "--signal-dir", str(self.network_dir),
            "--signal-roles", str(artifacts["signal_roles"]["path"]),
            "--assignment", str(artifacts["link_assignment"]["path"]),
            "--adjacency", str(artifacts["adjacency"]["path"]),
            "--storage", str(artifacts["storage_capacity"]["path"]),
            "--tuning", str(artifacts["tuning"]["path"]),
            "--calibration", str(artifacts["calibration"]["path"]),
            "--control-mapping", str(artifacts["control_mapping"]["path"]),
            "--detector-mapping", str(artifacts["detector_mapping"]["path"]),
            "--vbs-config", str(artifacts["generated_vbs"]["path"]),
            "--adapter", str(artifacts["adapter"]["path"]),
            "--vendor-root", str(SOURCE_ROOT),
            "--numsim-root", str(SOURCE_ROOT),
            "--action-dir", str(self.root),
            "--strict",
            "--require-complete",
        ]
        for gate_name in validator.AUDIT_REQUIRED_GATES:
            arguments.extend(("--required-gate", gate_name))
        args = auditor.make_parser(REPO).parse_args(arguments)
        audit_payload, exit_code = auditor.build_complete_manifest(args)
        if exit_code != 0:
            failed = audit_payload["completion_policy"]["non_pass_gates"]
            raise AssertionError(f"fixture current auditor is not strict complete PASS: {failed}")
        self.write_json(self.audit_path, audit_payload)

    def refresh_certification_wrappers(self) -> None:
        preflight = json.loads(self.preflight_path.read_text(encoding="utf-8"))
        self.write_run_artifact_manifest()
        self.write_audit(preflight, self.sha(self.preflight_path))

    def validate(self) -> dict[str, object]:
        return validator.validate_snapshot(self.root, self.runtime_source_path, self.preflight_path, self.audit_path)


class ValidateBaselineSnapshotTests(unittest.TestCase):
    def make_fixture(self) -> tuple[tempfile.TemporaryDirectory[str], BaselineFixture]:
        temporary = tempfile.TemporaryDirectory()
        return temporary, BaselineFixture(Path(temporary.name))

    def test_complete_synthetic_baseline_passes(self) -> None:
        temporary, fixture = self.make_fixture(); self.addCleanup(temporary.cleanup)
        result = fixture.validate()
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["complete"])
        self.assertEqual(result["reasons"], [])
        self.assertEqual(result["sample_dimensions"]["state_csv_observations"], 721)
        expected_rows = 2 * (
            len(fixture.contract["physical_vsl_rows"])
            + len(fixture.contract["physical_ramp_rows"])
        )
        self.assertEqual(result["sample_dimensions"]["cumulative_action_rows"], expected_rows)

    def test_provenance_control_start_and_warmup_are_required(self) -> None:
        temporary, fixture = self.make_fixture(); self.addCleanup(temporary.cleanup)
        payload = json.loads(fixture.provenance_path.read_text(encoding="utf-8")); payload["control_start_sec"] = 840; payload["warmup_controller"] = "stackelberg"; fixture.write_json(fixture.provenance_path, payload)
        gate = fixture.validate()["checks"]["run_provenance"]
        self.assertEqual(gate["status"], "FAIL")
        self.assertIn("control_start_sec must be 900", gate["evidence"]["reasons"])

    def test_early_stop_and_com_failure_fail_runlog(self) -> None:
        temporary, fixture = self.make_fixture(); self.addCleanup(temporary.cleanup)
        text = fixture.runlog_path.read_text(encoding="utf-8").replace("STAGE=SIM_DONE\n", "").replace("SIM_SEC=3600", "SIM_SEC=300").replace("COM_FAILURES=0", "COM_FAILURES=1")
        fixture.runlog_path.write_text(text, encoding="utf-8")
        gate = fixture.validate()["checks"]["run_completion_and_failures"]
        self.assertEqual(gate["status"], "FAIL")
        self.assertIn("COM_FAILURES must be 0", gate["evidence"]["reasons"])

    def test_missing_anchor_is_not_complete(self) -> None:
        temporary, fixture = self.make_fixture(); self.addCleanup(temporary.cleanup)
        (fixture.decision_dir / "anchor_002100.json").unlink()
        result = fixture.validate()
        self.assertNotEqual(result["status"], "PASS")
        self.assertEqual(result["checks"]["state_action_anchor_contract"]["status"], "NOT_EVALUATED")

    def test_run_id_mismatch_fails_json_contract(self) -> None:
        temporary, fixture = self.make_fixture(); self.addCleanup(temporary.cleanup)
        path = fixture.decision_dir / "action_000900.json"; payload = json.loads(path.read_text(encoding="utf-8")); payload["run_provenance"]["run_id"] = "different"; fixture.write_json(path, payload)
        self.assertEqual(fixture.validate()["checks"]["state_action_anchor_contract"]["status"], "FAIL")

    def test_state_sidecars_do_not_break_inventory_or_audit_comparison(self) -> None:
        # sidecar 는 state 의 형제로 state_ 접두사를 물려받아 두 발견 경로에 모두 걸린다.
        # audit 만 거르고 여기서 안 거르면 :786 대조가 어긋나 FAIL 한다.
        temporary, fixture = self.make_fixture(); self.addCleanup(temporary.cleanup)
        state_path = fixture.decision_dir / "state_000900.json"
        self.assertTrue(state_path.is_file())
        for suffix in validator._current_auditor().STATE_SIDECAR_SUFFIXES:
            state_path.with_name(state_path.stem + suffix).write_text(
                '{"status": "PASS"}', encoding="utf-8"
            )
        # 실제 흐름에서는 감사와 baseline 검증이 같은 디렉터리 상태를 본다.
        # 감사 생성 이후에 파일을 넣으면 정확 재고 계약이 별개 이유로 FAIL 한다.
        fixture.refresh_certification_wrappers()
        result = fixture.validate()
        self.assertEqual(result["checks"]["state_action_anchor_contract"]["status"], "PASS")
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["reasons"], [])

    def test_stale_extra_anchor_fails_exact_inventory(self) -> None:
        temporary, fixture = self.make_fixture(); self.addCleanup(temporary.cleanup)
        fixture.write_json(fixture.decision_dir / "anchor_003000.json", fixture.state_payload(3000))
        gate = fixture.validate()["checks"]["state_action_anchor_contract"]
        self.assertEqual(gate["status"], "FAIL")
        self.assertEqual(len(gate["evidence"]["unexpected"]), 1)

    def test_non_noop_signal_vsl_and_ramp_payloads_fail(self) -> None:
        for mutation in ("signal_csv", "vsl_csv", "ramp_csv", "vsl_json", "ramp_json"):
            with self.subTest(mutation=mutation):
                temporary, fixture = self.make_fixture(); self.addCleanup(temporary.cleanup)
                csv_path = fixture.decision_dir / "action_000900.csv"
                header, rows, _ = validator._read_csv(csv_path)
                if mutation == "signal_csv":
                    rows.append({"kind": "signal", "id": "SC1", "sc_no": "1", "major_green": "90", "minor_green": "20", "offset": "0"})
                    fixture.write_csv(csv_path, header, rows)
                elif mutation == "vsl_csv":
                    rows[0]["speed_kph"] = "60"; fixture.write_csv(csv_path, header, rows)
                elif mutation == "ramp_csv":
                    ramp_row = next(row for row in rows if row["kind"] == "ramp_meter")
                    ramp_row["rate_vph"] = "500"; fixture.write_csv(csv_path, header, rows)
                else:
                    json_path = fixture.decision_dir / "action_000900.json"
                    payload = json.loads(json_path.read_text(encoding="utf-8"))
                    if mutation == "vsl_json": payload["vsl"]["FW_E"] = 60.0
                    else: payload["ramp_metering"]["R_D_E"] = 500.0
                    fixture.write_json(json_path, payload)
                self.assertEqual(fixture.validate()["checks"]["no_control_action_contract"]["status"], "FAIL")

    def test_cumulative_vsl_err_readback_fails(self) -> None:
        temporary, fixture = self.make_fixture(); self.addCleanup(temporary.cleanup)
        path = fixture.root / f"action_{fixture.name}.csv"
        header, rows, _ = validator._read_csv(path)
        row = next(item for item in rows if item["kind"] == "vsl")
        row["readback"] = "ERR:VSL readback mismatch"
        fixture.write_csv(path, header, rows)
        gate = fixture.validate()["checks"]["no_control_action_contract"]
        self.assertEqual(gate["status"], "FAIL")
        self.assertTrue(any("VSL readback" in reason for reason in gate["evidence"]["reasons"]))

    def test_state_csv_requires_exact_13_columns_and_typed_rows(self) -> None:
        temporary, fixture = self.make_fixture(); self.addCleanup(temporary.cleanup)
        path = fixture.root / f"state_{fixture.name}.csv"
        fixture.write_csv(path, ["sim_sec", "total_vehicles"], [{"sim_sec": sec, "total_vehicles": 0} for sec in validator.EXPECTED_STATE_TIMES])
        self.assertEqual(fixture.validate()["checks"]["state_csv_contract"]["status"], "FAIL")

        temporary2, fixture2 = self.make_fixture(); self.addCleanup(temporary2.cleanup)
        path2 = fixture2.root / f"state_{fixture2.name}.csv"
        header, rows, _ = validator._read_csv(path2)
        rows[0]["mean_speed_kph"] = "nan"
        rows[0]["decision_wall_sec"] = "-1"
        fixture2.write_csv(path2, header, rows)
        self.assertEqual(fixture2.validate()["checks"]["state_csv_contract"]["status"], "FAIL")

    def test_fatal_err_is_never_clean(self) -> None:
        temporary, fixture = self.make_fixture(); self.addCleanup(temporary.cleanup)
        err_path = fixture.root / f"vissim_network_{fixture.name}.err"; err_path.write_text("FATAL fixture\n", encoding="utf-8")
        marker_path = fixture.root / f"vissim_error_evidence_{fixture.name}.json"; marker = json.loads(marker_path.read_text(encoding="utf-8")); marker["present"] = True; marker["artifact"] = {"path": str(err_path.resolve()), "exists": True, "sha256": fixture.sha(err_path)}; marker["binding_text"] = marker["binding_text"].replace("present=false", "present=true"); marker["binding_sha256"] = hashlib.sha256(marker["binding_text"].encode()).hexdigest(); fixture.write_json(marker_path, marker)
        self.assertEqual(fixture.validate()["checks"]["vissim_error_evidence"]["status"], "FAIL")

    def test_wrong_preflight_hash_and_audit_failure_fail_chain(self) -> None:
        temporary, fixture = self.make_fixture(); self.addCleanup(temporary.cleanup)
        audit = json.loads(fixture.audit_path.read_text(encoding="utf-8")); audit["status"] = "FAIL"; audit["gate_summary"]["strict_complete_status"] = "FAIL"; fixture.write_json(fixture.audit_path, audit)
        preflight = json.loads(fixture.preflight_path.read_text(encoding="utf-8")); preflight["reasons"] = ["tampered"]; fixture.write_json(fixture.preflight_path, preflight)
        self.assertEqual(fixture.validate()["checks"]["source_preflight_audit_contract"]["status"], "FAIL")

    def test_self_declared_or_fabricated_source_chain_never_passes(self) -> None:
        for mutation in ("runtime_command", "runtime_checks", "preflight_command", "preflight_checks", "skeletal_audit"):
            with self.subTest(mutation=mutation):
                temporary, fixture = self.make_fixture(); self.addCleanup(temporary.cleanup)
                if mutation.startswith("runtime"):
                    payload = json.loads(fixture.runtime_source_path.read_text(encoding="utf-8"))
                    if mutation == "runtime_command":
                        payload["command_version"]["sha256"] = "a" * 64
                    else:
                        payload["checks"] = []
                    fixture.write_json(fixture.runtime_source_path, payload)
                elif mutation.startswith("preflight"):
                    payload = json.loads(fixture.preflight_path.read_text(encoding="utf-8"))
                    if mutation == "preflight_command":
                        payload["command_version"]["sha256"] = "a" * 64
                    else:
                        payload["checks"] = []
                    fingerprint = hashlib.sha256(
                        json.dumps(
                            validator._preflight_fingerprint_payload(payload),
                            ensure_ascii=True,
                            sort_keys=True,
                            separators=(",", ":"),
                        ).encode("utf-8")
                    ).hexdigest()
                    payload["fingerprint"]["sha256"] = fingerprint
                    payload["fingerprint_sha256"] = fingerprint
                    fixture.write_json(fixture.preflight_path, payload)
                else:
                    fixture.write_json(fixture.audit_path, {
                        "schema_version": 2,
                        "status": "PASS",
                        "strict": True,
                        "require_complete": True,
                        "reasons": [],
                        "action_directory": {"path": str(fixture.root.resolve())},
                        "gate_summary": {"pass": 2, "fail": 0, "not_evaluated": 0, "overall": "PASS", "strict_complete_status": "PASS"},
                        "completion_policy": {"required_gates": list(validator.AUDIT_REQUIRED_GATES), "required_gate_count": len(validator.AUDIT_REQUIRED_GATES), "non_pass_gates": [], "complete": True},
                        "gates": {name: {"status": "PASS"} for name in validator.AUDIT_REQUIRED_GATES},
                    })
                gate = fixture.validate()["checks"]["source_preflight_audit_contract"]
                self.assertEqual(gate["status"], "FAIL")

    def test_audit_replay_rejects_status_only_gates_and_empty_evidence(self) -> None:
        for mutation in ("status_only_gates", "empty_global_evidence"):
            with self.subTest(mutation=mutation):
                temporary, fixture = self.make_fixture(); self.addCleanup(temporary.cleanup)
                payload = json.loads(fixture.audit_path.read_text(encoding="utf-8"))
                if mutation == "status_only_gates":
                    payload["gates"] = {
                        name: {"status": gate["status"], "reason": gate["reason"]}
                        for name, gate in payload["gates"].items()
                    }
                else:
                    payload["sample_dimensions"] = {}
                    payload["units"] = {}
                    payload["downstream_consumers"] = []
                    payload["artifact_evidence"] = {}
                payload["semantic_projection_sha256"] = auditor.semantic_projection_sha256(payload)
                fixture.write_json(fixture.audit_path, payload)
                gate = fixture.validate()["checks"]["source_preflight_audit_contract"]
                self.assertEqual(gate["status"], "FAIL")
                self.assertTrue(any("current auditor replay" in reason for reason in gate["evidence"]["reasons"]))

    def test_run_artifact_manifest_proves_csv_freshness(self) -> None:
        temporary, fixture = self.make_fixture(); self.addCleanup(temporary.cleanup)
        path = fixture.root / f"state_{fixture.name}.csv"
        header, rows, _ = validator._read_csv(path)
        rows[0]["mean_speed_kph"] = "1.0"
        fixture.write_csv(path, header, rows)
        self.assertEqual(fixture.validate()["checks"]["run_artifact_manifest"]["status"], "FAIL")

    def test_stale_state_csv_fails_even_after_manifest_and_audit_rewrap(self) -> None:
        temporary, fixture = self.make_fixture(); self.addCleanup(temporary.cleanup)
        path = fixture.root / f"state_{fixture.name}.csv"
        stale = datetime(2000, 1, 1, tzinfo=timezone.utc).timestamp()
        os.utime(path, (stale, stale))
        fixture.refresh_certification_wrappers()
        gate = fixture.validate()["checks"]["run_artifact_manifest"]
        self.assertEqual(gate["status"], "FAIL")
        self.assertTrue(any("simulation window: state_csv" in reason for reason in gate["evidence"]["reasons"]))

    def test_stale_decision_json_fails_even_after_manifest_and_audit_rewrap(self) -> None:
        temporary, fixture = self.make_fixture(); self.addCleanup(temporary.cleanup)
        path = fixture.decision_dir / "action_000900.json"
        stale = datetime(2000, 1, 1, tzinfo=timezone.utc).timestamp()
        os.utime(path, (stale, stale))
        fixture.refresh_certification_wrappers()
        gate = fixture.validate()["checks"]["run_artifact_manifest"]
        self.assertEqual(gate["status"], "FAIL")
        self.assertTrue(any("decision artifact predates" in reason for reason in gate["evidence"]["reasons"]))

    def test_stale_error_records_and_recreated_source_fail_closed(self) -> None:
        for mutation in ("malformed", "hash_mismatch", "fatal_archive", "source_recreated"):
            with self.subTest(mutation=mutation):
                temporary, fixture = self.make_fixture(); self.addCleanup(temporary.cleanup)
                marker_path = fixture.root / f"vissim_error_evidence_{fixture.name}.json"
                marker = json.loads(marker_path.read_text(encoding="utf-8"))
                if mutation == "source_recreated":
                    Path(marker["source_path"]).write_text("late error file\n", encoding="utf-8")
                else:
                    archive_root = Path(str(fixture.root.resolve()) + ".pre_run_err_archive")
                    archive_root.mkdir()
                    archive_path = archive_root / f"attempt_01_{fixture.name}.err"
                    archive_path.write_text("FATAL stale fixture\n" if mutation == "fatal_archive" else "stale fixture\n", encoding="utf-8")
                    if mutation == "malformed":
                        stale = {"attempt": "one", "archived_path": ""}
                    else:
                        stale = {
                            "attempt": 1,
                            "source_path": marker["source_path"],
                            "archived_path": str(archive_path.resolve()),
                            "sha256": "0" * 64 if mutation == "hash_mismatch" else fixture.sha(archive_path),
                            "archived_at_utc": datetime.now(timezone.utc).isoformat(),
                        }
                    marker["stale_pre_run"] = [stale]
                    fixture.write_json(marker_path, marker)
                gate = fixture.validate()["checks"]["vissim_error_evidence"]
                self.assertEqual(gate["status"], "FAIL")

    def test_fake_python_or_wrong_version_cannot_pass(self) -> None:
        temporary, fixture = self.make_fixture(); self.addCleanup(temporary.cleanup)
        fake = fixture.root / "python.exe"; fake.write_bytes(b"fake Python bytes")
        provenance = json.loads(fixture.provenance_path.read_text(encoding="utf-8")); provenance["python_executable"]["path"] = str(fake); provenance["python_executable"]["sha256"] = fixture.sha(fake); provenance["python_executable"]["version"] = "9.9.9"; provenance["python_executable"]["version_triplet"] = [9, 9, 9]; fixture.write_json(fixture.provenance_path, provenance)
        gate = fixture.validate()["checks"]["python_runtime_identity"]
        self.assertEqual(gate["status"], "FAIL")

        temporary2, fixture2 = self.make_fixture(); self.addCleanup(temporary2.cleanup)
        text = fixture2.runlog_path.read_text(encoding="utf-8").replace(f"PYTHON_VERSION={sys.version}", "PYTHON_VERSION=Python 3.99.0")
        fixture2.runlog_path.write_text(text, encoding="utf-8")
        self.assertEqual(fixture2.validate()["checks"]["python_runtime_identity"]["status"], "FAIL")

    def test_state_csv_must_have_canonical_timing_through_3600(self) -> None:
        temporary, fixture = self.make_fixture(); self.addCleanup(temporary.cleanup)
        path = fixture.root / f"state_{fixture.name}.csv"
        lines = path.read_text(encoding="utf-8").splitlines()
        path.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")
        self.assertEqual(fixture.validate()["checks"]["state_csv_contract"]["status"], "FAIL")

    def test_strict_require_complete_exit_and_atomic_output(self) -> None:
        temporary, fixture = self.make_fixture(); self.addCleanup(temporary.cleanup)
        output = fixture.root / "snapshot.json"
        code = validator.main([str(fixture.root), "--runtime-source", str(fixture.runtime_source_path), "--preflight", str(fixture.preflight_path), "--audit", str(fixture.audit_path), "--out", str(output), "--strict", "--require-complete"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["status"], "PASS")
        self.assertEqual(list(fixture.root.glob(".snapshot.json.*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
