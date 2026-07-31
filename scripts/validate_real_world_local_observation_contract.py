from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAPPING = WORKSPACE_ROOT / "evaluation/real_world_modi_control/detector_local_mapping.json"
DEFAULT_TUNING = WORKSPACE_ROOT / "evaluation/configs/real_world_modi_pstack_adapter_v0_20260719.json"
DEFAULT_CALIBRATION = WORKSPACE_ROOT / "evaluation/calibration/real_world_modi_control_v0_20260719.json"
DEFAULT_OUT = WORKSPACE_ROOT / "evaluation/runs/real_world_local_observation_contract/summary.json"


def _freeway_rows() -> list[dict[str, float]]:
    return [
        {"count": 0.0, "speed_sum": 0.0, "length_km": 1.0, "lanes": 4.0}
        for _ in range(8)
    ]


def _movement_total(state: Any, signal: str) -> float:
    return sum(
        max(0.0, float(value))
        for movement, value in state.urban_movement_queue.items()
        if str(movement).startswith(f"{signal}_off")
    )


def _assert_close(name: str, actual: float, expected: float, eps: float = 1.0e-9) -> None:
    if abs(actual - expected) > eps:
        raise AssertionError(f"{name}: expected {expected}, got {actual}")


def run(mapping_path: Path, tuning_path: Path, calibration_path: Path) -> dict[str, Any]:
    if str(WORKSPACE_ROOT) not in sys.path:
        sys.path.insert(0, str(WORKSPACE_ROOT))

    from evaluation.controllers import vissim_stackelberg_adapter as adapter

    repo_root = adapter.DEFAULT_REPO_ROOT
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from src.models.state import TrafficState

    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    tuning = json.loads(tuning_path.read_text(encoding="utf-8"))
    calibration = json.loads(calibration_path.read_text(encoding="utf-8"))
    state_json = {
        "sim_sec": 60,
        "sim_period_sec": 300,
        "control_interval_sec": 60,
        "urban_vehicles": 9999,
        "boundary_vehicles": 8888,
        "ramp_counts": {"D": 999, "F": 777},
        "local_observation": {
            "schema_version": 1,
            "mode": "real_world_connector_local_v1",
            "source": "synthetic_real_world_connector_leak_test",
            "global_vehicle_scan_masked": True,
            "link_counts": {
                "10479": 9,
                "10491": 6,
                "10480": 4,
                "10482": 2,
                "10481": 0,
                "10483": 0,
                "10484": 0,
                "10490": 0,
                "10638": 0,
                "10639": 0,
                "10643": 0,
                "10644": 0,
                "10645": 0,
                "10646": 0,
                "10681": 0,
                "10682": 0,
            },
        },
        "freeway_segments": {
            "FW_E": _freeway_rows(),
            "FW_W": _freeway_rows(),
        },
        "demand": {
            "urban_volume_vph": 355.0,
            "freeway_volume_vph": 3080.0,
            "ramp_volume_vph": 0.0,
            "demand_profile": "synthetic_real_world_local_contract",
        },
    }
    cfg = adapter.build_config(
        repo_root,
        control_interval=60,
        sim_period=300,
        mode="fast-smoke",
        calibration=calibration,
        tuning=tuning,
        local_observation=True,
    )
    state = adapter.traffic_state_from_vissim(
        state_json,
        cfg,
        TrafficState,
        mapping,
        calibration,
    )
    summary = adapter.build_local_observation_summary(state_json, cfg, mapping, calibration)

    d_ramp_total = float(state.ramp_queue["R_D_W"] + state.ramp_queue["R_D_E"])
    f_ramp_total = float(state.ramp_queue["R_F_W"] + state.ramp_queue["R_F_E"])
    _assert_close("D ramp connector queue", d_ramp_total, 6.0)
    _assert_close("F ramp connector queue leak", f_ramp_total, 0.0)

    off_fraction = float(summary["split_parameters"]["offramp_storage_fraction"])
    expected_d_movement = 15.0 * (1.0 - off_fraction)
    expected_d_storage = 15.0 * off_fraction
    d_movement = _movement_total(state, "D")
    f_movement = _movement_total(state, "F")
    _assert_close("D off-ramp movement queue", d_movement, expected_d_movement)
    _assert_close("F off-ramp movement queue leak", f_movement, 0.0)
    _assert_close(
        "D off-ramp storage occupancy",
        float(summary["urban_link_storage_occupancy"].get("OR_D_W_storage", 0.0)),
        expected_d_storage,
    )

    u_d = summary["agents"]["U_D"]
    u_f = summary["agents"]["U_F"]
    if "10479" not in u_d["link_counts"] or "10480" not in u_d["link_counts"]:
        raise AssertionError("U_D does not expose D off-ramp and ramp-meter connector links")
    if "10479" in u_f["link_counts"] or "10480" in u_f["link_counts"]:
        raise AssertionError("U_F leaks D connector links")

    return {
        "status": "ok",
        "mapping_version": mapping.get("mapping_version"),
        "follower_solver_mode": cfg.mpc.follower_solver_mode,
        "agent_count": len(summary["agents"]),
        "D_ramp_queue": d_ramp_total,
        "F_ramp_queue": f_ramp_total,
        "D_offramp_movement_queue": d_movement,
        "F_offramp_movement_queue": f_movement,
        "D_offramp_storage_link": "OR_D_W_storage",
        "D_offramp_storage_occupancy": expected_d_storage,
        "offramp_storage_fraction": off_fraction,
        "global_urban_input": state_json["urban_vehicles"],
        "global_boundary_input": state_json["boundary_vehicles"],
        "checks": [
            "real_world_local_observation_overrides_global_aggregates",
            "D_connector_counts_do_not_leak_to_F_agent",
            "off_ramp_connector_counts_feed_off_ramp_storage",
            "ramp_meter_connector_counts_feed_model_ramp_queues",
            "distributed_mode_enabled_for_real_world_local_observation",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mapping-json", default=str(DEFAULT_MAPPING))
    parser.add_argument("--tuning-json", default=str(DEFAULT_TUNING))
    parser.add_argument("--calibration-json", default=str(DEFAULT_CALIBRATION))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    result = run(Path(args.mapping_json), Path(args.tuning_json), Path(args.calibration_json))
    if result["follower_solver_mode"] != "distributed":
        raise AssertionError(f"Expected distributed follower mode, got {result['follower_solver_mode']}")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
