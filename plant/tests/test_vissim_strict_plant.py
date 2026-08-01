from __future__ import annotations

import unittest

from src.vissim_strict.plant import StrictPlant
from src.vissim_strict.contraction import contract_topology
from src.vissim_strict.schema import (
    ActionSchedule,
    ActionScheduleEntry,
    CellParameters,
    ControlAction,
    DemandEntry,
    DemandSchedule,
    LegacyIntent,
    PlantParameters,
    PlantState,
    SCHEMA_VERSION,
    SchemaError,
    SignalPlan,
    StepStatus,
    TransferEdgeSpec,
    VehicleStock,
)


TOPOLOGY_HASH = "synthetic-topology-v1"


def cell(cell_id: str, lane_group: str, index: int = 0) -> dict:
    return {
        "id": cell_id,
        "lane_group_id": lane_group,
        "link_id": f"link:{lane_group}",
        "ordered_index": index,
        "length_m": 10.0,
        "lane_count": 1,
        "lanes": [f"lane:{cell_id}"],
        "storage_veh": 10.0,
    }


def movement(movement_id: str, source: str, target: str, turn_ratio=None) -> dict:
    return {
        "id": movement_id,
        "source_cell_id": source,
        "target_cell_id": target,
        "source_lane_group_id": f"lg:{source}",
        "target_lane_group_id": f"lg:{target}",
        "turn_ratio": turn_ratio,
    }


def topology(cells, movements=(), boundaries=(), gates=(), groups=(), fixed=(), hydraulic_view=None) -> dict:
    result = {
        "schema_version": "fixture/v1",
        "topology_hash": TOPOLOGY_HASH,
        "cells": list(cells),
        "movements": list(movements),
        "boundaries": list(boundaries),
        "signal_gates": list(gates),
        "signal_groups": list(groups),
        "schedules": {"fixed": list(fixed), "controlled": [], "derived": []},
        "freeway_interfaces": [],
    }
    if hydraulic_view is not None:
        result["hydraulic_view"] = hydraulic_view
    return result


def parameters(
    cells,
    ratios=(),
    priorities=(),
    saturation=(),
    *,
    dt=1.0,
    v_free=5.0,
    w=5.0,
    qmax=1.0,
) -> PlantParameters:
    return PlantParameters(
        topology_hash=TOPOLOGY_HASH,
        cells={
            item["id"]: CellParameters(
                v_free_mps=v_free,
                w_mps=w,
                rho_jam_veh_per_m_lane=1.0,
                q_max_vehps=qmax,
            )
            for item in cells
        },
        urban_dt_sec=dt,
        movement_turn_ratios=dict(ratios),
        node_priorities=dict(priorities),
        saturation_flow_vehps=dict(saturation),
        provenance={"fixture": "unit-test"},
        uncertainty={"fixture": "none"},
        calibration_version="golden-v1",
    )


def state(cell_values, source_values=(), buffer_values=(), *, time_sec=0.0) -> PlantState:
    stocks = []
    cell_refs = {}
    source_refs = {}
    buffer_refs = {}
    for cell_id, counts in cell_values:
        stock_id = f"stock:cell:{cell_id}"
        stocks.append(VehicleStock(stock_id, "urban_cell", cell_id, sum(counts.values()), counts))
        cell_refs[cell_id] = stock_id
    for boundary_id, counts in source_values:
        stock_id = f"stock:source:{boundary_id}"
        stocks.append(VehicleStock(stock_id, "boundary_source_queue", boundary_id, sum(counts.values()), counts))
        source_refs[boundary_id] = stock_id
    for buffer_id, counts in buffer_values:
        stock_id = f"stock:buffer:{buffer_id}"
        stocks.append(VehicleStock(stock_id, "travel_time_buffer", buffer_id, sum(counts.values()), counts))
        buffer_refs[buffer_id] = stock_id
    return PlantState(
        topology_hash=TOPOLOGY_HASH,
        sim_time_sec=time_sec,
        stocks=tuple(stocks),
        urban_cell_stock_id=cell_refs,
        source_queue_stock_id=source_refs,
        travel_time_buffer_stock_id=buffer_refs,
    )


def demand(boundary_rates=(), *, start=0.0, end=30.0) -> DemandSchedule:
    return DemandSchedule(
        schedule_id="demand:fixture",
        topology_hash=TOPOLOGY_HASH,
        start_time_sec=start,
        end_time_sec=end,
        interval_sec=end - start,
        entries=(DemandEntry(start, end, dict(boundary_rates)),),
    )


def value(next_state: PlantState, cell_id: str) -> float:
    refs = dict(next_state.urban_cell_stock_id)
    return next_state.stock_by_id()[refs[cell_id]].vehicle_count_veh


class StrictPlantGoldenTests(unittest.TestCase):
    def test_fixed_red_and_controlled_green_gate_service(self):
        cells = [cell("a", "lg:a"), cell("b", "lg:b")]
        moves = [movement("m", "a", "b")]
        gates = [
            {
                "id": "gate:g",
                "signal_group_id": "sg:1:1",
                "controlled_movement_ids": ["m"],
                "fixed_green_fraction": 0.0,
            }
        ]
        plant = StrictPlant(
            topology(cells, moves, gates=gates),
            parameters(cells, ratios={"m": {"*": 1.0}}, saturation={"gate:g": 1.0, "m": 1.0}),
        )
        initial = state([("a", {"car": 4.0}), ("b", {"car": 0.0})])

        red = plant.step(initial, None, demand(), 1.0)
        self.assertEqual(red.status, StepStatus.OK)
        self.assertAlmostEqual(dict(red.diagnostics.movement_flow_veh)["m"], 0.0)

        plan = SignalPlan("plan:green", "sc:1", 0.0, gate_green_fraction={"gate:g": 1.0})
        action = ControlAction(
            schema_version=SCHEMA_VERSION,
            action_id="action:1",
            topology_hash=TOPOLOGY_HASH,
            based_on_state_hash=initial.state_hash,
            decision_time_sec=0.0,
            valid_from_sec=0.0,
            activation_boundary_sec=0.0,
            valid_until_sec=10.0,
            signal_plans={"sc:1": plan},
            authority_ids=("gate:g",),
        )
        green = plant.step(initial, action, demand(), 1.0)
        self.assertEqual(green.status, StepStatus.OK)
        self.assertAlmostEqual(dict(green.diagnostics.movement_flow_veh)["m"], 1.0)
        self.assertEqual(green.action_hash, action.action_hash)

    def test_fixed_timeline_uses_exact_green_overlap(self):
        cells = [cell("a", "lg:a"), cell("b", "lg:b")]
        moves = [movement("m", "a", "b")]
        gates = [{"id": "gate:g", "signal_group_id": "sg:1:1", "controlled_movement_ids": ["m"]}]
        groups = [{"id": "sg:1:1", "controller_id": "sc:1", "controller_no": "1", "sg_no": "1"}]
        fixed = [
            {
                "id": "fixed:1",
                "controller_id": "sc:1",
                "controller_offset_sec": 0.0,
                "program": {
                    "cycle_length_sec": 2.0,
                    "program_offset_sec": 0.0,
                    "sg_timelines": {
                        "1": {
                            "intervals": [
                                {"start_sec": 0.0, "end_sec": 0.5, "state": "RED"},
                                {"start_sec": 0.5, "end_sec": 1.0, "state": "GREEN"},
                                {"start_sec": 1.0, "end_sec": 2.0, "state": "RED"},
                            ]
                        }
                    },
                },
            }
        ]
        plant = StrictPlant(
            topology(cells, moves, gates=gates, groups=groups, fixed=fixed),
            parameters(cells, ratios={"m": {"*": 1.0}}, saturation={"gate:g": 2.0, "m": 2.0}, qmax=2.0),
        )
        initial = state([("a", {"car": 4.0}), ("b", {"car": 0.0})])
        result = plant.step(initial, None, demand(), 1.0)
        self.assertAlmostEqual(dict(result.diagnostics.movement_flow_veh)["m"], 1.0)

    def test_commodity_fifo_diverge_preserves_70_30(self):
        cells = [cell("a", "lg:a"), cell("b", "lg:b"), cell("c", "lg:c")]
        moves = [movement("left", "a", "b"), movement("right", "a", "c")]
        plant = StrictPlant(
            topology(cells, moves),
            parameters(cells, ratios={"left": {"car": 0.7}, "right": {"car": 0.3}}),
        )
        initial = state([("a", {"car": 10.0}), ("b", {"car": 0.0}), ("c", {"car": 0.0})])
        result = plant.step(initial, None, demand(), 1.0)
        flows = dict(result.diagnostics.movement_flow_veh)
        self.assertAlmostEqual(flows["left"], 0.7)
        self.assertAlmostEqual(flows["right"], 0.3)
        self.assertAlmostEqual(value(result.next_state, "a"), 9.0)

    def test_merge_priorities_share_downstream_supply(self):
        cells = [cell("a", "lg:a"), cell("b", "lg:b"), cell("c", "lg:c")]
        moves = [movement("major", "a", "c"), movement("minor", "b", "c")]
        plant = StrictPlant(
            topology(cells, moves),
            parameters(
                cells,
                ratios={"major": {"*": 1.0}, "minor": {"*": 1.0}},
                priorities={"major": 3.0, "minor": 1.0},
            ),
        )
        initial = state([("a", {"car": 10.0}), ("b", {"car": 10.0}), ("c", {"car": 8.0})])
        result = plant.step(initial, None, demand(), 1.0)
        flows = dict(result.diagnostics.movement_flow_veh)
        self.assertAlmostEqual(flows["major"], 0.75)
        self.assertAlmostEqual(flows["minor"], 0.25)

    def test_downstream_full_causes_spillback_without_clamp_delete(self):
        cells = [cell("a", "lg:a"), cell("b", "lg:b")]
        moves = [movement("m", "a", "b")]
        plant = StrictPlant(topology(cells, moves), parameters(cells, ratios={"m": {"*": 1.0}}))
        initial = state([("a", {"car": 5.0}), ("b", {"car": 10.0})])
        result = plant.step(initial, None, demand(), 1.0)
        self.assertEqual(result.status, StepStatus.OK)
        self.assertAlmostEqual(dict(result.diagnostics.movement_flow_veh)["m"], 0.0)
        self.assertAlmostEqual(value(result.next_state, "a"), 5.0)
        self.assertIn("b", result.diagnostics.spillback_cell_ids)
        self.assertTrue(result.diagnostics.no_clamp_delete)

    def test_source_queue_sink_ledger_and_multistep_class_mass(self):
        cells = [cell("a", "lg:a")]
        boundary_id = "boundary:source:1"
        boundaries = [{"id": boundary_id, "type": "source", "target_cell_id": "a"}]
        plant = StrictPlant(topology(cells, boundaries=boundaries), parameters(cells))
        current = state([("a", {"car": 0.0})], [(boundary_id, {"car": 0.0})])
        schedule = demand({boundary_id: {"car": 0.4, "bus": 0.2}})
        total_arrivals = 0.0
        total_exits = 0.0
        for _ in range(12):
            result = plant.step(current, None, schedule, 1.0)
            self.assertEqual(result.status, StepStatus.OK)
            self.assertLessEqual(abs(result.diagnostics.mass_residual_veh), 1.0e-9)
            self.assertTrue(all(abs(value) <= 1.0e-9 for _, value in result.diagnostics.mass_residual_by_class_veh))
            total_arrivals += result.diagnostics.external_demand_arrivals_veh
            total_exits += sum(value for _, value in result.diagnostics.sink_outflow_veh)
            current = result.next_state
        self.assertAlmostEqual(current.total_vehicle_inventory(), total_arrivals - total_exits)
        self.assertTrue(dict(current.cumulative_sink_outflow_veh))

    def test_deterministic_output_and_stale_action_rejection(self):
        cells = [cell("a", "lg:a")]
        plant = StrictPlant(topology(cells), parameters(cells))
        initial = state([("a", {"car": 2.0})])
        first = plant.step(initial, None, demand(), 1.0)
        second = plant.step(initial, None, demand(), 1.0)
        self.assertEqual(first.next_state.state_hash, second.next_state.state_hash)
        self.assertEqual(first.diagnostics, second.diagnostics)

        stale = ControlAction(
            schema_version=SCHEMA_VERSION,
            action_id="stale",
            topology_hash=TOPOLOGY_HASH,
            based_on_state_hash="old-state",
            decision_time_sec=0.0,
            valid_from_sec=0.0,
            activation_boundary_sec=0.0,
            valid_until_sec=2.0,
        )
        rejected = plant.step(initial, stale, demand(), 1.0)
        self.assertEqual(rejected.status, StepStatus.INVALID_INPUT)
        self.assertEqual(rejected.reason_code, "stale_action_state_hash")
        self.assertIsNone(rejected.next_state)

    def test_rejects_unresolved_turn_ratio_and_cfl_violation(self):
        cells = [cell("a", "lg:a"), cell("b", "lg:b")]
        moves = [movement("m", "a", "b", turn_ratio=None)]
        with self.assertRaisesRegex(SchemaError, "unresolved turn_ratio"):
            StrictPlant(topology(cells, moves), parameters(cells))
        with self.assertRaisesRegex(SchemaError, "CFL violation"):
            StrictPlant(topology([cell("a", "lg:a")]), parameters([cell("a", "lg:a")], dt=3.0))

    def test_public_action_schedule_preserves_contract_fields_and_hashes(self):
        initial = state([("a", {"car": 0.0})])
        plan = SignalPlan("plan:1", "sc:1", 5.0, gate_green_fraction={"gate:g": 0.5})
        action = ControlAction(
            schema_version=SCHEMA_VERSION,
            action_id="action:public",
            topology_hash=TOPOLOGY_HASH,
            based_on_state_hash=initial.state_hash,
            decision_time_sec=0.0,
            valid_from_sec=0.0,
            activation_boundary_sec=5.0,
            valid_until_sec=60.0,
            signal_plans={"sc:1": plan},
            ramp_metering_vehps={"ramp:1": 0.2},
            vsl_mps={"segment:1": 20.0},
            allocations={"movement:1": 0.7},
            legacy_intent=LegacyIntent(10.0, "veh", 300.0, "veh_per_hour", {"source": "legacy"}),
            authority_ids=("gate:g",),
        )
        schedule = ActionSchedule(
            schedule_id="schedule:1",
            control_interval_sec=30.0,
            prediction_horizon_steps=3,
            control_horizon_steps=1,
            move_blocking=True,
            activation_boundary_sec=5.0,
            entries=(ActionScheduleEntry(5.0, 35.0, action),),
        )
        self.assertTrue(action.action_hash)
        self.assertTrue(schedule.schedule_hash)
        self.assertEqual(dict(action.ramp_metering_vehps)["ramp:1"], 0.2)
        self.assertEqual(action.legacy_intent.n_uf_star_unit, "veh_per_hour")

    def test_external_hydraulic_contraction_preserves_serial_pulse_travel_and_mass(self):
        raw_cells = [cell("u1", "lg:u", 0), cell("u2", "lg:u", 1)]
        boundary_id = "boundary:source:pulse"
        boundaries = [{"id": boundary_id, "type": "source", "target_cell_id": "u1"}]
        uncontracted = StrictPlant(
            topology(raw_cells, boundaries=boundaries),
            parameters(raw_cells, v_free=10.0, w=10.0),
        )

        macro = {
            "id": "h:u",
            "lane_group_id": "hydraulic:lg:u",
            "link_id": "link:lg:u",
            "ordered_index": 0,
            "length_m": 20.0,
            "flow_length_m": 10.0,
            "lane_count": 1,
            "storage_veh": 20.0,
            "minimum_travel_time_sec": 2.0,
            "delay_buffer_steps": 2,
            "member_cell_ids": ["u1", "u2"],
            "preserved_anchor_ids": [boundary_id, "sink:u2"],
        }
        hydraulic_view = {
            "schema_version": "hydraulic-view/v1",
            "hydraulic_cells": [macro],
            "transfer_edges": [],
            "raw_cell_to_hydraulic_cell": {"u1": "h:u", "u2": "h:u"},
            "required_anchor_ids": [boundary_id, "sink:u2"],
            "preserved_anchor_ids": [boundary_id, "sink:u2"],
            "validation_report": {"valid": True},
        }
        contracted = StrictPlant(
            topology(raw_cells, boundaries=boundaries, hydraulic_view=hydraulic_view),
            parameters([macro], v_free=10.0, w=10.0),
        )
        self.assertTrue(contracted.uses_hydraulic_view)
        self.assertEqual(contracted.required_travel_time_buffer_ids, ("buffer:h:u:stage:0",))

        pulse = DemandSchedule(
            schedule_id="demand:pulse",
            topology_hash=TOPOLOGY_HASH,
            start_time_sec=0.0,
            end_time_sec=6.0,
            interval_sec=1.0,
            entries=(
                DemandEntry(0.0, 1.0, {boundary_id: {"car": 1.0}}),
                DemandEntry(1.0, 6.0, {boundary_id: {"car": 0.0}}),
            ),
        )
        raw_state = state(
            [("u1", {"car": 0.0}), ("u2", {"car": 0.0})],
            [(boundary_id, {"car": 0.0})],
        )
        hydraulic_state = state(
            [("h:u", {"car": 0.0})],
            [(boundary_id, {"car": 0.0})],
            [("buffer:h:u:stage:0", {"car": 0.0})],
        )
        raw_sink_flow = []
        hydraulic_sink_flow = []
        for _ in range(6):
            raw_result = uncontracted.step(raw_state, None, pulse, 1.0)
            hydraulic_result = contracted.step(hydraulic_state, None, pulse, 1.0)
            self.assertEqual(raw_result.status, StepStatus.OK)
            self.assertEqual(hydraulic_result.status, StepStatus.OK)
            raw_sink_flow.append(sum(value for _, value in raw_result.diagnostics.sink_outflow_veh))
            hydraulic_sink_flow.append(sum(value for _, value in hydraulic_result.diagnostics.sink_outflow_veh))
            self.assertAlmostEqual(
                raw_result.next_state.total_vehicle_inventory(),
                hydraulic_result.next_state.total_vehicle_inventory(),
            )
            raw_state = raw_result.next_state
            hydraulic_state = hydraulic_result.next_state
        self.assertEqual(raw_sink_flow, hydraulic_sink_flow)
        self.assertEqual(raw_sink_flow[:3], [0.0, 0.0, 1.0])

    def test_hydraulic_zero_storage_transfer_is_conservative(self):
        hydraulic_cells = [cell("h:a", "h:lg:a"), cell("h:b", "h:lg:b")]
        view = {
            "schema_version": "hydraulic-view/v1",
            "hydraulic_cells": hydraulic_cells,
            "transfer_edges": [
                {
                    "id": "transfer:a-b",
                    "source_hydraulic_cell_id": "h:a",
                    "target_hydraulic_cell_id": "h:b",
                    "kind": "zero_storage_transfer",
                    "turn_ratios": {"*": 1.0},
                    "minimum_travel_time_sec": 0.0,
                }
            ],
            "preserved_anchor_ids": [],
            "required_anchor_ids": [],
        }
        plant = StrictPlant(
            topology([], hydraulic_view=view),
            parameters(hydraulic_cells),
        )
        initial = state([("h:a", {"car": 2.0}), ("h:b", {"car": 0.0})])
        result = plant.step(initial, None, demand(), 1.0)
        self.assertEqual(result.status, StepStatus.OK)
        self.assertAlmostEqual(value(result.next_state, "h:a"), 1.0)
        self.assertAlmostEqual(value(result.next_state, "h:b"), 1.0)
        self.assertAlmostEqual(result.diagnostics.mass_residual_veh, 0.0)
        with self.assertRaisesRegex(SchemaError, "explicit hydraulic travel-time-buffer cell"):
            TransferEdgeSpec("delayed", "h:a", "h:b", minimum_travel_time_sec=1.1, delay_steps=2)

    def test_accepts_canonical_contraction_module_output_directly(self):
        raw_cells = [cell("r1", "lg:r", 0), cell("r2", "lg:r", 1)]
        raw_cells[0].update(
            start_position_m=0.0,
            end_position_m=10.0,
            downstream_cell_ids=["r2"],
            upstream_cell_ids=[],
            minimum_travel_time_sec=1.0,
            parameter_placeholders={"v_free_mps": 10.0},
            source={"kind": "derived.cell", "vissim_no": "1", "lane_no": 1},
        )
        raw_cells[1].update(
            start_position_m=10.0,
            end_position_m=20.0,
            downstream_cell_ids=[],
            upstream_cell_ids=["r1"],
            minimum_travel_time_sec=1.0,
            parameter_placeholders={"v_free_mps": 10.0},
            source={"kind": "derived.cell", "vissim_no": "1", "lane_no": 1},
        )
        boundary_id = "boundary:source:canonical"
        base = topology(raw_cells, boundaries=[{"id": boundary_id, "type": "source", "target_cell_id": "r1"}])
        contracted_fields = contract_topology(base, urban_dt_sec=1.0)
        base.update(contracted_fields)
        macro = contracted_fields["hydraulic_cells"][0]
        plant = StrictPlant(base, parameters([macro], v_free=10.0, w=10.0))
        self.assertTrue(plant.uses_hydraulic_view)
        macro_id = macro["id"]
        buffer_id = plant.required_travel_time_buffer_ids[0]
        initial = state(
            [(macro_id, {"car": 0.0})],
            [(boundary_id, {"car": 0.0})],
            [(buffer_id, {"car": 0.0})],
        )
        result = plant.step(initial, None, demand({boundary_id: {"car": 1.0}}), 1.0)
        self.assertEqual(result.status, StepStatus.OK)
        self.assertAlmostEqual(result.next_state.total_vehicle_inventory(), 1.0)

    def test_accepts_canonical_stockless_short_connector_transfer(self):
        def raw(raw_id, group, start, end, upstream, downstream, link):
            item = cell(raw_id, group)
            item.update(
                start_position_m=start,
                end_position_m=end,
                length_m=end - start,
                storage_veh=(end - start) / 7.5,
                upstream_cell_ids=list(upstream),
                downstream_cell_ids=list(downstream),
                minimum_travel_time_sec=(end - start) / 10.0,
                parameter_placeholders={"v_free_mps": 10.0},
                source={"kind": "derived.cell", "vissim_no": link, "lane_no": 1},
            )
            return item

        raw_cells = [
            raw("up", "lg:up", 0.0, 20.0, (), ("short",), "1"),
            raw("short", "lg:connector", 0.0, 5.0, ("up",), ("down",), "100"),
            raw("down", "lg:down", 0.0, 20.0, ("short",), (), "2"),
        ]
        base = topology(raw_cells)
        contracted = contract_topology(base, urban_dt_sec=1.0)
        self.assertEqual(len(contracted["transfer_edges"]), 1)
        base.update(contracted)
        plant = StrictPlant(base, parameters(contracted["hydraulic_cells"], v_free=10.0, w=10.0))
        up_id = contracted["raw_to_hydraulic"]["up"]["id"]
        down_id = contracted["raw_to_hydraulic"]["down"]["id"]
        buffer_values = [(buffer_id, {"car": 0.0}) for buffer_id in plant.required_travel_time_buffer_ids]
        initial = state(
            [(up_id, {"car": 1.0}), (down_id, {"car": 0.0})],
            buffer_values=buffer_values,
        )
        result = plant.step(initial, None, demand(), 1.0)
        self.assertEqual(result.status, StepStatus.OK)
        self.assertAlmostEqual(result.next_state.total_vehicle_inventory(), 1.0)
        self.assertAlmostEqual(value(result.next_state, up_id), 0.0)

    def test_advance_interval_has_exact_time_and_does_not_mutate_inputs(self):
        cells = [cell("a", "lg:a")]
        plant = StrictPlant(topology(cells), parameters(cells))
        initial = state([("a", {"car": 2.0})])
        schedule = demand()
        original_state_hash = initial.state_hash
        original_demand_hash = schedule.demand_hash
        result = plant.advance_interval(initial, None, schedule, 3.0)
        self.assertEqual(result.status, StepStatus.OK)
        self.assertEqual(result.next_state.sim_time_sec, 3.0)
        self.assertEqual(result.completed_horizon_sec, 3.0)
        self.assertLessEqual(abs(result.diagnostics.mass_residual_veh), 1.0e-9)
        self.assertEqual(initial.sim_time_sec, 0.0)
        self.assertEqual(initial.state_hash, original_state_hash)
        self.assertEqual(schedule.demand_hash, original_demand_hash)

    def test_rollout_batch_preserves_order_tie_break_and_early_abort_status(self):
        cells = [cell("a", "lg:a")]
        plant = StrictPlant(topology(cells), parameters(cells))
        initial = state([("a", {"car": 2.0})])
        schedule = demand()

        def candidate(action_id):
            return ControlAction(
                schema_version=SCHEMA_VERSION,
                action_id=action_id,
                topology_hash=TOPOLOGY_HASH,
                based_on_state_hash=initial.state_hash,
                decision_time_sec=0.0,
                valid_from_sec=0.0,
                activation_boundary_sec=0.0,
                valid_until_sec=10.0,
            )

        actions = (candidate("candidate:second-name"), candidate("candidate:first-name"))
        action_hashes = tuple(action.action_hash for action in actions)
        batch = plant.rollout_batch(initial, actions, schedule, 0.0, 2.0)
        self.assertEqual(batch.batch_status, StepStatus.OK)
        self.assertEqual(batch.selected_candidate_index, 0)
        self.assertEqual(tuple(item.candidate_index for item in batch.candidate_results), (0, 1))
        self.assertEqual(tuple(item.action_hash for item in batch.candidate_results), action_hashes)
        self.assertFalse(batch.fallback_required)
        self.assertEqual(initial.sim_time_sec, 0.0)
        self.assertEqual(tuple(action.action_hash for action in actions), action_hashes)

        aborted = plant.rollout_batch(initial, (actions[0],), schedule, 0.0, 3.0, abort_above=0.0)
        self.assertEqual(aborted.batch_status, StepStatus.PARTIAL)
        self.assertEqual(aborted.candidate_results[0].status, StepStatus.EARLY_ABORTED)
        self.assertFalse(aborted.candidate_results[0].is_feasible)
        self.assertTrue(aborted.fallback_required)

    def test_project_observation_oracle_wrapper_returns_schema_state(self):
        cells = [cell("a", "lg:a")]
        plant = StrictPlant(topology(cells), parameters(cells))
        observation = {
            "schema_version": "vissim-strict-raw-observation/v1",
            "observation_id": "oracle:1",
            "network_hash": TOPOLOGY_HASH,
            "sim_time_sec": 4.0,
            "captured_interval": {"start_sec": 3.0, "end_sec": 4.0},
            "units": {},
            "cell_truth": [{"cell_id": "a", "vehicle_count_veh": 3.0, "speed_mps": 4.0}],
            "signal_readback": [],
            "boundary_values": [],
        }
        projected = plant.project_observation(observation, mode="vissim_oracle")
        self.assertIsInstance(projected, PlantState)
        self.assertEqual(projected.sim_time_sec, 4.0)
        self.assertAlmostEqual(projected.total_vehicle_inventory(), 3.0)
        self.assertEqual(value(projected, "a"), 3.0)


if __name__ == "__main__":
    unittest.main()
