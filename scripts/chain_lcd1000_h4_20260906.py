# -*- coding: utf-8 -*-
"""lcd1000 h4 팔: 포화 방출률 (FRAG SAT) — h3(METER) 위에 한 수정만 더. 사용: python chain_lcd1000_h4_20260906.py [tags...] (기본 METER SAT)
판정(기전): (1) measured_capacity_observed_links > 0 인 결정 비율(이탈 계수가 실제로 들어오나 = RW_QUEUE_WINDOW 배선),
(2) sat_est_329/420/32/66 궤적(씨앗에서 온라인 갱신으로 움직이나), (3) SC1002 p4 · SC105 p1 녹색과 회랑 재차·링크 420,
(4) 미터 기전(h3 판정 재확인). 그 다음 TTT 를 h0 8082.3 / h1 8629.0 / h3 과 비교."""
import io, json, sys, glob, re, importlib.util
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
series, meter_verdict = h2.series, h3.meter_verdict

COR = ["317", "321", "322", "325", "326", "329", "1220014203", "1220014201"]


def sat_verdict(name):
    D = R / "evaluation/runs" / name / ("decisions_%s" % name)
    ts = sorted(int(re.search(r"(\d+)\.json", p).group(1)) for p in glob.glob(str(D / "action_*.json")))
    n = 0; observed = 0; traj = {"329": [], "420": [], "32": [], "66": [], "1220018401": []}; enabled = 0
    for t in ts:
        try:
            a = json.load(io.open(D / ("action_%06d.json" % t), encoding="utf-8"))
        except Exception:
            continue
        md = a.get("metadata") or {}; dg = a.get("diagnostics") or {}
        src = {**dg, **md}
        n += 1
        enabled += int(float(src.get("measured_capacity_enabled", 0) or 0) > 0)
        observed += int(float(src.get("measured_capacity_observed_links", 0) or 0) > 0)
        if t % 900 == 0:
            for lk in traj:
                v = src.get("sat_est_%s" % lk)
                traj[lk].append("t%d:%s" % (t, ("%.0f" % float(v)) if v is not None else "-"))
    out = ["결정 %d · measured 켜짐 %d · 이탈계수 관측 반영 %d (RW_QUEUE_WINDOW 배선 %s)" % (n, enabled, observed, "OK" if observed > 0 else "실패")]
    for lk, vals in traj.items():
        out.append("sat_est_%s: %s" % (lk, " ".join(vals)))
    return out


def main():
    tags = sys.argv[1:] or ["METER", "SAT"]
    cfg_name = make_config(tags)
    name = "h4_%s_lcd1000_x18_20260906" % "_".join(t.lower() for t in tags)
    log("=== lcd1000 h4 시작 · %s (%s) · 기준 h0 8082.3 / h1 8629.0 ===" % ("+".join(tags), cfg_name))
    ttt = run(name, cfg_name)
    ref = {}
    for nm in ("h3_meter_lcd1000_x18_20260906",):
        try:
            ref[nm] = ttt_of(nm)
        except Exception:
            pass
    log("  TTT h4(%s) = %.1f (무제어 대비 %+.1f · h1 대비 %+.1f%s)" % ("+".join(tags), ttt, ttt - 8082.3, ttt - 8629.0, "".join(" · %s 대비 %+.1f" % (k[:8], ttt - v) for k, v in ref.items())))
    log("  -- 포화 방출률 기전")
    for row in sat_verdict(name):
        log("     " + row)
    log("  -- 미터 기전")
    rows, rr = meter_verdict(name)
    for r in rows:
        log("     " + r)
    log("  -- 시계열")
    for row in series(name):
        log("     " + row)
    log("=== h4 끝 ===")


if __name__ == "__main__":
    main()
