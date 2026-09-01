# -*- coding: utf-8 -*-
"""METANET 동역학 4항(tau · nu · kappa · delta_merge)을 한-스텝-앞 예측오차로 적합한다.

왜 (2026-08-30).

FD 재적합(2026-08-28)은 **평형 관계** V(rho) 를 이루는 셋만 우리 자료로 맞췄다.

    v_free 120.0 · rho_crit 27.0 · a 1.6        config (우리가 적합)
    ------------------------------------------------------------
    metanet_tau_h              0.005 (18 s)     **vendor 기본값**
    metanet_nu_km2_h            65.0            **vendor 기본값**
    metanet_kappa_veh_km_lane   40.0            **vendor 기본값**
    metanet_delta_merge          0.0            0 (비활성)

속도가 평형으로 **어떻게 이완하는지**는 한 번도 우리 망을 본 적이 없다. 그리고 증상이 이미 있다 —
"plant 롤아웃이 발산한다(tau 무상한이 주범)", "plant 충실도가 세그먼트 해상도에서 15% 오차".
세그먼트 해상도는 정확히 이 항들이 지배하는 자리다.

delta_merge 를 대수적으로 역산하려던 시도는 실패했다(2026-08-30, 문헌값의 970배가 나왔다).
이유는 셋이다: (1) 관측이 150 s 간격이라 한-스텝 갱신식에 못 넣는다, (2) VISSIM 은 METANET 이
아니므로 "참 delta" 가 아니라 **METANET 이 VISSIM 을 가장 잘 재현하는 delta** 를 찾아야 한다,
(3) tau·nu·kappa 가 틀린 채로 delta 만 떼면 다른 항의 오차를 delta 가 흡수한다. 그래서 **함께**
적합한다.

방법.

    t 의 관측 상태(세그먼트 16개 밀도·속도) -> 실제 플랜트 코드 `freeway_step` 으로 150 s 전진
    -> t+150 s 예측을 t+150 s 관측과 대조. (T_c=150 s = T_f 10 s x K_cf 15 라 정확히 맞는다.)

    본선 유입은 .inpx 의 구간별 volume 을 그대로 쓴다(link 26 -> FW_W, 74 -> FW_E).
    램프 유입은 **실측**을 쓴다(.fzp 고유차량 계수, ramp_arrival_calibration_20260830.json) —
    모델 forecast 는 실측의 39% 라 그 오차를 동역학 항이 흡수하게 두면 안 된다.
    제어는 무제어(VSL=v_free · 미터링=용량)이고 자료도 무제어 런이라 컨트롤러 간섭이 없다.

    점수 = 밀도 RMSE/평균 + 속도 RMSE/평균 (무차원 합)

**홀드아웃으로 검정한다.** 적합에 안 쓴 수요 배율에서도 좋아져야 진짜다 — FD 때와 같은 규약.

사용:
  python scripts/calibrate_metanet_dynamics_20260830.py --smoke      # 현행값 오차만
  python scripts/calibrate_metanet_dynamics_20260830.py              # 격자 적합
"""
import argparse
import copy
import glob
import io
import json
import math
import re
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R))
sys.path.insert(0, str(R / "vendor/NumSim-mine"))

# 실측 램프 유입 [veh/h] — outputs/ramp_arrival_calibration_20260830.json
RAMP_VPH = {"R_D_W": 752.0, "R_F_W": 1212.0, "R_D_E": 938.0, "R_F_E": 555.0}
# .inpx 본선 구간유량 (x1.0). link 26 -> FW_W, 74 -> FW_E. 둘이 같은 프로파일이다.
MAINLINE_BASE = [3080.0, 4400.0, 4620.0, 3960.0, 3080.0, 2200.0]
INTERVAL_SEC = 900.0

# 램프 합류 세그먼트 보정 (2026-08-30).
# 생성기가 R_F_W 를 셀 4 로 뽑는데 실측은 셀 5 다. 커넥터가 둘인데(10646 · 10644)
# 각각 체인 6072.6 m · 6774.3 m 에 붙고 셀 5 의 시작이 6736.06 m 라 서로 다른 셀로 갈린다.
# `representative_segment` 는 **용량 가중** 다수결인데 넷 다 900 vph 로 같아 동률이 되고,
# 규칙이 상류를 택해 4 가 나왔다. 실측 유량은 431 대 781 로 **하류가 64%** 다.
# 오프라인 A/B: FW_W|4 밀도 MAPE 49.9% -> 16.8%, 전체 점수 +5.44%.
MERGE_FIX = {"R_F_W": 5}

FIT_RUNS = [("nocontrolstep_20260826", 1.0), ("ncsweep_x18_20260828", 1.8),
            ("ncsweep_x22_20260828", 2.2)]
HOLDOUT_RUNS = [("ncsweep_x16_20260828", 1.6), ("ncsweep_x20_20260828", 2.0)]


def mainline_vph(sim_sec, mult):
    idx = min(int(sim_sec // INTERVAL_SEC), len(MAINLINE_BASE) - 1)
    return MAINLINE_BASE[idx] * mult


def load_pairs(run, mult, qb, cfg, TrafficState, dm, cal, t0=900.0):
    """(초기상태, 관측된 다음 세그먼트, sim_sec) 목록. 결정 간격이 곧 T_c 다."""
    files = sorted(glob.glob(str(R / "evaluation/runs" / run / "decisions_*/state_*.json")))
    sjs = []
    for f in files:
        sj = json.loads(Path(f).read_text(encoding="utf-8"))
        sjs.append((float(sj.get("sim_sec") or 0.0), sj))
    sjs.sort(key=lambda x: x[0])
    pairs = []
    for i in range(len(sjs) - 1):
        t, sj = sjs[i]
        t2, sj2 = sjs[i + 1]
        if t < t0 or abs((t2 - t) - cfg.simulation.T_c_h * 3600.0) > 1.0:
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
        pairs.append((st, obs, t, mult))
    return pairs


def score(pairs, cfg, freeway_step, ControlAction, DemandStep, params):
    """params 를 net 에 심고 전 쌍을 전진시켜 밀도·속도 오차를 잰다."""
    net = cfg.network
    if MERGE_FIX:
        idx = dict(net.ramp_merge_segment_index)
        idx.update(MERGE_FIX)
        net.ramp_merge_segment_index = idx
    net.metanet_tau_h = params["tau_sec"] / 3600.0
    if hasattr(net, "metanet_tau_sec"):
        net.metanet_tau_sec = params["tau_sec"]
    net.metanet_nu_km2_h = params["nu"]
    net.metanet_kappa_veh_km_lane = params["kappa"]
    net.metanet_delta_merge = params["delta"]

    dr = dv = 0.0
    sr = sv = 0.0
    cnt = 0
    for st0, obs, t, mult in pairs:
        st = copy.deepcopy(st0)
        control = ControlAction(
            ramp_metering={r: float(net.ramp_capacity_veh_h[r]) for r in net.ramps},
            vsl={lk: float(net.v_free) for lk in net.freeway_links},
            green_times={}, offsets={}, inflow_outflow_allocation={},
        )
        demand = DemandStep(
            freeway_mainline={lk: mainline_vph(t, mult) for lk in net.freeway_links},
            urban_boundary={},
            ramp_arrival=dict(RAMP_VPH),
        )
        try:
            freeway_step(st, control, demand, cfg)
        except Exception:
            return None
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
    rmse_r = math.sqrt(dr / cnt)
    rmse_v = math.sqrt(dv / cnt)
    mr = sr / cnt
    mv = sv / cnt
    return {"rmse_rho": rmse_r, "rmse_speed": rmse_v, "mean_rho": mr, "mean_speed": mv,
            "score": rmse_r / max(mr, 1e-9) + rmse_v / max(mv, 1e-9), "n": cnt}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true", help="현행값 오차만 재고 끝낸다")
    ap.add_argument("--out", default="outputs/metanet_dynamics_calibration_20260830")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    import importlib.util
    sp = importlib.util.spec_from_file_location(
        "qb", R / "evaluation/controllers/vissim_stackelberg_adapter.py")
    qb = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(qb)
    from src.models.state import ControlAction, TrafficState
    from src.models.demand import DemandStep
    from src.models.metanet import freeway_step

    tun = qb.load_optional_json(str(R / "evaluation/configs/canon_fdfit3_20260828.json"))
    cal = qb.load_optional_json(
        str(R / "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json"))
    qb.install_config_switches(tun)
    cfg = qb.build_config(R / "vendor/NumSim-mine", 150.0, 5400.0, "wu-link",
                          cal, tun, local_observation=True, flagship=True)
    dm = qb.load_optional_json(str(R / "evaluation/real_world_modi_control/detector_local_mapping.json"))

    cur = {"tau_sec": float(cfg.network.metanet_tau_h) * 3600.0,
           "nu": float(cfg.network.metanet_nu_km2_h),
           "kappa": float(cfg.network.metanet_kappa_veh_km_lane),
           "delta": float(getattr(cfg.network, "metanet_delta_merge", 0.0) or 0.0)}
    print("현행 %s" % cur)
    print("FD  v_free %.1f · rho_crit %.2f · a %.3f"
          % (cfg.network.v_free, cfg.network.rho_crit, cfg.network.metanet_a_m))
    print()

    fit_pairs, hold_pairs = [], []
    for run, mult in FIT_RUNS:
        p = load_pairs(run, mult, qb, cfg, TrafficState, dm, cal)
        fit_pairs += p
        print("적합  %-28s x%-4.1f 쌍 %d개" % (run, mult, len(p)))
    for run, mult in HOLDOUT_RUNS:
        p = load_pairs(run, mult, qb, cfg, TrafficState, dm, cal)
        hold_pairs += p
        print("홀드  %-28s x%-4.1f 쌍 %d개" % (run, mult, len(p)))
    print()

    base_fit = score(fit_pairs, cfg, freeway_step, ControlAction, DemandStep, cur)
    base_hold = score(hold_pairs, cfg, freeway_step, ControlAction, DemandStep, cur)
    for nm, s in (("적합셋", base_fit), ("홀드아웃", base_hold)):
        if s:
            print("현행 %s: 밀도 RMSE %.2f (평균 %.2f · %.1f%%) · 속도 RMSE %.2f (평균 %.1f · %.1f%%) · 점수 %.4f"
                  % (nm, s["rmse_rho"], s["mean_rho"], 100 * s["rmse_rho"] / s["mean_rho"],
                     s["rmse_speed"], s["mean_speed"], 100 * s["rmse_speed"] / s["mean_speed"], s["score"]))
    if args.smoke:
        return 0

    best = (base_fit["score"], dict(cur))
    evals = 0
    stage = [
        # delta 범위 (2026-08-30 2차). 1차 격자는 상단이 0.15 였는데 그 뒤 sweep 에서
        # delta=4.0 이 홀드아웃 0.4196 으로 0.15(0.4282)보다 좋았다 — 격자가 좁아 못 찾았다.
        # delta 가 커야 하는 이유는 부분적으로 기하다: 문헌 delta 는 0.5 km 세그먼트 기준이고
        # 우리는 1.347 km x 4차로라 분모 L*lanes 가 3.6배 크다. 다만 그것으로 설명되는 건
        # 3~4배지 전부가 아니다 — 나머지는 1.347 km 평균이 합류부 국소 감속을 희석하는 몫이다.
        {"tau_sec": [3, 5, 7, 10, 14, 18, 26, 38], "nu": [20, 40, 65, 90, 120],
         "kappa": [15, 25, 40, 60, 85], "delta": [0.0, 0.5, 2.0, 4.0, 8.0, 16.0]},
    ]
    for grid in stage:
        for tau in grid["tau_sec"]:
            for nu in grid["nu"]:
                for kap in grid["kappa"]:
                    for dl in grid["delta"]:
                        p = {"tau_sec": tau, "nu": nu, "kappa": kap, "delta": dl}
                        s = score(fit_pairs, cfg, freeway_step, ControlAction, DemandStep, p)
                        evals += 1
                        if s and s["score"] < best[0]:
                            best = (s["score"], dict(p))
        print("거친 격자 %d회 · 최선 %.4f %s" % (evals, best[0], best[1]))

    # 국소 정련
    for _ in range(4):
        improved = False
        b = dict(best[1])
        for key, steps in (("tau_sec", [-3, -1, 1, 3]), ("nu", [-10, -4, 4, 10]),
                           ("kappa", [-8, -3, 3, 8]), ("delta", [-1.0, -0.3, 0.3, 1.0])):
            for d in steps:
                p = dict(b)
                p[key] = max(1e-4 if key != "delta" else 0.0, p[key] + d)
                s = score(fit_pairs, cfg, freeway_step, ControlAction, DemandStep, p)
                evals += 1
                if s and s["score"] < best[0]:
                    best = (s["score"], dict(p))
                    improved = True
        if not improved:
            break
    print("정련 후 %d회 · 최선 %.4f %s" % (evals, best[0], best[1]))

    fit_s = score(fit_pairs, cfg, freeway_step, ControlAction, DemandStep, best[1])
    hold_s = score(hold_pairs, cfg, freeway_step, ControlAction, DemandStep, best[1])
    print()
    print("%-10s %14s %14s %14s %14s"
          % ("", "밀도RMSE(적합)", "속도RMSE(적합)", "밀도RMSE(홀드)", "속도RMSE(홀드)"))
    print("%-10s %14.2f %14.2f %14.2f %14.2f"
          % ("현행", base_fit["rmse_rho"], base_fit["rmse_speed"],
             base_hold["rmse_rho"], base_hold["rmse_speed"]))
    print("%-10s %14.2f %14.2f %14.2f %14.2f"
          % ("적합", fit_s["rmse_rho"], fit_s["rmse_speed"], hold_s["rmse_rho"], hold_s["rmse_speed"]))
    gain_fit = 100 * (1 - fit_s["score"] / base_fit["score"])
    gain_hold = 100 * (1 - hold_s["score"] / base_hold["score"])
    print()
    print("점수 개선  적합셋 %+.1f%% · **홀드아웃 %+.1f%%**" % (gain_fit, gain_hold))
    verdict = ("홀드아웃에서도 개선 — 채택 가능" if gain_hold > 2.0
               else "홀드아웃 개선이 미미하다 — 과적합이거나 이 항들이 지배적이지 않다")
    print("판정: %s" % verdict)

    doc = {
        "schema_version": "metanet-dynamics-calibration/1",
        "generated": "2026-08-30",
        "merge_fix": MERGE_FIX,
        "why": "FD 재적합은 평형 3항만 맞췄다. tau/nu/kappa 는 vendor 기본값이고 delta_merge 는 0 이다. "
               "delta 단독 대수 역산은 실패했으므로(문헌값의 970배) 네 항을 함께 적합한다.",
        "method": "관측 t -> 실제 plant freeway_step 으로 150s 전진 -> t+150s 관측과 대조. "
                  "본선 유입 .inpx 구간유량 · 램프 유입 실측 · 무제어 자료.",
        "fit_runs": {r: m for r, m in FIT_RUNS},
        "holdout_runs": {r: m for r, m in HOLDOUT_RUNS},
        "ramp_arrival_vph": RAMP_VPH,
        "current": cur, "fitted": best[1],
        "current_scores": {"fit": base_fit, "holdout": base_hold},
        "fitted_scores": {"fit": fit_s, "holdout": hold_s},
        "gain_percent": {"fit": gain_fit, "holdout": gain_hold},
        "evaluations": evals, "verdict": verdict,
    }
    (R / (args.out + ".json")).write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print("-> %s.json" % args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
