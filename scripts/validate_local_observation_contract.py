from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPO_ROOT = Path("C:/Users/TRLAB/Desktop/찐찐막/Numerical-Sim")
DEFAULT_MAPPING = WORKSPACE_ROOT / "evaluation/detector_install/detector_local_mapping.json"
DEFAULT_OUT = WORKSPACE_ROOT / "evaluation/runs/local_observation_contract/summary.json"


def _freeway_rows() -> list[dict[str, float]]:
    return [
        {"count": 0.0, "speed_sum": 0.0, "length_km": 0.58, "lanes": 2.0}
        for _ in range(5)
    ]


def _signal_movement_total(state: Any, cfg: Any, signal: str) -> float:
    return sum(
        max(0.0, float(state.urban_movement_queue.get(movement, 0.0)))
        for movement, spec in cfg.network.urban_movements.items()
        if str(spec.get("signal", "")) == signal
    )


def _assert_close(name: str, actual: float, expected: float, eps: float = 1.0e-9) -> None:
    if abs(actual - expected) > eps:
        raise AssertionError(f"{name}: expected {expected}, got {actual}")


def run(repo_root: Path, mapping_path: Path) -> dict[str, Any]:
    if str(WORKSPACE_ROOT) not in sys.path:
        sys.path.insert(0, str(WORKSPACE_ROOT))
    from evaluation.controllers.vissim_stackelberg_adapter import (
        build_config,
        build_local_observation_summary,
        mask_state_for_agent,
        traffic_state_from_vissim,
    )

    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from src.controllers.distributed_coordinator import build_agent_specs
    from src.models.state import TrafficState

    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    state_json = {
        "sim_sec": 60,
        "sim_period_sec": 300,
        "control_interval_sec": 60,
        # These aggregate values are intentionally absurd. Local mode must
        # ignore them and use local_observation.link_counts instead.
        "urban_vehicles": 9999,
        "boundary_vehicles": 8888,
        "ramp_counts": {"D": 999, "F": 777},
        "local_observation": {
            "schema_version": 1,
            "mode": "detector_local_v1",
            "source": "synthetic_leak_test",
            "global_vehicle_scan_masked": True,
            "link_counts": {
                # D boundary approach only.
                "21": 80,
                # D on-ramp storage only.
                "25": 40,
                # D off-ramp approach only.
                "26": 20,
                # F side explicitly empty.
                "30": 0,
                "31": 0,
                "32": 0,
            },
        },
        "freeway_segments": {
            "FW_E": _freeway_rows(),
            "FW_W": _freeway_rows(),
        },
        "demand": {
            "urban_volume_vph": 2200,
            "freeway_volume_vph": 3000,
            "ramp_volume_vph": 250,
            "demand_profile": "synthetic_local_contract",
        },
    }
    cfg = build_config(
        repo_root,
        control_interval=60,
        sim_period=300,
        mode="fast-smoke",
        calibration={},
        tuning={},
        local_observation=True,
    )
    state = traffic_state_from_vissim(state_json, cfg, TrafficState, mapping)
    summary = build_local_observation_summary(state_json, cfg, mapping)

    d_ramp_total = state.ramp_queue["R_D_W"] + state.ramp_queue["R_D_E"]
    f_ramp_total = state.ramp_queue["R_F_W"] + state.ramp_queue["R_F_E"]
    _assert_close("D ramp queue", d_ramp_total, 40.0)
    _assert_close("F ramp queue", f_ramp_total, 0.0)

    u_d_total = _signal_movement_total(state, cfg, "D")
    u_f_total = _signal_movement_total(state, cfg, "F")
    if u_d_total <= 99.999:
        raise AssertionError(f"U_D should see D local movement queues, got {u_d_total}")
    _assert_close("U_F leaked D/F movement queue", u_f_total, 0.0)

    total_movement_queue = sum(max(0.0, float(v)) for v in state.urban_movement_queue.values())
    if total_movement_queue > 101.0:
        raise AssertionError(
            "Aggregate urban_vehicles leaked into movement queues: "
            f"local total should be about 100, got {total_movement_queue}"
        )

    u_d = summary["agents"]["U_D"]
    u_f = summary["agents"]["U_F"]
    if "21" not in u_d["link_counts"]:
        raise AssertionError("U_D does not expose its D boundary approach link 21")
    if "21" in u_f["link_counts"]:
        raise AssertionError("U_F observation leaks D approach link 21")

    f_side_agents = {
        agent_id: spec
        for agent_id, spec in summary["agents"].items()
        if spec.get("visible_ramps") and any(str(ramp).startswith("R_F_") for ramp in spec["visible_ramps"])
    }
    for agent_id, spec in f_side_agents.items():
        leaked = sum(max(0.0, float(v)) for v in spec.get("ramp_queue", {}).values())
        _assert_close(f"{agent_id} leaked D ramp queue", leaked, 0.0)

    urban_agents, freeway_agents = build_agent_specs(cfg)
    agent_by_id = {agent.id: agent for agent in [*urban_agents, *freeway_agents]}
    masked_u_f = mask_state_for_agent(state, cfg, agent_by_id["U_F"])
    _assert_close("masked U_F movement queue", _signal_movement_total(masked_u_f, cfg, "F"), 0.0)
    _assert_close("masked U_F leaked U_D movement queue", _signal_movement_total(masked_u_f, cfg, "D"), 0.0)
    masked_u_d = mask_state_for_agent(state, cfg, agent_by_id["U_D"])
    if _signal_movement_total(masked_u_d, cfg, "D") <= 99.999:
        raise AssertionError("masked U_D lost its own local movement queue")

    f_ramp_agent_ids = [
        agent.id
        for agent in freeway_agents
        if any(str(ramp).startswith("R_F_") for ramp in agent.ramps)
    ]
    for agent_id in f_ramp_agent_ids:
        masked_f = mask_state_for_agent(state, cfg, agent_by_id[agent_id])
        leaked = masked_f.ramp_queue["R_D_W"] + masked_f.ramp_queue["R_D_E"]
        _assert_close(f"masked {agent_id} leaked D ramp queue", leaked, 0.0)

    return {
        "status": "ok",
        "follower_solver_mode": cfg.mpc.follower_solver_mode,
        "agent_count": len(summary["agents"]),
        "D_ramp_queue": d_ramp_total,
        "F_ramp_queue": f_ramp_total,
        "U_D_movement_queue": u_d_total,
        "U_F_movement_queue": u_f_total,
        "total_movement_queue": total_movement_queue,
        "global_urban_input": state_json["urban_vehicles"],
        "global_boundary_input": state_json["boundary_vehicles"],
        "checks": [
            "local_observation_overrides_global_aggregates",
            "D_ramp_does_not_leak_to_F_ramp_agents",
            "D_urban_link_does_not_leak_to_U_F",
            "runtime_agent_state_masking_blocks_cross_agent_state",
            "distributed_mode_enabled_for_local_observation",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=str(DEFAULT_REPO_ROOT))
    parser.add_argument("--mapping-json", default=str(DEFAULT_MAPPING))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    result = run(Path(args.repo_root), Path(args.mapping_json))
    if result["follower_solver_mode"] != "distributed":
        raise AssertionError(f"Expected distributed follower mode, got {result['follower_solver_mode']}")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
