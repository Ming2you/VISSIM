# -*- coding: utf-8 -*-
"""in_gne 벡터 탐색이 실제로 무엇을 고를지 VISSIM 없이 예측한다.

`_solve_urban_agent_local` 의 in_gne 블록(priced_wu_link_controller.py:600-690)을 그대로
복제한다 — 시드 둘(직전 커밋 · 상류 p1 해) · trust region · 쌍교환 후보 · 라운드 반복.
가격은 실런 디스크값(`wu_phase_price_*`)을 쓴다.

옛 채점기(local 항등 0)와 새 채점기(ramp-aware)를 같은 가격·같은 시드로 맞대면
"패치가 커밋 벡터를 바꾸는가" 가 런 없이 나온다.
"""
import argparse
import glob
import importlib.util
import io
import json
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R))
sys.path.insert(0, str(R / "vendor/NumSim-mine"))
sys.path.insert(0, str(R / "scripts"))
import offline_harness_20260904 as OH  # noqa: E402

RUN = "ctl_start900_x18_20260904"


def pick(fol, ctx, signal, state, previous, price, weight, trust, rounds, steps):
    """in_gne 블록의 탐색을 복제한다. 반환 (best_vec, best_obj, moved_sec)."""
    from src.models.state import MODEL_PHASES, phase_key
    setup = fol._phase_refine_signal_setup(signal, state, ctx)

    def scored(vec):
        if setup is not None:
            local = fol._phase_local_cost_phased(signal, vec, setup, ctx)
        else:
            local = fol.phase_shape_local_cost(signal, vec, state)
        ext = sum(float(price.get(pid, 0.0)) * (float(vec.get(pid, 0.0)) - float(ref.get(pid, 0.0)))
                  for pid in MODEL_PHASES)
        return float(local) + weight * ext

    ref = {pid: float(previous.green_times.get(phase_key(signal, pid), 0.0))
           for pid in MODEL_PHASES}
    anchor = dict(ref)

    def in_trust(vec):
        if trust is None:
            return True
        return all(abs(float(vec.get(p, 0.0)) - float(anchor.get(p, 0.0))) <= float(trust) + 1e-9
                   for p in MODEL_PHASES)

    best = dict(ref)
    best_obj = scored(best)
    for _r in range(max(1, int(rounds))):
        moved = False
        for step in steps:
            for cand in fol._phase_exchange_candidates(signal, best, float(step)):
                if not in_trust(cand):
                    continue
                o = scored(cand)
                if o < best_obj - 1e-12:
                    best, best_obj = cand, o
                    moved = True
        if not moved:
            break
    mv = sum(abs(float(best.get(p, 0.0)) - float(ref.get(p, 0.0))) for p in MODEL_PHASES) / 2.0
    return best, best_obj, mv, setup is not None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--indices", default="6,18,30")
    ap.add_argument("--signals", default="SC1001,SC1004,SC1,SC109")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    sp = importlib.util.spec_from_file_location(
        "qb", R / "evaluation/controllers/vissim_stackelberg_adapter.py")
    qb = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(qb)
    from src.models.state import TrafficState, ControlAction, MODEL_PHASES, phase_key
    from src.models.demand import DemandStep

    D = R / "evaluation/runs" / RUN
    S = sorted(glob.glob(str(D / "decisions_*/state_*.json")))
    A = sorted(glob.glob(str(D / "decisions_*/action_*.json")))
    sigs = [x for x in a.signals.split(",") if x.strip()]

    for cfg_name, label in (("canon_default_20260904", "옛 채점기"),
                            ("arm_ramplocal_ingne900_20260904", "새 채점기")):
        print("\n########## %s (%s) ##########" % (label, cfg_name))
        for idx in [int(x) for x in a.indices.split(",") if x.strip()]:
            prev = A[idx - 1]
            cfg, st, sj, meta, dm, cal, tun = OH.build(
                qb, TrafficState, str(R / ("evaluation/configs/%s.json" % cfg_name)), S[idx], prev)
            hz = int(cfg.mpc.horizon_steps) + max(0, int(getattr(cfg.mpc, "leader_value_depth", 0)))
            fc = qb.demand_from_state(sj, cfg, DemandStep, hz, cal, dm)
            previous = qb.control_from_json(Path(prev), cfg, ControlAction)
            ctl = qb.build_priced_wu_link_controller(cfg, tun)
            ctl.price_parallel_workers = 0
            fol = ctl.nash_solver
            fol.phase_price_local_cost_model = str(
                getattr(ctl, "phase_price_local_cost_model", "drain"))
            ctx = fol._phase_refine_context(st, previous, fc)
            disk = json.loads(Path(A[idx]).read_text(encoding="utf-8")).get("diagnostics") or {}
            trust = float(getattr(ctl, "signal_marginal_price_trust_sec", 6.0) or 6.0)
            rounds = int(getattr(ctl, "phase_price_refine_rounds", 12) or 12)
            steps = tuple(getattr(cfg.mpc, "phase_price_exchange_steps_sec", (6.0,)))
            weight = float(getattr(ctl, "phase_price_weight", 1.0))
            print("  --- 결정 %d (t=%d) trust %.1f · rounds %d · steps %s ---"
                  % (idx, 150 * idx, trust, rounds, steps))
            for sig in sigs:
                price = {p: float(disk["wu_phase_price_%s_%s" % (sig, p)])
                         for p in MODEL_PHASES if ("wu_phase_price_%s_%s" % (sig, p)) in disk}
                if not price:
                    continue
                best, obj, mv, has = pick(fol, ctx, sig, st, previous, price,
                                          weight, trust, rounds, steps)
                base = {p: round(float(previous.green_times.get(phase_key(sig, p), 0.0)), 1)
                        for p in MODEL_PHASES}
                print("     %-8s setup=%-5s 기준 %s -> 선택 %s  이동 %.1f초"
                      % (sig, has, base,
                         {p: round(float(best.get(p, 0.0)), 1) for p in MODEL_PHASES}, mv))


if __name__ == "__main__":
    main()
