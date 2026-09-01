from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPO_ROOT = Path("C:/Users/TRLAB/Desktop/찐찐막/Numerical-Sim")
DEFAULT_OUT = WORKSPACE_ROOT / "evaluation/detector_install/detector_local_mapping.json"


# Vissim physical link -> Numerical-Sim abstract queue origin(s).
# The controller must not infer movement queues from aggregate urban counts.
# It may only split vehicles observed on a local approach/ramp link into the
# movements whose origin is that local link.
LINK_TO_ORIGINS: dict[int, tuple[str, ...]] = {
    1: ("in_A_left",),
    3: ("in_A_top",),
    5: ("A_to_B",),
    6: ("B_to_A",),
    7: ("A_to_D",),
    8: ("D_to_A",),
    9: ("in_B_top",),
    11: ("B_to_C",),
    12: ("C_to_B",),
    13: ("B_to_E",),
    14: ("E_to_B",),
    15: ("in_C_top",),
    18: ("in_C_right",),
    19: ("C_to_F",),
    20: ("F_to_C",),
    21: ("in_D_left",),
    23: ("D_to_E",),
    24: ("E_to_D",),
    26: ("OR_D_W", "OR_D_E"),
    27: ("E_to_F",),
    28: ("F_to_E",),
    30: ("in_F_right",),
    32: ("OR_F_W", "OR_F_E"),
}

RAMP_LINK_TO_QUEUES: dict[int, tuple[str, ...]] = {
    25: ("R_D_W", "R_D_E"),
    31: ("R_F_W", "R_F_E"),
}

BOUNDARY_LINK_TO_QUEUE: dict[int, str] = {
    1: "in_A_left",
    2: "out_A_left",
    3: "in_A_top",
    4: "out_A_top",
    9: "in_B_top",
    10: "out_B_top",
    15: "in_C_top",
    16: "out_C_top",
    17: "out_C_right",
    18: "in_C_right",
    21: "in_D_left",
    22: "out_D_left",
    29: "out_F_right",
    30: "in_F_right",
}

FREEWAY_LINKS: dict[int, str] = {
    33: "FW_E",
    34: "FW_W",
}

VISSIM_FREEWAY_SEGMENTS_PER_LINK = 5
VISSIM_RAMP_MERGE_SEGMENT_INDEX = {
    "R_D_W": 3,
    "R_F_W": 1,
    "R_D_E": 1,
    "R_F_E": 3,
}
VISSIM_OFF_RAMP_SEGMENT_INDEX = {
    "OR_D_W": 3,
    "OR_F_W": 1,
    "OR_D_E": 1,
    "OR_F_E": 3,
}


def _freeway_agent_id(link: str, segment_index: int) -> str:
    suffix = link.split("_")[-1] if "_" in link else link
    return f"F_{suffix}{segment_index}"


def _urban_agent_id(signal: str) -> str:
    return f"U_{signal}"


def _configured_segment_index(mapping: Any, key: str, fallback: int, n_segments: int) -> int:
    if isinstance(mapping, dict) and key in mapping:
        return max(0, min(n_segments - 1, int(float(mapping[key]))))
    return max(0, min(n_segments - 1, int(fallback)))


def build_mapping(repo_root: Path) -> dict[str, Any]:
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    from src.models.state import ExperimentConfig

    cfg = ExperimentConfig.from_file(repo_root / "src/config/default.yaml")
    net = cfg.network

    link_to_movements: dict[str, list[dict[str, Any]]] = {}
    for link_no, origins in LINK_TO_ORIGINS.items():
        entries: list[dict[str, Any]] = []
        origin_set = set(origins)
        for movement, spec in net.urban_movements.items():
            origin = str(spec.get("origin", ""))
            if origin not in origin_set:
                continue
            entries.append({
                "movement": movement,
                "weight": float(spec.get("beta", 1.0)),
                "signal": str(spec.get("signal", "")),
                "phase": str(spec.get("phase", "")),
                "kind": str(spec.get("kind", "")),
                "origin": origin,
            })
        link_to_movements[str(link_no)] = entries

    movement_to_links: dict[str, list[str]] = {}
    for link_no, entries in link_to_movements.items():
        for entry in entries:
            movement_to_links.setdefault(str(entry["movement"]), []).append(link_no)

    agents: dict[str, dict[str, Any]] = {}
    for signal in net.signals:
        movements = [
            movement
            for movement, spec in net.urban_movements.items()
            if str(spec.get("signal", "")) == signal
        ]
        visible_links = sorted({
            link
            for movement in movements
            for link in movement_to_links.get(movement, [])
        }, key=lambda value: int(value))
        visible_ramps = sorted({
            str(spec.get("ramp", ""))
            for movement, spec in net.urban_movements.items()
            if movement in movements and str(spec.get("ramp", ""))
        })
        visible_off_ramps = sorted({
            str(spec.get("off_ramp", ""))
            for movement, spec in net.urban_movements.items()
            if movement in movements and str(spec.get("off_ramp", ""))
        })
        agents[_urban_agent_id(signal)] = {
            "kind": "urban",
            "signal": signal,
            "visible_links": visible_links,
            "visible_movements": sorted(movements),
            "visible_ramps": visible_ramps,
            "visible_off_ramps": visible_off_ramps,
        }

    for vissim_link_no, model_link in FREEWAY_LINKS.items():
        for segment_index in range(VISSIM_FREEWAY_SEGMENTS_PER_LINK):
            ramps = [
                ramp
                for ramp in net.ramps
                if net.ramp_to_freeway.get(ramp) == model_link
                and _configured_segment_index(
                    VISSIM_RAMP_MERGE_SEGMENT_INDEX,
                    ramp,
                    VISSIM_FREEWAY_SEGMENTS_PER_LINK // 2,
                    VISSIM_FREEWAY_SEGMENTS_PER_LINK,
                ) == segment_index
            ]
            off_ramps = [
                off_ramp
                for off_ramp in net.off_ramps
                if net.off_ramp_from_freeway.get(off_ramp) == model_link
                and _configured_segment_index(
                    VISSIM_OFF_RAMP_SEGMENT_INDEX,
                    off_ramp,
                    VISSIM_FREEWAY_SEGMENTS_PER_LINK - 1,
                    VISSIM_FREEWAY_SEGMENTS_PER_LINK,
                ) == segment_index
            ]
            agents[_freeway_agent_id(model_link, segment_index)] = {
                "kind": "freeway",
                "model_link": model_link,
                "segment_index": segment_index,
                "visible_links": [str(vissim_link_no)],
                "visible_movements": [],
                "visible_ramps": sorted(ramps),
                "visible_off_ramps": sorted(off_ramps),
            }

    return {
        "schema_version": 1,
        "mapping_version": "detector_local_v1_20260627",
        "description": (
            "Local observation contract for the hypothetical Vissim network. "
            "Follower inputs are built from detector/local-zone link counts, "
            "not aggregate global urban/boundary vehicle counts."
        ),
        "source": {
            "repo_root": str(repo_root),
            "numerical_sim_config": str(repo_root / "src/config/default.yaml"),
        },
        "observable_links": sorted(
            {
                *LINK_TO_ORIGINS.keys(),
                *RAMP_LINK_TO_QUEUES.keys(),
                *BOUNDARY_LINK_TO_QUEUE.keys(),
                *FREEWAY_LINKS.keys(),
            }
        ),
        "link_to_origins": {str(k): list(v) for k, v in LINK_TO_ORIGINS.items()},
        "link_to_movements": link_to_movements,
        "ramp_link_to_queues": {str(k): list(v) for k, v in RAMP_LINK_TO_QUEUES.items()},
        "boundary_link_to_queue": {str(k): v for k, v in BOUNDARY_LINK_TO_QUEUE.items()},
        "freeway_link_to_model_link": {str(k): v for k, v in FREEWAY_LINKS.items()},
        "agents": agents,
        "guardrails": {
            "leader_visibility": "global_state_allowed",
            "follower_visibility": "agent_visible_links_movements_ramps_only",
            "adapter_global_fallback_allowed_only_when_local_observation_absent": True,
            "vissim_internal_scan_is_masked_before_controller": True,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=str(DEFAULT_REPO_ROOT))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    mapping = build_mapping(Path(args.repo_root))
    out.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "out": str(out),
        "agents": len(mapping["agents"]),
        "observable_links": len(mapping["observable_links"]),
        "movement_links": len(mapping["link_to_movements"]),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
