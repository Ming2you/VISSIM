# -*- coding: utf-8 -*-
"""Ver2 N=21 격자 METANET 재보정 — 정상상태 FD 와 동역학을 **함께** (2026-09-07).

무엇이 왜 필요했나. 2026-09-07 오전까지 우리가 맞춘 것은 평형 관계 V(ρ) 셋(v_free·ρ_cr·a)뿐이고,
속도가 평형으로 **어떻게 이완하는지**(τ·ν·κ)는 2026-08-30 에 **구 4차로 망**에서 맞춘 값이 그대로였다.
합류항 δ 는 어느 config 에도 없어 0(비활성)이었고, 차로감소항 φ 는 vendor 에 아예 없었다.

이 스크립트가 맞추는 것 (2026-08-30 방식 = 한-스텝-앞 예측오차, 실제 플랜트 코드로 전진):
  급 FD    plain4 (v_free, ρ_cr, a) · plain3 (v_free, ρ_cr, a)   ← 램프 없는 셀을 **합쳐서 하나로**
  합류 셀  자체 FD (v_free, ρ_cr, a) + δ_merge                    ← on-ramp 유입이 속도를 떨어뜨리는 항
  차로감소 φ                                                      ← Δλ>0 인 직전 셀(FW_E 12)에만
  동역학   τ · ν · κ

  t 의 21셀 관측 → freeway_step 으로 T_c(150 s) 전진 → t+150 관측과 대조.
  점수 = ρ RMSE/평균 + v RMSE/평균 (무차원 합). **홀드아웃 수요에서도 좋아져야 채택한다.**

전제: 어댑터에 apply_segparams_patch / apply_lanedrop_patch 가 적용돼 있어야 한다.
사용:
  python calibrate_metanet_ver2n21_20260907.py --smoke     # 현행값 점수만
  python calibrate_metanet_ver2n21_20260907.py             # 단계별 좌표하강
"""
import argparse
import copy
import glob
import importlib.util
import io
import json
import math
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
CFG_PATH = R / "evaluation/configs/canon_ver2n21_20260907.json"
MAPPING = R / "evaluation/real_world_modi_control_ver2n21_20260907/control_mapping_ver2n21.json"
PARAMS = R / "outputs/freeway_segment_params_ver2n21_v2_20260908.json"
SPLIT = R / "outputs/freeway_ramp_split_v2_20260907.json"

MAINLINE_BASE = [5544.0, 7920.0, 8316.0, 7128.0, 5544.0, 3960.0]   # Ver2 .inpx (x18 기준)
INTERVAL_SEC = 900.0
FIT_RUNS = [("n21_nocontrol_ver2_x18_20260907", 1.0),
            ("n21_x12_nocontrol_ver2_20260907", 0.6667),
            ("n21_x04_nocontrol_ver2_20260907", 0.2222)]
HOLDOUT_RUNS = [("n21_x15_nocontrol_ver2_20260907", 0.8333),
                ("n21_x08_nocontrol_ver2_20260907", 0.4444)]

PLAIN4 = [("FW_E", i) for i in range(2, 8)]
PLAIN3 = [("FW_W", i) for i in range(1, 5)]


def load_boundary(tag):
    """실현된 경계조건 (150 s 창). 요구 수요가 아니라 **실제로 들어온 유량**이다 —
    이 망은 진입이 막혀 x18 FW_E 는 첨두 요구 8316 중 중앙 4032 만 들어온다(2026-09-08 실측).
    요구치를 먹이면 상류가 과충전되고 그 오차를 τ·κ·δ 가 흡수해 문헌과 동떨어진 값이 나온다."""
    bc = {}
    with io.open(R / ("outputs/fd_ver2_20260907/boundary_%s.csv" % tag), encoding="utf-8") as f:
        import csv as _csv
        for r in _csv.DictReader(f):
            t = float(r["t_start"])
            bc.setdefault(t, {"mainline": {}, "ramp": {}})[r["kind"]][r["key"]] = float(r["veh_h"])
    return bc


def mainline_vph(sim_sec, mult):
    idx = min(int(sim_sec // INTERVAL_SEC), len(MAINLINE_BASE) - 1)
    return MAINLINE_BASE[idx] * mult


def load_module(path, name):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def build_param_table(base_params, theta, merge_cells, arm):
    """theta 를 42셀 파라미터 표로 편다.

    arm="plain"  : **모든 셀이 급 대표 FD**(차로수별) 하나를 쓴다. 램프 셀의 속도 결손은 전적으로 δ 가,
                   차로감소는 φ 가 설명해야 한다 — 파라미터가 적고 물리적이며, 램프 유입이 0 이면
                   자동으로 평지로 돌아간다. 사용자 제안(2026-09-07).
    arm="cell"   : 산출물의 **셀별 FD** 를 쓰고 δ·φ 를 그 위에 얹는다(램프 셀은 배율로 미세조정).
    두 팔의 홀드아웃 점수를 대조해 어느 쪽이 실제로 VISSIM 을 잘 재현하는지 판정한다."""
    tbl = {"FW_E": [], "FW_W": []}
    for link in ("FW_E", "FW_W"):
        for i in range(21):
            rec = dict(base_params["segments"]["%s_S%d" % (link, i)])
            rec.setdefault("q_cap", rec.get("q_cap_veh_h_lane", 0.0))
            lanes = int(rec["lanes"])
            key = (link, i)
            pre = "p4_" if lanes >= 4 else "p3_"
            if arm == "plain":
                rec["v_free"] = theta[pre + "vf"]
                rec["rho_crit"] = theta[pre + "kc"]
                rec["metanet_a_m"] = theta[pre + "a"]
            elif arm == "mid":
                # 중간안 1: 급 형상(ρ_cr·a) 공용 + **합류 셀만** v_free 를 실측으로.
                #   적합 파라미터는 A 와 같고, 합류 셀 v_free 는 맞추는 값이 아니라 재는 값이다.
                rec["rho_crit"] = theta[pre + "kc"]
                rec["metanet_a_m"] = theta[pre + "a"]
                rec["v_free"] = float(rec.get("v_free_meas", rec["v_free"])) if key in merge_cells else theta[pre + "vf"]
            elif arm == "mid2":
                # 중간안 2: 급 형상 공용 + **모든 셀** v_free 를 실측으로.
                #   v_free 는 저밀도 속도로 셀마다 직접 재는 값이고, ρ_cr·a 만 급이 공유한다.
                rec["rho_crit"] = theta[pre + "kc"]
                rec["metanet_a_m"] = theta[pre + "a"]
                rec["v_free"] = float(rec.get("v_free_meas", rec["v_free"]))
            elif key in PLAIN4 or key in PLAIN3:
                rec["v_free"] = theta[pre + "vf"]
                rec["rho_crit"] = theta[pre + "kc"]
                rec["metanet_a_m"] = theta[pre + "a"]
            elif key in merge_cells:
                rec["v_free"] = rec["v_free"] * theta["merge_vf_scale"]
                rec["rho_crit"] = rec["rho_crit"] * theta["merge_kc_scale"]
                rec["metanet_a_m"] = theta["merge_a"]
            tbl[link].append({k: float(rec[k]) for k in ("v_free", "rho_crit", "metanet_a_m")})
    return tbl


def score(pairs, cfg, qb, freeway_step, ControlAction, DemandStep, theta, base_params, merge_cells, ramp_vph, arm):
    net = cfg.network
    net.metanet_tau_h = theta["tau_sec"] / 3600.0
    if hasattr(net, "metanet_tau_sec"):
        net.metanet_tau_sec = theta["tau_sec"]
    net.metanet_nu_km2_h = theta["nu"]
    net.metanet_kappa_veh_km_lane = theta["kappa"]
    net.metanet_delta_merge = theta["delta"]
    setattr(net, "freeway_lane_drop_phi", theta["phi"])
    setattr(net, "freeway_segment_params", build_param_table(base_params, theta, merge_cells, arm))

    qb._FW_SEG_CTX_STATE["lane_drop_fired"] = 0
    dr = dv = sr = sv = 0.0
    cnt = 0
    for st0, obs, t, mult in pairs:
        st = copy.deepcopy(st0)
        control = ControlAction(
            ramp_metering={r: float(net.ramp_capacity_veh_h[r]) for r in net.ramps},
            vsl={lk: float(net.v_free) for lk in net.freeway_links},
            green_times={}, offsets={}, inflow_outflow_allocation={})
        if isinstance(mult, dict):
            fw_in = {lk: float(mult["mainline"].get(lk, 0.0)) for lk in net.freeway_links}
            rp_in = {r: float(mult["ramp"].get(r, ramp_vph.get(r, 0.0))) for r in net.ramps}
        else:
            fw_in = {lk: mainline_vph(t, mult) for lk in net.freeway_links}
            rp_in = dict(ramp_vph)
        demand = DemandStep(freeway_mainline=fw_in, urban_boundary={}, ramp_arrival=rp_in)
        try:
            freeway_step(st, control, demand, cfg)
        except Exception:
            return None
        # 조용한 no-op 방지. φ>0 인데 차로감소항이 한 번도 안 걸렸으면 배선이 끊긴 것이다
        # (2026-09-08 실제 사고: 문맥 해제를 항 계산보다 위에 둬서 Δλ 가 늘 0 이었다).
        if theta["phi"] > 0.0 and int(qb._FW_SEG_CTX_STATE.get("lane_drop_fired", 0)) == 0:
            raise RuntimeError("차로감소항이 발화하지 않았다 — 배선 확인 필요 (phi=%.3f)" % theta["phi"])
        for link in net.freeway_links:
            rows = obs.get(link) or []
            for i, row in enumerate(rows):
                if row is None or i >= len(st.freeway_density[link]):
                    continue
                ro, vo = row
                rp = float(st.freeway_density[link][i])
                vp = float(st.freeway_speed[link][i])
                if not (math.isfinite(rp) and math.isfinite(vp)):
                    return None
                dr += (rp - ro) ** 2
                dv += (vp - vo) ** 2
                sr += ro
                sv += vo
                cnt += 1
    if cnt == 0:
        return None
    rmse_r, rmse_v = math.sqrt(dr / cnt), math.sqrt(dv / cnt)
    mr, mv = sr / cnt, sv / cnt
    return {"rmse_rho": rmse_r, "rmse_speed": rmse_v, "mean_rho": mr, "mean_speed": mv,
            "score": rmse_r / max(mr, 1e-9) + rmse_v / max(mv, 1e-9), "n": cnt}


def load_pairs(run, mult, qb, cfg, TrafficState, dm, cal, bc=None, t0=900.0):
    files = sorted(glob.glob(str(R / "evaluation/runs" / run / "decisions_*/state_*.json")))
    sjs = []
    for f in files:
        sj = json.loads(Path(f).read_text(encoding="utf-8"))
        sjs.append((float(sj.get("sim_sec") or 0.0), sj))
    sjs.sort(key=lambda x: x[0])
    pairs = []
    tc = cfg.simulation.T_c_h * 3600.0
    for i in range(len(sjs) - 1):
        t, sj = sjs[i]
        t2, sj2 = sjs[i + 1]
        if t < t0 or abs((t2 - t) - tc) > 1.0:
            continue
        st = qb.traffic_state_from_vissim(sj, cfg, TrafficState, detector_mapping=dm, calibration=cal)
        obs = {}
        for link, arr in (sj2.get("freeway_segments") or {}).items():
            rows = []
            for s in arr:
                c = float(s.get("count") or 0.0)
                L = float(s.get("length_km") or 0.0)
                n = float(s.get("lanes") or 0.0)
                ss = float(s.get("speed_sum") or 0.0)
                rows.append((c / (L * n), ss / c) if (c > 0 and L > 0 and n > 0) else None)
            obs[link] = rows
        w = bc.get(float(int(t // 150.0) * 150)) if bc else None
        pairs.append((st, obs, t, mult if w is None else w))
    return pairs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--out", default="outputs/metanet_calibration_ver2n21_20260907")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.path.insert(0, str(R))
    sys.path.insert(0, str(R / "vendor/NumSim-mine"))
    sys.path.insert(0, str(R / "scripts"))
    sys.path.insert(0, str(R / "evaluation/controllers"))
    qb = load_module(R / "evaluation/controllers/vissim_stackelberg_adapter.py", "qb")
    import offline_harness_20260904 as OH
    from src.models.state import ControlAction, TrafficState
    from src.models.demand import DemandStep
    from src.models.metanet import freeway_step

    base_params = json.load(io.open(PARAMS, encoding="utf-8"))
    split = json.load(io.open(SPLIT, encoding="utf-8"))
    merge_cells = {(r["direction"], r["segment_index"]) for r in split["on_ramps"]}
    mapping = json.load(io.open(MAPPING, encoding="utf-8"))

    first_run = FIT_RUNS[0][0]
    d = R / "evaluation/runs" / first_run / ("decisions_%s" % first_run)
    cfg, st, sj, meta, dm, cal, tun = OH.build(
        qb, TrafficState, str(CFG_PATH), str(d / "state_004500.json"), str(d / "action_004350.json"))
    qb.install_freeway_segment_lanes(cfg, tun, mapping)
    if hasattr(qb, "install_freeway_lane_drop"):
        qb.install_freeway_lane_drop(cfg, tun)
    qb.install_freeway_segment_runtime(cfg)

    # Ver2 실측 합류유량 (fzp 고유차량 계수, t>=900, x12/x18 평균). 구 망 기준 2026-08-30 값
    # (R_D_W 752 · R_F_W 1212 · R_D_E 938 · R_F_E 555)과 다르다 — 서측이 크게 늘었다.
    # δ 가 곧 q_ramp 에 곱해지므로 이 입력이 틀리면 δ 가 그 오차를 흡수한다.
    ramp_vph = {"R_D_W": 1024.0, "R_F_W": 1639.0, "R_D_E": 968.0, "R_F_E": 496.0}
    ramp_vph = {r: ramp_vph.get(r, 900.0) for r in cfg.network.ramps}
    print("램프 도착[veh/h]:", {k: round(v) for k, v in ramp_vph.items()})

    fit_pairs, hold_pairs = [], []
    tag_of = {FIT_RUNS[0][0]: "x18", FIT_RUNS[1][0]: "x12", FIT_RUNS[2][0]: "x04",
              HOLDOUT_RUNS[0][0]: "x15", HOLDOUT_RUNS[1][0]: "x08"}
    for run, mult in FIT_RUNS:
        p = load_pairs(run, mult, qb, cfg, TrafficState, dm, cal, load_boundary(tag_of[run]))
        print("  적합 %-38s 쌍 %d" % (run, len(p)))
        fit_pairs += p
    for run, mult in HOLDOUT_RUNS:
        p = load_pairs(run, mult, qb, cfg, TrafficState, dm, cal, load_boundary(tag_of[run]))
        print("  홀드 %-38s 쌍 %d" % (run, len(p)))
        hold_pairs += p

    p4 = base_params["plain_class"]["4"]
    p3 = base_params["plain_class"]["3"]
    theta0 = {"p4_vf": p4["v_free"], "p4_kc": p4["rho_crit"], "p4_a": p4["metanet_a_m"],
              "p3_vf": p3["v_free"], "p3_kc": p3["rho_crit"], "p3_a": p3["metanet_a_m"],
              "merge_vf_scale": 1.0, "merge_kc_scale": 1.0, "merge_a": 1.5,
              "tau_sec": 7.0, "nu": 48.0, "kappa": 25.0, "delta": 0.0, "phi": 0.0}
    sc = lambda th, pr, arm="cell": score(pr, cfg, qb, freeway_step, ControlAction, DemandStep, th,
                                          base_params, merge_cells, ramp_vph, arm)
    base_fit, base_hold = sc(theta0, fit_pairs, "cell"), sc(theta0, hold_pairs, "cell")
    print("\n현행값  적합 %.4f (ρ %.2f / v %.2f) · 홀드 %.4f" %
          (base_fit["score"], base_fit["rmse_rho"], base_fit["rmse_speed"], base_hold["score"]))
    if args.smoke:
        return

    # 격자는 넉넉히. 1차 시도(2026-09-07)에서 v_free·ν·κ 가 경계에 붙어 A/B 판정을 못 믿게 됐다 —
    # 경계에 붙은 값은 최적이 아니라 "더 갈 데가 없었다"는 뜻이다.
    STAGES = [
        ("급 FD 4차로", [("p4_vf", [100, 108, 115, 120, 123, 128, 133]),
                         ("p4_kc", [24, 28, 32, 36, 40, 45, 52]),
                         ("p4_a", [0.9, 1.2, 1.5, 1.8, 2.2, 2.8])]),
        ("급 FD 3차로", [("p3_vf", [100, 108, 115, 120, 122, 128, 133]),
                         ("p3_kc", [20, 24, 28, 32, 36, 42]),
                         ("p3_a", [0.9, 1.3, 1.7, 2.0, 2.4, 2.8])]),
        ("동역학", [("tau_sec", [3, 5, 7, 10, 15, 20, 30, 45, 60]),
                    ("nu", [5, 12, 20, 35, 48, 65, 90, 120]),
                    ("kappa", [4, 8, 12, 18, 25, 35, 50])]),
        ("합류 δ + 셀 FD", [("delta", [0.0, 1.0, 2.0, 5.0, 10.0, 17.3, 25.0, 40.0]),
                            ("merge_vf_scale", [0.7, 0.85, 1.0, 1.15, 1.3]),
                            ("merge_kc_scale", [0.5, 0.7, 1.0, 1.3, 1.6]),
                            ("merge_a", [1.0, 1.5, 2.0, 2.8])]),
        ("차로감소 φ", [("phi", [0.0, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0])]),
    ]
    # 문헌 제약 격자 (Messmer & Papageorgiou 1990 · Kotsialos et al. 2002 전형 범위).
    # 자유 적합이 문헌 밖으로 나가면 그것은 결과가 아니라 **증상**이다 — 다른 오차를 그 축이 흡수하고 있다는.
    # 이 격자로 홀드아웃이 얼마나 나빠지는지가 판정이다: 거의 안 나빠지면 문헌값을 쓰면 되고,
    # 크게 나빠지면 아직 못 찾은 오차원이 있다는 뜻이다.
    LIT_STAGES = [
        ("급 FD 4차로", [("p4_vf", [115, 120, 123, 128]), ("p4_kc", [25, 28, 31, 35]),
                         ("p4_a", [1.4, 1.6, 1.8, 2.0])]),
        ("급 FD 3차로", [("p3_vf", [115, 120, 122, 128]), ("p3_kc", [25, 28, 31, 35]),
                         ("p3_a", [1.4, 1.6, 1.8, 2.0])]),
        ("동역학", [("tau_sec", [15, 18, 20, 25]), ("nu", [30, 40, 50, 60]),
                    ("kappa", [10, 15, 20, 30, 40])]),
        ("합류 δ + 셀 FD", [("delta", [0.005, 0.0122, 0.05, 0.1, 0.3]),
                            ("merge_vf_scale", [0.85, 1.0, 1.15]),
                            ("merge_kc_scale", [0.7, 1.0, 1.3]), ("merge_a", [1.4, 1.7, 2.0])]),
        ("차로감소 φ", [("phi", [0.0, 0.5, 1.0, 1.5, 2.0, 3.0])]),
    ]

    results = {}
    ARMS = [("plain", "A 평지 FD 하나 + δ + φ"), ("cell", "B 셀별 FD + δ + φ"),
            ("mid", "C 급형상 + 합류셀 실측 v_free + δ + φ"), ("mid2", "D 급형상 + 전셀 실측 v_free + δ + φ"),
            ("cell_lit", "B-lit 셀별 FD (문헌 제약)"), ("mid2_lit", "D-lit 전셀 실측 v_free (문헌 제약)")]
    import os as _os
    _only = [a.strip() for a in (_os.environ.get("RW_CALIB_ARMS", "") or "").split(",") if a.strip()]
    if _only:
        ARMS = [x for x in ARMS if x[0] in _only]
    for arm, arm_label in ARMS:
        theta = dict(theta0)
        struct = arm.replace("_lit", "")
        use = LIT_STAGES if arm.endswith("_lit") else STAGES
        drop = [] if struct == "cell" else ["merge_"]
        if struct in ("mid2",):
            drop += ["p4_vf", "p3_vf"]        # 전 셀 실측 v_free 를 쓰므로 급 v_free 는 의미가 없다
        stages = [(n, [ax for ax in axes if not any(ax[0].startswith(d) for d in drop)]) for n, axes in use]
        r0 = sc(theta, fit_pairs, struct)
        best = r0["score"]
        print(chr(10) + "--- %s --- 시작 점수 %.4f" % (arm_label, best))
        for rnd in range(4):
            for stage_name, axes in stages:
                for key, values in axes:
                    cur = theta[key]
                    cand = []
                    for v in values:
                        th = dict(theta)
                        th[key] = v
                        r = sc(th, fit_pairs, struct)
                        if r:
                            cand.append((r["score"], v))
                    if not cand:
                        continue
                    cand.sort()
                    if cand[0][0] < best - 1e-9:
                        best, theta[key] = cand[0][0], cand[0][1]
                        print("  R%d %-14s %-16s %s → %s   점수 %.4f" % (rnd + 1, stage_name, key, cur, theta[key], best))
        results[arm] = {"label": arm_label, "theta": dict(theta),
                        "fit": sc(theta, fit_pairs, struct), "hold": sc(theta, hold_pairs, struct)}
        print("  %s  적합 %.4f · 홀드 %.4f" % (arm_label, results[arm]["fit"]["score"], results[arm]["hold"]["score"]))
    print(chr(10) + "=== 팔 비교 (홀드아웃 기준) ===")
    NP = {"plain": 11, "cell": 14, "mid": 11, "mid2": 9, "cell_lit": 14, "mid2_lit": 9}
    for arm in [a for a, _ in ARMS]:
        if arm not in results:
            continue
        r = results[arm]
        print("  %-34s 홀드 %.4f (ρ RMSE %.2f · v RMSE %.2f)  적합 파라미터 %d개"
              % (r["label"], r["hold"]["score"], r["hold"]["rmse_rho"], r["hold"]["rmse_speed"], NP[arm]))
    winner = min(results, key=lambda a: results[a]["hold"]["score"])
    print("  → %s 최우수" % results[winner]["label"])
    theta = results[winner]["theta"]
    fit_r, hold_r = results[winner]["fit"], results[winner]["hold"]
    print("\n=== 결과 ===")
    print("  적합  %.4f → %.4f  (%+.1f%%)" % (base_fit["score"], fit_r["score"],
                                             100 * (fit_r["score"] / base_fit["score"] - 1)))
    print("  홀드  %.4f → %.4f  (%+.1f%%)  ← 이게 좋아져야 진짜다" %
          (base_hold["score"], hold_r["score"], 100 * (hold_r["score"] / base_hold["score"] - 1)))
    print("  ρ RMSE %.2f → %.2f · v RMSE %.2f → %.2f" %
          (base_hold["rmse_rho"], hold_r["rmse_rho"], base_hold["rmse_speed"], hold_r["rmse_speed"]))
    for k in sorted(theta):
        mark = "" if abs(theta[k] - theta0[k]) > 1e-9 else "   (변화 없음)"
        print("  %-16s %s → %s%s" % (k, round(theta0[k], 4), round(theta[k], 4), mark))
    out = {"schema": "metanet_calibration_v2n21", "arm_results": {k: {"label": v["label"], "theta": v["theta"],
           "fit_score": v["fit"]["score"], "hold_score": v["hold"]["score"]} for k, v in results.items()},
           "winner": winner, "fit_runs": FIT_RUNS, "holdout_runs": HOLDOUT_RUNS,
           "theta0": theta0, "theta": theta, "fit_before": base_fit, "fit_after": fit_r,
           "holdout_before": base_hold, "holdout_after": hold_r,
           "merge_cells": ["%s_S%d" % k for k in sorted(merge_cells)]}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    io.open(args.out + ".json", "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
    print("\n→ %s.json" % args.out)


if __name__ == "__main__":
    main()
