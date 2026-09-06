# -*- coding: utf-8 -*-
"""내가 오프라인으로 재현한 레버 가격이 실런 디스크 값과 같은가.

실런 진단 `wu_price_rollout_count` = 43 인데 오프라인 재현은 109 다. 같은 코드·같은 입력인데
계수가 2.5배 다르다. 값이 일치하면 계수 기록이 불완전한 것이고, 값이 다르면 실런이 실제로
더 싼 경로를 탄 것이다.
"""
import argparse, glob, importlib.util, json, sys
from collections import Counter
from pathlib import Path
import traceback

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R)); sys.path.insert(0, str(R / "vendor/NumSim-mine"))
sys.path.insert(0, str(R / "scripts"))
import offline_harness_20260904 as OH  # noqa: E402

PREFIXES = [("wu_b2_price_SC", "green"), ("wu_b3_meter_price_R", "meter"),
            ("wu_b3_vsl_price_FW", "vsl"), ("wu_f3_offset_price_SC", "offset")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="ctl_start900_x18_20260904")
    ap.add_argument("--config", default="canon_default_20260904")
    ap.add_argument("--index", type=int, default=18)
    ap.add_argument("--workers", type=int, default=0)
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
    ctl.price_parallel_workers = a.workers

    tally = Counter()
    for mod in (SWM, PWL):
        orig = mod.evaluate_price_point
        def mk(orig):
            def counted(*args, **kw):
                for fr in reversed(traceback.extract_stack()[:-1]):
                    if fr.name not in ("counted", "<lambda>", "serial", "<genexpr>"):
                        tally[fr.name] += 1; break
                return orig(*args, **kw)
            return counted
        mod.evaluate_price_point = mk(orig)

    ctl._maybe_refresh_signal_prices(st, forecast, previous)
    mine = dict(getattr(ctl, "_signal_price_meta", {}) or {})
    disk = json.loads(Path(actions[i]).read_text(encoding="utf-8")).get("diagnostics") or {}

    print("결정 %s" % Path(actions[i]).name)
    print("\n=== 롤아웃 계수 ===")
    for who, n in tally.most_common():
        print("   %-40s %3d" % (who, n))
    print("   %-40s %3d" % ("실측 합계", sum(tally.values())))
    print("   %-40s %s / 디스크 %s" % ("wu_price_rollout_count",
                                       mine.get("wu_price_rollout_count"),
                                       disk.get("wu_price_rollout_count")))
    print("\n=== 가격 값 대조 (내 재현 vs 실런 디스크) ===")
    print("   %-8s %5s %9s %14s %14s" % ("채널", "키수", "완전일치", "최대절대차", "최대상대차"))
    for pref, lab in PREFIXES:
        ks = [k for k in sorted(mine) if k.startswith(pref) and "_ref" not in k
              and not k.endswith(("_enabled", "_count", "_delta_sec", "_trust_sec"))]
        both = [k for k in ks if k in disk]
        if not both:
            print("   %-8s %5d   겹치는 키 없음" % (lab, len(ks)))
            continue
        ad = [abs(float(mine[k]) - float(disk[k])) for k in both]
        rl = [abs(float(mine[k]) - float(disk[k])) / max(abs(float(disk[k])), 1e-12) for k in both]
        print("   %-8s %5d %9d %14.4e %14.3f"
              % (lab, len(both), sum(1 for x in ad if x < 1e-9), max(ad), max(rl)))


if __name__ == "__main__":
    main()
