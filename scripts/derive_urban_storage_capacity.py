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
    args = ap.parse_args()

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

    caps, lens = {}, {}
    n_int = n_bnd = 0
    for l, sc in owner.items():
        g = geo[l]
        up = up_owner.get(l)
        if up is not None:
            name = f"SC{int(up)}_to_SC{int(sc)}"   # 상류 -> 나 방향이 곧 내 approach 다
            n_int += 1
        else:
            name = f"SC{int(sc)}_{leg.get(l, '?')}_out"   # 상류 SC 가 없으면 유입 경계
            n_bnd += 1
        caps[name] = caps.get(name, 0.0) + g["len_m"] / 1000.0 * g["lanes"] * jam
        lens[name] = lens.get(name, 0.0) + g["len_m"]
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
            "note": "링크는 assign_links_to_players.py 의 분할 귀속을 쓴다(중복 없음).",
        }
        os.makedirs(os.path.dirname(os.path.abspath(args.json_out)) or ".", exist_ok=True)
        json.dump(payload, open(args.json_out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"\nJSON={args.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
