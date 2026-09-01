# -*- coding: utf-8 -*-
"""far 의 도시항이 리더 후보들 사이에서 갈리는가, 아니면 상수처럼 붙는가.

한 결정을 **실런과 같은 배선으로** 재생하면서(어댑터 main 을 그대로 호출),
  1) 후보 채점 호출마다 far 를 도시/본선/램프 항으로 분해해 기록하고,
  2) 그 far 를 만든 rollout 말단 상태(states[-1])의 n_u·n_main·램프큐를 같이 남기고,
  3) 후보별 팔로워 응답 레버(녹색·미터링·VSL·offset)를 기록한다.

분해식은 vendor 원본(stackelberg_mpc.py:88 mfd_far_cost_to_go)을 그대로 옮겨 적고,
매 호출에서 원본 반환값과 분해 합의 잔차를 검사한다(residual 이 0 이 아니면 분해가 틀린 것).

산출: outputs/far_candidate_spread_<run>_<sec>.json
"""
import argparse
import copy
import importlib.util
import json
import os
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R))
sys.path.insert(0, str(R / "vendor/NumSim-mine"))

RECORDS = []          # far 호출 기록
CAND = []             # 후보 평가 기록
CTX = {"cur": None}
PAYLOAD_KEEP = {}     # 레버 스윕용 cfg/state/forecast/previous


def far_components(cfg, state):
    """mfd_far_cost_to_go(stackelberg_mpc.py:88) 를 항별로 분해한다(같은 식·같은 순서)."""
    from src.models.metanet import (
        _ramp_merge_index, _clip, desired_speed_kmh, segment_flow_veh_h,
    )
    net = cfg.network
    tc_h = float(cfg.simulation.T_c_h)
    w = float(getattr(cfg.mpc, "leader_mfd_far_weight", 1.0))
    state_aware = bool(getattr(cfg.mpc, "leader_mfd_far_state_aware", False))
    real_v = bool(getattr(cfg.mpc, "leader_mfd_far_real_speed", False))

    # ---- urban ----
    n_prot = float(state.protected_accumulation_veh(net))
    n_bq = float(state.boundary_in_queue_vehicles(net))
    n_u = n_prot + n_bq
    n_crit = float(getattr(cfg.mpc, "leader_mfd_far_ncrit", 1700.0))
    g_free = float(getattr(cfg.mpc, "leader_mfd_far_g_free", 640.0))
    g_cong = float(getattr(cfg.mpc, "leader_mfd_far_g_cong", 500.0))
    g_u = g_free if n_u < n_crit else g_cong
    urban = (n_u * n_u) * tc_h / (2.0 * max(g_u, 1.0))

    # ---- freeway mainline ----
    seg_len = float(net.freeway_segment_length_km)
    v_free = float(net.v_free)
    ramp_total = sum(max(0.0, float(state.ramp_queue.get(r, 0.0))) for r in net.ramps)
    n_main = max(0.0, float(state.total_freeway_vehicles(net)) - ramp_total)
    g_fw = float(getattr(cfg.mpc, "leader_mfd_far_g_fw", 300.0))
    main = 0.0
    if getattr(cfg.mpc, "leader_mfd_far_freeflow_offset", False):
        n_seg_l = int(net.freeway_segments_per_link)
        t_trav = (n_seg_l * seg_len) / max(v_free, 1.0)
        for link in net.freeway_links:
            dens = state.freeway_density.get(link, [])
            lanes = state.freeway_effective_lanes.get(link, [])

            def _lane_at(i):
                return max(float(lanes[i]) if i < len(lanes) else float(net.freeway_lanes), 1.0e-9)

            n_l = sum(max(0.0, float(dens[i])) * seg_len * _lane_at(i) for i in range(len(dens)))
            t_trav_l, g_fw_l = t_trav, g_fw
            if state_aware and dens:
                spd_l = state.freeway_speed.get(link, []) if real_v else []
                t_trav_l = 0.0
                caps = []
                for i in range(len(dens)):
                    if real_v and i < len(spd_l):
                        v_i = max(float(spd_l[i]), 1.0)
                    else:
                        v_i = desired_speed_kmh(max(0.0, float(dens[i])), v_free, net.rho_crit)
                    t_trav_l += seg_len / max(v_i, 1.0)
                    cap_i = segment_flow_veh_h(
                        net.rho_crit,
                        desired_speed_kmh(net.rho_crit, v_free, net.rho_crit),
                        _lane_at(i),
                    )
                    if real_v and i < len(spd_l) and float(dens[i]) > float(net.rho_crit):
                        cap_i = min(cap_i, max(float(dens[i]) * max(float(spd_l[i]), 1.0) * _lane_at(i), 1.0))
                    caps.append(cap_i)
                g_fw_l = min(caps) if caps else g_fw
            drainable_l = g_fw_l * (t_trav_l / max(tc_h, 1.0e-9))
            n_eff = max(0.0, n_l - drainable_l)
            main += (n_eff * n_eff) * tc_h / (2.0 * max(g_fw_l, 1.0)) + n_l * t_trav_l / 2.0
    else:
        main = (n_main * n_main) * tc_h / (2.0 * max(g_fw, 1.0))

    # ---- ramp ----
    ramp = 0.0
    per_ramp = {}
    for r in net.ramps:
        q = max(0.0, float(state.ramp_queue.get(r, 0.0)))
        if q <= 0.0:
            per_ramp[str(r)] = 0.0
            continue
        link = net.ramp_to_freeway.get(r)
        dens = state.freeway_density.get(link, [])
        if not dens:
            per_ramp[str(r)] = 0.0
            continue
        midx = _ramp_merge_index(cfg, r, len(dens))
        rho_merge = float(dens[midx])
        recv = _clip((net.rho_max - rho_merge) / max(net.rho_max - net.rho_crit, 1.0e-9), 0.0, 1.0)
        merge_interval = float(net.ramp_capacity_veh_h[r]) * recv * tc_h
        if state_aware:
            spd_r = state.freeway_speed.get(link, []) if real_v else []
            t_ramp_traverse = sum(
                seg_len / max(
                    (float(spd_r[i]) if real_v and i < len(spd_r)
                     else desired_speed_kmh(max(0.0, float(dens[i])), v_free, net.rho_crit)),
                    1.0,
                )
                for i in range(midx, len(dens))
            )
        else:
            t_ramp_traverse = (len(dens) - midx) * seg_len / max(v_free, 1.0)
        term = (q * q) * tc_h / (2.0 * max(merge_interval, 1.0e-6)) + q * t_ramp_traverse
        per_ramp[str(r)] = w * term
        ramp += term

    return {
        "urban": w * urban, "main": w * main, "ramp": w * ramp,
        "total": w * (urban + main + ramp),
        "n_u": n_u, "n_protected": n_prot, "n_boundary_in": n_bq,
        "n_main": n_main, "ramp_queue_total": ramp_total,
        "g_u": g_u, "g_fw": g_fw,
        "per_ramp": per_ramp,
        "ramp_queue": {str(r): float(state.ramp_queue.get(r, 0.0)) for r in net.ramps},
    }


def lever_summary(control):
    if control is None:
        return {}
    return {
        "green_times": {str(k): float(v) for k, v in dict(control.green_times).items()},
        "ramp_metering": {str(k): float(v) for k, v in dict(control.ramp_metering).items()},
        "vsl": {str(k): float(v) for k, v in dict(control.vsl).items()},
        "offsets": {str(k): float(v) for k, v in dict(control.offsets).items()},
        "inflow_outflow_allocation": {
            str(k): float(v) for k, v in dict(control.inflow_outflow_allocation).items()},
        "N_P_star": float(control.N_P_star), "N_UF_star": float(control.N_UF_star),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="canon_farbn_d00_x18_20260901")
    ap.add_argument("--sec", type=int, required=True)
    ap.add_argument("--all-candidates", action="store_true",
                    help="prefilter 를 무력화해 9개 후보 전부 full 채점")
    ap.add_argument("--lever-sweep", action="store_true",
                    help="후보 레버 교차 스왑 rollout 으로 어느 레버가 n_u 를 움직이는지")
    ap.add_argument("--tuning", default="", help="provenance 대신 쓸 tuning json(실런 재현용)")
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    run_dir = R / "evaluation/runs" / args.run
    dec = run_dir / ("decisions_" + args.run)
    state_json = dec / ("state_%06d.json" % args.sec)
    prev_json = dec / ("action_%06d.json" % (args.sec - 150))
    prov = json.loads((run_dir / ("run_provenance_%s.json" % args.run)).read_text(encoding="utf-8"))
    files = prov["files"]
    out_path = Path(args.out) if args.out else (
        R / "outputs" / ("far_candidate_spread_%s_%06d.json" % (args.run, args.sec)))

    os.environ.setdefault("RW_MAINLINE_SG_ONLY", "1")

    scratch = Path(os.environ.get("TEMP", ".")) / "far_probe"
    scratch.mkdir(parents=True, exist_ok=True)

    # ---- 계측 설치: 어댑터가 import 하기 전에 vendor 모듈을 먼저 잡는다 ----
    import src.controllers.stackelberg_mpc as sm
    TRUE_FAR = sm.mfd_far_cost_to_go
    TRUE_WORKER = sm._stackelberg_candidate_worker
    TRUE_PREFILTER = sm.StackelbergMPCController._prefilter_leader_candidates

    def far_recorder(cfg, state):
        val = float(TRUE_FAR(cfg, state))
        comp = far_components(cfg, state)
        comp["far_true"] = val
        comp["residual"] = val - comp["total"]
        comp["ctx"] = CTX["cur"]
        RECORDS.append(comp)
        return val

    def worker_wrapper(payload):
        return TRUE_WORKER(payload)

    TRUE_FULL = sm.StackelbergMPCController._evaluate_full_candidate

    def full_candidate_wrapper(self, index, action, state, forecast, previous,
                               stage="coarse", incumbent_obj=float("inf"),
                               rollout_abort_obj=float("inf")):
        idx = int(index)
        CTX["cur"] = {"index": idx, "stage": str(stage),
                      "cand_N_P_star": float(action.N_P_star),
                      "cand_N_UF_star": float(action.N_UF_star)}
        if not PAYLOAD_KEEP:
            PAYLOAD_KEEP["cfg"] = self.cfg
            PAYLOAD_KEEP["state"] = copy.deepcopy(state)
            PAYLOAD_KEEP["forecast"] = forecast
            PAYLOAD_KEEP["previous"] = copy.deepcopy(previous)
        n0 = len(RECORDS)
        try:
            res = TRUE_FULL(self, idx, action, state, forecast, previous,
                            stage=stage, incumbent_obj=incumbent_obj,
                            rollout_abort_obj=rollout_abort_obj)
        finally:
            CTX["cur"] = None
        CAND.append({
            "index": idx, "stage": str(stage),
            "cand_N_P_star": float(action.N_P_star), "cand_N_UF_star": float(action.N_UF_star),
            "objective": float(res.objective),
            "far_calls": list(range(n0, len(RECORDS))),
            "control": lever_summary(res.nash.control),
            "objective_terms": {str(k): float(v) for k, v in dict(res.objective_terms).items()},
        })
        CTRL_KEEP.append((idx, res.nash.control.copy()))
        return res

    def prefilter_all(self, candidates, state, forecast, previous, global_scope=False):
        sel, meta = TRUE_PREFILTER(self, candidates, state, forecast, previous, global_scope)
        meta = dict(meta)
        meta["probe_prefilter_overridden"] = 1.0
        return list(range(len(candidates))), meta

    sm.mfd_far_cost_to_go = far_recorder
    sm._stackelberg_candidate_worker = worker_wrapper
    sm.StackelbergMPCController._evaluate_full_candidate = full_candidate_wrapper
    if args.all_candidates:
        sm.StackelbergMPCController._prefilter_leader_candidates = prefilter_all

    # ---- 어댑터 main 을 러너와 같은 인자로 ----
    # 워커(spawn)가 boot["module"] 을 import 해야 하므로 실런과 같은 이름으로 싣는다.
    sys.path.insert(0, str(R / "evaluation/controllers"))
    sp = importlib.util.spec_from_file_location(
        "vissim_stackelberg_adapter", R / "evaluation/controllers/vissim_stackelberg_adapter.py")
    qb = importlib.util.module_from_spec(sp)
    sys.modules["vissim_stackelberg_adapter"] = qb
    sp.loader.exec_module(qb)

    argv = [
        "adapter",
        "--state-json", str(state_json),
        "--out-action-json", str(scratch / ("action_%06d.json" % args.sec)),
        "--out-action-csv", str(scratch / ("action_%06d.csv" % args.sec)),
        "--mapping-json", files["control_mapping"]["path"],
        "--controller", prov["controller"],
        "--detector-mapping-json", str(R / "evaluation/real_world_modi_control_distributed_20260728/detector_local_mapping_distributed_core17legs4f_20260826.json"),
        "--calibration-json", files["calibration"]["path"],
        "--tuning-json", (args.tuning or files["tuning"]["path"]),
    ]
    if prev_json.exists():
        argv += ["--previous-action-json", str(prev_json)]
    sys.argv = argv
    qb.main()

    payload_cfg = PAYLOAD_KEEP.get("cfg")
    cfg_flags = {}
    if payload_cfg is not None:
        m = payload_cfg.mpc
        cfg_flags = {
            "leader_mfd_far_enabled": bool(getattr(m, "leader_mfd_far_enabled", False)),
            "leader_mfd_far_at_d0": bool(getattr(m, "leader_mfd_far_at_d0", False)),
            "leader_mfd_far_state_aware": bool(getattr(m, "leader_mfd_far_state_aware", False)),
            "leader_mfd_far_real_speed": bool(getattr(m, "leader_mfd_far_real_speed", False)),
            "leader_mfd_far_freeflow_offset": bool(getattr(m, "leader_mfd_far_freeflow_offset", False)),
            "leader_mfd_far_g_free": float(getattr(m, "leader_mfd_far_g_free", 0.0)),
            "leader_mfd_far_g_cong": float(getattr(m, "leader_mfd_far_g_cong", 0.0)),
            "leader_mfd_far_g_fw": float(getattr(m, "leader_mfd_far_g_fw", 0.0)),
            "leader_mfd_far_ncrit": float(getattr(m, "leader_mfd_far_ncrit", 0.0)),
            "leader_mfd_far_weight": float(getattr(m, "leader_mfd_far_weight", 1.0)),
            "leader_value_depth": int(getattr(m, "leader_value_depth", 0)),
            "horizon_steps": int(getattr(m, "horizon_steps", 0)),
            "leader_proxy_near_far": bool(getattr(m, "leader_proxy_near_far", False)),
            "T_c_h": float(payload_cfg.simulation.T_c_h),
            "far_ramp_capacity_veh_h": {
                str(k): float(v) for k, v in
                dict(getattr(payload_cfg.network, "far_ramp_capacity_veh_h", {}) or {}).items()},
            "ramp_capacity_veh_h": {
                str(k): float(v) for k, v in dict(payload_cfg.network.ramp_capacity_veh_h).items()},
        }

    # ---- 초기(플랜트) 상태의 far ----
    plant = None
    if payload_cfg is not None and PAYLOAD_KEEP.get("state") is not None:
        plant = far_components(payload_cfg, PAYLOAD_KEEP["state"])

    # ---- 레버 교차 스왑 ----
    sweep = []
    if args.lever_sweep and len(CAND) >= 2 and payload_cfg is not None:
        from src.controllers.rollout_endpoint import evaluate_price_point
        from src.controllers.stackelberg_wu_metered import StackelbergWuMeteredController
        base_ctrl = None
        alt_ctrl = None
        # 목적값 최소 후보 = base, 최대 = alt
        ordered = sorted(CAND, key=lambda r: r["objective"])
        base_i, alt_i = ordered[0]["index"], ordered[-1]["index"]
        for rec, ctrl in CTRL_KEEP:
            if rec == base_i:
                base_ctrl = ctrl
            if rec == alt_i:
                alt_ctrl = ctrl
        if base_ctrl is not None and alt_ctrl is not None:
            spec_owner = sm.StackelbergMPCController(payload_cfg)
            spec = spec_owner._rollout_spec(
                score_mode="leader", far_enabled=True, leader_hinge=True, hinge_forecast=True)
            st = PAYLOAD_KEEP["state"]
            fc = PAYLOAD_KEEP["forecast"]

            def run(tag, ctrl):
                CTX["cur"] = {"sweep": tag}
                n0 = len(RECORDS)
                pt = evaluate_price_point(st.copy(), ctrl, fc, (), spec)
                CTX["cur"] = None
                comp = RECORDS[n0] if len(RECORDS) > n0 else {}
                sweep.append({"tag": tag, "ttt": float(pt.ttt), "objective": float(pt.objective),
                              "far": float(pt.far),
                              "n_u": comp.get("n_u"), "urban": comp.get("urban"),
                              "main": comp.get("main"), "ramp": comp.get("ramp")})

            run("base", base_ctrl)
            run("alt", alt_ctrl)
            for fam in ("green_times", "ramp_metering", "vsl", "offsets",
                        "inflow_outflow_allocation"):
                c = base_ctrl.copy()
                setattr(c, fam, dict(getattr(alt_ctrl, fam)))
                run("base+alt_" + fam, c)

    out = {
        "schema_version": "far-candidate-spread/1",
        "run": args.run, "sim_sec": args.sec,
        "all_candidates": bool(args.all_candidates),
        "cfg": cfg_flags,
        "plant_state_far": plant,
        "candidates": CAND,
        "far_calls": RECORDS,
        "sweep": sweep,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("WROTE %s  far_calls=%d candidates=%d" % (out_path, len(RECORDS), len(CAND)))


CTRL_KEEP = []

if __name__ == "__main__":
    main()
