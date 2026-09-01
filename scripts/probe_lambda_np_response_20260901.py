# -*- coding: utf-8 -*-
"""팔로워의 Σnin(λ_P) 응답곡선을 직접 잰다 — 리더 탐색 없이.

`np_primal_dual_iters=0` · `np_candidate_lambda=False` 로 두면 solve() 는
warm-start λ(=`_lambda_P`) 하나로 Jacobi 를 1회 재수렴시키고 끝난다
(wu_faithful_follower.py:4195, 4418). 그래서 `_lambda_P` 를 직접 꽂으면
Σnin(λ) 를 점별로 잴 수 있다. λ_P 상한(:445)이 무엇을 자르고 있는지
"상한을 올리면 Σnin 이 내려가는가" 를 이 곡선 하나로 판정한다.

vendor 는 한 줄도 안 고친다.
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="canon_farbn_d00_x18_20260901")
    ap.add_argument("--indices", default="12,16,20,23,29")
    ap.add_argument("--lams", default="0,0.01,0.05,0.1,0.5,1,2,5,10,20,50,200,1000,100000")
    ap.add_argument("--out", default="outputs/lambda_np_response_curve.json")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    os.environ.setdefault("RW_MAINLINE_SG_ONLY", "1")

    tuning_path = str(R / ("evaluation/configs/%s.json" % args.run))
    sp = importlib.util.spec_from_file_location(
        "qb", R / "evaluation/controllers/vissim_stackelberg_adapter.py")
    qb = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(qb)
    from src.models.state import TrafficState, ControlAction
    from src.models.demand import DemandStep
    from src.controllers.leader import LeaderAction

    states = sorted(glob.glob(str(R / "evaluation/runs" / args.run / "decisions_*/state_*.json")))
    actions = sorted(glob.glob(str(R / "evaluation/runs" / args.run / "decisions_*/action_*.json")))
    lams = [float(x) for x in args.lams.split(",") if x.strip()]

    rows = []
    for i in [int(x) for x in args.indices.split(",") if x.strip()]:
        prev = actions[i - 1] if i > 0 else str(R / "__missing_previous.json")
        disk = json.loads(Path(actions[i]).read_text(encoding="utf-8"))
        ddg = disk.get("diagnostics") or {}
        n_uf = float(ddg.get("leader_selected_N_UF_star", 0.0))
        n_p = float(ddg.get("leader_intent_N_P_star", 0.0))

        cfg, st, sj, meta = PFC.build_cfg_and_state(
            qb, TrafficState, tuning_path, states[i], prev)
        cfg.mpc.np_primal_dual_iters = 0       # PD 루프 OFF -> λ 는 warm-start 하나뿐
        cfg.mpc.np_candidate_lambda = False    # 후보별 λ̂ 선반영 OFF
        tun = qb.load_optional_json(tuning_path)
        cal = qb.load_optional_json(str(R / PFC.DEFAULT_CAL))
        cal = qb.deep_update(dict(cal), tun.get("calibration_override") or {})
        dmp = str(tun.get("detector_mapping_json", "")).strip()
        dm = qb.load_optional_json(str(R / dmp) if not Path(dmp).is_absolute() else dmp)
        dm, _ = qb.filter_midblock_links_from_detector_mapping(dm, tun)
        hz = int(cfg.mpc.horizon_steps) + max(0, int(getattr(cfg.mpc, "leader_value_depth", 0)))
        forecast = qb.demand_from_state(sj, cfg, DemandStep, hz, cal, dm)
        previous = qb.control_from_json(Path(prev), cfg, ControlAction)
        action = LeaderAction(N_P_star=n_p, N_UF_star=n_uf)

        pts = []
        base_green = None
        for lam in lams:
            controller = qb.build_priced_wu_link_controller(cfg, tun)
            solver = controller.nash_solver
            # cap 은 위로 열어 둔다 — 여기서 재는 것은 "λ 를 이 값으로 두면 Σnin 이 얼마인가".
            solver.lambda_np_cap = max(1.0e12, lam * 10.0)
            solver._lambda_P = float(lam)
            t0 = time.perf_counter()
            res = solver.solve(st.copy(), action, forecast, previous)
            dt = time.perf_counter() - t0
            d = dict(res.control.diagnostics or {})
            g = dict(res.control.green_times)
            if base_green is None:
                base_green = g
            keys = set(g) | set(base_green)
            l1 = sum(abs(float(g.get(k, 0.0)) - float(base_green.get(k, 0.0))) for k in keys)
            pts.append({
                "lam": lam,
                "lam_used": float(d.get("wu_faithful_lambda_P", -1.0)),
                "sum_nin": float(d.get("wu_faithful_np_sum_nin", 0.0)),
                "feas_min": float(d.get("wu_faithful_np_feasible_min", 0.0)),
                "feas_max": float(d.get("wu_faithful_np_feasible_max", 0.0)),
                "green_L1_vs_lam0": l1,
                "solve_sec": dt,
                "green": g,
            })
            print("  λ=%-10g Σnin=%9.3f  feas=[%.1f,%.1f]  greenL1(vs λ0)=%8.3f (%.1fs)"
                  % (lam, pts[-1]["sum_nin"], pts[-1]["feas_min"], pts[-1]["feas_max"],
                     l1, dt))
        rows.append({
            "index": i, "sim_sec": float(sj.get("sim_sec", 0.0)),
            "leader_intent_N_P": n_p, "N_UF_star": n_uf,
            "disk_sum_nin": float(ddg.get("wu_faithful_np_sum_nin", 0.0)),
            "disk_lam": float(ddg.get("wu_faithful_lambda_P", 0.0)),
            "disk_feas_min": float(ddg.get("leader_np_follower_feasible_min", 0.0)),
            "disk_feas_max": float(ddg.get("leader_np_follower_feasible_max", 0.0)),
            "points": pts,
        })
        print("[%2d] t=%.0f  디스크 λ=%.2f Σnin=%.2f" % (
            i, rows[-1]["sim_sec"], rows[-1]["disk_lam"], rows[-1]["disk_sum_nin"]))
        (R / args.out).write_text(json.dumps(
            {"schema_version": "lambda-np-response/1", "run": args.run,
             "lams": lams, "rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
        print("  -> %s" % args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
