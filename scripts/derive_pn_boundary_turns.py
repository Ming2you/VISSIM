# -*- coding: utf-8 -*-
"""보호망(protected network) 경계 회전을 망에서 유도한다 — core17legs4b 정본.

무엇을 푸는가
-------------
리더가 유입·유출을 조이려면 **VISSIM 에서 실제로 셀 수 있는 주소**가 있어야 한다.
config 의 `urban_movements` 는 leg 교차곱으로 선언돼 있어 물리 회전보다 많다
(SC1 은 4갈래 교차로인데 56개가 선언돼 있다. 통제 17 SC 합계 선언 364 대 실제 201).
그래서 선언을 망에 맞추는 대신 **망에서 회전을 유도**한다.

절차
----
1. leg 마다 구역을 매긴다
     내부    반대편이 통제 SC (또는 내부 leg 와 축을 공유하는 게이트)
     경계면  반대편이 비통제 player · 게이트 · 램프
     외부    비통제 player 의 leg
2. 전이표로 판정한다. 진출 leg 는 "그 leg 로 나가면 어디로 가느냐" 로 읽는다.
     내부->내부 internal · 내부->외부 outflow · 경계면->내부 inflow
     경계면->외부 external · 외부->내부 inflow · 외부->외부 outside_pn
3. leg 의 **정지선 링크**(그 SC 의 signal head 가 걸린 최하류 링크)에서 나가는
   커넥터 하나 = 회전 하나. (from_link, connector, to_link) 가 런타임 주소가 된다.
4. 통제 가능 여부를 가른다. 정지선에 그 SC 의 신호두가 없으면 경계를 넘어도 못 조인다.
5. 조일 수 없는 유입과 보호망 안쪽 vehicleInput 을 **상수 부하**로 따로 센다.

규칙이 이렇게 된 이유 (되돌리지 마라)
------------------------------------
* **경계면 우선.** 한 링크를 경계면 leg 와 내부 leg 가 같이 물면 경계면이 이긴다.
  경계면은 보호망을 자르는 면이라 내부로 흡수되면 그 자리의 유입·유출이 사라진다.
  (SC107·S 의 링크 378·379 를 SC108·W_SC107 이 같이 물어 내부로 먹히고 있었다.)
* **도착 구역은 하류로 걸어서 본다.** 교차로 직후 진출 카리지웨이는 어느 leg 권역에도
  안 잡혀 있는 곳이 25군데다. 그대로 두면 통제 SC 사이 구간인데도 유출로 찍힌다.
  무소유면 하류로 걸어 처음 만나는 소유자를 쓴다 (mid-block 귀속 규칙과 같다).
* **양끝이 버퍼면 횡단이 아니다.** 정지선 앞 회랑 안의 이동이라 보호망을 넘지 않는다.
  (379 구룡터널 진입 -> 378 은 SC107 정지선 382 앞이고 실제 횡단은 10618 이다.
   이걸 세면 같은 차량을 두 번 센다.)
* **relFlow 는 비어 있으면 1 이다.** 0 으로 읽으면 지하차도 같은 경로가 통째로 사라진다.
  130개 결정부 중 68개가 빈 relFlow 를 갖는다.
* **FORCE_PERI.** 자동 규칙으로는 내부로 접히지만 거기서 차량이 보호망 안으로 들어오는
  자리. 사용자가 전수 검토해 확정했다 (2026-08-19).
* **정지선 바깥에서 들어오는 횡단도 줍는다.** 유도기는 정지선에서 바깥으로만 보므로,
  진입 줄기가 무소유면 그 줄기에서 권역으로 들어오는 횡단이 통째로 안 보인다.
  다만 상류가 있는 mid-block 링크(하류 귀속 규칙이 이미 적용되는 자리)와 freeway 는
  제외한다 — 안 그러면 259·336 같은 내부 이동이 가짜 유입으로 잡힌다.

기대 산출 (2026-08-19 기준)
---------------------------
  leg 구역        내부 67 · 경계면 18 · 외부 36
  회전            306 (통제 17 SC 안 204)
  판정            internal 123 · inflow 35 · outflow 34 · external 10 · outside_pn 104
  통제 가능 경계   74 (유입 32 · 유출 34 · 외부통과 8)
  상수 부하        3,920 veh/h (통제 불가 유입 1,529 + 내부 주입 2,391)
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DEF_INPX = ROOT / "network/real_world_gaepo_modi/modi_eval_userfix_20260814d.inpx"
DEF_CFG = ROOT / "evaluation/configs/real_world_modi_pstack_distributed_core17legs4b_20260819.json"
DEF_TERR = ROOT / "outputs/urban_player_territory_v1_20260819.json"
DEF_OUT = ROOT / "outputs/pn_boundary_turns_v1_20260819.json"

# 자동 규칙으로는 내부로 접히지만 실제로는 망 진입점이라 경계면인 leg.
# 사용자 전수 검토 확정 2026-08-19. 근거는 module docstring 참조.
FORCE_PERI = {
    ("SC1", "S"): "망 진입점 — 1220042300 구룡터널_NB 1336 veh/h 주입",
}

TABLE = {
    ("내부", "내부"): "internal",
    ("내부", "외부"): "outflow",
    ("경계면", "내부"): "inflow",
    ("경계면", "외부"): "external",
    ("외부", "내부"): "inflow",
    ("외부", "외부"): "outside_pn",
}
DIRV = {"N": (0, 1), "S": (0, -1), "E": (1, 0), "W": (-1, 0)}


def base(k: str) -> str:
    return str(k).split("_")[0]


def relval(v) -> float:
    """relFlow 문자열 -> 상대유량. 비어 있으면 1 (VISSIM 기본값)."""
    if v is None or not str(v).strip():
        return 1.0
    m = re.findall(r":\s*([0-9.]+)", str(v))
    return float(m[0]) if m else 1.0


class Net:
    """inpx 에서 필요한 것만 뽑아 든다."""

    def __init__(self, inpx: Path):
        self.cfrom, self.cto, self.pts = {}, {}, {}
        self.real = set()
        self.head = collections.defaultdict(set)      # 링크 -> {(SC, sg)}
        self.vin = collections.defaultdict(list)      # 링크 -> [{no,name,vol}]
        self.route = collections.defaultdict(list)    # 링크 -> [{first,rel}]
        for _, el in ET.iterparse(str(inpx), events=("end",)):
            if el.tag == "link":
                no = el.get("no")
                pts = [(float(p.get("x")), float(p.get("y"))) for p in el.iter("linkPolyPoint")]
                if pts:
                    self.pts[no] = pts
                f, t = el.find("fromLinkEndPt"), el.find("toLinkEndPt")
                if f is not None and t is not None:
                    a, b = (f.get("lane") or "").split(), (t.get("lane") or "").split()
                    if a and b:
                        self.cfrom[no], self.cto[no] = a[0], b[0]
                elif pts:
                    self.real.add(no)
                el.clear()
            elif el.tag == "signalHead":
                sg, lk = (el.get("sg") or "").split(), (el.get("lane") or "").split()
                if len(sg) > 1 and lk:
                    self.head[lk[0]].add((f"SC{int(sg[0])}", int(sg[1])))
                el.clear()
            elif el.tag == "vehicleInput":
                lk = el.get("link")
                if lk:
                    v = [float(x.get("volume")) for x in el.iter() if x.get("volume") is not None]
                    self.vin[lk].append({"no": el.get("no"), "name": el.get("name") or "",
                                         "vol": max(v) if v else 0.0})
                el.clear()
            elif el.tag == "vehicleRoutingDecisionStatic":
                for r in el.iter("vehicleRouteStatic"):
                    seq = [x.get("key") for x in r.iter("intObjectRef")]
                    self.route[el.get("link")].append(
                        {"first": seq[0] if seq else r.get("destLink"),
                         "rel": relval(r.get("relFlow"))})
                el.clear()

        self.down = collections.defaultdict(list)     # 링크 -> [(커넥터, 하류링크)]
        for c, s in self.cfrom.items():
            if self.cto.get(c):
                self.down[s].append((c, self.cto[c]))
        self.ups = {self.cto[c] for c in self.cfrom if self.cto.get(c)}

    def heading(self, conn: str):
        """커넥터를 빠져나간 뒤의 진행 방위.

        커넥터 자체의 현으로 재면 좌회전이 진입·진출의 평균이라 45도로 뭉개진다.
        하류 링크의 첫 구간 방향이 곧 진출 방위다.
        """
        q = self.pts.get(self.cto.get(conn)) or []
        if len(q) >= 2:
            for j in range(1, len(q)):
                dx, dy = q[j][0] - q[0][0], q[j][1] - q[0][1]
                if math.hypot(dx, dy) > 8.0:
                    return dx, dy
            return q[-1][0] - q[0][0], q[-1][1] - q[0][1]
        p = self.pts.get(conn) or []
        if len(p) >= 2:
            return p[-1][0] - p[-2][0], p[-1][1] - p[-2][1]
        return 0.0, 0.0

    def compass(self, conn: str):
        dx, dy = self.heading(conn)
        n = math.hypot(dx, dy) or 1.0
        best, bs = None, 0.0
        for d, (ux, uy) in DIRV.items():
            v = (dx * ux + dy * uy) / n
            if v > bs:
                bs, best = v, d
        return best if bs > 0.45 else None

    def conn_flow(self, link: str, conn: str):
        """진입 링크의 수요 중 이 커넥터가 나르는 몫 (veh/h). 모르면 None."""
        vol = sum(x["vol"] for x in self.vin.get(link, []))
        if not vol or link in self.ups:
            return None
        rs = self.route.get(link)
        if not rs:
            outs = [c for c, _d in self.down.get(link, [])]
            return round(vol, 0) if len(outs) == 1 else None
        tot = sum(r["rel"] for r in rs)
        mine = sum(r["rel"] for r in rs if r["first"] == conn)
        return round(vol * mine / tot, 0) if tot else None


def derive(net: Net, cfg: dict, terr: dict):
    netcfg = cfg["config_overrides"]["network"]
    legs_cfg, ctl = netcfg["grid_node_legs"], set(netcfg["signals"])
    urb, fw = terr["territory"]["urban"], terr["territory"]["freeway"]
    fwset = {x for v in fw.values() for x in v}

    # --- 1. leg 구역 ---------------------------------------------------------
    zone, why = {}, {}
    for sc, legs in legs_cfg.items():
        inner_dirs = {base(k) for k in legs if "_" in k and str(k).split("_", 1)[1] in ctl}
        for k, spec in legs.items():
            nb = str(k).split("_", 1)[1] if "_" in k else None
            if sc not in ctl:
                z, w = "외부", "비통제 player"
            elif nb in ctl:
                z, w = "내부", f"반대편 {nb} 통제"
            elif nb is None and base(k) in inner_dirs:
                z, w = "내부", f"{base(k)}축 내부 leg 와 합쳐진 게이트"
            elif nb == "RAMP" or (spec or {}).get("type") == "ramp":
                z, w = "경계면", "램프"
            elif nb:
                z, w = "경계면", f"반대편 {nb} 비통제"
            else:
                z, w = "경계면", "게이트 (망 진입)"
            zone[(sc, k)], why[(sc, k)] = z, w
    for t, reason in FORCE_PERI.items():
        if t in zone:
            zone[t], why[t] = "경계면", reason + " (사용자 확정)"

    # --- 2. 링크 소유와 구역 --------------------------------------------------
    own = collections.defaultdict(set)
    for sc, legs in urb.items():
        for k, lks in legs.items():
            for lk in lks:
                own[lk].add((sc, k))
    peri_link = {lk for lk, v in own.items() if any(zone.get(t) == "경계면" for t in v)}
    inner_link = {lk for lk, v in own.items()
                  if any(zone.get(t) == "내부" for t in v) and lk not in peri_link}

    def dest_zone(lk, hops=6):
        seen, fr = {lk}, [lk]
        for _ in range(hops):
            nxt = []
            for l in fr:
                if l in inner_link:
                    return "내부"
                if l in own or l in fwset:
                    return "외부"
                for _c, d in net.down.get(l, []):
                    if d not in seen:
                        seen.add(d)
                        nxt.append(d)
            if not nxt:
                break
            fr = nxt
        return "외부"

    # --- 3. 정지선에서 회전 유도 ------------------------------------------------
    turns, skipped, legstat = [], [], {}
    for (sc, k), z in zone.items():
        L = set((urb.get(sc) or {}).get(k, []))
        if not L:
            legstat[f"{sc}|{k}"] = {"z": z, "stops": [], "turns": 0, "why": why[(sc, k)]}
            continue
        term = [l for l in L if any(d not in L for _c, d in net.down.get(l, []))]
        sig = [l for l in term if any(s == sc for s, _ in net.head.get(l, ()))]
        stops = sorted(sig or term, key=int)
        n = 0
        for l in stops:
            for c, d in net.down.get(l, []):
                if d in L:
                    continue
                if l in peri_link and d in peri_link:      # 버퍼 안 이동은 횡단이 아니다
                    skipped.append({"sc": sc, "leg": k, "conn": c, "from": l, "to": d})
                    continue
                dz = dest_zone(d)
                turns.append({
                    "sc": sc, "leg": k, "z": z, "stop": l, "conn": c, "to": d, "dz": dz,
                    "k": TABLE[(z, dz)], "dir": net.compass(c),
                    "sg": sorted({g for s, g in net.head.get(l, ()) if s == sc}),
                    "ctrl": bool([g for s, g in net.head.get(l, ()) if s == sc]),
                    "in_vol": round(sum(x["vol"] for x in net.vin.get(l, [])), 0),
                    "flow": net.conn_flow(l, c),
                    "to_own": sorted(f"{a}·{b}" for a, b in own.get(d, ())),
                })
                n += 1
        legstat[f"{sc}|{k}"] = {"z": z, "stops": stops, "turns": n,
                                "why": why[(sc, k)], "sig": bool(sig)}

    # 정지선 바깥에서 들어오는 횡단도 본다.
    #
    # 유도기는 leg 의 정지선에서 **바깥으로** 나가는 커넥터만 회전으로 잡는다. 그래서
    # 진입 줄기가 어느 leg 권역에도 없으면 그 줄기에서 권역으로 들어오는 횡단이 통째로
    # 안 보인다. link 69(서측 진입, 1400 veh/h)를 어느 player 에도 주지 않기로 하면
    # 10636(69->75, SC1005 지하차도)과 10644(69->26)가 사라지는 식이다.
    # 횡단은 구역이 바뀌는 커넥터지 정지선의 소유물이 아니다. 무소유 상류에서
    # 권역 안으로 들어오는 커넥터를 여기서 줍는다.
    # 다만 아무 무소유 링크나 주우면 안 된다. 상류가 있는 mid-block 링크는 이미
    # '하류에서 처음 만나는 player 에 귀속' 규칙이 적용되는 자리라 그 커넥터는 내부다
    # (259 -> 1220011003, 336 -> 1210014303 이 그렇게 가짜 유입으로 잡혔다).
    # freeway 링크도 아니다. **진짜 발원지** — 망 진입점이거나 vehicleInput 이 붙은
    # 비-freeway 무소유 링크 — 에서 들어오는 것만 줍는다.
    have = {t["conn"] for t in turns}
    for c, up in net.cfrom.items():
        d = net.cto.get(c)
        if c in have or not d or up in own or up in fwset:
            continue
        if up in net.ups and up not in net.vin:
            continue
        holders = [(sc, k) for sc, k in own.get(d, ()) if zone.get((sc, k))]
        if not holders:
            continue
        holders.sort(key=lambda t: (0 if zone[t] == "경계면" else (1 if zone[t] == "내부" else 2), t))
        sc, k = holders[0]
        dz = dest_zone(d)
        turns.append({
            "sc": sc, "leg": k, "z": "외부", "stop": up, "conn": c, "to": d, "dz": dz,
            "k": TABLE[("외부", dz)], "dir": net.compass(c),
            "sg": sorted({g for s, g in net.head.get(up, ()) if s == sc}),
            "ctrl": bool([g for s, g in net.head.get(up, ()) if s == sc]),
            "in_vol": round(sum(x["vol"] for x in net.vin.get(up, [])), 0),
            "flow": net.conn_flow(up, c),
            "to_own": sorted(f"{a}·{b}" for a, b in own.get(d, ())),
            "from_unowned": True,
        })

    # 정지선을 공유하는 leg 가 있다 (SC1001 의 W 와 W_RAMP 는 같은 link 32).
    # 커넥터 하나 = 회전 하나이므로 커넥터를 유일 키로 접고 leg 는 목록으로 붙인다.
    uniq = {}
    for t in turns:
        u = uniq.get(t["conn"])
        if u is None:
            u = dict(t)
            u["legs"] = [f"{t['sc']}·{t['leg']}"]
            u.pop("leg")
            uniq[t["conn"]] = u
        else:
            u["legs"].append(f"{t['sc']}·{t['leg']}")
    turns = list(uniq.values())

    # --- 4. 통제 불가 내부 유입 ------------------------------------------------
    src, seen_vi = [], set()
    for lk, vis in net.vin.items():
        if lk in net.ups:
            continue
        holders = sorted((a, b) for a, b in own.get(lk, ()) if a in ctl)
        if not holders:
            continue
        zs = {zone.get(t) for t in holders}
        if "내부" not in zs or "경계면" in zs:
            continue
        for vi in vis:
            if vi["no"] in seen_vi:
                continue
            seen_vi.add(vi["no"])
            src.append({"link": lk, "input": vi["no"], "name": vi["name"], "vol": vi["vol"],
                        "legs": [f"{a}·{b}" for a, b in holders],
                        "dummy": "dummy" in vi["name"].lower()})
    src.sort(key=lambda r: -r["vol"])

    cross = [t for t in turns if t["k"] in ("inflow", "outflow", "external")]
    load_x = [t for t in cross if not t["ctrl"] and t["k"] == "inflow"]
    return {
        "zone": zone, "why": why, "turns": turns, "legstat": legstat, "skipped": skipped,
        "src": src, "src_total": sum(r["vol"] for r in src),
        "load_cross": load_x, "load_cross_v": sum(t["flow"] or 0 for t in load_x),
        "ctl": ctl, "own": own, "peri_link": peri_link, "inner_link": inner_link,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--inpx", type=Path, default=DEF_INPX)
    ap.add_argument("--config", type=Path, default=DEF_CFG)
    ap.add_argument("--territory", type=Path, default=DEF_TERR)
    ap.add_argument("--out", type=Path, default=DEF_OUT)
    ap.add_argument("--dry-run", action="store_true", help="요약만 찍고 파일은 안 쓴다")
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    net = Net(a.inpx)
    cfg = json.loads(a.config.read_text(encoding="utf-8"))
    terr = json.loads(a.territory.read_text(encoding="utf-8"))
    R = derive(net, cfg, terr)

    T, ctl = R["turns"], R["ctl"]
    cnt = collections.Counter(t["k"] for t in T)
    cross = [t for t in T if t["k"] in ("inflow", "outflow", "external")]
    surf = collections.Counter(t["k"] for t in cross if t["ctrl"])
    unctrl = [t for t in cross if not t["ctrl"]]
    load = R["load_cross_v"] + R["src_total"]

    print(f"leg 구역     {dict(collections.Counter(R['zone'].values()))}")
    print(f"회전         {len(T)}  (통제 17 SC 안 {sum(1 for t in T if t['sc'] in ctl)})")
    print(f"판정         {dict(cnt.most_common())}")
    print(f"통제 가능 경계 {sum(surf.values())}  {dict(surf.most_common())}")
    print(f"통제 불가 횡단 {len(unctrl)}  " +
          ", ".join(f"{t['conn']}({t['k']}"
                    + (f", {int(t['flow'])} veh/h" if t.get("flow") else "") + ")"
                    for t in sorted(unctrl, key=lambda z: int(z["conn"]))))
    print(f"버퍼 안 제외   {len({x['conn'] for x in R['skipped']})}")
    print(f"상수 부하     {load:.0f} veh/h "
          f"(통제 불가 유입 {R['load_cross_v']:.0f} + 내부 주입 {R['src_total']:.0f}, "
          f"주입점 {len(R['src'])}곳)")

    if a.dry_run:
        return 0

    payload = {
        "schema": "pn_boundary_turns/v1",
        "generated": "2026-08-19",
        "generator": "scripts/derive_pn_boundary_turns.py",
        "regeneration_policy": (
            "이 파일은 위 생성기로만 다시 만든다. 규칙(경계면 우선 · 하류 걷기 · 버퍼 제외 · "
            "relFlow 기본 1 · FORCE_PERI)은 사용자가 전수 검토해 확정했다. 되돌리지 마라."),
        "definition": {
            "leg_zone": "내부 = 반대편이 통제 SC(또는 내부 leg 와 축을 공유하는 게이트) · "
                        "경계면 = 반대편이 비통제/게이트/램프 · 외부 = 비통제 player",
            "table": {"내부->내부": "internal", "내부->외부": "outflow",
                      "경계면->내부": "inflow", "경계면->외부": "external",
                      "외부->내부": "inflow", "외부->외부": "outside_pn"},
            "exit_leg": "진출 leg 는 '그 leg 로 나가면 어디로 가느냐' 로 읽는다. "
                        "경계면 leg 로 나가면 곧 외부다.",
            "destination": "도착 링크가 내부 leg 소유면 내부. 무소유면 하류로 걸어 "
                           "처음 만나는 소유자를 쓴다.",
            "controllable": "출발 정지선에 그 SC 의 signal head 가 있어야 조일 수 있다.",
        },
        "sources": {"inpx": a.inpx.name, "config": a.config.name, "territory": a.territory.name},
        "counts": dict(cnt),
        "control_surface": {
            "note": "리더가 실제로 조일 수 있는 경계 횡단.",
            "counts": dict(surf),
            "connectors": [t["conn"] for t in cross if t["ctrl"]],
        },
        "constant_load": {
            "note": "게이트로 못 막고 N_P 에 그냥 쌓이는 몫. N_P* 여유에 상수로 반영한다.",
            "uncontrollable_inflow_veh_h": R["load_cross_v"],
            "interior_injection_veh_h": R["src_total"],
            "total_veh_h": load,
            "uncontrollable_inflow": [
                {"connector": t["conn"], "from_link": t["stop"], "to_link": t["to"],
                 "legs": t["legs"], "flow_veh_h": t.get("flow")} for t in R["load_cross"]],
            "interior_injection": R["src"],
        },
        "uncontrollable_crossings": {
            "note": "경계는 넘지만 출발 정지선에 신호두가 없어 조일 수 없는 횡단. "
                    "external 은 보호망 밖으로만 지나가 N_P 에 쌓이지 않으므로 상수 부하에서 뺐다.",
            "connectors": [{"class": t["k"], "connector": t["conn"], "from_link": t["stop"],
                            "to_link": t["to"], "legs": t["legs"],
                            "flow_veh_h": t.get("flow")} for t in unctrl],
        },
        "buffer_internal_excluded": {
            "note": "양끝이 모두 경계 버퍼인 커넥터. 정지선 앞 회랑 안의 이동이라 "
                    "보호망을 넘지 않는다. 세면 같은 차량을 두 번 센다.",
            "connectors": R["skipped"],
        },
        "leg_zone": {f"{a_}|{b_}": {"zone": v, "why": R["why"][(a_, b_)]}
                     for (a_, b_), v in sorted(R["zone"].items())},
        "turns": [{"class": t["k"], "sc": t["sc"], "legs": t["legs"], "leg_zone": t["z"],
                   "dest_zone": t["dz"], "from_link": t["stop"], "connector": t["conn"],
                   "to_link": t["to"], "heading": t["dir"], "signal_groups": t["sg"],
                   "controllable": t["ctrl"], "entry_volume_veh_h": t["in_vol"],
                   "flow_veh_h": t.get("flow")}
                  for t in sorted(T, key=lambda z: (z["k"], int(z["conn"])))],
    }
    a.out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n-> {a.out}  ({a.out.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
