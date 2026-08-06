from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import copy
import json
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


from scripts.build_state_manifest_v2_1 import (
    CAPTURE_SCHEMA_VERSION,
    MAX_STATE_BYTES,
    VehicleCaptureEvidenceError,
    build_vehicle_capture_evidence,
    capture_evidence_json_bytes,
    main as builder_main,
    publish_vehicle_capture_evidence_create_once,
    validate_vehicle_capture_evidence,
    vehicle_capture_sidecar_path,
)
from scripts.tests.test_b1a_run_manifest_slice import RunManifestFixture
from plant.src.vissim_strict.physical_projection import (
    file_sha256,
    strict_load_json,
    workspace_relative_path,
)
from plant.src.vissim_strict.run_evidence import MONOTONIC_CLOCK
from plant.src.vissim_strict.topology import canonical_json_sha256


def write_json(path: Path, value: object) -> None:
    from plant.src.vissim_strict.physical_projection import atomic_write_json

    atomic_write_json(path, value)  # type: ignore[arg-type]


class VehicleCaptureEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.run_manifest = self.root / "runs" / "run_manifest_v2_1.json"
        self.state = self.root / "runs" / "state_000060.json"
        self.topology = self.root / "outputs" / "physical_stock_topology_v2_1.json"
        self.run_manifest.parent.mkdir(parents=True, exist_ok=True)
        self.topology.parent.mkdir(parents=True, exist_ok=True)
        topology = {
            "semantic_sha256": "a" * 64,
            "stocks": [
                {"id": "c", "link_no": "10", "lane_no": 1, "parent_kind": "connector", "roles": ["connector"]},
                {"id": "r1", "link_no": "20", "lane_no": 1, "parent_kind": "link", "roles": ["urban"]},
                {"id": "r2", "link_no": "20", "lane_no": 2, "parent_kind": "link", "roles": ["urban"]},
                {"id": "s", "link_no": "30", "lane_no": 1, "parent_kind": "link", "roles": ["urban"]},
            ],
        }
        write_json(self.topology, topology)
        self.manifest_obj = {
            "run_id": "run-001",
            "qualification": {"mode": "live_required"},
            "approved_topology": {"topology_path": workspace_relative_path(self.root, self.topology)},
        }
        write_json(self.run_manifest, self.manifest_obj)
        self.manifest_sha = file_sha256(self.run_manifest)
        self.validated = SimpleNamespace(
            artifact={
                "run_id": "run-001",
                "qualification": {"mode": "live_required"},
                "approved_topology": {"topology_path": workspace_relative_path(self.root, self.topology)},
            },
            qualification_mode="live_required",
        )
        self.state_obj = {
            "sim_sec": 60.0,
            "run_provenance": {
                "run_id": "run-001",
                "manifest_path": workspace_relative_path(self.root, self.run_manifest),
                "manifest_sha256": self.manifest_sha,
            },
            "total_vehicles": 4,
            "stopped_vehicles": 0,
            "vehicle_records": {
                "schema_version": "vissim-vehicle-records-v2.1",
                "complete": True,
                "paused_at_sim_sec": 60.0,
                "capture_sim_sec_before": 60.0,
                "capture_sim_sec_after": 60.0,
                "source_attributes": {"vehicle_number": "No", "lane": "Lane", "position": "Pos", "speed": "Speed"},
                "stopped_threshold_kph": 1.0,
                "collection_count_before": 4,
                "collection_count_after": 4,
                "record_count": 4,
                "unobservable_count": 0,
                "external_source_count": 0,
                "full_network_link_counts": {"10": 1, "20": 2, "30": 1},
                "full_network_link_stopped_counts": {"10": 0, "20": 0, "30": 0},
                "records": [
                    {"veh_no": 9, "link_no": 30, "lane_no": 1, "position_m": 1.0, "speed_kph": 10.0, "stopped": False},
                    {"veh_no": 2, "link_no": 20, "lane_no": 2, "position_m": 2.0, "speed_kph": 20.0, "stopped": False},
                    {"veh_no": 7, "link_no": 10, "lane_no": 1, "position_m": 3.0, "speed_kph": 30.0, "stopped": False},
                    {"veh_no": 5, "link_no": 20, "lane_no": 1, "position_m": 4.0, "speed_kph": 40.0, "stopped": False},
                ],
            },
        }
        write_json(self.state, self.state_obj)
        self.request = {
            "run_id": "run-001",
            "sim_sec": 60.0,
            "qualification": {"mode": "live_required"},
            "run_manifest_path": workspace_relative_path(self.root, self.run_manifest),
            "run_manifest_sha256": self.manifest_sha,
            "state_path": workspace_relative_path(self.root, self.state),
            "vissim_version_raw": "2020.00",
            "counts": {"collection_count_before": 4, "collection_count_after": 4, "record_count": 4},
            "capture_timer": {
                "clock": MONOTONIC_CLOCK,
                "start_ns": 100,
                "end_ns": 200,
                "elapsed_sec": 0.0,
            },
            "raw_attribute_rows": [
                {"com_key": 9, "no_value": 9, "lane_raw": "30-1", "parsed_link_no": 30, "parsed_lane_no": 1, "position_value": 1.0, "speed_value": 10.0},
                {"com_key": 2, "no_value": 2, "lane_raw": "20-2", "parsed_link_no": 20, "parsed_lane_no": 2, "position_value": 2.0, "speed_value": 20.0},
                {"com_key": 7, "no_value": 7, "lane_raw": "10-1", "parsed_link_no": 10, "parsed_lane_no": 1, "position_value": 3.0, "speed_value": 30.0},
                {"com_key": 5, "no_value": 5, "lane_raw": "20-1", "parsed_link_no": 20, "parsed_lane_no": 1, "position_value": 4.0, "speed_value": 40.0},
            ],
        }
        self.validator_patch = mock.patch(
            "scripts.build_state_manifest_v2_1.validate_run_manifest",
            return_value=self.validated,
        )
        self.validator = self.validator_patch.start()

    def tearDown(self) -> None:
        if self.validator is not None:
            self.validator_patch.stop()
        self.tmp.cleanup()

    def build(self) -> dict:
        return build_vehicle_capture_evidence(workspace_root=self.root, request=self.request)

    def test_builds_exact_schema_hash_and_priority_samples(self) -> None:
        evidence = self.build()
        self.assertEqual(tuple(evidence), (
            "schema_version",
            "run_id",
            "sim_sec",
            "qualification",
            "run_manifest_path",
            "run_manifest_sha256",
            "state_path",
            "vissim_version_raw",
            "counts",
            "capture_timer",
            "raw_attribute_samples",
            "semantic_sha256",
        ))
        self.assertEqual(evidence["schema_version"], CAPTURE_SCHEMA_VERSION)
        self.assertEqual(evidence["capture_timer"]["elapsed_sec"], 1.0e-7)
        self.assertEqual([row["no_value"] for row in evidence["raw_attribute_samples"]], [2, 5, 7, 9])
        self.assertIn(7, [row["no_value"] for row in evidence["raw_attribute_samples"]])
        self.assertEqual(
            evidence["semantic_sha256"],
            canonical_json_sha256({key: evidence[key] for key in tuple(evidence)[:-1]}),
        )
        self.validator.assert_called()

    def test_rejects_malformed_topology_stock_identities(self) -> None:
        for bad_link_no in ("01", "0", "", "10.0", True):
            with self.subTest(link_no=bad_link_no):
                topology = strict_load_json(self.topology)
                topology["stocks"][0]["link_no"] = bad_link_no
                write_json(self.topology, topology)
                with self.assertRaises(VehicleCaptureEvidenceError):
                    self.build()
                topology["stocks"][0]["link_no"] = "10"
                write_json(self.topology, topology)
        for bad_lane_no in (0, "1", True):
            with self.subTest(lane_no=bad_lane_no):
                topology = strict_load_json(self.topology)
                topology["stocks"][0]["lane_no"] = bad_lane_no
                write_json(self.topology, topology)
                with self.assertRaises(VehicleCaptureEvidenceError):
                    self.build()
                topology["stocks"][0]["lane_no"] = 1
                write_json(self.topology, topology)

    def test_actual_manifest_validation_accepts_compiler_shaped_string_topology(self) -> None:
        self.validator_patch.stop()
        self.validator = None
        fixture = RunManifestFixture(Path(tempfile.gettempdir()))
        try:
            root = fixture.root
            fixture.manifest["qualification"] = {"mode": "live_required"}
            fixture.rehash()
            run_manifest = root / "runs" / "run_manifest_v2_1.json"
            run_manifest.parent.mkdir(parents=True, exist_ok=True)
            write_json(run_manifest, fixture.manifest)
            manifest_sha = file_sha256(run_manifest)
            run_id = fixture.manifest["run_id"]
            sim_sec = fixture.manifest["allowed_capture_times"][0]
            topology_path = root / fixture.manifest["approved_topology"]["topology_path"].replace("/", "\\")
            topology = strict_load_json(topology_path)
            self.assertTrue(all(isinstance(stock["link_no"], str) for stock in topology["stocks"]))
            state = root / "runs" / "state_000060.json"
            state_obj = copy.deepcopy(self.state_obj)
            state_obj["sim_sec"] = sim_sec
            state_obj["run_provenance"] = {
                "run_id": run_id,
                "manifest_path": workspace_relative_path(root, run_manifest),
                "manifest_sha256": manifest_sha,
            }
            state_obj["vehicle_records"]["paused_at_sim_sec"] = sim_sec
            state_obj["vehicle_records"]["capture_sim_sec_before"] = sim_sec
            state_obj["vehicle_records"]["capture_sim_sec_after"] = sim_sec
            state_obj["vehicle_records"]["full_network_link_counts"] = {"1": 2, "2": 1, "3": 1}
            state_obj["vehicle_records"]["full_network_link_stopped_counts"] = {"1": 0, "2": 0, "3": 0}
            state_obj["vehicle_records"]["records"] = [
                {"veh_no": 9, "link_no": 3, "lane_no": 1, "position_m": 1.0, "speed_kph": 10.0, "stopped": False},
                {"veh_no": 2, "link_no": 1, "lane_no": 2, "position_m": 2.0, "speed_kph": 20.0, "stopped": False},
                {"veh_no": 7, "link_no": 2, "lane_no": 1, "position_m": 3.0, "speed_kph": 30.0, "stopped": False},
                {"veh_no": 5, "link_no": 1, "lane_no": 1, "position_m": 4.0, "speed_kph": 40.0, "stopped": False},
            ]
            write_json(state, state_obj)
            request = copy.deepcopy(self.request)
            request.update({
                "run_id": run_id,
                "sim_sec": sim_sec,
                "qualification": {"mode": "live_required"},
                "run_manifest_path": workspace_relative_path(root, run_manifest),
                "run_manifest_sha256": manifest_sha,
                "state_path": workspace_relative_path(root, state),
                "raw_attribute_rows": [
                    {"com_key": 9, "no_value": 9, "lane_raw": "3-1", "parsed_link_no": 3, "parsed_lane_no": 1, "position_value": 1.0, "speed_value": 10.0},
                    {"com_key": 2, "no_value": 2, "lane_raw": "1-2", "parsed_link_no": 1, "parsed_lane_no": 2, "position_value": 2.0, "speed_value": 20.0},
                    {"com_key": 7, "no_value": 7, "lane_raw": "2-1", "parsed_link_no": 2, "parsed_lane_no": 1, "position_value": 3.0, "speed_value": 30.0},
                    {"com_key": 5, "no_value": 5, "lane_raw": "1-1", "parsed_link_no": 1, "parsed_lane_no": 1, "position_value": 4.0, "speed_value": 40.0},
                ],
            })
            evidence = build_vehicle_capture_evidence(workspace_root=root, request=request)
            self.assertEqual(evidence["run_manifest_sha256"], manifest_sha)
            self.assertEqual([row["no_value"] for row in evidence["raw_attribute_samples"]], [2, 5, 7, 9])
        finally:
            fixture.close()

    def test_create_once_publish_and_validate_reject_replacement(self) -> None:
        sidecar = vehicle_capture_sidecar_path(self.state)
        publish_vehicle_capture_evidence_create_once(
            workspace_root=self.root,
            request=self.request,
            output_path=sidecar,
        )
        loaded = strict_load_json(sidecar)
        self.assertEqual(validate_vehicle_capture_evidence(loaded, workspace_root=self.root), loaded)
        with self.assertRaises(VehicleCaptureEvidenceError):
            publish_vehicle_capture_evidence_create_once(
                workspace_root=self.root,
                request=self.request,
                output_path=sidecar,
            )

    def test_concurrent_create_once_publish_has_one_immutable_winner(self) -> None:
        sidecar = vehicle_capture_sidecar_path(self.state)
        requests = []
        expected_payloads = []
        for index in range(8):
            request = copy.deepcopy(self.request)
            request["capture_timer"]["start_ns"] = 1_000 + index * 100
            request["capture_timer"]["end_ns"] = 1_050 + index * 100
            requests.append(request)
            evidence = build_vehicle_capture_evidence(workspace_root=self.root, request=request)
            expected_payloads.append(capture_evidence_json_bytes(evidence))
        barrier = threading.Barrier(len(requests))

        def publish(index: int) -> tuple[int, str]:
            barrier.wait(timeout=5.0)
            try:
                publish_vehicle_capture_evidence_create_once(
                    workspace_root=self.root,
                    request=requests[index],
                    output_path=sidecar,
                )
                return index, "success"
            except VehicleCaptureEvidenceError:
                return index, "closed"

        with ThreadPoolExecutor(max_workers=len(requests)) as executor:
            results = list(executor.map(publish, range(len(requests))))

        successes = [index for index, status in results if status == "success"]
        self.assertEqual(len(successes), 1, results)
        self.assertEqual([status for _, status in results].count("closed"), len(requests) - 1)
        final_bytes = sidecar.read_bytes()
        self.assertEqual(final_bytes, expected_payloads[successes[0]])
        self.assertIn(final_bytes, expected_payloads)
        loaded = strict_load_json(sidecar)
        self.assertEqual(validate_vehicle_capture_evidence(loaded, workspace_root=self.root), loaded)

    def test_mutations_fail_closed(self) -> None:
        cases = []
        bad = copy.deepcopy(self.request)
        bad["counts"]["record_count"] = 3
        cases.append(bad)
        bad = copy.deepcopy(self.request)
        bad["capture_timer"]["end_ns"] = 100
        cases.append(bad)
        bad = copy.deepcopy(self.request)
        bad["raw_attribute_rows"][0]["parsed_link_no"] = 999
        cases.append(bad)
        bad = copy.deepcopy(self.request)
        bad["raw_attribute_rows"][1]["position_value"] = 999.0
        cases.append(bad)
        for candidate in cases:
            with self.subTest(candidate=candidate):
                with self.assertRaises(VehicleCaptureEvidenceError):
                    build_vehicle_capture_evidence(workspace_root=self.root, request=candidate)

    def test_integer_domain_mutations_fail_closed_in_producer(self) -> None:
        cases = []
        bad = copy.deepcopy(self.request)
        bad["counts"]["record_count"] = 20_001
        cases.append(bad)
        bad = copy.deepcopy(self.request)
        bad["capture_timer"]["start_ns"] = 10**100
        bad["capture_timer"]["end_ns"] = 10**100 + 100
        cases.append(bad)
        bad = copy.deepcopy(self.request)
        bad["raw_attribute_rows"][0]["no_value"] = 2_147_483_648
        cases.append(bad)
        bad = copy.deepcopy(self.request)
        bad["raw_attribute_rows"][0]["parsed_link_no"] = 2_147_483_648
        cases.append(bad)
        bad = copy.deepcopy(self.request)
        bad["raw_attribute_rows"][0]["parsed_lane_no"] = 2_147_483_648
        cases.append(bad)
        for candidate in cases:
            with self.subTest(candidate=json.dumps(candidate, default=str)[:120]):
                with self.assertRaises(VehicleCaptureEvidenceError):
                    build_vehicle_capture_evidence(workspace_root=self.root, request=candidate)

        state = copy.deepcopy(self.state_obj)
        state["vehicle_records"]["records"][0]["veh_no"] = 2_147_483_648
        write_json(self.state, state)
        with self.assertRaises(VehicleCaptureEvidenceError):
            build_vehicle_capture_evidence(workspace_root=self.root, request=self.request)

    def test_state_record_shape_and_numeric_mutations_fail_in_producer_and_validator(self) -> None:
        base_evidence = self.build()

        def assert_state_mutation_rejected(mutator) -> None:
            state = copy.deepcopy(self.state_obj)
            mutator(state["vehicle_records"]["records"][0])
            write_json(self.state, state)
            with self.assertRaises(VehicleCaptureEvidenceError):
                build_vehicle_capture_evidence(workspace_root=self.root, request=self.request)
            with self.assertRaises(VehicleCaptureEvidenceError):
                validate_vehicle_capture_evidence(base_evidence, workspace_root=self.root)

        cases = [
            ("position_string", lambda record: record.__setitem__("position_m", "1.0")),
            ("position_bool", lambda record: record.__setitem__("position_m", True)),
            ("position_integer", lambda record: record.__setitem__("position_m", 1)),
            ("speed_string", lambda record: record.__setitem__("speed_kph", "10.0")),
            ("speed_bool", lambda record: record.__setitem__("speed_kph", False)),
            ("speed_integer", lambda record: record.__setitem__("speed_kph", 10)),
            ("negative_speed", lambda record: record.__setitem__("speed_kph", -0.1)),
            ("negative_position_beyond_tolerance", lambda record: record.__setitem__("position_m", -0.0000011)),
            ("stopped_mismatch", lambda record: record.__setitem__("stopped", True)),
            ("extra_field", lambda record: record.__setitem__("extra", 1)),
            ("missing_field", lambda record: record.__delitem__("speed_kph")),
        ]
        for label, mutator in cases:
            with self.subTest(label=label):
                assert_state_mutation_rejected(mutator)

        self.state.write_text(
            json.dumps(self.state_obj, allow_nan=False, separators=(",", ":")).replace(
                '"position_m":1.0',
                '"position_m":NaN',
                1,
            ),
            encoding="utf-8",
        )
        with self.assertRaises((VehicleCaptureEvidenceError, ValueError)):
            build_vehicle_capture_evidence(workspace_root=self.root, request=self.request)
        with self.assertRaises((VehicleCaptureEvidenceError, ValueError)):
            validate_vehicle_capture_evidence(base_evidence, workspace_root=self.root)

    def test_state_envelope_counts_are_rederived_in_producer_and_validator(self) -> None:
        base_evidence = self.build()

        def assert_state_mutation_rejected(label: str, mutator) -> None:
            state = copy.deepcopy(self.state_obj)
            mutator(state)
            write_json(self.state, state)
            with self.subTest(path="producer", label=label):
                with self.assertRaises(VehicleCaptureEvidenceError):
                    build_vehicle_capture_evidence(workspace_root=self.root, request=self.request)
            with self.subTest(path="validator", label=label):
                with self.assertRaises(VehicleCaptureEvidenceError):
                    validate_vehicle_capture_evidence(base_evidence, workspace_root=self.root)

        cases = [
            ("link_count_drift", lambda state: state["vehicle_records"]["full_network_link_counts"].__setitem__("10", 4)),
            ("link_count_missing_key", lambda state: state["vehicle_records"]["full_network_link_counts"].pop("30")),
            ("link_count_extra_key", lambda state: state["vehicle_records"]["full_network_link_counts"].__setitem__("40", 0)),
            ("stopped_count_drift", lambda state: state["vehicle_records"]["full_network_link_stopped_counts"].__setitem__("20", 1)),
            ("stopped_count_missing_zero_key", lambda state: state["vehicle_records"]["full_network_link_stopped_counts"].pop("30")),
            ("stopped_count_extra_key", lambda state: state["vehicle_records"]["full_network_link_stopped_counts"].__setitem__("40", 0)),
            ("link_map_bool_value", lambda state: state["vehicle_records"]["full_network_link_counts"].__setitem__("10", True)),
            ("link_map_string_value", lambda state: state["vehicle_records"]["full_network_link_counts"].__setitem__("10", "1")),
            ("link_map_negative_value", lambda state: state["vehicle_records"]["full_network_link_counts"].__setitem__("10", -1)),
            ("link_map_oversize_value", lambda state: state["vehicle_records"]["full_network_link_counts"].__setitem__("10", 20_001)),
            ("link_map_noncanonical_key", lambda state: state["vehicle_records"]["full_network_link_counts"].__setitem__("010", 1)),
            ("link_map_bool_key", lambda state: state["vehicle_records"].__setitem__("full_network_link_counts", {True: 1})),
            ("collection_count_drift", lambda state: state["vehicle_records"].__setitem__("collection_count_before", 3)),
            ("unobservable_count_drift", lambda state: state["vehicle_records"].__setitem__("unobservable_count", 1)),
            ("envelope_extra_field", lambda state: state["vehicle_records"].__setitem__("extra", 1)),
            ("envelope_missing_field", lambda state: state["vehicle_records"].pop("source_attributes")),
            ("root_total_drift", lambda state: state.__setitem__("total_vehicles", 3)),
            ("root_stopped_total_drift", lambda state: state.__setitem__("stopped_vehicles", 1)),
        ]
        for label, mutator in cases:
            assert_state_mutation_rejected(label, mutator)

    def test_required_state_envelope_exact_types_on_producer_validator_and_cli(self) -> None:
        base_evidence = self.build()
        cli_args = [
            "--workspace-root", str(self.root),
            "--validate-state-run-binding",
            "--state", str(self.state),
            "--run-manifest", str(self.run_manifest),
            "--run-manifest-sha256", self.manifest_sha,
            "--run-id", "run-001",
            "--qualification-mode", "live_required",
            "--capture-time", "60.0",
        ]

        def assert_state_mutation_rejected(label: str, mutator) -> None:
            state = copy.deepcopy(self.state_obj)
            mutator(state)
            write_json(self.state, state)
            with self.subTest(path="producer", label=label):
                with self.assertRaises(VehicleCaptureEvidenceError):
                    build_vehicle_capture_evidence(workspace_root=self.root, request=self.request)
            with self.subTest(path="validator", label=label):
                with self.assertRaises(VehicleCaptureEvidenceError):
                    validate_vehicle_capture_evidence(base_evidence, workspace_root=self.root)
            with self.subTest(path="cli", label=label):
                self.assertEqual(builder_main(cli_args), 1)

        cases = [
            ("missing_root_total_vehicles", lambda state: state.pop("total_vehicles")),
            ("missing_root_stopped_vehicles", lambda state: state.pop("stopped_vehicles")),
            ("null_root_total_vehicles", lambda state: state.__setitem__("total_vehicles", None)),
            ("bool_root_total_vehicles", lambda state: state.__setitem__("total_vehicles", True)),
            ("string_root_total_vehicles", lambda state: state.__setitem__("total_vehicles", "4")),
            ("negative_root_total_vehicles", lambda state: state.__setitem__("total_vehicles", -1)),
            ("overflow_root_total_vehicles", lambda state: state.__setitem__("total_vehicles", 20_001)),
            ("null_root_stopped_vehicles", lambda state: state.__setitem__("stopped_vehicles", None)),
            ("bool_root_stopped_vehicles", lambda state: state.__setitem__("stopped_vehicles", False)),
            ("string_root_stopped_vehicles", lambda state: state.__setitem__("stopped_vehicles", "0")),
            ("negative_root_stopped_vehicles", lambda state: state.__setitem__("stopped_vehicles", -1)),
            ("overflow_root_stopped_vehicles", lambda state: state.__setitem__("stopped_vehicles", 20_001)),
            ("unobservable_bool_false", lambda state: state["vehicle_records"].__setitem__("unobservable_count", False)),
            ("external_source_bool_false", lambda state: state["vehicle_records"].__setitem__("external_source_count", False)),
            ("stopped_threshold_bool_true", lambda state: state["vehicle_records"].__setitem__("stopped_threshold_kph", True)),
            ("stopped_threshold_integer_one", lambda state: state["vehicle_records"].__setitem__("stopped_threshold_kph", 1)),
            ("paused_at_sim_sec_integer", lambda state: state["vehicle_records"].__setitem__("paused_at_sim_sec", 60)),
            ("capture_sim_sec_before_integer", lambda state: state["vehicle_records"].__setitem__("capture_sim_sec_before", 60)),
            ("capture_sim_sec_after_integer", lambda state: state["vehicle_records"].__setitem__("capture_sim_sec_after", 60)),
        ]
        for label, mutator in cases:
            assert_state_mutation_rejected(label, mutator)

    def test_state_envelope_accepts_rederived_stopped_threshold_boundary(self) -> None:
        state = copy.deepcopy(self.state_obj)
        state["stopped_vehicles"] = 1
        state["vehicle_records"]["full_network_link_stopped_counts"] = {"10": 0, "20": 1, "30": 0}
        state["vehicle_records"]["records"][1]["speed_kph"] = 0.999
        state["vehicle_records"]["records"][1]["stopped"] = True
        write_json(self.state, state)
        request = copy.deepcopy(self.request)
        request["raw_attribute_rows"][1]["speed_value"] = 0.999
        evidence = build_vehicle_capture_evidence(workspace_root=self.root, request=request)
        self.assertEqual(validate_vehicle_capture_evidence(evidence, workspace_root=self.root), evidence)

    def test_lane_raw_reparsed_and_bound_to_parser_output(self) -> None:
        producer_cases = []
        bad = copy.deepcopy(self.request)
        bad["raw_attribute_rows"][0]["lane_raw"] = "31-1"
        producer_cases.append(("raw_parsed_disagreement", bad))
        bad = copy.deepcopy(self.request)
        bad["raw_attribute_rows"][0]["lane_raw"] = "30--1"
        producer_cases.append(("two_hyphens", bad))
        bad = copy.deepcopy(self.request)
        bad["raw_attribute_rows"][0]["lane_raw"] = "030-1"
        producer_cases.append(("noncanonical_decimal", bad))
        bad = copy.deepcopy(self.request)
        bad["raw_attribute_rows"][0]["lane_raw"] = "３０-1"
        producer_cases.append(("non_ascii_digit", bad))
        for label, candidate in producer_cases:
            with self.subTest(path="producer", label=label):
                with self.assertRaises(VehicleCaptureEvidenceError):
                    build_vehicle_capture_evidence(workspace_root=self.root, request=candidate)

        evidence = self.build()
        validator_cases = []
        bad = copy.deepcopy(evidence)
        bad["raw_attribute_samples"][0]["lane_raw"] = "21-2"
        validator_cases.append(("raw_parsed_disagreement", bad))
        bad = copy.deepcopy(evidence)
        bad["raw_attribute_samples"][0]["lane_raw"] = "20-2\n"
        validator_cases.append(("vertical_whitespace", bad))
        bad = copy.deepcopy(evidence)
        bad["raw_attribute_samples"][0]["lane_raw"] = "20-２"
        validator_cases.append(("non_ascii_digit", bad))
        for label, candidate in validator_cases:
            with self.subTest(path="validator", label=label):
                with self.assertRaises(VehicleCaptureEvidenceError):
                    validate_vehicle_capture_evidence(candidate, workspace_root=self.root)

    def test_evidence_validator_rejects_count_type_path_run_time_hash_and_nonfinite_mutations(self) -> None:
        evidence = self.build()
        cases = []
        bad = copy.deepcopy(evidence)
        bad["counts"]["record_count"] = True
        cases.append(bad)
        bad = copy.deepcopy(evidence)
        bad["run_id"] = "other-run"
        cases.append(bad)
        bad = copy.deepcopy(evidence)
        bad["sim_sec"] = 120.0
        cases.append(bad)
        bad = copy.deepcopy(evidence)
        bad["state_path"] = "../escape.json"
        cases.append(bad)
        bad = copy.deepcopy(evidence)
        bad["run_manifest_sha256"] = "b" * 64
        cases.append(bad)
        bad = copy.deepcopy(evidence)
        bad["capture_timer"]["elapsed_sec"] = float("nan")
        cases.append(bad)
        bad = copy.deepcopy(evidence)
        bad["capture_timer"]["start_ns"] = 10**100
        bad["capture_timer"]["end_ns"] = 10**100 + 100
        bad["capture_timer"]["elapsed_sec"] = 1.0e-7
        cases.append(bad)
        bad = copy.deepcopy(evidence)
        bad["raw_attribute_samples"][0]["no_value"] = 2_147_483_648
        bad["raw_attribute_samples"][0]["com_key"] = 2_147_483_648
        cases.append(bad)
        bad = copy.deepcopy(evidence)
        bad["semantic_sha256"] = "0" * 64
        cases.append(bad)
        for candidate in cases:
            with self.subTest(candidate=json.dumps(candidate, default=str, allow_nan=True)[:120]):
                with self.assertRaises((VehicleCaptureEvidenceError, ValueError, OSError)):
                    validate_vehicle_capture_evidence(candidate, workspace_root=self.root)

    def test_oversize_20000_rows_selects_at_most_64_with_priority(self) -> None:
        rows = []
        records = []
        for vehicle_no in range(1, 20_001):
            link_no = 30
            lane_no = 1
            if vehicle_no == 101:
                link_no = 10
            elif vehicle_no == 202:
                link_no = 20
                lane_no = 2
            rows.append({
                "com_key": vehicle_no,
                "no_value": vehicle_no,
                "lane_raw": f"{link_no}-{lane_no}",
                "parsed_link_no": link_no,
                "parsed_lane_no": lane_no,
                "position_value": float(vehicle_no),
                "speed_value": 10.0,
            })
            records.append({
                "veh_no": vehicle_no,
                "link_no": link_no,
                "lane_no": lane_no,
                "position_m": float(vehicle_no),
                "speed_kph": 10.0,
                "stopped": False,
            })
        self.state_obj["vehicle_records"]["collection_count_before"] = 20_000
        self.state_obj["vehicle_records"]["collection_count_after"] = 20_000
        self.state_obj["vehicle_records"]["record_count"] = 20_000
        self.state_obj["total_vehicles"] = 20_000
        self.state_obj["stopped_vehicles"] = 0
        self.state_obj["vehicle_records"]["records"] = records
        self.state_obj["vehicle_records"]["full_network_link_counts"] = {"10": 1, "20": 1, "30": 19_998}
        self.state_obj["vehicle_records"]["full_network_link_stopped_counts"] = {"10": 0, "20": 0, "30": 0}
        write_json(self.state, self.state_obj)
        request = copy.deepcopy(self.request)
        request["counts"] = {"collection_count_before": 20_000, "collection_count_after": 20_000, "record_count": 20_000}
        request["raw_attribute_rows"] = rows
        evidence = build_vehicle_capture_evidence(workspace_root=self.root, request=request)
        samples = evidence["raw_attribute_samples"]
        self.assertEqual(len(samples), 64)
        self.assertIn(101, [row["no_value"] for row in samples])
        self.assertIn(202, [row["no_value"] for row in samples])
        too_many = copy.deepcopy(request)
        too_many["raw_attribute_rows"] = rows + [rows[-1]]
        with self.assertRaises(VehicleCaptureEvidenceError):
            build_vehicle_capture_evidence(workspace_root=self.root, request=too_many)

    def test_cli_validate_state_run_binding_rejects_bom_and_malformed_utf8(self) -> None:
        args = [
            "--workspace-root", str(self.root),
            "--validate-state-run-binding",
            "--state", str(self.state),
            "--run-manifest", str(self.run_manifest),
            "--run-manifest-sha256", self.manifest_sha,
            "--run-id", "run-001",
            "--qualification-mode", "live_required",
            "--capture-time", "60.0",
        ]
        self.assertEqual(builder_main(args), 0)
        self.state.write_bytes(b"\xef\xbb\xbf" + self.state.read_bytes())
        self.assertEqual(builder_main(args), 1)
        self.state.write_bytes(b"\xff")
        self.assertEqual(builder_main(args), 1)

    def test_cli_validate_state_run_binding_rejects_oversize_state_before_acceptance(self) -> None:
        args = [
            "--workspace-root", str(self.root),
            "--validate-state-run-binding",
            "--state", str(self.state),
            "--run-manifest", str(self.run_manifest),
            "--run-manifest-sha256", self.manifest_sha,
            "--run-id", "run-001",
            "--qualification-mode", "live_required",
            "--capture-time", "60.0",
        ]
        self.assertEqual(builder_main(args), 0)
        oversize = copy.deepcopy(self.state_obj)
        oversize["padding"] = "x" * MAX_STATE_BYTES
        self.state.write_text(json.dumps(oversize, allow_nan=False), encoding="utf-8")
        self.assertGreater(self.state.stat().st_size, MAX_STATE_BYTES)
        self.assertEqual(builder_main(args), 1)

    def test_cli_vehicle_capture_request_and_sidecar_reject_valid_body_bom(self) -> None:
        request_path = self.root / "runs" / "vehicle_capture_request.json"
        sidecar = vehicle_capture_sidecar_path(self.state)
        write_json(request_path, self.request)
        request_path.write_bytes(b"\xef\xbb\xbf" + request_path.read_bytes())
        produce_args = [
            "--workspace-root", str(self.root),
            "--produce-vehicle-capture",
            "--vehicle-capture-request", str(request_path),
            "--vehicle-capture", str(sidecar),
        ]
        self.assertEqual(builder_main(produce_args), 1)
        self.assertFalse(sidecar.exists())

        publish_vehicle_capture_evidence_create_once(
            workspace_root=self.root,
            request=self.request,
            output_path=sidecar,
        )
        sidecar.write_bytes(b"\xef\xbb\xbf" + sidecar.read_bytes())
        validate_args = [
            "--workspace-root", str(self.root),
            "--validate-vehicle-capture",
            "--vehicle-capture", str(sidecar),
        ]
        self.assertEqual(builder_main(validate_args), 1)

    def test_empty_capture_is_valid_with_empty_samples(self) -> None:
        self.state_obj["vehicle_records"]["collection_count_before"] = 0
        self.state_obj["vehicle_records"]["collection_count_after"] = 0
        self.state_obj["vehicle_records"]["record_count"] = 0
        self.state_obj["total_vehicles"] = 0
        self.state_obj["stopped_vehicles"] = 0
        self.state_obj["vehicle_records"]["full_network_link_counts"] = {}
        self.state_obj["vehicle_records"]["full_network_link_stopped_counts"] = {}
        self.state_obj["vehicle_records"]["records"] = []
        write_json(self.state, self.state_obj)
        request = copy.deepcopy(self.request)
        request["counts"] = {"collection_count_before": 0, "collection_count_after": 0, "record_count": 0}
        request["raw_attribute_rows"] = []
        evidence = build_vehicle_capture_evidence(workspace_root=self.root, request=request)
        self.assertEqual(evidence["raw_attribute_samples"], [])


if __name__ == "__main__":
    unittest.main()
