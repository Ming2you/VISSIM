from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True)
class GlobalState:
    sim_sec: float
    total_vehicles: int
    urban_vehicles: int
    freeway_vehicles: int
    ramp_vehicles: int
    boundary_vehicles: int
    other_vehicles: int
    mean_speed_kph: float
    stopped_vehicles: int


@dataclass(frozen=True)
class ControllerAction:
    sim_sec: float
    mode: str
    command: str
    metadata: dict[str, Any]


class GlobalController(Protocol):
    def act(self, state: GlobalState) -> ControllerAction:
        ...


class GlobalNoopController:
    """Phase-0 controller: consumes global state but does not actuate Vissim."""

    def act(self, state: GlobalState) -> ControllerAction:
        return ControllerAction(
            sim_sec=state.sim_sec,
            mode="GLOBAL_NOOP",
            command="observe_only",
            metadata={
                "reason": "signal controllers/heads are not present in the current network",
                "total_vehicles": state.total_vehicles,
                "mean_speed_kph": state.mean_speed_kph,
                "stopped_vehicles": state.stopped_vehicles,
            },
        )


class FixedTimePlaceholderController:
    """Phase-1 placeholder until signal groups/heads are available in an evaluation INPX."""

    def __init__(self, cycle_sec: int = 90) -> None:
        self.cycle_sec = cycle_sec

    def act(self, state: GlobalState) -> ControllerAction:
        cycle_pos = int(state.sim_sec) % self.cycle_sec
        phase = "major" if cycle_pos < self.cycle_sec // 2 else "minor"
        return ControllerAction(
            sim_sec=state.sim_sec,
            mode="FIXED_TIME_PLACEHOLDER",
            command=f"set_{phase}_phase_when_signal_objects_exist",
            metadata={"cycle_sec": self.cycle_sec, "cycle_pos": cycle_pos, "phase": phase},
        )


def state_from_csv_row(row: dict[str, str]) -> GlobalState:
    return GlobalState(
        sim_sec=float(row["sim_sec"]),
        total_vehicles=int(row["total_vehicles"]),
        urban_vehicles=int(row["urban_vehicles"]),
        freeway_vehicles=int(row["freeway_vehicles"]),
        ramp_vehicles=int(row["ramp_vehicles"]),
        boundary_vehicles=int(row["boundary_vehicles"]),
        other_vehicles=int(row["other_vehicles"]),
        mean_speed_kph=float(row["mean_speed_kph"]),
        stopped_vehicles=int(row["stopped_vehicles"]),
    )


def build_controller(name: str) -> GlobalController:
    if name == "noop":
        return GlobalNoopController()
    if name == "fixed-time-placeholder":
        return FixedTimePlaceholderController()
    raise ValueError(f"unknown controller: {name}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-csv", required=True)
    parser.add_argument("--out-jsonl", required=True)
    parser.add_argument("--controller", choices=["noop", "fixed-time-placeholder"], default="noop")
    args = parser.parse_args()

    controller = build_controller(args.controller)
    state_csv = Path(args.state_csv)
    out_jsonl = Path(args.out_jsonl)
    out_jsonl.parent.mkdir(parents=True, exist_ok=True)

    with state_csv.open(newline="", encoding="utf-8-sig") as f, out_jsonl.open("w", encoding="utf-8") as out:
        for row in csv.DictReader(f):
            state = state_from_csv_row(row)
            action = controller.act(state)
            out.write(json.dumps(asdict(action), ensure_ascii=False) + "\n")

    print(f"WROTE={out_jsonl}")


if __name__ == "__main__":
    main()
