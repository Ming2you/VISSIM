#!/usr/bin/env python3
"""고속도로 파라미터를 **다단계 목적**으로 훑는다.

## 왜 다단계인가

MPC 는 모형을 H 스텝 굴려 쓴다. 그런데 지금 파라미터는 짧은 지평에 맞춰져 있고, 관측하면
300 초 이후 절벽이 있다. 지평을 450 초로 늘리려면 그 구간에서 좋은 파라미터를 찾아야 하므로
목적함수를 스텝 1~8(=480 초)의 중앙 APE 로 둔다. 1스텝 적합과 다른 답이 나올 수 있다.

## 왜 freeway_capacity_veh_h 도 넣는가

속도 파라미터(rho_crit / nu / tau / kappa / a_m)는 속도만 정한다. 그런데 실측하면 모형이
질량을 쌓는다 - 600 초에 관측 대비 +665 ~ +991 대다. 터미널 배출이
    terminal_out = min(mainline_sending, q_cap * lanes_now / freeway_lanes)
로 걸리므로(metanet.py:526-527) `freeway_capacity_veh_h` 는 **하류 배출을 직접 캡한다**.
질량 수지에 손댈 수 있는 유일한 파라미터라 함께 훑는다.

## 방법

현재 값에서 좌표별로 훑는다(joint grid 는 6^5 라 불가). 각 점마다
audit_rollout_prediction_accuracy.py 를 별도 프로세스로 돌려 격리한다. 셀 수를 줄여 속도를
얻고, 우승자는 나중에 전체 셀로 재확인해야 한다 - 그 재확인 전에는 결론이 아니다.
"""
from __future__ import annotations
import argparse, json, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = "real_world_modi_pstack_distributed_pedovrx_20260814.json"

GRID = {
    "rho_crit":               [18.0, 20.401, 24.0, 27.0, 30.0, 34.0, 38.0],
    "metanet_nu_km2_h":       [25.0, 35.0, 45.0, 55.0, 65.0, 80.0],
    "metanet_tau_h":          [0.0025, 0.005, 0.0075, 0.010, 0.015],
    "metanet_kappa_veh_km_lane": [10.0, 20.0, 30.0, 40.0, 60.0],
    "metanet_a_m":            [1.2, 1.5, 1.867, 2.2, 2.6],
    "freeway_capacity_veh_h": [5000.0, 6000.0, 6900.0, 8000.0, 9500.0, 11000.0],
}


def objective(path: Path, max_step: int) -> dict[str, float]:
    """스텝 1..max_step 의 중앙 APE. 고속도로 속도·대수를 따로, 그리고 합산도 낸다."""
    d = json.loads(path.read_text(encoding="utf-8"))
    by = d["raw"]["all"]["median_ape_by_step"]
    ks = [k for k in by if int(k) <= max_step]
    spd = [by[k]["freeway_mean_speed_kph"] for k in ks]
    cnt = [by[k]["freeway_total_veh"] for k in ks]
    urb = [by[k]["urban_total_veh"] for k in ks]
    m = lambda v: sum(v) / len(v)
    return {"freeway_speed": m(spd), "freeway_count": m(cnt), "urban": m(urb),
            "score": m(spd) + m(cnt)}


def run_point(name: str, value: float, cells: int, steps: int, max_step: int,
              out_dir: Path) -> dict | None:
    cfg = {"extends": BASE,
           "name": f"sweep_{name}_{value}",
           "description": "freeway parameter sweep probe (offline accuracy only)",
           "config_overrides": {"network": {name: value}}}
    with tempfile.NamedTemporaryFile("w", suffix=".json", dir=str(REPO / "evaluation" / "configs"),
                                     delete=False, encoding="utf-8") as fh:
        json.dump(cfg, fh, ensure_ascii=False)
        tmp = Path(fh.name)
    out = out_dir / f"acc_{name}_{value}.json"
    try:
        proc = subprocess.run(
            [sys.executable, str(REPO / "scripts" / "audit_rollout_prediction_accuracy.py"),
             "--run-dir", str(REPO / "evaluation" / "runs" / "n5_parent_20260814"),
             "--horizon-steps", str(steps), "--limit-cells", str(cells),
             "--tuning", str(tmp), "--out", str(out)],
            capture_output=True, text=True, timeout=3600)
        if proc.returncode not in (0, 2) or not out.is_file():
            print(f"    실패 {name}={value}: rc={proc.returncode} {proc.stderr[-160:]}")
            return None
        return objective(out, max_step)
    except subprocess.TimeoutExpired:
        print(f"    시간초과 {name}={value}")
        return None
    finally:
        tmp.unlink(missing_ok=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--cells", type=int, default=3)
    ap.add_argument("--steps", type=int, default=10)
    ap.add_argument("--max-step", type=int, default=8, help="목적함수에 넣을 최대 스텝(8=480초)")
    ap.add_argument("--only", default="", help="쉼표로 파라미터 이름 제한")
    args = ap.parse_args()

    out_dir = args.out.parent / "sweep_runs"
    out_dir.mkdir(parents=True, exist_ok=True)
    keep = [k.strip() for k in args.only.split(",") if k.strip()] or list(GRID)

    print(f"목적 = 스텝 1..{args.max_step} 의 (고속도로 속도 APE + 대수 APE) 평균")
    print(f"셀 {args.cells}개, 지평 {args.steps} 스텝\n")
    results: dict[str, list] = {}
    for name in keep:
        print(f"=== {name} ===")
        rows = []
        for value in GRID[name]:
            got = run_point(name, value, args.cells, args.steps, args.max_step, out_dir)
            if got:
                rows.append({"value": value, **got})
                print(f"  {value:>10} 속도 {got['freeway_speed']:6.1f}%  대수 {got['freeway_count']:6.1f}%"
                      f"  도시부 {got['urban']:5.1f}%  score {got['score']:6.1f}")
        if rows:
            best = min(rows, key=lambda r: r["score"])
            print(f"  -> 최적 {name} = {best['value']}  score {best['score']:.1f}")
            results[name] = rows
    args.out.write_text(json.dumps(
        {"schema_version": "freeway-param-sweep-v1",
         "objective": f"mean over steps 1..{args.max_step} of (freeway speed APE + freeway count APE)",
         "cells": args.cells, "horizon_steps": args.steps,
         "note": "좌표별 스윕이라 상호작용은 못 본다. 우승자는 전체 9셀로 재확인해야 한다.",
         "results": results}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"\n기록: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
