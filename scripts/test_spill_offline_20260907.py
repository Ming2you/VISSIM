# -*- coding: utf-8 -*-
"""스필백 관측+가드 오프라인 검증: b0 상태(t=3600/4500)에서 ramp_spillback·state.ramp_queue·가드 강제값을 찍는다.
사용: python test_spill.py <adapter_path> [config_name] [run_name] [T ...]"""
import sys, io, json, importlib.util, time
from pathlib import Path


def main():
    R = Path("C:/Users/TRLAB/Desktop/찐찐막/VISSIM")
    sys.path.insert(0, str(R)); sys.path.insert(0, str(R / "vendor/NumSim-mine")); sys.path.insert(0, str(R / "scripts"))
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ADAPTER = sys.argv[1]
    CFGN = sys.argv[2] if len(sys.argv) > 2 else "h_SPILLTEST_20260907"
    RUN = sys.argv[3] if len(sys.argv) > 3 else "b0_rl_b0_lcd1000_x18_20260907"
    TS = [int(x) for x in sys.argv[4:]] or [3600, 4500]
    sp = importlib.util.spec_from_file_location("qb", R / ADAPTER); qb = importlib.util.module_from_spec(sp); sp.loader.exec_module(qb)
    import offline_harness_20260904 as OH
    from src.models.state import TrafficState, ControlAction
    from src.models.demand import DemandStep
    D = R / "evaluation/runs" / RUN / ("decisions_%s" % RUN)
    for T in TS:
        cfg, st, sj, meta, dm, cal, tun = OH.build(qb, TrafficState, str(R / "evaluation/configs" / (CFGN + ".json")),
                                                  str(D / ("state_%06d.json" % T)), str(D / ("action_%06d.json" % (T - 150))))
        summ = getattr(st, "local_observation_summary", {}) or {}
        print("T=%d spillback_obs=%s · ramp_spillback=%s · state.ramp_queue=%s · ramp_counts=%s" % (
            T, getattr(cfg.network, "ramp_spillback_obs", None),
            {k: round(v) for k, v in (summ.get("ramp_spillback") or {}).items()},
            {k: round(v) for k, v in st.ramp_queue.items()}, sj.get("ramp_counts")))
        fc = qb.demand_from_state(sj, cfg, DemandStep, int(cfg.mpc.horizon_steps), cal, dm)
        ctl = qb.control_from_json(D / ("action_%06d.json" % (T - 150)), cfg, ControlAction)
        c = qb.build_priced_wu_link_controller(cfg, tun); c.price_parallel_workers = 0
        t0 = time.time(); act = c.decide(st, fc, ctl, cfg); md = {}
        before = dict(act.ramp_metering)
        qb.apply_ramp_spillback_guard(act, cfg, st, tun.get("actuation", {}), md)
        live = json.load(io.open(D / ("action_%06d.json" % T), encoding="utf-8")).get("ramp_metering") or {}
        print("   decide %.0f s · 요청 %s → 가드 후 %s · live(b0) %s" % (
            time.time() - t0, {k: round(v) for k, v in before.items()}, {k: round(v) for k, v in act.ramp_metering.items()},
            {k: round(v) for k, v in live.items()}))
        print("   가드 메타:", {k: (round(v, 1) if isinstance(v, float) else v) for k, v in md.items() if k.startswith("rw_spill")})


if __name__ == "__main__":
    main()
