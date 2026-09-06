# -*- coding: utf-8 -*-
"""lcd1000 D/A 팔: D = 망 압력(h_np_20260906), A = 가격 없음(h_p0_20260906). h2(one-hop) 종료 후 순차 실행.
비교 기준: h0 무제어 8082.3 · h1 정본(롤아웃 가격) 8629.0 · h2 one-hop(체인 로그)."""
import io, json, sys, glob, importlib.util
from pathlib import Path

R = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sp = importlib.util.spec_from_file_location("ch", R / "scripts/chain_lcd1000_20260906.py"); ch = importlib.util.module_from_spec(sp); sp.loader.exec_module(ch)
sp2 = importlib.util.spec_from_file_location("h2", R / "scripts/chain_lcd1000_h2_20260906.py"); h2 = importlib.util.module_from_spec(sp2); sp2.loader.exec_module(h2)
log, run, ttt_of, series = ch.log, ch.run, ch.ttt_of, h2.series

ARMS = [("h3_np_lcd1000_x18_20260906", "h_np_20260906", "D 망 압력(평균 전파, 램프 노드 off, local_scale)"),
        ("h4_p0_lcd1000_x18_20260906", "h_p0_20260906", "A 가격 없음(weight 0)")]


def main():
    only = sys.argv[1:] if len(sys.argv) > 1 else None
    for name, cfg, desc in ARMS:
        if only and name not in only:
            continue
        log("=== %s 시작 · config %s ===" % (desc, cfg))
        ttt = run(name, cfg)
        log("  TTT %s = %.1f (무제어 대비 %+.1f · 정본 h1 대비 %+.1f)" % (name, ttt, ttt - 8082.3, ttt - 8629.0))
        for row in series(name):
            log("     " + row)
        D = R / "evaluation/runs" / name / ("decisions_%s" % name)
        n = 0; fb = 0; rho = []
        for a in sorted(glob.glob(str(D / "action_*.json"))):
            dg = (json.load(io.open(a, encoding="utf-8")).get("diagnostics") or {}); n += 1
            fb += int(float(dg.get("network_pressure_fallback_rollout", dg.get("observed_backpressure_fallback_rollout", 0)) or 0) > 0)
            if "network_pressure_rho_fw" in dg: rho.append(float(dg["network_pressure_rho_fw"]))
        log("  진단: 결정 %d · 롤아웃 폴백 %d · ρ(A↓) 최대 %s" % (n, fb, ("%.3f" % max(rho)) if rho else "-"))
    log("=== D/A 끝 ===")


if __name__ == "__main__":
    main()
