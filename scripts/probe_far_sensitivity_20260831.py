# -*- coding: utf-8 -*-
"""리더 결정이 램프 큐에 반응하는가 — far(terminal cost)가 실제로 실리는지 잰다.

왜 (2026-08-31).

`w_ramp_queue` 를 0 으로 두자 램프 큐가 249 -> 1,469 veh 로 폭증했다(x1.8, VISSIM).
지평 450 s 인데 그 큐를 빼는 데 1,504 s 가 걸리므로, 리더가 창 밖 비용을 못 보면 미터링이
공짜로 보인다 — 전형적인 근시 병리다.

그런데 그 자리를 겨냥한 항이 이미 둘 있다.

    리더    mfd_far_cost_to_go 의 freeway reservoir 항
            ramp: q²/(2·merge_rate)·T_c_h (대기) + q·T_ramp_traverse (합류 후 통과)
            merge_rate = ramp_cap·receiving(ρ_merge) → 혼잡할수록 배수 느림
            leader_mfd_far_enabled·state_aware·real_speed·at_d0 전부 True
    팔로워  follower_terminal_cost_enabled 의 Q²/2R 삼각 배수 tail — **기본 OFF**

그리고 오프라인으로 far 자체는 램프 큐에 제대로 반응한다(+100 -> +15.1, +1200 -> +273.0, 볼록).
그런데 **실런 진단에 far 키가 하나도 없다.** CLAUDE.md 가 기록한 전례가 있다 —
"코디네이터는 point.objective 를 아예 안 본다 ... far 는 계산되고 **버려진다**".

무엇을 재나.

    같은 상태에서 **램프 큐만** 바꿔 controller.decide 를 부르고,
    (a) 커밋된 ramp_metering 합 (b) N_UF_star (c) 리더 목적값 이 움직이는지 본다.

    움직이면 far 가 실린 것이고 근시 병리 가설은 기각이다.
    안 움직이면 far 가 버려지는 것이고, 그때 고칠 자리는 두 곳이다 —
    리더 목적함수 배선, 또는 follower_terminal_cost_enabled.

산출: outputs/far_sensitivity_20260831.json
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

RAMP_VPH = {"R_D_W": 752.0, "R_F_W": 1212.0, "R_D_E": 938.0, "R_F_E": 555.0}
MAINLINE_BASE = [3080.0, 4400.0, 4620.0, 3960.0, 3080.0, 2200.0]
ADDS = [0.0, 150.0, 400.0, 900.0, 1800.0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tuning", default="evaluation/configs/canon_wrq0_d173_x18_20260831.json")
    ap.add_argument("--run", default="canon_wrq0_d173_x18_20260831")
    ap.add_argument("--index", type=int, default=18)
    ap.add_argument("--demand-mult", type=float, default=1.8)
    ap.add_argument("--out", default="outputs/far_sensitivity_20260831.json")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    sp = importlib.util.spec_from_file_location(
        "qb", R / "evaluation/controllers/vissim_stackelberg_adapter.py")
    qb = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(qb)
    from src.models.state import TrafficState
    from src.models.demand import DemandStep
    from src.controllers.stackelberg_mpc import mfd_far_cost_to_go

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
    net = cfg.network

    print("구성  far_enabled %s · at_d0 %s · state_aware %s · real_speed %s · value_depth %s"
          % (cfg.mpc.leader_mfd_far_enabled, cfg.mpc.leader_mfd_far_at_d0,
             cfg.mpc.leader_mfd_far_state_aware, cfg.mpc.leader_mfd_far_real_speed,
             cfg.mpc.leader_value_depth))
    print("      w_ramp_queue %.1f · follower_terminal_cost %s · 지평 %.0f s"
          % (cfg.leader.w_ramp_queue,
             getattr(cfg.mpc, "follower_terminal_cost_enabled", False),
             cfg.simulation.control_interval * cfg.mpc.horizon_steps))
    print()

    sf = sorted(glob.glob(str(R / "evaluation/runs" / args.run / "decisions_*/state_*.json")))[args.index]
    sj = json.loads(Path(sf).read_text(encoding="utf-8"))
    base_state = qb.traffic_state_from_vissim(sj, cfg, TrafficState,
                                              detector_mapping=dm, calibration=cal)
    _fm, ub, ra, _p = qb.profiled_demand_rates(sj, cfg, cal, dm)
    t = float(sj.get("sim_sec") or 0.0)
    idx = min(int(t // 900.0), len(MAINLINE_BASE) - 1)
    ml = MAINLINE_BASE[idx] * args.demand_mult

    def demand():
        return DemandStep(freeway_mainline={lk: ml for lk in net.freeway_links},
                          urban_boundary=dict(ub), ramp_arrival=dict(RAMP_VPH))

    forecast = [demand() for _ in range(max(1, cfg.mpc.horizon_steps))]

    rows = []
    print("%-10s %10s %12s %12s %12s %12s"
          % ("램프큐 +", "램프큐 합", "far", "미터링 합", "N_UF*", "리더 목적값"))
    for add in ADDS:
        st = copy.deepcopy(base_state)
        n = max(1, len(st.ramp_queue))
        for r in st.ramp_queue:
            st.ramp_queue[r] = float(base_state.ramp_queue.get(r, 0.0)) + add / n
        far = float(mfd_far_cost_to_go(cfg, st))
        ctl = controller.decide(st.copy(), forecast, None, cfg)
        d = dict(ctl.diagnostics or {})
        ms = sum(float(v) for v in (ctl.ramp_metering or {}).values())
        nuf = float(d.get("leader_selected_N_UF_star", d.get("leader_candidate_best_N_UF_star", 0.0)) or 0.0)
        obj = float(d.get("leader_total_objective", d.get("leader_candidate_best_objective", 0.0)) or 0.0)
        rows.append({"add": add, "ramp_queue_sum": sum(st.ramp_queue.values()),
                     "far": far, "meter_sum": ms, "nuf": nuf, "objective": obj,
                     "metering": {k: float(v) for k, v in (ctl.ramp_metering or {}).items()}})
        print("%-10.0f %10.1f %12.2f %12.0f %12.0f %12.3f"
              % (add, sum(st.ramp_queue.values()), far, ms, nuf, obj))

    d_far = rows[-1]["far"] - rows[0]["far"]
    d_obj = rows[-1]["objective"] - rows[0]["objective"]
    d_ms = rows[-1]["meter_sum"] - rows[0]["meter_sum"]
    print()
    print("램프큐 0 -> %.0f 일 때   far %+.2f · 리더 목적값 %+.3f · 미터링 %+.0f"
          % (ADDS[-1], d_far, d_obj, d_ms))
    if abs(d_obj) < 1e-6:
        verdict = ("**far 가 리더 목적함수에 안 실린다** — 램프 큐를 %.0f veh 늘려도 목적값이 "
                   "한 자리도 안 변한다. far 는 계산되고 버려진다." % ADDS[-1])
    elif abs(d_ms) < 1e-6:
        verdict = ("목적값은 %+.3f 움직이는데 **미터링이 안 바뀐다** — far 가 실리기는 하나 "
                   "결정으로 번역되지 않는다(후보 격자·팔로워가 지배)." % d_obj)
    else:
        verdict = ("far 가 실리고 결정도 바뀐다 — 램프큐 %.0f veh 증가에 미터링 %+.0f veh/h. "
                   "근시 병리 가설은 이 축에서는 기각이다." % (ADDS[-1], d_ms))
    print("판정: %s" % verdict)

    doc = {"schema_version": "far-sensitivity/1", "generated": "2026-08-31",
           "tuning": args.tuning, "run": args.run, "decision_sim_sec": t,
           "config": {"leader_mfd_far_enabled": cfg.mpc.leader_mfd_far_enabled,
                      "leader_mfd_far_at_d0": cfg.mpc.leader_mfd_far_at_d0,
                      "leader_value_depth": cfg.mpc.leader_value_depth,
                      "w_ramp_queue": cfg.leader.w_ramp_queue,
                      "follower_terminal_cost_enabled":
                          getattr(cfg.mpc, "follower_terminal_cost_enabled", False),
                      "horizon_sec": cfg.simulation.control_interval * cfg.mpc.horizon_steps},
           "rows": rows, "verdict": verdict}
    (R / args.out).write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print("-> %s" % args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
