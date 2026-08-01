from __future__ import annotations

import math
import unittest

from src.vissim_strict.hybrid import (
    FreewayNetworkParameters,
    FreewaySegmentParameters,
    MainlineConnection,
    OffRampInterface,
    OnRampInterface,
    StrictHybridPlant,
    kph_to_mps,
    mps_to_kph,
    veh_per_hour_to_vehps,
    veh_per_km_lane_to_veh_per_m_lane,
    veh_per_m_lane_to_veh_per_km_lane,
    vehps_to_veh_per_hour,
)
from src.vissim_strict.schema import (
    DemandEntry,
    DemandSchedule,
    LaneLoss,
    PlantState,
    SchemaError,
    StepAction,
    StepStatus,
    VehicleStock,
)


TOPOLOGY_HASH = "hybrid-test-topology"


def segment() -> FreewaySegmentParameters:
    return FreewaySegmentParameters(
        length_m=500.0,
        lane_count=1.0,
        v_free_mps=20.0,
        w_mps=5.0,
        rho_critical_veh_per_m_lane=0.05,
        rho_jam_veh_per_m_lane=0.20,
        q_max_vehps_per_lane=1.5,
        tau_sec=10.0,
    )


def demand(end: float = 30.0) -> DemandSchedule:
    return DemandSchedule(
        schedule_id="demand",
        topology_hash=TOPOLOGY_HASH,
        start_time_sec=0.0,
        end_time_sec=end,
        interval_sec=end,
        entries=(DemandEntry(0.0, end, {}),),
    )


def lane_loss_demand(lanes_closed: float) -> DemandSchedule:
    return DemandSchedule(
        schedule_id="lane-loss",
        topology_hash=TOPOLOGY_HASH,
        start_time_sec=0.0,
        end_time_sec=30.0,
        interval_sec=30.0,
        entries=(
            DemandEntry(
                0.0,
                30.0,
                {},
                freeway_lane_loss=(LaneLoss("f1", lanes_closed, 0.0, 30.0),),
            ),
        ),
    )


def parameters(*, on_ramp: bool = False, off_ramp: bool = False) -> FreewayNetworkParameters:
    return FreewayNetworkParameters(
        topology_hash=TOPOLOGY_HASH,
        dt_sec=1.0,
        segments={"f1": segment(), "f2": segment()},
        mainline_connections=(
            MainlineConnection("f1-f2", "f1", "f2", 0.75 if off_ramp else 1.0),
        ),
        on_ramps=(OnRampInterface("ramp-1", "stock:ramp", "f2", 1.0),) if on_ramp else (),
        off_ramps=(
            OffRampInterface("off-1", "f1", "stock:off", 0.25, 1.0, 20.0),
        ) if off_ramp else (),
    )


def state(
    f1: dict[str, float] | None = None,
    f2: dict[str, float] | None = None,
    *,
    ramp: dict[str, float] | None = None,
    off: dict[str, float] | None = None,
    speed: float = 20.0,
) -> PlantState:
    f1 = {"car": 20.0} if f1 is None else f1
    f2 = {"car": 0.0} if f2 is None else f2
    stocks = [
        VehicleStock("stock:f1", "freeway_segment", "f1", sum(f1.values()), f1),
        VehicleStock("stock:f2", "freeway_segment", "f2", sum(f2.values()), f2),
    ]
    ramp_refs = {}
    off_refs = {}
    if ramp is not None:
        stocks.append(VehicleStock("stock:ramp", "ramp_queue", "ramp-1", sum(ramp.values()), ramp))
        ramp_refs["ramp-1"] = "stock:ramp"
    if off is not None:
        stocks.append(VehicleStock("stock:off", "off_ramp_storage", "off-1", sum(off.values()), off))
        off_refs["off-1"] = "stock:off"
    return PlantState(
        topology_hash=TOPOLOGY_HASH,
        sim_time_sec=0.0,
        stocks=tuple(stocks),
        urban_cell_stock_id={},
        freeway_segment_stock_id={"f1": "stock:f1", "f2": "stock:f2"},
        ramp_queue_stock_id=ramp_refs,
        off_ramp_storage_stock_id=off_refs,
        freeway_speed_mps={"f1": speed, "f2": speed},
    )


def action(current: PlantState, *, vsl=None, meter=None, valid_until=30.0) -> StepAction:
    vsl = {} if vsl is None else vsl
    meter = {} if meter is None else meter
    return StepAction(
        action_id="a",
        topology_hash=TOPOLOGY_HASH,
        based_on_state_hash=current.state_hash,
        decision_time_sec=current.sim_time_sec,
        valid_from_sec=0.0,
        valid_until_sec=valid_until,
        vsl_mps=vsl,
        ramp_metering_vehps=meter,
        authority_ids=tuple(sorted(set(vsl) | set(meter))),
    )


class StrictHybridTests(unittest.TestCase):
    def test_two_segment_metanet_pulse(self) -> None:
        initial = state()
        result = StrictHybridPlant(parameters()).step(initial, None, demand(), 1.0)
        self.assertEqual(result.status, StepStatus.OK)
        assert result.next_state is not None
        after = result.next_state.stock_by_id()
        moved = after["stock:f2"].vehicle_count_veh
        self.assertGreater(moved, 0.0)
        self.assertAlmostEqual(after["stock:f1"].vehicle_count_veh, 20.0 - moved)
        self.assertTrue(result.diagnostics.no_clamp_delete)

    def test_vsl_reduces_same_step_sending(self) -> None:
        initial = state()
        plant = StrictHybridPlant(parameters())
        free = plant.step(initial, None, demand(), 1.0)
        limited = plant.step(initial, action(initial, vsl={"f1": 5.0}), demand(), 1.0)
        self.assertEqual(limited.status, StepStatus.OK)
        free_f2 = free.next_state.stock_by_id()["stock:f2"].vehicle_count_veh
        limited_f2 = limited.next_state.stock_by_id()["stock:f2"].vehicle_count_veh
        self.assertLess(limited_f2, free_f2)

    def test_ramp_metering_and_exact_interface_transaction(self) -> None:
        initial = state(f1={"car": 0.0}, ramp={"car": 5.0, "truck": 5.0})
        plant = StrictHybridPlant(parameters(on_ramp=True))
        result = plant.step(initial, action(initial, meter={"ramp-1": 0.3}), demand(), 1.0)
        self.assertEqual(result.status, StepStatus.OK)
        after = result.next_state.stock_by_id()
        source_decrement = 10.0 - after["stock:ramp"].vehicle_count_veh
        target_increment = after["stock:f2"].vehicle_count_veh
        flow = dict(dict(result.diagnostics.interface_transfer_by_class_veh)["ramp-1"])
        self.assertAlmostEqual(source_decrement, 0.3)
        self.assertAlmostEqual(source_decrement, target_increment)
        self.assertAlmostEqual(source_decrement, sum(flow.values()))
        self.assertAlmostEqual(flow["car"], flow["truck"])
        self.assertEqual(flow, dict(after["stock:f2"].class_counts_veh))

    def test_off_ramp_split_is_conserved_by_class(self) -> None:
        initial = state(f1={"car": 12.0, "truck": 8.0}, off={"car": 0.0, "truck": 0.0})
        result = StrictHybridPlant(parameters(off_ramp=True)).step(initial, None, demand(), 1.0)
        self.assertEqual(result.status, StepStatus.OK)
        after = result.next_state.stock_by_id()
        flow = dict(dict(result.diagnostics.interface_transfer_by_class_veh)["off-1"])
        self.assertAlmostEqual(after["stock:off"].vehicle_count_veh, sum(flow.values()))
        self.assertAlmostEqual(flow["car"] / flow["truck"], 12.0 / 8.0)
        self.assertAlmostEqual(result.next_state.total_vehicle_inventory(), initial.total_vehicle_inventory())

    def test_blocked_downstream_retains_vehicles(self) -> None:
        initial = state(f1={"car": 20.0}, f2={"car": 100.0})
        result = StrictHybridPlant(parameters()).step(initial, None, demand(), 1.0)
        self.assertEqual(result.status, StepStatus.OK)
        after = result.next_state.stock_by_id()
        self.assertAlmostEqual(after["stock:f1"].vehicle_count_veh, 20.0)
        self.assertAlmostEqual(after["stock:f2"].vehicle_count_veh, 100.0)

    def test_lane_loss_reduces_capacity_without_deleting_stock(self) -> None:
        initial = state(f1={"car": 40.0})
        plant = StrictHybridPlant(parameters())
        baseline = plant.step(initial, None, demand(), 1.0)
        lane_loss = plant.step(initial, None, lane_loss_demand(0.5), 1.0)
        self.assertEqual(lane_loss.status, StepStatus.OK)
        baseline_flow = baseline.next_state.stock_by_id()["stock:f2"].vehicle_count_veh
        reduced_flow = lane_loss.next_state.stock_by_id()["stock:f2"].vehicle_count_veh
        self.assertLess(reduced_flow, baseline_flow)
        self.assertAlmostEqual(
            lane_loss.next_state.total_vehicle_inventory(), initial.total_vehicle_inventory()
        )

    def test_total_and_class_mass_over_multiple_steps(self) -> None:
        current = state(f1={"car": 12.0, "truck": 8.0}, f2={"car": 3.0, "truck": 2.0})
        baseline = current.inventory_by_class()
        plant = StrictHybridPlant(parameters())
        for _ in range(10):
            result = plant.step(current, None, demand(), 1.0)
            self.assertEqual(result.status, StepStatus.OK)
            self.assertLessEqual(abs(result.diagnostics.mass_residual_veh), 1.0e-6)
            self.assertTrue(result.diagnostics.no_clamp_delete)
            current = result.next_state
        for class_id, value in baseline.items():
            self.assertAlmostEqual(current.inventory_by_class()[class_id], value, places=9)

    def test_stability_validation_rejects_oversized_step(self) -> None:
        with self.assertRaises(SchemaError):
            FreewayNetworkParameters(
                topology_hash=TOPOLOGY_HASH,
                dt_sec=30.0,
                segments={"f1": segment()},
            )

    def test_advance_interval_is_pure_and_exact(self) -> None:
        initial = state()
        result = StrictHybridPlant(parameters()).advance_interval(initial, None, demand(), 3.0)
        self.assertEqual(result.status, StepStatus.OK)
        self.assertEqual(result.completed_horizon_sec, 3.0)
        self.assertEqual(result.next_state.sim_time_sec, 3.0)
        self.assertEqual(initial.sim_time_sec, 0.0)

    def test_si_round_trips(self) -> None:
        self.assertAlmostEqual(mps_to_kph(kph_to_mps(90.0)), 90.0)
        self.assertAlmostEqual(vehps_to_veh_per_hour(veh_per_hour_to_vehps(1800.0)), 1800.0)
        density = veh_per_km_lane_to_veh_per_m_lane(35.0)
        self.assertAlmostEqual(veh_per_m_lane_to_veh_per_km_lane(density), 35.0)
        self.assertTrue(math.isfinite(density))


if __name__ == "__main__":
    unittest.main()
