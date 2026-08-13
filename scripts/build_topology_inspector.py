# 격자 토폴로지 검사 도면을 단일 HTML 로 굽는다.
#
# 왜 필요한가.
#   `grid_node_legs` 는 손으로 읽어서 검증할 수 있는 크기가 아니다(노드 41, leg 264).
#   2026-08-13 에 이 도면으로 세 가지를 찾았다 — 자유 우회전으로 제어 신호를 관통한 인접 8쌍,
#   고속도로 본선·램프를 타고 이어진 "도시" 인접 7쌍, 실제 유입 게이트가 없는 경계 leg 112개.
#   전부 숫자만 봐서는 안 보이고 실제 도로 형상 위에 겹쳐야 보였다.
#
# 무엇을 그리나.
#   바탕      inpx 의 링크 폴리라인 전부(도시/고속도로 본선/램프를 구분)
#   위        모델이 주장하는 인접(구 규칙 vs 새 규칙을 겹쳐서 차이를 보여준다)
#   노드 클릭 그 교차로가 **소유한 링크**(approach queue 범위)를 강조하고 목록을 낸다
#
# 사용:
#   python scripts/build_topology_inspector.py --out outputs/topology_inspector.html
import argparse
import csv
import io
import json
import os
import sys
import xml.etree.ElementTree as ET

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
J = lambda *p: os.path.join(REPO, *p)

FREEWAY_MAINLINE = {"2", "24", "26", "74", "10699", "10702"}


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _deep_update(base, over):
    out = dict(base)
    for k, v in over.items():
        out[k] = _deep_update(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def load_config_chain(path):
    """evaluation config 의 `extends` 를 풀어 합친다.

    어댑터(`vissim_stackelberg_adapter.load_optional_json`)와 같은 규칙이다 — 자식이 이긴다.
    이걸 안 하면 부모에만 있는 `grid_node_legs` 가 안 보인다.
    """
    path = os.path.abspath(path)
    data = load_json(path)
    ext = data.get("extends", "")
    if not ext:
        return data
    parent = ext if os.path.isabs(ext) else os.path.join(os.path.dirname(path), ext)
    child = dict(data)
    child.pop("extends", None)
    return _deep_update(load_config_chain(parent), child)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=J("evaluation", "configs",
                    "real_world_modi_pstack_distributed_core15n41legfix_20260812.json"))
    ap.add_argument("--network", default=J("network", "real_world_gaepo_modi",
                    "modi_eval_rw_control_n4dr150_20260812.inpx"))
    ap.add_argument("--roles", default=J("evaluation", "real_world_modi_inventory",
                    "signal_controller_roles_n4dr150_20260812.csv"))
    ap.add_argument("--assignment", default=J("outputs", "link_player_assignment_20260805.json"))
    ap.add_argument("--follower-map", default=J("evaluation", "real_world_modi_inventory",
                    "urban_follower_sc_map.csv"))
    ap.add_argument("--gate-map", default=J("evaluation", "real_world_modi_inventory",
                    "urban_input_gate_map_legfix_20260813.csv"))
    ap.add_argument("--adjacency-a", default=J("outputs", "intersection_adjacency_n4dr150_baseline_20260813.json"),
                    help="비교 기준(구 규칙)")
    ap.add_argument("--adjacency-b", default=J("outputs", "intersection_adjacency_n4dr150_geo30_20260813.json"),
                    help="비교 대상(새 규칙)")
    ap.add_argument("--out", default=J("outputs", "topology_inspector.html"))
    ap.add_argument("--view", choices=["inspect", "clean"], default="inspect",
                    help="inspect = 감사용(구·새 인접 겹침, 소유 링크 강조), "
                         "clean = 새 규칙 결과만 읽기 쉽게 그린 판")
    args = ap.parse_args()

    cfg_net = load_config_chain(args.config)["config_overrides"]["network"]
    legs = cfg_net["grid_node_legs"]
    controlled = set(cfg_net["signals"])

    ass = load_json(args.assignment)
    own = ass["link_owner"]
    link_leg = ass.get("link_leg", {})
    geom_meta = ass.get("link_geometry", {})
    ramp = set(ass.get("freeway_bound_links", []))

    # 좌표·이름
    xy, name = {}, {}
    with open(args.roles, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            node = "SC" + str(row["no"]).strip()
            raw = (row.get("centroid_xy") or "").strip()
            if raw.startswith("["):
                a, b = json.loads(raw)
                xy[node] = (round(float(a), 1), round(float(b), 1))
            name[node] = (row.get("name") or "").strip()

    follower = {}
    with open(args.follower_map, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            follower["SC" + str(row["sc_no"]).strip()] = int(row["urban_follower_id"])

    gate_legs, gates = set(), []
    with open(args.gate_map, encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader([l for l in fh if not l.startswith("#")]))
    for row in rows:
        if row.get("gate"):
            gate_legs.add(row["model_node"] + "|" + row.get("leg", ""))
            gates.append({"gate": row["gate"], "node": row["model_node"],
                          "leg": row.get("leg", ""), "peak": row.get("peak_volume_vph", "")})
    gate_nodes = {g["node"] for g in gates}

    # 링크 형상
    root = ET.parse(args.network).getroot()
    links = []
    for ln in root.find("links"):
        no = ln.get("no")
        pp = ln.find("./geometry/linkPolyPts")
        if no is None or pp is None:
            continue
        pts = [(round(float(p.get("x")), 1), round(float(p.get("y")), 1)) for p in pp]
        if len(pts) < 2:
            continue
        kind = ("FW" if no in FREEWAY_MAINLINE else "RAMP" if no in ramp
                else "URBAN" if own.get(no) else "OTHER")
        links.append({"no": no, "kind": kind, "owner": own.get(no),
                      "leg": link_leg.get(no, ""),
                      "len": round(float((geom_meta.get(no) or {}).get("len_m", 0) or 0), 1),
                      "pts": [c for p in pts for c in p]})

    def undirected(path):
        d = load_json(path)
        return sorted({tuple(sorted(("SC%d" % int(k), "SC%d" % int(v))))
                       for k, vs in d["adjacency"].items() for v in vs}), d

    adjA, rawA = undirected(args.adjacency_a)
    adjB, rawB = undirected(args.adjacency_b)
    setA, setB = set(adjA), set(adjB)

    # 도면에서 다르게 그릴 노드 — player 를 지정했으면 **비-player 전부**, 아니면 통과 노드.
    deriv = rawB.get("derivation", {}) or {}
    player_ids = {"SC%d" % n for n in (deriv.get("player_nodes") or [])}
    if player_ids:
        through = {n for n in legs if n not in player_ids}
    else:
        through = {"SC%d" % n for n in (deriv.get("through_nodes") or [])}

    nodes = []
    for node in sorted(legs):
        grid = [[k, str(l.get("node", ""))] for k, l in legs[node].items()
                if str(l.get("type", "")) == "grid"]
        bnd = [k for k, l in legs[node].items() if str(l.get("type", "")) == "boundary"]
        owned = sorted((r["no"] for r in links if r["owner"] and "SC%s" % r["owner"] == node),
                       key=lambda s: (len(s), s))
        nodes.append({
            "node": node, "x": xy.get(node, (None, None))[0], "y": xy.get(node, (None, None))[1],
            "name": name.get(node, ""), "follower": follower.get(node),
            "controlled": node in controlled, "has_gate": node in gate_nodes,
            "through": node in through,
            "grid_legs": grid, "boundary_legs": bnd, "owned_links": owned,
            "owned_len": round(sum(r["len"] for r in links
                                   if r["owner"] and "SC%s" % r["owner"] == node), 1),
        })

    payload = {
        "nodes": nodes, "links": links, "gates": gates,
        "adj_a": adjA, "adj_b": adjB,
        "removed": sorted(setA - setB), "added": sorted(setB - setA),
        "seg_a": rawA.get("internal_link_members", {}),
        "seg_b": rawB.get("internal_link_members", {}),
        "deriv_b": rawB.get("derivation", {}),
        "sources": {
            "config": os.path.basename(args.config), "network": os.path.basename(args.network),
            "roles": os.path.basename(args.roles), "assignment": os.path.basename(args.assignment),
            "adj_a": os.path.basename(args.adjacency_a), "adj_b": os.path.basename(args.adjacency_b),
        },
    }

    tpl_name = ("topology_inspector_template.html" if args.view == "inspect"
                else "topology_clean_template.html")
    tpl = os.path.join(os.path.dirname(os.path.abspath(__file__)), tpl_name)
    with open(tpl, encoding="utf-8") as fh:
        html = fh.read()
    html = html.replace("__DATA__", json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(html)

    print(f"노드 {len(nodes)}  링크 {len(links)}  게이트 {len(gates)}")
    print(f"인접  A(구) {len(adjA)}  B(새) {len(adjB)}  제거 {len(payload['removed'])}  추가 {len(payload['added'])}")
    print(f"소유 링크 합계 {sum(len(n['owned_links']) for n in nodes)}개 "
          f"/ 도면 링크 {len(links)}개")
    print(f"wrote {args.out} ({os.path.getsize(args.out)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
