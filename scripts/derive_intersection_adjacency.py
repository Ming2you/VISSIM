# 교차로 간 인접관계를 네트워크에서 유도한다 — 모델 도시부를 격자로 연결하기 위한 재료.
#
# 왜 필요한가.
#   generate_real_world_distributed_players.py 는 각 SC 를 4-leg **경계 노드**로 만든다.
#   모든 leg 가 type=boundary 라 교차로가 서로 연결되지 않은 36 개의 독립 섬이다.
#   그래서 (1) 한 교차로에서 밀린 차가 옆 교차로로 번지는 파급이 모델에 없고,
#   (2) 교차로 **사이** 도로에 있는 차량을 담을 저류링크가 없어 관측 포착률이 낮다.
#
# 유도 방법.
#   정지선 신호두가 있는 링크 = 그 SC 로 진입하는 approach 다.
#   A 의 approach 링크에서 커넥터 그래프를 하류로 따라가다 처음 만나는 다른 SC 의
#   approach 링크가 B 라면 A -> B 가 인접이다(중간에 제3의 SC 를 지나면 중단).
#   leg 방위는 두 SC 의 centroid 방위각으로 N/S/E/W 에 배정한다.
#
# 사용:
#   python scripts/derive_intersection_adjacency.py [--max-hops 40] [--json-out out.json]
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


def numeric_id(value):
    return int(value)


def parse_int_csv(text):
    out = []
    for part in str(text or "").replace(";", ",").split(","):
        part = part.strip()
        if part:
            try:
                out.append(int(float(part)))
            except ValueError:
                pass
    return out


# 8방위(2026-08-04). 4방위로는 개포동 인접쌍 116개 중 21쌍이 표현 불가였다 —
# 같은 방위에 이웃이 둘 이상 걸려 순서 의존으로 버려졌다. 모델 코어도 8방위로 확장했다
# (NumSim-mine/src/models/grid_topology.py: LEG_DIRECTIONS/OPPOSITE_LEG/NS_AXIS).
LEG8 = ("E", "NE", "N", "NW", "W", "SW", "S", "SE")


def bearing_leg(dx, dy, legs8=True):
    """A 에서 B 로의 방위 -> A 쪽에서 본 leg 방위. 화면좌표는 y 가 북쪽 증가로 본다."""
    if not legs8:
        if abs(dx) >= abs(dy):
            return "E" if dx > 0 else "W"
        return "N" if dy > 0 else "S"
    import math as _m
    ang = _m.degrees(_m.atan2(dy, dx)) % 360.0
    return LEG8[int((ang + 22.5) // 45.0) % 8]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--network", default=DEFAULT_NET)
    ap.add_argument("--roles", default=DEFAULT_ROLES)
    ap.add_argument("--max-hops", type=int, default=40)
    ap.add_argument("--legs4", action="store_true", help="구 4방위로 유도(비교용)")
    ap.add_argument("--json-out", default="")
    args = ap.parse_args()

    import xml.etree.ElementTree as ET
    root = ET.parse(args.network).getroot()

    # 커넥터 그래프: fromLink -> [toLink]
    downstream = defaultdict(set)
    for ln in root.iter("link"):
        f = ln.find("./fromLinkEndPt")
        t = ln.find("./toLinkEndPt")
        if f is None or t is None:
            continue
        fl = (f.get("lane") or "").split()[0] if f.get("lane") else None
        tl = (t.get("lane") or "").split()[0] if t.get("lane") else None
        if fl and tl:
            downstream[fl].add(tl)

    rows = list(csv.DictReader(open(args.roles, newline="", encoding="utf-8-sig")))
    sc_links, centroid = {}, {}
    for r in rows:
        if str(r.get("active", "")).lower() != "true":
            continue
        no = int(r["no"])
        links = [str(x) for x in parse_int_csv(r.get("unique_head_links", ""))]
        if not links:
            continue
        sc_links[no] = set(links)
        try:
            xy = json.loads(r.get("centroid_xy") or "[]")
            if len(xy) == 2:
                centroid[no] = (float(xy[0]), float(xy[1]))
        except Exception:
            pass
    link_owner = {}
    for sc in sorted(sc_links):
        for l in sorted(sc_links[sc], key=numeric_id):
            link_owner.setdefault(l, sc)

    print(f"활성 SC {len(sc_links)}개, 정지선 링크 {len(link_owner)}개, 커넥터 그래프 노드 {len(downstream)}개")
    print()

    # A -> B 인접과 **그 사이 경로상의 링크**를 함께 모은다.
    #
    # 경로 링크가 왜 필요한가. 모델의 내부 directed link(SCa_to_SCb)는 두 교차로 **사이**
    # 도로다. 관측된 VISSIM 링크를 그 위에 귀속시키지 못하면 저류가 영원히 0 이고,
    # 연결형 토폴로지를 세워도 포착률이 안 오른다(2026-08-04 실측: 내부링크 140개 중 점유 0).
    # BFS 에서 부모 포인터를 남겨 A 의 정지선에서 B 의 정지선까지 지나온 링크를 기록한다.
    adjacency = defaultdict(set)
    path_links = defaultdict(set)   # (A, B) -> 그 사이 링크 집합
    for sc in sorted(sc_links):
        for start in sorted(sc_links[sc], key=numeric_id):
            seen = {start}
            parent = {}
            seeds = sorted(downstream.get(start, ()), key=numeric_id)
            q = deque((nxt, 1) for nxt in seeds)
            for nxt in seeds:
                parent[nxt] = None
            while q:
                cur, hops = q.popleft()
                if cur in seen or hops > args.max_hops:
                    continue
                seen.add(cur)
                owner = link_owner.get(cur)
                if owner is not None and owner != sc:
                    adjacency[sc].add(owner)
                    # 경로 역추적 — B 의 정지선 링크는 B 소유이므로 제외한다.
                    node = parent.get(cur)
                    while node is not None:
                        if link_owner.get(node) is None:
                            path_links[(sc, owner)].add(node)
                        node = parent.get(node)
                    continue  # 제3 SC 를 지나치지 않는다
                for nxt in sorted(downstream.get(cur, ()), key=numeric_id):
                    if nxt not in parent:
                        parent[nxt] = cur
                    q.append((nxt, hops + 1))

    print(f"{'SC':>7}{'차수':>5}  인접 SC")
    total = 0
    for sc in sorted(adjacency):
        nb = sorted(adjacency[sc])
        total += len(nb)
        print(f"{sc:>7}{len(nb):>5}  {nb}")
    isolated = sorted(set(sc_links) - set(adjacency))
    print()
    print(f"방향성 인접쌍 {total}개, 평균 차수 {total/max(len(adjacency),1):.1f}")
    if isolated:
        print(f"인접이 없는 SC {len(isolated)}개: {isolated}")

    # leg 방위 배정.
    #
    # 실제 도로망은 격자가 아니라 한 방위에 이웃이 둘 이상 붙는다(8방위로도 116쌍 중 13쌍이
    # 겹쳤고 그 10쌍이 인터체인지 클러스터였다). 방위 하나에 이웃 하나를 강제하면 그만큼
    # 버려지고, 어느 것을 버릴지가 순서 의존이라 재현성도 없다.
    #
    # 그래서 leg 키를 **'방위_이웃'** 복합으로 둔다. 방위는 접두사로 그대로 복원되므로
    # phase 배정(NS_AXIS)과 직진 유도(OPPOSITE_LEG)가 살아 있고 이웃은 하나도 안 버려진다.
    # 모델 쪽 지원: NumSim-mine/src/models/grid_topology.py 의 leg_base_dir().
    legs = defaultdict(dict)
    plain = defaultdict(dict)   # 비교용: 구 방식(방위 하나당 이웃 하나)
    conflicts = []
    for sc in sorted(adjacency):
        nbs = adjacency[sc]
        if sc not in centroid:
            continue
        ax, ay = centroid[sc]
        for nb in sorted(nbs):
            if nb not in centroid:
                continue
            bx, by = centroid[nb]
            leg = bearing_leg(bx - ax, by - ay, legs8=not args.legs4)
            legs[sc][f"{leg}_SC{nb}"] = nb
            if leg in plain[sc] and plain[sc][leg] != nb:
                conflicts.append((sc, leg, plain[sc][leg], nb))
            else:
                plain[sc][leg] = nb
    print()
    kept = sum(len(v) for v in legs.values())
    print(f"leg 배정된 SC {len(legs)}개, 복합 키 leg {kept}개 (인접쌍 {total}개 중 보존 {100*kept/max(total,1):.1f}%)")
    if conflicts:
        print(f"참고 — 구 방식(방위당 1이웃)이었다면 {len(conflicts)}쌍을 버렸을 것:")
        for c in conflicts[:6]:
            print(f"   SC{c[0]} leg {c[1]}: SC{c[2]} 유지, SC{c[3]} 탈락")
    from collections import Counter
    deg = Counter(len(v) for v in legs.values())
    print(f"leg 수 분포: {dict(sorted(deg.items()))}")
    base_deg = Counter(len({k.split('_', 1)[0] for k in v}) for v in legs.values())
    print(f"사용 방위 수 분포: {dict(sorted(base_deg.items()))}")
    seg_links = {l for v in path_links.values() for l in v}
    print(f"내부 구간을 이루는 VISSIM 링크 {len(seg_links)}개, 구간 {len([1 for v in path_links.values() if v])}개")

    if args.json_out:
        payload = {
            "adjacency": {str(k): sorted(adjacency[k]) for k in sorted(adjacency)},
            "legs": {
                str(k): {leg: legs[k][leg] for leg in sorted(legs[k])}
                for k in sorted(legs)
            },
            "isolated": isolated,
            "would_be_dropped_if_single_neighbor_per_direction": [
                {"sc": c[0], "leg": c[1], "kept": c[2], "dropped": c[3]} for c in conflicts
            ],
            "pair_count": total,
            "leg_count": sum(len(v) for v in legs.values()),
            # 내부 directed link(SCa_to_SCb) -> 그 구간을 이루는 VISSIM 링크.
            # build_detector_mapping 이 관측 링크를 이 저류에 귀속시키는 데 쓴다.
            "internal_link_members": {
                f"SC{a}_to_SC{b}": sorted(v, key=numeric_id)
                for (a, b), v in sorted(path_links.items()) if v
            },
        }
        os.makedirs(os.path.dirname(os.path.abspath(args.json_out)) or ".", exist_ok=True)
        json.dump(payload, open(args.json_out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"\nJSON={args.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
