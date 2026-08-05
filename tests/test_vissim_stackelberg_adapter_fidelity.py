from __future__ import annotations

import unittest
from types import SimpleNamespace

from evaluation.controllers import vissim_stackelberg_adapter as adapter


class PlantFidelityProjectionTests(unittest.TestCase):
    def test_projection_diagnostics_expose_clipping_and_unrepresented_mass(self) -> None:
        network = SimpleNamespace(
            urban_link_storage_veh={"S1": 10.0},
            off_ramp_storage_link={},
            urban_movements={"M1": {}},
            ramps=["R1"],
        )
        cfg = SimpleNamespace(network=network)
        state_json = {
            "local_observation": {
                "link_counts": {"L1": 8, "L2": 20, "L3": 3, "L4": 2, "L5": 5},
                "link_speeds_kph": {"L1": 20, "L2": 10, "L3": 0, "L4": 15, "L5": 80},
                "link_stopped_counts": {"L1": 2, "L2": 12, "L3": 3},
                "link_queue_tail_pos_m": {"L1": 80, "L2": 25},
            }
        }
        mapping = {
            "link_to_origins": {"L1": ["S1"], "L2": ["S1"]},
            "link_to_movements": {"L1": [{"movement": "M1", "weight": 1.0}]},
            "ramp_link_to_queues": {"L4": ["R1"]},
            "freeway_link_to_model_link": {"L5": "FW_E"},
            "agents": {"U1": {"visible_links": ["L1", "L2", "L3"]}},
        }
        calibration = {
            "observation": {
                "internal_storage_fraction": 0.5,
                "offramp_storage_fraction": 0.5,
            }
        }

        summary = adapter.build_local_observation_summary(
            state_json,
            cfg,
            mapping,
            calibration,
        )
        diagnostics = summary["projection_diagnostics"]

        self.assertEqual(summary["link_speeds_kph"]["L5"], 80.0)
        self.assertEqual(summary["agents"]["U1"]["link_stopped_counts"]["L2"], 12.0)
        self.assertEqual(summary["agents"]["U1"]["link_queue_tail_pos_m"]["L2"], 25.0)
        self.assertAlmostEqual(summary["urban_movement_queue"]["M1"], 4.0)
        self.assertAlmostEqual(summary["urban_link_storage_occupancy"]["S1"], 10.0)
        self.assertAlmostEqual(diagnostics["input_link_vehicle_count_veh"], 38.0)
        self.assertAlmostEqual(diagnostics["storage_assigned_veh"], 10.0)
        self.assertAlmostEqual(diagnostics["storage_capacity_clipped_veh"], 14.0)
        self.assertAlmostEqual(diagnostics["movement_queue_assigned_veh"], 4.0)
        self.assertAlmostEqual(diagnostics["represented_vehicle_count_veh"], 21.0)
        self.assertAlmostEqual(diagnostics["unrepresented_vehicle_count_veh"], 17.0)
        self.assertAlmostEqual(diagnostics["mass_balance_error_veh"], 17.0)
        self.assertEqual(summary["unrepresented_by_link"], {"L2": 14.0, "L3": 3.0})

    def test_run_provenance_marks_missing_inputs(self) -> None:
        missing = adapter.WORKSPACE_ROOT / "__missing_plant_fidelity_input__"
        provenance = adapter.build_run_provenance(
            repo_root=adapter.WORKSPACE_ROOT / "vendor" / "NumSim-mine",
            state_json={},
            state_path=missing,
            mapping_path=missing,
            detector_mapping_path=missing,
            calibration_path=missing,
            tuning_path=missing,
        )

        self.assertTrue(provenance["workspace_git_commit"])
        self.assertEqual(provenance["numsim_snapshot_commit"], "35a5c82")
        self.assertEqual(provenance["numsim_git_commit"], "")
        self.assertEqual(provenance["schema_version"], 2)
        self.assertFalse(provenance["inputs"]["state_json"]["exists"])
        self.assertEqual(provenance["inputs"]["state_json"]["sha256"], "")


if __name__ == "__main__":
    unittest.main()
