# -*- coding: utf-8 -*-
"""도시 agent 가 램프 미터링에 반응하는가 — 실제 solve() 에서 인자를 포착해 재생한다.

왜 (2026-08-31).

고속도로 모델 수정마다 freeway 는 좋아지고 urban 이 그보다 나빠진다(x1.0 mergefix
-4.3/+32.1, mergedyn -2.5/+7.4 · x1.8 mergefix -4.8/+18.4). 가설은 "그 상충이 GNE 안에서
저울질되지 않는다" 였다.

1단계는 **반증됐다** — 미터링을 4분의 1로 조이면 `_frozen_reservoir_drain` 이 75% 반응한다
(scripts/probe_urban_ramp_tradeoff_20260831.py). 사슬이 끊겨 있지 않다.

남은 두 단계를 잰다.

    2) 미터링 -> 도시 agent 의 국소 목적값이 움직이는가
    3) 미터링 -> 도시 agent 가 **다른 green 을 고르는가**   <- 저울질의 정의

어떻게. `_solve_urban_agent_local` 은 인자가 일곱 개(coupling · arr_movement · s_eff_frozen ·
reservoir_drain · freeway_congestion · lambda_p · forecast_arrivals)이고 전부 solve() 내부에서
만들어진다. 손으로 재구성하면 그 자체가 오독의 원천이므로(2026-08-31 에 detector mapping 을
추론으로 골랐다가 교정값을 한 번 틀렸다) **실제 solve() 를 한 번 돌려 인자를 그대로 포착**한다.
그 다음 `previous`(snapshot)의 ramp_metering 만 바꾸고 reservoir_drain 을 다시 계산해
같은 함수를 재호출한다. 나머지 결합값은 동결이라 단일변수가 된다.

램프를 먹이는 신호와 그렇지 않은 신호를 함께 재서, 반응이 있다면 그것이 램프 경로 때문인지
전역 잡음인지 가른다.

산출: outputs/urban_metering_response_20260831.json
"""
import argparse
import copy
import glob
import importlib.util
import json
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R))
sys.path.insert(0, str(R / "vendor/NumSim-mine"))

SCALES = [0.25, 0.5, 0.75, 1.0, 1.25]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="canon_fd3sw22_20260828")
    ap.add_argument("--tuning", default="evaluation/configs/canon_fd3sw22_20260828.json")
    ap.add_argument("--decision-index", type=int, default=18)
    ap.add_argument("--out", default="outputs/urban_metering_response_20260831.json")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    sp = importlib.util.spec_from_file_location(
        "qb", R / "evaluation/controllers/vissim_stackelberg_adapter.py")
    qb = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(qb)
    from src.models.state import ControlAction, TrafficState
    from src.models.demand import DemandStep

    tun = qb.load_optional_json(str(R / args.tuning))
    cal = qb.load_optional_json(
        str(R / "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json"))
    cal = qb.deep_update(dict(cal), tun.get("calibration_override") or {})
    dm = qb.load_optional_json(str(R / str(tun.get("detector_mapping_json")).replace("\\", "/")))
    qb.install_config_switches(tun)
    cfg = qb.build_config(R / "vendor/NumSim-mine", 150.0, 5400.0, "wu-link",
                          cal, tun, local_observation=True, flagship=True)
    qb._plant_rollout_far_into(cfg, tun)
    controller = qb.build_priced_wu_link_controller(cfg, tun)
    follower = controller.nash_solver
    net = cfg.network

    sfs = sorted(glob.glob(str(R / "evaluation/runs" / args.run / "decisions_*/state_*.json")))
    afs = sorted(glob.glob(str(R / "evaluation/runs" / args.run / "decisions_*/action_*.json")))
    sf, af = sfs[args.decision_index], afs[args.decision_index]
    sj = json.loads(Path(sf).read_text(encoding="utf-8"))
    aj = json.loads(Path(af).read_text(encoding="utf-8"))
    state = qb.traffic_state_from_vissim(sj, cfg, TrafficState, detector_mapping=dm, calibration=cal)
    _fm, ub, ra, _p = qb.profiled_demand_rates(sj, cfg, cal, dm)
    demand = DemandStep(freeway_mainline=dict(_fm), urban_boundary=dict(ub), ramp_arrival=dict(ra))
    print("결정 t=%s · 램프도착합 %.0f vph · 커밋 미터링합 %.0f"
          % (sj.get("sim_sec"), sum(ra.values()),
             sum(float(v) for v in (aj.get("ramp_metering") or {}).values())))

    # ---- 인자 포착 ----
    captured = {}
    orig = follower._solve_urban_agent_local

    def spy(signal, *a, **kw):
        if signal not in captured:
            captured[signal] = (copy.deepcopy(a), dict(kw))
        return orig(signal, *a, **kw)

    follower._solve_urban_agent_local = spy
    try:
        follower.solve(state, None, demand, previous_control=None)
    finally:
        follower._solve_urban_agent_local = orig
    print("인자 포착 신호 %d개" % len(captured))
    if not captured:
        print("!! 포착 실패")
        return 1

    # 램프를 소유한 freeway agent 의 이웃 교차로 (CLAUDE.md: SC1001 · SC1004)
    ramp_signals = [s for s in ("SC1001", "SC1004") if s in captured]
    others = [s for s in captured if s not in ramp_signals][:4]
    print("램프 인접 신호 %s · 대조 %s" % (ramp_signals, others))
    print()

    # ---- 재생: ramp_metering 만 바꾼다 ----
    # 포착 인자 순서: (state, coupling, arr_movement, s_eff_frozen, reservoir_drain,
    #                 freeway_congestion, previous, leader, lambda_p, forecast_arrivals,
    #                 horizon_h, demand, ...)
    IDX_RESERVOIR, IDX_PREV = 4, 6
    rows = {}
    for sig in ramp_signals + others:
        a, kw = captured[sig]
        base_prev = a[IDX_PREV]
        base_meter = {k: float(v) for k, v in dict(base_prev.ramp_metering).items()}
        per = {}
        for sc in SCALES:
            aa = list(copy.deepcopy(a))
            prev = aa[IDX_PREV]
            prev.ramp_metering = {k: v * sc for k, v in base_meter.items()}
            aa[IDX_RESERVOIR] = follower._frozen_reservoir_drain(aa[0], prev, demand)
            p1, obj, _e, nin = orig(sig, *aa, **kw)
            per[sc] = {"p1": float(p1), "objective": float(obj), "nin": float(nin),
                       "meter_sum": sum(prev.ramp_metering.values()),
                       "drain_sum": float(sum(aa[IDX_RESERVOIR].values()))}
        rows[sig] = per
        base = per[1.0]
        dp = max(abs(per[s]["p1"] - base["p1"]) for s in SCALES)
        do = max(abs(per[s]["objective"] - base["objective"]) for s in SCALES)
        rel = 100 * do / max(abs(base["objective"]), 1e-9)
        tag = "램프인접" if sig in ramp_signals else "대조"
        print("%-8s %-6s green p1 최대변화 %7.3f s · 목적값 최대변화 %10.4f (%.4f%%)"
              % (sig, tag, dp, do, rel))
        for sc in SCALES:
            p = per[sc]
            print("      x%-5.2f 미터링 %7.0f · drain %7.0f -> p1 %7.3f · obj %12.4f"
                  % (sc, p["meter_sum"], p["drain_sum"], p["p1"], p["objective"]))
        print()

    dp_ramp = max((max(abs(rows[s][x]["p1"] - rows[s][1.0]["p1"]) for x in SCALES)
                   for s in ramp_signals), default=0.0)
    dp_other = max((max(abs(rows[s][x]["p1"] - rows[s][1.0]["p1"]) for x in SCALES)
                    for s in others), default=0.0)
    if dp_ramp < 1e-6:
        verdict = ("**저울질이 없다** — 미터링을 4분의 1로 조여도 램프 인접 신호의 green 선택이 "
                   "한 자리도 안 바뀐다. 국소 비용이 미터링에 무감각하다.")
    elif dp_ramp > max(dp_other, 1e-9) * 3:
        verdict = ("**저울질이 있다** — 램프 인접 신호의 green 이 미터링에 %.3f s 반응하고, "
                   "대조 신호(%.3f s)보다 크다. 램프 경로가 실제로 작동한다." % (dp_ramp, dp_other))
    else:
        verdict = ("판정 보류 — 램프 인접 %.3f s 대 대조 %.3f s 로 구별이 안 된다. 반응이 "
                   "램프 경로 고유가 아닐 수 있다." % (dp_ramp, dp_other))
    print("판정: %s" % verdict)

    doc = {
        "schema_version": "urban-metering-response/1",
        "generated": "2026-08-31",
        "why": "고속도로 수정마다 freeway 개선분보다 urban 악화분이 크다. 그 상충이 GNE 안에서 "
               "저울질되는지 실제 solve() 인자를 포착해 재생으로 잰다.",
        "method": "solve() 를 한 번 돌려 _solve_urban_agent_local 인자를 포착 -> "
                  "previous.ramp_metering 만 배율로 바꾸고 reservoir_drain 재계산 -> 같은 함수 재호출. "
                  "나머지 결합값은 동결이라 단일변수다.",
        "run": args.run, "decision_sim_sec": sj.get("sim_sec"),
        "ramp_signals": ramp_signals, "control_signals": others,
        "scales": SCALES, "rows": rows,
        "max_green_change_ramp_sec": dp_ramp, "max_green_change_control_sec": dp_other,
        "verdict": verdict,
    }
    (R / args.out).write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print("-> %s" % args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
