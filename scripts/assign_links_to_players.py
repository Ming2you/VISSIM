# 도시부 VISSIM 링크를 플레이어(교차로)에 **분할** 귀속시킨다.
#
# 규칙(2026-08-05 사용자 결정).
#   한 링크는 정확히 한 플레이어에만 속한다. 배정 기준은 **그 링크가 진입하는 교차로** —
#   링크에서 하류로 따라가 처음 만나는 정지선의 SC 가 소유자다. 즉 링크는 그 교차로의
#   approach queue 다. 빠지는 링크가 있어서는 안 된다.
#
# 왜 이 규칙인가.
#   이전 유도(derive_intersection_adjacency.py 의 internal_link_members)는 "A 의 정지선에서
#   B 까지 가는 **모든 경로**의 링크"를 구간 멤버로 삼았다. 그러면 A 의 정지선이 여럿이고
#   경로가 갈리므로 한 링크가 여러 구간에 동시에 들어간다 — 실측에서 160개 중 57개(36%)가
#   중복이었고 링크 31 은 21개 구간에 소속됐다. 차량이 중복 계상되어 저류 용량도, 포착률도
#   신뢰할 수 없게 된다. 하류 최초 SC 기준은 유일하게 정해지므로 정의상 분할이다.
#
# 산출: 링크 -> (소유 SC, 도착 leg 방위). 모델 저류·용량·길이 유도의 입력.
import argparse
import csv
import io
import json
import math
import os
import sys
from collections import defaultdict, deque

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_NET = os.path.join(REPO, "network", "real_world_gaepo_modi", "modi_eval_rw_control.inpx")
DEFAULT_ROLES = os.path.join(REPO, "evaluation", "real_world_modi_inventory", "signal_controller_roles.csv")
FREEWAY_LINKS = {"2", "24", "26", "74", "10699", "10702"}
# VBS 가 이미 ramp 로 따로 세는 커넥터(run_real_world_stackelberg_controller.vbs:103).
# urban_vehicles 분모에 안 들어가므로 여기서도 뺀다.
RAMP_METER_CONNECTORS = {"10480", "10482", "10646", "10644", "10639", "10681", "10490", "10484"}
LEG8 = ("E", "NE", "N", "NW", "W", "SW", "S", "SE")


def parse_int_csv(text):
    out = []
    for part in str(text or "").replace(";", ",").split(","):
        part = part.strip()
        if part:
            try:
                out.append(str(int(float(part))))
            except ValueError:
                pass
    return out


def bearing_leg(dx, dy):
    ang = math.degrees(math.atan2(dy, dx)) % 360.0
    return LEG8[int((ang + 22.5) // 45.0) % 8]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--network", default=DEFAULT_NET)
    ap.add_argument("--roles", default=DEFAULT_ROLES)
    ap.add_argument("--max-hops", type=int, default=60)
    ap.add_argument("--json-out", default="")
    args = ap.parse_args()

    import xml.etree.ElementTree as ET
    root = ET.parse(args.network).getroot()

    downstream = defaultdict(set)
    geo = {}
    for ln in root.iter("link"):
        no = ln.get("no")
        if no is None:
            continue
        f, t = ln.find("./fromLinkEndPt"), ln.find("./toLinkEndPt")
        pts = [(float(p.get("x")), float(p.get("y"))) for p in ln.iter("linkPolyPoint")]
        length = sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)) if len(pts) > 1 else 0.0
        geo[str(no)] = {
            "len_m": length,
            "lanes": max(1, len(ln.findall("./lanes/lane"))),
            "is_connector": f is not None and t is not None,
            "xy": pts[0] if pts else None,
        }
        if f is not None and t is not None:
            fl = (f.get("lane") or "").split()[0] if f.get("lane") else None
            tl = (t.get("lane") or "").split()[0] if t.get("lane") else None
            if fl and tl:
                # 커넥터를 **노드로** 넣는다. 예전에는 fl -> tl 로 건너뛰어서 커넥터에
                # 진입 간선이 없었고, 커넥터에서 시작한 BFS 가 즉시 끊겨 전부 '출구'가 됐다.
                downstream[fl].add(str(no))
                downstream[str(no)].add(tl)

    rows = list(csv.DictReader(open(args.roles, newline="", encoding="utf-8-sig")))
    stop_owner, centroid = {}, {}
    for r in rows:
        if str(r.get("active", "")).lower() != "true":
            continue
        no = int(r["no"])
        for l in parse_int_csv(r.get("unique_head_links", "")):
            stop_owner.setdefault(l, no)
        try:
            xy = json.loads(r.get("centroid_xy") or "[]")
            if len(xy) == 2:
                centroid[no] = (float(xy[0]), float(xy[1]))
        except Exception:
            pass

    # 2026-08-05: 커넥터를 분할에 **포함**한다.
    #   기존에는 `not g["is_connector"]` 로 걸러 냈는데, VBS 는 커넥터 위 차량도
    #   RW_CLASSIFY_UNMATCHED_AS_URBAN=True 로 urban_vehicles 에 넣는다. 실측 결과
    #   교차로 커넥터 426개가 359 대(도시부의 8.7%)를 싣고 있었다 — 분모에는 있고
    #   분자에는 없는 항목이라 귀속 기준 100% 가 원리적으로 불가능했다.
    #   같은 BFS 규칙이 그대로 적용된다: 접근로 중간 커넥터는 그 교차로 X, 교차로 내부
    #   회전 커넥터는 정지선을 이미 지났으므로 다음 교차로 Y 에 귀속된다(사용자 확인).
    urban = [l for l in geo if l not in FREEWAY_LINKS and l not in RAMP_METER_CONNECTORS]
    print(f"활성 SC {len(set(stop_owner.values()))}개, 정지선 링크 {len(stop_owner)}개")
    print(f"도시부 링크 {len(urban)}개 (커넥터 포함. 고속도로·램프미터커넥터 제외)")
    print()

    # 각 링크에서 하류로 최초 SC 를 찾는다 — 그 SC 가 소유자.
    # leg = **도달하는 정지선 링크**. 한 정지선이 곧 하나의 접근로이므로, centroid 방위로
    # 묶는 것보다 물리적으로 정확하다(방위로 묶으면 한 방위에 접근로가 여럿 몰린다).
    # 하류로 훑어 **처음 만나는 것**의 종류로 귀속을 정한다(사용자 확정 2026-08-05).
    #   신호 정지선 -> 그 플레이어의 approach queue
    #   고속도로 링크 -> freeway follower (기존에는 이것도 '출구' 로 섞였다)
    #   아무것도 없음(종단) -> 출구, 모니터링 전용
    # BFS 라 '처음' 은 홉 수 기준 최근접이다.
    owner, hops_to_owner, stop_of, freeway_bound = {}, {}, {}, {}
    for link in urban:
        if link in stop_owner:
            owner[link] = stop_owner[link]
            hops_to_owner[link] = 0
            stop_of[link] = link
            continue
        seen = {link}
        q = deque((n, 1) for n in downstream.get(link, ()))
        found = None
        while q and found is None:
            cur, h = q.popleft()
            if cur in seen or h > args.max_hops:
                continue
            seen.add(cur)
            if cur in stop_owner:
                found = ("sc", stop_owner[cur], h, cur)
                break
            if cur in FREEWAY_LINKS:
                found = ("fw", cur, h, None)
                break
            for n in downstream.get(cur, ()):
                q.append((n, h + 1))
        if found and found[0] == "sc":
            owner[link] = found[1]
            hops_to_owner[link] = found[2]
            stop_of[link] = found[3]
        elif found:
            freeway_bound[link] = found[1]

    # 하류에 SC 가 없는 링크 = 네트워크 **출구 계열**이다. 실측 확인(2026-08-05):
    # 미귀속 77개 전부가 출구로 향한다(하류 커넥터 자체가 없는 종단 63개 + 종단까지
    # SC 없이 이어지는 14개). 이 차량들은 이미 모든 교차로를 지나 빠져나가는 중이므로
    # **모니터링만 하고 플레이어에 귀속하지 않는다**(사용자 결정). 어느 플레이어의
    # approach queue 도 아니고, 제어로 바꿀 수 있는 상태도 아니다.
    exits = [l for l in urban if l not in owner and l not in freeway_bound]
    print(f"플레이어 귀속 {len(owner)}/{len(urban)}   freeway follower {len(freeway_bound)}개"
          f"   출구(모니터링 전용) {len(exits)}개")
    print("   -> 도시부 링크가 '귀속' / 'freeway' / '출구' 로 남김없이 나뉜다(분할 + 무누락).")

    # 상류 교차로 — 모델의 방향성 저류 SCa_to_SCb 를 만들려면 상류 a 가 필요하다.
    #
    # 2026-08-05: 처음엔 leg 방위로 인접표(derive_intersection_adjacency)와 조인했는데
    # 성공률이 126쌍 중 79쌍(63%)이었다. 인접표는 교차로-교차로 벡터로, 여기는 링크
    # 기하로 방위를 내기 때문에 굽거나 편심인 접근로에서 어긋난다. 그 결과 47쌍이
    # "인접 없는 방위"로 오분류돼 경계 저류로 새고, SC1001_to_SC1004 처럼 실제로 있는
    # 내부 저류가 용량을 못 받았다. 방위를 경유하지 말고 **같은 커넥터 그래프를 뒤집어**
    # 상류를 직접 찾는다 — owner 를 구한 BFS 와 정확히 같은 근거를 쓴다.
    upstream = defaultdict(set)
    for a, bs in downstream.items():
        for b in bs:
            upstream[b].add(a)
    up_owner = {}
    for link in owner:
        seen = {link}
        q = deque((n, 1) for n in upstream.get(link, ()))
        while q:
            cur, h = q.popleft()
            if cur in seen or h > args.max_hops:
                continue
            seen.add(cur)
            sc = stop_owner.get(cur)
            if sc is not None:
                if sc != owner[link]:
                    up_owner[link] = sc
                    break
                continue  # 같은 SC 의 다른 접근로 — 교차로 너머로 넘어가지 않는다.
            for n in upstream.get(cur, ()):
                q.append((n, h + 1))
    print(f"상류 SC 확정 {len(up_owner)}/{len(owner)}   (없으면 유입 경계 = 경계 저류)")

    # 도착 leg 방위 — 링크 시작점에서 소유 SC 중심으로의 방위의 반대(=SC 가 본 방향)
    # 정지선 링크의 방위 — 그 정지선 시작점에서 교차로 중심으로 본 방향.
    stop_leg = {}
    for s, sc in stop_owner.items():
        c, pt = centroid.get(sc), geo.get(s, {}).get("xy")
        if c and pt:
            stop_leg[s] = bearing_leg(pt[0] - c[0], pt[1] - c[1])
    # leg = **방위**. 한 접근로의 직진·좌회전 차로가 VISSIM 에서 별도 링크라 정지선 단위로
    # 쪼개면 과분할된다(실측: SC2 가 정지선 9개 = leg 9개). 물리적 leg 는 방위 하나이고
    # 같은 방위의 정지선들은 그 접근로의 차로다 — 하나의 leg 저류로 합친다.
    legs = {link: stop_leg.get(stop_of.get(link, ""), "?") for link in owner}

    by_owner = defaultdict(list)
    for l, sc in owner.items():
        by_owner[sc].append(l)
    from collections import Counter
    deg = Counter(len(v) for v in by_owner.values())
    print(f"플레이어 {len(by_owner)}개, 링크 수 분포 {dict(sorted(deg.items()))}")
    print()
    print(f"{'SC':>7}{'링크':>6}{'길이m':>9}{'차로합':>8}   leg 분포")
    for sc in sorted(by_owner):
        ls = by_owner[sc]
        L = sum(geo[l]["len_m"] for l in ls)
        lanes = sum(geo[l]["lanes"] for l in ls)
        lg = Counter(legs.get(l, "?") for l in ls)
        print(f"{sc:>7}{len(ls):>6}{L:>9.0f}{lanes:>8}   {dict(sorted(lg.items()))}")

    if args.json_out:
        payload = {
            "rule": "link -> first downstream signal controller (approach queue owner). strict partition.",
            "link_owner": {l: owner[l] for l in sorted(owner, key=lambda x: int(x))},
            "link_leg": {l: legs[l] for l in sorted(legs, key=lambda x: int(x))},
            "link_upstream": {l: up_owner[l] for l in sorted(up_owner, key=lambda x: int(x))},
            "link_stop_line": {l: stop_of[l] for l in sorted(stop_of, key=lambda x: int(x)) if l in owner},
            "link_geometry": {l: {"len_m": geo[l]["len_m"], "lanes": geo[l]["lanes"]}
                              for l in sorted(owner, key=lambda x: int(x))},
            "freeway_bound_links": {l: freeway_bound[l] for l in sorted(freeway_bound, key=lambda x: int(x))},
            "monitor_only_exit_links": exits,
            "urban_link_count": len(urban),
        }
        os.makedirs(os.path.dirname(os.path.abspath(args.json_out)) or ".", exist_ok=True)
        json.dump(payload, open(args.json_out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"\nJSON={args.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
