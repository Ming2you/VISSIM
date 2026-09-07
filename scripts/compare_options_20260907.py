# -*- coding: utf-8 -*-
"""가격 옵션 런 비교표: 기준 h5(METER+SAT+SAT2) 대비 h7(PW25)·h8(TS)·h10(JOINT). TTT · 지역별 적분 · SC1002 p4 · 링크 329 방류 · 미터 폐쇄."""
import io, json, sys, glob, re, collections, importlib.util
from pathlib import Path

R = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sp = importlib.util.spec_from_file_location("ch", R / "scripts/chain_lcd1000_20260906.py"); ch = importlib.util.module_from_spec(sp); sp.loader.exec_module(ch)
sp3 = importlib.util.spec_from_file_location("h3", R / "scripts/chain_lcd1000_h3_20260906.py"); h3 = importlib.util.module_from_spec(sp3); sp3.loader.exec_module(h3)
sp5 = importlib.util.spec_from_file_location("h5", R / "scripts/chain_lcd1000_h5_20260906.py"); h5 = importlib.util.module_from_spec(sp5); sp5.loader.exec_module(h5)

RUNS = [("h0 무제어", "h0_nocontrol_lcd1000_x18_20260906"), ("h3 METER", "h3_meter_lcd1000_x18_20260906"), ("h5 기준", "h5_meter_sat_sat2_lcd1000_x18_20260906"),
        ("h7 ④가중0.25", "h7_meter_sat_sat2_pw25_lcd1000_x18_20260906"), ("h8 ①2단정련", "h8_meter_sat_sat2_ts_lcd1000_x18_20260906"), ("h10 ③회랑결합", "h10_meter_sat_sat2_joint_lcd1000_x18_20260906")]
GROUPS = {"회랑": ["317", "321", "322", "325", "326", "329", "1220014203", "1220014201"], "420": ["420"], "31/32": ["31", "32"], "66": ["66"]}


def regional(name):
    D = R / "evaluation/runs" / name / ("decisions_%s" % name); prev_t = 0; acc = collections.Counter(); fw = urb = ramp = 0.0
    for p in sorted(glob.glob(str(D / "state_*.json")), key=lambda p: int(re.search(r"(\d+)\.json", p).group(1))):
        t = int(re.search(r"(\d+)\.json", p).group(1)); j = json.load(io.open(p, encoding="utf-8")); dt = (t - prev_t) / 3600.0; prev_t = t
        lc = j["vehicle_records"].get("full_network_link_counts") or {}
        for g, links in GROUPS.items(): acc[g] += dt * sum(float(lc.get(l, 0)) for l in links)
        fw += dt * float(j.get("freeway_vehicles", 0)); urb += dt * float(j.get("urban_vehicles", 0)); ramp += dt * float(j.get("ramp_vehicles", 0))
    return fw, urb, ramp, acc


def p4_stats(name):
    D = R / "evaluation/runs" / name / ("decisions_%s" % name); vals = []
    for a in sorted(glob.glob(str(D / "action_*.json"))):
        t = int(re.search(r"(\d+)\.json", a).group(1))
        if t < 900: continue
        g = json.load(io.open(a, encoding="utf-8")).get("green_times") or {}; vals.append((float(g.get("SC1002_p4", 0)), float(g.get("SC105_p1", 0))))
    if not vals: return "-"
    return "SC1002 p4 평균 %.0f(>30: %d/%d) · SC105 p1 평균 %.0f" % (sum(v[0] for v in vals) / len(vals), sum(1 for v in vals if v[0] > 30), len(vals), sum(v[1] for v in vals) / len(vals))


def main():
    print("| 런 | TTT | Δh5 | 본선 | 도시 | 램프 | 회랑 | 420 | 31/32 | 66 |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    base = None
    for tag, name in RUNS:
        try: ttt = ch.ttt_of(name)
        except Exception: print("| %s | (없음) |" % tag); continue
        if tag.startswith("h5"): base = ttt
        fw, urb, ramp, acc = regional(name)
        print("| %s | %.1f | %s | %.0f | %.0f | %.0f | %.0f | %.0f | %.0f | %.0f |" % (tag, ttt, ("%+.1f" % (ttt - base)) if base is not None else "-", fw, urb, ramp, acc["회랑"], acc["420"], acc["31/32"], acc["66"]))
    print()
    for tag, name in RUNS[1:]:
        D = R / "evaluation/runs" / name
        if not D.is_dir(): continue
        rows, _ = h3.meter_verdict(name)
        print("%s: %s" % (tag, p4_stats(name)))
        print("   329 방류: %s" % h5.link329_discharge(name))
        print("   미터: %s" % " | ".join(r.split("(")[0] + "(" + r.split("(")[1].split(")")[0] + ") " + r.split(")")[1].strip() for r in rows if r.startswith("R_D_W") or r.startswith("R_F_E")))


if __name__ == "__main__":
    main()
