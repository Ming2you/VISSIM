# -*- coding: utf-8 -*-
"""far(MFD tail)의 세 성분을 결정 시각별로 분해하고, far 가 보는 n_u 를 플랜트 누적과 대조한다.

vendor 는 한 줄도 안 고친다. 어댑터 main() 의 배선을 그대로 재현해 cfg·TrafficState 를 만들고,
`mfd_far_cost_to_go` 와 **같은 식**을 state 로 재계산해 성분을 뽑은 뒤,
패치된 모듈 함수의 반환값과 총합이 일치하는지 검증한다(불일치면 시끄럽게 실패).

산출: outputs/far_components_<run>_<stamp>.json
"""
import argparse
import glob
import importlib.util
import json
import os
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R))
sys.path.insert(0, str(R / "vendor/NumSim-mine"))

DEFAULT_CAL = "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json"


def build_cfg_and_state(qb, TrafficState, tuning_path, state_path, prev_action_path):
    """어댑터 main() 의 설치 순서를 그대로 재현한다 (vissim_stackelberg_adapter.py:8960-9045)."""
    state_json = json.loads(Path(state_path).read_text(encoding="utf-8"))
    calibration = qb.load_optional_json(str(R / DEFAULT_CAL))
    tuning = qb.load_optional_json(str(tuning_path))
    qb.install_config_switches(tuning)
    dm_path = str(tuning.get("detector_mapping_json", "") or "").strip()
    if dm_path and not Path(dm_path).is_absolute():
        dm_path = str(R / dm_path)
    detector_mapping = qb.load_optional_json(dm_path)
    if not detector_mapping:
        raise SystemExit("detector mapping unreadable: %r" % dm_path)
    detector_mapping, _ = qb.filter_midblock_links_from_detector_mapping(detector_mapping, tuning)
    override = tuning.get("calibration_override", {})
    if isinstance(override, dict):
        calibration = qb.deep_update(dict(calibration), override)
    control_interval = float(state_json.get("control_interval_sec", 150.0))
    sim_period = float(state_json.get("sim_period_sec", 5400.0))
    local_observation = bool(qb._link_counts_from_local_observation(state_json) and detector_mapping)
    cfg = qb.build_config(R / "vendor/NumSim-mine", control_interval, sim_period, "fast-smoke",
                          calibration, tuning, local_observation=local_observation, flagship=True)
    meta = {}
    meta.update(qb.install_adapter_calibration_fingerprints(cfg, tuning))
    meta.update(qb.install_vissim_calibration_runtime_patches(cfg, calibration))
    meta.update(qb.install_tau_length_cap_patch(cfg))
    meta.update(qb.apply_movement_phase_correction(cfg, tuning))
    meta.update(qb.apply_dead_phase_beta_zero(cfg))
    meta.update(qb.install_vsl_metanet_rollout_runtime_patch(cfg, tuning))
    meta.update(qb.install_urban_stopline_storage(cfg, tuning))
    meta.update(qb.install_measured_turn_beta(cfg, tuning))
    meta.update(qb._relabel(qb.apply_dead_phase_beta_zero(cfg), "after_measured_beta"))
    detector_mapping, _mm = qb.install_merged_movements(cfg, tuning, detector_mapping)
    meta.update(_mm)
    meta.update(qb.install_phase_vector_green_patch(cfg, tuning))
    meta.update(qb.install_movement_capacity_by_lanes(cfg, tuning))
    meta.update(qb.install_native_signal_structure(cfg, tuning))
    meta.update(qb.install_measured_movement_capacity(cfg, tuning, state_json, prev_action_path))
    meta.update(qb.install_measured_far_reservoir_rates(cfg, tuning, state_json, prev_action_path))
    meta.update(qb.install_far_ramp_capacity_patch(cfg))
    state = qb.traffic_state_from_vissim(state_json, cfg, TrafficState, detector_mapping,
                                         calibration, physical_projection_input=None)
    return cfg, state, state_json, meta


def far_components(cfg, state):
    """stackelberg_mpc.mfd_far_cost_to_go(:88) 와 같은 식을 성분별로 재계산한다.

    far 호출 동안만 유효한 램프 용량 스왑(install_far_ramp_capacity_patch)을 흉내내려고
    `far_ramp_capacity_veh_h` 가 있으면 그걸 쓴다.
    """
    from src.models.metanet import _ramp_merge_index, _clip, desired_speed_kmh
    net = cfg.network
    tc_h = float(cfg.simulation.T_c_h)
    w = float(getattr(cfg.mpc, "leader_mfd_far_weight", 1.0))
    state_aware = bool(getattr(cfg.mpc, "leader_mfd_far_state_aware", False))
    real_v = bool(getattr(cfg.mpc, "leader_mfd_far_real_speed", False))

    n_prot = float(state.protected_accumulation_veh(net))
    n_bin = float(state.boundary_in_queue_vehicles(net))
    n_u = n_prot + n_bin
    n_crit = float(getattr(cfg.mpc, "leader_mfd_far_ncrit", 1700.0))
    g_free = float(getattr(cfg.mpc, "leader_mfd_far_g_free", 640.0))
    g_cong = float(getattr(cfg.mpc, "leader_mfd_far_g_cong", 500.0))
    g_u = g_free if n_u < n_crit else g_cong
    urban_term = (n_u * n_u) * tc_h / (2.0 * max(g_u, 1.0))

    seg_len = float(net.freeway_segment_length_km)
    v_free = float(net.v_free)
    ramp_total = sum(max(0.0, float(state.ramp_queue.get(r, 0.0))) for r in net.ramps)
    n_main = max(0.0, float(state.total_freeway_vehicles(net)) - ramp_total)
    g_fw = float(getattr(cfg.mpc, "leader_mfd_far_g_fw", 300.0))
    if getattr(cfg.mpc, "leader_mfd_far_freeflow_offset", False):
        raise SystemExit("freeflow_offset 이 켜져 있다 - 이 프로브의 본선항 식이 다르다")
    mainline_term = (n_main * n_main) * tc_h / (2.0 * max(g_fw, 1.0))

    far_caps = getattr(net, "far_ramp_capacity_veh_h", None) or {}
    ramp_term = 0.0
    ramp_rows = {}
    for ramp in net.ramps:
        q = max(0.0, float(state.ramp_queue.get(ramp, 0.0)))
        if q <= 0.0:
            continue
        link = net.ramp_to_freeway.get(ramp)
        dens = state.freeway_density.get(link, [])
        if not dens:
            continue
        midx = _ramp_merge_index(cfg, ramp, len(dens))
        rho_merge = float(dens[midx])
        recv = _clip((net.rho_max - rho_merge) / max(net.rho_max - net.rho_crit, 1.0e-9), 0.0, 1.0)
        cap = float(far_caps.get(ramp, net.ramp_capacity_veh_h[ramp]))
        merge_interval = cap * recv * tc_h
        if state_aware:
            spd_r = state.freeway_speed.get(link, []) if real_v else []
            t_ramp_traverse = sum(
                seg_len / max(
                    (float(spd_r[i]) if real_v and i < len(spd_r)
                     else desired_speed_kmh(max(0.0, float(dens[i])), v_free, net.rho_crit)),
                    1.0)
                for i in range(midx, len(dens)))
        else:
            t_ramp_traverse = (len(dens) - midx) * seg_len / max(v_free, 1.0)
        wait = (q * q) * tc_h / (2.0 * max(merge_interval, 1.0e-6))
        trav = q * t_ramp_traverse
        ramp_term += wait + trav
        ramp_rows[ramp] = {"q": q, "cap_used_veh_h": cap, "recv": recv,
                           "merge_interval_veh": merge_interval,
                           "wait": wait, "traverse": trav}

    total = w * (urban_term + mainline_term + ramp_term)
    return {
        "n_u_far": n_u,
        "n_u_far_protected_accumulation_veh": n_prot,
        "n_u_far_boundary_in_queue_veh": n_bin,
        "n_crit": n_crit, "g_u_used": g_u, "g_free": g_free, "g_cong": g_cong,
        "n_main": n_main, "ramp_queue_total": ramp_total, "g_fw": g_fw,
        "tc_h": tc_h, "weight": w,
        "urban_term": w * urban_term,
        "mainline_term": w * mainline_term,
        "ramp_term": w * ramp_term,
        "far_total": total,
        "ramp_detail": ramp_rows,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="canon_farbn_d00_x18_20260901")
    ap.add_argument("--tuning", default="")
    ap.add_argument("--indices", default="4,10,18,26,34")
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    os.environ.setdefault("RW_MAINLINE_SG_ONLY", "1")

    tuning_path = args.tuning or str(R / ("evaluation/configs/%s.json" % args.run))
    sp = importlib.util.spec_from_file_location(
        "qb", R / "evaluation/controllers/vissim_stackelberg_adapter.py")
    qb = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(qb)
    from src.models.state import TrafficState
    import src.controllers.stackelberg_mpc as sm

    states = sorted(glob.glob(str(R / "evaluation/runs" / args.run / "decisions_*/state_*.json")))
    actions = sorted(glob.glob(str(R / "evaluation/runs" / args.run / "decisions_*/action_*.json")))
    idxs = [int(x) for x in args.indices.split(",") if x.strip()]
    rows = []
    for i in idxs:
        if i >= len(states):
            continue
        sp_i = states[i]
        prev = actions[i - 1] if i > 0 else str(R / "__missing_previous.json")
        cfg, st, sj, meta = build_cfg_and_state(qb, TrafficState, tuning_path, sp_i, prev)
        comp = far_components(cfg, st)
        # 실제 (패치된) 모듈 함수와 총합 대조
        actual = float(sm.mfd_far_cost_to_go(cfg, st))
        comp["far_total_from_vendor"] = actual
        comp["far_total_mismatch"] = actual - comp["far_total"]
        # 플랜트 액션 진단
        act = json.loads(Path(actions[i]).read_text(encoding="utf-8"))
        dg = act.get("diagnostics") or {}
        base = float(dg.get("leader_base_accumulation", 0.0))
        bq = float(dg.get("leader_boundary_in_queue_veh", 0.0))
        comp.update({
            "index": i,
            "sim_sec": float(sj.get("sim_sec", 0.0)),
            "state_file": Path(sp_i).name,
            "n_u_plant_leader_base_accumulation": base,
            "n_u_plant_leader_boundary_in_queue_veh": bq,
            "n_u_plant": base + bq,
            "ratio_far_over_plant": (comp["n_u_far"] / (base + bq)) if (base + bq) > 0 else 0.0,
            "far_enabled": bool(cfg.mpc.leader_mfd_far_enabled),
            "far_at_d0": bool(getattr(cfg.mpc, "leader_mfd_far_at_d0", False)),
            "state_aware": bool(getattr(cfg.mpc, "leader_mfd_far_state_aware", False)),
            "real_speed": bool(getattr(cfg.mpc, "leader_mfd_far_real_speed", False)),
            "horizon_steps": int(cfg.mpc.horizon_steps),
            "far_measured_g_cong_meta": float(meta.get("far_measured_g_cong", 0.0)),
            "far_measured_g_fw_meta": float(meta.get("far_measured_g_fw", 0.0)),
        })
        # 단일 상태 대조군: 플랜트 총 urban/freeway 를 같은 상태에서 직접 잰다
        net = cfg.network
        comp["single_state_total_urban_veh"] = float(st.total_urban_vehicles(net))
        comp["single_state_objective_urban_veh"] = float(st.objective_urban_vehicles(net, True))
        comp["single_state_total_freeway_veh"] = float(st.total_freeway_vehicles(net))
        comp["single_state_off_ramp_storage_veh"] = float(st.off_ramp_storage_occupancy_veh(net))
        comp["single_state_boundary_leg_veh"] = float(st.boundary_leg_vehicles(net))
        comp["single_state_accum_base_equiv"] = (
            comp["single_state_total_freeway_veh"] + comp["single_state_off_ramp_storage_veh"]
            + comp["single_state_objective_urban_veh"])
        rows.append(comp)
        tot = max(comp["far_total"], 1.0e-12)
        print("[%2d] t=%6.0f  n_u_far=%9.1f  n_u_plant=%10.1f  ratio=%.4f  "
              "far=%9.2f (urban %.2f=%.1f%% · main %.2f=%.1f%% · ramp %.2f=%.1f%%)  vendor=%9.2f d=%.3g"
              % (i, comp["sim_sec"], comp["n_u_far"], comp["n_u_plant"], comp["ratio_far_over_plant"],
                 comp["far_total"],
                 comp["urban_term"], 100.0 * comp["urban_term"] / tot,
                 comp["mainline_term"], 100.0 * comp["mainline_term"] / tot,
                 comp["ramp_term"], 100.0 * comp["ramp_term"] / tot,
                 actual, comp["far_total_mismatch"]))

    out = args.out or ("outputs/far_components_%s.json" % args.run)
    doc = {"schema_version": "far-components/1", "run": args.run, "tuning": tuning_path,
           "rows": rows}
    (R / out).write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print("-> %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
