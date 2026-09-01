# -*- coding: utf-8 -*-
"""보호망 경계 회전 지도를 만든다 (단일 HTML).

`derive_pn_boundary_turns.py` 의 판정을 실제 VISSIM 좌표 위에 얹어, leg 구역과
회전 등급을 겹으로 볼 수 있는 자립형 페이지를 낸다. 템플릿은 같은 폴더의
`pn_boundary_map.tpl.html` 이고 `__DATA__` 자리에 JSON 을 끼워 넣는다.

  python scripts/build_pn_boundary_map.py
  python scripts/build_pn_boundary_map.py --out reports/pn_map.html
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from derive_pn_boundary_turns import (  # noqa: E402
    DEF_CFG, DEF_INPX, DEF_TERR, Net, derive)

ROOT = Path(__file__).resolve().parents[1]
TPL = Path(__file__).resolve().parent / "pn_boundary_map.tpl.html"
DEF_OUT = ROOT / "outputs/pn_boundary_map_20260819.html"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--inpx", type=Path, default=DEF_INPX)
    ap.add_argument("--config", type=Path, default=DEF_CFG)
    ap.add_argument("--territory", type=Path, default=DEF_TERR)
    ap.add_argument("--out", type=Path, default=DEF_OUT)
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    net = Net(a.inpx)
    cfg = json.loads(a.config.read_text(encoding="utf-8"))
    terr = json.loads(a.territory.read_text(encoding="utf-8"))
    R = derive(net, cfg, terr)
    ZONE, own, TU = R["zone"], R["own"], R["turns"]
    netcfg = cfg["config_overrides"]["network"]
    LEGS, CTL = netcfg["grid_node_legs"], R["ctl"]
    URB = terr["territory"]["urban"]
    FWSET = {x for v in terr["territory"]["freeway"].values() for x in v}

    # --- 좌표 정규화 ----------------------------------------------------------
    xs = [p[0] for v in net.pts.values() for p in v]
    ys = [p[1] for v in net.pts.values() for p in v]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    W = 1900.0
    H = W * (y1 - y0) / (x1 - x0)

    def tf(p):
        return [round((p[0] - x0) / (x1 - x0) * W, 1),
                round(H - (p[1] - y0) / (y1 - y0) * H, 1)]

    def simp(pts):
        o = [tf(pts[0])]
        for p in pts[1:]:
            q = tf(p)
            if abs(q[0] - o[-1][0]) + abs(q[1] - o[-1][1]) > 1.2:
                o.append(q)
        if len(o) == 1:
            o.append(tf(pts[-1]))
        return o

    def link_zone(lk):
        zs = {ZONE.get(t) for t in own.get(lk, ())}
        for z in ("경계면", "내부", "외부"):     # 경계면 우선 — 판정 규칙과 같다
            if z in zs:
                return z
        return "freeway" if lk in FWSET else "무소유"

    TZ = {t["conn"]: t for t in TU}
    STOPSET = {t["stop"] for t in TU}
    SRCMAP = {r["link"]: r for r in R["src"]}
    links, conns = {}, {}
    for no, pts in net.pts.items():
        rec = {"p": simp(pts), "z": link_zone(no),
               "o": sorted(f"{a_}·{b_}" for a_, b_ in own.get(no, ()))}
        if no in net.cfrom:
            rec["f"], rec["t"] = net.cfrom[no], net.cto[no]
            t = TZ.get(no)
            if t:
                rec.update({"k": t["k"], "legs": t["legs"], "dir": t["dir"], "dz": t["dz"],
                            "sg": t["sg"], "ctrl": t["ctrl"], "vol": t["in_vol"],
                            "flow": t.get("flow")})
            conns[no] = rec
        else:
            if no in STOPSET:
                rec["stop"] = 1
            if no in SRCMAP:
                rec["src"] = SRCMAP[no]["vol"]
                rec["srcname"] = SRCMAP[no]["name"]
            links[no] = rec

    CEN = {}
    for sc in LEGS:
        sig = [net.pts[l][-1] for l, v in net.head.items()
               if any(s == sc for s, _ in v) and l in net.pts]
        ps = sig or [net.pts[l][-1] for k in (URB.get(sc) or {})
                     for l in URB[sc][k] if l in net.pts]
        if ps:
            CEN[sc] = tf((sum(p[0] for p in ps) / len(ps), sum(p[1] for p in ps) / len(ps)))

    byn = collections.defaultdict(collections.Counter)
    for t in TU:
        byn[t["sc"]][t["k"]] += 1
    decl = collections.Counter(str(s["intersection"]) for s in netcfg["urban_movements"].values())

    nodes = {}
    for sc in LEGS:
        legs = []
        for k in sorted(LEGS[sc]):
            st = R["legstat"].get(f"{sc}|{k}", {})
            legs.append({"k": k, "z": ZONE.get((sc, k), "?"), "why": R["why"].get((sc, k), ""),
                         "stops": st.get("stops", []), "sig": st.get("sig", False),
                         "n": len((URB.get(sc) or {}).get(k, []))})
        nodes[sc] = {"c": CEN.get(sc), "ctl": sc in CTL, "legs": legs,
                     "cnt": dict(byn[sc]), "decl": decl.get(sc, 0),
                     "turns": sum(byn[sc].values())}

    cross = [t for t in TU if t["k"] in ("inflow", "outflow", "external")]
    data = {
        "W": round(W), "H": round(H), "links": links, "conns": conns, "nodes": nodes,
        "turns": TU, "counts": dict(collections.Counter(t["k"] for t in TU)),
        "zone_counts": dict(collections.Counter(ZONE.values())),
        "ctrl_counts_surface": dict(collections.Counter(t["k"] for t in cross if t["ctrl"])),
        "unctrl": [t for t in cross if not t["ctrl"]],
        "skipped": R["skipped"], "src": R["src"], "src_total": R["src_total"],
        "load_cross": R["load_cross"], "load_cross_v": R["load_cross_v"],
        "load_total": R["load_cross_v"] + R["src_total"],
        "n_decl": sum(decl[s] for s in CTL),
        "n_turn_ctl": sum(1 for t in TU if t["sc"] in CTL),
    }
    html = TPL.read_text(encoding="utf-8")
    if "__DATA__" not in html:
        raise SystemExit(f"템플릿에 __DATA__ 자리가 없다: {TPL}")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(
        html.replace("__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":"))),
        encoding="utf-8")
    print(f"실링크 {len(links)}  커넥터 {len(conns)}  회전 {len(TU)}")
    print(f"-> {a.out}  ({a.out.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
