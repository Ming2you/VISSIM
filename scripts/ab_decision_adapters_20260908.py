# -*- coding: utf-8 -*-
"""어댑터 두 벌로 같은 결정을 돌려 **비트 동치**와 소요시간을 대조한다 (2026-09-08).

용도: 결과 불변이라고 주장하는 성능 패치를 실런 전에 검증한다. 녹색분율 hot path 패치
(상수 재계산 걷어내기)가 첫 대상이다.

사용: python ab_decision_adapters_20260908.py <adapter_A> <adapter_B> <config> <run> <T> [workers]
"""
import importlib.util
import io
import json
import subprocess
import sys
import time
from pathlib import Path

R = Path("C:/Users/TRLAB/Desktop/찐찐막/VISSIM")

CHILD = r'''
import importlib.util, io, json, os, sys, time
from pathlib import Path
R = Path(os.environ["VR"])
sys.path.insert(0, str(R)); sys.path.insert(0, str(R / "vendor/NumSim-mine"))
sys.path.insert(0, str(R / "scripts")); sys.path.insert(0, str(R / "evaluation/controllers"))
ADAPTER, CFGN, RUN, T, W, OUT = sys.argv[1:7]
sp = importlib.util.spec_from_file_location("qb", ADAPTER)
qb = importlib.util.module_from_spec(sp); sp.loader.exec_module(qb)
import offline_harness_20260904 as OH
from src.models.state import TrafficState
from src.models.demand import DemandStep
D = R / "evaluation/runs" / RUN / ("decisions_%s" % RUN)
cfg, st, sj, meta, dm, cal, tun = OH.build(
    qb, TrafficState, str(R / "evaluation/configs" / (CFGN + ".json")),
    str(D / ("state_%06d.json" % int(T))), str(D / ("action_%06d.json" % (int(T) - 150))))
fc = qb.demand_from_state(dict(sj), cfg, DemandStep, int(cfg.mpc.horizon_steps), cal, dm)
ctrl = qb.build_priced_wu_link_controller(cfg, tun)
ctrl.price_parallel_workers = int(W)
t0 = time.time()
act = ctrl.decide(st, fc, None, cfg)
wall = time.time() - t0
def dump(a):
    out = {}
    for name in ("ramp_metering", "vsl", "green_times", "offsets", "inflow_outflow_allocation"):
        v = getattr(a, name, None)
        if isinstance(v, dict):
            out[name] = {str(k): (round(float(x), 9) if isinstance(x, (int, float)) else str(x))
                         for k, x in sorted(v.items())}
    for name in ("N_P_star", "N_UF_star"):
        v = getattr(a, name, None)
        if v is not None:
            out[name] = round(float(v), 9)
    dg = getattr(a, "diagnostics", None)
    if isinstance(dg, dict):
        out["diagnostics"] = {str(k): (round(float(v), 9) if isinstance(v, (int, float)) else str(v))
                              for k, v in sorted(dg.items())}
    return out
io.open(OUT, "w", encoding="utf-8").write(json.dumps({"wall_sec": wall, "action": dump(act)},
                                                     ensure_ascii=False, indent=1))
print("WALL %.1f" % wall)
'''


def run_one(adapter, cfgn, run, t, workers, out):
    child = R / "scripts" / "_ab_child_20260908.py"
    io.open(child, "w", encoding="utf-8").write(CHILD)
    import os
    env = dict(os.environ, VR=str(R))
    p = subprocess.run([sys.executable, str(child), adapter, cfgn, run, str(t), str(workers), str(out)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    if p.returncode != 0:
        print(p.stdout[-2000:]); print(p.stderr[-3000:])
        raise SystemExit("child failed for %s" % adapter)
    return json.load(io.open(out, encoding="utf-8"))


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    A, B, CFGN, RUN, T = sys.argv[1:6]
    W = sys.argv[6] if len(sys.argv) > 6 else "0"
    ra = run_one(A, CFGN, RUN, T, W, R / "outputs/_ab_A.json")
    print("A %-70s %8.1f s" % (Path(A).name, ra["wall_sec"]), flush=True)
    rb = run_one(B, CFGN, RUN, T, W, R / "outputs/_ab_B.json")
    print("B %-70s %8.1f s" % (Path(B).name, rb["wall_sec"]), flush=True)

    same = ra["action"] == rb["action"]
    print("\n행동 비트 동치: %s" % ("예" if same else "아니오"))
    if not same:
        ka, kb = ra["action"], rb["action"]
        for sec in sorted(set(ka) | set(kb)):
            va, vb = ka.get(sec), kb.get(sec)
            if va == vb:
                continue
            if isinstance(va, dict) and isinstance(vb, dict):
                diff = [k for k in sorted(set(va) | set(vb)) if va.get(k) != vb.get(k)]
                print("  %-28s 불일치 %d개: %s" % (sec, len(diff), diff[:8]))
                for k in diff[:5]:
                    print("      %-40s A=%s  B=%s" % (k, va.get(k), vb.get(k)))
            else:
                print("  %-28s A=%s B=%s" % (sec, va, vb))
    print("\n소요 %.1f -> %.1f s  (%+.1f%%)"
          % (ra["wall_sec"], rb["wall_sec"], 100.0 * (rb["wall_sec"] - ra["wall_sec"]) / max(ra["wall_sec"], 1e-9)))
    sys.exit(0 if same else 1)


if __name__ == "__main__":
    main()
