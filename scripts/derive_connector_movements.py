"""movement 를 **정지선 커넥터**로 다시 유도한다.

문제
----
`config_overrides.network.urban_movements` 474개는 물리 회전이 아니라 **leg 교차곱**이다.
26개 신호 전부에서 `movement 수 == L x (L-1)` 이 정확히 성립한다(L = 권역 leg 수).
합계 121 leg -> 474.

그런데 권역 leg 는 물리 접근로보다 많다. 같은 방위가 두 번 세어진다:

    SC1 leg 8개 = E, E_SC11, N, N_SC101, S, S_SC107, W, W_SC105
      E vs E_SC11    링크 27 / 27·27  -> **완전히 같은 집합**
      N vs N_SC101   링크  1 / 1·25   -> 경계판이 내부판의 부분집합
      S vs S_SC107   링크  1 / 1·17
      W vs W_SC105   링크  1 / 1·19

경계판의 그 1개 링크는 `boundary_extra_legs` 가 "상류 종단에 vehicleInput 있음"으로
적어 둔 **수요 주입점**이지 새 접근로가 아니다. 교차곱이 그걸 독립 leg 로 세면서
SC1 이 8x7 = 56 movement 가 됐다. 실제 물리 회전은 4x3 = 12 다.

부산물:
  - u_turn 44개 중 **40개가 같은 방위 쌍둥이 사이**다(`SC1_E_to_E_SC11` — 자기 자신).
  - 같은 물리 회전이 둘로 쪼개진 쌍이 **70쌍**이고, 70쌍 전부 현시가 같다.
  - 같은 정지선을 공유하는 movement 들이 **각자 용량을 갖는다.** SC1 동쪽 14개의
    모델 용량 합이 16,226 veh/h 인데 그 접근로는 3차로 하나다.

유도
----
movement 는 "정지선에서 **어느 커넥터를 타는가**" 여야 한다. 그게 신호가 실제로
통제하는 단위다. 그 뒤 어디로 가느냐는 하류 배분이라 `beta` 가 맡는다.

    1. `.inpx` signalHead 로 정지선을 정한다. SG 1-8 만 본다(9 이상은 미드블록).
    2. 정지선 링크에서 나가는 커넥터 = 그 접근로의 물리 회전.
    3. 커넥터의 to_link 를 권역으로 접어 목적 (신호, leg) 를 얻는다.
    4. 목적이 하나뿐이면 movement 하나로 통일하고, 여러 갈래면 갈래마다 하나 둔다.
       (갈래가 커넥터보다 잘게 쪼개지는 경우는 beta 가 다룰 몫이지 movement 가 아니다.)

leg 병합 규칙: 링크 집합이 같거나 부분집합이면 하나다. 이름은 하류가 드러나는 쪽
(`_SC` 가 붙은 쪽)을 쓴다 — `SC1_E_to_S` 보다 `SC1_E_to_S_SC107` 이 목적을 말해 준다.
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MAINLINE_SG_MAX = 8  # SG 9 이상은 미드블록이라 본선 정지선으로 세지 않는다.


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--network", default="network/real_world_gaepo_modi/modi_eval_userfix_20260814e.inpx")
    ap.add_argument("--territory", default="outputs/urban_player_territory_v1_20260819.json")
    ap.add_argument("--movements-config",
                    default="evaluation/configs/real_world_modi_pstack_distributed_core17legs4b_20260819.json")
    ap.add_argument("--out", default="outputs/movement_connector_map_20260824.json")
    args = ap.parse_args()

    root = ET.parse(ROOT / args.network).getroot()

    lanes_of: dict[str, int] = {}
    conn: dict[str, tuple[str, str]] = {}
    center: dict[str, tuple[float, float]] = {}
    for link in root.iter("link"):
        no = str(link.get("no"))
        node = link.find("lanes")
        lanes_of[no] = len(list(node)) if node is not None else 0
        px, py = [], []
        for pt in link.iter("linkPolyPoint"):
            try:
                px.append(float(pt.get("x")))
                py.append(float(pt.get("y")))
            except (TypeError, ValueError):
                continue
        if px:
            center[no] = (sum(px) / len(px), sum(py) / len(py))
        f, t = link.find("fromLinkEndPt"), link.find("toLinkEndPt")
        if f is None or t is None:
            continue
        fl = (f.get("lane") or "").split()
        tl = (t.get("lane") or "").split()
        if fl and tl:
            conn[no] = (fl[0], tl[0])

    # 정지선: SG 1-8 신호두가 달린 링크. sg="<controller> <group>".
    stopline: dict[str, set[tuple[str, int]]] = collections.defaultdict(set)
    for head in root.iter("signalHead"):
        lane = (head.get("lane") or "").split()
        sg = (head.get("sg") or "").split()
        if len(lane) < 1 or len(sg) < 2:
            continue
        try:
            sc, grp = "SC" + str(int(sg[0])), int(sg[1])
        except ValueError:
            continue
        if grp > MAINLINE_SG_MAX:
            continue
        stopline[lane[0]].add((sc, grp))

    def bearing(from_link: str, to_link: str) -> str:
        """망 밖으로 나가는 커넥터의 **자기 기준 출구 방위**.

        목적지가 권역 밖이면 하류 신호로 이름을 지을 수 없다. 기존 모델은 그럴 때
        방위(`to_W` / `to_S`)로 부르므로, 좌표로 방위를 내야 이름이 맞는다.
        한 접근로에서 망 밖으로 나가는 커넥터가 둘인 경우가 13곳 있는데, 방위가
        없으면 그 둘이 한 이름으로 뭉쳐 기존 movement 와 대응이 모호해진다.
        """
        a, b = center.get(from_link), center.get(to_link)
        if not a or not b:
            return "OUT"
        dx, dy = b[0] - a[0], b[1] - a[1]
        return ("E" if dx > 0 else "W") if abs(dx) >= abs(dy) else ("N" if dy > 0 else "S")

    terr = json.loads((ROOT / args.territory).read_text(encoding="utf-8"))["territory"]["urban"]
    owner: dict[str, tuple[str, str]] = {}
    for sig, legs in terr.items():
        for leg, ids in legs.items():
            for i in ids:
                owner.setdefault(str(i), (sig, leg))

    # --- leg 병합 ---
    merged: dict[tuple[str, str], tuple[str, str]] = {}
    for sig, legs in terr.items():
        items = [(leg, set(str(x) for x in ids)) for leg, ids in legs.items()]
        for a, sa in items:
            rep = (sig, a)
            for b, sb in items:
                if a == b:
                    continue
                if sa < sb or (sa == sb and "_SC" in b and "_SC" not in a):
                    rep = (sig, b)
                    break
            merged[(sig, a)] = rep

    def rep_of(key):
        seen = set()
        while merged.get(key, key) != key and key not in seen:
            seen.add(key)
            key = merged[key]
        return key

    rep_links: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    for (sig, leg) in merged:
        rep_links[rep_of((sig, leg))] |= set(str(x) for x in terr[sig][leg])

    # --- 대표 접근로별 정지선 커넥터 ---
    result: dict[str, dict] = {}
    for rep, links in sorted(rep_links.items()):
        sig, leg = rep
        # 이 접근로의 정지선 링크 = 이 신호의 SG 1-8 신호두가 달린, 이 leg 소속 링크
        stops = sorted(l for l in links if any(s == sig for s, _ in stopline.get(l, ())))
        turns = []
        for c, (fl, tl) in sorted(conn.items(), key=lambda kv: int(kv[0])):
            if fl not in stops:
                continue
            o = owner.get(tl)
            dest = rep_of(o) if o else None
            turns.append({
                "connector": c, "from_link": fl, "to_link": tl,
                "lanes": lanes_of.get(c, 0),
                "dest_signal": dest[0] if dest else None,
                "dest_leg": dest[1] if dest else None,
                "dest": ("%s_%s" % dest) if dest else ("OUT_" + bearing(fl, tl)),
                "bearing": bearing(fl, tl),
                "sg": sorted(g for s, g in stopline.get(fl, ()) if s == sig),
            })
        result["%s|%s" % rep] = {
            "signal": sig, "approach": leg,
            "stoplines": stops, "n_links": len(links),
            "turns": turns,
        }

    # --- movement 제안: 목적별로 커넥터를 묶는다 ---
    proposal: dict[str, dict] = {}
    for key, r in result.items():
        by_dest: dict[str, list[dict]] = collections.defaultdict(list)
        for t in r["turns"]:
            by_dest[t["dest"]].append(t)
        for dest, ts in by_dest.items():
            name = "%s_%s_to_%s" % (r["signal"], r["approach"], dest.split("_", 1)[1])
            proposal[name] = {
                "signal": r["signal"], "approach": r["approach"],
                "dest": dest, "connectors": [t["connector"] for t in ts],
                "lanes": sum(t["lanes"] for t in ts),
                "sg": sorted({g for t in ts for g in t["sg"]}),
            }

    doc = {
        "schema": "movement_connector_map/v1",
        "generated": "2026-08-24",
        "note": ("movement 를 정지선 커넥터로 다시 유도한다. 정지선은 SG 1-8 신호두가 "
                 "달린 링크. leg 는 링크 집합이 같거나 부분집합이면 병합하고 이름은 "
                 "하류가 드러나는 쪽(_SC 붙은 쪽)을 쓴다."),
        "approaches": result,
        "proposal": proposal,
    }
    (ROOT / args.out).write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")

    # --- 보고 ---
    um = json.loads((ROOT / args.movements_config).read_text(encoding="utf-8")) \
        ["config_overrides"]["network"]["urban_movements"]
    absorbed = sum(1 for k, v in merged.items() if k != v)
    nturn = sum(len(r["turns"]) for r in result.values())
    nostop = [k for k, r in result.items() if not r["stoplines"]]
    print("leg %d -> 병합 후 %d (흡수 %d)" % (len(merged), len(rep_links), absorbed))
    print("정지선 커넥터 %d개 · movement 제안 %d개 (현재 선언 %d개)"
          % (nturn, len(proposal), len(um)))
    print("정지선을 못 찾은 접근로 %d개" % len(nostop))
    dist = collections.Counter(len(r["turns"]) for r in result.values())
    print("접근로당 회전 수 분포:", dict(sorted(dist.items())))

    ctrl = {"SC1", "SC5", "SC6", "SC7", "SC11", "SC12", "SC16", "SC101", "SC105",
            "SC107", "SC108", "SC109", "SC1001", "SC1002", "SC1003", "SC1004", "SC1005"}
    print("\n%-9s %6s %6s %6s   현재 대비" % ("신호", "접근로", "회전", "제안"))
    for sig in sorted(ctrl, key=lambda x: (len(x), x)):
        rs = [r for r in result.values() if r["signal"] == sig]
        pr = [p for p in proposal.values() if p["signal"] == sig]
        cur = sum(1 for s in um.values() if str(s.get("signal")) == sig)
        print("  %-9s %5d %6d %6d   %d -> %d" %
              (sig, len(rs), sum(len(r["turns"]) for r in rs), len(pr), cur, len(pr)))
    print("\n=== SC1 상세 ===")
    for k in sorted(result):
        if not k.startswith("SC1|"):
            continue
        r = result[k]
        print("  %s  정지선 %s" % (k, ",".join(r["stoplines"]) or "없음"))
        for t in r["turns"]:
            print("      conn %-7s %s -> %-11s %d차로 SG%s  ==> %s"
                  % (t["connector"], t["from_link"], t["to_link"], t["lanes"],
                     t["sg"], t["dest"]))
    print("\n저장: %s" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
