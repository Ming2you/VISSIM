# -*- coding: utf-8 -*-
"""ablation 사다리 (2026-09-07): 기준 = h7(METER+SAT+SAT2+PW25, 8356.4). 후보를 한 단씩 얹고 기준 대비 −GATE(50 veh·h, 시드 σ) 이상 좋아지면 채택(누적),
아니면 버리고 다음. 후보 순서: QB(큐 β 귀속) → CAP+V2(추정 상한 + 램프 유출 제외 씨앗) → PW10(가중 0.10; PW25 대체) → LG(리더 폴백 가드 0.002).
사용: python chain_ablation_20260907.py [시작 rung 번호]  (기존 완주 런은 run() 이 RESUME 로 재사용)"""
import io, json, sys, glob, re, importlib.util
from pathlib import Path

R = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sp = importlib.util.spec_from_file_location("ch", R / "scripts/chain_lcd1000_20260906.py"); ch = importlib.util.module_from_spec(sp); sp.loader.exec_module(ch)
sp4 = importlib.util.spec_from_file_location("h4", R / "scripts/chain_lcd1000_h4_20260906.py"); h4 = importlib.util.module_from_spec(sp4); sp4.loader.exec_module(h4)
sp3 = importlib.util.spec_from_file_location("h3", R / "scripts/chain_lcd1000_h3_20260906.py"); h3 = importlib.util.module_from_spec(sp3); sp3.loader.exec_module(h3)
sp2 = importlib.util.spec_from_file_location("h2", R / "scripts/chain_lcd1000_h2_20260906.py"); h2 = importlib.util.module_from_spec(sp2); sp2.loader.exec_module(h2)
log, run, ttt_of, make_config = ch.log, ch.run, ch.ttt_of, ch.make_config

GATE = 50.0
BASE_TAGS = ["METER", "SAT", "SAT2", "PW25"]
BASE_TTT = 8356.4
# (rung 이름, 추가 태그, 제거 태그)
RUNGS = [("h12", ["QB"], []), ("h13", ["CAP", "V2"], []), ("h14", ["PW10"], ["PW25"]), ("h15", ["LG"], []),
         # h10(JOINT, 가격 1.0) 이 h5 −193 이라 가중 0.25 위에 회랑 결합을 얹는 것도 시험
         ("h16", ["JOINT"], [])]


def name_of(prefix, tags):
    return "%s_%s_lcd1000_x18_20260907" % (prefix, "_".join(t.lower() for t in tags))


def main():
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    log("=== ablation 사다리 시작 · 기준 h7 %s = %.1f · GATE %.0f ===" % ("+".join(BASE_TAGS), BASE_TTT, GATE))
    tags = list(BASE_TAGS); best = BASE_TTT; best_name = "h7_meter_sat_sat2_pw25_lcd1000_x18_20260906"
    for i, (prefix, add, remove) in enumerate(RUNGS):
        if i < start:
            continue
        cand = [t for t in tags if t not in remove] + add
        cfg_name = make_config(cand)
        name = name_of(prefix, cand)
        log("--- rung %s: %s (기준 %.1f)" % (prefix, "+".join(cand), best))
        ttt = run(name, cfg_name)
        d = ttt - best
        log("  TTT %s = %.1f (기준 대비 %+.1f · 무제어 대비 %+.1f)" % (prefix, ttt, d, ttt - 8082.3))
        for row in h4.sat_verdict(name)[:1]:
            log("     " + row)
        rows, _ = h3.meter_verdict(name)
        for r in rows:
            if r.startswith("R_D_W") or r.startswith("R_F_E"):
                log("     " + r)
        for row in h2.series(name)[1:4]:
            log("     " + row)
        if ttt <= best - GATE:
            tags, best, best_name = cand, ttt, name
            log("  관문: 채택 → 플랫폼 = %s (%.1f)" % ("+".join(tags), best))
        else:
            log("  관문: 기각 (%+.1f, GATE %.0f) → 플랫폼 유지 %s" % (d, GATE, "+".join(tags)))
    log("=== ablation 끝 · 최종 플랫폼 %s = %.1f (%s) ===" % ("+".join(tags), best, best_name))
    log("ABLATION_DONE")


if __name__ == "__main__":
    main()
