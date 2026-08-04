# 플랜트 자체의 시드간 재현성(잡음 하한)을 G5 지표 공간에서 잰다.
#
# 원리. 시드 A 의 관측 궤적을 시드 B 에 대한 '완벽한 예측'으로 놓고 G5 지표를 계산하면,
# 그것이 어떤 모델도 넘을 수 없는 하한이다. 이 하한이 계약 임계보다 크면
# 그 게이트는 모델 작업으로 통과할 수 없다.
#
# 임계 정의(harness/gates/g5_metrics.py:287)
#   threshold = max(5.0, 0.10 * mean_observed_count)
# 이므로 셀/링크 임계비 8 은 링크 대수가 셀 대수의 8 배(링크=8세그먼트)인 데서 온다.
#
# 사용법:
#   python measure_plant_noise_floor.py <bottleneck_segments_A.csv> <B.csv> [C.csv ...] [--from-sec 2700]

from __future__ import annotations

import argparse
import csv
import statistics as st
from itertools import combinations
from pathlib import Path

FLOOR_VEH = 5.0
RATIO = 0.10


def load(path: Path, from_sec: float):
    """(sim_sec, model_link, segment_index) -> (count, speed, lanes)"""
    cells = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            try:
                t = float(row["sim_sec"])
            except (KeyError, ValueError):
                continue
            if t < from_sec:
                continue
            key = (t, row["model_link"], int(row["segment_index"]))
            cells[key] = (float(row["count"]), float(row["mean_speed_kph"]))
    return cells


def link_totals(cells):
    """(sim_sec, model_link) -> (count_sum, count_weighted_speed)"""
    acc = {}
    for (t, ml, _si), (c, v) in cells.items():
        a = acc.setdefault((t, ml), [0.0, 0.0])
        a[0] += c
        a[1] += c * v
    return {k: (a[0], (a[1] / a[0] if a[0] > 0 else 0.0)) for k, a in acc.items()}


def metrics(pred, obs):
    """pred/obs 는 key -> (count, speed). 공통 key 만 쓴다."""
    keys = sorted(set(pred) & set(obs))
    if not keys:
        return None
    cnt_ae = [abs(pred[k][0] - obs[k][0]) for k in keys]
    mean_obs = st.mean([obs[k][0] for k in keys])
    spd = [(pred[k][1], obs[k][1]) for k in keys if obs[k][1] > 1.0]
    mape = st.mean([abs(p - o) / o for p, o in spd]) if spd else float("nan")
    return dict(n=len(keys), mae=st.mean(cnt_ae), mean_obs=mean_obs,
                thr=max(FLOOR_VEH, RATIO * mean_obs), mape=mape)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csvs", nargs="+", type=Path)
    ap.add_argument("--from-sec", type=float, default=2700.0)
    args = ap.parse_args()

    runs = {}
    for p in args.csvs:
        name = p.stem.split("seed")[-1] or p.stem
        runs[name] = load(p, args.from_sec)
        print(f"seed {name:<6} {p.name}   셀 표본 {len(runs[name])}")
    if len(runs) < 2:
        print("시드가 2 개 미만이라 하한을 잴 수 없다.")
        return

    print(f"\n{'='*84}\n시드쌍별 '한 시드로 다른 시드를 예측' 오차 = 플랜트 잡음 하한\n")
    print(f"{'A -> B':<16}{'셀 MAE':>10}{'셀 임계':>10}{'판정':>7}"
          f"{'셀 MAPE':>11}{'링크 MAE':>11}{'링크 임계':>11}{'판정':>7}")
    print("-" * 84)
    cell_maes, cell_mapes, link_maes, cell_thrs, link_thrs = [], [], [], [], []
    for a, b in combinations(sorted(runs), 2):
        for p, o in ((a, b), (b, a)):
            mc = metrics(runs[p], runs[o])
            ml = metrics(link_totals(runs[p]), link_totals(runs[o]))
            if not mc or not ml:
                continue
            okc = "PASS" if mc["mae"] <= mc["thr"] else "FAIL"
            okl = "PASS" if ml["mae"] <= ml["thr"] else "FAIL"
            print(f"{p+' -> '+o:<16}{mc['mae']:>10.3f}{mc['thr']:>10.3f}{okc:>7}"
                  f"{mc['mape']:>11.4f}{ml['mae']:>11.3f}{ml['thr']:>11.3f}{okl:>7}")
            cell_maes.append(mc["mae"]); cell_mapes.append(mc["mape"])
            link_maes.append(ml["mae"]); cell_thrs.append(mc["thr"]); link_thrs.append(ml["thr"])

    if not cell_maes:
        return
    print(f"\n{'='*84}\n=== 잡음 하한 요약 ({len(cell_maes)} 쌍)")
    def line(nm, vals, thr):
        m, sd = st.mean(vals), (st.pstdev(vals) if len(vals) > 1 else 0.0)
        t = st.mean(thr) if thr else float("nan")
        print(f"  {nm:<22} 평균 {m:8.3f}  표준편차 {sd:6.3f}  범위 {min(vals):7.3f}~{max(vals):7.3f}"
              + (f"   임계 {t:7.3f}   비 {m/t:5.2f}x" if thr else ""))
    line("셀 대수 MAE", cell_maes, cell_thrs)
    line("링크 대수 MAE", link_maes, link_thrs)
    line("셀 속도 MAPE", cell_mapes, None)

    ct, lt = st.mean(cell_thrs), st.mean(link_thrs)
    print(f"\n판정")
    print(f"  셀 대수  : 하한 {st.mean(cell_maes):.3f} vs 임계 {ct:.3f}"
          f"  -> {'하한이 임계를 넘는다. 모델 작업으로 통과 불가.' if st.mean(cell_maes) > ct else '여유 있음.'}")
    print(f"  링크 대수: 하한 {st.mean(link_maes):.3f} vs 임계 {lt:.3f}"
          f"  -> {'하한이 임계를 넘는다.' if st.mean(link_maes) > lt else '여유 있음.'}")


if __name__ == "__main__":
    main()
