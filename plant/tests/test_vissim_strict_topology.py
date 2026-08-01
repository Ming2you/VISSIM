import copy
import hashlib
import tempfile
import unittest
from pathlib import Path

from src.vissim_strict.topology import (
    _build_influence_subgraphs,
    canonical_json_sha256,
    canonical_json_text,
    compile_inpx,
    validate_topology,
)


SYNTHETIC_INPX = """<?xml version="1.0" encoding="UTF-8"?>
<network version="702" vissimVersion="test">
  <links>
    <link no="1" name="upstream" level="1" linkBehavType="1" gradient="0">
      <geometry><linkPolyPts>
        <linkPolyPoint x="0" y="0" zOffset="0"/>
        <linkPolyPoint x="100" y="0" zOffset="0"/>
      </linkPolyPts></geometry>
      <lanes><lane width="3.5"/><lane width="3.25" closed="true"/></lanes>
    </link>
    <link no="2" name="downstream" level="1" linkBehavType="1" gradient="0">
      <geometry><linkPolyPts>
        <linkPolyPoint x="110" y="0" zOffset="0"/>
        <linkPolyPoint x="210" y="0" zOffset="0"/>
      </linkPolyPts></geometry>
      <lanes><lane width="3.5"/></lanes>
    </link>
    <link no="100" name="turn">
      <fromLinkEndPt lane="1 1" pos="80"/>
      <geometry><linkPolyPts>
        <linkPolyPoint x="80" y="0" zOffset="0"/>
        <linkPolyPoint x="110" y="0" zOffset="0"/>
      </linkPolyPts></geometry>
      <lanes><lane width="3.5"/></lanes>
      <toLinkEndPt lane="2 1" pos="10"/>
    </link>
  </links>
  <signalControllers>
    <signalController no="10" name="SC10" active="true" type="FIXEDTIME"
      supplyFile2="#data#test.sig" progNo="1" offset="0">
      <sgs><signalGroup no="1" name="through" amber="3" minGreen="5" minRed="1" redAmber="0"/></sgs>
    </signalController>
  </signalControllers>
  <signalHeads>
    <signalHead no="501" lane="1 1" pos="40" sg="10 1"/>
    <signalHead no="502" lane="100 1" pos="15" sg="10 1"/>
  </signalHeads>
  <vehicleInputs>
    <vehicleInput no="1" link="1" name="source">
      <timeIntVehVols><timeIntervalVehVolume timeInt="1 0" volume="600"/></timeIntVehVols>
    </vehicleInput>
  </vehicleInputs>
  <vehicleRoutingDecisionsStatic>
    <vehicleRoutingDecisionStatic no="7" link="1" pos="20">
      <vehRoutSta><vehicleRouteStatic no="1" destLink="2" destPos="90" relFlow="1">
        <linkSeq><intObjectRef key="100"/></linkSeq>
      </vehicleRouteStatic></vehRoutSta>
    </vehicleRoutingDecisionStatic>
    <vehicleRoutingDecisionStatic no="8" link="100" pos="10">
      <vehRoutSta><vehicleRouteStatic no="1" destLink="100" destPos="25" relFlow="1">
        <linkSeq><intObjectRef key="100"/></linkSeq>
      </vehicleRouteStatic></vehRoutSta>
    </vehicleRoutingDecisionStatic>
  </vehicleRoutingDecisionsStatic>
  <dataCollectionPoints>
    <dataCollectionPoint no="1" lane="1 1" pos="25"/>
    <dataCollectionPoint no="2" lane="100 1" pos="12"/>
  </dataCollectionPoints>
  <queueCounters>
    <queueCounter no="1" link="1" pos="35"/>
    <queueCounter no="2" link="100" pos="20"/>
  </queueCounters>
  <vehicleTravelTimeMeasurements>
    <vehicleTravelTimeMeasurement no="1"><start link="1" pos="0"/><end link="2" pos="100"/></vehicleTravelTimeMeasurement>
    <vehicleTravelTimeMeasurement no="2"><start link="100" pos="1"/><end link="100" pos="29"/></vehicleTravelTimeMeasurement>
  </vehicleTravelTimeMeasurements>
  <simulation startTm="3600" simPeriod="7200"/>
</network>
"""


class TopologyCompilerTests(unittest.TestCase):
    def compile_fixture(self):
        directory = tempfile.TemporaryDirectory()
        path = Path(directory.name) / "fixture.inpx"
        path.write_text(SYNTHETIC_INPX, encoding="utf-8")
        return directory, path, compile_inpx(path)

    def test_canonical_json_golden_and_finite_rules(self):
        payload = {"text": "offset", "items": ["x", "y"], "a": 1}
        expected = '{"a":1,"items":["x","y"],"text":"offset"}'
        self.assertEqual(canonical_json_text(payload), expected)
        self.assertEqual(
            canonical_json_sha256(payload),
            "d0151c7e66c7fc710810597fa93b171e01f18e2b668d289b9f5b60d14930e45b",
        )
        self.assertEqual(canonical_json_text({"z": -0.0, "e": 1.0e-7}), '{"e":1e-7,"z":0.0}')
        with self.assertRaises(ValueError):
            canonical_json_text({"bad": float("nan")})

    def test_connector_references_and_source_metadata(self):
        directory, path, manifest = self.compile_fixture()
        self.addCleanup(directory.cleanup)
        connector = manifest["connectors"][0]
        self.assertEqual(connector["from_endpoint"]["lane_id"], "lane:1:1")
        self.assertEqual(connector["to_endpoint"]["lane_id"], "lane:2:1")
        self.assertEqual(manifest["simulation"]["start_time_sec"], 3600.0)
        self.assertEqual(manifest["source"]["inpx_sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertTrue(manifest["validation_report"]["valid"])

    def test_topology_hash_is_checkout_path_independent(self):
        first = tempfile.TemporaryDirectory()
        second = tempfile.TemporaryDirectory()
        self.addCleanup(first.cleanup)
        self.addCleanup(second.cleanup)
        first_path = Path(first.name) / "fixture.inpx"
        second_path = Path(second.name) / "fixture.inpx"
        first_path.write_text(SYNTHETIC_INPX, encoding="utf-8")
        second_path.write_text(SYNTHETIC_INPX, encoding="utf-8")

        first_manifest = compile_inpx(first_path)
        second_manifest = compile_inpx(second_path)

        self.assertEqual(first_manifest["source"]["inpx_path"], "fixture.inpx")
        self.assertEqual(first_manifest["topology_hash"], second_manifest["topology_hash"])

    def test_signal_and_connector_positions_split_lane_cells(self):
        directory, _, manifest = self.compile_fixture()
        self.addCleanup(directory.cleanup)
        upstream = [cell for cell in manifest["cells"] if cell["lane_group_id"] == "lg:link:1:lane:1"]
        downstream = [cell for cell in manifest["cells"] if cell["lane_group_id"] == "lg:link:2:lane:1"]
        connector = [cell for cell in manifest["cells"] if cell["lane_group_id"] == "lg:link:100:lane:1"]
        self.assertEqual([(cell["start_position_m"], cell["end_position_m"]) for cell in upstream], [(0.0, 40.0), (40.0, 80.0), (80.0, 100.0)])
        self.assertEqual([(cell["start_position_m"], cell["end_position_m"]) for cell in downstream], [(0.0, 10.0), (10.0, 100.0)])
        self.assertEqual(
            [(cell["start_position_m"], cell["end_position_m"]) for cell in connector],
            [(0.0, 15.0), (15.0, 30.0)],
        )
        source_cell = upstream[1]
        self.assertIn(connector[0]["id"], source_cell["downstream_cell_ids"])
        self.assertIn(source_cell["id"], connector[0]["upstream_cell_ids"])
        self.assertIn(downstream[1]["id"], connector[-1]["downstream_cell_ids"])
        self.assertIn(connector[-1]["id"], downstream[1]["upstream_cell_ids"])
        self.assertTrue(all(cell["length_m"] > 0.0 for cell in manifest["cells"]))
        self.assertTrue(all(cell["storage_veh"] > 0.0 for cell in manifest["cells"]))

    def test_connector_lane_groups_and_permitted_network_references(self):
        directory, _, manifest = self.compile_fixture()
        self.addCleanup(directory.cleanup)
        connector = manifest["connectors"][0]
        self.assertEqual(connector["lanes"][0]["id"], "lane:100:1")
        self.assertEqual(connector["connector_lane_group_ids"], ["lg:link:100:lane:1"])
        self.assertIn(
            "lg:link:100:lane:1",
            {group["id"] for group in manifest["lane_groups"]},
        )
        decision = next(item for item in manifest["routing_decisions"] if item["vissim_no"] == "8")
        self.assertEqual(decision["link_id"], "connector:100")
        route = next(item for item in manifest["routes"] if item["decision_id"] == decision["id"])
        self.assertEqual(route["destination_link_id"], "connector:100")
        self.assertEqual(route["link_sequence_ids"], ["connector:100"])
        data_point = next(item for item in manifest["data_collection_points"] if item["vissim_no"] == "2")
        self.assertEqual(data_point["lane_ref"]["lane_group_id"], "lg:link:100:lane:1")
        queue_counter = next(item for item in manifest["queue_counters"] if item["vissim_no"] == "2")
        self.assertEqual(queue_counter["link_id"], "connector:100")
        connector_gate = next(gate for gate in manifest["signal_gates"] if gate["signal_head_id"] == "signal-head:502")
        self.assertEqual(connector_gate["controlled_movement_ids"], ["movement:100"])
        self.assertEqual(
            manifest["defaults"]["modeling_resolution"]["lane_grouping"],
            "individual_vissim_lane",
        )
        self.assertFalse(
            manifest["defaults"]["modeling_resolution"]["true_lane_grouping_inferred"]
        )
        movement = manifest["movements"][0]
        self.assertIsNone(movement["turn_ratio"])
        self.assertIsNone(movement["capacity_vehps"])
        self.assertIsNone(movement["priority"])
        self.assertEqual(
            {gap["parameter"] for gap in movement["parameter_gaps"]},
            {"turn_ratio", "capacity_vehps", "priority"},
        )
        interface = manifest["freeway_interface_candidates"][0]
        self.assertEqual(interface["status"], "classification_required")
        self.assertEqual(interface["movement_id"], movement["id"])
        self.assertTrue(manifest["validation_report"]["valid"])

    def test_cfl_warning_is_reported_without_invalidating_topology(self):
        directory, _, manifest = self.compile_fixture()
        self.addCleanup(directory.cleanup)
        cfl_warnings = [
            warning
            for warning in manifest["validation_report"]["warnings"]
            if warning["code"] == "cfl_reference_dt_exceeds_cell_travel_time"
        ]
        self.assertTrue(cfl_warnings)
        warned_cell = next(
            cell for cell in manifest["cells"] if cell["id"] == cfl_warnings[0]["entity_id"]
        )
        self.assertFalse(warned_cell["cfl"]["reference_dt_satisfies_free_flow_cfl"])
        self.assertEqual(warned_cell["cfl"]["backward_wave_status"], "calibration_required")
        self.assertTrue(manifest["validation_report"]["valid"])

    def test_unresolved_movement_value_requires_explicit_parameter_gap(self):
        directory, _, manifest = self.compile_fixture()
        self.addCleanup(directory.cleanup)
        invalid = copy.deepcopy(manifest)
        invalid["movements"][0]["parameter_gaps"] = []
        invalid.pop("validation_report", None)
        invalid.pop("topology_hash", None)
        report = validate_topology(invalid)
        self.assertFalse(report["valid"])
        self.assertIn(
            "undeclared_movement_parameter_gap",
            {error["code"] for error in report["errors"]},
        )

    def test_controller_centered_subgraph_has_exclusive_and_boundary_ownership(self):
        directory, _, manifest = self.compile_fixture()
        self.addCleanup(directory.cleanup)
        subgraphs = _build_influence_subgraphs(
            manifest["cells"],
            manifest["signal_gates"],
            controlled_uf_to_sc=((99, "10"),),
        )
        self.assertEqual(len(subgraphs), 1)
        subgraph = subgraphs[0]
        self.assertEqual(subgraph["controller_id"], "sc:10")
        self.assertTrue(subgraph["seed_cell_ids"])
        self.assertTrue(subgraph["owned_cell_ids"])
        self.assertEqual(
            subgraph["vehicle_ownership"]["owned_cell_ids"],
            subgraph["owned_cell_ids"],
        )
        self.assertTrue(subgraph["vehicle_ownership"]["boundary"])
        self.assertTrue(
            all(
                item["external_vehicle_owner_kind"] == "frozen_boundary_trajectory"
                for item in subgraph["vehicle_ownership"]["boundary"]
            )
        )
        self.assertEqual(
            set(subgraph["action_enabled_gate_ids"]),
            set(subgraph["owned_gate_ids"]),
        )

    def test_manifest_and_hash_are_deterministic(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "fixture.inpx"
        path.write_text(SYNTHETIC_INPX, encoding="utf-8")
        first = compile_inpx(path)
        second = compile_inpx(path)
        self.assertEqual(first, second)
        self.assertEqual(first["topology_hash"], second["topology_hash"])

    def test_invalid_connector_reference_is_reported(self):
        directory, _, manifest = self.compile_fixture()
        self.addCleanup(directory.cleanup)
        invalid = copy.deepcopy(manifest)
        invalid["connectors"][0]["to_endpoint"]["link_no"] = "999"
        invalid.pop("validation_report", None)
        invalid.pop("topology_hash", None)
        report = validate_topology(invalid)
        self.assertFalse(report["valid"])
        self.assertIn("dangling_link_ref", {error["code"] for error in report["errors"]})

    def test_broken_connector_cell_adjacency_is_reported(self):
        directory, _, manifest = self.compile_fixture()
        self.addCleanup(directory.cleanup)
        invalid = copy.deepcopy(manifest)
        source_cell = next(
            cell
            for cell in invalid["cells"]
            if cell["lane_group_id"] == "lg:link:1:lane:1"
            and cell["end_position_m"] == 80.0
        )
        connector_cell_id = next(
            cell["id"]
            for cell in invalid["cells"]
            if cell["lane_group_id"] == "lg:link:100:lane:1"
            and cell["ordered_index"] == 0
        )
        source_cell["downstream_cell_ids"].remove(connector_cell_id)
        invalid.pop("validation_report", None)
        invalid.pop("topology_hash", None)
        report = validate_topology(invalid)
        self.assertFalse(report["valid"])
        self.assertIn(
            "missing_connector_upstream_adjacency",
            {error["code"] for error in report["errors"]},
        )


if __name__ == "__main__":
    unittest.main()
