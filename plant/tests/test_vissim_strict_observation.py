from __future__ import annotations

import copy
import unittest

from src.vissim_strict.observation import (
    ObservationProjectionError,
    project_observation,
)
from src.vissim_strict.topology import canonical_json_sha256


def manifest():
    return {
        "topology_hash": "a" * 64,
        "cells": [
            {
                "id": "cell:link:1:lane:1:seg:0000",
                "lane_group_id": "lg:link:1:lane:1",
                "ordered_index": 0,
                "start_position_m": 0.0,
                "end_position_m": 50.0,
                "length_m": 50.0,
                "lane_count": 1,
                "lanes": ["lane:1:1"],
                "storage_veh": 10.0,
                "model_type": "ctm",
                "parameter_placeholders": {"v_free_mps": 20.0},
            },
            {
                "id": "cell:link:1:lane:1:seg:0001",
                "lane_group_id": "lg:link:1:lane:1",
                "ordered_index": 1,
                "start_position_m": 50.0,
                "end_position_m": 100.0,
                "length_m": 50.0,
                "lane_count": 1,
                "lanes": ["lane:1:1"],
                "storage_veh": 10.0,
                "model_type": "ctm",
                "parameter_placeholders": {"v_free_mps": 20.0},
            },
        ],
        "observation_operators": [
            {
                "id": "observation:data-collection:1",
                "kind": "data_collection_point",
                "lane_ref": {"lane_id": "lane:1:1"},
                "position_m": 25.0,
            },
            {
                "id": "observation:queue-counter:1",
                "kind": "queue_counter",
                "link_no": "1",
            },
            {
                "id": "observation:travel-time:1",
                "kind": "travel_time_measurement",
                "start": {"link_no": "1", "position_m": 0.0},
                "end": {"link_no": "1", "position_m": 100.0},
            },
        ],
        "signal_groups": [],
        "signal_controllers": [],
        "boundaries": [],
    }


def envelope(**updates):
    value = {
        "schema_version": "vissim-strict-raw-observation/v1",
        "observation_id": "obs-1",
        "network_hash": "a" * 64,
        "sim_time_sec": 120.0,
        "captured_interval": {"start_sec": 60.0, "end_sec": 120.0},
        "units": {},
        "detector_values": [],
        "signal_readback": [],
        "boundary_values": [],
    }
    value.update(updates)
    return value


def rehash_state(state):
    result = copy.deepcopy(state)
    payload = dict(result)
    payload.pop("state_hash", None)
    result["state_hash"] = canonical_json_sha256(payload)
    return result


class OracleProjectorTests(unittest.TestCase):
    def test_oracle_is_deterministic_and_has_exclusive_stocks(self):
        raw = envelope(
            cell_truth=[
                {
                    "cell_id": "cell:link:1:lane:1:seg:0001",
                    "vehicle_count_veh": 4.0,
                    "speed": 36.0,
                    "speed_unit": "km_per_hour",
                },
                {
                    "cell_id": "cell:link:1:lane:1:seg:0000",
                    "vehicle_count_veh": 2.0,
                    "speed_mps": 15.0,
                },
            ]
        )
        first = project_observation(manifest(), raw, mode="vissim_oracle")
        second = project_observation(manifest(), copy.deepcopy(raw), mode="vissim_oracle")
        self.assertEqual(first, second)
        self.assertEqual(first["state_hash"], second["state_hash"])
        self.assertEqual(len(first["stocks"]), 2)
        self.assertEqual(sum(item["vehicle_count_veh"] for item in first["stocks"].values()), 6.0)
        self.assertEqual(first["urban"]["speed_mps"]["cell:link:1:lane:1:seg:0001"], 10.0)

    def test_oracle_requires_every_cell_once(self):
        raw = envelope(
            cell_truth=[{
                "cell_id": "cell:link:1:lane:1:seg:0000",
                "vehicle_count_veh": 1.0,
                "speed_mps": 1.0,
            }]
        )
        with self.assertRaisesRegex(ObservationProjectionError, "incomplete"):
            project_observation(manifest(), raw, mode="vissim_oracle")


class DetectorProjectorTests(unittest.TestCase):
    def test_unit_conversion_and_bounded_reconstruction(self):
        raw = envelope(
            detector_values=[
                {
                    "detector_id": "d1",
                    "operator_id": "observation:data-collection:1",
                    "measurement_kind": "flow",
                    "value": 1800.0,
                    "unit": "veh_per_hour",
                    "observed_at_sec": 120.0,
                    "interval_start_sec": 60.0,
                    "interval_end_sec": 120.0,
                },
                {
                    "detector_id": "d1",
                    "operator_id": "observation:data-collection:1",
                    "measurement_kind": "speed",
                    "value": 36.0,
                    "unit": "km_per_hour",
                    "observed_at_sec": 120.0,
                    "interval_start_sec": 60.0,
                    "interval_end_sec": 120.0,
                },
                {
                    "detector_id": "q1",
                    "operator_id": "observation:queue-counter:1",
                    "measurement_kind": "queue_length",
                    "value": 0.075,
                    "unit": "km",
                    "observed_at_sec": 120.0,
                    "interval_start_sec": None,
                    "interval_end_sec": None,
                },
            ]
        )
        state = project_observation(manifest(), raw, mode="detector_realistic")
        upstream = state["stocks"]["stock:urban-cell:cell:link:1:lane:1:seg:0000"]
        downstream = state["stocks"]["stock:urban-cell:cell:link:1:lane:1:seg:0001"]
        self.assertAlmostEqual(upstream["vehicle_count_veh"], 2.5)
        self.assertAlmostEqual(downstream["vehicle_count_veh"], 10.0)
        self.assertAlmostEqual(state["urban"]["speed_mps"]["cell:link:1:lane:1:seg:0000"], 10.0)
        self.assertLessEqual(upstream["vehicle_count_veh"], 10.0)

    def test_missing_and_stale_masks_are_explicit(self):
        raw = envelope(
            detector_values=[{
                "detector_id": "d1",
                "operator_id": "observation:data-collection:1",
                "measurement_kind": "speed",
                "value": 10.0,
                "unit": "m_per_sec",
                "observed_at_sec": 60.0,
                "interval_start_sec": None,
                "interval_end_sec": None,
            }]
        )
        state = project_observation(
            manifest(), raw, mode="detector_realistic", config={"stale_after_sec": 30.0}
        )
        estimation = state["estimation"]
        self.assertTrue(estimation["stale_mask"]["observation:data-collection:1"])
        self.assertTrue(estimation["missing_mask"]["observation:queue-counter:1"])
        self.assertIn("missing_detector_data", estimation["fallback_flags"])
        self.assertIn("stale_detector_data", estimation["fallback_flags"])
        self.assertEqual(estimation["covariance"]["schema_version"], "diagonal-covariance/v1")

    def test_projection_is_independent_of_detector_record_order(self):
        records = [
            {
                "detector_id": "d1",
                "operator_id": "observation:data-collection:1",
                "measurement_kind": "occupancy",
                "value": 25.0,
                "unit": "percent",
                "observed_at_sec": 110.0,
                "interval_start_sec": None,
                "interval_end_sec": None,
            },
            {
                "detector_id": "d1",
                "operator_id": "observation:data-collection:1",
                "measurement_kind": "speed",
                "value": 8.0,
                "unit": "m_per_sec",
                "observed_at_sec": 115.0,
                "interval_start_sec": None,
                "interval_end_sec": None,
            },
        ]
        first = project_observation(manifest(), envelope(detector_values=records), mode="detector_realistic")
        second = project_observation(manifest(), envelope(detector_values=list(reversed(records))), mode="detector_realistic")
        self.assertEqual(first, second)

    def test_hidden_truth_and_oracle_previous_state_are_rejected(self):
        leaked = envelope(cell_truth=[])
        with self.assertRaisesRegex(ObservationProjectionError, "non-detector fields"):
            project_observation(manifest(), leaked, mode="detector_realistic")

        oracle = project_observation(
            manifest(),
            envelope(cell_truth={
                "cell:link:1:lane:1:seg:0000": {"vehicle_count_veh": 1.0, "speed_mps": 1.0},
                "cell:link:1:lane:1:seg:0001": {"vehicle_count_veh": 1.0, "speed_mps": 1.0},
            }),
            mode="vissim_oracle",
        )
        with self.assertRaisesRegex(ObservationProjectionError, "previous detector_realistic"):
            project_observation(
                manifest(), envelope(), previous_state=oracle, mode="detector_realistic"
            )

    def test_previous_detector_state_contract_rejects_cross_network_future_and_tampering(self):
        previous = project_observation(manifest(), envelope(), mode="detector_realistic")
        current = envelope(
            observation_id="obs-2",
            sim_time_sec=180.0,
            captured_interval={"start_sec": 120.0, "end_sec": 180.0},
        )

        accepted = project_observation(
            manifest(), current, previous_state=previous, mode="detector_realistic"
        )
        self.assertTrue(
            any(
                source.get("source") == "previous_estimate"
                for sources in accepted["estimation"]["provenance"].values()
                for source in sources
            )
        )

        mutations = []
        wrong_schema = copy.deepcopy(previous)
        wrong_schema["schema_version"] = "vissim-strict-plant-state/v999"
        mutations.append((wrong_schema, "schema_version"))

        wrong_topology = copy.deepcopy(previous)
        wrong_topology["topology_hash"] = "b" * 64
        mutations.append((wrong_topology, "topology_hash"))

        future = copy.deepcopy(previous)
        future["sim_time_sec"] = 9999.0
        mutations.append((future, "from the future"))

        corrupted = copy.deepcopy(previous)
        corrupted["urban"]["speed_mps"]["cell:link:1:lane:1:seg:0000"] = 999.0
        mutations.append((corrupted, "state_hash mismatch"))

        wrong_projector = copy.deepcopy(previous)
        wrong_projector["estimation"]["projector_version"] = "oracle-projector"
        mutations.append((rehash_state(wrong_projector), "projector_version"))

        for state, error in mutations:
            with self.subTest(error=error):
                with self.assertRaisesRegex(ObservationProjectionError, error):
                    project_observation(
                        manifest(), current, previous_state=state, mode="detector_realistic"
                    )

    def test_oracle_provenance_cannot_be_relabelled_as_detector_state(self):
        oracle = project_observation(
            manifest(),
            envelope(cell_truth={
                "cell:link:1:lane:1:seg:0000": {
                    "vehicle_count_veh": 1.0,
                    "speed_mps": 1.0,
                },
                "cell:link:1:lane:1:seg:0001": {
                    "vehicle_count_veh": 1.0,
                    "speed_mps": 1.0,
                },
            }),
            mode="vissim_oracle",
        )
        oracle["estimation"]["mode"] = "detector_realistic"
        oracle["estimation"]["projector_version"] = "vissim-strict-observation-projector/v1"
        disguised = rehash_state(oracle)
        current = envelope(
            observation_id="obs-2",
            sim_time_sec=180.0,
            captured_interval={"start_sec": 120.0, "end_sec": 180.0},
        )
        with self.assertRaisesRegex(ObservationProjectionError, "oracle-derived"):
            project_observation(
                manifest(), current, previous_state=disguised, mode="detector_realistic"
            )


if __name__ == "__main__":
    unittest.main()
