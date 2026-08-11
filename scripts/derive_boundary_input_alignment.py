#!/usr/bin/env python3
# VISSIM 수요 유입 지점과 모델 경계 게이트(in_<SC>_<방위>)의 기하 정렬을 산출물로 봉인한다.
"""유입 지점마다 (링크, 실 방위, 하류 SC, 대응 게이트 또는 미대응 사유, 구간별 유량)을 낸다.

## 무엇을 푸는가

모델은 노드마다 이웃이 안 쓴 **정방위**(N/S/E/W)에 경계 게이트를 자동으로 심는다
(`generate_real_world_distributed_players.py:391-396`). 그 생성기는 VISSIM 을 보지 않는다.
반면 실제 수요는 VISSIM `vehicleInput` 34개에서만 들어온다. 둘이 기하적으로 맞는지가
격자 재정렬의 입력이므로, 여기서 **사실만** 봉인한다.

## 방위 규약 - 실측으로 푼 매듭

두 표가 같은 좌표계를 쓰는지부터 확인해야 했다.

    좌표계   `.inpx` 의 `linkPolyPoint` x/y 하나뿐이다. `netPara@northDir="0"` 이므로
             +y 가 북이다. SC centroid(`signal_controller_roles.csv:centroid_xy`)도
             같은 파일의 신호두 위치 평균이라 같은 프레임이다.
    향       `grid_node_legs` 의 grid leg 는 SC -> 이웃 SC 방위,
             `link_player_assignment.link_leg` 는 SC -> 접근로 시점 방위.
             둘 다 **교차로 중심에서 바깥으로** 향한다. 규약이 같다.

즉 좌표계·향은 어긋나 있지 않다. 어긋나는 것은 **추정기**다. `link_leg` 는 정지선 링크의
**시점**(교차로에서 멀리 떨어진 상류 끝)을 쓰는데, 그 점은 접근로가 굽거나 편심이면
접근 방위를 대표하지 못한다. 그래서 추정기 4종을 SG 이름(NBT/SBT/EBT/WBT = 진행 방향)이라는
**바깥 기준진리**에 대고 점수화해 산출물에 싣는다. 어느 추정기를 쓰느냐로 정렬 판정이
바뀌므로 정렬 집계도 추정기별로 둘 다 낸다. 판정은 하지 않는다.

## 조인

유입 링크에서 커넥터 그래프를 하류로 BFS 해 **처음 만나는 정지선**의 SC 가 그 수요를
받는 노드다. 그래프와 정지선 소유자는 `audit_plant_fidelity` 의
`_network_downstream` / `read_stop_owners` 를 그대로 쓴다 - 감사와 같은 근거를 쓰려는 것이다.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

from audit_plant_fidelity import _network_downstream, read_stop_owners  # noqa: E402

DEFAULT_NETWORK = REPO / "network" / "real_world_gaepo_modi" / "modi_eval_rw_control.inpx"
DEFAULT_VEHICLE_INPUTS = REPO / "evaluation" / "real_world_modi_inventory" / "vehicle_input_roles.csv"
DEFAULT_SC_ROLES = REPO / "evaluation" / "real_world_modi_inventory" / "signal_controller_roles.csv"
DEFAULT_ASSIGNMENT = REPO / "outputs" / "link_player_assignment_20260805.json"
DEFAULT_CONFIG = (
    REPO / "evaluation" / "configs" / "real_world_modi_pstack_distributed_core15n41_20260805.json"
)

LEG8 = ("E", "NE", "N", "NW", "W", "SW", "S", "SE")
CARDINAL_DEG = {"E": 0.0, "N": 90.0, "W": 180.0, "S": 270.0}
OPPOSITE = {"E": "W", "W": "E", "N": "S", "S": "N", "NE": "SW", "SW": "NE", "NW": "SE", "SE": "NW"}
TRAVEL_FROM_SG_NAME = {"NB": "N", "SB": "S", "EB": "E", "WB": "W"}
# 정렬 판정의 1차 추정기. 아래 scoreboard 에서 SG 이름 대비 총오차가 가장 작았다.
PRIMARY_ESTIMATOR = "link_chord_reversed"
MAX_HOPS = 60


def _bearing_deg(dx: float, dy: float) -> float:
    return math.degrees(math.atan2(dy, dx)) % 360.0


def _angle_gap(a: float, b: float) -> float:
    gap = abs(a - b) % 360.0
    return min(gap, 360.0 - gap)


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _point_at(points: list[tuple[float, float]], pos: float) -> tuple[float, float] | None:
    """폴리라인 위 거리 `pos` 의 점. 신호두는 링크 상 위치로만 주어진다."""
    if not points:
        return None
    walked = 0.0
    for start, end in zip(points, points[1:]):
        segment = math.dist(start, end)
        if segment > 0 and walked + segment >= pos:
            ratio = (pos - walked) / segment
            return (start[0] + ratio * (end[0] - start[0]), start[1] + ratio * (end[1] - start[1]))
        walked += segment
    return points[-1]


def _entry_class(role: str, name: str) -> str:
    if role != "urban_input":
        return "freeway"
    if "dummy" in name.lower():
        return "dummy"
    return "unnamed" if not name.strip() else "named"


def read_network(path: Path) -> dict[str, Any]:
    """`.inpx` 에서 기하·신호두·SG 이름·수요를 한 번에 읽는다."""
    root = ET.parse(path).getroot()
    points: dict[str, list[tuple[float, float]]] = {}
    for link in root.iter("link"):
        no = link.get("no")
        if no is None:
            continue
        points[str(no)] = [
            (float(p.get("x")), float(p.get("y"))) for p in link.iter("linkPolyPoint")
        ]

    sg_names: dict[tuple[str, str], str] = {}
    for controller in root.iter("signalController"):
        sc_no = str(controller.get("no"))
        for group in controller.iter("signalGroup"):
            sg_names[(sc_no, str(group.get("no")))] = str(group.get("name", ""))

    heads_by_link: dict[str, set[tuple[str, str]]] = defaultdict(set)
    head_xy: dict[tuple[str, str], list[tuple[float, float]]] = defaultdict(list)
    for head in root.iter("signalHead"):
        lane = (head.get("lane") or "").split()
        sg_ref = (head.get("sg") or "").split()
        if not lane or len(sg_ref) != 2:
            continue
        link_no, sc_no = lane[0], sg_ref[0]
        heads_by_link[link_no].add((sc_no, sg_ref[1]))
        xy = _point_at(points.get(link_no, []), float(head.get("pos") or 0.0))
        if xy is not None:
            head_xy[(sc_no, link_no)].append(xy)

    demand: dict[str, dict[str, Any]] = {}
    for element in root.iter("vehicleInput"):
        by_interval: dict[float, float] = defaultdict(float)
        for volume in element.iter("timeIntervalVehVolume"):
            slot = (volume.get("timeInt") or "").split()
            if len(slot) != 2:
                continue
            by_interval[float(slot[1]) / 1000.0] += float(volume.get("volume") or 0.0)
        ordered = sorted(by_interval.items())
        demand[str(element.get("no"))] = {
            "link": str(element.get("link")),
            "name": str(element.get("name", "")),
            "time_intervals_sec": [slot for slot, _ in ordered],
            "volumes_vph": [round(value, 6) for _, value in ordered],
        }

    north = next(root.iter("netPara"), None)
    return {
        "points": points,
        "sg_names": sg_names,
        "heads_by_link": dict(heads_by_link),
        "head_xy": dict(head_xy),
        "demand": demand,
        "north_dir_attribute": None if north is None else str(north.get("northDir")),
    }


def read_centroids(path: Path) -> dict[str, tuple[float, float]]:
    centroids: dict[str, tuple[float, float]] = {}
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            if str(row.get("active", "")).lower() != "true":
                continue
            try:
                xy = json.loads(row.get("centroid_xy") or "[]")
                sc_no = str(int(float(str(row.get("no", "")))))
            except (ValueError, json.JSONDecodeError):
                continue
            if len(xy) == 2:
                centroids[sc_no] = (float(xy[0]), float(xy[1]))
    return centroids


def first_downstream_stop_line(
    link: str, downstream: dict[str, set[str]], stop_owners: dict[str, str]
) -> tuple[str | None, int | None, str | None, list[str]]:
    """유입 링크 -> (SC, 홉수, 정지선 링크, 같은 홉의 다른 종단들)."""
    if link in stop_owners:
        return stop_owners[link], 0, link, []
    seen = {link}
    frontier = sorted(downstream.get(link, set()) - seen, key=int)
    for hop in range(1, MAX_HOPS + 1):
        if not frontier:
            break
        seen.update(frontier)
        hits = sorted(
            (node for node in frontier if node in stop_owners),
            key=lambda node: (int(stop_owners[node]), int(node)),
        )
        if hits:
            ties = [f"SC{stop_owners[node]}@{node}" for node in hits[1:]]
            return stop_owners[hits[0]], hop, hits[0], ties
        following: set[str] = set()
        for node in frontier:
            following |= downstream.get(node, set())
        frontier = sorted(following - seen, key=int)
    return None, None, None, []


def leg_estimates(
    stop_link: str | None,
    sc_no: str | None,
    network: dict[str, Any],
    centroids: dict[str, tuple[float, float]],
) -> dict[str, float | None]:
    """접근 leg 방위(도) 추정기 4종. 전부 교차로 바깥을 향한다."""
    estimates: dict[str, float | None] = {
        "centroid_to_link_start": None,
        "link_chord_reversed": None,
        "link_last_segment_reversed": None,
        "centroid_to_signal_head": None,
    }
    points = network["points"].get(stop_link or "", [])
    if len(points) >= 2:
        estimates["link_chord_reversed"] = _bearing_deg(
            points[0][0] - points[-1][0], points[0][1] - points[-1][1]
        )
        estimates["link_last_segment_reversed"] = _bearing_deg(
            points[-2][0] - points[-1][0], points[-2][1] - points[-1][1]
        )
    centre = centroids.get(sc_no or "")
    if centre is not None and points:
        estimates["centroid_to_link_start"] = _bearing_deg(
            points[0][0] - centre[0], points[0][1] - centre[1]
        )
        heads = network["head_xy"].get((sc_no or "", stop_link or ""), [])
        if heads:
            hx = sum(p[0] for p in heads) / len(heads)
            hy = sum(p[1] for p in heads) / len(heads)
            estimates["centroid_to_signal_head"] = _bearing_deg(hx - centre[0], hy - centre[1])
    return estimates


def _leg_of(bearing: float | None) -> str | None:
    if bearing is None:
        return None
    return LEG8[int((bearing + 22.5) // 45.0) % 8]


def score_estimators(
    network: dict[str, Any], stop_owners: dict[str, str], centroids: dict[str, tuple[float, float]]
) -> list[dict[str, Any]]:
    """SG 이름(진행 방향)을 바깥 기준진리로 삼아 추정기를 점수화한다.

    이름이 방향 하나로 확정되고 신호두가 SC 하나만 가리키는 정지선 링크만 쓴다.
    잔차 중앙값은 추정기 오차가 아니라 **도로망이 좌표축에서 돌아간 각**을 포함한다.
    비교는 상대 순위와 45도 초과 총오차 건수로 한다.
    """
    errors: dict[str, list[float]] = defaultdict(list)
    for link, refs in network["heads_by_link"].items():
        controllers = {sc for sc, _ in refs}
        if len(controllers) != 1:
            continue
        sc_no = controllers.pop()
        if sc_no not in centroids or stop_owners.get(link) != sc_no:
            continue
        travels = {
            TRAVEL_FROM_SG_NAME[name[:2]]
            for name in (network["sg_names"].get(ref, "") for ref in refs)
            if name[:2] in TRAVEL_FROM_SG_NAME
        }
        if len(travels) != 1:
            continue
        truth = CARDINAL_DEG[OPPOSITE[travels.pop()]]
        for name, bearing in leg_estimates(link, sc_no, network, centroids).items():
            if bearing is not None:
                errors[name].append(_angle_gap(bearing, truth))
    board: list[dict[str, Any]] = []
    for name in ("centroid_to_link_start", "link_chord_reversed",
                 "link_last_segment_reversed", "centroid_to_signal_head"):
        values = errors.get(name, [])
        board.append(
            {
                "estimator": name,
                "n": len(values),
                "median_abs_error_deg": round(statistics.median(values), 3) if values else None,
                "mean_abs_error_deg": round(statistics.fmean(values), 3) if values else None,
                "gross_error_gt_45deg": sum(1 for value in values if value > 45.0),
                "is_primary": name == PRIMARY_ESTIMATOR,
            }
        )
    return board


def reproduce_assignment_leg(
    assignment: dict[str, Any], network: dict[str, Any], centroids: dict[str, tuple[float, float]]
) -> dict[str, Any]:
    """`link_leg` 를 centroid->정지선시점 추정기로 재현한다. 규약 동일성의 증거."""
    stop_of = assignment.get("link_stop_line") or {}
    owner = assignment.get("link_owner") or {}
    checked = matched = 0
    mismatches: list[dict[str, str]] = []
    for link, leg in (assignment.get("link_leg") or {}).items():
        stop_link = str(stop_of.get(link, ""))
        sc_no = str(owner.get(link, ""))
        bearing = leg_estimates(stop_link, sc_no, network, centroids)["centroid_to_link_start"]
        if bearing is None:
            continue
        checked += 1
        if _leg_of(bearing) == leg:
            matched += 1
        elif len(mismatches) < 20:
            mismatches.append({"link": link, "artifact": leg, "recomputed": _leg_of(bearing)})
    return {
        "estimator": "centroid_to_link_start",
        "n": checked,
        "match": matched,
        "mismatch_examples": mismatches,
    }


def _model_legs(config: dict[str, Any]) -> tuple[dict[str, Any], list[str], list[str]]:
    network = (config.get("config_overrides") or {}).get("network") or {}
    return (
        network.get("grid_node_legs") or {},
        [str(value) for value in network.get("boundary_in_links") or []],
        [str(value) for value in network.get("boundary_out_links") or []],
    )


def match_gate(node: str, leg: str | None, grid_node_legs: dict[str, Any]) -> dict[str, Any]:
    """노드의 leg 목록에서 그 방위를 찾는다. 경계 게이트만 정렬로 센다."""
    if node not in grid_node_legs:
        return {"status": "unaligned", "reason": "node_absent_from_model", "gate": None}
    if leg is None:
        return {"status": "unaligned", "reason": "leg_undetermined", "gate": None}
    kinds: set[str] = set()
    for key, spec in grid_node_legs[node].items():
        if str(key).split("_", 1)[0] != leg or not isinstance(spec, dict):
            continue
        kind = str(spec.get("type", ""))
        kinds.add(kind)
        if kind == "boundary":
            return {"status": "aligned", "reason": "boundary_gate_on_same_leg",
                    "gate": str(spec.get("in", ""))}
    if "grid" in kinds:
        reason = "leg_occupied_by_grid_neighbour"
    elif "ramp" in kinds:
        reason = "leg_occupied_by_ramp"
    else:
        reason = "leg_absent_at_node"
    return {"status": "unaligned", "reason": reason, "gate": None}


def _volume_totals(rows: list[dict[str, Any]]) -> dict[str, float]:
    return {
        "first_volume_vph": round(
            sum(row["volumes_vph"][0] for row in rows if row["volumes_vph"]), 6
        ),
        "peak_volume_vph": round(
            sum(max(row["volumes_vph"]) for row in rows if row["volumes_vph"]), 6
        ),
    }


def _estimator_summary(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    aligned = [row for row in rows if row["alignment"][key]["status"] == "aligned"]
    unaligned = [row for row in rows if row["alignment"][key]["status"] != "aligned"]
    reasons: dict[str, int] = defaultdict(int)
    for row in unaligned:
        reasons[row["alignment"][key]["reason"]] += 1
    diagonal = sum(1 for row in rows if row["leg"][key] in ("NE", "NW", "SE", "SW"))
    return {
        "aligned": len(aligned),
        "unaligned": len(unaligned),
        "diagonal_leg": diagonal,
        "cardinal_leg": sum(1 for row in rows if row["leg"][key] in CARDINAL_DEG),
        "undetermined_leg": sum(1 for row in rows if row["leg"][key] is None),
        "unaligned_reasons": dict(sorted(reasons.items())),
        "aligned_volume": _volume_totals(aligned),
        "unaligned_volume": _volume_totals(unaligned),
        "matched_gates": sorted({row["alignment"][key]["gate"] for row in aligned}),
    }


def derive(
    network_path: Path = DEFAULT_NETWORK,
    vehicle_input_roles_path: Path = DEFAULT_VEHICLE_INPUTS,
    sc_roles_path: Path = DEFAULT_SC_ROLES,
    assignment_path: Path = DEFAULT_ASSIGNMENT,
    config_path: Path = DEFAULT_CONFIG,
) -> dict[str, Any]:
    network_path = Path(network_path)
    network = read_network(network_path)
    centroids = read_centroids(sc_roles_path)
    downstream, graph_error = _network_downstream(network_path)
    if graph_error:
        raise SystemExit(f"network graph unavailable: {graph_error}")
    stop_owners, owner_error = read_stop_owners(Path(sc_roles_path))
    if owner_error:
        raise SystemExit(f"stop-line owners unavailable: {owner_error}")
    assignment = json.loads(Path(assignment_path).read_text(encoding="utf-8"))
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    grid_node_legs, boundary_in, boundary_out = _model_legs(config)
    assignment_leg = assignment.get("link_leg") or {}

    rows: list[dict[str, Any]] = []
    with Path(vehicle_input_roles_path).open(newline="", encoding="utf-8-sig") as handle:
        roles = list(csv.DictReader(handle))
    for role_row in roles:
        vi_no = str(int(float(str(role_row["no"]))))
        link = str(int(float(str(role_row["link"]))))
        role = str(role_row.get("role", ""))
        declared = network["demand"].get(vi_no, {})
        name = str(declared.get("name") or role_row.get("name") or "")
        sc_no, hops, stop_link, ties = first_downstream_stop_line(link, downstream, stop_owners)
        bearings = leg_estimates(stop_link, sc_no, network, centroids)
        node = f"SC{sc_no}" if sc_no else None
        leg = {
            "link_geometry": _leg_of(bearings[PRIMARY_ESTIMATOR]),
            "link_last_segment": _leg_of(bearings["link_last_segment_reversed"]),
            "centroid_to_link_start": _leg_of(bearings["centroid_to_link_start"]),
            "centroid_to_signal_head": _leg_of(bearings["centroid_to_signal_head"]),
            "assignment": assignment_leg.get(link),
        }
        node_legs = grid_node_legs.get(node or "", {})
        rows.append(
            {
                "vehicle_input_no": vi_no,
                "link": link,
                "name": name,
                "role": role,
                "entry_class": _entry_class(role, name),
                "time_intervals_sec": declared.get("time_intervals_sec", []),
                "volumes_vph": declared.get("volumes_vph", []),
                "downstream_sc": sc_no,
                "downstream_hops": hops,
                "downstream_ties": ties,
                "stop_line_link": stop_link,
                "leg_bearing_deg": {
                    key: None if value is None else round(value, 3)
                    for key, value in bearings.items()
                },
                "leg": leg,
                "model_node": node,
                "model_node_present": node in grid_node_legs,
                "model_node_boundary_gates": sorted(
                    key for key, spec in node_legs.items()
                    if isinstance(spec, dict) and spec.get("type") == "boundary"
                ),
                "model_node_grid_legs": sorted(
                    key for key, spec in node_legs.items()
                    if isinstance(spec, dict) and spec.get("type") == "grid"
                ),
                "alignment": {
                    "link_geometry": match_gate(node or "", leg["link_geometry"], grid_node_legs),
                    "assignment": match_gate(node or "", leg["assignment"], grid_node_legs),
                },
            }
        )

    by_class: dict[str, int] = defaultdict(int)
    for row in rows:
        by_class[row["entry_class"]] += 1
    urban = [row for row in rows if row["entry_class"] in ("named", "unnamed")]
    dummy = [row for row in rows if row["entry_class"] == "dummy"]
    matched_by_estimator = {
        key: {gate for row in urban if row["alignment"][key]["status"] == "aligned"
              for gate in [row["alignment"][key]["gate"]]}
        for key in ("link_geometry", "assignment")
    }
    declared_in = set(boundary_in)

    return {
        "schema_version": 1,
        "generator": "scripts/derive_boundary_input_alignment.py",
        "sources": {
            "network": {"path": str(network_path), "sha256": _sha256(network_path)},
            "vehicle_input_roles": {
                "path": str(vehicle_input_roles_path),
                "sha256": _sha256(vehicle_input_roles_path),
            },
            "sc_roles": {"path": str(sc_roles_path), "sha256": _sha256(sc_roles_path)},
            "assignment": {"path": str(assignment_path), "sha256": _sha256(assignment_path)},
            "config": {"path": str(config_path), "sha256": _sha256(config_path)},
        },
        "bearing_convention": {
            "frame": "inpx linkPolyPoint x/y; SC centroid = mean signal-head position (same frame)",
            "north_dir_attribute": network["north_dir_attribute"],
            "leg_orientation": "outward_from_intersection_centre",
            "primary_estimator": PRIMARY_ESTIMATOR,
            "ground_truth": "signal group names NBT/SBT/EBT/WBT declare the travel direction; "
                            "the approach leg is its opposite",
            "estimator_scoreboard": score_estimators(network, stop_owners, centroids),
            "assignment_leg_reproduction": reproduce_assignment_leg(
                assignment, network, centroids
            ),
        },
        "vehicle_inputs": rows,
        "summary": {
            "vehicle_input_count": len(rows),
            "by_role": dict(sorted({
                role: sum(1 for row in rows if row["role"] == role) for role in
                {row["role"] for row in rows}
            }.items())),
            "by_entry_class": dict(sorted(by_class.items())),
            "join": {
                "resolved": sum(1 for row in rows if row["downstream_sc"]),
                "unresolved": sum(1 for row in rows if not row["downstream_sc"]),
            },
            "urban_entry_points": {
                "count": len(urban),
                **_volume_totals(urban),
                "by_entry_class": {
                    name: {
                        "count": sum(1 for row in urban if row["entry_class"] == name),
                        **_volume_totals([row for row in urban if row["entry_class"] == name]),
                    }
                    for name in ("named", "unnamed")
                },
                "by_estimator": {
                    key: _estimator_summary(urban, key)
                    for key in ("link_geometry", "assignment")
                },
            },
            "dummy_inputs": {"count": len(dummy), **_volume_totals(dummy)},
            "model_gates": {
                "node_count": len(grid_node_legs),
                "boundary_leg_count": sum(
                    1 for legs in grid_node_legs.values() for spec in legs.values()
                    if isinstance(spec, dict) and spec.get("type") == "boundary"
                ),
                "boundary_in_declared": len(boundary_in),
                "boundary_out_declared": len(boundary_out),
                "gates_with_matched_input_link_geometry": len(
                    matched_by_estimator["link_geometry"] & declared_in
                ),
                "gates_without_matched_input_link_geometry": len(
                    declared_in - matched_by_estimator["link_geometry"]
                ),
                "gates_with_matched_input_assignment": len(
                    matched_by_estimator["assignment"] & declared_in
                ),
                "gates_without_matched_input_assignment": len(
                    declared_in - matched_by_estimator["assignment"]
                ),
            },
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--network", default=str(DEFAULT_NETWORK))
    parser.add_argument("--vehicle-inputs", default=str(DEFAULT_VEHICLE_INPUTS))
    parser.add_argument("--sc-roles", default=str(DEFAULT_SC_ROLES))
    parser.add_argument("--assignment", default=str(DEFAULT_ASSIGNMENT))
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--json-out", default="")
    args = parser.parse_args()

    artifact = derive(
        network_path=Path(args.network),
        vehicle_input_roles_path=Path(args.vehicle_inputs),
        sc_roles_path=Path(args.sc_roles),
        assignment_path=Path(args.assignment),
        config_path=Path(args.config),
    )
    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(artifact, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
        print(f"JSON={out}")
    summary = artifact["summary"]
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
