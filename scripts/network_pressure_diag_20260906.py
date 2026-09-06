# -*- coding: utf-8 -*-
"""Stage 1~5 진단 (2026-09-06): 기록된 상태에서 망 압력을 계산해 표로 낸다. 컨트롤러 결정은 하지 않는다(라이브 무영향).
사용: python scripts/network_pressure_diag_20260906.py <t> <run> <base_cfg> [<onehop_cfg>] [signals]
출력: evaluation/runs/<run>/netpressure_<t>_{nodes,movements,phases}.csv + 표준출력 표."""
import csv, io, json, sys, time, importlib.util
from pathlib import Path

R = Path(__file__).resolve().parents[1]


def main():
    sys.path.insert(0, str(R)); sys.path.insert(0, str(R / "vendor/NumSim-mine")); sys.path.insert(0, str(R / "scripts"))
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    T = int(sys.argv[1]); RUN = sys.argv[2]; CFG = sys.argv[3]
    ONEHOP_CFG = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] != "-" else None
    SIGS = sys.argv[5].split(",") if len(sys.argv) > 5 else ["SC105", "SC1001", "SC1004", "SC1002", "SC5", "SC101"]
    sp = importlib.util.spec_from_file_location("qb", R / "evaluation/controllers/vissim_stackelberg_adapter.py"); qb = importlib.util.module_from_spec(sp); sp.loader.exec_module(qb)
    sp2 = importlib.util.spec_from_file_location("npz", R / "evaluation/controllers/network_pressure.py"); npz = importlib.util.module_from_spec(sp2); sp2.loader.exec_module(npz)
    import offline_harness_20260904 as OH
    from src.models.state import TrafficState, ControlAction
    from src.models.demand import DemandStep
    D = R / "evaluation/runs" / RUN / ("decisions_%s" % RUN)
    S = str(D / ("state_%06d.json" % T)); A = str(D / ("action_%06d.json" % (T - 150)))
    t0 = time.time()
    cfg, st, sj, meta, dm, cal, tun = OH.build(qb, TrafficState, str(R / "evaluation/configs" / (CFG + ".json")), S, A)
    res = npz.compute(cfg, st, sj, A, R)
    P = res["params"]; topo = res["topology"]; bur = res["burdens"]; pot = res["potentials"]; ph = res["phase_prices"]
    print("=== 망 압력 진단 %s t=%d · 계산 %.1f s · 창 %d · local_scale %.3f" % (RUN, T, time.time() - t0, res["windows_used"], res["local_scale"]))
    # Stage 2: 그래프 검사
    ck = topo["checks"]
    print("[Stage 2] 노드 %d · 간선 %d · β 행합>1 %d개 %s · sink %d개 %s · 저장용량 0 %d개 · 자기루프 %d" % (
        len(topo["nodes"]), len(topo["edges"]), len(ck["row_sum_over_1"]), ck["row_sum_over_1"][:4], len(ck["sinks"]), ck["sinks"][:6], len(ck["no_storage"]), len(ck["self_loops"])))
    # Stage 3: 잠재
    print("[Stage 3] ρ(A↓) %.4f · ρ(A↑) %.4f · max γ %.4f · 반복 fw %d(res %.1e) bw %d(res %.1e) · 간선 fw %d bw %d · ψ↓ [%.3f, %.3f] ψ↑ [%.3f, %.3f] h" % (
        pot["rho_fw"], pot["rho_bw"], pot["max_gamma"], pot["iters_fw"], pot["resid_fw"], pot["iters_bw"], pot["resid_bw"], pot["n_edges_fw"], pot["n_edges_bw"],
        min(pot["psi_fw"].values()), max(pot["psi_fw"].values()), min(pot["psi_bw"].values()), max(pot["psi_bw"].values())))
    # Stage 1: SC105 p1 · SC1001 p3 관련 노드
    print("[Stage 1] 노드 부담 (n/N 점유 · dep gcap μ̂[src] · T B e · ψ↓ ψ↑ · γ)")
    focus = ["SC1002_to_SC105", "SC105_to_SC1005", "SC105_to_SC1", "SC105_to_SC1003", "in_SC1001_W", "SC1001_to_SC1002", "SC1001_to_SC1003", "SC1001_to_SC2002", "R_D_W", "R_D_E", "SC5_to_SC101", "SC101_to_SC1002", "SC1002_to_SC1001"]
    for n in focus:
        if n not in bur: print("   %-18s (없음)" % n); continue
        b = bur[n]
        print("   %-18s n %5.0f/%5.0f (%.2f) · dep %5.0f gcap %5.0f μ̂ %5.0f[%s] · T %.3f B %.2f e %.3f · ψ↓ %.3f ψ↑ %.3f · γ %.2f" % (
            n, b["n"], b["N"], b["occ"], b["dep"], b["gcap"], b["mu"], "g" if b["mu_from_gcap"] else "d", b["T"], b["B"], b["e"], pot["psi_fw"][n], pot["psi_bw"][n], pot["gamma"][n]))
    # L 기울기 (phased 국소, 순수 교환 방향 ΔL/δ) — 컨트롤러·ctx 만 만든다(decide 없음)
    fc = qb.demand_from_state(sj, cfg, DemandStep, int(cfg.mpc.horizon_steps), cal, dm)
    ctl = qb.control_from_json(Path(A), cfg, ControlAction)
    c = qb.build_priced_wu_link_controller(cfg, tun); c.price_parallel_workers = 0; fol = c.nash_solver
    fol.phase_price_local_cost_model = "phased"; ctx = fol._phase_refine_context(st, ctl, fc)
    delta = float(c.phase_price_delta_sec)
    def lgrad(sig):
        base = c._phase_vector(ctl, sig); setup = fol._phase_refine_signal_setup(sig, st, ctx) if ctx else None
        if setup is None: return base, {}
        L0 = fol._phase_local_cost_phased(sig, base, setup, ctx); out = {}
        for pid in npz.MODEL_PHASES:
            mv = c._phase_direction(sig, base, pid, delta)
            if mv is None: continue
            out[pid] = (fol._phase_local_cost_phased(sig, mv, setup, ctx) - L0) / delta
        return base, out
    # one-hop 어댑터 가격 (h2 방식) — onehop_cfg 로 설치 함수 호출
    onehop = {}
    if ONEHOP_CFG:
        tun2 = qb.load_optional_json(str(R / "evaluation/configs" / (ONEHOP_CFG + ".json")))
        qb.install_observed_backpressure_price(cfg, tun2, sj, A)
        onehop = dict(getattr(cfg.network, "observed_backpressure_prices", None) or {})
    live = json.load(io.open(str(D / ("action_%06d.json" % T)), encoding="utf-8")); ldg = live.get("diagnostics") or {}; lg = live.get("green_times") or {}
    # Stage 5 표
    print("[Stage 5] 교차로/현시 · ref녹색 · 라이브녹색 · ΔL/δ(국소, −=이득) · 롤아웃가격 · one-hop(어댑터) · 1hop(모듈) · NP · EXT  [veh·h/s; NP/EXT/1hop 은 물리 척도, ×local_scale 이 L 통화]")
    extremes = sorted(((abs(v["NP"]), s, p) for s, d in ph.items() for p, v in d.items()), reverse=True)[:6]
    show = list(SIGS) + [s for _, s, _ in extremes if s not in SIGS]
    for sig in show:
        base, lg_ = lgrad(sig)
        for pid in npz.MODEL_PHASES:
            if pid not in ph.get(sig, {}): continue
            v = ph[sig][pid]
            print("   %-7s %s ref %4.0f live %4.0f · ΔL/δ %+.4f · roll %+.4f · 1hopA %+.4f · 1hopM %+.4f · NPavg %+.4f · NPsum %+.4f · EXT %+.4f" % (
                sig, pid, base.get(pid, 0), lg.get("%s_%s" % (sig, pid), 0), lg_.get(pid, float("nan")), float(ldg.get("wu_phase_price_%s_%s" % (sig, pid), 0) or 0),
                float((onehop.get(sig) or {}).get(pid, 0.0)), v["ONEHOP"], v["NP"], v.get("NP_SUM", float("nan")), v["EXT"]))
    # movement 상세: SC105 p1 · SC1001 p3
    print("[Stage 4] movement 압력 상세 (s_eff · e_o e_d · ψ↓_d ψ↑_o relief_o · π NP/EXT/1hop)")
    for row in res["movements"]:
        if (row["signal"], row["phase"]) in (("SC105", "p1"), ("SC1001", "p3"), ("SC1001", "p1"), ("SC1002", "p4"), ("SC5", "p3")):
            print("   %-32s q %4.0f s_eff %.3f · e_o %.3f e_d %.3f · ψ↓_d %.3f ψ↑_o %.3f rel_o %.3f · NP %+.4f EXT %+.4f 1hop %+.4f" % (
                row["m"], row["q_m"], row["s_eff"], row["e_o"], row["e_d"], row["psi_fw_d"], row["psi_bw_o"], row["up_relief_o"], row["pi_NP"], row["pi_EXT"], row["pi_1hop"]))
    # CSV
    out = R / "evaluation/runs" / RUN
    with io.open(out / ("netpressure_%06d_nodes.csv" % T), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["node", "n", "N", "occ", "dep", "gcap", "mu", "mu_from_gcap", "T", "B", "e", "psi_fw", "psi_bw", "up_relief", "gamma"])
        for n, b in bur.items(): w.writerow([n] + [round(b[k], 5) for k in ("n", "N", "occ", "dep", "gcap", "mu", "mu_from_gcap", "T", "B", "e")] + [round(pot["psi_fw"][n], 5), round(pot["psi_bw"][n], 5), round(pot["up_relief"][n], 5), round(pot["gamma"][n], 4)])
    with io.open(out / ("netpressure_%06d_movements.csv" % T), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); keys = list(res["movements"][0].keys()) if res["movements"] else []; w.writerow(keys)
        for row in res["movements"]: w.writerow([row[k] if not isinstance(row[k], float) else round(row[k], 6) for k in keys])
    with io.open(out / ("netpressure_%06d_phases.csv" % T), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["signal", "phase", "ONEHOP", "NP", "EXT"])
        for s, d in ph.items():
            for p, v in d.items(): w.writerow([s, p, round(v["ONEHOP"], 6), round(v["NP"], 6), round(v["EXT"], 6)])
    print("=== CSV: %s/netpressure_%06d_{nodes,movements,phases}.csv · 끝 %.1f s" % (out, T, time.time() - t0))


if __name__ == "__main__":
    main()
