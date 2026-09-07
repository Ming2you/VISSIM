# -*- coding: utf-8 -*-
"""lcd1000 h3 팔: 램프 미터 액추에이션 전달함수 (FRAG METER, config h_METER_20260906) — 한 런에 수정 하나.
판정은 TTT 가 아니라 **기전**: 부분개방 결정에서 plant 실현 유량 / 요청(되쓴 실현값) 의 중앙비가 0.8~1.2 에 들어오나
(h1 은 1.9~2.65), 완전 폐쇄(0) 결정 수, 램프 큐 포화(≥140) 횟수. 그 다음 TTT 를 h0 8082.3 / h1 8629.0 / h2 8677.6 과 비교."""
import io, json, sys, glob, re, importlib.util, collections, csv
from pathlib import Path

R = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sp = importlib.util.spec_from_file_location("ch", R / "scripts/chain_lcd1000_20260906.py")
ch = importlib.util.module_from_spec(sp); sp.loader.exec_module(ch)
log, run, ttt_of, make_config = ch.log, ch.run, ch.ttt_of, ch.make_config
sp2 = importlib.util.spec_from_file_location("h2", R / "scripts/chain_lcd1000_h2_20260906.py")
h2 = importlib.util.module_from_spec(sp2); sp2.loader.exec_module(h2)
series = h2.series

ON = {"R_D_W": ["10480", "10482"], "R_D_E": ["10484", "10490"], "R_F_W": ["10646", "10644"], "R_F_E": ["10681", "10639"]}


def meter_verdict(name):
    """rate(action t, 되쓴 실현값) vs plant 유량(state t+150 의 far_measurement 커넥터 합)."""
    D = R / "evaluation/runs" / name / ("decisions_%s" % name)
    ts = sorted(int(re.search(r"(\d+)\.json", p).group(1)) for p in glob.glob(str(D / "action_*.json")))
    ratios = {k: [] for k in ON}; closed = {k: 0 for k in ON}; partial = {k: 0 for k in ON}; opened = {k: 0 for k in ON}
    sat = {k: 0 for k in ON}; req_vs_real = []
    for t in ts:
        try:
            a = json.load(io.open(D / ("action_%06d.json" % t), encoding="utf-8")); j = json.load(io.open(D / ("state_%06d.json" % (t + 150)), encoding="utf-8"))
        except Exception:
            continue
        lv = (j["local_observation"].get("far_measurement") or {}).get("link_volume_veh_h") or {}; m = a.get("ramp_metering") or {}; dg = a.get("diagnostics") or {}
        rc = j.get("ramp_counts") or {}
        for k, conns in ON.items():
            rate = m.get(k)
            if rate is None:
                continue
            flow = sum(float(lv.get(c, 0) or 0) for c in conns)
            if float(rc.get(k, 0)) >= 140:
                sat[k] += 1
            if rate <= 1.0:
                closed[k] += 1
            elif float(dg.get("rw_meter_open_%s" % k, 1.0)) >= 0.5:
                opened[k] += 1
            else:
                partial[k] += 1; ratios[k].append(flow / max(rate, 1.0))
            rq = dg.get("rw_meter_requested_%s" % k)
            if rq is not None:
                req_vs_real.append((k, t, round(float(rq)), round(float(rate))))
    out = []
    for k in ON:
        v = sorted(ratios[k]); med = v[len(v) // 2] if v else None
        out.append("%s 부분 %d(실현/요청 중앙 %s · Q1 %s · Q3 %s) 폐쇄 %d 열림 %d 큐포화 %d" % (
            k, partial[k], ("%.2f" % med) if med else "-", ("%.2f" % v[len(v) // 4]) if v else "-", ("%.2f" % v[(3 * len(v)) // 4]) if v else "-", closed[k], opened[k], sat[k]))
    return out, req_vs_real


def main():
    cfg_name = make_config(["METER"])
    log("=== lcd1000 h3 시작 · 램프 미터 전달함수(%s) · 기준 h0 8082.3 / h1 8629.0 / h2 8677.6 ===" % cfg_name)
    name = "h3_meter_lcd1000_x18_20260906"
    ttt = run(name, cfg_name)
    log("  TTT h3(미터 전달함수) = %.1f (무제어 대비 %+.1f · h1 대비 %+.1f · h2 대비 %+.1f)" % (ttt, ttt - 8082.3, ttt - 8629.0, ttt - 8677.6))
    for nm in ("h1_base_lcd1000_x18_20260906", name):
        log("  -- %s 미터 기전" % nm)
        rows, rr = meter_verdict(nm)
        for r in rows:
            log("     " + r)
        if rr:
            log("     요청→실현 예: " + ", ".join("%s@%d %d→%d" % x for x in rr[:10]))
    for nm in (name,):
        log("  -- %s 시계열" % nm)
        for row in series(nm):
            log("     " + row)
    log("=== h3 끝 ===")


if __name__ == "__main__":
    main()
