# -*- coding: utf-8 -*-
"""Stage 6 비교 지표 (2026-09-06): 런 이름들을 받아 network/urban/freeway TTT, 최대 큐(링크 재차 최대), 굶김 이벤트,
min-green/max-green 도달 수, 그리드락 징후(정지 비율), 결정당 계산시간을 표로 낸다.
사용: python scripts/stage6_metrics_20260906.py <run1> <run2> ..."""
import io, json, sys, glob, re, importlib.util, statistics
from pathlib import Path

R = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sp = importlib.util.spec_from_file_location("ch", R / "scripts/chain_gated_20260905.py"); ch = importlib.util.module_from_spec(sp); sp.loader.exec_module(ch)
GREEN_MIN, GREEN_MAX_DEFAULT = 23.0, 78.0
COR = ["317", "321", "322", "325", "326", "329", "1220014203", "1220014201"]


def metrics(name):
    D = R / "evaluation/runs" / name / ("decisions_%s" % name)
    states = sorted(glob.glob(str(D / "state_*.json")), key=lambda p: int(re.search(r"(\d+)\.json", p).group(1)))
    acts = sorted(glob.glob(str(D / "action_*.json")), key=lambda p: int(re.search(r"(\d+)\.json", p).group(1)))
    tot = fw = urb = ramp = 0.0; prev_t = 0; max_link = (0, ""); stopped_frac = []; max_ramp = 0
    for p in states:
        t = int(re.search(r"(\d+)\.json", p).group(1)); j = json.load(io.open(p, encoding="utf-8")); dt = (t - prev_t) / 3600.0; prev_t = t
        tot += dt * float(j.get("total_vehicles", 0)); fw += dt * float(j.get("freeway_vehicles", 0)); urb += dt * float(j.get("urban_vehicles", 0)); ramp += dt * float(j.get("ramp_vehicles", 0))
        lc = j["vehicle_records"].get("full_network_link_counts") or {}
        for l, n in lc.items():
            if n > max_link[0]: max_link = (n, l)
        tv = float(j.get("total_vehicles", 0) or 0); stopped_frac.append(float(j.get("stopped_vehicles", 0) or 0) / tv if tv else 0.0)
        max_ramp = max(max_ramp, max((v for k, v in (j.get("ramp_counts") or {}).items() if k.startswith("R_")), default=0))
    min_hits = max_hits = starve = 0; walls = []; n_dec = 0; starve_events = []
    for a in acts:
        t = int(re.search(r"(\d+)\.json", a).group(1))
        if t < 900: continue
        doc = json.load(io.open(a, encoding="utf-8")); g = doc.get("green_times") or {}; md = doc.get("metadata") or {}; n_dec += 1
        for k, v in g.items():
            if v <= GREEN_MIN + 0.5: min_hits += 1
            if v >= GREEN_MAX_DEFAULT - 0.5: max_hits += 1
        # 굶김: 현시가 최소녹색인데 그 현시 movement 큐 합 ≥ 40 (state 의 모형 큐는 없으니 plant 정지 재차로 근사 불가 → 액션 진단의 pre_refine 대비 감소 12 s 이상 & 최소 도달)
        dg = doc.get("diagnostics") or {}
        for k, v in g.items():
            pre = dg.get("wu_pre_refine_" + k)
            if pre is not None and float(pre) - float(v) >= 12.0 and float(v) <= GREEN_MIN + 0.5:
                starve += 1; starve_events.append((t, k, round(float(pre)), round(float(v))))
        w = md.get("wall_sec") or md.get("decide_wall_sec") or md.get("controller_wall_sec")
        if w is not None: walls.append(float(w))
    try: ttt = ch.ttt_of(name)
    except Exception: ttt = float("nan")
    return {"run": name, "TTT": ttt, "tot_int": tot, "fw": fw, "urb": urb, "ramp": ramp, "max_link": max_link, "max_ramp": max_ramp,
            "stopped_frac_max": max(stopped_frac) if stopped_frac else 0, "min_hits": min_hits, "max_hits": max_hits, "n_dec": n_dec,
            "starve": starve, "starve_ex": starve_events[:5], "wall_med": statistics.median(walls) if walls else float("nan")}


def main():
    rows = [metrics(n) for n in sys.argv[1:]]
    print("%-36s %8s %7s %7s %6s | %-14s %6s %6s | %7s %7s %6s | %6s" % ("run", "TTT", "fw", "urb", "ramp", "max link(n,id)", "maxRq", "stop%", "minHit", "maxHit", "starve", "wall_s"))
    for r in rows:
        print("%-36s %8.1f %7.0f %7.0f %6.0f | %-14s %6d %5.0f%% | %7d %7d %6d | %6s" % (
            r["run"][:36], r["TTT"], r["fw"], r["urb"], r["ramp"], "%d,%s" % r["max_link"], r["max_ramp"], 100 * r["stopped_frac_max"], r["min_hits"], r["max_hits"], r["starve"], ("%.0f" % r["wall_med"]) if r["wall_med"] == r["wall_med"] else "-"))
        if r["starve_ex"]: print("      굶김 예: %s" % r["starve_ex"])


if __name__ == "__main__":
    main()
