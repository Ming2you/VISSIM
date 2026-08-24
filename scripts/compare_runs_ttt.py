"""런들의 TTT 를 한 표로 비교한다. 짝지은 비교와 시드 분산을 함께 보여준다.

TTT = `state_<run>.csv` 의 `total_vehicles` 사다리꼴 적분 [veh·h].

**두 가지를 반드시 지킨다.**

1. **완주만 센다.** 적분 상한이 짧으면 TTT 가 그만큼 작게 나온다 — 미완주 런을 읽어
   무제어 시드 15 를 4645 로 오독한 전례가 있다(완주값 4763.8).
2. **표본 간격을 표시한다.** 2026-08-24 부터 기본이 30초다(종전 5초). 리샘플 오차는
   실측 −0.02~0.04% 로 작지만, 간격이 다른 런을 맞댈 때는 그 사실이 보여야 한다.

시드 σ(무제어 5시드 50.7 veh·h = 1.06%)는 **수준**의 분산이지 짝지은 차이의 분산이
아니다. 같은 시드끼리의 비교(공통 난수)는 그보다 훨씬 정밀하다 — 이 표는 그 둘을
섞지 않도록 시드를 같이 찍는다.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import pathlib
import statistics
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load(run: str):
    path = ROOT / "evaluation" / "runs" / run / f"state_{run}.csv"
    if not path.is_file():
        return None
    series = {}
    with io.open(path, encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            try:
                series[float(row["sim_sec"])] = float(row["total_vehicles"])
            except (KeyError, TypeError, ValueError):
                continue
    return series or None


def ttt(series, end_min: float):
    times = sorted(series)
    if len(times) < 5 or max(times) < end_min:
        return None
    total = 0.0
    for i in range(len(times) - 1):
        total += (series[times[i]] + series[times[i + 1]]) / 2.0 * ((times[i + 1] - times[i]) / 3600.0)
    return total, len(times), times[1] - times[0], max(times)


def seed_of(run: str):
    path = ROOT / "evaluation" / "runs" / run / f"run_provenance_{run}.json"
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("seed")
    except (OSError, ValueError):
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="*", help="런 이름들. 비우면 evaluation/runs 전체")
    ap.add_argument("--base", default="nocontrol_s13_20260824", help="기준선 런")
    ap.add_argument("--end-min", type=float, default=5395.0, help="이 시각까지 있어야 완주로 본다")
    ap.add_argument("--seed-group", default="nocontrol_s", help="시드 분산을 낼 런 이름 접두어")
    args = ap.parse_args()

    runs = args.runs
    if not runs:
        root = ROOT / "evaluation" / "runs"
        runs = sorted(p.name for p in root.iterdir() if p.is_dir()) if root.is_dir() else []

    rows, skipped = [], []
    for run in runs:
        series = load(run)
        if series is None:
            skipped.append((run, "state CSV 없음"))
            continue
        got = ttt(series, args.end_min)
        if got is None:
            times = sorted(series)
            skipped.append((run, f"미완주 (끝 {max(times) if times else 0:.0f}s)"))
            continue
        value, n, step, end = got
        rows.append({"run": run, "ttt": value, "n": n, "step": step, "end": end, "seed": seed_of(run)})

    base = next((r for r in rows if r["run"] == args.base), None)
    rows.sort(key=lambda r: r["ttt"])

    print(f"{'런':34s} {'TTT':>9s} {'vs 기준':>10s} {'시드':>5s} {'점':>6s} {'간격':>5s}")
    for r in rows:
        delta = f"{r['ttt'] - base['ttt']:+9.1f}" if base else "        -"
        pct = f"({100 * (r['ttt'] - base['ttt']) / base['ttt']:+.2f}%)" if base else ""
        mark = "  <- 기준" if base and r["run"] == base["run"] else ""
        print(f"{r['run']:34s} {r['ttt']:9.1f} {delta} {pct:>9s} "
              f"{str(r['seed']):>5s} {r['n']:6d} {r['step']:5.0f}{mark}")

    group = [r for r in rows if r["run"].startswith(args.seed_group)]
    if len(group) >= 3:
        vals = [r["ttt"] for r in group]
        mean, sd = statistics.mean(vals), statistics.stdev(vals)
        print(f"\n시드 분산({args.seed_group}*, n={len(group)}): 평균 {mean:.1f} · "
              f"σ {sd:.1f} ({100 * sd / mean:.2f}%) · 범위 [{min(vals):.1f}, {max(vals):.1f}]")
        print("  주의: 이 σ 는 **수준**의 분산이다. 같은 시드끼리의 짝지은 차이는 "
              "공통 난수 덕에 이보다 훨씬 정밀하다 — 두 값을 섞어 판정하지 마라.")

    if skipped:
        print(f"\n제외 {len(skipped)}개:")
        for run, why in skipped[:12]:
            print(f"  {run:34s} {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
