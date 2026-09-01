# -*- coding: utf-8 -*-
"""실제 decide() 중에 far 가 **어떤 state 를 보는지** 기록한다.

far 는 관측 state 가 아니라 rollout 말단 `states[-1]` 에서 계산된다
(rollout_endpoint.py:406-409). 그래서 관측 시점 값(probe_far_components)만으로는
런에서 실제로 쓰인 n_u 를 알 수 없다. 여기서는 `stackelberg_mpc.mfd_far_cost_to_go`
를 몽키패치해 호출마다 성분을 적고, 어댑터의 램프용량 스왑 **안쪽**에서 돌게
설치 순서를 잡는다(어댑터 패치가 이 래퍼를 다시 감싸므로 우리 래퍼는 스왑된
용량을 본다).

vendor 는 한 줄도 안 고친다.
"""
import argparse
import glob
import importlib.util
import json
import os
import statistics
import sys
import time
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R))
sys.path.insert(0, str(R / "vendor/NumSim-mine"))

import probe_far_components_20260901 as PFC  # noqa: E402  (같은 폴더)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="canon_farbn_d00_x18_20260901")
    ap.add_argument("--tuning", default="")
    ap.add_argument("--indices", default="18")
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    os.environ.setdefault("RW_MAINLINE_SG_ONLY", "1")

    tuning_path = args.tuning or str(R / ("evaluation/configs/%s.json" % args.run))
    sp = importlib.util.spec_from_file_location(
        "qb", R / "evaluation/controllers/vissim_stackelberg_adapter.py")
    qb = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(qb)
    from src.models.state import TrafficState
    from src.models.demand import DemandStep
    from src.models.state import ControlAction
    import src.controllers.stackelberg_mpc as sm

    states = sorted(glob.glob(str(R / "evaluation/runs" / args.run / "decisions_*/state_*.json")))
    actions = sorted(glob.glob(str(R / "evaluation/runs" / args.run / "decisions_*/action_*.json")))
    rows = []
    for i in [int(x) for x in args.indices.split(",") if x.strip()]:
        prev = actions[i - 1] if i > 0 else str(R / "__missing_previous.json")
        cfg, st, sj, meta = PFC.build_cfg_and_state(qb, TrafficState, tuning_path, states[i], prev)

        calls = []
        base_fn = sm.mfd_far_cost_to_go  # 어댑터 램프패치가 이미 감싼 함수

        def recorder(c, s, _base=base_fn):
            comp = PFC.far_components(c, s)
            v = float(_base(c, s))
            comp["far_total_from_vendor"] = v
            calls.append(comp)
            return v

        # 플랜트 n_u(leader_base_accumulation)가 **몇 개 state 의 합**인지 직접 센다.
        from src.controllers.leader import Leader
        acc_calls = []
        _orig_acc = Leader._state_accumulation_base

        def acc_rec(self, sts, _o=_orig_acc):
            lst = list(sts)
            net = self.cfg.network
            per = [{
                "freeway": float(s.total_freeway_vehicles(net)),
                "off_ramp_storage": float(s.off_ramp_storage_occupancy_veh(net)),
                "objective_urban": float(s.objective_urban_vehicles(
                    net, self.cfg.leader.state_accumulation_exclude_boundary_legs)),
                "total_urban": float(s.total_urban_vehicles(net)),
                "protected": float(s.protected_accumulation_veh(net)),
                "boundary_in": float(s.boundary_in_queue_vehicles(net)),
            } for s in lst]
            base, excl = _o(self, lst)
            acc_calls.append({"n_states": len(lst), "base": float(base), "per_state": per})
            return base, excl

        Leader._state_accumulation_base = acc_rec
        sm.mfd_far_cost_to_go = recorder
        try:
            controller = qb.build_priced_wu_link_controller(cfg, {})
            tun = qb.load_optional_json(tuning_path)
            controller = qb.build_priced_wu_link_controller(cfg, tun)
            cal = qb.load_optional_json(str(R / PFC.DEFAULT_CAL))
            cal = qb.deep_update(dict(cal), tun.get("calibration_override") or {})
            dmp = str(tun.get("detector_mapping_json", "")).strip()
            dm = qb.load_optional_json(str(R / dmp) if not Path(dmp).is_absolute() else dmp)
            dm, _ = qb.filter_midblock_links_from_detector_mapping(dm, tun)
            hz = int(cfg.mpc.horizon_steps) + max(0, int(getattr(cfg.mpc, "leader_value_depth", 0)))
            forecast = qb.demand_from_state(sj, cfg, DemandStep, hz, cal, dm)
            previous = qb.control_from_json(Path(prev), cfg, ControlAction)
            t0 = time.perf_counter()
            ctl = controller.decide(st.copy(), forecast, previous, cfg)
            elapsed = time.perf_counter() - t0
        finally:
            sm.mfd_far_cost_to_go = base_fn
            Leader._state_accumulation_base = _orig_acc

        d0 = PFC.far_components(cfg, st)
        act = json.loads(Path(actions[i]).read_text(encoding="utf-8"))
        dg = act.get("diagnostics") or {}
        plant = float(dg.get("leader_base_accumulation", 0.0)) + float(
            dg.get("leader_boundary_in_queue_veh", 0.0))
        nus = [c["n_u_far"] for c in calls]
        tots = [c["far_total"] for c in calls]
        row = {
            "index": i, "sim_sec": float(sj.get("sim_sec", 0.0)),
            "decide_sec": elapsed, "far_calls": len(calls),
            "horizon_steps": int(cfg.mpc.horizon_steps),
            "leader_value_depth": int(getattr(cfg.mpc, "leader_value_depth", 0)),
            "n_u_far_at_d0_observed": d0["n_u_far"],
            "far_total_at_d0_observed": d0["far_total"],
            "n_u_plant_action_json": plant,
            "n_u_far_rollout_min": min(nus) if nus else None,
            "n_u_far_rollout_med": statistics.median(nus) if nus else None,
            "n_u_far_rollout_max": max(nus) if nus else None,
            "far_total_rollout_min": min(tots) if tots else None,
            "far_total_rollout_med": statistics.median(tots) if tots else None,
            "far_total_rollout_max": max(tots) if tots else None,
            "calls": calls,
            "acc_calls_n": len(acc_calls),
            "acc_n_states": sorted({c["n_states"] for c in acc_calls}),
            "acc_base_max": max((c["base"] for c in acc_calls), default=0.0),
            "acc_sample": acc_calls[-1] if acc_calls else None,
        }
        rows.append(row)
        print("[%2d] t=%.0f  far 호출 %d회 (%.1fs)  n_u d0=%.1f · rollout %.1f~%.1f (med %.1f)"
              % (i, row["sim_sec"], len(calls), elapsed, d0["n_u_far"],
                 row["n_u_far_rollout_min"] or 0.0, row["n_u_far_rollout_max"] or 0.0,
                 row["n_u_far_rollout_med"] or 0.0))
        if calls:
            c = calls[0]
            t = max(c["far_total"], 1e-12)
            print("     첫 호출  far=%.2f  urban %.2f(%.1f%%) main %.2f(%.1f%%) ramp %.2f(%.1f%%)"
                  % (c["far_total"], c["urban_term"], 100 * c["urban_term"] / t,
                     c["mainline_term"], 100 * c["mainline_term"] / t,
                     c["ramp_term"], 100 * c["ramp_term"] / t))
        print("     플랜트 n_u(액션 JSON) = %.1f · base 호출 %d회 · state 개수 %s · base_max %.1f"
              % (plant, len(acc_calls), row["acc_n_states"], row["acc_base_max"]))
        if acc_calls:
            s = acc_calls[-1]
            for k, p in enumerate(s["per_state"]):
                print("       state[%d] fw=%.1f offR=%.1f objUrb=%.1f totUrb=%.1f prot=%.1f bin=%.1f"
                      % (k, p["freeway"], p["off_ramp_storage"], p["objective_urban"],
                         p["total_urban"], p["protected"], p["boundary_in"]))

    out = args.out or ("outputs/far_at_decide_%s.json" % args.run)
    (R / out).write_text(json.dumps({"schema_version": "far-at-decide/1", "run": args.run,
                                     "rows": rows}, ensure_ascii=False, indent=1),
                         encoding="utf-8")
    print("-> %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
