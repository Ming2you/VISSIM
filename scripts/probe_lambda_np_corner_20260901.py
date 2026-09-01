# -*- coding: utf-8 -*-
"""λ 를 무한대로 밀면 각 신호가 정말 'nin 최소' 후보를 고르는가 — 코너 판정.

λ_P 상한을 올려도 Σnin 이 안 내려간다면 두 가지 중 하나다:
 (a) 이미 코너다 — 모든 신호가 자기 후보집합의 nin 최소를 고르고 있다. λ 는 더 살 게 없다.
 (b) 코너가 아니다 — 다른 항(own-TTS·가격·offset)이 λ 를 이기고 있다.
`_solve_urban_agent_local`(:3722 호출부) 을 감싸 신호별 선택 p1 과 후보집합 nin 최소를
같은 인자로 대조한다. vendor 는 안 고친다.
"""
import argparse
import glob
import json
import os
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R))
sys.path.insert(0, str(R / "vendor/NumSim-mine"))
sys.path.insert(0, str(R / "evaluation/controllers"))

import probe_far_components_20260901 as PFC  # noqa: E402
import vissim_stackelberg_adapter as qb  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="canon_farbn_d00_x18_20260901")
    ap.add_argument("--index", type=int, default=12)
    ap.add_argument("--lams", default="10,100000")
    ap.add_argument("--out", default="outputs/lambda_np_corner.json")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    os.environ.setdefault("RW_MAINLINE_SG_ONLY", "1")

    tuning_path = str(R / ("evaluation/configs/%s.json" % args.run))
    from src.models.state import TrafficState, ControlAction
    from src.models.demand import DemandStep
    from src.controllers.leader import LeaderAction
    from src.controllers.wu_faithful_follower import WuFaithfulFollower

    states = sorted(glob.glob(str(R / "evaluation/runs" / args.run / "decisions_*/state_*.json")))
    actions = sorted(glob.glob(str(R / "evaluation/runs" / args.run / "decisions_*/action_*.json")))
    i = args.index
    prev = actions[i - 1]
    ddg = json.loads(Path(actions[i]).read_text(encoding="utf-8"))["diagnostics"]

    cfg, st, sj, _ = PFC.build_cfg_and_state(qb, TrafficState, tuning_path, states[i], prev)
    cfg.mpc.np_primal_dual_iters = 0
    cfg.mpc.np_candidate_lambda = False
    tun = qb.load_optional_json(tuning_path)
    cal = qb.load_optional_json(str(R / PFC.DEFAULT_CAL))
    cal = qb.deep_update(dict(cal), tun.get("calibration_override") or {})
    dmp = str(tun.get("detector_mapping_json", "")).strip()
    dm = qb.load_optional_json(str(R / dmp) if not Path(dmp).is_absolute() else dmp)
    dm, _ = qb.filter_midblock_links_from_detector_mapping(dm, tun)
    hz = int(cfg.mpc.horizon_steps) + max(0, int(getattr(cfg.mpc, "leader_value_depth", 0)))
    forecast = qb.demand_from_state(sj, cfg, DemandStep, hz, cal, dm)
    previous = qb.control_from_json(Path(prev), cfg, ControlAction)
    action = LeaderAction(N_P_star=float(ddg.get("leader_intent_N_P_star", -250.0)),
                          N_UF_star=float(ddg.get("leader_selected_N_UF_star", 0.0)))

    out = {"run": args.run, "index": i, "sim_sec": float(sj.get("sim_sec", 0.0)),
           "disk_sum_nin": float(ddg.get("wu_faithful_np_sum_nin", 0.0)),
           "disk_feas_min": float(ddg.get("leader_np_follower_feasible_min", 0.0)),
           "arms": []}
    _orig = WuFaithfulFollower._solve_urban_agent_local
    for lam in [float(x) for x in args.lams.split(",")]:
        rec = {}

        def wrapped(self, signal, state, coupling, arr_movement, s_eff_frozen,
                    reservoir_drain, freeway_congestion, previous, leader=None,
                    lambda_p=0.0, forecast_arrivals=None, horizon_h=1.0, demand=None,
                    candidates_override=None, committed_prev=None, _o=_orig):
            r = _o(self, signal, state, coupling, arr_movement, s_eff_frozen,
                   reservoir_drain, freeway_congestion, previous, leader, lambda_p,
                   forecast_arrivals, horizon_h, demand, candidates_override,
                   committed_prev)
            best_p1, best_obj, evals, best_nin = r
            snapshot = previous
            cands = (list(candidates_override) if candidates_override is not None
                     else self._urban_green_candidates(signal, state, coupling, snapshot))
            # B2.1 신뢰영역(:885-898) 을 여기서 그대로 재현해 **실제로 채점된 후보집합**을 만든다.
            trusted = list(cands)
            trust_active = 0
            if (candidates_override is None
                    and self.signal_marginal_price is not None
                    and self.signal_marginal_price_trust_sec is not None
                    and signal in self.signal_marginal_price):
                tr = float(self.signal_marginal_price_trust_sec)
                ref = float(self.signal_marginal_price_ref.get(
                    signal, self._wu and 0.0 or 0.0))
                sub = [p1 for p1 in cands if abs(p1 - ref) <= tr + 1.0e-9]
                if sub:
                    trusted = sub
                    trust_active = 1
            nins = [(float(p1), float(self._agent_net_inflow_veh(
                signal, p1, state, forecast_arrivals, horizon_h))) for p1 in cands]
            tnins = [(float(p1), float(self._agent_net_inflow_veh(
                signal, p1, state, forecast_arrivals, horizon_h))) for p1 in trusted]
            if nins:
                p_min, n_min = min(nins, key=lambda t: t[1])
                tp_min, tn_min = min(tnins, key=lambda t: t[1])
                rec[signal] = {"lambda_p_seen": float(lambda_p),
                               "chosen_p1": float(best_p1), "chosen_nin": float(best_nin),
                               "argmin_p1": p_min, "min_nin": n_min,
                               "gap_veh": float(best_nin) - n_min,
                               "n_candidates": len(nins),
                               "evals_reported": int(evals),
                               "price_active": int(
                                   self.signal_marginal_price is not None
                                   and signal in (self.signal_marginal_price or {})),
                               "trust_sec": (None if self.signal_marginal_price_trust_sec
                                             is None else float(
                                                 self.signal_marginal_price_trust_sec)),
                               "baseline_move_box": int(bool(getattr(
                                   self.cfg.mpc, "baseline_move_box", False))),
                               "committed_prev_given": int(committed_prev is not None),
                               "trust_active": trust_active,
                               "n_trusted": len(tnins),
                               "trusted_argmin_p1": tp_min, "trusted_min_nin": tn_min,
                               "gap_within_trust_veh": float(best_nin) - tn_min,
                               "nin_spread_full_veh": max(n for _, n in nins) - n_min,
                               "nin_spread_trust_veh": max(n for _, n in tnins) - tn_min}
                # 코너를 안 잡은 신호는 **같은 함수로 두 후보의 비용을 직접 재본다**
                # (candidates_override 단일 후보 = 그 후보의 cost, :879-881).
                if float(best_nin) - n_min > 1.0e-9:
                    def _score(p):
                        rr = _o(self, signal, state, coupling, arr_movement, s_eff_frozen,
                                reservoir_drain, freeway_congestion, previous, leader,
                                lambda_p, forecast_arrivals, horizon_h, demand, [p],
                                committed_prev)
                        return float(rr[1]), float(rr[3])
                    c_ch, n_ch = _score(float(best_p1))
                    c_am, n_am = _score(float(p_min))
                    rec[signal].update({
                        "cost_at_chosen": c_ch, "nin_at_chosen_rescored": n_ch,
                        "cost_at_full_argmin": c_am, "nin_at_full_argmin_rescored": n_am,
                        "cost_argmin_minus_chosen": c_am - c_ch})
            return r

        WuFaithfulFollower._solve_urban_agent_local = wrapped
        try:
            controller = qb.build_priced_wu_link_controller(cfg, tun)
            controller.nash_solver.lambda_np_cap = 1.0e12
            controller.nash_solver._lambda_P = lam
            res = controller.nash_solver.solve(st.copy(), action, forecast, previous)
        finally:
            WuFaithfulFollower._solve_urban_agent_local = _orig
        d = dict(res.control.diagnostics or {})
        rows = sorted(rec.items())
        at_corner = sum(1 for _, v in rows if v["gap_veh"] <= 1.0e-9)
        at_trust_corner = sum(1 for _, v in rows if v["gap_within_trust_veh"] <= 1.0e-9)
        single = sum(1 for _, v in rows if v["n_trusted"] <= 1)
        flat = sum(1 for _, v in rows if v["nin_spread_trust_veh"] <= 1.0e-9)
        arm = {"lam": lam,
               "sum_nin": float(d.get("wu_faithful_np_sum_nin", 0.0)),
               "feas_min": float(d.get("wu_faithful_np_feasible_min", 0.0)),
               "signals_at_nin_corner": at_corner, "signals_total": len(rows),
               "signals_at_trust_corner": at_trust_corner,
               "signals_single_trusted_candidate": single,
               "signals_flat_nin_in_trust": flat,
               "sum_gap_veh": sum(v["gap_veh"] for _, v in rows),
               "sum_gap_within_trust_veh": sum(v["gap_within_trust_veh"] for _, v in rows),
               "per_signal": {k: v for k, v in rows}}
        out["arms"].append(arm)
        print("λ=%-10g Σnin=%9.3f feas_min=%8.3f | 전체후보 코너 %d/%d(잔여 %.3f) · "
              "신뢰영역 안 코너 %d/%d(잔여 %.3f) · 후보1개 %d · nin평평 %d"
              % (lam, arm["sum_nin"], arm["feas_min"], at_corner, len(rows),
                 arm["sum_gap_veh"], at_trust_corner, len(rows),
                 arm["sum_gap_within_trust_veh"], single, flat))
        for k, v in rows:
            print("   %-9s p1=%6.2f nin=%8.3f | 신뢰 n=%2d min p1=%6.2f nin=%8.3f gap=%7.3f "
                  "spread(신뢰/전체)=%7.3f/%7.3f | 전체 argmin p1=%6.2f gap=%7.3f"
                  % (k, v["chosen_p1"], v["chosen_nin"], v["n_trusted"],
                     v["trusted_argmin_p1"], v["trusted_min_nin"],
                     v["gap_within_trust_veh"], v["nin_spread_trust_veh"],
                     v["nin_spread_full_veh"], v["argmin_p1"], v["gap_veh"]))
    (R / args.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("-> %s" % args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
