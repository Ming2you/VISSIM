# -*- coding: utf-8 -*-
"""lcd1000 h5 팔: 큐 β 귀속 (FRAG QB) — h4(METER+SAT) 위에 한 수정만 더. 사용: python chain_lcd1000_h5_20260906.py [tags...] (기본 METER SAT QB)
판정(기전): (1) SC1002 p4(좌회전) 녹색이 23 에서 움직이나, (2) 링크 329 실제 방류(차량 레코드 차분)의 좌회전 차로 몫이 늘어나나,
(3) 회랑 재차·링크 420, (4) 미터·포화 기전 재확인. 그 다음 TTT 를 h0/h1/h3/h4 와 비교."""
import io, json, sys, glob, re, importlib.util, collections
from pathlib import Path

R = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sp = importlib.util.spec_from_file_location("ch", R / "scripts/chain_lcd1000_20260906.py")
ch = importlib.util.module_from_spec(sp); sp.loader.exec_module(ch)
log, run, ttt_of, make_config = ch.log, ch.run, ch.ttt_of, ch.make_config
sp2 = importlib.util.spec_from_file_location("h2", R / "scripts/chain_lcd1000_h2_20260906.py")
h2 = importlib.util.module_from_spec(sp2); sp2.loader.exec_module(h2)
sp3 = importlib.util.spec_from_file_location("h3", R / "scripts/chain_lcd1000_h3_20260906.py")
h3 = importlib.util.module_from_spec(sp3); sp3.loader.exec_module(h3)
sp4 = importlib.util.spec_from_file_location("h4", R / "scripts/chain_lcd1000_h4_20260906.py")
h4 = importlib.util.module_from_spec(sp4); sp4.loader.exec_module(h4)
series, meter_verdict, sat_verdict = h2.series, h3.meter_verdict, h4.sat_verdict


def link329_discharge(name):
    """링크 329 실제 방류(veh/h, 15분 창): 총 / 좌회전 차로4 / 직진 2+3 / 우회전 1."""
    D = R / "evaluation/runs" / name / ("decisions_%s" % name)
    ts = sorted(int(re.search(r"(\d+)\.json", p).group(1)) for p in glob.glob(str(D / "state_*.json")))
    prev = None; prev_t = None; out = {}
    for t in ts:
        try:
            recs = json.load(io.open(D / ("state_%06d.json" % t), encoding="utf-8"))["vehicle_records"].get("records") or []
        except Exception:
            continue
        cur = {x["veh_no"]: x.get("lane_no") for x in recs if x.get("link_no") == 329}
        if prev is not None and t - prev_t == 150:
            gone = [v for v in prev if v not in cur]; by = collections.Counter(prev[v] for v in gone)
            out[t] = (len(gone) * 24, by.get(4, 0) * 24, (by.get(2, 0) + by.get(3, 0)) * 24, by.get(1, 0) * 24)
        prev, prev_t = cur, t
    cells = []
    for w0 in (1800, 2700, 3600, 4500):
        vals = [v for t, v in out.items() if w0 < t <= w0 + 900]
        if vals:
            n = len(vals); cells.append("%d-%d: %3.0f(좌%3.0f 직%3.0f 우%3.0f)" % (w0, w0 + 900, sum(v[0] for v in vals) / n, sum(v[1] for v in vals) / n, sum(v[2] for v in vals) / n, sum(v[3] for v in vals) / n))
    return " | ".join(cells)


def p4_series(name):
    D = R / "evaluation/runs" / name / ("decisions_%s" % name)
    vals = []
    for a in sorted(glob.glob(str(D / "action_*.json"))):
        t = int(re.search(r"(\d+)\.json", a).group(1))
        if t < 900 or t % 600 != 0:
            continue
        g = json.load(io.open(a, encoding="utf-8")).get("green_times") or {}
        vals.append("t%d:%s" % (t, "/".join("%.0f" % g.get("SC1002_p%d" % k, 0) for k in (1, 2, 3, 4))))
    return " ".join(vals)


def main():
    tags = sys.argv[1:] or ["METER", "SAT", "QB"]
    cfg_name = make_config(tags)
    name = "h5_%s_lcd1000_x18_20260906" % "_".join(t.lower() for t in tags)
    log("=== lcd1000 h5 시작 · %s (%s) · 기준 h0 8082.3 / h1 8629.0 ===" % ("+".join(tags), cfg_name))
    ttt = run(name, cfg_name)
    ref = {}
    for nm in ("h3_meter_lcd1000_x18_20260906", "h4_meter_sat_lcd1000_x18_20260906"):
        try:
            ref[nm] = ttt_of(nm)
        except Exception:
            pass
    log("  TTT h5(%s) = %.1f (무제어 대비 %+.1f · h1 대비 %+.1f%s)" % ("+".join(tags), ttt, ttt - 8082.3, ttt - 8629.0, "".join(" · %s 대비 %+.1f" % (k[:8], ttt - v) for k, v in ref.items())))
    log("  -- SC1002 녹색(p1/p2/p3/p4) 궤적")
    for nm in ("h4_meter_sat_lcd1000_x18_20260906", name):
        log("     %s: %s" % (nm[:8], p4_series(nm)))
    log("  -- 링크 329 실제 방류")
    for nm in ("h0_nocontrol_lcd1000_x18_20260906", "h4_meter_sat_lcd1000_x18_20260906", name):
        log("     %s: %s" % (nm[:8], link329_discharge(nm)))
    log("  -- 포화 방출률 기전")
    for row in sat_verdict(name):
        log("     " + row)
    log("  -- 미터 기전")
    rows, _ = meter_verdict(name)
    for r in rows:
        log("     " + r)
    log("  -- 시계열")
    for row in series(name):
        log("     " + row)
    log("=== h5 끝 ===")


if __name__ == "__main__":
    main()
