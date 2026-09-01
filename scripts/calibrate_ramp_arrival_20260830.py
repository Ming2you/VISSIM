# -*- coding: utf-8 -*-
"""램프별 `queue_drain_horizon_sec` 를 실측에서 뽑고, 그 모형이 성립하는지 검정한다.

왜 (2026-08-30).

어댑터의 `local_ramp_arrival_forecast` 는 램프 점유[veh]를 유입률[veh/h]로 이렇게 바꾼다.

    arrival_vph = 점유 * 3600 / queue_drain_horizon_sec        (그 뒤 cap 으로 클립)

지금 config 는 `queue_drain_horizon_sec = 120.0` **스칼라 하나**를 램프 넷에 다 쓴다.
실측하면 합이 1200 vph 인데 플랜트는 3457 vph 를 보낸다 — **35%**. 어댑터 주석
(vissim_stackelberg_adapter.py:5960)이 이 증상을 이미 적어놨다:

    "이 때문에 모델 ramp_arrival 이 플랜트의 3.5분의 1로 나왔고, 모델 세계에서만
     미터가 수요를 구속하지 않아 dTTT/d(meter) 가 정의상 0 이 됐다(G6 램프 축 붕괴 원인)."

그리고 고칠 자리도 이미 있다 — 같은 블록이 `queue_drain_horizon_sec_by_ramp` 를 읽는다.
2026-08-04 에 그 필드를 만들면서 "실측 역산값이 R_F_E 25.7 s ~ R_F_W 116.6 s" 라고
적었는데 **값을 config 에 넣지 않았다.**

무엇을 하는가.

    처리량  q[veh/h]  = .fzp 에서 그 램프 링크를 지난 **고유 차량 수** / 창길이
                        (점유 스냅샷이 아니라 직접 계수 — 이것이 기준값이다)
    점유    N[veh]    = 상태 JSON 의 link_counts 합 (어댑터가 쓰는 바로 그 채널)
    통과시간 T[s]     = N * 3600 / q                    <- 구하려는 값

**핵심 검정은 T 가 수요에 대해 상수인가다.** T 는 커넥터 길이/속도에서 나오는 기하량이라
상수여야 한다. 수요에 따라 크게 변하면 선형 모형(점유 x 상수)이 틀린 것이고, 램프별 상수를
넣어도 한 작동점에서만 맞는다 — 그 경우 이 스크립트는 값을 쓰지 말라고 경고한다.

여러 무제어 런(수요 배율만 다름)에서 재므로 그 검정이 가능하다.

산출: outputs/ramp_arrival_calibration_20260830.json
"""
import argparse
import glob
import io
import json
import os
import statistics as st
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent

# detector_local_mapping.json 의 ramp_link_to_queues 와 같은 배정이다.
RAMP_LINKS = {
    "R_D_W": ["10480", "10482"],
    "R_F_W": ["10646", "10644"],
    "R_D_E": ["10490", "10484"],
    "R_F_E": ["10639", "10681"],
}
RUNS = [
    ("nocontrolstep_20260826", 1.0),
    ("ncsweep_x16_20260828", 1.6),
    ("ncsweep_x18_20260828", 1.8),
    ("ncsweep_x20_20260828", 2.0),
    ("ncsweep_x22_20260828", 2.2),
]


def throughput_from_fzp(run, t0, t1):
    """램프 링크를 지난 고유 차량 수 -> veh/h. 없으면 None."""
    files = sorted(glob.glob(str(R / "evaluation/runs" / run / "vissim_eval/*.fzp")))
    if not files:
        return None
    want = {lk: ramp for ramp, lks in RAMP_LINKS.items() for lk in lks}
    seen = {ramp: set() for ramp in RAMP_LINKS}
    with io.open(files[0], encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line or line[0] in "*$":
                continue
            parts = line.split(";", 3)
            if len(parts) < 3:
                continue
            try:
                t = float(parts[0])
            except ValueError:
                continue
            if t < t0 or t > t1:
                continue
            ramp = want.get(parts[2])
            if ramp is not None:
                seen[ramp].add(parts[1])
    hours = (t1 - t0) / 3600.0
    return {ramp: len(v) / hours for ramp, v in seen.items()}


def occupancy_from_states(run, t0):
    """어댑터가 읽는 바로 그 채널(local_observation.link_counts)의 램프 점유 중앙값."""
    acc = {ramp: [] for ramp in RAMP_LINKS}
    for f in sorted(glob.glob(str(R / "evaluation/runs" / run / "decisions_*/state_*.json"))):
        sj = json.loads(Path(f).read_text(encoding="utf-8"))
        if float(sj.get("sim_sec") or 0.0) < t0:
            continue
        lc = (sj.get("local_observation") or {}).get("link_counts") or {}
        for ramp, lks in RAMP_LINKS.items():
            acc[ramp].append(sum(float(lc.get(k, 0) or 0) for k in lks))
    return {ramp: (st.median(v) if v else 0.0) for ramp, v in acc.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--t0", type=float, default=900.0)
    ap.add_argument("--t1", type=float, default=5400.0)
    ap.add_argument("--runs", nargs="*", default=[r for r, _ in RUNS])
    ap.add_argument("--out", default="outputs/ramp_arrival_calibration_20260830.json")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    mult = dict(RUNS)
    per_run = {}
    for run in args.runs:
        q = throughput_from_fzp(run, args.t0, args.t1)
        if q is None:
            print("%-28s (fzp 없음 — 건너뜀)" % run)
            continue
        occ = occupancy_from_states(run, args.t0)
        drain = {r: (occ[r] * 3600.0 / q[r]) if q[r] > 1e-9 else None for r in RAMP_LINKS}
        per_run[run] = {"demand_multiplier": mult.get(run), "throughput_vph": q,
                        "occupancy_veh": occ, "drain_sec": drain}
        print("%-28s x%-4s  처리량합 %6.0f vph"
              % (run, mult.get(run), sum(q.values())))

    if not per_run:
        print("!! 자료가 없다")
        return 1

    print()
    print("%-8s %s" % ("램프", "  ".join("x%-5.1f" % per_run[r]["demand_multiplier"] for r in per_run)))
    print("-- 통과시간 T [s] (수요별) --")
    stable = {}
    for ramp in RAMP_LINKS:
        vals = [per_run[r]["drain_sec"][ramp] for r in per_run]
        good = [v for v in vals if v is not None and v > 0]
        row = "  ".join("%6.1f" % v if v else "     -" for v in vals)
        if len(good) >= 2:
            cv = st.pstdev(good) / st.mean(good)
            stable[ramp] = {"median_sec": st.median(good), "cv": cv, "values": good}
            print("%-8s %s   중앙 %6.1f · 변동계수 %.3f %s"
                  % (ramp, row, st.median(good), cv, "" if cv < 0.25 else "**불안정**"))
        else:
            print("%-8s %s   (표본 부족)" % (ramp, row))

    print()
    print("-- 처리량 q [veh/h] (수요별) --")
    for ramp in RAMP_LINKS:
        print("%-8s %s"
              % (ramp, "  ".join("%6.0f" % per_run[r]["throughput_vph"][ramp] for r in per_run)))

    worst_cv = max((v["cv"] for v in stable.values()), default=1.0)
    ok = worst_cv < 0.25
    print()
    print("모형 검정: 통과시간이 수요에 걸쳐 %s (최대 변동계수 %.3f)"
          % ("**상수에 가깝다 — 램프별 상수 사용 가능**" if ok else
             "**상수가 아니다 — 점유x상수 모형이 틀렸다**", worst_cv))

    caps = {ramp: max(per_run[r]["throughput_vph"][ramp] for r in per_run) for ramp in RAMP_LINKS}
    doc = {
        "schema_version": "ramp-arrival-calibration/1",
        "generated": "2026-08-30",
        "why": "local_ramp_arrival_forecast 가 queue_drain_horizon_sec=120 스칼라를 램프 넷에 "
               "다 써서 모델 ramp_arrival 이 플랜트의 35% 로 나온다. 어댑터가 이미 읽는 "
               "queue_drain_horizon_sec_by_ramp 에 넣을 값을 실측에서 뽑는다.",
        "method": "q=.fzp 고유차량수/창길이 (직접 계수) · N=상태JSON link_counts 중앙 · T=N*3600/q",
        "window_sec": [args.t0, args.t1],
        "per_run": per_run,
        "model_valid": ok,
        "worst_cv": worst_cv,
        "recommended": {
            "queue_drain_horizon_sec_by_ramp": {r: round(v["median_sec"], 1) for r, v in stable.items()},
            "max_vph_by_ramp": {r: round(c * 1.15, 0) for r, c in caps.items()},
            "note": "max_vph_by_ramp 는 실측 최대의 1.15배 — 현행 스칼라 cap 900 은 "
                    "R_F_W 실측(1212)을 자른다. 여유를 두되 물리 용량 1800 을 넘기지 않는다.",
        },
        "current_config": {"queue_drain_horizon_sec": 120.0, "max_vph_per_ramp": 900.0},
    }
    (R / args.out).write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print()
    print("권장 queue_drain_horizon_sec_by_ramp: %s"
          % {r: round(v["median_sec"], 1) for r, v in stable.items()})
    print("권장 max_vph_by_ramp:                 %s" % {r: round(c * 1.15, 0) for r, c in caps.items()})
    print("-> %s" % args.out)
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
