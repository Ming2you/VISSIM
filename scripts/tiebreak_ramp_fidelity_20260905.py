# -*- coding: utf-8 -*-
"""동률 타이브레이크 / B 진단: 램프 기구 충실도.

두 런(기준·B)에서 표본 결정마다
  (1) 모형이 freeway 에 넘기는 u_on(veh/h)  — estimate_onramp_reservoir_inflow (B 는 leg_split 대체판)
  (2) plant 실측: W_out 발 램프 유입 = 링크평가 RM 커넥터 10480+10484(D, 링크 31 발)·10646+10681(F, 링크 68 발)
      (10482/10490/10644/10639 는 정지선 앞 peel-off = 외생이라 제외). state_{t+150} 의 far_measurement 가
      [t, t+150] 구간이라 u_on(t) 와 맞댄다.
  (3) W_out 점유: plant 링크 31/68 재차 vs 모형 (cap − urban_link_storage)
를 표로 낸다. 사용: python tiebreak_ramp_fidelity_20260905.py <기준런> <B런> [t1,t2,...]
"""
import csv
import glob
import importlib.util
import io
import json
import sys
from pathlib import Path

R = Path(r"C:\Users\TRLAB\Desktop\찐찐막\VISSIM")
sys.path.insert(0, str(R)); sys.path.insert(0, str(R / "vendor/NumSim-mine")); sys.path.insert(0, str(R / "scripts"))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RAMPS = ("R_D_W", "R_D_E", "R_F_W", "R_F_E")
WOUT_CONN = {"R_D_W": ["10480"], "R_D_E": ["10484"], "R_F_W": ["10646"], "R_F_E": ["10681"]}
PEEL_CONN = {"R_D_W": ["10482"], "R_D_E": ["10490"], "R_F_W": ["10644"], "R_F_E": ["10639"]}
WOUT_LINK = {"SC1001_W_out": "31", "SC1004_W_out": "68"}


def measured(run, t):
    """state_t 의 far_measurement (직전 150 s 구간)."""
    p = sorted(glob.glob(str(R / "evaluation/runs" / run / "decisions_*" / ("state_%06d.json" % t))))
    if not p:
        return None
    lv = ((json.load(io.open(p[0], encoding="utf-8")).get("local_observation") or {}).get("far_measurement") or {}).get("link_volume_veh_h") or {}
    out = {}
    for r_ in RAMPS:
        out[r_] = (sum(float(lv.get(c, 0.0)) for c in WOUT_CONN[r_]), sum(float(lv.get(c, 0.0)) for c in PEEL_CONN[r_]))
    return out


def link_counts(run, t):
    f = glob.glob(str(R / "evaluation/runs" / run / "bottleneck_links_*.csv"))
    o = {}
    for x in csv.DictReader(io.open(f[0], encoding="utf-8", errors="replace")):
        if int(float(x["sim_sec"])) == t:
            o[str(x["link"])] = float(x["count"] or 0)
    return o


import os
def config_of(run):
    env = os.environ.get("TIEBREAK_CFG_" + run)
    if env:
        return env
    prov = glob.glob(str(R / "evaluation/runs" / run / "run_provenance_*.json"))
    if prov:
        t = io.open(prov[0], encoding="utf-8", errors="replace").read()
        import re
        m = re.search(r"evaluation[\\/]configs[\\/]([A-Za-z0-9_]+)\.json", t)
        if m:
            return m.group(1)
    raise RuntimeError("config 를 provenance 에서 못 찾음: " + run)


def main():
    base, bname = sys.argv[1], sys.argv[2]
    ts = [int(x) for x in (sys.argv[3].split(",") if len(sys.argv) > 3 else "1200,1800,2400,3000,3600,4200".split(","))]
    sp = importlib.util.spec_from_file_location("qb", R / "evaluation/controllers/vissim_stackelberg_adapter.py")
    qb = importlib.util.module_from_spec(sp); sp.loader.exec_module(qb)
    import offline_harness_20260904 as OH
    from src.models.state import TrafficState, ControlAction
    from src.models.demand import DemandStep
    import src.controllers.wu_distributed as wd
    # 클래스 몽키패치가 프로세스에 남으므로 런마다 새 프로세스로 돌리는 것이 정석이지만,
    # 두 런의 차이는 cfg(leg_split)이고 런타임 패치는 cfg 플래그로 분기하므로 같은 프로세스에서도 된다.
    for run in (base, bname):
        cfgn = config_of(run)
        print("=== %s (config %s) ===" % (run, cfgn))
        print("  %6s | %-38s | %-38s | %s" % ("t", "u_on 모형 [D_W D_E F_W F_E]", "실측 W_out발 [D_W D_E F_W F_E]", "peel-off 실측 · W_out 점유 plant/모형 31,68"))
        D = R / "evaluation/runs" / run
        S = sorted(glob.glob(str(D / "decisions_*/state_*.json"))); A = sorted(glob.glob(str(D / "decisions_*/action_*.json")))
        idx = {int(Path(s).name[-11:-5]): k for k, s in enumerate(S)}
        for t in ts:
            if t not in idx or idx[t] == 0:
                continue
            i = idx[t]
            try:
                cfg, st, sj, meta, dm, cal, tun = OH.build(qb, TrafficState, str(R / "evaluation/configs" / (cfgn + ".json")), S[i], A[i - 1])
                fc = qb.demand_from_state(sj, cfg, DemandStep, int(cfg.mpc.horizon_steps), cal, dm)
                ctl = qb.control_from_json(Path(A[i]), cfg, ControlAction)
                u = wd.estimate_onramp_reservoir_inflow(st, ctl, fc[0], cfg)
                net = cfg.network
                occ = {}
                for lk, plant_link in WOUT_LINK.items():
                    cap = float(net.urban_link_storage_veh.get(lk, 0.0))
                    occ[plant_link] = cap - float(st.urban_link_storage.get(lk, cap))
            except Exception as e:
                print("  %6d | 실패 %r" % (t, e)); continue
            m = measured(run, t + 150) or {r_: (float("nan"), float("nan")) for r_ in RAMPS}
            lc = link_counts(run, t)
            print("  %6d | %-38s | %-38s | peel %s · 31 %.0f/%.0f · 68 %.0f/%.0f" % (
                t, " ".join("%6.0f" % u.get(r_, 0) for r_ in RAMPS), " ".join("%6.0f" % m[r_][0] for r_ in RAMPS),
                " ".join("%4.0f" % m[r_][1] for r_ in RAMPS), lc.get("31", 0), occ.get("31", 0), lc.get("68", 0), occ.get("68", 0)))


if __name__ == "__main__":
    main()
