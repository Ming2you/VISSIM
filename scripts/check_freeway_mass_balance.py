# freeway 본선 체인의 질량보존을 유량 연속성으로 검정한다.
#
# 원리. 정상상태에서 세그먼트 유량은 q = rho * lanes * v 다.
# 램프가 없는 인접 세그먼트 사이에서 q 가 유지되어야 하고, 유지되지 않으면
# 그 경계에서 차량이 생기거나 사라진다는 뜻이다.
# 실제로 수리 전 개포동 네트워크는 FW_E S5(= link 2 의 끝, 체인 7426 m)에서
# 라우팅 결함으로 차량이 삭제되어 약 223 veh/h 가 사라지고 있었다.
#
# 사용법: python check_freeway_mass_balance.py <bottleneck_segments.csv> [--from-sec 900] [--label 이름]
#         여러 개를 주면 나란히 비교한다.

from __future__ import annotations

import argparse
import csv
import statistics as st
from collections import defaultdict
from pathlib import Path


def load(path: Path, from_sec: float):
    """(model_link, segment_index) -> 평가구간 평균 (density, speed, lanes, count)"""
    acc = defaultdict(lambda: {"rho": [], "v": [], "lanes": None, "cnt": []})
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            try:
                t = float(row["sim_sec"])
            except (KeyError, ValueError):
                continue
            if t < from_sec:
                continue
            key = (row["model_link"], int(row["segment_index"]))
            a = acc[key]
            a["rho"].append(float(row["density_veh_km_lane"]))
            a["v"].append(float(row["mean_speed_kph"]))
            a["cnt"].append(float(row["count"]))
            a["lanes"] = int(row["lanes"])
    out = {}
    for key, a in acc.items():
        if not a["rho"]:
            continue
        # 유량은 표본마다 구해 평균낸다 (평균의 곱이 아니라 곱의 평균)
        q = [r * a["lanes"] * v for r, v in zip(a["rho"], a["v"])]
        out[key] = dict(rho=st.mean(a["rho"]), v=st.mean(a["v"]), lanes=a["lanes"],
                        cnt=st.mean(a["cnt"]), q=st.mean(q), n=len(q))
    return out


def report(datasets):
    models = sorted({m for d in datasets.values() for (m, _) in d})
    for model in models:
        print(f"\n{'=' * 78}\n{model} — 세그먼트별 유량 q = rho x lanes x v  [veh/h]\n")
        idxs = sorted({i for d in datasets.values() for (m, i) in d if m == model})
        head = f"{'seg':>4}" + "".join(f"{lbl:>26}" for lbl in datasets)
        print(head)
        print("-" * len(head))
        prev = {lbl: None for lbl in datasets}
        for i in idxs:
            cells = []
            for lbl, d in datasets.items():
                rec = d.get((model, i))
                if rec is None:
                    cells.append(f"{'-':>26}")
                    continue
                dq = "" if prev[lbl] is None else f" {rec['q'] - prev[lbl]:+7.0f}"
                prev[lbl] = rec["q"]
                cells.append(f"{rec['q']:>10.0f}{dq:>9}  ρ{rec['rho']:>4.1f}")
            print(f"{i:>4}" + "".join(cells))

        print(f"\n{'seg':>4}" + "".join(f"{'평균속도(km/h)':>26}" for _ in datasets))
        for i in idxs:
            cells = []
            for lbl, d in datasets.items():
                rec = d.get((model, i))
                cells.append(f"{'-':>26}" if rec is None else f"{rec['v']:>26.1f}")
            print(f"{i:>4}" + "".join(cells))

        # 최대 하락 구간
        print()
        for lbl, d in datasets.items():
            seq = [(i, d[(model, i)]["q"]) for i in idxs if (model, i) in d]
            if len(seq) < 2:
                continue
            drops = [(seq[k][0], seq[k + 1][0], seq[k + 1][1] - seq[k][1]) for k in range(len(seq) - 1)]
            worst = min(drops, key=lambda x: x[2])
            tot = seq[-1][1] - seq[0][1]
            print(f"  [{lbl}] 최대 유량 하락  S{worst[0]}→S{worst[1]}: {worst[2]:+.0f} veh/h"
                  f"   |  전 구간 순변화 S{seq[0][0]}→S{seq[-1][0]}: {tot:+.0f} veh/h")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csvs", nargs="+")
    ap.add_argument("--from-sec", type=float, default=900.0)
    ap.add_argument("--labels", default="")
    args = ap.parse_args()

    labels = [s.strip() for s in args.labels.split(",")] if args.labels else []
    datasets = {}
    for k, p in enumerate(args.csvs):
        lbl = labels[k] if k < len(labels) else Path(p).stem[:24]
        datasets[lbl] = load(Path(p), args.from_sec)
        n = sum(v["n"] for v in datasets[lbl].values())
        print(f"{lbl:<26} {p}   표본 {n}")
    report(datasets)


if __name__ == "__main__":
    main()
