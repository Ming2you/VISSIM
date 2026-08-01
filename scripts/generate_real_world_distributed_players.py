from __future__ import annotations

import argparse
import csv
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SIGNAL_ROLES = ROOT / "evaluation/real_world_modi_inventory/signal_controller_roles.csv"
DEFAULT_CONTROL_MAPPING = ROOT / "evaluation/real_world_modi_control/control_mapping.json"
DEFAULT_DETECTOR_MAPPING = ROOT / "evaluation/real_world_modi_control/detector_local_mapping.json"
DEFAULT_NETWORK = ROOT / "network/real_world_gaepo_modi/modi_eval_rw_control.inpx"
DEFAULT_PREDICTION_CALIBRATION = ROOT / "evaluation/calibration/real_world_prediction_calibration_pshb4500fix_20260724.json"
OUT_DIR = ROOT / "evaluation/real_world_modi_control_distributed_20260728"
CONFIG_DIR = ROOT / "evaluation/configs"
GENERATED_DIR = ROOT / "evaluation/generated"
OUTPUTS_DIR = ROOT / "outputs"

# ---------------------------------------------------------------------------
# Urban Follower ID ↔ VISSIM SC (2026-07-31 정정)
#
# 이전 구현은 사용자가 표시한 플레이어 번호를 VISSIM SC 번호로 착각해 그대로
# 박아넣었다(구 CORE15_SC_NUMBERS 주석 "Manual interpretation of the user's
# 2026-07-28 marked-up 15-player core"). 두 체계는 다르다 — UF1→SC1004,
# UF8→SC1, UF15→SC5. 그 결과 15core는 15개 중 8개가, primary19는 SC 1~19를
# 그대로 써서 19개 중 14개가 엉뚱한 신호기를 제어하고 있었다.
#
# 이제 매핑은 사용자 검증 원본(Urban-Follower.xlsx)에서 기계 추출한 CSV가
# 유일한 근거다(scripts/extract_urban_follower_map.py). 수동 해석 금지.
# ---------------------------------------------------------------------------
DEFAULT_URBAN_FOLLOWER_MAP = ROOT / "evaluation/real_world_modi_inventory/urban_follower_sc_map.csv"

# 사용자 지정 코어 15 플레이어 = Urban Follower ID 1~16 중 11 제외.
# ★ 이 값은 UF ID다. SC 번호가 아니다.
CORE15_URBAN_FOLLOWER_IDS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14, 15, 16]


def load_urban_follower_sc_map(path: Path = DEFAULT_URBAN_FOLLOWER_MAP) -> dict[int, int]:
    """UF ID → SC 번호. CSV가 없으면 추출 스크립트를 실행하라고 알린다."""
    if not path.exists():
        raise SystemExit(
            f"UF→SC 매핑 CSV가 없다: {path}\n"
            "  python scripts/extract_urban_follower_map.py 를 먼저 실행할 것."
        )
    return {int(row["urban_follower_id"]): int(row["sc_no"]) for row in read_csv(path)}


def urban_follower_scs(uf_ids: list[int], uf_map: dict[int, int]) -> list[int]:
    unknown = sorted(set(uf_ids) - set(uf_map))
    if unknown:
        raise ValueError(f"매핑에 없는 Urban Follower ID: {unknown}")
    return sorted(uf_map[uf] for uf in uf_ids)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def parse_int_csv(text: str) -> list[int]:
    out: list[int] = []
    for part in str(text or "").replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.append(int(float(part)))
        except ValueError:
            continue
    return out


def first_int(text: str | None) -> int | None:
    match = re.search(r"-?\d+", str(text or ""))
    return int(match.group(0)) if match else None


def parse_sg_ref(text: str | None) -> tuple[int, int] | None:
    parts = [int(v) for v in re.findall(r"-?\d+", str(text or ""))]
    if len(parts) < 2:
        return None
    return parts[0], parts[1]


def signal_group_axis(name: str, sg_no: int) -> str:
    upper = str(name or "").upper()
    if "EB" in upper or "WB" in upper:
        return "EW"
    if "NB" in upper or "SB" in upper:
        return "NS"
    if int(sg_no) == 1:
        return "EW"
    if int(sg_no) == 2:
        return "NS"
    return "unknown"


def signal_head_link_axes(network_path: Path) -> dict[int, dict[str, set[str]]]:
    root = ET.parse(network_path).getroot()
    sg_axis_by_sc: dict[int, dict[int, str]] = {}
    for sc in root.iter("signalController"):
        sc_no = first_int(sc.get("no"))
        if sc_no is None:
            continue
        by_sg: dict[int, str] = {}
        for sg in sc.findall("./sgs/signalGroup"):
            sg_no = first_int(sg.get("no"))
            if sg_no is None:
                continue
            by_sg[sg_no] = signal_group_axis(str(sg.get("name", "")), sg_no)
        sg_axis_by_sc[sc_no] = by_sg

    axes: dict[int, dict[str, set[str]]] = {}
    for sh in root.iter("signalHead"):
        sg_ref = parse_sg_ref(sh.get("sg"))
        link_no = first_int(sh.get("lane"))
        if sg_ref is None or link_no is None:
            continue
        sc_no, sg_no = sg_ref
        axis = sg_axis_by_sc.get(sc_no, {}).get(sg_no, "unknown")
        axes.setdefault(sc_no, {}).setdefault(str(link_no), set()).add(axis)
    return axes


def signal_head_link_max_pos(network_path: Path) -> dict[int, dict[str, float]]:
    root = ET.parse(network_path).getroot()
    out: dict[int, dict[str, float]] = {}
    for sh in root.iter("signalHead"):
        sg_ref = parse_sg_ref(sh.get("sg"))
        link_no = first_int(sh.get("lane"))
        if sg_ref is None or link_no is None:
            continue
        sc_no = sg_ref[0]
        try:
            pos = float(str(sh.get("pos", "0")).strip())
        except ValueError:
            pos = 0.0
        by_link = out.setdefault(sc_no, {})
        link_key = str(link_no)
        by_link[link_key] = max(float(by_link.get(link_key, 0.0)), pos)
    return out


def controlled_link_owner(
    rows: list[dict[str, str]],
    head_pos_by_sc: dict[int, dict[str, float]],
) -> dict[str, int]:
    candidates: dict[str, list[tuple[float, int]]] = {}
    for row in rows:
        sc_no = int(row["no"])
        for link in parse_int_csv(row.get("unique_head_links", "")):
            candidates.setdefault(str(link), []).append((float(head_pos_by_sc.get(sc_no, {}).get(str(link), 0.0)), sc_no))
    owners: dict[str, int] = {}
    for link, values in candidates.items():
        owners[link] = sorted(values, key=lambda item: (item[0], -item[1]), reverse=True)[0][1]
    return owners


def owned_links_for_signal(
    row: dict[str, str],
    link_owner_by_link: dict[str, int],
) -> list[str]:
    sc_no = int(row["no"])
    return [
        str(link)
        for link in parse_int_csv(row.get("unique_head_links", ""))
        if link_owner_by_link.get(str(link), sc_no) == sc_no
    ]


def active_fixedtime_signal_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return sorted(
        [
            row
            for row in rows
            if row.get("active", "").lower() == "true"
            and row.get("type", "").upper() == "FIXEDTIME"
            and int(float(row.get("signal_head_count") or 0)) > 0
        ],
        key=lambda row: int(row["no"]),
    )


def _select_by_sc(rows: list[dict[str, str]], wanted: set[int], label: str) -> list[dict[str, str]]:
    """지정 SC만 고른다. 하나라도 인벤토리에 없으면 조용히 빠뜨리지 않고 실패시킨다."""
    selected = [
        row for row in active_fixedtime_signal_rows(rows) if int(row.get("no", "0")) in wanted
    ]
    missing = sorted(wanted - {int(row["no"]) for row in selected})
    if missing:
        raise ValueError(
            f"{label}: 인벤토리에 없거나 비활성인 signal controller {missing}\n"
            "  네트워크를 수정했다면 인벤토리를 먼저 재생성할 것:\n"
            "  python scripts/inventory_real_world_modi.py --inpx network/real_world_gaepo_modi/modi.inpx"
        )
    return selected


def selected_signal_rows(rows: list[dict[str, str]], selector: str) -> list[dict[str, str]]:
    if selector == "primary19":
        # Urban Follower 1~19 전체(SC 번호 1~19가 아니다 — 위 매핑 주석 참조).
        uf_map = load_urban_follower_sc_map()
        selected = _select_by_sc(rows, set(uf_map.values()), "primary19")
    elif selector == "core15":
        uf_map = load_urban_follower_sc_map()
        wanted = set(urban_follower_scs(CORE15_URBAN_FOLLOWER_IDS, uf_map))
        selected = _select_by_sc(rows, wanted, "core15")
    elif selector == "all-active-heads":
        selected = active_fixedtime_signal_rows(rows)
    else:
        wanted = {int(x) for x in parse_int_csv(selector)}
        selected = [row for row in active_fixedtime_signal_rows(rows) if int(row.get("no", "0")) in wanted]
    if not selected:
        raise ValueError(f"No signal controllers matched selector={selector!r}")
    return sorted(selected, key=lambda row: int(row["no"]))


def selector_slug(selector: str, count: int) -> str:
    if selector == "primary19":
        return "19sc"
    if selector == "core15":
        return "15core"
    if selector == "all-active-heads":
        return f"{count}sc_all"
    return f"{count}sc_custom"


def signal_id(sc_no: int) -> str:
    return f"SC{sc_no}"


def movement(signal: str, suffix: str, phase: str, origin: str, receiving: str, kind: str = "boundary_in") -> dict[str, Any]:
    return {
        "intersection": signal,
        "approach": suffix,
        "exit": "out",
        "beta": 1.0,
        "signal": signal,
        "phase": f"{signal}_{phase}",
        "origin": origin,
        "destination": receiving,
        "receiving_link": receiving,
        "kind": kind,
    }


def build_network_override(rows: list[dict[str, str]], include_freeway_interface_coupling: bool = True) -> dict[str, Any]:
    signals = [signal_id(int(row["no"])) for row in rows]
    grid_node_legs: dict[str, Any] = {}
    urban_movements: dict[str, Any] = {}
    boundary_in: list[str] = []
    boundary_out: list[str] = []
    storage: dict[str, float] = {}

    for sid in signals:
        grid_node_legs[sid] = {
            "N": {"type": "boundary", "in": f"in_{sid}_N", "out": f"out_{sid}_N", "out_link": f"{sid}_N_out"},
            "S": {"type": "boundary", "in": f"in_{sid}_S", "out": f"out_{sid}_S", "out_link": f"{sid}_S_out"},
            "E": {"type": "boundary", "in": f"in_{sid}_E", "out": f"out_{sid}_E", "out_link": f"{sid}_E_out"},
            "W": {"type": "boundary", "in": f"in_{sid}_W", "out": f"out_{sid}_W", "out_link": f"{sid}_W_out"},
        }
        for leg in ("N", "S", "E", "W"):
            boundary_in.append(f"in_{sid}_{leg}")
            boundary_out.append(f"out_{sid}_{leg}")
            storage[f"{sid}_{leg}_out"] = 220.0
        for suffix, phase, leg in (
            ("NS_N", "p1", "N"),
            ("NS_S", "p1", "S"),
            ("EW_E", "p2", "E"),
            ("EW_W", "p2", "W"),
        ):
            key = f"{sid}_{suffix}_to_out"
            urban_movements[key] = movement(sid, suffix, phase, f"in_{sid}_{leg}", f"{sid}_{leg}_out")

    # SC1 is the inventoried freeway-interface signal controller. Attach the
    # four model on/off ramp movements to that urban player so distributed
    # coupling remains connected to the freeway follower.
    has_sc1_coupling = "SC1" in signals and include_freeway_interface_coupling
    if has_sc1_coupling:
        ramp_phase = {
            "R_D_W": "p1",
            "R_D_E": "p2",
            "R_F_W": "p1",
            "R_F_E": "p2",
        }
        ramp_to_freeway = {
            "R_D_W": "FW_W",
            "R_F_W": "FW_W",
            "R_D_E": "FW_E",
            "R_F_E": "FW_E",
        }
        for ramp, phase in ramp_phase.items():
            key = f"SC1_on_{ramp}"
            storage[f"SC1_{ramp}_queue"] = 180.0
            urban_movements[key] = movement("SC1", f"on_{ramp}", phase, f"in_SC1_{ramp}", f"SC1_{ramp}_queue", "on_ramp")
            urban_movements[key]["ramp"] = ramp
            urban_movements[key]["destination"] = ramp_to_freeway[ramp]
        off_phase = {
            "OR_D_W": "p1",
            "OR_D_E": "p2",
            "OR_F_W": "p1",
            "OR_F_E": "p2",
        }
        for off_ramp, phase in off_phase.items():
            key = f"SC1_off_{off_ramp}"
            storage[f"{off_ramp}_storage"] = 120.0
            urban_movements[key] = movement("SC1", f"off_{off_ramp}", phase, off_ramp, f"{off_ramp}_storage", "off_ramp")
            urban_movements[key]["off_ramp"] = off_ramp

    return {
        "signals": signals,
        "uncontrolled_nodes": [],
        "urban_links": [],
        "grid_node_legs": grid_node_legs,
        "urban_movements": urban_movements,
        "boundary_in_links": boundary_in,
        "boundary_out_links": boundary_out,
        "urban_link_storage_veh": storage,
        "on_ramp_to_movement": {
            "R_D_W": ["SC1_on_R_D_W"] if has_sc1_coupling else [],
            "R_D_E": ["SC1_on_R_D_E"] if has_sc1_coupling else [],
            "R_F_W": ["SC1_on_R_F_W"] if has_sc1_coupling else [],
            "R_F_E": ["SC1_on_R_F_E"] if has_sc1_coupling else [],
        },
        "off_ramp_to_movement": {
            "OR_D_W": ["SC1_off_OR_D_W"] if has_sc1_coupling else [],
            "OR_D_E": ["SC1_off_OR_D_E"] if has_sc1_coupling else [],
            "OR_F_W": ["SC1_off_OR_F_W"] if has_sc1_coupling else [],
            "OR_F_E": ["SC1_off_OR_F_E"] if has_sc1_coupling else [],
        },
    }


def prune_network_movements_to_observed_axes(
    network_override: dict[str, Any],
    rows: list[dict[str, str]],
    head_axes_by_sc: dict[int, dict[str, set[str]]],
    link_owner_by_link: dict[str, int],
) -> dict[str, Any]:
    observed_axes_by_signal: dict[str, set[str]] = {}
    for row in rows:
        sc_no = int(row["no"])
        sid = signal_id(sc_no)
        axes: set[str] = set()
        for link in owned_links_for_signal(row, link_owner_by_link):
            axes.update(axis for axis in head_axes_by_sc.get(sc_no, {}).get(str(link), set()) if axis in {"NS", "EW"})
        observed_axes_by_signal[sid] = axes

    urban_movements: dict[str, Any] = {}
    removed: dict[str, list[str]] = {}
    for movement_key, spec in network_override["urban_movements"].items():
        signal = str(spec.get("signal", ""))
        phase = str(spec.get("phase", ""))
        axes = observed_axes_by_signal.get(signal, {"NS", "EW"})
        keep = True
        if phase.endswith("_p1") and axes and "NS" not in axes:
            keep = False
        if phase.endswith("_p2") and axes and "EW" not in axes:
            keep = False
        if keep:
            urban_movements[movement_key] = spec
        else:
            removed.setdefault(signal, []).append(movement_key)

    network_override["urban_movements"] = urban_movements
    network_override["on_ramp_to_movement"] = {
        ramp: [movement for movement in movements if movement in urban_movements]
        for ramp, movements in network_override.get("on_ramp_to_movement", {}).items()
    }
    network_override["off_ramp_to_movement"] = {
        off_ramp: [movement for movement in movements if movement in urban_movements]
        for off_ramp, movements in network_override.get("off_ramp_to_movement", {}).items()
    }
    return network_override


def build_control_mapping(
    base: dict[str, Any],
    rows: list[dict[str, str]],
    monitor_rows: list[dict[str, str]],
    detector_path: Path,
    selector: str,
) -> dict[str, Any]:
    out = dict(base)
    out["description"] = (
        "Distributed real-world Gaepo modi control mapping: freeway/ramp controls copied "
        "from the validated base mapping; selected core urban signals expanded to "
        "individual SC players while peripheral signals are monitored only."
    )
    out["detector_mapping_json"] = str(detector_path)
    out["urban_signal_selector"] = selector
    out["controlled_signal_controllers"] = [int(row["no"]) for row in rows]
    out["monitoring_only_signal_controllers"] = [int(row["no"]) for row in monitor_rows]
    out["signals"] = [
        {
            "id": signal_id(int(row["no"])),
            "sc_no": int(row["no"]),
            "name": row.get("name", ""),
            "role": row.get("role", ""),
            "source": "evaluation/real_world_modi_inventory/signal_controller_roles.csv",
        }
        for row in rows
    ]
    return out


def movements_for_link_axes(signal_movements: list[str], link_axes: set[str]) -> list[str]:
    if not link_axes or "unknown" in link_axes:
        return list(signal_movements)
    wanted_phases: set[str] = set()
    if "NS" in link_axes:
        wanted_phases.add("_p1")
    if "EW" in link_axes:
        wanted_phases.add("_p2")
    selected = [
        movement_key
        for movement_key in signal_movements
        if any(str(movement_key).endswith(phase) or phase in str(movement_key) for phase in wanted_phases)
    ]
    # Synthetic on/off-ramp movements at SC1 are attached to p1/p2 by suffix
    # names, not by the movement key, so match against their spec below.
    return selected if selected else list(signal_movements)


def build_detector_mapping(
    base: dict[str, Any],
    rows: list[dict[str, str]],
    monitor_rows: list[dict[str, str]],
    network_override: dict[str, Any],
    selector: str,
    head_axes_by_sc: dict[int, dict[str, set[str]]],
    link_owner_by_link: dict[str, int],
) -> dict[str, Any]:
    out = dict(base)
    out["mapping_version"] = f"real_world_modi_distributed_{selector}_v1_20260728"
    out["description"] = (
        "Distributed connector/local observation mapping. Base freeway/ramp/off-ramp "
        "observations are preserved; selected core signal-head links are added as "
        "urban-agent local queues and peripheral signal-head links are monitored only."
    )
    link_to_movements = {str(k): list(v) for k, v in dict(base.get("link_to_movements", {})).items()}
    link_to_origins = {str(k): list(v) for k, v in dict(base.get("link_to_origins", {})).items()}
    agents = dict(base.get("agents", {}))
    observable = {str(v) for v in base.get("observable_links", [])}
    movement_keys_by_signal: dict[str, list[str]] = {}
    movement_phase_by_key: dict[str, str] = {}
    for movement_key, spec in network_override["urban_movements"].items():
        movement_keys_by_signal.setdefault(str(spec.get("signal")), []).append(movement_key)
        movement_phase_by_key[movement_key] = str(spec.get("phase", ""))

    for row in rows:
        sc_no = int(row["no"])
        sid = signal_id(sc_no)
        links = owned_links_for_signal(row, link_owner_by_link)
        signal_movements = movement_keys_by_signal.get(sid, [])
        for link in links:
            observable.add(link)
            link_to_origins.setdefault(link, [])
            for leg in ("N", "S", "E", "W"):
                origin = f"{sid}_{leg}_out"
                if origin not in link_to_origins[link]:
                    link_to_origins[link].append(origin)
            entries = link_to_movements.setdefault(link, [])
            existing = {str(item.get("movement")) for item in entries if isinstance(item, dict)}
            link_axes = head_axes_by_sc.get(sc_no, {}).get(str(link), set())
            phase_filtered = [
                movement_key
                for movement_key in signal_movements
                if (
                    "unknown" in link_axes
                    or not link_axes
                    or (
                        "NS" in link_axes
                        and str(movement_phase_by_key.get(movement_key, "")).endswith("_p1")
                    )
                    or (
                        "EW" in link_axes
                        and str(movement_phase_by_key.get(movement_key, "")).endswith("_p2")
                    )
                )
            ] or list(signal_movements)
            for movement_key in phase_filtered:
                if movement_key not in existing:
                    entries.append({
                        "movement": movement_key,
                        "weight": 1.0,
                        "source": "signal_head_phase_axis",
                        "axes": sorted(link_axes) if link_axes else ["unknown"],
                    })
        agents[f"U_{sid}"] = {
            "kind": "urban",
            "signal": sid,
            "sc_no": sc_no,
            "name": row.get("name", ""),
            "control_enabled": True,
            "monitoring_only": False,
            "visible_links": links,
            "visible_movements": signal_movements,
            "visible_link_axes": {
                link: sorted(head_axes_by_sc.get(sc_no, {}).get(str(link), {"unknown"}))
                for link in links
            },
            "visible_ramps": [
                ramp for ramp, movements in network_override["on_ramp_to_movement"].items()
                if any(m in signal_movements for m in movements)
            ],
            "visible_off_ramps": [
                off for off, movements in network_override["off_ramp_to_movement"].items()
                if any(m in signal_movements for m in movements)
            ],
        }
    for row in monitor_rows:
        sc_no = int(row["no"])
        sid = signal_id(sc_no)
        links = [str(v) for v in parse_int_csv(row.get("unique_head_links", ""))]
        for link in links:
            observable.add(link)
            link_to_origins.setdefault(link, [])
        agents[f"MON_{sid}"] = {
            "kind": "urban_monitor",
            "signal": sid,
            "sc_no": sc_no,
            "name": row.get("name", ""),
            "control_enabled": False,
            "monitoring_only": True,
            "visible_links": links,
            "visible_link_axes": {
                link: sorted(head_axes_by_sc.get(sc_no, {}).get(str(link), {"unknown"}))
                for link in links
            },
            "visible_movements": [],
            "visible_ramps": [],
            "visible_off_ramps": [],
        }
    out["observable_links"] = sorted(int(v) for v in observable if str(v).strip().isdigit())
    out["link_to_movements"] = link_to_movements
    out["link_to_origins"] = link_to_origins
    out["agents"] = agents
    out["guardrails"] = {
        **dict(base.get("guardrails", {})),
        "distributed_urban_signal_players": {
            "enabled": True,
            "selector": selector,
            "controlled_signal_controllers": [int(row["no"]) for row in rows],
            "monitoring_only_signal_controllers": [int(row["no"]) for row in monitor_rows],
            "note": "Only controlled_signal_controllers enter the P-Stack urban follower/action space.",
        },
    }
    return out


def build_tuning_config(
    network_override: dict[str, Any],
    control_mapping_path: Path,
    detector_mapping_path: Path,
    selector: str,
    slug: str,
    monitor_rows: list[dict[str, str]],
) -> dict[str, Any]:
    signals = network_override["signals"]
    return {
        "extends": "real_world_modi_pstack_vsl_rollout_vissimdsd_20260725.json",
        "name": f"real_world_modi_pstack_distributed_{slug}_20260728",
        "description": (
            "Copy-only distributed urban-follower experiment. Keeps the validated real-world freeway/VSL/"
            "ramp setup, but expands urban signal control from one SC1 interface lever to selected "
            "individual core urban follower agents. Peripheral signal controllers remain observation-only."
        ),
        "mapping_json": str(control_mapping_path),
        "detector_mapping_json": str(detector_mapping_path),
        "urban_signal_selector": selector,
        "config_overrides": {
            "network": network_override,
            "mpc": {
                "follower_solver_mode": "distributed",
                "distributed_coupling_tol": 0.05,
                "stackelberg_allocation_mode": "simplified",
                "leader_candidate_count": 9,
                "leader_refinement_candidate_count": 5,
                "max_nash_iter": 4,
                "stackelberg_prefilter_top_k": 3,
                "stackelberg_prefilter_local_top_k": 3,
            },
            "urban_follower": {
                "allocation_pso_particles": 6,
                "allocation_pso_iterations": 8,
                "max_offset_step": 15.0,
                "offset_smoothness_weight": 0.08,
                "green_smoothness_weight": 0.08,
            },
        },
        "actuation": {
            "active_lever_mask": {
                "enabled": False,
                "allowed_signals": signals,
                "monitoring_only_signals": [signal_id(int(row["no"])) for row in monitor_rows],
            },
            "real_world_signal_control": {
                "enabled": True,
                "apply_to_no_control": False,
            },
        },
        "safety": {
            "original_files_unchanged": True,
            "copy_only_outputs": [
                str(control_mapping_path),
                str(detector_mapping_path),
            ],
        },
        "notes": [
            "This is an experiment config, not a promoted baseline.",
            "SC1 receives the freeway-interface ramp/off-ramp coupling when included in the selected control set.",
            "Monitoring-only signal controllers are scanned into local observations but are not listed in network.signals, so they do not get green/offset actions.",
            "The first smoke should be short because distributed urban agents enlarge the signal action space.",
        ],
    }


def write_generated_vbs(path: Path, base: dict[str, Any], detector_path: Path, observable_links: list[int], rows: list[dict[str, str]]) -> None:
    # 본선 체인/기하는 control_mapping.json이 정본이다(체인 정의는
    # evaluation/real_world_modi_control/freeway_mainline_chain.csv). 여기서 다시 계산하지 않는다.
    fw = base["freeway_model_links"]
    ramp_meters = base.get("ramp_meters", [])
    missing_chain = sorted(model for model, spec in fw.items() if "chain_links" not in spec)
    if missing_chain:
        raise SystemExit(
            f"control_mapping.json에 본선 체인 정보가 없다: {missing_chain}\n"
            "  python scripts/generate_real_world_control_mapping.py 를 먼저 다시 돌릴 것."
        )
    chain_links_all = sorted({int(link) for spec in fw.values() for link in spec["chain_links"]})
    lines = [
        "' Generated by scripts/generate_real_world_distributed_players.py",
        # 2: 본선이 링크 체인이 되면서 RW_*_CHAIN_LINKS / RW_*_CHAIN_OFFSETS_M 가 필수다.
        "RW_SCHEMA_VERSION = 2",
        'RW_FREEWAY_LINKS = "' + ",".join(str(v) for v in chain_links_all) + '"',
        'RW_FREEWAY_INPUT_LINKS = "26,74"',
        "RW_CLASSIFY_UNMATCHED_AS_URBAN = True",
    ]
    for model_link, var in (("FW_E", "RW_FW_E"), ("FW_W", "RW_FW_W")):
        spec = fw[model_link]
        chain_links = [int(v) for v in spec["chain_links"]]
        chain_offsets = [float(v) for v in spec["chain_offsets_m"]]
        lines.extend([
            f"{var}_LINK = {int(spec['physical_link'])}",
            f"{var}_LENGTH_M = {float(spec['length_m']):.6f}",
            f"{var}_LANES = {int(spec['lanes'])}",
            f'{var}_CHAIN_LINKS = "' + ",".join(str(v) for v in chain_links) + '"',
            f'{var}_CHAIN_OFFSETS_M = "' + ",".join(f"{v:.6f}" for v in chain_offsets) + '"',
            f'{var}_SEG_BOUNDS = "' + ",".join(f"{float(v):.6f}" for v in spec["segment_bounds_m"]) + '"',
            f'{var}_SEG_LENGTHS_KM = "' + ",".join(f"{float(v):.6f}" for v in spec["segment_length_profile_km"]) + '"',
        ])
    lines.extend([
        'RW_RAMP_METER_IDS = "' + ",".join(str(r["id"]) for r in ramp_meters) + '"',
        'RW_RAMP_METER_SCS = "' + ",".join(str(int(r["sc_no"])) for r in ramp_meters) + '"',
        'RW_RAMP_METER_CONNECTORS = "' + ",".join(str(int(r["connector"])) for r in ramp_meters) + '"',
        'RW_RAMP_METER_MODEL_KEYS = "' + ",".join(str(r["model_ramp_key"]) for r in ramp_meters) + '"',
        'RW_SIGNAL_SCS = "' + ",".join(str(int(row["no"])) for row in rows) + '"',
        'RW_LOCAL_OBSERVABLE_LINKS = "' + ",".join(str(int(v)) for v in observable_links) + '"',
        f'RW_DETECTOR_MAPPING_PATH = "{detector_path}"',
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_wrapper(
    path: Path,
    tuning_path: Path,
    mapping_path: Path,
    generated_path: Path,
    calibration_path: Path,
) -> None:
    text = (ROOT / "scripts/run_real_world_single_watchdog.ps1").read_text(encoding="utf-8")
    text = text.replace(
        'evaluation\\configs\\real_world_modi_pstack_adapter_v0_20260719.json',
        str(tuning_path.relative_to(ROOT)).replace("/", "\\"),
    )
    text = text.replace(
        'evaluation\\calibration\\real_world_modi_control_v0_20260719.json',
        str(calibration_path.relative_to(ROOT)).replace("/", "\\"),
    )
    text = text.replace(
        'evaluation\\real_world_modi_control\\control_mapping.json',
        str(mapping_path.relative_to(ROOT)).replace("/", "\\"),
    )
    text = text.replace(
        'evaluation\\generated\\real_world_modi_control_config.vbs',
        str(generated_path.relative_to(ROOT)).replace("/", "\\"),
    )
    path.write_text(text, encoding="utf-8")


def write_report(
    path: Path,
    rows: list[dict[str, str]],
    monitor_rows: list[dict[str, str]],
    files: dict[str, Path],
    detector: dict[str, Any],
    tuning: dict[str, Any],
) -> None:
    lines = [
        "# Real-world distributed urban followers, copy-only config",
        "",
        "Generated on 2026-07-28.",
        "",
        "## Selected Urban Signal Players",
        "",
        "| player | sc_no | name | signal heads | observed links |",
        "| --- | ---: | --- | ---: | ---: |",
    ]
    for row in rows:
        links = parse_int_csv(row.get("unique_head_links", ""))
        lines.append(
            f"| U_SC{int(row['no'])} | {int(row['no'])} | {row.get('name', '')} | "
            f"{int(float(row.get('signal_head_count') or 0))} | {len(links)} |"
        )
    lines.extend([
        "",
        "## Monitoring-Only Signal Controllers",
        "",
        "| monitor | sc_no | name | signal heads | observed links |",
        "| --- | ---: | --- | ---: | ---: |",
    ])
    for row in monitor_rows:
        links = parse_int_csv(row.get("unique_head_links", ""))
        lines.append(
            f"| MON_SC{int(row['no'])} | {int(row['no'])} | {row.get('name', '')} | "
            f"{int(float(row.get('signal_head_count') or 0))} | {len(links)} |"
        )
    lines.extend([
        "",
        "## Files",
        "",
    ])
    for label, file_path in files.items():
        lines.append(f"- {label}: `{file_path.relative_to(ROOT)}`")
    lines.extend([
        "",
        "## Structure",
        "",
        f"- Urban follower count in model config: `{len(tuning['config_overrides']['network']['signals'])}`",
        f"- Controlled urban SC agent count in detector mapping: `{len([k for k, v in detector.get('agents', {}).items() if str(k).startswith('U_SC') and v.get('control_enabled')])}`",
        f"- Monitoring-only SC agent count in detector mapping: `{len([k for k, v in detector.get('agents', {}).items() if str(k).startswith('MON_SC') and v.get('monitoring_only')])}`",
        f"- Observable links scanned by VBS: `{len(detector.get('observable_links', []))}`",
        "- Freeway/ramp VSL and metering mapping are copied from the validated base mapping.",
        "- Signal-head link queue attribution is derived from `.inpx` signal-head/SG names: EB/WB links feed EW/major movements and NB/SB links feed NS/minor movements.",
        "- In `core15`, SC1 is strict approach-only; ramp/off-ramp observations stay in freeway/base local observation rather than the SC1 urban follower.",
        "- `.layx` is treated as visual/layout validation only; `.inpx` is the plant and topology source.",
        "- Monitoring-only signals are not emitted as `kind=signal` rows in the action CSV.",
        "- Original files are not overwritten; use the distributed wrapper/config paths explicitly.",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selector", default="primary19", help="primary19, core15, all-active-heads, or comma-separated SC numbers")
    args = parser.parse_args()

    all_signal_rows = active_fixedtime_signal_rows(read_csv(DEFAULT_SIGNAL_ROLES))
    rows = selected_signal_rows(all_signal_rows, args.selector)
    slug = selector_slug(args.selector, len(rows))
    controlled_sc = {int(row["no"]) for row in rows}
    monitor_rows = [row for row in all_signal_rows if int(row["no"]) not in controlled_sc]
    base_mapping = read_json(DEFAULT_CONTROL_MAPPING)
    base_detector = read_json(DEFAULT_DETECTOR_MAPPING)
    head_axes_by_sc = signal_head_link_axes(DEFAULT_NETWORK)
    head_pos_by_sc = signal_head_link_max_pos(DEFAULT_NETWORK)
    # 인벤토리(modi.inpx 기준)에는 있지만 eval 네트워크에는 아직 없는 SC가 있으면
    # movement가 빈 채로 조용히 생성된다 — 2026-07-31 UF/SC 혼동과 같은 부류의
    # 침묵 실패라 여기서 끊는다. 네트워크 재빌드 순서는 아래 안내 참조.
    stale = sorted(controlled_sc - set(head_axes_by_sc))
    if stale:
        raise SystemExit(
            f"eval 네트워크에 없는 signal controller {stale}\n"
            f"  네트워크: {DEFAULT_NETWORK}\n"
            "  modi.inpx를 수정했다면 eval 네트워크를 먼저 재빌드할 것:\n"
            "    1) python scripts/prepare_real_world_modi_eval_copy.py\n"
            "    2) cscript //nologo scripts\\install_real_world_freeway_controls.vbs "
            "<sanitized.inpx> <sanitized.layx> <rw_control.inpx> <rw_control.layx> "
            "evaluation\\real_world_modi_control\\freeway_control_manifest.csv   (VISSIM COM 필요)\n"
            "    3) python scripts/generate_real_world_control_mapping.py\n"
            "    4) 이 스크립트 재실행"
        )
    link_owner_by_link = controlled_link_owner(rows, head_pos_by_sc)

    include_sc1_coupling = args.selector != "core15"
    network_override = build_network_override(rows, include_freeway_interface_coupling=include_sc1_coupling)
    network_override = prune_network_movements_to_observed_axes(
        network_override,
        rows,
        head_axes_by_sc,
        link_owner_by_link,
    )
    detector_path = OUT_DIR / f"detector_local_mapping_distributed_{slug}_20260728.json"
    mapping_path = OUT_DIR / f"control_mapping_distributed_{slug}_20260728.json"
    player_path = OUT_DIR / f"player_config_distributed_{slug}_20260728.json"
    tuning_path = CONFIG_DIR / f"real_world_modi_pstack_distributed_{slug}_20260728.json"
    generated_path = GENERATED_DIR / f"real_world_modi_control_config_distributed_{slug}_20260728.vbs"
    wrapper_name = "run_real_world_single_watchdog_distributed.ps1" if slug == "19sc" else f"run_real_world_single_watchdog_distributed_{slug}.ps1"
    report_name = "real_world_distributed_urban_followers_20260728.md" if slug == "19sc" else f"real_world_distributed_urban_followers_{slug}_20260728.md"
    wrapper_path = ROOT / f"scripts/{wrapper_name}"
    report_path = OUTPUTS_DIR / report_name

    detector = build_detector_mapping(
        base_detector,
        rows,
        monitor_rows,
        network_override,
        args.selector,
        head_axes_by_sc,
        link_owner_by_link,
    )
    mapping = build_control_mapping(base_mapping, rows, monitor_rows, detector_path, args.selector)
    tuning = build_tuning_config(network_override, mapping_path, detector_path, args.selector, slug, monitor_rows)
    player_config = {
        "schema_version": 1,
        "created_at": "2026-07-28",
        "mode": f"distributed_urban_signal_players_{slug}",
        "urban_signal_selector": args.selector,
        "controlled_signal_controllers": sorted(controlled_sc),
        "monitoring_only_signal_controllers": [int(row["no"]) for row in monitor_rows],
        "players": [
            {
                "id": "leader_network_manager",
                "kind": "leader",
                "state_scope": "whole network split into freeway links 2/26 and urban signal-player local observations",
                "controlled_followers": ["freeway_follower_real_world"] + [f"urban_follower_SC{int(row['no'])}" for row in rows],
            },
            {
                "id": "freeway_follower_real_world",
                "kind": "freeway_follower",
                "physical_links": [26, 2],
                "vsl_segments": [seg["segment_id"] for seg in base_mapping.get("segments", [])],
                "ramp_meters": [rm["id"] for rm in base_mapping.get("ramp_meters", [])],
            },
        ] + [
            {
                "id": f"urban_follower_SC{int(row['no'])}",
                "kind": "urban_follower",
                "signal_id": signal_id(int(row["no"])),
                "sc_no": int(row["no"]),
                "name": row.get("name", ""),
                "control_enabled": True,
                "local_observation_agent": f"U_{signal_id(int(row['no']))}",
            }
            for row in rows
        ] + [
            {
                "id": f"urban_monitor_SC{int(row['no'])}",
                "kind": "urban_monitor",
                "signal_id": signal_id(int(row["no"])),
                "sc_no": int(row["no"]),
                "name": row.get("name", ""),
                "control_enabled": False,
                "monitoring_only": True,
                "local_observation_agent": f"MON_{signal_id(int(row['no']))}",
            }
            for row in monitor_rows
        ],
        "source_files": {
            "signal_roles": str(DEFAULT_SIGNAL_ROLES),
            "network_inpx": str(DEFAULT_NETWORK),
            "base_control_mapping": str(DEFAULT_CONTROL_MAPPING),
        "base_detector_mapping": str(DEFAULT_DETECTOR_MAPPING),
        "prediction_calibration": str(DEFAULT_PREDICTION_CALIBRATION),
        },
    }

    write_json(detector_path, detector)
    write_json(mapping_path, mapping)
    write_json(player_path, player_config)
    write_json(tuning_path, tuning)
    write_generated_vbs(generated_path, base_mapping, detector_path, detector["observable_links"], rows)
    write_wrapper(wrapper_path, tuning_path, mapping_path, generated_path, DEFAULT_PREDICTION_CALIBRATION)
    write_report(report_path, rows, monitor_rows, {
        "control mapping": mapping_path,
        "detector mapping": detector_path,
        "player config": player_path,
        "P-Stack tuning": tuning_path,
        "generated VBS config": generated_path,
        "watchdog wrapper": wrapper_path,
    }, detector, tuning)

    print(f"signals={len(rows)}")
    print(f"monitoring_only_signals={len(monitor_rows)}")
    print(f"observable_links={len(detector['observable_links'])}")
    print(f"mapping={mapping_path}")
    print(f"detector={detector_path}")
    print(f"tuning={tuning_path}")
    print(f"wrapper={wrapper_path}")
    print(f"report={report_path}")


if __name__ == "__main__":
    main()
