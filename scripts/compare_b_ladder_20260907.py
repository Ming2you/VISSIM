# -*- coding: utf-8 -*-
"""B 사다리 비교표 (2026-09-07): 무제어 h0 · canon h11 · h7(오늘 최선) · b0(canon+RL+B0) → b1 +METER → b2 +SAT/SAT2 → b3 +PW25 → b4 +B5.
TTT · 지역별 적분 · 회랑/420/31-32/66 · SC1001/SC1004 꼭짓점 · SC1002 p4 · 링크 329 방류 · 미터 폐쇄 · B 진단. compare_options 의 함수를 재사용."""
import io, json, sys, glob, re, importlib.util
from pathlib import Path

R = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
spc = importlib.util.spec_from_file_location("co", R / "scripts/compare_options_20260907.py"); co = importlib.util.module_from_spec(spc); spc.loader.exec_module(co)
spb = importlib.util.spec_from_file_location("bl", R / "scripts/chain_b_ladder_20260907.py"); bl = importlib.util.module_from_spec(spb); spb.loader.exec_module(bl)

RUNS = [("h0 무제어", "h0_nocontrol_lcd1000_x18_20260906"), ("h11 canon_0905", "h11_canon0905_lcd1000_x18_20260907"),
        ("h7 canon+METER+SAT+SAT2+PW25", "h7_meter_sat_sat2_pw25_lcd1000_x18_20260906"),
        ("b0 canon+RL+B0", "b0_rl_b0_lcd1000_x18_20260907"), ("b1(구) +METER", "b1_rl_b0_meter_lcd1000_x18_20260907"),
        ("b1' +METER+MF1+LG", "b1_rl_b0_meter_mf1_lg_lcd1000_x18_20260907"),
        ("b2 +SAT/SAT2", "b2_rl_b0_meter_mf1_lg_sat_sat2_lcd1000_x18_20260907"), ("b3 +PW25", "b3_rl_b0_meter_mf1_lg_sat_sat2_pw25_lcd1000_x18_20260907"),
        ("b4 +B5", "b4_rl_b0_meter_mf1_lg_sat_sat2_pw25_b5_lcd1000_x18_20260907")]


def vertex(name, sc):
    fs = sorted(glob.glob(str(R / "evaluation/runs" / name / "decisions_*" / "action_*.json")))
    n = v = 0; p3 = 0.0
    for f in fs:
        t = int(re.search(r"action_(\d+)", f).group(1))
        if t < 900:
            continue
        g = json.load(io.open(f, encoding="utf-8")).get("green_times") or {}
        p = [float(g.get("%s_p%d" % (sc, i), 0)) for i in (1, 2, 3, 4)]
        n += 1; p3 += p[2]; v += 1 if (max(p) >= 70 and sorted(p)[2] <= 23) else 0
    return ("%d/%d p3̄%.0f" % (v, n, p3 / n)) if n else "-"


def main():
    print("| 런 | TTT | Δb0 | Δh7 | 본선 | 도시 | 램프 | 회랑 | 420 | 31/32 | 66 | SC1001 꼭짓점 | SC1004 꼭짓점 |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    b0 = None; h7 = None
    for tag, name in RUNS:
        try:
            ttt = co.ch.ttt_of(name)
        except Exception:
            print("| %s | (없음/미완주) |" % tag); continue
        if tag.startswith("b0"): b0 = ttt
        if tag.startswith("h7"): h7 = ttt
        fw, urb, ramp, acc = co.regional(name)
        print("| %s | %.1f | %s | %s | %.0f | %.0f | %.0f | %.0f | %.0f | %.0f | %.0f | %s | %s |" % (
            tag, ttt, ("%+.1f" % (ttt - b0)) if b0 is not None else "-", ("%+.1f" % (ttt - h7)) if h7 is not None else "-",
            fw, urb, ramp, acc["회랑"], acc["420"], acc["31/32"], acc["66"], vertex(name, "SC1001"), vertex(name, "SC1004")))
    print()
    for tag, name in RUNS[2:]:
        D = R / "evaluation/runs" / name
        if not D.is_dir():
            continue
        print("%s: %s" % (tag, co.p4_stats(name)))
        print("   329 방류: %s" % co.h5.link329_discharge(name))
        try:
            rows, _ = co.h3.meter_verdict(name)
            print("   미터: %s" % " | ".join(r[:60] for r in rows if r[:5] in ("R_D_W", "R_F_E", "R_F_W", "R_D_E")))
        except Exception as e:
            print("   미터: (판정 실패 %s)" % str(e)[:60])
        for row in bl.b_verdict(name)[2:]:
            print("  " + row[:230])


if __name__ == "__main__":
    main()
