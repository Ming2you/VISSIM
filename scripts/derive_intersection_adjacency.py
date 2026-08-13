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
#   leg 방위는 **그 접근을 실제로 나르는 정지선 링크가 A 에 들어오는 방향**이다.
#
# leg 방위를 왜 중심 방위각으로 정하면 안 되는가(2026-08-11).
#   모델은 노드 A 의 leg `{방위}_SC{B}` 를 origin `SCB_to_SCA` — 즉 **B 에서 A 로 들어오는
#   접근** — 의 방위로 읽는다(derive_movement_signal_group_map.origin_leg_bearings).
#   그런데 두 교차로 중심을 잇는 현(弦)의 방위각은 그 접근로가 실제로 어느 쪽에서
#   들어오는지와 다르다. 도로가 굽기 때문이다. 실측:
#
#       SC1004 는 SC1001 의 남쪽   -> 중심 방위각 S      (구 규칙)
#       그 접근을 나르는 정지선 링크 32 는 SC1001 에 **서쪽**에서 들어온다
#       배정 산출물이 이미 안다:  link_leg["32"] = "W", link_leg["71"] = "SW"
#
#   `NS_AXIS = {N,S,NW,SE}` 가 leg 방위로 현시를 정하므로 S 는 p1(남북), W 는 p2(동서)다.
#   그래서 EW 축 SG2·SG5 가 p1 으로 끌려 들어가 SC1001/SC1004 의 p1 이 두 축의 합집합
#   141.0 s (주기 150 s 의 94%) 가 됐다. 한 현시가 그럴 수는 없다.
#
#   측정된 접근 방위와 두 폴백 후보를 실측 114쌍으로 대조했다.
#       중심 방위각      정확 93/114 (81.6%)   축 일치 112/114 (98.2%)  <- 축 오류 2건이 이 결함
#       역방향의 반대    정확 88/108 (81.5%)   축 일치 108/108 (100%)
#   역방향-반대는 축은 다 맞지만 SC1001 의 `NW_SC2001` 을 `N` 으로 옮겨 램프 leg 이
#   설 자리(빈 정방위)를 없앤다. 그래서 채택하지 않았다. 측정값이 없으면 중심 방위각으로
#   떨어지고 그 수를 산출물과 콘솔에 남긴다.
#
# 사용:
#   python scripts/derive_intersection_adjacency.py [--max-hops 40] [--json-out out.json]
#       [--link-assignment-json outputs/link_player_assignment_20260805.json]
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
DEFAULT_ASSIGNMENT = os.path.join(REPO, "outputs", "link_player_assignment_20260805.json")


# assign_links_to_players.py 의 FREEWAY_LINKS 와 같은 집합이다. 두 곳이 갈리면 안 된다.
FREEWAY_MAINLINE = {"2", "24", "26", "74", "10699", "10702"}


def _point_seg_dist(px, py, a, b):
    """점 (px,py) 에서 선분 a-b 까지의 거리."""
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


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


def approach_legs_from_assignment(assignment):
    """(소유 SC, 상류 SC) -> 그 접근을 나르는 정지선 링크의 물리 방위.

    `assign_links_to_players.py` 산출물이 재료다. 그 스크립트는 링크마다
    `link_owner`(하류 최초 SC), `link_upstream`(상류 최초 SC), `link_leg`(그 링크가
    도달하는 정지선의 방위 = 정지선 시작점에서 소유 SC 중심으로 본 방향)를 준다.
    그러므로 owner=A, upstream=B 인 링크들의 `link_leg` 가 곧 "B 에서 A 로 들어오는
    접근의 방위" 다.

    한 접근에 링크가 여럿이면(직진·좌회전 차로가 별 링크) 어떻게 하나로 모으는가.
    `assign_links_to_players` 가 이미 **정지선 단위가 아니라 방위 단위로** 묶어 두었다
    (같은 방위의 정지선들은 한 접근로의 차로다). 실측으로 확인했다 — 114쌍 전부에서
    `link_leg` 값이 하나뿐이라 모을 것이 없다. 그래도 망이 바뀌면 갈릴 수 있으므로
    갈리면 버리지 말고 **그 쌍을 미측정으로 돌려** 폴백이 세도록 한다(조용한 임의 선택 금지).
    """
    owner = assignment.get("link_owner") or {}
    upstream = assignment.get("link_upstream") or {}
    leg = assignment.get("link_leg") or {}
    seen = defaultdict(set)
    for link, a in owner.items():
        b = upstream.get(link)
        if b is None:
            continue
        d = leg.get(link)
        if d and d != "?":
            seen[(int(a), int(b))].add(d)
    return {pair: next(iter(v)) for pair, v in seen.items() if len(v) == 1}, \
           {pair: sorted(v) for pair, v in seen.items() if len(v) > 1}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--network", default=DEFAULT_NET)
    ap.add_argument("--roles", default=DEFAULT_ROLES)
    ap.add_argument("--max-hops", type=int, default=40)
    ap.add_argument("--legs4", action="store_true", help="구 4방위로 유도(비교용). 접근로 방위를 안 쓴다")
    ap.add_argument("--link-assignment-json", default=DEFAULT_ASSIGNMENT,
                    help="assign_links_to_players.py 산출 JSON. leg 방위의 근거. "
                         "빈 문자열이면 구 규칙(중심 방위각)으로 떨어진다")
    ap.add_argument("--json-out", default="")
    # ── 2026-08-13 추가. 기본값은 구 동작 그대로다(radius 0, 배제 없음). ──────────
    ap.add_argument(
        "--intersection-radius", type=float, default=0.0,
        help="0 보다 크면 **형상으로도** 통과를 판정한다. 걷는 링크의 폴리라인이 제3 SC 의 "
             "centroid 이 반경[m] 안을 지나면 그 SC 에 도달한 것으로 보고 멈춘다. "
             "구 규칙은 정지선 신호두가 달린 링크로만 통과를 판정해서, 신호두가 없는 "
             "자유 우회전으로 교차로를 빠져나가면 중단이 발동하지 않았다(2026-08-13 실측: "
             "8쌍이 제어 신호 SC11·SC12·SC101·SC109 를 관통했고 전부 A-C-B 2홉의 중복이었다)")
    ap.add_argument(
        "--exclude-freeway", action="store_true",
        help="고속도로 본선·램프 링크를 걷기에서 뺀다. 도시 격자 인접을 유도하는데 커넥터가 "
             "램프로 올라가 본선을 타고 다른 램프로 내려오면, 도시 도로로는 안 이어진 두 "
             "교차로가 인접이 된다(2026-08-13 실측: 7쌍이 도시 링크를 하나도 안 쓴다)")
    ap.add_argument(
        "--through-nodes", default="",
        help="쉼표로 구분한 SC 번호. 이 노드는 **교차로가 아니라 블록 중간 요소**로 본다 — "
             "걷기가 여기서 멈추지 않고 지나가며, 그 링크는 지나온 구간의 저류에 들어간다. "
             "보행자 midblock 신호가 노드로 들어오면 한 블록이 여러 구간으로 쪼개져, 실제로는 "
             "이웃인 교차로 둘이 인접이 아니게 된다(예: SC105 포이사거리 ↔ SC1 구룡초교 사이에 "
             "SC9001·SC9002 가 끼어 있다). 이 목록의 노드는 인접 그래프에서 빠진다")
    ap.add_argument(
        "--player-nodes", default="",
        help="쉼표로 구분한 SC 번호 = urban player. 주면 **2차 걷기**를 한 번 더 돌린다 — "
             "player 에서 출발해 다른 player 를 만날 때까지 비-player 를 그냥 지나가며, "
             "그렇게 찾은 player↔player 인접을 기존 인접에 **더한다**. 분기점(비-player) 은 "
             "노드로 그대로 남는다. 비-player 는 제어 레버가 아니므로 그 위를 건너뛰는 간선이 "
             "신호를 우회하지 않는다 — 제어 신호를 우회하던 2026-08-13 결함과는 다른 경우다")
    ap.add_argument(
        "--player-max-span", type=int, default=0,
        help="2차 걷기에서 player↔player 간선이 건너뛸 수 있는 **비-player SC 개수 상한**. "
             "0 이면 무제한. 무제한이면 비-player 가 사슬로 늘어선 구간(SC2001~SC2005)에서 "
             "2 km 짜리 '인접' 이 생긴다 — 물리적으로 인접이라 보기 어렵다")
    ap.add_argument(
        "--player-barrier-degree", type=int, default=0,
        help="2차 걷기에서 **비-player 라도 이 차수 이상이면 멈춘다**(1차 인접 기준 차수). "
             "3 을 주면 분기점을 넘지 않는다 — midblock(차수 2) 만 접힌다. 분기점을 건너뛰면 "
             "갈래가 다른 두 player 가 한 구간처럼 묶인다(예: SC108↔SC12 가 SC7·SC16 을 넘어 "
             "1,085 m). 0 이면 끄기")
    ap.add_argument(
        "--player-barrier-nodes", default="",
        help="차수와 무관하게 2차 걷기를 멈출 비-player SC 번호. --player-barrier-degree 와 합쳐진다")
    args = ap.parse_args()

    import xml.etree.ElementTree as ET
    root = ET.parse(args.network).getroot()

    # 링크 폴리라인 — 형상 기반 통과 판정과 배제에 쓴다.
    link_pts = {}
    for ln in root.iter("link"):
        no = ln.get("no")
        pp = ln.find("./geometry/linkPolyPts")
        if no is None or pp is None:
            continue
        pts = [(float(p.get("x")), float(p.get("y"))) for p in pp]
        if len(pts) >= 2:
            link_pts[no] = pts

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
    # 통과 노드 — 교차로가 아니라 블록 중간 요소. 노드 집합에서 빼고, 그 정지선 링크는
    # 소유자 없는 링크로 남겨 지나온 구간의 저류 멤버가 되게 한다.
    through = {int(x) for x in parse_int_csv(args.through_nodes)} if args.through_nodes else set()
    through &= set(sc_links)
    through_links = set()
    if through:
        for sc in sorted(through):
            through_links |= sc_links.pop(sc)
            centroid.pop(sc, None)
        print(f"통과 노드 {len(through)}개 제외: {sorted(through)}  (정지선 링크 {len(through_links)}개는 구간 멤버로 남긴다)")

    link_owner = {}
    for sc in sorted(sc_links):
        for l in sorted(sc_links[sc], key=numeric_id):
            link_owner.setdefault(l, sc)

    print(f"활성 SC {len(sc_links)}개, 정지선 링크 {len(link_owner)}개, 커넥터 그래프 노드 {len(downstream)}개")

    # 배제 링크 — 고속도로 본선·램프.
    excluded = set()
    if args.exclude_freeway:
        excluded |= FREEWAY_MAINLINE
        if args.link_assignment_json and os.path.isfile(args.link_assignment_json):
            _a = json.load(open(args.link_assignment_json, encoding="utf-8"))
            excluded |= {str(x) for x in _a.get("freeway_bound_links", [])}
        print(f"배제 링크 {len(excluded)}개(고속도로 본선·램프)")

    # 형상 통과 판정 — 링크 -> 그 폴리라인이 반경 안을 지나는 SC 집합.
    near_sc = defaultdict(set)
    if args.intersection_radius > 0:
        R = args.intersection_radius
        for lid, pts in link_pts.items():
            for sc, (cx, cy) in centroid.items():
                if any(_point_seg_dist(cx, cy, pts[i], pts[i + 1]) < R for i in range(len(pts) - 1)):
                    near_sc[lid].add(sc)
        hit = sum(1 for v in near_sc.values() if v)
        print(f"형상 통과 판정 반경 {R:.0f} m — 링크 {hit}개가 SC 중심 반경 안을 지난다")
    print()

    # A -> B 인접과 **그 사이 경로상의 링크**를 함께 모은다.
    #
    # 경로 링크가 왜 필요한가. 모델의 내부 directed link(SCa_to_SCb)는 두 교차로 **사이**
    # 도로다. 관측된 VISSIM 링크를 그 위에 귀속시키지 못하면 저류가 영원히 0 이고,
    # 연결형 토폴로지를 세워도 포착률이 안 오른다(2026-08-04 실측: 내부링크 140개 중 점유 0).
    # BFS 에서 부모 포인터를 남겨 A 의 정지선에서 B 의 정지선까지 지나온 링크를 기록한다.
    adjacency = defaultdict(set)
    path_links = defaultdict(set)   # (A, B) -> 그 사이 링크 집합
    geometric_stops = []            # 형상으로만 잡힌 통과 (sc, 도달SC, 링크)

    def walk(origins, stop_owner, stop_near, record_geo=True, max_span=0):
        """origins 의 정지선에서 출발해 stop_owner 에 잡히는 SC 까지 걷는다.

        stop_owner 에 없는 SC 는 **그냥 지나간다** — 그 SC 의 정지선 링크도 소유자가
        없으므로 지나온 구간의 저류 멤버가 된다. 두 번째 호출에서 player 만 stop_owner
        에 넣으면 player↔player 인접이 나온다.
        """
        for sc in sorted(origins):
            for start in sorted(origins[sc], key=numeric_id):
                seen = {start}
                parent = {}
                seeds = [n for n in sorted(downstream.get(start, ()), key=numeric_id) if n not in excluded]
                q = deque((nxt, 1) for nxt in seeds)
                for nxt in seeds:
                    parent[nxt] = None
                while q:
                    cur, hops = q.popleft()
                    if cur in seen or hops > args.max_hops:
                        continue
                    seen.add(cur)
                    owner = stop_owner.get(cur)
                    # 정지선으로 못 잡는 통과를 형상으로 잡는다. 신호두가 없는 자유 우회전이
                    # 여기로 걸린다. 도달 SC 는 반경 안에 든 것 중 하나면 된다(중단이 목적).
                    if owner is None or owner == sc:
                        geo_hit = sorted(stop_near.get(cur, frozenset()) - {sc})
                        if geo_hit:
                            owner = geo_hit[0]
                            if record_geo:
                                geometric_stops.append((sc, owner, cur))
                    if owner is not None and owner != sc:
                        # 경로 역추적 — B 의 정지선 링크는 B 소유이므로 제외한다.
                        chain, spanned = [], set()
                        node = parent.get(cur)
                        while node is not None:
                            if stop_owner.get(node) is None:
                                chain.append(node)
                                mid = link_owner.get(node)
                                if mid is not None and mid not in (sc, owner):
                                    spanned.add(mid)
                            node = parent.get(node)
                        if max_span and len(spanned) > max_span:
                            continue  # 너무 멀리 건너뛴다 — 인접으로 세지 않는다
                        adjacency[sc].add(owner)
                        path_links[(sc, owner)].update(chain)
                        continue  # 도달 SC 를 지나치지 않는다
                    for nxt in sorted(downstream.get(cur, ()), key=numeric_id):
                        if nxt in excluded:
                            continue
                        if nxt not in parent:
                            parent[nxt] = cur
                        q.append((nxt, hops + 1))

    walk(sc_links, link_owner, near_sc)

    # 2차 걷기 — player 만 정차점으로 두고 비-player 를 지나간다. 결과는 **더한다**.
    players = {int(x) for x in parse_int_csv(args.player_nodes)} if args.player_nodes else set()
    players &= set(sc_links)
    player_pairs_added = 0
    barrier = set()
    if players:
        before = {k: set(v) for k, v in adjacency.items()}

        # 장벽 — player 가 아니어도 2차 걷기를 멈추는 노드. 분기점을 건너뛰지 않기 위한 것.
        base_deg = defaultdict(set)
        for a, nbs in adjacency.items():
            for b in nbs:
                base_deg[a].add(b)
                base_deg[b].add(a)
        barrier = {int(x) for x in parse_int_csv(args.player_barrier_nodes)} if args.player_barrier_nodes else set()
        if args.player_barrier_degree > 0:
            barrier |= {sc for sc in sc_links
                        if sc not in players and len(base_deg.get(sc, ())) >= args.player_barrier_degree}
        barrier &= set(sc_links) - players
        if barrier:
            print(f"2차 걷기 장벽 {len(barrier)}개(비-player 분기점): {sorted(barrier)}")

        stops = players | barrier
        p_owner = {l: sc for l, sc in link_owner.items() if sc in stops}
        p_near = defaultdict(set)
        for lid, scs in near_sc.items():
            hit = scs & stops
            if hit:
                p_near[lid] = hit
        walk({sc: sc_links[sc] for sc in players}, p_owner, p_near,
             record_geo=False, max_span=args.player_max_span)
        player_pairs_added = sum(len(adjacency[k] - before.get(k, set())) for k in adjacency)
        span_note = f", 건너뛰기 상한 {args.player_max_span}" if args.player_max_span else ", 상한 없음"
        print(f"player {len(players)}개로 2차 걷기{span_note} — 방향성 인접 {player_pairs_added}개 추가")

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
    approach_leg, split_pairs = {}, {}
    if args.link_assignment_json and not args.legs4:
        _assign = json.load(open(args.link_assignment_json, encoding="utf-8"))
        approach_leg, split_pairs = approach_legs_from_assignment(_assign)
        print()
        print(f"배정 JSON: {args.link_assignment_json}  접근 방위 {len(approach_leg)}쌍"
              f"  방위가 갈린 쌍 {len(split_pairs)}개")

    legs = defaultdict(dict)
    plain = defaultdict(dict)   # 비교용: 구 방식(방위 하나당 이웃 하나)
    conflicts = []
    leg_source = {}             # (sc, nb) -> "approach" | "centroid_fallback"
    centroid_fallback = []      # 접근로 측정이 없어 현(弦) 방위각으로 떨어진 쌍
    changed_by_approach = []    # 구 규칙과 달라진 쌍
    for sc in sorted(adjacency):
        nbs = adjacency[sc]
        if sc not in centroid:
            continue
        ax, ay = centroid[sc]
        for nb in sorted(nbs):
            if nb not in centroid:
                continue
            bx, by = centroid[nb]
            chord = bearing_leg(bx - ax, by - ay, legs8=not args.legs4)
            leg = approach_leg.get((sc, nb))
            if leg is None:
                leg, source = chord, "centroid_fallback"
                centroid_fallback.append((sc, nb, chord))
            else:
                source = "approach"
                if leg != chord:
                    changed_by_approach.append((sc, nb, chord, leg))
            leg_source[(sc, nb)] = source
            legs[sc][f"{leg}_SC{nb}"] = nb
            if leg in plain[sc] and plain[sc][leg] != nb:
                conflicts.append((sc, leg, plain[sc][leg], nb))
            else:
                plain[sc][leg] = nb
    print()
    n_app = sum(1 for v in leg_source.values() if v == "approach")
    print(f"leg 방위 근거: 접근로 실측 {n_app}개, 중심 방위각 폴백 {len(centroid_fallback)}개")
    if centroid_fallback:
        print("   폴백 쌍(접근을 나르는 링크가 배정 산출물에 없다):")
        for a, b, d in centroid_fallback:
            print(f"      SC{a} -> SC{b}: {d}")
    print(f"구 규칙(중심 방위각)과 달라진 leg {len(changed_by_approach)}개:")
    for a, b, old, new in changed_by_approach:
        ns = {"N", "S", "NW", "SE"}
        flip = "  ** 축 뒤집힘 **" if ((old in ns) != (new in ns)) else ""
        print(f"      SC{a} -> SC{b}: {old} -> {new}{flip}")
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
            # 이 산출물이 어떤 규칙으로 나왔는지. 구 산출물과 섞이면 안 된다.
            "derivation": {
                "network": os.path.basename(args.network),
                "intersection_radius_m": args.intersection_radius,
                "exclude_freeway": bool(args.exclude_freeway),
                "excluded_link_count": len(excluded),
                "player_nodes": sorted(players),
                "player_pairs_added": player_pairs_added,
                "player_max_span": args.player_max_span,
                "player_barrier_degree": args.player_barrier_degree,
                "player_barrier_nodes": sorted(barrier) if players else [],
                "through_nodes": sorted(through),
                "through_link_count": len(through_links),
                "geometric_stop_count": len(geometric_stops),
                "geometric_stops": [
                    {"from": a, "reached": b, "link": l} for a, b, l in geometric_stops
                ],
            },
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
