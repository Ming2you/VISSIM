from __future__ import annotations

from dataclasses import dataclass, field, replace
from types import SimpleNamespace
import unittest

from src.vissim_strict.bridge import (
    BridgeError,
    StrictCouplingBridge,
    legacy_to_strict,
    strict_to_legacy,
)
from src.vissim_strict.schema import (
    ControlAction as StrictControlAction,
    DemandSchedule,
    PlantState,
    StepResult,
    StepStatus,
    VehicleStock,
)


TOPOLOGY_HASH = "a" * 64


@dataclass(eq=True)
class DemandStep:
    freeway_mainline: dict[str, float]
    urban_boundary: dict[str, float]
    ramp_arrival: dict[str, float]
    incident_capacity_factor: float = 1.0
    freeway_lane_loss: dict[str, dict[int, float]] = field(default_factory=dict)


@dataclass(eq=True)
class ControlAction:
    N_P_star: float
    N_UF_star: float
    ramp_metering: dict[str, float]
    vsl: dict[str, float]
    green_times: dict[str, float]
    offsets: dict[str, float]
    inflow_outflow_allocation: dict[str, float]
    infeasibility: dict[str, object] = field(default_factory=dict)
    diagnostics: dict[str, object] = field(default_factory=dict)


@dataclass
class TrafficState:
    freeway_density: dict[str, float]
    freeway_speed: dict[str, float]
    freeway_flow: dict[str, float]
    ramp_queue: dict[str, float]
    urban_queue: dict[str, float]
    boundary_queue: dict[str, float]
    time_sec: float = 0.0


def _cfg(n_uf_unit: str = "veh_per_hour") -> SimpleNamespace:
    return SimpleNamespace(
        simulation=SimpleNamespace(control_interval=180.0),
        network=SimpleNamespace(
            cycle_length=120.0,
            freeway_links=["FW_W"],
            ramps=["R_W"],
        ),
        leader=SimpleNamespace(N_UF_star_unit=n_uf_unit),
    )


def _strict_state(time_sec: float = 0.0) -> PlantState:
    return PlantState(
        topology_hash=TOPOLOGY_HASH,
        sim_time_sec=time_sec,
        stocks=(VehicleStock("stock:c1", "urban_cell", "c1", 3.0, {"default": 3.0}),),
        urban_cell_stock_id={"c1": "stock:c1"},
    )


def _legacy_state(time_sec: float = 0.0) -> TrafficState:
    return TrafficState(
        freeway_density={},
        freeway_speed={},
        freeway_flow={},
        ramp_queue={},
        urban_queue={"marker": 1.0},
        boundary_queue={},
        time_sec=time_sec,
    )


def _legacy_action() -> ControlAction:
    return ControlAction(
        N_P_star=321.5,
        N_UF_star=987.25,
        ramp_metering={"R_W": 1800.0},
        vsl={"FW_W": 72.0},
        green_times={"UF1_p1": 35.0, "UF1_p2": 45.0},
        offsets={"UF1": 17.5},
        inflow_outflow_allocation={"M1": 900.0},
        infeasibility={"slack": 2.0},
        diagnostics={"solver": "fixture"},
    )


def _legacy_demand() -> DemandStep:
    return DemandStep(
        freeway_mainline={"FW_W": 3600.0},
        urban_boundary={"B_N": 720.0},
        ramp_arrival={"R_W": 900.0},
        incident_capacity_factor=0.75,
        freeway_lane_loss={"FW_W": {1: 1.0}},
    )


class _StubPlant:
    topology_hash = TOPOLOGY_HASH

    def __init__(self) -> None:
        self.parameters = SimpleNamespace(urban_dt_sec=1.0, parameter_hash="params")
        self.calls: list[tuple[PlantState, StrictControlAction, DemandSchedule, float]] = []

    def step(
        self,
        state: PlantState,
        action: StrictControlAction,
        demand: DemandSchedule,
        dt_sec: float,
    ) -> StepResult:
        self.calls.append((state, action, demand, dt_sec))
        if action.based_on_state_hash != state.state_hash:
            return StepResult(
                StepStatus.INVALID_INPUT,
                None,
                None,
                "stale_action_state_hash",
                "stale",
                self.topology_hash,
                state.state_hash,
                action.action_hash,
                "params",
                demand.demand_hash,
                False,
                False,
                0.0,
            )
        next_state = replace(state, sim_time_sec=state.sim_time_sec + dt_sec, state_hash="")
        return StepResult(
            StepStatus.OK,
            next_state,
            None,
            None,
            None,
            self.topology_hash,
            state.state_hash,
            action.action_hash,
            "params",
            demand.demand_hash,
            True,
            True,
            dt_sec,
        )


class _FrozenPlant(_StubPlant):
    def step(
        self,
        state: PlantState,
        action: StrictControlAction,
        demand: DemandSchedule,
        dt_sec: float,
    ) -> StepResult:
        self.calls.append((state, action, demand, dt_sec))
        return StepResult(
            StepStatus.OK,
            state,
            None,
            None,
            None,
            self.topology_hash,
            state.state_hash,
            action.action_hash,
            "params",
            demand.demand_hash,
            True,
            True,
            dt_sec,
        )


class ConversionTests(unittest.TestCase):
    def test_action_round_trip_preserves_fields_and_units(self) -> None:
        legacy = _legacy_action()
        strict = legacy_to_strict(
            legacy,
            cfg=_cfg(),
            topology_hash=TOPOLOGY_HASH,
            based_on_state_hash="state-hash",
            start_time_sec=10.0,
            end_time_sec=190.0,
        )
        self.assertIsInstance(strict, StrictControlAction)
        self.assertEqual(dict(strict.ramp_metering_vehps), {"R_W": 0.5})
        self.assertEqual(dict(strict.vsl_mps), {"FW_W": 20.0})
        self.assertEqual(dict(strict.allocations), {"M1": 0.25})
        self.assertEqual(strict.legacy_intent.n_uf_star_unit, "veh_per_hour")
        plan = dict(strict.signal_plans)["UF1"]
        self.assertAlmostEqual(dict(plan.gate_green_fraction)["UF1_p1"], 35.0 / 120.0)
        self.assertEqual(dict(plan.metadata)["offset_actuation"], "intent_only")

        restored = strict_to_legacy(strict, cfg=_cfg(), control_action_factory=ControlAction)
        self.assertEqual(restored, legacy)

    def test_n_uf_control_interval_unit_round_trip(self) -> None:
        strict = legacy_to_strict(
            _legacy_action(),
            cfg=_cfg("veh_per_control_interval"),
            topology_hash=TOPOLOGY_HASH,
            based_on_state_hash="state-hash",
            start_time_sec=0.0,
            end_time_sec=180.0,
        )
        self.assertEqual(strict.legacy_intent.n_uf_star_unit, "veh_per_control_interval")
        self.assertEqual(
            strict_to_legacy(
                strict,
                cfg=_cfg("veh_per_control_interval"),
                control_action_factory=ControlAction,
            ),
            _legacy_action(),
        )

    def test_signal_phase_expands_to_multiple_physical_gates(self) -> None:
        strict = legacy_to_strict(
            _legacy_action(),
            cfg=_cfg(),
            topology_hash=TOPOLOGY_HASH,
            based_on_state_hash="state-hash",
            start_time_sec=10.0,
            end_time_sec=190.0,
            signal_mapping={
                "UF1": {"controller_id": "sc:1004", "command_ids": []},
                "UF1_p1": {
                    "controller_id": "sc:1004",
                    "command_ids": ["gate:head:1", "gate:head:2"],
                },
                "UF1_p2": {
                    "controller_id": "sc:1004",
                    "command_ids": ["gate:head:3"],
                },
            },
            signal_cycle_sec_by_controller={"sc:1004": 60.0},
        )
        plan = dict(strict.signal_plans)["sc:1004"]
        self.assertEqual(len(strict.signal_plans), 1)
        green = dict(plan.gate_green_fraction)
        self.assertEqual(set(green), {"gate:head:1", "gate:head:2", "gate:head:3"})
        self.assertEqual(green["gate:head:1"], green["gate:head:2"])
        self.assertAlmostEqual(green["gate:head:1"], 35.0 / 60.0)
        self.assertEqual(set(strict.authority_ids), set(green) | {"R_W", "FW_W", "M1"})

    def test_demand_round_trip_preserves_categories_units_and_lane_loss(self) -> None:
        legacy = _legacy_demand()
        strict = legacy_to_strict(
            legacy,
            cfg=_cfg(),
            topology_hash=TOPOLOGY_HASH,
            start_time_sec=20.0,
            end_time_sec=200.0,
        )
        self.assertIsInstance(strict, DemandSchedule)
        rates = strict.rates_for_interval(20.0, 200.0)
        self.assertEqual(rates["FW_W"]["default"], 1.0)
        self.assertEqual(rates["B_N"]["default"], 0.2)
        self.assertEqual(rates["R_W"]["default"], 0.25)
        self.assertEqual(strict.global_incident_capacity_factor, 0.75)
        self.assertEqual(strict_to_legacy(strict, cfg=_cfg(), demand_step_factory=DemandStep), legacy)


class StrictCouplingBridgeTests(unittest.TestCase):
    def test_strict_path_rebases_internal_steps_and_mutates_once(self) -> None:
        plant = _StubPlant()
        legacy = _legacy_state()
        initial = _strict_state()
        copy_calls: list[PlantState] = []

        def copy_back(target: TrafficState, source: PlantState) -> None:
            copy_calls.append(source)
            target.time_sec = source.sim_time_sec
            target.urban_queue["marker"] = source.total_vehicle_inventory()

        bridge = StrictCouplingBridge(
            mode="strict",
            plant=plant,
            projector=lambda _legacy, _previous: initial,
            copy_back=copy_back,
        )
        result = bridge(legacy, _legacy_action(), _legacy_demand(), _cfg(), end_time_sec=2.0)

        self.assertEqual(result.path, "strict")
        self.assertEqual(result.time_owner, "strict_kernel")
        self.assertEqual(len(result.step_results), 2)
        self.assertEqual(len(plant.calls), 2)
        self.assertEqual(len(copy_calls), 1)
        self.assertEqual(legacy.time_sec, 2.0)
        self.assertEqual(legacy.urban_queue["marker"], 3.0)
        self.assertEqual(plant.calls[0][1].based_on_state_hash, plant.calls[0][0].state_hash)
        self.assertEqual(plant.calls[1][1].based_on_state_hash, plant.calls[1][0].state_hash)

        second = bridge(legacy, _legacy_action(), _legacy_demand(), _cfg(), end_time_sec=3.0)
        self.assertEqual(second.strict_state.sim_time_sec, 3.0)
        self.assertEqual(len(copy_calls), 2)
        with self.assertRaisesRegex(BridgeError, "double-step"):
            bridge(legacy, _legacy_action(), _legacy_demand(), _cfg(), end_time_sec=3.0)
        self.assertEqual(len(copy_calls), 2)

    def test_stale_action_is_rejected_before_plant_or_copy_back(self) -> None:
        plant = _StubPlant()
        legacy = _legacy_state()
        initial = _strict_state()
        copy_calls: list[PlantState] = []
        stale = legacy_to_strict(
            _legacy_action(),
            cfg=_cfg(),
            topology_hash=TOPOLOGY_HASH,
            based_on_state_hash="stale-state-hash",
            start_time_sec=0.0,
            end_time_sec=1.0,
        )
        bridge = StrictCouplingBridge(
            mode="strict",
            plant=plant,
            copy_back=lambda _target, source: copy_calls.append(source),
        )
        with self.assertRaisesRegex(BridgeError, "stale action"):
            bridge(
                legacy,
                _legacy_action(),
                _legacy_demand(),
                _cfg(),
                end_time_sec=1.0,
                strict_state=initial,
                strict_action=stale,
            )
        self.assertEqual(plant.calls, [])
        self.assertEqual(copy_calls, [])
        self.assertEqual(legacy.time_sec, 0.0)

    def test_time_freeze_is_rejected_before_copy_back(self) -> None:
        plant = _FrozenPlant()
        legacy = _legacy_state()
        copy_calls: list[PlantState] = []
        bridge = StrictCouplingBridge(
            mode="strict",
            plant=plant,
            projector=lambda _legacy, _previous: _strict_state(),
            copy_back=lambda _target, source: copy_calls.append(source),
        )
        with self.assertRaisesRegex(BridgeError, "time freeze"):
            bridge(legacy, _legacy_action(), _legacy_demand(), _cfg(), end_time_sec=1.0)
        self.assertEqual(len(plant.calls), 1)
        self.assertEqual(copy_calls, [])
        self.assertEqual(legacy.time_sec, 0.0)

    def test_legacy_fallback_requires_explicit_mode(self) -> None:
        calls: list[float] = []

        def fallback(_state: TrafficState, _action: ControlAction, _demand: DemandStep, _cfg: object, end: float) -> str:
            calls.append(end)
            return "legacy-result"

        bridge = StrictCouplingBridge(mode="legacy", legacy_fallback=fallback)
        result = bridge(_legacy_state(), _legacy_action(), _legacy_demand(), _cfg(), end_time_sec=180.0)
        self.assertEqual(result.path, "legacy")
        self.assertEqual(result.time_owner, "legacy_kernel")
        self.assertEqual(result.legacy_result, "legacy-result")
        self.assertEqual(calls, [180.0])


if __name__ == "__main__":
    unittest.main()
