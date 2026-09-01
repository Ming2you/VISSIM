"""램프 급전 대장 — 어느 현시가 어느 on-ramp 를 먹이는가 (2026-09-01).

왜. on-ramp 는 권역 정본에서 **freeway 플레이어 소유**이고 도시 movement 로 배선하지
않는다(`grid_node_legs` 의 `W_RAMP.on = {}`, 사용자 결정 2026-09-01). 그래서 도시
컨트롤러는 램프를 직접 제어하지 않는다.

그런데 **신호는 램프 유입량에 실제로 영향을 준다.** 램프미터가 도시 정지선의 하류에 있는
경우가 있기 때문이다:

    링크 31 ← SC1001 서향 3개(정지선 통과)  →  10480 pos735(R_D_W) · 10484 pos412(R_D_E)
    링크 68 ← SC1004 서향 3개(정지선 통과)  →  10646 pos352(R_F_W) · 10681 pos117(R_F_E)

반대로 신호가 못 건드리는 경로도 있다:

    링크 32  10482 pos1028 · 10490 pos1330  <  SC1001 정지선 pos~1955   상류라 제어 불가
    링크 69  무소유 줄기 (CLAUDE.md 'SC1004 서측')
    링크 70  신호두 0개

이 대장은 그 구분을 기록만 한다 — 제어는 하지 않는다. 나중에 램프 spillback 이 생겼을 때
"그 램프를 먹이는 현시를 조인다" 를 하려면 이 매핑이 먼저 있어야 한다.

정본 입력: 커넥터 지도 · 권역 · 램프미터 VBS. 추론으로 채우지 않는다.
"""
from __future__ import annotations
import argparse, csv, json, sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]

# scripts/install_real_world_freeway_controls.vbs:440-447 (connector, from_link, ramp, pos_on_from_link)
RAMP_METERS = [
    ("10480", "31", "R_D_W", 734.931),
    ("10482", "32", "R_D_W", 1028.621),
    ("10646", "68", "R_F_W", 352.004),
    ("10644", "69", "R_F_W", 1740.482),
    ("10639", "70", "R_F_E", 180.143),
    ("10681", "68", "R_F_E", 76.589),
    ("10490", "32", "R_D_E", 1330.644),
    ("10484", "31", "R_D_E", 412.087),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="outputs/ramp_feed_map_20260901.json")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    conn_map = json.loads((R / "outputs/movement_connector_map_20260824.json").read_text(encoding="utf-8"))
    terr = json.loads((R / "outputs/urban_player_territory_v1_20260819.json").read_text(encoding="utf-8"))

    # 링크를 정지선으로 갖는 접근로에서, 그 링크로 **방류하는** 상류 접근로를 찾는다.
    # (커넥터 지도는 approach -> turns 이고 turn 마다 from_link/to_link 가 있다.)
    feeders: dict[str, list[dict[str, object]]] = {}
    for app_key, app in (conn_map.get("approaches") or {}).items():
        for t in app.get("turns", []):
            to_link = str(t.get("to_link"))
            feeders.setdefault(to_link, []).append({
                "signal": app.get("signal"),
                "approach": app.get("approach"),
                "connector": t.get("connector"),
                "from_link": t.get("from_link"),
                "signal_groups": t.get("sg"),
                "dest": t.get("dest"),
            })

    owned: dict[str, list[str]] = {}
    for player, legs in terr["territory"]["urban"].items():
        for leg, links in legs.items():
            for lk in links:
                owned.setdefault(str(lk), []).append("%s·%s" % (player, leg))
    for player, links in terr["territory"]["freeway"].items():
        for lk in links:
            owned.setdefault(str(lk), []).append("freeway·%s" % player)

    doc: dict[str, object] = {
        "schema_version": "ramp-feed-map/1",
        "generated": "2026-09-01",
        "what": "on-ramp 별 급전 경로와 그 경로가 신호 제어 가능한지",
        "policy": ("권역은 그대로 둔다 — on-ramp 는 freeway 플레이어 소유이고 도시 movement 로 "
                   "배선하지 않는다(grid_node_legs W_RAMP.on = {}). 이 대장은 관측·기록 전용이다."),
        "ramps": {},
    }
    for conn, from_link, ramp, pos in RAMP_METERS:
        entry = doc["ramps"].setdefault(ramp, {"meters": []})
        ups = feeders.get(from_link, [])
        controllable = bool(ups)
        entry["meters"].append({
            "connector": conn,
            "from_link": from_link,
            "meter_pos_m_on_from_link": pos,
            "from_link_owner": owned.get(from_link, ["무소유"]),
            "signal_controllable": controllable,
            "why": ("정지선 하류라 신호가 그 링크로의 방류를 조절한다"
                    if controllable else
                    "그 링크로 방류하는 신호 접근로가 없다 — 상류 이탈 또는 무소유/무신호"),
            "fed_by": ups,
        })

    out = R / a.out
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print("-> %s" % a.out)
    for ramp in ("R_D_W", "R_D_E", "R_F_W", "R_F_E"):
        ms = doc["ramps"][ramp]["meters"]
        c = [m for m in ms if m["signal_controllable"]]
        u = [m for m in ms if not m["signal_controllable"]]
        print("\n%s" % ramp)
        for m in c:
            sigs = sorted({str(f["signal"]) for f in m["fed_by"]})
            print("   제어가능  conn %-7s 링크 %-4s  급전 %s (접근로 %d)"
                  % (m["connector"], m["from_link"], ",".join(sigs), len(m["fed_by"])))
        for m in u:
            print("   제어불가  conn %-7s 링크 %-4s  소유 %s"
                  % (m["connector"], m["from_link"], ",".join(m["from_link_owner"])))


if __name__ == "__main__":
    main()
