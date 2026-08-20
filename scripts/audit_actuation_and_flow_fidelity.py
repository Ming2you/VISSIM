# -*- coding: utf-8 -*-
"""액추에이션 충실도(녹색)와 유량 충실도(통과 대수)를 한 런에서 갈라 잰다.

왜 필요한가
-----------
리더가 폴백에 계속 기각당할 때 원인이 셋 중 어디인지 가려야 한다.

  (a) 우리가 정한 녹색이 VISSIM 에 안 들어간다   -> 액추에이션 결함
  (b) 들어갔는데 모델이 예측한 유량이 안 나온다   -> 모델(environment) 결함
  (c) 둘 다 맞는데 제어가 실제로 나쁘다           -> 제어 결함

2026-08-20 실측에서는 (a) 가 깨끗하고 (b) 가 20~32% 어긋났다. 그 판정을 매 런 반복할 수
있게 도구로 굳힌다.

무엇을 재나
-----------
**녹색**  `action_<run>.csv` 의 `signal_sg` 행은 컬럼을 재사용한다(러너 VBS:1008 주석) —
`dsd_no`=SG 번호, `link`=창 인덱스, `p1_green`=창 시작[s], `p2_green`=창 끝[s],
`green_sec`=플랜 주기[s]. **`green_sec` 은 녹색 길이가 아니다.** 여기서 SG 별 계획창을
만들고, `decisions_*/signal_readback.csv` 의 `post_step` 표본을 시간 적분해 실현 녹색과
맞댄다.

비교 대상은 **SG 자기 계획창**이지 현시 녹색이 아니다. SC5·SC7·SC109 처럼 SG 가 현시의
일부만 녹색인 설계가 있어, 현시 녹색과 맞대면 40% 밖에 안 나오는 것처럼 보인다
(2026-08-20 오판).

**유량**  `decisions_*/state_<t>.json` 의 `vehicle_records.records` 는 전 차량 스냅샷이다.
`veh_no` 를 인접 결정 간에 대조하면 사라진 차량 = 완료, 새로 나타난 차량 = 진입이다.
회계가 `재고(t+1) = 재고(t) + 진입 - 완료` 로 정확히 닫히는지 자체 검증한다.

모델 쪽은 `leader_fallback_guard_fallback_completed_proxy_veh`
(= `distributed_response_mainline_exit_veh` + `..._boundary_out_sink_veh`) 이고 롤아웃
horizon(기본 3스텝) 구간이다. 그래서 VISSIM 실측도 같은 구간으로 합쳐 비교한다.

한계
----
`signal_readback.csv` 표본이 ~5초 간격이라 녹색 길이 해상도가 ±5초다. 그래서 임계값
기본이 6.0 초다. 더 촘촘히 봐야 하면 러너의 되읽기 주기를 줄여야 한다.
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run_paths(run_dir: Path):
    decisions = sorted(run_dir.glob("decisions_*"))
    if not decisions:
        raise SystemExit("decisions_* 디렉터리가 없다: " + str(run_dir))
    action = next(iter(run_dir.glob("action_*.csv")), None)
    if action is None:
        raise SystemExit("action CSV 가 없다: " + str(run_dir))
    return action, decisions[0] / "signal_readback.csv", decisions[0]


def green_fidelity(action_csv: Path, readback_csv: Path, tol_sec: float) -> dict:
    """SG 계획창 대 실현 녹색."""
    if not readback_csv.exists():
        return {"available": False, "reason": readback_csv.name + " 없음"}

    with readback_csv.open(encoding="utf-8-sig") as fh:
        all_rows = list(csv.DictReader(fh))
    disagreements = sum(1 for r in all_rows if r["requested_state"] != r["readback_state"])
    rows = [r for r in all_rows if r["stage"] == "post_step"]

    seq = collections.defaultdict(list)
    for r in rows:
        seq[(r["sc_no"], r["sg_no"])].append((float(r["sim_sec"]), r["readback_state"]))
    for key in seq:
        seq[key].sort()

    def realized(sc, sg, t0, t1):
        s = [x for x in seq.get((sc, sg), []) if t0 <= x[0] <= t1]
        return sum(s[i + 1][0] - s[i][0] for i in range(len(s) - 1) if s[i][1] == "GREEN")

    plan = collections.defaultdict(float)
    with action_csv.open(encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            if r["kind"] != "signal_sg":
                continue
            plan[(r["sim_sec"], r["sc_no"], r["dsd_no"])] += (
                float(r["p2_green"]) - float(r["p1_green"])
            )

    # 마지막 결정의 창은 시뮬 종료 뒤로 뻗어 되읽기가 없다. 그대로 재면 실현 0 으로
    # 나와 전부 위반으로 잡힌다(2026-08-20 최초 판에서 128건이 그렇게 잡혔다).
    # 되읽기가 창을 온전히 덮는 것만 채점한다.
    last_sample = max((s[-1][0] for s in seq.values() if s), default=0.0)

    offenders = []
    worst = 0.0
    skipped_uncovered = 0
    for (t, sc, sg), want in sorted(plan.items()):
        t0 = float(t)
        if t0 + 150.0 > last_sample:
            skipped_uncovered += 1
            continue
        got = realized(sc, sg, t0, t0 + 150.0)
        delta = got - want
        worst = max(worst, abs(delta))
        if abs(delta) > tol_sec:
            offenders.append({
                "sim_sec": t0, "sc": sc, "sg": sg,
                "planned_sec": round(want, 1),
                "realized_sec": round(got, 1),
                "delta_sec": round(delta, 1),
            })

    return {
        "available": True,
        "readback_rows": len(all_rows),
        "readback_disagreements": disagreements,
        "sg_windows_declared": len(plan),
        "sg_windows_checked": len(plan) - skipped_uncovered,
        "sg_windows_skipped_beyond_sim_end": skipped_uncovered,
        "tolerance_sec": tol_sec,
        "sg_windows_off_tolerance": len(offenders),
        "worst_abs_delta_sec": round(worst, 1),
        "verdict": "PASS" if not offenders and disagreements == 0 else "FAIL",
        "offenders": offenders[:20],
    }


def flow_fidelity(decision_dir: Path) -> dict:
    """모델 완료 프록시 대 VISSIM 실측 완료(veh_no 대조)."""
    snaps = {}
    for f in sorted(decision_dir.glob("state_*.json")):
        payload = json.loads(f.read_text(encoding="utf-8"))
        vr = payload.get("vehicle_records") or {}
        if not vr.get("complete"):
            continue
        t = int(os.path.basename(str(f))[6:12])
        snaps[t] = {r["veh_no"] for r in (vr.get("records") or [])}

    times = sorted(snaps)
    if len(times) < 2:
        return {"available": False, "reason": "완전한 vehicle_records 스냅샷이 2개 미만"}

    per = {}
    ledger_ok = True
    for a, b in zip(times, times[1:]):
        done = len(snaps[a] - snaps[b])
        new = len(snaps[b] - snaps[a])
        per[(a, b)] = {"completed": done, "entered": new, "stock_end": len(snaps[b])}
        if len(snaps[a]) + new - done != len(snaps[b]):
            ledger_ok = False

    comparisons = []
    for f in sorted(decision_dir.glob("action_*.json")):
        diag = (json.loads(f.read_text(encoding="utf-8")).get("diagnostics") or {})
        key = "leader_fallback_guard_fallback_completed_proxy_veh"
        if key not in diag:
            continue
        t = int(os.path.basename(str(f))[7:13])
        steps = int(diag.get("distributed_grid_rollout_horizon_steps", 3) or 3)
        actual = 0
        complete = True
        for i in range(steps):
            span = (t + 150 * i, t + 150 * (i + 1))
            if span in per:
                actual += per[span]["completed"]
            else:
                complete = False
        if not complete:
            continue
        model = float(diag[key])
        comparisons.append({
            "sim_sec": t,
            "horizon_steps": steps,
            "model_completed_veh": round(model, 1),
            "vissim_completed_veh": actual,
            "ratio_model_over_vissim": round(model / actual, 3) if actual else None,
            "leader_model_completed_veh": round(
                float(diag.get("leader_fallback_guard_leader_completed_proxy_veh", 0.0)), 1),
        })

    ratios = [c["ratio_model_over_vissim"] for c in comparisons if c["ratio_model_over_vissim"]]
    mean_ratio = round(sum(ratios) / len(ratios), 3) if ratios else None
    return {
        "available": True,
        "vehicle_ledger_closes": ledger_ok,
        "intervals": [dict(from_sec=a, to_sec=b, **v) for (a, b), v in per.items()],
        "comparisons": comparisons,
        "mean_ratio_model_over_vissim": mean_ratio,
        "verdict": "PASS" if ratios and all(0.9 <= r <= 1.1 for r in ratios) else "FAIL",
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("run_dir", type=Path, help="evaluation/runs/<name>")
    ap.add_argument("--green-tolerance-sec", type=float, default=6.0,
                    help="되읽기 표본이 ~5초 간격이라 기본 6.0")
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    run_dir = args.run_dir if args.run_dir.is_absolute() else ROOT / args.run_dir
    action, readback, ddir = _run_paths(run_dir)
    report = {
        "schema": "actuation_flow_fidelity/v1",
        "run": run_dir.name,
        "green": green_fidelity(action, readback, args.green_tolerance_sec),
        "flow": flow_fidelity(ddir),
    }

    green, flow = report["green"], report["flow"]
    print("=== " + run_dir.name + " ===")
    if green.get("available"):
        print("녹색  {}  되읽기 {}행 · 불일치 {} · SG창 {} 중 허용초과 {} "
              "(최대 편차 {}s, 허용 {}s, 종료초과로 제외 {})".format(
                  green["verdict"], green["readback_rows"], green["readback_disagreements"],
                  green["sg_windows_checked"], green["sg_windows_off_tolerance"],
                  green["worst_abs_delta_sec"], green["tolerance_sec"],
                  green["sg_windows_skipped_beyond_sim_end"]))
        for o in green["offenders"][:5]:
            print("     t={:.0f} SC{} SG{} 계획 {}s 실현 {}s ({:+}s)".format(
                o["sim_sec"], o["sc"], o["sg"], o["planned_sec"], o["realized_sec"], o["delta_sec"]))
    else:
        print("녹색  측정 불가 — " + str(green.get("reason")))

    if flow.get("available"):
        print("유량  {}  차량회계 {} · 모델/VISSIM 평균비 {}".format(
            flow["verdict"], "닫힘" if flow["vehicle_ledger_closes"] else "안 닫힘",
            flow["mean_ratio_model_over_vissim"]))
        print("     {:>7}{:>10}{:>10}{:>8}".format("결정", "모델", "VISSIM", "비율"))
        for c in flow["comparisons"]:
            print("     {:7d}{:10.1f}{:10d}{:8.3f}".format(
                c["sim_sec"], c["model_completed_veh"], c["vissim_completed_veh"],
                c["ratio_model_over_vissim"]))
    else:
        print("유량  측정 불가 — " + str(flow.get("reason")))

    if args.out:
        out = args.out if args.out.is_absolute() else ROOT / args.out
        out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        print("\n-> " + str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
