# -*- coding: utf-8 -*-
"""λ_P 상한(`WuFaithfulFollower.lambda_np_cap`, wu_faithful_follower.py:445)만 바꿔
완주한 런의 실제 결정을 오프라인 재생하며 A/B 한다.

배선은 probe_far_at_decide_20260901.py 와 동일(어댑터 main() 재현 + 몽키패치).
vendor 는 한 줄도 안 고친다. 상한은 config 키가 아니라 인스턴스 속성이라
`WuFaithfulFollower.__init__` 을 감싸 사후 대입한다(모든 서브클래스 포함).

산출: outputs/lambda_np_cap_ab_<run>.json
"""
import argparse
import glob
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R))
sys.path.insert(0, str(R / "vendor/NumSim-mine"))

import probe_far_components_20260901 as PFC  # noqa: E402


def _green_l1(a, b):
    keys = set(a) | set(b)
    return sum(abs(float(a.get(k, 0.0)) - float(b.get(k, 0.0))) for k in keys)


def _dict_l1(a, b):
    keys = set(a) | set(b)
    return sum(abs(float(a.get(k, 0.0)) - float(b.get(k, 0.0))) for k in keys)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="canon_farbn_d00_x18_20260901")
    ap.add_argument("--tuning", default="")
    ap.add_argument("--indices", default="12,16,20,23,29")
    ap.add_argument("--caps", default="10,50,200,1000,1e9")
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    os.environ.setdefault("RW_MAINLINE_SG_ONLY", "1")

    tuning_path = args.tuning or str(R / ("evaluation/configs/%s.json" % args.run))
    # 어댑터는 **제 이름으로** 임포트한다 — 가격 워커 풀이 자식 프로세스에서
    # `importlib.import_module(boot["module"])` 로 되살리므로(priced_wu_link_controller.py:817)
    # "qb" 같은 임시 이름이면 ModuleNotFoundError 로 병렬 가격이 조용히 죽는다.
    sys.path.insert(0, str(R / "evaluation/controllers"))
    import vissim_stackelberg_adapter as qb  # noqa: E402
    from src.models.state import TrafficState
    from src.models.demand import DemandStep
    from src.models.state import ControlAction
    import src.controllers.stackelberg_mpc as sm
    from src.controllers.wu_faithful_follower import WuFaithfulFollower

    # ---- 상한 주입: __init__ 사후 대입(서브클래스 LinkAgentWuFollower 포함) ----
    _orig_init = WuFaithfulFollower.__init__
    CAP = {"v": 10.0}

    def _patched_init(self, *a, **kw):
        _orig_init(self, *a, **kw)
        self.lambda_np_cap = float(CAP["v"])

    WuFaithfulFollower.__init__ = _patched_init

    states = sorted(glob.glob(str(R / "evaluation/runs" / args.run / "decisions_*/state_*.json")))
    actions = sorted(glob.glob(str(R / "evaluation/runs" / args.run / "decisions_*/action_*.json")))
    caps = [float(x) for x in args.caps.split(",") if x.strip()]
    idxs = [int(x) for x in args.indices.split(",") if x.strip()]

    rows = []
    for i in idxs:
        prev = actions[i - 1] if i > 0 else str(R / "__missing_previous.json")
        disk = json.loads(Path(actions[i]).read_text(encoding="utf-8"))
        disk_dg = disk.get("diagnostics") or {}
        arms = []
        for cap in caps:
            CAP["v"] = cap
            cfg, st, sj, meta = PFC.build_cfg_and_state(
                qb, TrafficState, tuning_path, states[i], prev)
            calls = []
            base_fn = sm.mfd_far_cost_to_go

            def recorder(c, s, _base=base_fn):
                comp = PFC.far_components(c, s)
                v = float(_base(c, s))
                comp["far_total_from_vendor"] = v
                calls.append(comp)
                return v

            solves = []
            _orig_solve = WuFaithfulFollower.solve

            def _rec_solve(self, state_, leader_, demand_, previous_control_=None,
                           leader_incumbent_obj=float("inf"), _o=_orig_solve):
                res = _o(self, state_, leader_, demand_, previous_control_,
                         leader_incumbent_obj)
                d = dict(getattr(res.control, "diagnostics", {}) or {})
                solves.append({
                    "n_p_star_in": float(getattr(leader_, "N_P_star", 0.0))
                    if leader_ is not None else None,
                    "n_uf_star_in": float(getattr(leader_, "N_UF_star", 0.0))
                    if leader_ is not None else None,
                    "cap_on_self": float(getattr(self, "lambda_np_cap", -1.0)),
                    "lam_path": d.get("wu_faithful_np_pd_lam_path", ""),
                    "lam_P": float(d.get("wu_faithful_lambda_P", 0.0)),
                    "pd_exit": float(d.get("wu_faithful_np_pd_exit", -9.0)),
                    "pd_iters": float(d.get("wu_faithful_np_pd_iters", 0.0)),
                    "pd_residual": float(d.get("wu_faithful_np_pd_residual", 0.0)),
                    "sum_nin": float(d.get("wu_faithful_np_sum_nin", 0.0)),
                    "projected_target": float(d.get("wu_faithful_np_projected_target", 0.0)),
                    "feas_min": float(d.get("wu_faithful_np_feasible_min", 0.0)),
                    "feas_max": float(d.get("wu_faithful_np_feasible_max", 0.0)),
                    "green": dict(res.control.green_times),
                })
                return res

            WuFaithfulFollower.solve = _rec_solve
            sm.mfd_far_cost_to_go = recorder
            try:
                tun = qb.load_optional_json(tuning_path)
                cal = qb.load_optional_json(str(R / PFC.DEFAULT_CAL))
                cal = qb.deep_update(dict(cal), tun.get("calibration_override") or {})
                dmp = str(tun.get("detector_mapping_json", "")).strip()
                dm = qb.load_optional_json(str(R / dmp) if not Path(dmp).is_absolute() else dmp)
                dm, _ = qb.filter_midblock_links_from_detector_mapping(dm, tun)
                controller = qb.build_priced_wu_link_controller(cfg, tun)
                # 어댑터 main():9362-9370 을 그대로 — 이 셋이 빠지면 리더 목적함수와
                # fallback guard 가 실제 런과 달라진다(β̂ 미복원 -> guard 가 리더를 기각).
                fmeta = {}
                fmeta.update(qb.install_vissim_terminal_cost_objective(controller, cfg, tun))
                fmeta.update(qb.install_price_worker_bootstrap(controller, sj, dm))
                fmeta.update(qb.restore_leader_feedback_state(controller, tun, Path(prev)))
                caps_seen = sorted({
                    float(getattr(o, "lambda_np_cap"))
                    for o in (controller.nash_solver,)
                    if hasattr(o, "lambda_np_cap")})
                hz = int(cfg.mpc.horizon_steps) + max(
                    0, int(getattr(cfg.mpc, "leader_value_depth", 0)))
                forecast = qb.demand_from_state(sj, cfg, DemandStep, hz, cal, dm)
                previous = qb.control_from_json(Path(prev), cfg, ControlAction)
                t0 = time.perf_counter()
                result = controller.decide_with_info(st.copy(), forecast, previous, cfg)
                ctl = result.control
                elapsed = time.perf_counter() - t0
            finally:
                sm.mfd_far_cost_to_go = base_fn
                WuFaithfulFollower.solve = _orig_solve

            dg = dict(ctl.diagnostics or {})
            base = float(dg.get("leader_objective_base", 0.0))
            hor = float(dg.get("leader_pred_horizon_ttt", 0.0))
            far_implied = base - hor
            best = None
            if calls:
                best = min(calls, key=lambda c: abs(c["far_total"] - far_implied))
            arm = {
                "cap": cap,
                "caps_on_solver": caps_seen,
                "decide_sec": elapsed,
                "lam_path": dg.get("wu_faithful_np_pd_lam_path", ""),
                "lam_entry": float(dg.get("wu_faithful_np_pd_lam_entry", 0.0)),
                "lam_P": float(dg.get("wu_faithful_lambda_P", 0.0)),
                "lam_next": float(dg.get("wu_faithful_lambda_next", 0.0)),
                "pd_iters": float(dg.get("wu_faithful_np_pd_iters", 0.0)),
                "pd_exit": float(dg.get("wu_faithful_np_pd_exit", -9.0)),
                "pd_residual": float(dg.get("wu_faithful_np_pd_residual", 0.0)),
                "sum_nin": float(dg.get("wu_faithful_np_sum_nin", 0.0)),
                "projected_target": float(dg.get("wu_faithful_np_projected_target", 0.0)),
                "feas_min": float(dg.get("leader_np_follower_feasible_min", 0.0)),
                "feas_max": float(dg.get("leader_np_follower_feasible_max", 0.0)),
                "intent_N_P": float(dg.get("leader_intent_N_P_star", 0.0)),
                "realized_N_P": float(dg.get("leader_realized_N_P_star", 0.0)),
                "residual_N_P": float(dg.get("leader_response_N_P_star_realization_residual", 0.0)),
                "best_index": float(dg.get("leader_candidate_best_index", -1.0)),
                "best_intent_N_P": float(dg.get("leader_candidate_best_intent_N_P_star", 0.0)),
                "best_objective": float(dg.get("leader_candidate_best_objective", 0.0)),
                "second_index": float(dg.get("leader_candidate_second_index", -1.0)),
                "second_objective": float(dg.get("leader_candidate_second_objective", 0.0)),
                "cand_objective_spread": float(dg.get("leader_candidate_objective_spread", 0.0)),
                "selected_stage_fallback": float(dg.get("leader_selected_stage_fallback", 0.0)),
                "guard_rejected_leader": float(dg.get("leader_fallback_guard_rejected_leader", 0.0)),
                "obj_total": float(dg.get("leader_total_objective", 0.0)),
                "obj_base": base,
                "obj_density_penalty": float(dg.get("leader_density_penalty", 0.0)),
                "obj_mfd_storage_penalty": float(dg.get("leader_mfd_storage_penalty", 0.0)),
                "obj_ramp_queue_penalty": float(dg.get("leader_ramp_queue_penalty", 0.0)),
                "pred_horizon_ttt": hor,
                "pred_interval_ttt": float(dg.get("leader_pred_interval_ttt", 0.0)),
                "far_implied_from_base": far_implied,
                "far_calls": len(calls),
                "far_matched_total": (best or {}).get("far_total"),
                "far_matched_urban": (best or {}).get("urban_term"),
                "far_matched_mainline": (best or {}).get("mainline_term"),
                "far_matched_ramp": (best or {}).get("ramp_term"),
                "far_matched_n_u": (best or {}).get("n_u_far"),
                "green": dict(ctl.green_times),
                "ramp": dict(ctl.ramp_metering),
                "vsl": dict(ctl.vsl),
                "solves": solves,
                "all_diag": {k: v for k, v in dg.items()
                             if isinstance(v, (int, float, str))},
            }
            arms.append(arm)
            print("  cap=%-8g λ=%s  Σnin=%.2f  N_P*=%.2f  best_idx=%.0f obj=%.4f  (%.1fs)"
                  % (cap, arm["lam_path"], arm["sum_nin"], arm["realized_N_P"],
                     arm["best_index"], arm["best_objective"], elapsed))

        ref = arms[0]
        for a in arms:
            a["green_L1_vs_cap10"] = _green_l1(ref["green"], a["green"])
            a["ramp_L1_vs_cap10"] = _dict_l1(ref["ramp"], a["ramp"])
            a["vsl_L1_vs_cap10"] = _dict_l1(ref["vsl"], a["vsl"])
            a["sum_nin_delta_vs_cap10"] = a["sum_nin"] - ref["sum_nin"]
            a["obj_delta_vs_cap10"] = a["obj_total"] - ref["obj_total"]
        rows.append({
            "index": i,
            "sim_sec": float(json.loads(Path(states[i]).read_text(encoding="utf-8"))
                             .get("sim_sec", 0.0)),
            "disk_lam_path": disk_dg.get("wu_faithful_np_pd_lam_path", ""),
            "disk_sum_nin": float(disk_dg.get("wu_faithful_np_sum_nin", 0.0)),
            "disk_realized_N_P": float(disk_dg.get("leader_realized_N_P_star", 0.0)),
            "disk_best_index": float(disk_dg.get("leader_candidate_best_index", -1.0)),
            "disk_obj_total": float(disk_dg.get("leader_total_objective", 0.0)),
            "disk_green": dict(disk.get("green_times") or {}),
            "replay_cap10_green_L1_vs_disk": _green_l1(
                dict(disk.get("green_times") or {}), ref["green"]),
            "arms": arms,
        })
        print("[%2d] t=%.0f  디스크 Σnin=%.2f vs 재생(cap10) %.2f · green L1 %.4f"
              % (i, rows[-1]["sim_sec"], rows[-1]["disk_sum_nin"], ref["sum_nin"],
                 rows[-1]["replay_cap10_green_L1_vs_disk"]))

        out = args.out or ("outputs/lambda_np_cap_ab_%s.json" % args.run)
        (R / out).write_text(json.dumps(
            {"schema_version": "lambda-np-cap-ab/1", "run": args.run,
             "caps": caps, "rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
        print("  -> %s (누적 %d결정)" % (out, len(rows)))

    WuFaithfulFollower.__init__ = _orig_init
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
