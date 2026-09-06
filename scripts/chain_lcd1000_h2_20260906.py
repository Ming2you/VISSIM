# -*- coding: utf-8 -*-
"""lcd1000 h2 팔: 관측 역압 현시가격 (config h_bp_20260906) — h0(무제어 8082.3)·h1(정본 8629.0) 과 짝지어 비교.
chain_lcd1000_20260906.run() 을 그대로 재사용한다(러너 인자 동일, PowerShell 로 Vissim COM)."""
import io, json, sys, glob, re, importlib.util, collections
from pathlib import Path

R = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sp = importlib.util.spec_from_file_location("ch", R / "scripts/chain_lcd1000_20260906.py")
ch = importlib.util.module_from_spec(sp); sp.loader.exec_module(ch)
log, run, ttt_of = ch.log, ch.run, ch.ttt_of

COR = ["317", "321", "322", "325", "326", "329", "1220014203", "1220014201"]


def series(name):
    D = R / "evaluation/runs" / name / ("decisions_%s" % name)
    rows = []
    for t in (1800, 2700, 3600, 4500, 5400):
        try:
            j = json.load(io.open(D / ("state_%06d.json" % t), encoding="utf-8")); lc = j["vehicle_records"].get("full_network_link_counts") or {}
            a = json.load(io.open(D / ("action_%06d.json" % t), encoding="utf-8")); g = a.get("green_times") or {}; dg = a.get("diagnostics") or {}; m = a.get("ramp_metering") or {}
            rows.append("t%d 420=%d cor=%d 32=%d SC105p1=%.0f(%+.3f) SC1002=%s 미터=%s 램프=%s" % (
                t, lc.get("420", 0), sum(lc.get(l, 0) for l in COR), lc.get("32", 0), g.get("SC105_p1", 0), float(dg.get("wu_phase_price_SC105_p1", 0) or 0),
                "/".join("%.0f" % g.get("SC1002_p%d" % k, 0) for k in (1, 2, 3, 4)), {k[2:]: round(v) for k, v in m.items()}, {k: v for k, v in (j.get("ramp_counts") or {}).items() if k.startswith("R_")}))
        except Exception as e:
            rows.append("t%d -(%s)" % (t, str(e)[:40]))
    return rows


def main():
    log("=== lcd1000 h2 시작 · 관측 역압 현시가격(h_bp_20260906) · 기준 h0 8082.3 / h1 8629.0 ===")
    ttt = run("h2_bp_lcd1000_x18_20260906", "h_bp_20260906")
    log("  TTT h2(역압 가격) = %.1f (무제어 대비 %+.1f · 정본 h1 대비 %+.1f)" % (ttt, ttt - 8082.3, ttt - 8629.0))
    for name in ("h1_base_lcd1000_x18_20260906", "h2_bp_lcd1000_x18_20260906"):
        log("  -- %s" % name)
        for row in series(name):
            log("     " + row)
    # 역압 진단 요약
    D = R / "evaluation/runs/h2_bp_lcd1000_x18_20260906/decisions_h2_bp_lcd1000_x18_20260906"
    n = 0; fallback = 0; maxp = 0.0
    for a in sorted(glob.glob(str(D / "action_*.json"))):
        dg = (json.load(io.open(a, encoding="utf-8")).get("diagnostics") or {}); n += 1
        fallback += int(float(dg.get("observed_backpressure_fallback_rollout", 0) or 0) > 0)
        maxp = max(maxp, float(dg.get("observed_backpressure_max_price", 0) or 0))
    log("  역압 진단: 결정 %d · 롤아웃 폴백 %d · 최대 가격 %.3f" % (n, fallback, maxp))
    log("=== h2 끝 ===")


if __name__ == "__main__":
    main()
