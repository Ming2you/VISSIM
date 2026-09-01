# -*- coding: utf-8 -*-
"""METANET merge 항 계수 δ 를 우리 망 실측에서 역산하고, 문헌값 0.0122 와 대조한다.

왜 (2026-08-30).

`metanet_delta_merge` 는 지금 0.0(비활성)이다. state.py 필드 주석은 문헌 표준값 δ≈0.0122 를
권하며 그것이 "metering 의 교과서적 payoff(합류 교란 저감)" 를 여는 항이라고 적는다. 즉 이 값이
0 인 한 램프 유입이 본선 속도를 안 건드리고, 미터링으로 조여도 본선이 얻는 게 없다.

그런데 문헌값을 그대로 켜면 우리 망에 맞는지 모른다. 런을 태우기 전에 역산한다.

식.

    구현(local_freeway_plant.py:311 · metanet.py:358)
        Δv_step = −δ · dt_h · q_ramp · v / (L_km · λ · (ρ + κ))

    METANET 속도갱신에서 완화항과 균형을 이루는 정상상태:
        0 = (dt/τ)(V_eff − v) + Δv_step
        => v − V(ρ) = −δ · τ_h · q_ramp · v / (L · λ · (ρ + κ))          (dt 가 상쇄된다)

    따라서
        δ = −(v − V(ρ)) · L · λ · (ρ + κ) / (τ_h · q_ramp · v)

무엇을 재는가.

    v, ρ        상태 JSON 의 freeway_segments (실측)
    V(ρ)        재적합 FD (v_free 120.0 · rho_crit 27.0 · a 1.6)
    q_ramp      .fzp 고유차량 직접계수 (outputs/ramp_arrival_calibration_20260830.json)
    τ_h         cfg 실효값

**대조가 핵심이다.** FD 자체가 RMSE 10.5 kph 로 편의를 가지므로 잔차의 절대값은 못 쓴다.
같은 링크의 **비합류 세그먼트** 잔차를 기준선으로 빼서 합류 고유의 결손만 남긴다.

산출: outputs/delta_merge_calibration_20260830.json
"""
import argparse
import glob
import io
import json
import math
import statistics as st
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent

VF, RC, A = 120.0, 27.0, 1.6                 # 재적합 FD (2026-08-28)
KAPPA = 40.0
MERGE = {("FW_W", 2): "R_D_W", ("FW_W", 4): "R_F_W",
         ("FW_E", 5): "R_D_E", ("FW_E", 3): "R_F_E"}
Q_RAMP = {"R_D_W": 752.0, "R_F_W": 1212.0, "R_D_E": 938.0, "R_F_E": 555.0}
RUNS = [("nocontrolstep_20260826", 1.0), ("ncsweep_x16_20260828", 1.6),
        ("ncsweep_x18_20260828", 1.8), ("ncsweep_x20_20260828", 2.0),
        ("ncsweep_x22_20260828", 2.2)]


def fd(rho):
    return VF * math.exp(-(1.0 / A) * (rho / RC) ** A)


def collect(run, t0):
    """세그먼트별 (밀도, 속도, 차로, 길이) 표본."""
    out = {}
    for f in sorted(glob.glob(str(R / "evaluation/runs" / run / "decisions_*/state_*.json"))):
        sj = json.loads(Path(f).read_text(encoding="utf-8"))
        if float(sj.get("sim_sec") or 0.0) < t0:
            continue
        for link, arr in (sj.get("freeway_segments") or {}).items():
            for i, s in enumerate(arr):
                c = float(s.get("count") or 0.0)
                L = float(s.get("length_km") or 0.0)
                n = float(s.get("lanes") or 0.0)
                ss = float(s.get("speed_sum") or 0.0)
                if c <= 0 or L <= 0 or n <= 0:
                    continue
                out.setdefault((link, i), []).append(
                    (c / (L * n), ss / c, n, L))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--t0", type=float, default=900.0)
    ap.add_argument("--tau-h", type=float, default=None, help="미지정이면 cfg 실효값")
    ap.add_argument("--out", default="outputs/delta_merge_calibration_20260830")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    tau_h = args.tau_h
    if tau_h is None:
        sys.path.insert(0, str(R))
        import importlib.util
        sp = importlib.util.spec_from_file_location(
            "qb", R / "evaluation/controllers/vissim_stackelberg_adapter.py")
        qb = importlib.util.module_from_spec(sp)
        sp.loader.exec_module(qb)
        tun = qb.load_optional_json(str(R / "evaluation/configs/canon_fd3sw22_20260828.json"))
        cal = qb.load_optional_json(
            str(R / "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json"))
        qb.install_config_switches(tun)
        cfg = qb.build_config(R / "vendor/NumSim-mine", 150.0, 5400.0, "wu-link",
                              cal, tun, local_observation=True, flagship=True)
        tau_h = float(cfg.network.metanet_tau_h)
    print("τ = %.5f h (%.1f s) · κ = %.1f · FD %.1f/%.2f/%.3f"
          % (tau_h, tau_h * 3600, KAPPA, VF, RC, A))
    print()

    per_run = {}
    for run, mult in RUNS:
        segs = collect(run, args.t0)
        if not segs:
            continue
        resid = {}
        for key, rows in segs.items():
            rr = [(v - fd(rho)) for rho, v, _n, _L in rows]
            resid[key] = {"residual_kph": st.median(rr),
                          "rho": st.median([r[0] for r in rows]),
                          "speed": st.median([r[1] for r in rows]),
                          "lanes": st.median([r[2] for r in rows]),
                          "len_km": st.median([r[3] for r in rows])}
        per_run[run] = {"demand_multiplier": mult, "segments": resid}

    # 링크별 비합류 기준선
    print("%-8s %-6s %5s %8s %8s %8s %9s"
          % ("런", "링크", "셀", "밀도", "속도", "잔차", "합류램프"))
    rows_for_fit = []
    for run, d in per_run.items():
        base = {}
        for link in ("FW_W", "FW_E"):
            nm = [v["residual_kph"] for (lk, i), v in d["segments"].items()
                  if lk == link and (lk, i) not in MERGE]
            base[link] = st.median(nm) if nm else 0.0
        for (link, i), ramp in MERGE.items():
            v = d["segments"].get((link, i))
            if not v:
                continue
            excess = v["residual_kph"] - base[link]        # 합류 고유 결손(음수면 느리다)
            q = Q_RAMP[ramp]
            denom = tau_h * q * v["speed"]
            delta = (-excess * v["len_km"] * v["lanes"] * (v["rho"] + KAPPA) / denom) if denom > 0 else None
            rows_for_fit.append({"run": run, "demand_multiplier": d["demand_multiplier"],
                                 "link": link, "segment": i, "ramp": ramp,
                                 "rho": v["rho"], "speed": v["speed"], "lanes": v["lanes"],
                                 "residual_kph": v["residual_kph"], "baseline_kph": base[link],
                                 "merge_excess_kph": excess, "q_ramp_vph": q, "delta_implied": delta})
    for r in rows_for_fit:
        print("x%-7.1f %-6s %5d %8.2f %8.1f %8.2f %9s"
              % (r["demand_multiplier"], r["link"], r["segment"], r["rho"],
                 r["speed"], r["residual_kph"], r["ramp"]))

    print()
    print("%-8s %-9s %12s %12s %12s"
          % ("램프", "셀", "합류초과[kph]", "기준선[kph]", "함의 δ"))
    by_ramp = {}
    for r in rows_for_fit:
        by_ramp.setdefault(r["ramp"], []).append(r)
    for ramp, rs in by_ramp.items():
        ex = st.median([x["merge_excess_kph"] for x in rs])
        bl = st.median([x["baseline_kph"] for x in rs])
        ds = [x["delta_implied"] for x in rs if x["delta_implied"] is not None]
        by_ramp[ramp] = {"rows": rs, "merge_excess_median": ex,
                         "delta_median": st.median(ds) if ds else None,
                         "delta_values": ds}
        print("%-8s %-9s %12.2f %12.2f %12s"
              % (ramp, "%s[%d]" % (rs[0]["link"], rs[0]["segment"]), ex, bl,
                 "%.5f" % st.median(ds) if ds else "-"))

    alld = [x for v in by_ramp.values() for x in (v["delta_values"] or [])]
    pos = [x for x in alld if x > 0]
    print()
    if alld:
        print("함의 δ 전체 중앙 %.5f · 범위 %.5f ~ %.5f · 양수 %d/%d"
              % (st.median(alld), min(alld), max(alld), len(pos), len(alld)))
    print("문헌 표준값                0.01220")
    print()
    verdict = ""
    if not alld:
        verdict = "표본 없음"
    elif len(pos) < len(alld) * 0.6:
        verdict = ("**합류 세그먼트가 오히려 더 빠르다** — 이 망에서 merge 교란이 관측되지 않는다. "
                   "δ 를 켜면 없는 물리를 넣는 것이다.")
    else:
        m = st.median(pos)
        ratio = m / 0.0122
        verdict = ("합류 결손이 관측된다. 실측 함의 δ 중앙 %.5f = 문헌값의 %.2f배. "
                   "%s" % (m, ratio,
                           "문헌값이 우리 망에 대체로 맞는다." if 0.5 <= ratio <= 2.0
                           else "문헌값을 그대로 쓰면 %s." % ("과대" if ratio < 0.5 else "과소")))
    print("판정: %s" % verdict)

    doc = {
        "schema_version": "delta-merge-calibration/1",
        "generated": "2026-08-30",
        "why": "metanet_delta_merge=0 이라 램프 유입이 본선 속도를 안 건드린다 — 미터링의 "
               "교과서적 payoff 가 닫혀 있다. 문헌값 0.0122 를 켜기 전에 우리 망에서 역산한다.",
        "model": "정상상태 v-V(rho) = -delta*tau_h*q_ramp*v/(L*lanes*(rho+kappa))",
        "fd": {"v_free": VF, "rho_crit": RC, "a": A}, "tau_h": tau_h, "kappa": KAPPA,
        "q_ramp_vph": Q_RAMP,
        "merge_segments": {"%s[%d]" % k: v for k, v in MERGE.items()},
        "rows": rows_for_fit,
        "per_ramp": {k: {kk: vv for kk, vv in v.items() if kk != "rows"} for k, v in by_ramp.items()},
        "delta_implied_median": st.median(alld) if alld else None,
        "literature_delta": 0.0122,
        "verdict": verdict,
        "caveat": "정상상태 가정이다 — 실제 궤적은 과도상태를 포함한다. 그리고 잔차에는 FD "
                  "편의(RMSE 10.5 kph)와 차로수 변화가 섞이므로 같은 링크 비합류 셀을 기준선으로 뺐다.",
    }
    (R / (args.out + ".json")).write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print("-> %s.json" % args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
