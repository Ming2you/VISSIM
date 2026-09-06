# -*- coding: utf-8 -*-
"""가격 롤아웃 43회가 채널별로 어떻게 쪼개지는가 — 호출자 기준 계측.

green / metering / vsl / offset 네 채널이 전부 켜져 있는데 롤아웃 총량이 43 이다.
green 만 17신호 x (lo,hi) = 34 를 쓰므로 나머지 세 채널의 몫을 직접 센다.
"""
import argparse, glob, importlib.util, json, sys, traceback
from collections import Counter
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R)); sys.path.insert(0, str(R / "vendor/NumSim-mine"))
sys.path.insert(0, str(R / "scripts"))
import offline_harness_20260904 as OH  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="ctl_start900_x18_20260904")
    ap.add_argument("--config", default="canon_default_20260904")
    ap.add_argument("--index", type=int, default=18)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    tuning_path = str(R / ("evaluation/configs/%s.json" % a.config))
    sp = importlib.util.spec_from_file_location(
        "qb", R / "evaluation/controllers/vissim_stackelberg_adapter.py")
    qb = importlib.util.module_from_spec(sp); sp.loader.exec_module(qb)
    from src.models.state import TrafficState, ControlAction
    from src.models.demand import DemandStep
    import src.controllers.stackelberg_wu_metered as SWM
    import src.controllers.priced_wu_link_controller as PWL

    D = R / "evaluation/runs" / a.run
    states = sorted(glob.glob(str(D / "decisions_*/state_*.json")))
    actions = sorted(glob.glob(str(D / "decisions_*/action_*.json")))
    i = a.index
    prev = actions[i - 1] if i > 0 else str(R / "__missing.json")
    cfg, st, sj, meta, dm, cal, tun = OH.build(qb, TrafficState, tuning_path, states[i], prev)
    hz = int(cfg.mpc.horizon_steps) + max(0, int(getattr(cfg.mpc, "leader_value_depth", 0)))
    forecast = qb.demand_from_state(sj, cfg, DemandStep, hz, cal, dm)
    previous = qb.control_from_json(Path(prev), cfg, ControlAction)
    ctl = qb.build_priced_wu_link_controller(cfg, tun)
    ctl.price_parallel_workers = 0

    tally = Counter()

    def wrap(mod, name):
        orig = getattr(mod, name)
        def counted(*args, **kw):
            stack = traceback.extract_stack()
            who = "?"
            for fr in reversed(stack[:-1]):
                if fr.name not in ("counted", "<lambda>", "serial", "<genexpr>"):
                    who = fr.name; break
            tally[who] += 1
            return orig(*args, **kw)
        setattr(mod, name, counted)
        return orig
    o1 = wrap(SWM, "evaluate_price_point")
    o2 = wrap(PWL, "evaluate_price_point")

    print("채널 스위치  green=%s meter=%s vsl=%s offset=%s  lite=%s spsa=%s" % (
        ctl.signal_price_enabled, ctl.metering_price_enabled, ctl.vsl_price_enabled,
        ctl.offset_price_enabled, getattr(ctl, "price_lite", None),
        getattr(ctl, "price_spsa_enabled", None)))
    print("레버 규모    신호 %d · 램프 %d · vsl키 %d" % (
        len(list(cfg.network.signals)), len(list(getattr(cfg.network, "ramps", []) or [])),
        len(previous.vsl or {})))

    ctl._maybe_refresh_signal_prices(st, forecast, previous)
    n_lever = sum(tally.values())
    print("\n=== 레버 가격 (B2/B3/F3) 롤아웃 %d회 ===" % n_lever)
    for who, n in tally.most_common():
        print("   %-38s %3d" % (who, n))
    print("   진단 wu_price_rollout_count = %s" % getattr(ctl, "_price_rollout_count", None))

    tally.clear()
    ctl._refresh_phase_prices(st, forecast, previous)
    print("\n=== 현시가격 롤아웃 %d회 ===" % sum(tally.values()))
    for who, n in tally.most_common():
        print("   %-38s %3d" % (who, n))
    print("\n총합 %d회" % (n_lever + sum(tally.values())))
    SWM.evaluate_price_point = o1; PWL.evaluate_price_point = o2


if __name__ == "__main__":
    main()
