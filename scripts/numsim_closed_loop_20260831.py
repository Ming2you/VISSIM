# -*- coding: utf-8 -*-
"""플랜트 기반 폐루프 numerical sim. VISSIM 없이 **병렬로** 돌린다.

왜 (2026-08-31).

VISSIM 은 한 번에 하나만 뜨고 런당 75분이다. 2026-08-31 하루에 8런을 돌렸는데 그중 5런이
"고속도로 레버가 아예 안 켜져서" 아무것도 안 나온 런이었다 — 그 사실은 플랜트만으로 분 단위에
알 수 있었다. 선별이 있었으면 6시간을 아꼈다.

이 러너가 답하는 것 (전부 기전이다):

    레버가 켜지는가            vsl 분포 · 미터링이 도착을 구속한 결정 수 · density_stress
    사슬이 이어지는가          램프 큐가 쌓이는가 · blocked_q 가 비영인가
    목적함수에 곡률이 있는가     후보 스프레드 · 정련 발동률 · 폴백 승률

**TTT 로 팔 순위를 매기지 마라.** 컨트롤러와 플랜트가 같은 METANET 을 쓰므로 컨트롤러가 자기
모델에 대해 최적화한다. 모델 오차(세그먼트 예측 26%)가 통째로 사라진 세계의 TTT 는 VISSIM TTT 와
다른 물건이다. 남는 건 지평 절단과 GNE 분해 효과뿐이고 그건 지배항이 아니다. 순위와 시드는 VISSIM 이다.

왜 vendor 의 run_experiment.py 를 안 쓰나.

    src/experiments/run_experiment.py   auto-tuner 루프·리포트 껍데기(192줄)
    src/simulation/closed_loop_runner.py:run_closed_loop
        -> controller = StackelbergMPCController(cfg) if mode == "stackelberg_mpc" else None
           **우리 팔이 아니다.** 우리는 wu-link(PricedWuLinkStackelbergController)다.

vendor 편집은 금지이므로(CLAUDE.md) 같은 루프를 여기서 우리 컨트롤러로 돌린다. 플랜트는
`MixedTrafficSimulator` -> `run_coupled_interval` -> `freeway_substep` 으로, 우리가 오늘
tau·nu·kappa·delta 를 적합한 **바로 그 코드**다(scripts/whose_code.py 로 확인).

수요.
    본선   .inpx 구간별 vehicleInput volume (link 26 -> FW_W · 74 -> FW_E)
    램프   .fzp 고유차량 직접계수 실측 (752 / 1212 / 938 / 555 vph)
    도시   게이트별 유량은 VISSIM 상태에서 오므로 여기서는 실런 상태 JSON 의 값을 재생한다
           (--demand-from-run). 없으면 config 의 스칼라로 균등 배분한다.

사용:
  python scripts/numsim_closed_loop_20260831.py --tuning evaluation/configs/canon_fdfit3_20260828.json
  python scripts/numsim_closed_loop_20260831.py --tuning A.json B.json C.json --workers 3
"""
import argparse
import concurrent.futures as cf
import glob
import importlib.util
import json
import statistics as st
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent

# 실측 램프 유입 [veh/h] — outputs/ramp_arrival_calibration_20260830.json (.fzp 직접계수)
RAMP_VPH = {"R_D_W": 752.0, "R_F_W": 1212.0, "R_D_E": 938.0, "R_F_E": 555.0}
# .inpx 본선 구간유량 (x1.0). link 26 · 74 가 같은 프로파일이다.
MAINLINE_BASE = [3080.0, 4400.0, 4620.0, 3960.0, 3080.0, 2200.0]
INTERVAL_SEC = 900.0


def _load_adapter():
    sys.path.insert(0, str(R))
    sys.path.insert(0, str(R / "vendor/NumSim-mine"))
    sp = importlib.util.spec_from_file_location(
        "qb", R / "evaluation/controllers/vissim_stackelberg_adapter.py")
    qb = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(qb)
    return qb


def build(tuning, demand_mult=1.0):
    """우리 config 로 cfg + 컨트롤러 + 플랜트를 세운다."""
    qb = _load_adapter()
    from src.simulation.simulator import MixedTrafficSimulator
    from src.models.demand import DemandStep

    tun = qb.load_optional_json(str(R / tuning))
    cal = qb.load_optional_json(
        str(R / "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json"))
    cal = qb.deep_update(dict(cal), tun.get("calibration_override") or {})
    qb.install_config_switches(tun)
    cfg = qb.build_config(R / "vendor/NumSim-mine", 150.0, 5400.0, "wu-link",
                          cal, tun, local_observation=True, flagship=True)
    qb._plant_rollout_far_into(cfg, tun)
    controller = qb.build_priced_wu_link_controller(cfg, tun)
    sim = MixedTrafficSimulator(cfg)
    return qb, cfg, controller, sim, DemandStep, tun


def demand_at(cfg, sim_sec, mult, urban_by_gate, DemandStep):
    idx = min(int(sim_sec // INTERVAL_SEC), len(MAINLINE_BASE) - 1)
    ml = MAINLINE_BASE[idx] * mult
    net = cfg.network
    return DemandStep(
        freeway_mainline={lk: ml for lk in net.freeway_links},
        urban_boundary=dict(urban_by_gate),
        ramp_arrival=dict(RAMP_VPH),
    )


def gate_demand_from_run(cfg, run):
    """실런 상태 JSON 의 게이트별 유량을 sim_sec -> {gate: vph} 로 재생한다."""
    out = {}
    for f in sorted(glob.glob(str(R / "evaluation/runs" / run / "decisions_*/state_*.json"))):
        sj = json.loads(Path(f).read_text(encoding="utf-8"))
        g = ((sj.get("demand") or {}).get("urban_volume_vph_by_gate") or {})
        if g:
            out[float(sj.get("sim_sec") or 0.0)] = {str(k): float(v) for k, v in g.items()}
    return out


def run_one(tuning, steps, demand_mult, gate_src, label):
    qb, cfg, controller, sim, DemandStep, tun = build(tuning, demand_mult)
    net = cfg.network
    gates = gate_demand_from_run(cfg, gate_src) if gate_src else {}
    if not gates:
        v = float(getattr(cfg.demand, "urban_volume_vph", 500.0)) if hasattr(cfg, "demand") else 500.0
        flat = {str(k): v for k in list(net.boundary_in_links) + list(net.boundary_out_links)}
    previous = None
    rows = []
    for step in range(steps):
        t = sim.state.time_sec
        gk = min(gates, key=lambda x: abs(x - t)) if gates else None
        ub = gates[gk] if gk is not None else flat
        cur = demand_at(cfg, t, demand_mult, ub, DemandStep)
        # 모델 forecast 로 램프 도착을 덮는다 — 어댑터가 실런에서 하는 것과 같은 경로.
        forecast = [demand_at(cfg, t + i * cfg.simulation.control_interval, demand_mult, ub, DemandStep)
                    for i in range(max(1, cfg.mpc.horizon_steps))]
        control = controller.decide(sim.state.copy(), forecast, previous, cfg)
        log = sim.step(control, cur, step)
        previous = control
        d = dict(control.diagnostics or {})
        rm = {k: float(v) for k, v in (control.ramp_metering or {}).items()}
        # "구속" 은 미터링이 **모델이 보는 도착** 아래로 내려간 것이다. 실측(RAMP_VPH)과
        # 비교하면 안 된다 — 모델은 자기 forecast(local_ramp_arrival_forecast)로 도착을
        # 추정하고 그 값에 대해 최적화하므로, 실측과 비교하면 모델이 조이지도 않았는데
        # 조인 것처럼 잡힌다(2026-08-31 첫 스모크에서 4/4 오탐).
        arr = {k: float(v) for k, v in (cur.ramp_arrival or {}).items()}
        binds = sum(1 for k, v in rm.items() if v < arr.get(k, 0.0) - 1e-6)
        rows.append({
            "step": step, "time_sec": sim.state.time_sec,
            "freeway_ttt": log.freeway_ttt, "urban_ttt": log.urban_ttt,
            "total_ttt": log.freeway_ttt + log.urban_ttt,
            "vsl": sorted({round(float(x), 1) for x in (control.vsl or {}).values()}),
            "meter_sum": sum(rm.values()), "meter_binding_ramps": binds,
            "ramp_arrival_sum": sum(arr.values()),
            "ramp_queue_veh": float(d.get("leader_ramp_queue_veh", 0.0) or 0.0),
            "density_stress": float(d.get("leader_search_density_stress", 0.0) or 0.0),
            "cand_spread": float(d.get("leader_candidate_objective_spread", 0.0) or 0.0),
            "cand_best_obj": float(d.get("leader_candidate_best_objective", 0.0) or 0.0),
            "refine_active": float(d.get("leader_candidate_refinement_active", 0.0) or 0.0),
            "best_is_fallback": float(d.get("leader_candidate_best_stage_fallback", 0.0) or 0.0),
            # q-k 그림용 세그먼트 상태. 플랜트가 실제로 어느 작동점에 있는지 본다.
            "segments": [
                {"link": lk, "i": i,
                 "rho": float(sim.state.freeway_density[lk][i]),
                 "v": float(sim.state.freeway_speed[lk][i]),
                 "lanes": float(sim.state.freeway_effective_lanes[lk][i])
                 if getattr(sim.state, "freeway_effective_lanes", None) else float(net.freeway_lanes)}
                for lk in net.freeway_links
                for i in range(len(sim.state.freeway_density[lk]))
            ],
        })
    return {"label": label, "tuning": tuning, "steps": steps,
            "demand_multiplier": demand_mult, "rows": rows,
            "total_ttt": sim.total_ttt, "freeway_ttt": sim.freeway_ttt, "urban_ttt": sim.urban_ttt}


def summarize(r):
    rows = r["rows"]
    vs = sorted({v for x in rows for v in x["vsl"]})
    nb = sum(1 for x in rows if x["meter_binding_ramps"] > 0)
    sp = [100 * x["cand_spread"] / abs(x["cand_best_obj"]) for x in rows if abs(x["cand_best_obj"]) > 1e-9]
    return {
        "label": r["label"], "total_ttt": r["total_ttt"],
        "freeway_ttt": r["freeway_ttt"], "urban_ttt": r["urban_ttt"],
        "vsl_values": vs,
        "vsl_non_free_pct": 100.0 * sum(1 for x in rows for v in x["vsl"] if abs(v - 120.0) > 1e-6)
        / max(sum(len(x["vsl"]) for x in rows), 1),
        "meter_binding_steps": "%d/%d" % (nb, len(rows)),
        "meter_sum_median": st.median([x["meter_sum"] for x in rows]) if rows else 0,
        "ramp_arrival_median": st.median([x["ramp_arrival_sum"] for x in rows]) if rows else 0,
        "ramp_queue_max": max((x["ramp_queue_veh"] for x in rows), default=0.0),
        "density_stress_median": st.median([x["density_stress"] for x in rows]) if rows else 0,
        "cand_spread_pct_median": st.median(sp) if sp else 0.0,
        "refine_pct": 100.0 * sum(x["refine_active"] for x in rows) / max(len(rows), 1),
        "fallback_win_pct": 100.0 * sum(x["best_is_fallback"] for x in rows) / max(len(rows), 1),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tuning", nargs="+", required=True)
    ap.add_argument("--steps", type=int, default=36)
    ap.add_argument("--demand-mult", type=float, default=1.0)
    ap.add_argument("--demand-from-run", default="nocontrolstep_20260826",
                    help="게이트별 도시 수요를 재생할 실런. 빈 문자열이면 스칼라 균등")
    ap.add_argument("--workers", type=int, default=0, help="0=순차")
    ap.add_argument("--out", default="outputs/numsim_closed_loop_20260831.json")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    jobs = [(t, args.steps, args.demand_mult, args.demand_from_run or None, Path(t).stem)
            for t in args.tuning]
    results = []
    if args.workers > 1 and len(jobs) > 1:
        with cf.ProcessPoolExecutor(max_workers=args.workers) as ex:
            for r in ex.map(run_one, *zip(*jobs)):
                results.append(r)
    else:
        for j in jobs:
            results.append(run_one(*j))

    print("%-34s %10s %10s %10s %-22s %8s %9s %9s %10s %8s"
          % ("팔", "총TTT", "freeway", "urban", "VSL", "구속", "램프큐", "dens", "스프레드%", "정련%"))
    summaries = []
    for r in results:
        s = summarize(r)
        summaries.append(s)
        print("%-34s %10.1f %10.1f %10.1f %-22s %8s %9.1f %9.3f %10.4f %7.0f%%"
              % (s["label"][:34], s["total_ttt"], s["freeway_ttt"], s["urban_ttt"],
                 str(s["vsl_values"])[:22], s["meter_binding_steps"], s["ramp_queue_max"],
                 s["density_stress_median"], s["cand_spread_pct_median"], s["refine_pct"]))

    doc = {"schema_version": "numsim-closed-loop/1", "generated": "2026-08-31",
           "warning": "TTT 로 팔 순위를 매기지 마라 — 컨트롤러와 플랜트가 같은 METANET 이다. "
                      "이 러너는 기전(레버 발동·사슬 연결·목적함수 곡률)을 재는 선별 도구다.",
           "ramp_arrival_vph": RAMP_VPH, "mainline_base_vph": MAINLINE_BASE,
           "summaries": summaries, "runs": results}
    (R / args.out).write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print()
    print("-> %s" % args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
