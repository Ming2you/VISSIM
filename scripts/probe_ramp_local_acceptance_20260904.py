# -*- coding: utf-8 -*-
"""`install_ramp_aware_phase_local` 인수시험 — VISSIM 없이.

통과 조건 넷.
  1. 패치가 발화한다 (phase_local_ramp_aware_enabled=1, setup_built>0, setup_error=0)
  2. has_ramps 신호(SC1001·SC1004)의 국소비용이 **녹색에 따라 변한다** (옛 경로는 항등 0)
  3. non-ramp 신호는 **비트 동일** (패치가 그 경로를 안 건드린다)
  4. in_gne 채점식 `local + w·Σp·Δg` 이 이제 내부해를 가질 수 있다
     — 꼭짓점 점수가 최선이 아닌 지점이 생기는지 본다
"""
import argparse
import glob
import importlib.util
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R))
sys.path.insert(0, str(R / "vendor/NumSim-mine"))
sys.path.insert(0, str(R / "scripts"))
import offline_harness_20260904 as OH  # noqa: E402

RUN = "ctl_start900_x18_20260904"
RAMP = ("SC1001", "SC1004")
NONRAMP = ("SC1", "SC5", "SC109", "SC1002")


def build(qb, cfg_name, index):
    from src.models.state import TrafficState, ControlAction
    from src.models.demand import DemandStep
    D = R / "evaluation/runs" / RUN
    S = sorted(glob.glob(str(D / "decisions_*/state_*.json")))
    A = sorted(glob.glob(str(D / "decisions_*/action_*.json")))
    prev = A[index - 1]
    cfg, st, sj, meta, dm, cal, tun = OH.build(
        qb, TrafficState, str(R / ("evaluation/configs/%s.json" % cfg_name)), S[index], prev)
    hz = int(cfg.mpc.horizon_steps) + max(0, int(getattr(cfg.mpc, "leader_value_depth", 0)))
    fc = qb.demand_from_state(sj, cfg, DemandStep, hz, cal, dm)
    previous = qb.control_from_json(Path(prev), cfg, ControlAction)
    ctl = qb.build_priced_wu_link_controller(cfg, tun)
    ctl.price_parallel_workers = 0
    return cfg, st, fc, previous, ctl


def sweep(ctl, st, fc, previous, signals, label):
    """각 신호에서 p3 를 훑으며 국소비용을 잰다. 반환 {signal: [(g, cost), ...]}"""
    from src.models.state import MODEL_PHASES, phase_key
    fol = ctl.nash_solver
    fol.phase_price_local_cost_model = str(
        getattr(ctl, "phase_price_local_cost_model", "drain"))
    ctx = fol._phase_refine_context(st, previous, fc)
    out = {}
    print("  [%s] ctx = %s" % (label, "phased" if ctx is not None else "None(drain)"))
    for sig in signals:
        setup = fol._phase_refine_signal_setup(sig, st, ctx) if ctx is not None else None
        base = {p: float(previous.green_times.get(phase_key(sig, p), 0.0)) for p in MODEL_PHASES}
        live = [p for p in MODEL_PHASES if base[p] > 0.0]
        if "p3" not in live or len(live) < 3:
            tgt = live[-1]
        else:
            tgt = "p3"
        tot = sum(base[p] for p in live)
        rows = []
        for g in (20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 78.0):
            vec = dict(base)
            others = [p for p in live if p != tgt]
            rest = max(0.0, tot - g)
            for p in others:
                vec[p] = rest / len(others)
            vec[tgt] = g
            if setup is not None:
                c = fol._phase_local_cost_phased(sig, vec, setup, ctx)
            else:
                c = fol.phase_shape_local_cost(sig, vec, st)
            rows.append((g, float(c)))
        out[sig] = (tgt, rows, setup is not None)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", type=int, default=18)
    ap.add_argument("--old", default="canon_default_20260904")
    ap.add_argument("--new", default="arm_ramplocal_ingne900_20260904")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    sp = importlib.util.spec_from_file_location(
        "qb", R / "evaluation/controllers/vissim_stackelberg_adapter.py")
    qb = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(qb)

    print("=== 옛 경로 (canon_default, ramp_local_model 없음) ===")
    _, st0, fc0, pv0, c0 = build(qb, a.old, a.index)
    old = sweep(c0, st0, fc0, pv0, RAMP + NONRAMP, "old")
    print("   패치 진단 %s" % {k: v for k, v in qb._RAMPLOCAL_LAST.items()})

    qb._RAMPLOCAL_LAST.clear()
    qb._RAMP_ERR.clear()
    print("\n=== 새 경로 (ramp_local_model=ramp_aware) ===")
    _, st1, fc1, pv1, c1 = build(qb, a.new, a.index)
    new = sweep(c1, st1, fc1, pv1, RAMP + NONRAMP, "new")
    print("   패치 진단 %s" % {k: v for k, v in qb._RAMPLOCAL_LAST.items()})
    if qb._RAMP_ERR:
        print("   *** setup 오류: %s" % list(qb._RAMP_ERR)[:3])

    print("\n=== 조건 2: has_ramps 신호의 국소비용이 녹색에 반응하는가 ===")
    ok2 = True
    for sig in RAMP:
        tgt, ro, _ = old[sig]
        _, rn, has = new[sig]
        so = max(c for _, c in ro) - min(c for _, c in ro)
        sn = max(c for _, c in rn) - min(c for _, c in rn)
        print("   %-8s (%s)  옛 스프레드 %.6f   새 스프레드 %.6f   setup=%s"
              % (sig, tgt, so, sn, has))
        print("        옛 %s" % ["%.3f" % c for _, c in ro])
        print("        새 %s" % ["%.3f" % c for _, c in rn])
        if sn <= 1.0e-9:
            ok2 = False
    print("   -> %s" % ("PASS" if ok2 else "*** FAIL: 여전히 평평하다 ***"))

    print("\n=== 조건 3: non-ramp 신호는 비트 동일인가 ===")
    ok3 = True
    for sig in NONRAMP:
        _, ro, _ = old[sig]
        _, rn, _ = new[sig]
        d = max(abs(x - y) for (_, x), (_, y) in zip(ro, rn))
        print("   %-8s 최대 절대차 %.3e %s" % (sig, d, "" if d < 1e-12 else "  *** 다르다 ***"))
        if d >= 1e-12:
            ok3 = False
    print("   -> %s" % ("PASS" if ok3 else "*** FAIL ***"))

    print("\n=== 조건 4: 꼭짓점이 더 이상 자동 최선이 아닌가 (국소항만으로) ===")
    for sig in RAMP:
        _, rn, _ = new[sig]
        best = min(rn, key=lambda r: r[1])
        print("   %-8s 국소비용 최소 = g %.0f (꼭짓점 78 의 비용 %.3f, 최소 %.3f)"
              % (sig, best[0], dict(rn)[78.0], best[1]))


if __name__ == "__main__":
    main()
