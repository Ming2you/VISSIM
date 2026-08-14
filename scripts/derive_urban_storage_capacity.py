# 도시부 저류 용량·길이를 **실제 기하**에서 유도한다.
#
# 왜 필요한가.
#   생성기가 용량을 상수로 박고 있었다(경계 220, 내부 220, 램프큐 180, 오프램프 120).
#   실제 기하와 0.61x ~ 74x 어긋난다. 특히 SC1001_to_SC1004 는 물리 8,896 대인데 모델이 120 대로
#   보아 **모든 상태에서 v/c = 1.000** 이 된다. 그 결과 g6 spillback 이 72/72 레코드에서
#   (예측,관측)=(True,True) 가 되어 F1 이 1.000 으로 나왔다 — 개선이 아니라 용량 과소의 인공물이다.
#   게다가 adapter:566-569 의 min(capacity, current+share) 가 넘치는 관측을 잘라내 포착률도 깎는다.
#
# 입력.
#   scripts/assign_links_to_players.py 의 산출 — 링크가 (SC, leg) 로 **분할** 귀속돼 있다.
#   한 링크는 정확히 한 (SC, leg) 에만 속하므로 합산에 중복이 없다.
#
# 유도.
#   capacity[(SC,leg)] = sum(길이_km x 차로수) x jam_density
#   length[(SC,leg)]   = sum(길이_m)          (직렬 가정. 병렬 판정은 아래 --parallel-mode 참조)
#   jam_density 는 --jam 으로 주거나 실측 역산(--jam auto)한다.
#
# 모델 저류 이름 대응.
#   모델의 내부 directed link SCa_to_SCb 는 A 에서 B 로 가는 차량을 담는다. 사용자 규칙에서
#   그 차량은 **B 의 approach queue(A 방향)** 이므로, 멤버는 (SCb, A 를 향한 leg 방위) 의 링크다.
#   인접이 없는 방위의 approach 는 경계 저류 {SC}_{leg}_out 에 대응시킨다.
import argparse
import csv
import io
import json
import os
import statistics as st
import sys
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_ASSIGN = os.path.join(REPO, "outputs", "link_player_assignment_20260805.json")
DEFAULT_ADJ = os.path.join(REPO, "outputs", "intersection_adjacency8_20260804.json")


def derive_jam_density(assign, links_csv, t0):
    """정체 표본(속도<3kph 이고 정지차가 절반 이상)의 밀도 상위값을 jam density 로 본다.

    함정 — 관측창이 짧거나 정체가 안 나면 과소추정된다. 그래서 표본 수와 분포를 함께 찍고,
    표본이 부족하면 호출부가 물리 상수로 폴백하게 None 을 돌려준다.
    """
    geo = assign["link_geometry"]
    per = defaultdict(list)
    with open(links_csv, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if float(r["sim_sec"]) < t0:
                continue
            l = r["link"]
            if l in geo:
                per[l].append((float(r["count"]), float(r["mean_speed_kph"]), float(r["stopped_count"])))
    ks = []
    for l, v in per.items():
        g = geo[l]
        lkm = g["len_m"] / 1000.0
        if lkm <= 0.02:
            continue
        jam = [n / lkm / g["lanes"] for n, sp, stp in v if n > 0 and sp < 3.0 and stp >= 0.5 * n]
        if jam:
            ks.append(max(jam))
    if len(ks) < 10:
        return None, len(ks), []
    ks.sort()
    return ks[int(0.9 * (len(ks) - 1))], len(ks), ks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--assignment", default=DEFAULT_ASSIGN)
    ap.add_argument("--adjacency", default=DEFAULT_ADJ)
    ap.add_argument("--links-csv", default="", help="jam auto 역산용 bottleneck_links CSV")
    ap.add_argument("--t0", type=float, default=2700.0)
    ap.add_argument("--jam", default="auto", help="veh/km/lane 숫자 또는 auto")
    ap.add_argument("--jam-fallback", type=float, default=130.0)
    ap.add_argument("--min-capacity", type=float, default=10.0, help="너무 작은 저류의 하한")
    ap.add_argument("--json-out", default="")
    ap.add_argument(
        "--storage-override",
        default="",
        help="링크 -> 저류 이름 강제 지정 JSON. 유도 이름이 격자에 없는 링크를 "
             "기존 저류로 귀속시킨다 — link_storage_override_*.json 형식",
    )
    args = ap.parse_args()

    # 2026-08-14: 결손 저류 구제.
    #
    # 상류 BFS 는 `stop_owner[cur] != owner[link]` 로 **자기 SC 의 정지선을 건너뛴다**.
    # 정지선이 여럿인 큰 교차로(SC4·SC5·SC9·SC9001)에서는 한 정지선의 상류가 같은 SC 의
    # 다른 정지선뿐이라, 후보가 영영 안 나오고 "상류 없음 -> 유입 경계"로 떨어진다.
    # 그렇게 지어진 SC{n}_{대각방위}_out 은 격자에 게이트가 없어 저류가 안 세워지고,
    # 그 링크 위 차량이 어느 대기행렬에도 안 잡힌다(실측 14곳 923 veh).
    #
    # 방위 규칙으로는 못 푸는 자리라, 어느 구간에 속하는지를 밖에서 받는다.
    storage_override: dict[str, str] = {}
    if args.storage_override:
        _ov = json.load(open(args.storage_override, encoding="utf-8"))
        for link, spec in (_ov.get("override") or {}).items():
            name = spec.get("storage") if isinstance(spec, dict) else spec
            if name:
                storage_override[str(link)] = str(name)

    assign = json.load(open(args.assignment, encoding="utf-8"))
    owner, leg, geo = assign["link_owner"], assign["link_leg"], assign["link_geometry"]

    jam, n_samp, dist = args.jam_fallback, 0, []
    if args.jam == "auto":
        if not args.links_csv:
            print("경고 — --jam auto 인데 --links-csv 가 없다. 폴백을 쓴다.")
        else:
            got, n_samp, dist = derive_jam_density(assign, args.links_csv, args.t0)
            if got is None:
                print(f"경고 — 정체 표본이 {n_samp}개뿐이라 역산이 불안정하다. 폴백 {args.jam_fallback} 을 쓴다.")
            else:
                jam = got
    else:
        jam = float(args.jam)

    print(f"jam density = {jam:.1f} veh/km/lane" + (f"  (정체 표본 {n_samp}개의 p90)" if dist else "  (지정/폴백)"))
    if dist:
        print(f"   표본 분포: 중앙 {st.median(dist):.1f}  p75 {dist[3*len(dist)//4]:.1f}"
              f"  p90 {dist[int(0.9*len(dist))]:.1f}  최대 {max(dist):.1f}")
    print()

    # 저류 이름은 **링크의 상류 SC** 로 직접 짓는다.
    #
    # 2026-08-05 정정: 이전 판은 (SC, leg방위) 로 묶어 인접표와 방위로 조인했는데
    # 126쌍 중 79쌍(63%)만 맞았다. 두 스크립트가 방위를 다르게 계산하기 때문이다
    # (인접표=교차로간 벡터, 배정=링크 기하). 실패한 47쌍이 경계 저류로 새면서
    # SC1001_to_SC1004 같은 실제 내부 저류가 용량을 못 받았다. 이제 배정 스크립트가
    # 커넥터 그래프를 뒤집어 구한 link_upstream 을 쓴다 — 방위를 경유하지 않는다.
    up_owner = assign.get("link_upstream") or {}
    if not up_owner:
        print("오류 — assignment 에 link_upstream 이 없다. assign_links_to_players.py 를 다시 돌려라.")
        return 2

    # 2026-08-14: 분수 귀속(link_split / link_upstream_split)을 받는다.
    #
    # tie 링크는 물리적으로 소유자가 하나가 아니다 — 지하차도·램프 분기처럼 한 링크가
    # 정지선 둘 이상을 먹인다. assign_links_to_players.py 가 레거시 3분할에는
    # legacy_bucket 으로 한 자리만 넣고, 실제 배분은 link_split 로 싣는다. 저류는
    # 그 배분대로 나눠야 "SC 에 녹색을 주면 이 저류가 빠진다"는 관계가 성립한다.
    #
    # 하류 몫 x 상류 몫의 곱으로 통에 넣는다. freeway/termination 몫은 도시부 저류가
    # 아니므로 버리되, 얼마를 버렸는지 반드시 출력한다(조용한 누락 금지).
    split = assign.get("link_split") or {}
    up_split = assign.get("link_upstream_split") or {}

    def _down_parts(l, sc):
        """[(소유 SC, 지분)] — 도시부 몫만. 비도시부 지분은 두 번째 값으로 돌려준다."""
        spec = split.get(l)
        if not spec:
            return [(int(sc), 1.0)], 0.0
        urban, other = [], 0.0
        for p in spec.get("parts", []):
            to, share = str(p.get("to", "")), float(p.get("share", 0.0))
            if to.startswith("SC"):
                urban.append((int(to[2:]), share))
            else:
                other += share
        return (urban or [(int(sc), 1.0)]), (other if urban else 0.0)

    def _up_parts(l, up):
        """[(상류 SC 또는 None, 지분)]"""
        spec = up_split.get(l)
        if not spec:
            return [(up, 1.0)]
        out = []
        for p in spec.get("upstream", []):
            to, share = str(p.get("to", "")), float(p.get("share", 0.0))
            out.append((int(to[2:]) if to.startswith("SC") else None, share))
        return out or [(up, 1.0)]

    caps, lens = {}, {}
    n_int = n_bnd = 0
    n_split = 0
    n_ovr = 0
    ovr_veh = 0.0
    dropped_veh = 0.0
    for l, sc in owner.items():
        g = geo[l]
        cap_l = g["len_m"] / 1000.0 * g["lanes"] * jam
        # 강제 지정이 있으면 유도 이름 대신 그 저류에 통째로 넣는다.
        forced = storage_override.get(l)
        if forced:
            caps[forced] = caps.get(forced, 0.0) + cap_l
            lens[forced] = lens.get(forced, 0.0) + g["len_m"]
            n_ovr += 1
            ovr_veh += cap_l
            continue
        dparts, other_share = _down_parts(l, sc)
        uparts = _up_parts(l, up_owner.get(l))
        if len(dparts) > 1 or len(uparts) > 1 or other_share > 0.0:
            n_split += 1
        dropped_veh += cap_l * other_share
        for own_sc, ds in dparts:
            for up_sc, us in uparts:
                w = ds * us
                if w <= 0.0:
                    continue
                if up_sc is not None:
                    name = f"SC{int(up_sc)}_to_SC{int(own_sc)}"   # 상류 -> 나 방향이 곧 내 approach 다
                    n_int += 1
                else:
                    name = f"SC{int(own_sc)}_{leg.get(l, '?')}_out"   # 상류 SC 가 없으면 유입 경계
                    n_bnd += 1
                caps[name] = caps.get(name, 0.0) + cap_l * w
                lens[name] = lens.get(name, 0.0) + g["len_m"] * w
    if n_split:
        print(f"분수 귀속 적용 링크 {n_split}개 "
              f"(하류분할 {len(split)}건 · 상류분할 {len(up_split)}건 근거)")
        print(f"   도시부 아닌 몫으로 제외한 저류 {dropped_veh:,.0f} veh "
              f"(freeway/termination 지분)")
    if n_ovr:
        print(f"저류 강제 지정 링크 {n_ovr}개 · {ovr_veh:,.0f} veh "
              f"({os.path.basename(args.storage_override)})")
    caps = {k: max(args.min_capacity, v) for k, v in caps.items()}

    n_ib = sum(1 for k in caps if "_to_" in k)
    print(f"모델 저류 {len(caps)}개 유도  (내부 {n_ib}개 <- 링크 {n_int}개,"
          f"  경계 {len(caps)-n_ib}개 <- 링크 {n_bnd}개)")
    adj_pairs = set(json.load(open(args.adjacency, encoding="utf-8"))["internal_link_members"])
    derived_int = {k for k in caps if "_to_" in k}
    print(f"   인접표의 내부 pair {len(adj_pairs)}개와 대조: 일치 {len(derived_int & adj_pairs)}개,"
          f"  유도에만 {len(derived_int - adj_pairs)}개,  인접표에만 {len(adj_pairs - derived_int)}개")
    vals = sorted(caps.values())
    print(f"용량: 중앙 {st.median(vals):.0f}  p10 {vals[len(vals)//10]:.0f}  p90 {vals[9*len(vals)//10]:.0f}"
          f"  최소 {min(vals):.0f}  최대 {max(vals):.0f}  총 {sum(vals):.0f}")
    print(f"길이: 총 {sum(lens.values())/1000:.1f} km")
    print()
    print(f"{'모델 저류':<26}{'용량veh':>9}{'길이m':>9}")
    for k in sorted(caps, key=lambda x: -caps[x])[:10]:
        print(f"{k:<26}{caps[k]:>9.0f}{lens[k]:>9.0f}")

    if args.json_out:
        payload = {
            "jam_density_veh_km_lane": jam,
            "jam_sample_count": n_samp,
            "urban_link_storage_veh": {k: round(v, 1) for k, v in sorted(caps.items())},
            "urban_link_length_km": {k: round(v / 1000.0, 4) for k, v in sorted(lens.items())},
            "source": "scripts/derive_urban_storage_capacity.py",
            "note": "링크는 assign_links_to_players.py 의 분할 귀속을 쓴다(중복 없음). "
                    "link_split / link_upstream_split 이 있으면 그 지분대로 나눈다.",
            "fractional_links": n_split,
            "excluded_non_urban_veh": round(dropped_veh, 1),
        }
        os.makedirs(os.path.dirname(os.path.abspath(args.json_out)) or ".", exist_ok=True)
        json.dump(payload, open(args.json_out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"\nJSON={args.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
