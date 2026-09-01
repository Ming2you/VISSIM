from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPO_ROOT = Path("C:/Users/TRLAB/Desktop/찐찐막/Numerical-Sim")
DEFAULT_STATE = WORKSPACE_ROOT / "evaluation/runs/local_observation_contract/state_cli.json"
DEFAULT_MAPPING = WORKSPACE_ROOT / "evaluation/detector_install/detector_local_mapping.json"
DEFAULT_OUT = WORKSPACE_ROOT / "evaluation/runs/wu_controller_smoke/summary.json"


def _control_summary(control: Any) -> dict[str, Any]:
    return {
        "green_times": {k: float(v) for k, v in sorted(control.green_times.items())},
        "vsl": {k: float(v) for k, v in sorted(control.vsl.items())},
        "ramp_metering": {k: float(v) for k, v in sorted(control.ramp_metering.items())},
        "offsets": {k: float(v) for k, v in sorted(control.offsets.items())},
        "diagnostics_keys": sorted(str(k) for k in control.diagnostics.keys())[:40],
    }


def run(repo_root: Path, state_path: Path, mapping_path: Path, leader_enabled: bool) -> dict[str, Any]:
    if str(WORKSPACE_ROOT) not in sys.path:
        sys.path.insert(0, str(WORKSPACE_ROOT))
    from evaluation.controllers.vissim_stackelberg_adapter import (
        build_config,
        demand_from_state,
        traffic_state_from_vissim,
    )

    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from src.controllers.wu_distributed import WuDistributedController
    from src.models.state import ControlAction, TrafficState
    from src.models.demand import DemandStep

    state_json = json.loads(state_path.read_text(encoding="utf-8"))
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    control_interval = float(state_json.get("control_interval_sec", 60.0))
    sim_period = float(state_json.get("sim_period_sec", max(300.0, control_interval)))

    cfg = build_config(
        repo_root,
        control_interval=control_interval,
        sim_period=sim_period,
        mode="fast-smoke",
        calibration={},
        tuning={},
        local_observation=True,
    )
    # Wu's native implementation is a green+VSL authority reference. Keep the
    # same local-observation state conversion used by the Vissim adapter, then
    # ask the Wu controller to solve one control interval.
    state = traffic_state_from_vissim(state_json, cfg, TrafficState, mapping)
    forecast = demand_from_state(state_json, cfg, DemandStep, cfg.mpc.horizon_steps)
    previous = ControlAction.uncontrolled(cfg)

    controller = WuDistributedController(cfg, leader_enabled=leader_enabled)
    info = controller.decide_with_info(state, forecast, previous)
    control = info.control
    result = {
        "status": "ok",
        "controller": "WuDistributedController",
        "leader_enabled": bool(leader_enabled),
        "iterations": int(info.iterations),
        "converged": bool(info.converged),
        "coupling_residual": float(info.coupling_residual),
        "solver_evaluations": int(info.solver_evaluations),
        "computation_time_sec": float(info.computation_time_sec),
        "leader_candidates": int(info.leader_candidates),
        "leader_objective": float(info.leader_objective),
        "state_source": str(state_path),
        "mapping_source": str(mapping_path),
        "control": _control_summary(control),
    }
    if info.leader_selected is not None:
        result["leader_selected"] = {
            "n_p_star": float(info.leader_selected.n_p_star),
            "n_f_star": float(info.leader_selected.n_f_star),
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=str(DEFAULT_REPO_ROOT))
    parser.add_argument("--state-json", default=str(DEFAULT_STATE))
    parser.add_argument("--mapping-json", default=str(DEFAULT_MAPPING))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--leader-enabled", action="store_true")
    args = parser.parse_args()

    result = run(
        repo_root=Path(args.repo_root),
        state_path=Path(args.state_json),
        mapping_path=Path(args.mapping_json),
        leader_enabled=bool(args.leader_enabled),
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
