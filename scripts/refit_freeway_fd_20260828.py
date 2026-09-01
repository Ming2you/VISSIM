# -*- coding: utf-8 -*-
"""freeway FD 를 실측에서 다시 적합하고, canon_fdfit 이 주장하는 값을 재현 검증한다.

왜 (2026-08-28).

`canon_fdfit_20260827.json` 이 `_canonical.arm.fit` 에 적합 결과를 적어 놓았다 —
113.0 / 21.70 / 2.280 / 6325.8, RMSE 11.595, 자료 "무제어 네이티브 4런(수요 1.0/1.2/1.4배),
세그먼트x스텝 1984점, sim_sec>=900". 그런데 **그 적합의 산출물이 저장소에 없다.** outputs/ 의
FD 아티팩트는 전부 2026-08-01~24 세대다. 숫자가 config 주석에만 있고 재현 경로가 없다.

이 값은 지금 신기록 팔(canon_fdfit2 −158.5)의 단일변수이므로 근거가 주석 한 줄이면 안 된다.

무엇을 하는가.

    밀도  rho = count / (length_km x lanes)     [veh/km/lane]
    속도  v   = speed_sum / count               [kph]
    모형  V(rho) = v_free * exp(-(1/a) * (rho/rho_crit)^a)
    용량  q_cap = rho_crit * v_free * exp(-1/a) * lanes      (파생값, 자유 파라미터 아님)

무제어 런의 상태 JSON `freeway_segments` 에서 뽑는다. 수요 1.0/1.2/1.4 를 함께 쓰는 이유는
FD 가 수요의 함수가 아니라 도로의 성질이고, 혼잡부 점은 높은 수요에서만 나오기 때문이다.

산출: outputs/freeway_fd_refit_20260828.{json,csv}
"""
import argparse
import csv
import io
import json
import math
import sys
from pathlib import Path

import numpy as np

R = Path(__file__).resolve().parent.parent

DEMAND = {
    "nocontrolstep_20260826": 1.0,
    "nc_fw12_ramp1_20260827": 1.2,
    "nc_fw12_ramp2_20260827": 1.2,
    "nc_fw14_ramp1_20260827": 1.4,
    "nc_fw14_ramp2_20260827": 1.4,
    # 2026-08-28 본선 수요 sweep. 본선 진입 둘만 곱한 망이라 램프는 원본이다
    # (fw12/fw14 는 램프 relFlow 도 같이 바꿨다 — 두 변수).
    "ncsweep_x16_20260828": 1.6,
    "ncsweep_x17_20260828": 1.7,
    "ncsweep_x18_20260828": 1.8,
    "ncsweep_x19_20260828": 1.9,
    "ncsweep_x20_20260828": 2.0,
    "ncsweep_x21_20260828": 2.1,
    "ncsweep_x22_20260828": 2.2,
    "ncsweep_x23_20260828": 2.3,
    "ncsweep_x24_20260828": 2.4,
}


def collect(runs, min_sim_sec):
    rows = []
    for run in runs:
        for f in sorted((R / "evaluation/runs" / run).glob("decisions_*/state_*.json")):
            sj = json.loads(f.read_text(encoding="utf-8"))
            t = float(sj.get("sim_sec") or 0.0)
            if t < min_sim_sec:
                continue
            for link, arr in (sj.get("freeway_segments") or {}).items():
                for i, s in enumerate(arr):
                    c = float(s.get("count") or 0.0)
                    L = float(s.get("length_km") or 0.0)
                    n = float(s.get("lanes") or 0.0)
                    ss = float(s.get("speed_sum") or 0.0)
                    if c <= 0 or L <= 0 or n <= 0:
                        continue
                    rows.append({"run": run, "demand": DEMAND.get(run, 1.0), "sim_sec": t,
                                 "link": link, "segment": i,
                                 "density_veh_km_lane": c / (L * n),
                                 "speed_kph": ss / c, "count": c})
    return rows


def fit(rho, v):
    """V(rho)=v_free*exp(-(1/a)(rho/rho_crit)^a) 최소자승. 격자 + 국소 정련."""
    best = None
    for vf in np.arange(95.0, 126.0, 1.0):
        for rc in np.arange(12.0, 45.1, 0.5):
            for a in np.arange(1.2, 4.01, 0.1):
                pred = vf * np.exp(-(1.0 / a) * (rho / rc) ** a)
                r = float(np.sqrt(np.mean((v - pred) ** 2)))
                if best is None or r < best[0]:
                    best = (r, vf, rc, a)
    _r, vf, rc, a = best
    for _ in range(6):                      # 격자를 좁혀 정련
        step = (0.5, 0.25, 0.05)
        cand = best
        for dvf in (-step[0], 0.0, step[0]):
            for drc in (-step[1], 0.0, step[1]):
                for da in (-step[2], 0.0, step[2]):
                    vf2, rc2, a2 = vf + dvf, rc + drc, a + da
                    if rc2 <= 0 or a2 <= 0.2:
                        continue
                    pred = vf2 * np.exp(-(1.0 / a2) * (rho / rc2) ** a2)
                    r = float(np.sqrt(np.mean((v - pred) ** 2)))
                    if r < cand[0]:
                        cand = (r, vf2, rc2, a2)
        if cand == best:
            break
        best = cand
        _r, vf, rc, a = best
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="*", default=list(DEMAND))
    ap.add_argument("--min-sim-sec", type=float, default=900.0)
    ap.add_argument("--lanes", type=float, default=4.0)
    ap.add_argument("--bootstrap", type=int, default=200)
    ap.add_argument("--out", default="outputs/freeway_fd_refit_20260828")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    rows = collect(args.runs, args.min_sim_sec)
    if not rows:
        print("!! 점이 없다")
        return 1
    rho = np.array([r["density_veh_km_lane"] for r in rows])
    v = np.array([r["speed_kph"] for r in rows])
    print("런 %d개 · 점 %d개 · 밀도 %.1f ~ %.1f · sim_sec >= %.0f"
          % (len(set(r["run"] for r in rows)), len(rows), rho.min(), rho.max(), args.min_sim_sec))
    hi = int((rho >= 25).sum())
    print("   밀도 25 이상 %d점 (%.1f%%)  <- 혼잡부 표본" % (hi, 100.0 * hi / len(rho)))

    rmse, vf, rc, a = fit(rho, v)
    cap = rc * vf * math.exp(-1.0 / a) * args.lanes
    print()
    print("적합  v_free %.1f · rho_crit %.2f · a %.3f · RMSE %.3f kph · 함의용량 %.1f veh/h"
          % (vf, rc, a, rmse, cap))
    print("주장  v_free 113.0 · rho_crit 21.70 · a 2.280 · RMSE 11.595 · 용량 6325.8   (canon_fdfit_20260827)")
    print("현행  v_free 100.0 · rho_crit 33.50 · a 1.867 · 저장용량 4000  (parameters.json)")

    # 현행/주장값의 RMSE 도 같은 자료로 낸다
    def rmse_of(vf_, rc_, a_):
        return float(np.sqrt(np.mean((v - vf_ * np.exp(-(1.0 / a_) * (rho / rc_) ** a_)) ** 2)))
    print()
    print("같은 자료에서의 RMSE  적합 %.3f · 주장(113.0/21.7/2.28) %.3f · 현행(100/33.5/1.867) %.3f"
          % (rmse, rmse_of(113.0, 21.7, 2.28), rmse_of(100.0, 33.5, 1.867)))

    rng = np.random.default_rng(13)
    boots = []
    for _ in range(max(0, args.bootstrap)):
        idx = rng.integers(0, len(rho), len(rho))
        boots.append(fit(rho[idx], v[idx])[1:])
    ci = {}
    if boots:
        B = np.array(boots)
        for i, nm in enumerate(("v_free", "rho_crit", "metanet_a_m")):
            ci[nm] = [float(np.percentile(B[:, i], 5)), float(np.percentile(B[:, i], 95))]
        caps = B[:, 1] * B[:, 0] * np.exp(-1.0 / B[:, 2]) * args.lanes
        ci["capacity"] = [float(np.percentile(caps, 5)), float(np.percentile(caps, 95))]
        print()
        print("부트스트랩 %d회 90%% CI" % len(boots))
        for k, vv in ci.items():
            print("   %-14s %.2f ~ %.2f" % (k, vv[0], vv[1]))

    by_run = {}
    for r in rows:
        by_run.setdefault(r["run"], []).append(r["density_veh_km_lane"])
    print()
    print("%-26s %6s %8s %8s %8s" % ("런", "수요", "점수", "밀도중앙", "밀도최대"))
    for run in args.runs:
        d = by_run.get(run) or []
        if d:
            print("%-26s %6.1f %8d %8.2f %8.2f"
                  % (run, DEMAND.get(run, 1.0), len(d), float(np.median(d)), max(d)))

    doc = {
        "schema_version": "freeway-fd-refit/1",
        "generated": "2026-08-28",
        "why": "canon_fdfit_20260827 의 FD 값이 config 주석에만 있고 재현 가능한 산출물이 없었다. "
               "그 값이 지금 신기록 팔의 단일변수라 근거를 복원한다.",
        "model": "V(rho)=v_free*exp(-(1/a)*(rho/rho_crit)^a); capacity=rho_crit*v_free*exp(-1/a)*lanes",
        "runs": {r: DEMAND.get(r, 1.0) for r in args.runs},
        "min_sim_sec": args.min_sim_sec,
        "point_count": len(rows),
        "high_density_points": hi,
        "fit": {"v_free": vf, "rho_crit": rc, "metanet_a_m": a,
                "freeway_capacity_veh_h": cap, "rmse_kph": rmse},
        "claimed_canon_fdfit": {"v_free": 113.0, "rho_crit": 21.7, "metanet_a_m": 2.28,
                                "freeway_capacity_veh_h": 6325.8, "rmse_kph": 11.595},
        "rmse_on_this_data": {"refit": rmse, "claimed": rmse_of(113.0, 21.7, 2.28),
                              "current_parameters": rmse_of(100.0, 33.5, 1.867)},
        "bootstrap_ci_90": ci,
        "caveat": "혼잡부(밀도 25 이상) 표본이 %d점(%.1f%%)뿐이다. 정상상태 FD 만 맞춘 것이고 "
                  "동역학 예측력은 별개다 — 판정 기준은 폐루프 TTT 다." % (hi, 100.0 * hi / len(rho)),
    }
    (R / (args.out + ".json")).write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    with io.open(R / (args.out + ".csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print()
    print("-> %s.json / .csv" % args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
