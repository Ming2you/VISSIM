from __future__ import annotations

import copy
import base64
import csv
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
ADAPTER_PATH = ROOT / "evaluation/controllers/vissim_stackelberg_adapter.py"
MANIFEST_PATH = ROOT / "evaluation/strict_plant_20260731/canonical_topology.json"
MAPPING_PATH = (
    ROOT
    / "evaluation/real_world_modi_control_urban_follower_excel_20260731/control_mapping_urban_follower_excel_20260731.json"
)
VBS_PATH = ROOT / "scripts/run_real_world_stackelberg_controller.vbs"
WATCHDOG_PATH = ROOT / "scripts/run_real_world_single_watchdog_urban_follower_excel.ps1"
CANONICAL_ROOT = Path(os.environ.get("STRICT_NUMERICAL_SIM_REPO", r"C:\tmp\numerical-sim-strict-vissim"))


def load_adapter():
    spec = importlib.util.spec_from_file_location("vissim_stackelberg_adapter", ADAPTER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load adapter module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_shadow():
    root_text = str(CANONICAL_ROOT)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
    return importlib.import_module("src.vissim_strict.shadow")


class StrictActuationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.hmac_key = "phase5-test-operator-secret"
        os.environ["RW_ACTION_HMAC_KEY"] = cls.hmac_key
        cls.adapter = load_adapter()
        cls.shadow = load_shadow()
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        cls.mapping = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))

    def safe_two_phase_manifest(self):
        manifest = copy.deepcopy(self.manifest)
        schedules = {str(row["controller_no"]): row for row in manifest["schedules"]["fixed"]}
        for mapping_row in self.mapping["signals"]:
            schedule = schedules[str(mapping_row["sc_no"])]
            program = schedule["program"]
            cycle = float(program["cycle_length_sec"])
            p1_end = (cycle - 10.0) / 2.0
            p1 = [
                {"display_id": "3", "start_sec": 0.0, "end_sec": p1_end, "state": "GREEN", "source_kind": "command"},
                {"display_id": "4", "start_sec": p1_end, "end_sec": p1_end + 3.0, "state": "AMBER", "source_kind": "fixedstate"},
                {"display_id": "1", "start_sec": p1_end + 3.0, "end_sec": cycle, "state": "RED", "source_kind": "command"},
            ]
            p2_start = p1_end + 5.0
            p2 = [
                {"display_id": "1", "start_sec": 0.0, "end_sec": p2_start, "state": "RED", "source_kind": "command"},
                {"display_id": "3", "start_sec": p2_start, "end_sec": cycle - 5.0, "state": "GREEN", "source_kind": "command"},
                {"display_id": "4", "start_sec": cycle - 5.0, "end_sec": cycle - 2.0, "state": "AMBER", "source_kind": "fixedstate"},
                {"display_id": "1", "start_sec": cycle - 2.0, "end_sec": cycle, "state": "RED", "source_kind": "command"},
            ]
            phase_by_sg = {int(row["sg_no"]): row["phase"] for row in mapping_row["signal_groups"]}
            for sg_no, phase in phase_by_sg.items():
                program["sg_timelines"][str(sg_no)]["intervals"] = copy.deepcopy(p1 if phase == "p1" else p2)
        manifest["topology_hash"] = self.adapter.topology_hash_for_manifest(manifest)
        return manifest

    def write_canonical_evidence(self, directory: Path, manifest, controllers, approved_action_hash=None):
        program_hashes = sorted({row["native_program_sha256"] for row in controllers.values()})
        authority = {str(sc): list(row["authorized_sgs"]) for sc, row in controllers.items()}
        record_count = 42
        policy_hash = "7" * 64
        build_hash = "8" * 64
        action_schema_hash = "9" * 64
        actions = [hashlib.sha256(f"action-{index}".encode()).hexdigest() for index in range(record_count)]
        if approved_action_hash is not None:
            actions[0] = approved_action_hash
        shadow_records = []
        for index, action_hash in enumerate(actions):
            decision = index // 2
            candidate = index % 2
            stale_probe = index == 0
            fallback_probe = index == 2
            readback_probe = index == 4
            shadow_records.append({
                "schema_version": self.shadow.RECORD_SCHEMA_VERSION,
                "decision_id": f"d{decision:02d}", "candidate_id": f"c{candidate}",
                "strict_predicted_objective": float(candidate), "vissim_observed_objective": float(candidate),
                "strict_status": "OK", "strict_runtime_sec": 1.0,
                "strict_predicted_spillback": candidate == 0, "vissim_observed_spillback": candidate == 0,
                "fallback_required": fallback_probe, "fallback_event_logged": fallback_probe,
                "shadow_mode": True, "actuation_attempted": False,
                "stale_fault_injection_observed": stale_probe,
                "fallback_fault_injection_observed": fallback_probe,
                "readback_fault_injection_observed": readback_probe,
                "stale_action_detected": stale_probe, "stale_action_rejected": stale_probe,
                "stale_action_failure": False,
                "state_hash": "3" * 64, "based_on_state_hash": ("4" * 64 if stale_probe else "3" * 64),
                "readback_ok": True if readback_probe else None,
                "readback_action_hash": action_hash if readback_probe else None,
                "topology_hash": manifest["topology_hash"],
                "program_hash": program_hashes[index % len(program_hashes)], "action_hash": action_hash,
                "policy_hash": policy_hash, "build_hash": build_hash,
                "action_schema_hash": action_schema_hash,
            })
        g6 = self.shadow.evaluate_shadow_records(shadow_records)
        promoted_hash = actions[0]
        action_set_sha256 = self.adapter._canonical_mapping_digest({"action_hashes": [promoted_hash]})
        g8_rows = []
        for sc_no, sg_nos in authority.items():
            for sg_no in sg_nos:
                g8_rows.append({
                    "topology_hash": manifest["topology_hash"],
                    "program_hash": controllers[sc_no]["native_program_sha256"],
                    "action_hash": promoted_hash, "action_set_sha256": action_set_sha256,
                    "runtime_action_hash": "5" * 64,
                    "policy_hash": policy_hash, "build_hash": build_hash,
                    "action_schema_hash": action_schema_hash,
                    "runtime_action_hmac_sha256": "6" * 64,
                    "csv_payload_sha256": "a" * 64,
                    "envelope_hmac_sha256": "b" * 64,
                    "envelope_hmac_valid": True,
                    "row_contract_sha256": hashlib.sha256(f"row-{sc_no}-{sg_no}".encode()).hexdigest(),
                    "sc_no": sc_no, "sg_no": sg_no, "interval_id": "interval-1",
                    "evidence_kind": "sigstate", "requested_state": "GREEN", "state_readback": "GREEN",
                    "contr_by_com_requested": True, "contr_by_com_readback": True, "readback_ok": True,
                    "run_id": "run-1", "build_id": "build-1", "network_id": "network-1",
                    "seed": "13", "demand_identity": "demand-1",
                })
                g8_rows.append({
                    "topology_hash": manifest["topology_hash"],
                    "program_hash": controllers[sc_no]["native_program_sha256"],
                    "action_hash": promoted_hash, "action_set_sha256": action_set_sha256,
                    "runtime_action_hash": "5" * 64,
                    "policy_hash": policy_hash, "build_hash": build_hash,
                    "action_schema_hash": action_schema_hash,
                    "runtime_action_hmac_sha256": "6" * 64,
                    "csv_payload_sha256": "a" * 64,
                    "envelope_hmac_sha256": "b" * 64,
                    "envelope_hmac_valid": True,
                    "row_contract_sha256": hashlib.sha256(f"release-{sc_no}-{sg_no}".encode()).hexdigest(),
                    "sc_no": sc_no, "sg_no": sg_no, "interval_id": "release-1",
                    "evidence_kind": "native_release",
                    "parent_runtime_action_hash": "5" * 64,
                    "parent_action_interval_id": "interval-1",
                    "requested_state": "CONTRBYCOM:false", "state_readback": "CONTRBYCOM:false",
                    "contr_by_com_requested": False, "contr_by_com_readback": False, "readback_ok": True,
                    "run_id": "run-1", "build_id": "build-1", "network_id": "network-1",
                    "seed": "13", "demand_identity": "demand-1",
                })
        g8 = self.shadow.evaluate_com_readback_records(g8_rows, expected_authority=authority)
        specs = {}
        for name, report in (("g6", g6), ("g8", g8)):
            path = directory / f"{name}.json"
            path.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            specs[name] = {"path": str(path), "claimed_sha256": digest, "trusted_sha256": digest}
        return specs

    def test_shadow_is_valid_default_but_never_writes_signals(self) -> None:
        contract = self.adapter.build_strict_actuation_contract(
            self.manifest,
            self.mapping,
        )
        self.assertEqual(contract["requested_stage"], "shadow")
        self.assertEqual(contract["effective_stage"], "shadow")
        self.assertTrue(contract["contract_valid"])
        self.assertFalse(contract["signal_write_enabled"])
        self.assertFalse(contract["runtime_offset_enabled"])
        self.assertEqual(contract["topology_hash"], contract["computed_topology_hash"])
        self.assertEqual(set(contract["controllers"]), set(self.adapter.STRICT_UF_TO_SC.values()))
        self.assertTrue(all(row["native_epoch_sec"] == 0.0 for row in contract["controllers"].values()))
        self.assertTrue(all("native_switchpoint_sec" in row for row in contract["controllers"].values()))

    def test_authority_is_exactly_the_selected_fifteen_ufs_and_mapped_sgs(self) -> None:
        contract = self.adapter.build_strict_actuation_contract(self.manifest, self.mapping)
        self.assertEqual(
            {row["uf_id"] for row in contract["controllers"].values()},
            set(self.adapter.STRICT_UF_TO_SC),
        )
        mapping_by_sc = {str(row["sc_no"]): row for row in self.mapping["signals"]}
        for sc_no, row in contract["controllers"].items():
            self.assertEqual(
                row["authorized_sgs"],
                sorted(mapping_by_sc[sc_no]["signal_group_filter"]),
            )
            self.assertTrue(set(row["authorized_sgs"]).issubset(self.adapter.STRICT_MAIN_SGS))

    def test_hash_or_authority_tampering_fails_closed(self) -> None:
        manifest = copy.deepcopy(self.manifest)
        manifest["topology_hash"] = "0" * 64
        contract = self.adapter.build_strict_actuation_contract(manifest, self.mapping)
        self.assertFalse(contract["contract_valid"])
        self.assertFalse(contract["signal_write_enabled"])
        self.assertIn("TOPOLOGY_HASH_MISMATCH", contract["lock_reasons"])

        mapping = copy.deepcopy(self.mapping)
        mapping["controlled_urban_follower_ids"].append(19)
        contract = self.adapter.build_strict_actuation_contract(self.manifest, mapping)
        self.assertFalse(contract["contract_valid"])
        self.assertIn("MAPPING_CONTROLLED_UF_SET_MISMATCH", contract["lock_reasons"])

    def test_promoted_stages_remain_locked_and_offset_is_never_enabled(self) -> None:
        all_evidence = {
            "g3": True,
            "g6": True,
            "green_release": True,
            "offset_release": True,
            "midblock_release": True,
            "integrated_release": True,
        }
        green = self.adapter.build_strict_actuation_contract(
            self.manifest, self.mapping, "green-only", all_evidence
        )
        self.assertFalse(green["signal_write_enabled"])
        self.assertIn("MISSING_G6_EVIDENCE_PATH", green["lock_reasons"])
        self.assertIn("MISSING_G8_EVIDENCE_PATH", green["lock_reasons"])
        self.assertTrue(any(reason.startswith("UNSAFE_LEGACY_TWO_PHASE_WAVEFORM") for reason in green["lock_reasons"]))

        offset = self.adapter.build_strict_actuation_contract(
            self.manifest, self.mapping, "corridor-offset", all_evidence
        )
        self.assertFalse(offset["signal_write_enabled"])
        self.assertFalse(offset["runtime_offset_enabled"])
        self.assertIn("OFFSET_WRITES_DISABLED_IN_THIS_BUILD", offset["lock_reasons"])

        parent = self.adapter.build_strict_actuation_contract(
            self.manifest, self.mapping, "parent-midblock", all_evidence
        )
        integrated = self.adapter.build_strict_actuation_contract(
            self.manifest, self.mapping, "integrated", all_evidence
        )
        self.assertIn("PARENT_MIDBLOCK_COM_REPLAY_NOT_IMPLEMENTED", parent["lock_reasons"])
        self.assertIn("INTEGRATED_SIGNAL_COM_REPLAY_NOT_IMPLEMENTED", integrated["lock_reasons"])

    def test_green_release_requires_hashed_g6_and_g8_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            contract = self.adapter.build_strict_actuation_contract(self.manifest, self.mapping)
            specs = self.write_canonical_evidence(tmp_path, self.manifest, contract["controllers"])
            contract = self.adapter.build_strict_actuation_contract(
                self.manifest,
                self.mapping,
                "green-only",
                evidence_artifacts=specs,
            )
            self.assertTrue(contract["evidence_artifacts"]["g6"]["valid"])
            self.assertTrue(contract["evidence_artifacts"]["g8"]["valid"])
            self.assertFalse(any("EVIDENCE_" in reason for reason in contract["lock_reasons"]))
            self.assertFalse(contract["signal_write_enabled"], "native SG waveform remains independently locked")

            self_only = copy.deepcopy(specs)
            self_only["g8"].pop("trusted_sha256")
            self_only["g8"]["sha256"] = self_only["g8"]["claimed_sha256"]
            tampered = self.adapter.build_strict_actuation_contract(
                self.manifest,
                self.mapping,
                "green-only",
                evidence_artifacts=self_only,
            )
            self.assertIn("MISSING_OPERATOR_PINNED_G8_EVIDENCE_SHA256", tampered["lock_reasons"])

    def test_native_budget_normalization_preserves_cycle_budget(self) -> None:
        major, minor, status = self.adapter._normalize_two_phase_budget(90.0, 5.0, 144.0, 5.0, 5.0)
        self.assertAlmostEqual(major + minor, 144.0)
        self.assertGreaterEqual(major, 5.0)
        self.assertGreaterEqual(minor, 5.0)
        self.assertEqual(status, "normalized_to_native_effective_green_budget")

    def test_signal_csv_carries_native_provenance_and_is_fail_closed(self) -> None:
        contract = self.adapter.build_strict_actuation_contract(
            self.manifest,
            self.mapping,
            "green-only",
            {"green_release": True},
        )
        control = SimpleNamespace(
            green_times={
                key: 40.0
                for row in self.mapping["signals"]
                for key in (f"{row['id']}_p1", f"{row['id']}_p2")
            },
            offsets={row["id"]: 30.0 for row in self.mapping["signals"]},
        )
        cfg = SimpleNamespace(
            network=SimpleNamespace(lost_time=6.0),
            freeway_follower=SimpleNamespace(vsl_set=[60.0, 80.0, 100.0]),
        )
        mapping = dict(self.mapping)
        mapping["segments"] = []
        mapping["ramp_meters"] = []
        original = self.adapter.physical_ramp_actions
        self.adapter.physical_ramp_actions = lambda *args, **kwargs: {}
        try:
            with tempfile.TemporaryDirectory() as tmp:
                output = Path(tmp) / "action.csv"
                self.adapter.write_action_csv(
                    output,
                    control,
                    cfg,
                    mapping,
                    lambda *args: 80.0,
                    {"controller_status": "ok"},
                    {"real_world_signal_control": {"enabled": True}},
                    contract,
                )
                with output.open(encoding="utf-8-sig", newline="") as handle:
                    rows = list(csv.DictReader(handle))
        finally:
            self.adapter.physical_ramp_actions = original

        self.assertEqual(len(rows), len(self.adapter.STRICT_UF_TO_SC))
        for row in rows:
            self.assertEqual(row["actuation_stage"], "green-only")
            self.assertEqual(row["effective_stage"], "shadow")
            self.assertEqual(row["topology_hash"], self.manifest["topology_hash"])
            self.assertGreater(float(row["native_cycle_sec"]), 0.0)
            self.assertEqual(float(row["native_epoch_sec"]), 0.0)
            self.assertNotEqual(row["native_switchpoint_sec"], "")
            self.assertNotEqual(row["native_program_sha256"], "")
            self.assertEqual(row["offset"], "0.0")
            self.assertEqual(row["runtime_offset_enabled"], "0")
            self.assertEqual(row["signal_write_enabled"], "0")
            self.assertEqual(row["evidence_artifacts_valid"], "0")
            self.assertEqual(row["row_contract_sha256"], self.adapter.signal_row_contract_sha256(row))
            self.assertNotEqual(row["fail_reason"], "")

    def test_executable_preflight_rejects_semantic_tampering(self) -> None:
        manifest = self.safe_two_phase_manifest()
        base = self.adapter.build_strict_actuation_contract(manifest, self.mapping)
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            control = SimpleNamespace(
                green_times={
                    key: 40.0
                    for row in self.mapping["signals"]
                    for key in (f"{row['id']}_p1", f"{row['id']}_p2")
                },
                offsets={},
            )
            identity = self.adapter.build_strict_step_action_identity(
                control, self.mapping, base, {"sim_sec": 60.0}, 60.0
            )
            from src.vissim_strict.schema import StepAction
            canonical_action = StepAction(**identity["step_action_payload"])
            self.assertEqual(canonical_action.action_hash, identity["step_action_hash"])
            specs = self.write_canonical_evidence(
                tmp_path, manifest, base["controllers"]
            )
            g6_report = json.loads(Path(specs["g6"]["path"]).read_text(encoding="utf-8"))
            self.assertNotIn(identity["step_action_hash"], g6_report["provenance"]["action_hashes"])
            contract = self.adapter.build_strict_actuation_contract(
                manifest, self.mapping, "green-only", evidence_artifacts=specs
            )
            contract = self.adapter.bind_strict_action_identity(contract, identity)
            self.assertTrue(contract["signal_write_enabled"], contract["lock_reasons"])
            cfg = SimpleNamespace(
                network=SimpleNamespace(lost_time=10.0),
                freeway_follower=SimpleNamespace(vsl_set=[60.0, 80.0, 100.0]),
            )
            mapping = dict(self.mapping)
            mapping["segments"] = []
            mapping["ramp_meters"] = []
            output = tmp_path / "strict.csv"
            original_ramps = self.adapter.physical_ramp_actions
            self.adapter.physical_ramp_actions = lambda *args, **kwargs: {}
            try:
                self.adapter.write_action_csv(
                    output, control, cfg, mapping, lambda *args: 80.0,
                    {"controller_status": "ok"}, {"real_world_signal_control": {"enabled": True}}, contract,
                )
            finally:
                self.adapter.physical_ramp_actions = original_ramps
            trusted_g6 = specs["g6"]["trusted_sha256"]
            trusted_g8 = specs["g8"]["trusted_sha256"]
            accepted = self.adapter.verify_strict_action_csv(
                output, manifest, self.mapping, trusted_g6, trusted_g8, Path(specs["g6"]["path"]),
                trusted_g8_report_path=Path(specs["g8"]["path"]),
            )
            self.assertTrue(accepted["valid"], accepted["reasons"])

            state_path = tmp_path / "state.json"
            state_path.write_text(json.dumps({"sim_sec": 60.0}), encoding="utf-8")
            live = self.adapter.verify_strict_action_csv(
                output, manifest, self.mapping, trusted_g6, trusted_g8, Path(specs["g6"]["path"]),
                trusted_g8_report_path=Path(specs["g8"]["path"]), current_sim_sec=60.0,
                current_state_path=state_path, action_hmac_key=self.hmac_key,
            )
            self.assertTrue(live["valid"], live["reasons"])
            protocol = self.adapter.build_verified_action_protocol(output.read_bytes(), live, self.hmac_key)
            self.assertTrue(protocol.startswith(self.adapter.STRICT_ACTION_PROTOCOL_BEGIN))
            self.assertIn(self.adapter.STRICT_ACTION_CSV_BEGIN, protocol)
            self.assertIn(self.adapter.STRICT_ACTION_CSV_END, protocol)
            verified_protocol = self.adapter.verify_action_protocol_text(
                protocol, self.hmac_key, current_sim_sec=60.0,
                current_state_artifact_sha256=hashlib.sha256(state_path.read_bytes()).hexdigest(),
            )
            self.assertEqual(verified_protocol["headers"]["runtime_action_hash"], live["runtime_action_hash"])
            for tampered in (
                protocol.replace("major_green", "major_greeN", 1),
                protocol.replace("sim_sec=60.000000", "sim_sec=61.000000", 1),
                protocol.replace("envelope_hmac_sha256=", "envelope_hmac_sha256=0", 1),
                protocol.replace(live["current_state_hash"], "f" * 64, 1),
            ):
                with self.assertRaises(ValueError):
                    self.adapter.verify_action_protocol_text(
                        tampered, self.hmac_key, current_sim_sec=60.0,
                        current_state_artifact_sha256=hashlib.sha256(state_path.read_bytes()).hexdigest(),
                    )

            manifest_path = tmp_path / "safe-manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            cli = subprocess.run(
                [
                    sys.executable, "-B", str(ADAPTER_PATH),
                    "--verify-strict-action-csv", str(output),
                    "--emit-verified-action-protocol",
                    "--current-sim-sec", "60",
                    "--state-json", str(state_path),
                    "--repo-root", str(CANONICAL_ROOT),
                    "--mapping-json", str(MAPPING_PATH),
                    "--strict-topology-manifest", str(manifest_path),
                    "--trusted-g6-evidence-sha256", trusted_g6,
                    "--trusted-g8-evidence-sha256", trusted_g8,
                    "--trusted-g6-report-json", specs["g6"]["path"],
                    "--trusted-g8-report-json", specs["g8"]["path"],
                ],
                cwd=ROOT,
                env={**os.environ, "RW_ACTION_HMAC_KEY": self.hmac_key},
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(cli.returncode, 0, cli.stderr)
            self.assertTrue(cli.stdout.startswith(self.adapter.STRICT_ACTION_PROTOCOL_BEGIN))
            self.assertIn(self.adapter.STRICT_ACTION_PROTOCOL_END, cli.stdout)

            for sim_sec, expected_reason in (
                (61.0, "ACTION_INTERVAL_SIM_TICK_MISMATCH"),
                (59.0, "ACTION_DECISION_TIME_IN_FUTURE"),
                (120.0, "ACTION_OUTSIDE_VALIDITY_INTERVAL"),
            ):
                rejected = self.adapter.verify_strict_action_csv(
                    output, manifest, self.mapping, trusted_g6, trusted_g8, Path(specs["g6"]["path"]),
                    trusted_g8_report_path=Path(specs["g8"]["path"]), current_sim_sec=sim_sec,
                    current_state_path=state_path, action_hmac_key=self.hmac_key,
                )
                self.assertFalse(rejected["valid"])
                self.assertIn(expected_reason, rejected["reasons"])

            wrong_state = tmp_path / "wrong-state.json"
            wrong_state.write_text(json.dumps({"sim_sec": 60.0, "mutation": True}), encoding="utf-8")
            rejected = self.adapter.verify_strict_action_csv(
                output, manifest, self.mapping, trusted_g6, trusted_g8, Path(specs["g6"]["path"]),
                trusted_g8_report_path=Path(specs["g8"]["path"]), current_sim_sec=60.0,
                current_state_path=wrong_state, action_hmac_key=self.hmac_key,
            )
            self.assertIn("BASED_ON_STATE_HASH_MISMATCH", rejected["reasons"])

            rejected = self.adapter.verify_strict_action_csv(
                output, manifest, self.mapping, trusted_g6, trusted_g8, Path(specs["g6"]["path"]),
                trusted_g8_report_path=tmp_path / "deleted-g8.json", current_sim_sec=60.0,
                current_state_path=state_path, action_hmac_key=self.hmac_key,
            )
            self.assertTrue(any("G8_EVIDENCE" in reason for reason in rejected["reasons"]))

            g8_path = Path(specs["g8"]["path"])
            g8_bytes = g8_path.read_bytes()
            g8_path.write_text("{}", encoding="utf-8")
            try:
                replaced = self.adapter.verify_strict_action_csv(
                    output, manifest, self.mapping, trusted_g6, trusted_g8, Path(specs["g6"]["path"]),
                    trusted_g8_report_path=g8_path, current_sim_sec=60.0,
                    current_state_path=state_path, action_hmac_key=self.hmac_key,
                )
                self.assertIn("G8_EVIDENCE_SHA256_MISMATCH", replaced["reasons"])
            finally:
                g8_path.write_bytes(g8_bytes)

            g6_path = Path(specs["g6"]["path"])
            g6_bytes = g6_path.read_bytes()
            g6_path.write_text("{}", encoding="utf-8")
            try:
                replaced = self.adapter.verify_strict_action_csv(
                    output, manifest, self.mapping, trusted_g6, trusted_g8, g6_path,
                    trusted_g8_report_path=g8_path, current_sim_sec=60.0,
                    current_state_path=state_path, action_hmac_key=self.hmac_key,
                )
                self.assertIn("G6_EVIDENCE_SHA256_MISMATCH", replaced["reasons"])
            finally:
                g6_path.write_bytes(g6_bytes)

            missing_secret = self.adapter.verify_strict_action_csv(
                output, manifest, self.mapping, trusted_g6, trusted_g8, Path(specs["g6"]["path"]),
                trusted_g8_report_path=g8_path, current_sim_sec=60.0,
                current_state_path=state_path, action_hmac_key="",
            )
            self.assertIn("MISSING_RW_ACTION_HMAC_KEY", missing_secret["reasons"])

            sealed = tmp_path / "strict.validated.csv"
            preflight_result = tmp_path / "strict.preflight.json"
            sealed_result = self.adapter.seal_action_csv(
                output, sealed, preflight_result, manifest, self.mapping,
                trusted_g6, trusted_g8, Path(specs["g6"]["path"]),
                trusted_g8_report_path=Path(specs["g8"]["path"]),
            )
            self.assertTrue(sealed_result["valid"], sealed_result["reasons"])
            self.assertTrue(self.adapter._valid_sha256(sealed_result["runtime_action_hash"]))
            republished = self.adapter.seal_action_csv(
                output, sealed, preflight_result, manifest, self.mapping,
                trusted_g6, trusted_g8, Path(specs["g6"]["path"]),
                trusted_g8_report_path=Path(specs["g8"]["path"]),
            )
            self.assertTrue(republished["valid"], republished["reasons"])
            self.assertEqual(republished["runtime_action_hash"], sealed_result["runtime_action_hash"])
            sealed_bytes = sealed.read_bytes()
            output.write_bytes(b"tampered-after-preflight")
            self.assertEqual(sealed.read_bytes(), sealed_bytes)
            self.assertEqual(hashlib.sha256(sealed_bytes).hexdigest(), sealed_result["csv_content_sha256"])
            self.assertNotEqual(hashlib.sha256(output.read_bytes()).hexdigest(), sealed_result["csv_content_sha256"])

            with sealed.open(encoding="utf-8-sig", newline="") as handle:
                original_rows = list(csv.DictReader(handle))
                fields = list(original_rows[0])

            for field, value, expected_reason in (
                ("sg_phase_map", "2:p1", "SG_PHASE_MAP_MISMATCH"),
                ("native_program_offset_sec", "999", "NATIVE_PROGRAM_OFFSET_SEC_MISMATCH"),
                ("major_green", "1", "MAJOR_GREEN_OUT_OF_RANGE"),
            ):
                rows = copy.deepcopy(original_rows)
                rows[0][field] = value
                rows[0]["row_contract_sha256"] = self.adapter.signal_row_contract_sha256(rows[0])
                mutated = tmp_path / f"tampered_{field}.csv"
                with mutated.open("w", encoding="utf-8-sig", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=fields)
                    writer.writeheader()
                    writer.writerows(rows)
                result = self.adapter.verify_strict_action_csv(
                    mutated, manifest, self.mapping, trusted_g6, trusted_g8, Path(specs["g6"]["path"]),
                    trusted_g8_report_path=Path(specs["g8"]["path"]),
                )
                self.assertFalse(result["valid"])
                self.assertTrue(any(expected_reason in reason for reason in result["reasons"]), result["reasons"])

            rows = copy.deepcopy(original_rows)
            rows[0]["major_green"] = str(float(rows[0]["major_green"]) + 1.0)
            rows[0]["minor_green"] = str(float(rows[0]["minor_green"]) - 1.0)
            rows[0]["row_contract_sha256"] = self.adapter.signal_row_contract_sha256(rows[0])
            green_tamper = tmp_path / "tampered_green_budget_preserved.csv"
            with green_tamper.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
            result = self.adapter.verify_strict_action_csv(
                green_tamper, manifest, self.mapping, trusted_g6, trusted_g8, Path(specs["g6"]["path"]),
                trusted_g8_report_path=Path(specs["g8"]["path"]),
            )
            self.assertFalse(result["valid"])
            self.assertIn("RUNTIME_ACTION_HASH_MISMATCH", result["reasons"])

            rows = copy.deepcopy(original_rows)
            rows[0]["major_green"] = str(float(rows[0]["major_green"]) + 1.0)
            rows[0]["minor_green"] = str(float(rows[0]["minor_green"]) - 1.0)
            forged_runtime_hash = self.adapter.runtime_action_sha256(rows)
            for row in rows:
                row["runtime_action_hash"] = forged_runtime_hash
                if row.get("kind") == "signal":
                    row["row_contract_sha256"] = self.adapter.signal_row_contract_sha256(row)
            forged = tmp_path / "forged_without_hmac.csv"
            with forged.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
            result = self.adapter.verify_strict_action_csv(
                forged, manifest, self.mapping, trusted_g6, trusted_g8, Path(specs["g6"]["path"]),
                trusted_g8_report_path=Path(specs["g8"]["path"]), action_hmac_key=self.hmac_key,
            )
            self.assertFalse(result["valid"])
            self.assertIn("RUNTIME_ACTION_HMAC_MISMATCH", result["reasons"])

            untrusted = self.adapter.verify_strict_action_csv(
                output, manifest, self.mapping, "0" * 64, trusted_g8, Path(specs["g6"]["path"]),
                trusted_g8_report_path=Path(specs["g8"]["path"]),
            )
            self.assertFalse(untrusted["valid"])
            self.assertIn("G6_EVIDENCE_SHA256_MISMATCH", untrusted["reasons"])

    def test_com_evidence_aggregator_requires_full_readback(self) -> None:
        header = ["kind", "sc_no", "metadata"]
        contract = self.adapter.build_strict_actuation_contract(self.manifest, self.mapping)
        control = SimpleNamespace(
            green_times={
                key: 40.0 for row in self.mapping["signals"]
                for key in (f"{row['id']}_p1", f"{row['id']}_p2")
            }
        )
        identity = self.adapter.build_strict_step_action_identity(
            control, self.mapping, contract, {"sim_sec": 60.0}, 60.0
        )
        payload_rows = []
        for sc_no, native in contract["controllers"].items():
            minor = float(native["minimum_minor_sec"])
            major = float(native["native_effective_green_budget_sec"]) - minor
            payload_rows.append({
                "kind": "signal", "sc_no": sc_no, "authority_uf_id": native["uf_id"],
                "authorized_sgs": "|".join(map(str, native["authorized_sgs"])),
                "sg_phase_map": native["sg_phase_map"], "major_green": str(major),
                "minor_green": str(minor), "offset": "0.0",
                "native_cycle_sec": str(native["native_cycle_sec"]),
                "native_program_offset_sec": str(native["native_program_offset_sec"]),
                "native_controller_offset_sec": str(native["native_controller_offset_sec"]),
                "native_start_time_of_day_sec": str(native["native_start_time_of_day_sec"]),
                "native_epoch_sec": str(native["native_epoch_sec"]),
                "native_switchpoint_sec": str(native["native_switchpoint_sec"]),
                "native_program_no": str(native["native_program_no"]),
                "native_program_sha256": native["native_program_sha256"],
                "native_effective_green_budget_sec": str(native["native_effective_green_budget_sec"]),
                "native_lost_sec": str(native["native_lost_sec"]),
                "normalization": "native_budget_exact", "waveform_safe": "1",
                "signal_write_enabled": "1", "runtime_offset_enabled": "0",
                "topology_hash": contract["topology_hash"],
                "action_interval_id": identity["action_interval_id"],
                "action_valid_from_sec": str(identity["action_valid_from_sec"]),
                "action_valid_until_sec": str(identity["action_valid_until_sec"]),
                "action_decision_time_sec": str(identity["action_decision_time_sec"]),
                "based_on_state_hash": identity["based_on_state_hash"],
                "policy_hash": "7" * 64, "build_hash": "8" * 64,
                "action_schema_hash": "9" * 64,
            })
        runtime_hash = self.adapter.runtime_action_sha256(payload_rows)
        payload_buffer = io.StringIO(newline="")
        payload_fields = ["kind", *self.adapter.RUNTIME_ACTION_ROW_FIELDS]
        payload_writer = csv.DictWriter(payload_buffer, fieldnames=payload_fields, lineterminator="\n")
        payload_writer.writeheader()
        payload_writer.writerows(payload_rows)
        payload_text = payload_buffer.getvalue().rstrip("\r\n")
        payload_digest = hashlib.sha256(payload_text.encode()).hexdigest()
        state_artifact_hash = "c" * 64
        verification = {
            "runtime_action_hash": runtime_hash, "current_state_hash": identity["based_on_state_hash"],
            "current_state_artifact_sha256": state_artifact_hash, "sim_sec": "60.000000",
            "action_interval_id": identity["action_interval_id"],
            "action_decision_time_sec": "60.000000", "action_valid_from_sec": "60.000000",
            "action_valid_until_sec": "120.000000", "policy_hash": "7" * 64,
            "build_hash": "8" * 64, "action_schema_hash": "9" * 64,
        }
        envelope_hmac = self.adapter.action_envelope_hmac_sha256(verification, payload_digest, self.hmac_key)
        envelope_metadata = ";".join([
            f"csv_payload_b64={base64.b64encode(payload_text.encode()).decode()}",
            f"csv_payload_sha256={payload_digest}", f"envelope_hmac_sha256={envelope_hmac}",
            *[f"{key}={value}" for key, value in self.adapter.action_envelope_payload(verification, payload_digest).items()],
        ])
        rows = [{"kind": "action_envelope", "sc_no": "", "metadata": envelope_metadata}]
        for sc_no, native in contract["controllers"].items():
            for sg_no in native["authorized_sgs"]:
                metadata = (
                    f"sg_no={sg_no};requested_state=GREEN;state_readback=GREEN;contr_readback=True;"
                    f"readback_ok=true;evidence_kind=sigstate;interval_id={identity['action_interval_id']}:tick=60;"
                    f"topology_hash={self.manifest['topology_hash']};program_hash={native['native_program_sha256']};"
                    f"action_hash={identity['step_action_hash']};action_set_sha256={identity['action_set_sha256']};"
                    f"runtime_action_hash={runtime_hash};policy_hash={'7' * 64};build_hash={'8' * 64};"
                    f"action_schema_hash={'9' * 64};runtime_action_hmac_sha256={'6' * 64};"
                    f"row_contract_sha256={hashlib.sha256(f'{sc_no}-{sg_no}'.encode()).hexdigest()};"
                    f"csv_payload_sha256={payload_digest};envelope_hmac_sha256={envelope_hmac};"
                    f"parent_runtime_action_hash={runtime_hash};parent_action_interval_id={identity['action_interval_id']};"
                    "contr_requested=True;run_id=run-1;build_id=build-1;network_id=network-1;seed=13;demand_identity=demand-1"
                )
                rows.append({"kind": "signal_com", "sc_no": sc_no, "metadata": metadata})
                release_metadata = (
                    metadata.replace("requested_state=GREEN", "requested_state=")
                    .replace("state_readback=GREEN", "state_readback=")
                    .replace("contr_readback=True", "contr_readback=False")
                    .replace("contr_requested=True", "contr_requested=False")
                    .replace("evidence_kind=sigstate", "evidence_kind=native_release")
                    .replace(f"interval_id={identity['action_interval_id']}:tick=60", "interval_id=release:tick=61")
                )
                rows.append({"kind": "signal_com", "sc_no": sc_no, "metadata": release_metadata})
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "com.csv"
            with path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=header)
                writer.writeheader()
                writer.writerows(rows)
            passed = self.adapter.aggregate_com_evidence_csv(
                path, CANONICAL_ROOT, self.manifest, self.mapping
            )
            self.assertEqual(passed["gates"]["g8_readback"]["verdict"], "PASS")
            self.assertEqual(passed["gates"]["g8_native_release"]["verdict"], "PASS")
            self.assertEqual(passed["aggregate"]["success_rate"], 1.0)
            self.assertEqual(passed["provenance"]["action_hashes"], [identity["step_action_hash"]])

            with path.open("a", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=header)
                writer.writerow(rows[1])
            failed = self.adapter.aggregate_com_evidence_csv(
                path, CANONICAL_ROOT, self.manifest, self.mapping
            )
            self.assertEqual(failed["gates"]["g8_readback"]["verdict"], "FAIL")
            self.assertEqual(failed["aggregate"]["duplicate_authority_pair_count"], 1)

            unauthorized = dict(rows[1])
            unauthorized["sc_no"] = "9999"
            unauthorized["metadata"] = unauthorized["metadata"].replace("sg_no=", "sg_no=999;")
            with path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=header)
                writer.writeheader()
                writer.writerows(rows + [unauthorized])
            extra = self.adapter.aggregate_com_evidence_csv(
                path, CANONICAL_ROOT, self.manifest, self.mapping
            )
            self.assertEqual(extra["gates"]["g8_readback"]["verdict"], "FAIL")
            self.assertEqual(extra["aggregate"]["extra_authority_pair_count"], 1)

            contr_only = dict(rows[1])
            contr_only["metadata"] = (
                contr_only["metadata"].replace("requested_state=GREEN", "requested_state=")
                .replace("evidence_kind=sigstate", "evidence_kind=contr_by_com")
                .replace("interval_id=", "interval_id=contr-only-")
            )
            with path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=header)
                writer.writeheader()
                writer.writerows(rows + [contr_only])
            missing_sigstate = self.adapter.aggregate_com_evidence_csv(
                path, CANONICAL_ROOT, self.manifest, self.mapping
            )
            self.assertEqual(missing_sigstate["gates"]["g8_readback"]["verdict"], "FAIL")
            self.assertGreater(missing_sigstate["aggregate"]["missing_authority_pair_count"], 0)

            false_contr = [dict(row) for row in rows]
            false_contr[1]["metadata"] = false_contr[1]["metadata"].replace(
                "contr_requested=True", "contr_requested=False"
            )
            with path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=header)
                writer.writeheader()
                writer.writerows(false_contr)
            bad_contr = self.adapter.aggregate_com_evidence_csv(
                path, CANONICAL_ROOT, self.manifest, self.mapping
            )
            self.assertEqual(bad_contr["gates"]["g8_readback"]["verdict"], "FAIL")

            mismatched_release = [dict(row) for row in rows]
            release_index = next(
                index for index, row in enumerate(mismatched_release)
                if "evidence_kind=native_release" in row["metadata"]
            )
            mismatched_release[release_index]["metadata"] = mismatched_release[release_index]["metadata"].replace(
                f"parent_action_interval_id={identity['action_interval_id']}",
                "parent_action_interval_id=wrong-interval",
            )
            with path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=header)
                writer.writeheader()
                writer.writerows(mismatched_release)
            mismatched = self.adapter.aggregate_com_evidence_csv(
                path, CANONICAL_ROOT, self.manifest, self.mapping
            )
            self.assertEqual(mismatched["gates"]["g8_native_release"]["verdict"], "FAIL")
            self.assertGreater(mismatched["aggregate"]["native_release_parent_mismatch_count"], 0)

            with path.open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=header)
                writer.writeheader()
                writer.writerow(rows[1])
            one_row = self.adapter.aggregate_com_evidence_csv(
                path, CANONICAL_ROOT, self.manifest, self.mapping
            )
            self.assertEqual(one_row["gates"]["g8_readback"]["verdict"], "FAIL")
            self.assertGreater(one_row["aggregate"]["missing_authority_pair_count"], 0)

    def test_vbs_embeds_exact_authority_and_hashes(self) -> None:
        text = VBS_PATH.read_text(encoding="utf-8")
        self.assertIn(f'Const STRICT_EXPECTED_TOPOLOGY_HASH = "{self.manifest["topology_hash"]}"', text)
        self.assertIn("STRICT_AUTHORITY_FILTERS", text)
        self.assertIn("STRICT_PROGRAM_HASH_BY_SC", text)
        self.assertIn("STRICT_PHASE_MAP_BY_SC", text)
        self.assertIn("STRICT_CLOCK_META_BY_SC", text)
        self.assertIn("StrictCsvRowAuthorized", text)
        self.assertIn("PythonVerifiedActionPayload", text)
        self.assertIn("--emit-verified-action-protocol", text)
        self.assertIn("STRICT_ACTION_PROTOCOL_V1_BEGIN", text)
        self.assertIn("STRICT_ACTION_CSV_BEGIN", text)
        self.assertNotIn("PythonSealedActionCsv", text)
        self.assertNotIn("OpenTextFile(sealedCsvPath", text)
        self.assertIn("verifiedRuntimeActionHash", text)
        self.assertIn("runtime_action_hash=", text)
        self.assertIn("policy_hash=", text)
        self.assertIn("action_schema_hash=", text)
        self.assertIn("RW_TRUSTED_G6_REPORT_PATH", text)
        self.assertIn("RW_TRUSTED_G6_REPORT_SHA256", text)
        self.assertIn("RW_TRUSTED_G6_REPORT_PATH", text)
        self.assertIn("RW_TRUSTED_G8_REPORT_SHA256", text)
        self.assertIn("RW_TRUSTED_G8_REPORT_PATH", text)
        self.assertIn("RW_ACTION_HMAC_KEY", text)
        self.assertIn("Const STRICT_GREEN_ONLY_COMPILETIME_ENABLED = False", text)
        self.assertIn("green_only_compile_time_hard_lock", text)
        for row in self.mapping["signals"]:
            expected = f"{row['sc_no']}:" + "|".join(map(str, row["signal_group_filter"]))
            self.assertIn(expected, text)

    def test_old_csv_is_fail_closed_and_legacy_needs_explicit_opt_in(self) -> None:
        text = VBS_PATH.read_text(encoding="utf-8")
        old_header = "kind,id,dsd_no,sc_no,link,lane,speed_kph,major_green,minor_green,offset,rate_vph,green_sec,metadata"
        self.assertNotIn("actuation_stage", old_header.split(","))
        self.assertIn('If Not columns.Exists("actuation_stage") Then valid = False', text)
        self.assertIn('CsvValue(parts, columns, "actuation_stage", -1, "shadow")', text)
        self.assertIn('EnvironmentBool("RW_ALLOW_LEGACY_ACTUATION")', text)
        self.assertIn('LCase(Trim(CStr(stage))) = "legacy"', text)
        self.assertIn('Trim(CStr(RW_SIGNAL_SG_FILTERS)) <> ""', text)
        self.assertIn("sigOffset(scNo) = 0.0", text)
        self.assertGreaterEqual(text.count("If LegacyRowActuationAllowed(stage) Then"), 3)
        self.assertIn("If Not LegacyRuntimeActuationAllowed() Then Exit Sub", text)

    def test_vbs_enforces_shadow_atomic_com_and_evidence_logging(self) -> None:
        text = VBS_PATH.read_text(encoding="utf-8")
        self.assertIn("ReleaseRuntimeSignalControl", text)
        self.assertIn("ReleaseAllRuntimeActuation", text)
        self.assertIn("LegacyRuntimeActuationAllowed", text)
        self.assertIn("signal_write_enabled", text)
        self.assertIn("runtime_offset_enabled", text)
        self.assertIn("evidence_artifacts_valid", text)
        self.assertIn("waveform_safe", text)
        self.assertIn("native_program_offset_sec", text)
        self.assertIn("- CDbl(DictValue(sigProgramOffset", text)
        self.assertIn("switchpoint is not phase", text)
        self.assertIn('sg.AttValue("ContrByCOM") = False', text)
        self.assertIn("SetContrByComAndVerify", text)
        self.assertIn("RestoreControllerNative", text)
        self.assertIn("FatalActuationError", text)
        self.assertIn("WScript.Quit 91", text)
        self.assertIn("If CBool(rollbackFailed) Then FatalActuationError", text)
        self.assertIn("ControllerMetadataMatches", text)
        self.assertIn("LogSignalComEvidence", text)
        self.assertIn("prog_no=", text)
        self.assertIn("controller_offset_sec=", text)
        self.assertIn("cycle_sec=", text)
        self.assertIn("contr_readback=", text)
        self.assertIn("requested=", text)
        self.assertIn("readback=", text)
        self.assertIn("readback_ok=", text)
        self.assertIn("row_contract_sha256=", text)
        self.assertNotIn('TrySetAtt sc, "Offset"', text)
        self.assertNotIn('AttValue("Offset") =', text)

    def test_repo_root_is_explicit_and_portable(self) -> None:
        text = ADAPTER_PATH.read_text(encoding="utf-8")
        vbs = VBS_PATH.read_text(encoding="utf-8")
        self.assertIn('os.environ.get("STRICT_NUMERICAL_SIM_REPO", "")', text)
        self.assertIn("canonical Numerical-Sim repo is required", text)
        self.assertIn('cmd = cmd & " --repo-root "', vbs)
        self.assertNotIn("C:\\tmp\\numerical-sim-strict-vissim", text)

    def test_watchdog_passes_26th_repo_root_and_trusted_hashes(self) -> None:
        text = WATCHDOG_PATH.read_text(encoding="utf-8")
        self.assertIn("[string]$NumericalSimRepoRoot = $env:STRICT_NUMERICAL_SIM_REPO", text)
        self.assertIn('$argline = $argline + " " + (Q $NumericalSimRepoRoot)', text)
        self.assertIn("RW_TRUSTED_G6_REPORT_SHA256", text)
        self.assertIn("RW_TRUSTED_G8_REPORT_SHA256", text)
        self.assertIn("RW_TRUSTED_G8_REPORT_PATH", text)
        self.assertIn("RW_ACTION_HMAC_KEY", text)


if __name__ == "__main__":
    unittest.main()
