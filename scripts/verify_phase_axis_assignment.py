# leg 의 phase 축 배정이 **실측 방위각**과 맞는지 검증한다.
#
# 왜 필요한가.
#   grid_topology.NS_AXIS 는 어느 leg 방위를 남북 phase(p1)에 넣을지 정하는 상수다.
#   2026-08-04 에 8방위로 확장하며 {"N","S","NE","SW"} 로 넣었는데, NE/SW 를 45° 로
#   가정한 것이 틀렸다. 개포동 격자는 좌표축에서 15~37° 돌아가 있어 실측 축각이
#   NE 36.1° / SW 37.2°(동서축) / NW 122.2° / SE 121.6°(남북축) 다. 대각 leg 76개 중
#   현행 배정이 맞는 것이 0개였다. movement 287개(20.4%)의 phase 가 뒤집힌다.
#
#   모델 테스트는 이걸 못 잡는다 — default.yaml 격자가 4방위라 대각 원소를 조회조차
#   하지 않는다(대각 문자열 0건). 그래서 검증을 네트워크 기하가 있는 이쪽에 둔다.
#
# 기준.
#   두 교차로 중심을 잇는 벡터의 방위각(mod 180)이 [45,135) 이면 남북축, 아니면 동서축.
#   이건 grid_topology 주석이 이미 선언한 기준이며, 여기서는 그 기준을 실제 좌표에
#   적용해 코드의 집합과 대조한다.
import argparse
import csv
import io
import json
import math
import os
import sys
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_ROLES = os.path.join(REPO, "evaluation", "real_world_modi_inventory",
                             "signal_controller_roles.csv")
DEFAULT_ADJ = os.path.join(REPO, "outputs", "intersection_adjacency8_20260804.json")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--roles", default=DEFAULT_ROLES)
    ap.add_argument("--adjacency", default=DEFAULT_ADJ)
    ap.add_argument("--min-agree", type=float, default=0.80,
                    help="이 비율 미만이면 FAIL")
    args = ap.parse_args()

    sys.path.insert(0, os.path.join(os.path.dirname(REPO), "NumSim-mine"))
    from src.models.grid_topology import NS_AXIS

    centroid = {}
    with open(args.roles, newline="", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            if str(r.get("active", "")).lower() != "true":
                continue
            try:
                xy = json.loads(r.get("centroid_xy") or "[]")
            except Exception:
                continue
            if len(xy) == 2:
                centroid[int(r["no"])] = (float(xy[0]), float(xy[1]))

    legs = json.load(open(args.adjacency, encoding="utf-8"))["legs"]
    angles = defaultdict(list)
    for sc_txt, legmap in legs.items():
        a = centroid.get(int(sc_txt))
        if a is None:
            continue
        for leg_key, nb in legmap.items():
            b = centroid.get(int(nb))
            if b is None:
                continue
            angles[str(leg_key).split("_", 1)[0]].append(
                math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180.0)

    print(f"NS_AXIS = {sorted(NS_AXIS)}")
    print(f"{'leg':<5}{'n':>4}{'평균축각':>10}{'실측축':>8}{'코드축':>8}   판정")
    agree = total = 0
    bad = []
    for d in ("N", "NE", "E", "SE", "S", "SW", "W", "NW"):
        v = angles.get(d) or []
        if not v:
            continue
        mean = sum(v) / len(v)
        true_ns = 45.0 <= mean < 135.0
        code_ns = d in NS_AXIS
        ok = true_ns == code_ns
        total += len(v)
        agree += len(v) if ok else 0
        if not ok:
            bad.append((d, mean, len(v)))
        print(f"{d:<5}{len(v):>4}{mean:>10.1f}{'남북' if true_ns else '동서':>8}"
              f"{'남북' if code_ns else '동서':>8}   {'OK' if ok else '**불일치**'}")

    rate = agree / total if total else 0.0
    print(f"\n일치 {agree}/{total} = {100*rate:.1f}%")
    if bad:
        print("불일치 방위 — NS_AXIS 를 고쳐야 한다:")
        for d, mean, n in bad:
            print(f"   {d}: 실측 {mean:.1f}° 인데 코드는 반대 축 ({n}개 leg)")
    if rate < args.min_agree:
        print(f"RESULT FAIL  ({100*rate:.1f}% < {100*args.min_agree:.0f}%)")
        return 1
    print("RESULT PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
