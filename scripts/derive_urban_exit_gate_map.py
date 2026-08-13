# VISSIM 도시부 유출 링크를 모델 경계 게이트(out)에 잇는 대장(CSV)을 만든다
"""`derive_urban_input_gate_map.py` 의 **유출 짝**.

왜 필요한가.
    유입은 `urban_input_gate_map` 이 있는데 유출은 대장이 없다. 그래서
    `grid_node_legs` 의 경계 leg 이 실재하는지 판정할 근거가 **한쪽뿐**이었고,
    2026-08-13 실측에서 경계 leg 130개 중 유입 게이트가 붙은 것은 18개, 정지선
    신호두가 증언하는 것은 12개뿐이었다. 나머지 118개는 유입 근거로는 유령인데,
    **유출은 살아 있을 수 있다** — 유출은 내부 큐에서 빠져나가므로 유입 수요가 0이어도
    차량이 나간다. 그 판정을 하려면 이 대장이 있어야 한다.

유입과 결정적으로 다른 점.
    유입 대장은 vehicle input 의 **유량(vph)** 과 조인해서 총량으로 검증된다.
    유출은 sink 라 고유 유량이 없다 — 나가는 양은 신호가 통과시킨 만큼이다.
    그래서 이 대장은 **위상 조인일 뿐 수요 계약으로 검증할 수단이 없다.**
    유입 대장과 같은 수준의 근거를 기대하면 안 된다.

leg 방위 규칙.
    유출 링크가 교차로에서 **떠나는 방향**이 그 leg 이다. 링크 첫 점에 가장 가까운
    SC 중심을 출발 교차로로 보고(반경 안), 그 중심에서 링크 끝점으로의 방위각을
    8방위로 접는다. 유입 대장의 폴백 규칙(`leg.link_geometry`)과 같은 계열이다.
    유입처럼 이름 접미사를 먼저 쓰지 않는 이유는, 유출 링크에는 진행방향 접미사가
    붙은 이름이 거의 없기 때문이다(실측 226개 중 이름 있는 것 소수).

게이트 이름은 문자열로 짓지 않는다. config 의
`config_overrides.network.grid_node_legs[node][<leg>_*]["out"]` 에서 **읽어 온다**.
그 leg 에 boundary 가 없으면 사유를 status 에 남긴다 - 조용히 버리지 않는다.

    python scripts/derive_urban_exit_gate_map.py --out <csv>
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
DEFAULT_NETWORK = REPO / "network/real_world_gaepo_modi/modi_eval_rw_control_n4dr150_20260812.inpx"
DEFAULT_ROLES = REPO / "evaluation/real_world_modi_inventory/signal_controller_roles_n4dr150_20260812.csv"
DEFAULT_ASSIGNMENT = REPO / "outputs/link_player_assignment_20260805.json"
DEFAULT_CONFIG = REPO / "evaluation/configs/real_world_modi_pstack_distributed_core15n41legfix_20260812.json"

# assign_links_to_players.py 의 FREEWAY_LINKS 와 같은 집합이다. 두 곳이 갈리면 안 된다.
FREEWAY_MAINLINE = {"2", "24", "26", "74", "10699", "10702"}

BEARING_TO_LEG = [(0, "N"), (45, "NE"), (90, "E"), (135, "SE"),
                  (180, "S"), (225, "SW"), (270, "W"), (315, "NW")]

FIELDS = [
    "no",
    "gate",
    "status",
    "leg",
    "leg_source",
    "model_node",
    "link",
    "out_link",
    "lanes",
    "len_m",
    "bearing_deg",
    "dist_to_node_m",
    "name",  # 이름에 콤마가 들어갈 수 있어 **마지막**. 유입 대장과 같은 이유.
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def leg_from_bearing(deg: float) -> str:
    best, bd = "N", 999.0
    for ref, leg in BEARING_TO_LEG:
        d = abs((deg - ref + 180) % 360 - 180)
        if d < bd:
            best, bd = leg, d
    return best


def gate_on_leg(node: str, leg: str | None, grid_node_legs: dict[str, Any]) -> tuple[str, str, str]:
    """(gate, out_link, status). 이름은 config 에서 읽는다 - 문자열로 짓지 않는다."""
    if not node or node not in grid_node_legs:
        return "", "", "node_absent_from_model"
    if leg is None:
        return "", "", "leg_undetermined"
    kinds: set[str] = set()
    for key, spec in grid_node_legs[node].items():
        if str(key).split("_", 1)[0] != leg or not isinstance(spec, dict):
            continue
        kind = str(spec.get("type", ""))
        kinds.add(kind)
        if kind == "boundary":
            return str(spec.get("out", "")), str(spec.get("out_link", "")), "mapped"
    if "grid" in kinds:
        return "", "", "leg_occupied_by_grid_neighbour"
    if "ramp" in kinds:
        return "", "", "leg_occupied_by_ramp"
    return "", "", "leg_absent_at_node"


def load_network(path: Path) -> tuple[dict[str, list[tuple[float, float]]], dict[str, dict[str, Any]]]:
    root = ET.parse(path).getroot()
    pts: dict[str, list[tuple[float, float]]] = {}
    meta: dict[str, dict[str, Any]] = {}
    for ln in root.find("links"):
        no = ln.get("no")
        pp = ln.find("./geometry/linkPolyPts")
        if no is None or pp is None:
            continue
        poly = [(float(p.get("x")), float(p.get("y"))) for p in pp]
        if len(poly) < 2:
            continue
        pts[no] = poly
        lanes = ln.find("lanes")
        meta[no] = {"lanes": len(list(lanes)) if lanes is not None else 0,
                    "name": (ln.get("name") or "").strip()}
    return pts, meta


def load_centroids(path: Path) -> dict[str, tuple[float, float]]:
    out: dict[str, tuple[float, float]] = {}
    with path.open(newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            raw = (row.get("centroid_xy") or "").strip()
            if raw.startswith("["):
                a, b = json.loads(raw)
                out["SC" + str(row["no"]).strip()] = (float(a), float(b))
    return out


def build_rows(exits, pts, meta, centroid, grid_node_legs, ramp, radius) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for lid in sorted(exits, key=lambda s: (len(s), s)):
        poly = pts.get(lid)
        row: dict[str, Any] = {k: "" for k in FIELDS}
        row["no"] = lid
        row["link"] = lid
        if poly:
            row["lanes"] = meta.get(lid, {}).get("lanes", "")
            row["name"] = meta.get(lid, {}).get("name", "")
            row["len_m"] = round(sum(math.dist(poly[i], poly[i + 1]) for i in range(len(poly) - 1)), 1)
        if lid in FREEWAY_MAINLINE or lid in ramp:
            row["status"] = "freeway_excluded"
            rows.append(row)
            continue
        if not poly:
            row["status"] = "geometry_absent"
            rows.append(row)
            continue
        sx, sy = poly[0]
        node, dist = "", float("inf")
        for n, (cx, cy) in centroid.items():
            d = math.hypot(sx - cx, sy - cy)
            if d < dist:
                node, dist = n, d
        if dist > radius:
            row["status"] = "unattributed_beyond_radius"
            row["dist_to_node_m"] = round(dist, 1)
            rows.append(row)
            continue
        cx, cy = centroid[node]
        ex, ey = poly[-1]
        bearing = math.degrees(math.atan2(ex - cx, ey - cy)) % 360
        leg = leg_from_bearing(bearing)
        gate, out_link, status = gate_on_leg(node, leg, grid_node_legs)
        row.update({"model_node": node, "leg": leg, "leg_source": "link_geometry",
                    "bearing_deg": round(bearing, 1), "dist_to_node_m": round(dist, 1),
                    "gate": gate, "out_link": out_link, "status": status})
        rows.append(row)
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--network", default=str(DEFAULT_NETWORK))
    ap.add_argument("--roles", default=str(DEFAULT_ROLES))
    ap.add_argument("--assignment", default=str(DEFAULT_ASSIGNMENT))
    ap.add_argument("--config", default=str(DEFAULT_CONFIG))
    ap.add_argument("--radius", type=float, default=120.0,
                    help="유출 링크 시작점이 이 반경 안이면 그 교차로에서 나가는 것으로 본다")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    net_path, cfg_path, ass_path = Path(args.network), Path(args.config), Path(args.assignment)
    ass = json.loads(ass_path.read_text(encoding="utf-8"))
    config = json.loads(cfg_path.read_text(encoding="utf-8"))
    grid_node_legs = config["config_overrides"]["network"]["grid_node_legs"]

    pts, meta = load_network(net_path)
    centroid = load_centroids(Path(args.roles))
    exits = [l for l in ass.get("monitor_only_exit_links", [])]
    ramp = set(ass.get("freeway_bound_links", []))

    rows = build_rows(exits, pts, meta, centroid, grid_node_legs, ramp, args.radius)

    by_status: dict[str, int] = {}
    for row in rows:
        by_status[row["status"]] = by_status.get(row["status"], 0) + 1
    mapped = [r for r in rows if r["status"] == "mapped"]
    gates = sorted({r["gate"] for r in mapped})
    nodes = sorted({r["model_node"] for r in mapped}, key=lambda s: (len(s), s))

    provenance = [
        "generated by scripts/derive_urban_exit_gate_map.py",
        f"network={net_path.as_posix()} sha256={sha256(net_path)}",
        f"config={cfg_path.as_posix()} sha256={sha256(cfg_path)}",
        f"assignment={ass_path.as_posix()} sha256={sha256(ass_path)}",
        f"leg rule: departure bearing from node centroid -> 8-way; radius={args.radius:.0f} m",
        "no volume column by design - exits are sinks, throughput is whatever the signal passes",
        f"expected_mapped={len(mapped)}",
    ]
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        for line in provenance:
            fh.write(f"# {line}\n")
        writer = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(json.dumps({"exit_links": len(rows), "by_status": by_status,
                      "distinct_gates": len(gates), "distinct_nodes": len(nodes),
                      "nodes": nodes}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
