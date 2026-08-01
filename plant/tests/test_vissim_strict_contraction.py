from __future__ import annotations

import copy
import unittest

from src.vissim_strict.contraction import contract_topology


def cell(cell_id, group, start, end, upstream=(), downstream=(), *, link="1", lane=1, speed=10.0):
    length = end - start
    return {
        "id": cell_id,
        "lane_group_id": group,
        "start_position_m": start,
        "end_position_m": end,
        "length_m": length,
        "lanes": [f"lane:{link}:{lane}"],
        "storage_veh": length / 7.5,
        "minimum_travel_time_sec": length / speed,
        "upstream_cell_ids": list(upstream),
        "downstream_cell_ids": list(downstream),
        "parameter_placeholders": {"v_free_mps": speed},
        "source": {"kind": "derived.cell", "vissim_no": link, "lane_no": lane},
    }


def manifest(cells, **extra):
    value = {
        "cells": cells,
        "movements": [],
        "signal_gates": [],
        "routing_decisions": [],
        "routes": [],
        "boundaries": [],
        "observation_operators": [],
        "freeway_interface_candidates": [],
        "influence_subgraphs": [],
    }
    value.update(extra)
    return value


class ContractionGoldenTests(unittest.TestCase):
    def test_serial_cells_collapse_deterministically(self):
        cells = [
            cell("a", "lg:link:1:lane:1", 0, 10, downstream=("b",)),
            cell("b", "lg:link:1:lane:1", 10, 20, upstream=("a",), downstream=("c",)),
            cell("c", "lg:link:1:lane:1", 20, 30, upstream=("b",)),
        ]
        first = contract_topology(manifest(cells))
        second = contract_topology(copy.deepcopy(manifest(list(reversed(cells)))))
        self.assertEqual(1, len(first["hydraulic_cells"]))
        self.assertEqual(["a", "b", "c"], first["hydraulic_cells"][0]["raw_cell_ids"])
        self.assertEqual(first["contraction_report"]["hydraulic_hash"], second["contraction_report"]["hydraulic_hash"])

    def test_signal_gate_and_branch_are_not_crossed(self):
        cells = [
            cell("a", "lg:link:1:lane:1", 0, 15, downstream=("b",)),
            cell("b", "lg:link:1:lane:1", 15, 30, upstream=("a",), downstream=("c", "d")),
            cell("c", "lg:link:1:lane:1", 30, 45, upstream=("b",)),
            cell("d", "lg:link:2:lane:1", 0, 15, upstream=("b",), link="2"),
        ]
        gate = {"id": "g", "lane_group_id": "lg:link:1:lane:1", "position_m": 15.0}
        result = contract_topology(manifest(cells, signal_gates=[gate]))
        mapped = result["raw_to_hydraulic"]
        self.assertNotEqual(mapped["a"]["id"], mapped["b"]["id"])
        self.assertNotEqual(mapped["b"]["id"], mapped["c"]["id"])
        self.assertNotEqual(mapped["b"]["id"], mapped["d"]["id"])

    def test_short_connector_becomes_stockless_transfer(self):
        cells = [
            cell("road-up", "lg:link:1:lane:1", 0, 20, downstream=("connector",)),
            cell("connector", "lg:link:100:lane:1", 0, 5, upstream=("road-up",), downstream=("road-down",), link="100"),
            cell("road-down", "lg:link:2:lane:1", 0, 20, upstream=("connector",), link="2"),
        ]
        candidate = {"id": "fi:100", "connector_ids": ["connector:100"]}
        result = contract_topology(manifest(cells, freeway_interface_candidates=[candidate]))
        self.assertEqual(1, len(result["transfer_edges"]))
        edge = result["transfer_edges"][0]
        self.assertEqual(["connector"], edge["raw_cell_ids"])
        self.assertFalse(edge["owns_vehicles"])
        self.assertEqual("transfer_edge", result["raw_to_hydraulic"]["connector"]["kind"])
        self.assertEqual(2, len(result["hydraulic_cells"]))

    def test_parallel_lanes_never_share_vehicle_stock(self):
        cells = [
            cell("l1a", "lg:link:1:lane:1", 0, 10, downstream=("l1b",), lane=1),
            cell("l1b", "lg:link:1:lane:1", 10, 20, upstream=("l1a",), lane=1),
            cell("l2a", "lg:link:1:lane:2", 0, 10, downstream=("l2b",), lane=2),
            cell("l2b", "lg:link:1:lane:2", 10, 20, upstream=("l2a",), lane=2),
        ]
        result = contract_topology(manifest(cells))
        self.assertEqual(2, len(result["hydraulic_cells"]))
        self.assertNotEqual(result["raw_to_hydraulic"]["l1a"]["id"], result["raw_to_hydraulic"]["l2a"]["id"])

    def test_accounting_mapping_and_reachability_are_exact(self):
        cells = [
            cell("a", "lg:link:1:lane:1", 0, 20, downstream=("x",)),
            cell("x", "lg:link:10:lane:1", 0, 5, upstream=("a",), downstream=("b",), link="10"),
            cell("b", "lg:link:2:lane:1", 0, 20, upstream=("x",), link="2"),
        ]
        result = contract_topology(manifest(cells))
        report = result["contraction_report"]
        self.assertTrue(report["valid"])
        self.assertAlmostEqual(0.0, report["length_residual_m"], places=9)
        self.assertAlmostEqual(0.0, report["storage_residual_veh"], places=9)
        self.assertEqual({"a", "x", "b"}, set(result["raw_to_hydraulic"]))
        self.assertTrue(report["anchor_reachability_preserved"])
        self.assertTrue(report["no_duplicate_vehicle_ownership"])
        elements = result["hydraulic_cells"] + result["transfer_edges"]
        self.assertEqual(3, sum(len(item["raw_cell_ids"]) for item in elements))


if __name__ == "__main__":
    unittest.main()
