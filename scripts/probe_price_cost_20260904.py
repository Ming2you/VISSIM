# -*- coding: utf-8 -*-
"""현시가격 계산이 실제로 얼마나 일을 하는가 — 호출 수 · 벽시계 · 프로파일.

"너무 빠르다" 는 의심을 수치로 결판낸다. 재는 것 셋.
  1. `_refresh_phase_prices` 1회의 롤아웃 호출 수와 총 벽시계
  2. 롤아웃 1회당 벽시계
  3. cProfile 로 내부 루프가 실제로 몇 번 도는가 (substep x movement 규모가 나오는지)

vendor 무수정. 읽기 전용.
"""
import argparse, cProfile, glob, importlib.util, io, json, pstats, sys, time
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R)); sys.path.insert(0, str(R / "vendor/NumSim-mine"))
sys.path.insert(0, str(R / "scripts"))
import probe_far_components_20260901 as PFC  # noqa: E402
import offline_harness_20260904 as OH  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="ctl_start900_x18_20260904")
    ap.add_argument("--config", default="canon_default_20260904")
    ap.add_argument("--index", type=int, default=18)
    ap.add_argument("--profile", type=int, default=1)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    tuning_path = str(R / ("evaluation/configs/%s.json" % a.config))
    sp = importlib.util.spec_from_file_location(
        "qb", R / "evaluation/controllers/vissim_stackelberg_adapter.py")
    qb = importlib.util.module_from_spec(sp); sp.loader.exec_module(qb)
    from src.models.state import TrafficState, ControlAction
    from src.models.demand import DemandStep
    import src.controllers.priced_wu_link_controller as PWL

    D = R / "evaluation/runs" / a.run
    states = sorted(glob.glob(str(D / "decisions_*/state_*.json")))
    actions = sorted(glob.glob(str(D / "decisions_*/action_*.json")))
    i = a.index
    prev = actions[i - 1] if i > 0 else str(R / "__missing.json")

    cfg, st, sj, meta, dm0, cal0, tun0 = OH.build(qb, TrafficState, tuning_path, states[i], prev)
    print("  green 패치 설치 %s" % {k: v for k, v in meta.items() if "monitor" in k or "signal" in k})
    tun = qb.load_optional_json(tuning_path)
    cal = qb.deep_update(dict(qb.load_optional_json(str(R / PFC.DEFAULT_CAL))),
                         tun.get("calibration_override") or {})
    dmp = str(tun.get("detector_mapping_json", "")).strip()
    dm = qb.load_optional_json(str(R / dmp) if not Path(dmp).is_absolute() else dmp)
    dm, _ = qb.filter_midblock_links_from_detector_mapping(dm, tun)
    hz = int(cfg.mpc.horizon_steps) + max(0, int(getattr(cfg.mpc, "leader_value_depth", 0)))
    forecast = qb.demand_from_state(sj, cfg, DemandStep, hz, cal, dm)
    previous = qb.control_from_json(Path(prev), cfg, ControlAction)
    ctl = qb.build_priced_wu_link_controller(cfg, tun)
    ctl.price_parallel_workers = 0

    # ---- 규모 ----
    from src.models.urban_queue_model import movement_specs
    specs = movement_specs(cfg)
    net = cfg.network
    print("=== 규모 ===")
    print("  movement 선언        %d" % len(specs))
    print("  신호                 %d" % len(list(net.signals)))
    print("  horizon_steps        %d   leader_value_depth %s"
          % (cfg.mpc.horizon_steps, getattr(cfg.mpc, "leader_value_depth", None)))
    print("  T_c_h                %.6f h   (제어구간 %.0f s)"
          % (cfg.simulation.T_c_h, cfg.simulation.T_c_h * 3600.0))
    for k in ("T_u_h", "urban_substeps", "substeps_per_step", "T_u_sec"):
        if hasattr(cfg.simulation, k):
            print("  %-20s %s" % (k, getattr(cfg.simulation, k)))
    print("  freeway_segments/link %s  ramps %s"
          % (getattr(net, "freeway_segments_per_link", "?"), len(list(getattr(net, "ramps", []) or []))))

    # ---- 롤아웃 호출 계수 ----
    orig = PWL.evaluate_price_point
    stats = {"n": 0, "t": 0.0}

    def counted(*args, **kw):
        t0 = time.perf_counter()
        try:
            return orig(*args, **kw)
        finally:
            stats["n"] += 1
            stats["t"] += time.perf_counter() - t0

    PWL.evaluate_price_point = counted
    print("\n=== _refresh_phase_prices 1회 ===")
    t0 = time.perf_counter()
    ctl._refresh_phase_prices(st, forecast, previous)
    wall = time.perf_counter() - t0
    PWL.evaluate_price_point = orig

    fol = ctl.nash_solver
    prices = fol.signal_phase_price or {}
    npx = sum(len(v) for v in prices.values())
    print("  총 벽시계            %.3f s" % wall)
    print("  evaluate_price_point %d 회   합 %.3f s   1회당 %.4f s"
          % (stats["n"], stats["t"], stats["t"] / max(stats["n"], 1)))
    print("  롤아웃이 차지하는 몫  %.1f%%" % (100.0 * stats["t"] / max(wall, 1e-9)))
    print("  산출 가격            신호 %d · 현시 %d" % (len(prices), npx))
    print("  _phase_price_rollout_count 진단 %s"
          % getattr(ctl, "_phase_price_rollout_count", None))

    # ---- 롤아웃 1회 프로파일 ----
    if a.profile:
        print("\n=== 롤아웃 1회 cProfile (누적시간 상위) ===")
        sig = next(iter(prices)) if prices else None
        base = ctl._phase_vector(previous, sig) if sig else None
        pr = cProfile.Profile(); pr.enable()
        for _ in range(5):
            ctl._global_ttt_with_phases(st, previous, forecast, sig, base)
        pr.disable()
        buf = io.StringIO()
        ps = pstats.Stats(pr, stream=buf).sort_stats("cumulative")
        ps.print_stats(28)
        for ln in buf.getvalue().splitlines():
            if ln.strip():
                print("  " + ln)
        print("\n=== 호출 횟수 상위 (내부 루프 규모) ===")
        buf2 = io.StringIO()
        pstats.Stats(pr, stream=buf2).sort_stats("ncalls").print_stats(18)
        for ln in buf2.getvalue().splitlines():
            if ln.strip():
                print("  " + ln)


if __name__ == "__main__":
    main()
