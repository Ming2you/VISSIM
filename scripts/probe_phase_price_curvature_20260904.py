# -*- coding: utf-8 -*-
"""현시가격의 선형 외삽이 어디까지 유효한가 — 실제 전역 롤아웃 곡선을 직접 잰다.

가격 g_i 는 `_refresh_phase_prices` 가 **delta=6초** 유한차분으로 만든다. 그런데 정련과
GNE 는 그 미분에 Δg 를 곱해 점수를 매기므로, 실측된 적 없는 **36~48초** 이동을 선형으로
외삽한다. `served = min(available, green x cap)` 이 포화하면 응답은 오목이고 외삽은
이득을 과대평가한다 — 그러면 꼭짓점은 최적이 아니라 외삽 오차의 산물이다.

측정: 가격 방향 `_phase_direction(signal, base, pid, d)` 를 d = 0,6,12,...  로 늘려가며
`_global_ttt_with_phases` 를 실제로 굴린다. 선형예측(가격 x d)과 맞대면 끝난다.

vendor 는 한 줄도 안 고친다.
"""
import argparse, glob, importlib.util, json, os, sys
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
    ap.add_argument("--index", type=int, default=6)
    ap.add_argument("--signals", default="SC1001,SC1004,SC105")
    ap.add_argument("--deltas", default="0,3,6,12,18,24,30,36,42,48")
    ap.add_argument("--out", default="outputs/phase_price_curvature_20260904.json")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    tuning_path = str(R / ("evaluation/configs/%s.json" % a.config))
    sp = importlib.util.spec_from_file_location(
        "qb", R / "evaluation/controllers/vissim_stackelberg_adapter.py")
    qb = importlib.util.module_from_spec(sp); sp.loader.exec_module(qb)
    from src.models.state import TrafficState, ControlAction
    from src.models.demand import DemandStep

    D = R / "evaluation/runs" / a.run
    states = sorted(glob.glob(str(D / "decisions_*/state_*.json")))
    actions = sorted(glob.glob(str(D / "decisions_*/action_*.json")))
    i = a.index
    prev = actions[i - 1] if i > 0 else str(R / "__missing.json")
    print("결정 %s   직전 %s" % (Path(actions[i]).name, Path(prev).name))

    cfg, st, sj, meta, _dm, _cal, _tun = OH.build(qb, TrafficState, tuning_path, states[i], prev)
    print("monitor green 패치 %s · 모듈 %s" % (
        meta.get('monitor_fixed_signal_patch_enabled'),
        meta.get('monitor_fixed_signal_patched_module_count')))
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
    ctl.price_parallel_workers = 0                       # 직렬. VISSIM 이 도는 중이다
    fol = ctl.nash_solver
    # 국소항은 실런과 **같은 채점기**여야 한다. `install_phased_price_local` 이 쓰는 경로를
    # 그대로 복제한다 — drain 을 직접 부르면 실런이 안 쓰는 모형을 재게 된다.
    fol.phase_price_local_cost_model = str(getattr(ctl, "phase_price_local_cost_model", "drain"))
    ctx = fol._phase_refine_context(st, previous, forecast)
    print("국소 채점기 = %s" % ("phased" if ctx is not None else "drain(폴백)"))

    def local_of(sig, vec, setup):
        if ctx is None or setup is None:
            return float(fol.phase_shape_local_cost(sig, vec, st))
        return float(fol._phase_local_cost_phased(sig, vec, setup, ctx))

    disk = json.loads(Path(actions[i]).read_text(encoding="utf-8"))
    dg = disk.get("diagnostics") or {}
    gt = disk.get("green_times") or {}
    deltas = [float(x) for x in a.deltas.split(",") if x.strip()]

    base_ttt = ctl._global_ttt_with_phases(st, previous, forecast, "", None)
    print("기준 전역 TTT %.4f\n" % base_ttt)

    out = {"run": a.run, "index": i, "base_ttt": base_ttt, "signals": {}}
    for sig in [s for s in a.signals.split(",") if s.strip()]:
        base = ctl._phase_vector(previous, sig)
        price = {p: float(dg["wu_phase_price_%s_%s" % (sig, p)])
                 for p in ("p1", "p2", "p3", "p4")
                 if ("wu_phase_price_%s_%s" % (sig, p)) in dg}
        if not price:
            print("%s  가격 없음 — 건너뜀" % sig); continue
        tgt = min(price, key=lambda p: price[p])          # 가장 음수 = 정련이 미는 현시
        setup = fol._phase_refine_signal_setup(sig, st, ctx) if ctx is not None else None
        base_local = local_of(sig, base, setup)
        committed = {k.split("_")[-1]: float(v) for k, v in gt.items() if k.startswith(sig + "_")}
        print("%s  기준벡터 %s" % (sig, {k: round(v, 1) for k, v in base.items()}))
        print("        가격 %s   미는 현시 %s (%.5f)" % (
            {k: round(v, 4) for k, v in price.items()}, tgt, price[tgt]))
        print("        커밋 %s" % {k: round(v, 1) for k, v in committed.items()})
        print("   %6s %9s %11s %11s %11s %11s" % (
            "d(초)", tgt, "실제ΔTTT", "정련점수Δ", "국소Δ", "가격항"))
        rows = []
        for d in deltas:
            moved = base if d == 0.0 else ctl._phase_direction(sig, base, tgt, d)
            if moved is None:
                continue
            ttt = ctl._global_ttt_with_phases(st, previous, forecast, sig, moved)
            loc = local_of(sig, moved, setup)
            eff = float(moved.get(tgt, 0.0)) - float(base.get(tgt, 0.0))   # 실제 이동량(클리핑 후)
            lin = sum(price.get(q, 0.0) * (float(moved.get(q, 0.0)) - float(base.get(q, 0.0)))
                      for q in ("p1", "p2", "p3", "p4"))
            rows.append({"d": d, "g_target": moved.get(tgt), "eff_move": eff,
                         "ttt": ttt, "d_ttt": ttt - base_ttt, "linear": lin,
                         "local_d": loc - base_local,
                         "vec": {k: round(float(v), 2) for k, v in moved.items()}})
            print("   %6.0f %9.1f %11.4f %11.4f %11.4f %11.4f" % (
                d, moved.get(tgt, 0.0), ttt - base_ttt, (loc - base_local) + lin,
                loc - base_local, lin))
        # 실제로 커밋된 벡터 그 자체
        if committed:
            ttt_c = ctl._global_ttt_with_phases(st, previous, forecast, sig, committed)
            loc_c = local_of(sig, committed, setup)
            lin_c = sum(price.get(p, 0.0) * (committed.get(p, 0.0) - base.get(p, 0.0))
                        for p in ("p1", "p2", "p3", "p4"))
            print("   %6s %9.1f %11.4f %11.4f %11.4f %11.4f   <- 실제 커밋" % (
                "커밋", committed.get(tgt, 0.0), ttt_c - base_ttt,
                (loc_c - base_local) + lin_c, loc_c - base_local, lin_c))
            rows.append({"d": "committed", "g_target": committed.get(tgt), "ttt": ttt_c,
                         "d_ttt": ttt_c - base_ttt, "linear": lin_c,
                         "local_d": loc_c - base_local, "vec": committed})
        print()
        out["signals"][sig] = {"base": base, "price": price, "target": tgt,
                               "base_local": base_local, "rows": rows}
    Path(R / a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("저장 %s" % a.out)


if __name__ == "__main__":
    main()
