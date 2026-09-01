# -*- coding: utf-8 -*-
"""lambda -> inf 에서 팔로워가 낼 수 있는 Sigma nin 바닥을 후보집합 위에서 직접 측정한다.

배선은 probe_lambda_np_cap_20260901.py 와 동일(어댑터 재현 + 몽키패치). vendor 불변.
`_agent_net_inflow_veh` 호출을 (signal, p1) -> nin 으로 전부 수집해
  floor = sum_i min_{p1 in C_i} nin_i   (= lambda -> inf 극한, C_i 는 solver 가 실제 채점한 후보)
를 내고, 같은 결정의 진단 feas_min / 실현 Sigma nin 과 비교한다.
추가로 최소 후보에서 nin 을 movement kind 별로 분해한다.
"""
import argparse
import collections
import glob
import importlib.util
import json
import os
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R))
sys.path.insert(0, str(R / "vendor/NumSim-mine"))
import probe_far_components_20260901 as PFC  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="canon_farbn_d00_x18_20260901")
    ap.add_argument("--indices", default="20")
    ap.add_argument("--cap", type=float, default=10.0)
    ap.add_argument("--out", default="outputs/nin_floor_probe.json")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    os.environ.setdefault("RW_MAINLINE_SG_ONLY", "1")

    tuning_path = str(R / ("evaluation/configs/%s.json" % args.run))
    sp = importlib.util.spec_from_file_location(
        "qb", R / "evaluation/controllers/vissim_stackelberg_adapter.py")
    qb = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(qb)
    from src.models.state import TrafficState, ControlAction
    from src.models.demand import DemandStep
    from src.controllers.wu_faithful_follower import WuFaithfulFollower
    from src.controllers.wu_faithful_follower import distribute_phase_green

    # context = 하나의 _solve_followers 호출(= 같은 state/forecast_arrivals 객체).
    # 리더가 후보마다 팔로워를 다시 풀므로 문맥을 안 가르면 서로 다른 state 의 nin 이 섞인다.
    REC = {"ctx": {}, "order": [], "cur": None, "args": {}, "self": None}
    _orig_nin = WuFaithfulFollower._agent_net_inflow_veh

    def _ctx_key(state, fa, horizon_h):
        return (id(state), id(fa), round(float(horizon_h), 6))

    def _rec_nin(self, signal, green_p1, state, fa, horizon_h):
        v = _orig_nin(self, signal, green_p1, state, fa, horizon_h)
        k = _ctx_key(state, fa, horizon_h)
        if k not in REC["ctx"]:
            REC["ctx"][k] = {"nin": {}, "chosen": {}}
            REC["order"].append(k)
            REC["args"][k] = (state, fa, float(horizon_h))
        REC["ctx"][k]["nin"].setdefault(signal, {})[round(float(green_p1), 4)] = float(v)
        REC["cur"] = k
        REC["self"] = self
        return v

    _orig_solve = WuFaithfulFollower._solve_urban_agent_local

    def _rec_solve(self, signal, *a, **kw):
        out = _orig_solve(self, signal, *a, **kw)
        k = REC["cur"]
        if k is not None:
            REC["ctx"][k]["chosen"][signal] = (float(out[0]), float(out[3]))
        return out

    WuFaithfulFollower._agent_net_inflow_veh = _rec_nin
    WuFaithfulFollower._solve_urban_agent_local = _rec_solve

    _orig_init = WuFaithfulFollower.__init__

    def _patched_init(self, *a, **kw):
        _orig_init(self, *a, **kw)
        self.lambda_np_cap = float(args.cap)

    WuFaithfulFollower.__init__ = _patched_init

    states = sorted(glob.glob(str(R / "evaluation/runs" / args.run / "decisions_*/state_*.json")))
    actions = sorted(glob.glob(str(R / "evaluation/runs" / args.run / "decisions_*/action_*.json")))
    rows = []
    for i in [int(x) for x in args.indices.split(",") if x.strip()]:
        REC["ctx"].clear()
        REC["order"].clear()
        REC["args"].clear()
        REC["cur"] = None
        prev = actions[i - 1] if i > 0 else str(R / "__missing.json")
        disk = json.loads(Path(actions[i]).read_text(encoding="utf-8"))
        ddg = disk.get("diagnostics") or {}
        cfg, st, sj, meta = PFC.build_cfg_and_state(qb, TrafficState, tuning_path, states[i], prev)
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
        ctl = controller.decide(st.copy(), forecast, previous, cfg)
        dg = dict(ctl.diagnostics or {})

        solver = REC["self"]
        ctx_key = REC["order"][-1]
        ctx = REC["ctx"][ctx_key]
        state_used, fa, horizon_h = REC["args"][ctx_key]
        n_ctx = len(REC["order"])
        per = {}
        floor = 0.0
        ceil_ = 0.0
        chosen_sum = 0.0
        for sig, d in ctx["nin"].items():
            vals = sorted(d.items())
            mn = min(v for _, v in vals)
            mx = max(v for _, v in vals)
            argmn = min(vals, key=lambda kv: kv[1])[0]
            ch = ctx["chosen"].get(sig, (float("nan"), float("nan")))
            floor += mn
            ceil_ += mx
            if ch[1] == ch[1]:
                chosen_sum += ch[1]
            per[sig] = {
                "n_cand": len(vals),
                "p1_min": min(k for k, _ in vals),
                "p1_max": max(k for k, _ in vals),
                "nin_min": mn, "nin_max": mx, "nin_spread": mx - mn,
                "argmin_p1": argmn, "chosen_p1": ch[0], "chosen_nin": ch[1],
                "curve": {("%.2f" % k): v for k, v in vals},
            }
        decomp = {}
        net = cfg.network
        for sig in per:
            model = solver._local_models[sig]
            for tag, p1 in (("argmin", per[sig]["argmin_p1"]), ("chosen", per[sig]["chosen_p1"])):
                green = distribute_phase_green(net, float(p1), signal=sig)
                cyc = max(net.cycle_length, 1e-9)
                agg = collections.defaultdict(float)
                cap_agg = collections.defaultdict(float)
                avail_agg = collections.defaultdict(float)
                nbind = collections.defaultdict(int)
                ncnt = collections.defaultdict(int)
                for m in model.movements:
                    spec = solver._specs[m]
                    kind = model.kind_of[m]
                    av = max(0.0, float(state_used.urban_movement_queue.get(m, 0.0)))
                    if kind == "off_ramp":
                        inflow = solver._frozen_offramp_inflow(str(spec.get("off_ramp", "")), state_used)
                        av += inflow * horizon_h * float(spec.get("beta", 0.0))
                    else:
                        av += max(0.0, float(fa.get(m, 0.0)))
                    gf = green[model.phase_of[m]] / cyc
                    cap = horizon_h * gf * model.cap_flow_of[m]
                    s = min(av, max(0.0, cap))
                    agg[kind] += s
                    cap_agg[kind] += cap
                    avail_agg[kind] += av
                    ncnt[kind] += 1
                    if av <= cap + 1e-9:
                        nbind[kind] += 1
                decomp.setdefault(tag, {})[sig] = {
                    "served": dict(agg), "cap": dict(cap_agg), "avail": dict(avail_agg),
                    "n_mov": dict(ncnt), "n_arrival_limited": dict(nbind)}
        tot = {}
        for tag in decomp:
            a = collections.defaultdict(float)
            n = collections.defaultdict(int)
            nb = collections.defaultdict(int)
            for sig, dd in decomp[tag].items():
                for k, v in dd["served"].items():
                    a["served_" + k] += v
                for k, v in dd["cap"].items():
                    a["cap_" + k] += v
                for k, v in dd["avail"].items():
                    a["avail_" + k] += v
                for k, v in dd["n_mov"].items():
                    n[k] += v
                for k, v in dd["n_arrival_limited"].items():
                    nb[k] += v
            tot[tag] = {"agg": dict(a), "n_mov": dict(n), "n_arrival_limited": dict(nb)}
        row = {
            "index": i, "sim_sec": sj.get("sim_sec"), "cap": args.cap,
            "replay_sum_nin": float(dg.get("wu_faithful_np_sum_nin", 0.0)),
            "replay_feas_min": float(dg.get("leader_np_follower_feasible_min", 0.0)),
            "replay_feas_max": float(dg.get("leader_np_follower_feasible_max", 0.0)),
            "replay_lam_path": dg.get("wu_faithful_np_pd_lam_path", ""),
            "disk_sum_nin": float(ddg.get("wu_faithful_np_sum_nin", 0.0)),
            "disk_feas_min": float(ddg.get("leader_np_follower_feasible_min", 0.0)),
            "horizon_h": horizon_h,
            "candidate_floor_sum_min_nin": floor,
            "candidate_ceiling_sum_max_nin": ceil_,
            "chosen_sum_nin": chosen_sum,
            "n_signals": len(per), "n_contexts": n_ctx,
            "per_signal": per, "kind_totals": tot,
        }
        rows.append(row)
        print("[%d] t=%s  sum_nin(real)=%.2f  cand_floor=%.2f  cand_ceiling=%.2f  feas_min(diag)=%.2f  lam=%s"
              % (i, sj.get("sim_sec"), row["replay_sum_nin"], floor, ceil_,
                 row["replay_feas_min"], row["replay_lam_path"]))
        for tag in tot:
            print("   %-7s served in=%.1f off=%.1f out=%.1f | arrival-limited %s / n_mov %s"
                  % (tag, tot[tag]["agg"].get("served_boundary_in", 0.0),
                     tot[tag]["agg"].get("served_off_ramp", 0.0),
                     tot[tag]["agg"].get("served_boundary_out", 0.0),
                     dict(tot[tag]["n_arrival_limited"]), dict(tot[tag]["n_mov"])))
        (R / args.out).write_text(
            json.dumps({"schema": "nin-floor/1", "run": args.run, "rows": rows},
                       ensure_ascii=False, indent=1), encoding="utf-8")
    print("-> %s" % args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
