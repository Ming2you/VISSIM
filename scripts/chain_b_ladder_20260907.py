# -*- coding: utf-8 -*-
"""B 사다리 (2026-09-07): 0단 = canon_default_20260905 + RL + B0 ("기존 B0", 가격 가중 1.0; lcd200 의 g3 에 해당) 를 lcd1000 에서 뽑고,
그 위에 오늘(09-06~07) 수정을 한 단씩 **누적**한다: b1 +METER → b2 +SAT+SAT2 → b3 +PW25 → b4 +B5 (QB 는 B5 와 충돌해 제외).
관문(GATE 50)은 판정만 기록하고 플랫폼은 항상 누적한다(사용자 방식: 기전 확인 → TTT → 이상하면 재진단). 각 단 뒤에 기전 판정
(미터·포화방출·SC1001/SC1004 꼭짓점·leg_split 주입 대 실측·off-ramp 직행·B5) 을 찍는다.
사용: python chain_b_ladder_20260907.py [시작 rung 번호 0..4]  (완주 런은 run() 이 RESUME 로 재사용)"""
import io, json, sys, glob, re, importlib.util
from pathlib import Path

R = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")   # SystemExit/traceback 의 한글이 cp949 콘솔에서 깨지지 않게
sp = importlib.util.spec_from_file_location("ch", R / "scripts/chain_lcd1000_20260906.py"); ch = importlib.util.module_from_spec(sp); sp.loader.exec_module(ch)
sp4 = importlib.util.spec_from_file_location("h4", R / "scripts/chain_lcd1000_h4_20260906.py"); h4 = importlib.util.module_from_spec(sp4); sp4.loader.exec_module(h4)
sp3 = importlib.util.spec_from_file_location("h3", R / "scripts/chain_lcd1000_h3_20260906.py"); h3 = importlib.util.module_from_spec(sp3); sp3.loader.exec_module(h3)
sp2 = importlib.util.spec_from_file_location("h2", R / "scripts/chain_lcd1000_h2_20260906.py"); h2 = importlib.util.module_from_spec(sp2); sp2.loader.exec_module(h2)
log, run, ttt_of, make_config = ch.log, ch.run, ch.ttt_of, ch.make_config

GATE = 50.0
REF = {"무제어 h0": 8082.3, "canon h11": 8629.0, "h7(METER+SAT+SAT2+PW25)": 8356.4}
# (rung, 추가 태그). 누적.
# 2026-09-07 11:2x: b1(+METER 단독) 8361.6(+48.2) 진단 후 b1 = METER+MF1(수요 벌점)+LG(가드 0.002) 로 교체(사용자 승인). 옛 b1 런은 b1_rl_b0_meter_… 로 남김.
RUNGS = [("b0", ["RL", "B0"]), ("b1", ["METER", "MF1", "LG"]), ("b2", ["SAT", "SAT2"]), ("b3", ["PW25"]), ("b4", ["B5"])]
RM_CONN = {"R_D_W": "10480", "R_D_E": "10484", "R_F_W": "10646", "R_F_E": "10681"}   # W_out 발 미터 커넥터(링크평가 실측)


def name_of(prefix, tags):
    return "%s_%s_lcd1000_x18_20260907" % (prefix, "_".join(t.lower() for t in tags))


def _load(p):
    return json.load(io.open(p, encoding="utf-8"))


def _fnum(v, nd=1):
    try:
        return round(float(v), nd)
    except Exception:
        return v


def b_verdict(name):
    """B 기전 판정: SC1001/SC1004 녹색 궤적·꼭짓점 수, leg_split 주입/u_on 대 실측(W_out 발 미터 커넥터 링크평가), off-ramp 직행, B5, RL."""
    rows = []
    D = R / "evaluation/runs" / name
    acts = sorted(D.glob("decisions_*/action_*.json"))
    if not acts:
        return ["  (action 없음)"]
    ser = {"SC1001": [], "SC1004": []}
    for f in acts:
        a = _load(f); g = a.get("green_times") or {}; t = int(re.search(r"action_(\d+)", f.name).group(1))
        if t < 900:
            continue   # 워밍업(no-control) 결정은 균등 34.5 라 꼭짓점 통계를 희석한다 (ch._greens 와 같은 규칙)
        for sc in ser:
            ser[sc].append((t, [round(float(g.get("%s_p%d" % (sc, i), 0))) for i in (1, 2, 3, 4)]))
    for sc, s in ser.items():
        n = len(s); v = sum(1 for _, p in s if max(p) >= 70 and sorted(p)[2] <= 23)
        pick = [x for x in s if x[0] in (900, 1500, 2100, 2700, 3600, 4500, 5400)]
        rows.append("  %s 꼭짓점 %d/%d · 평균 %s · %s" % (sc, v, n, [round(sum(p[i] for _, p in s) / max(n, 1)) for i in range(4)],
                                                    " ".join("t%d:%d/%d/%d/%d" % ((t,) + tuple(p)) for t, p in pick)))
    flags = {}
    for f in acts[-1:]:
        dg = _load(f).get("diagnostics") or {}
        for k in ("leg_ramp_split_enabled", "leg_ramp_split_runtime", "offramp_direct_enabled", "gate_onramp_queue_enabled",
                  "phase_local_ramp_aware_enabled", "phase_price_ramp_signal_zeroed", "leg_ramp_split_substep_rebound_modules",
                  "gate_ramp_peeloff_enabled"):
            if k in dg:
                flags[k] = _fnum(dg[k], 0)
    rows.append("  스위치(마지막 결정): %s" % (flags or "B 진단 키 없음(B 꺼짐?)"))
    line = []
    prev_inj = None
    for t in (1800, 2700, 3600, 4500, 5400):
        fa = D / ("decisions_%s" % name) / ("action_%06d.json" % t); fs = D / ("decisions_%s" % name) / ("state_%06d.json" % t)
        if not fa.exists():
            continue
        dg = _load(fa).get("diagnostics") or {}
        # leg_ramp_split_injected_veh / offramp_direct_veh 는 프로세스 수명 누적기(모든 롤아웃 substep 합) — 절대값이 아니라 Δ 를 봐라.
        inj_raw = dg.get("leg_ramp_split_injected_veh"); uon = dg.get("leg_ramp_split_u_on_last"); od = dg.get("offramp_direct_veh"); kept = dg.get("gate_onramp_queue_kept")
        inj = inj_raw
        if inj_raw is not None:
            try:
                inj = "%s(Δ%s)" % (_fnum(inj_raw, 0), ("-" if prev_inj is None else _fnum(float(inj_raw) - prev_inj, 0)))
                prev_inj = float(inj_raw)
            except Exception:
                pass
        meas = None
        if fs.exists():
            try:
                lv = (((_load(fs).get("local_observation") or {}).get("far_measurement") or {}).get("link_volume_veh_h") or {})
                meas = {r: _fnum(lv.get(c), 0) for r, c in RM_CONN.items() if lv.get(c) is not None}
            except Exception:
                meas = None
        uon_s = ({k: _fnum(v, 0) for k, v in uon.items()} if isinstance(uon, dict) else _fnum(uon, 0))
        line.append("t%d 주입누적=%s u_on=%s 실측램프=%s 직행누적=%s B5kept=%s" % (t, inj if isinstance(inj, str) else _fnum(inj, 1), uon_s, meas, _fnum(od, 1), _fnum(kept, 0)))
    rows.extend("  " + x for x in line)
    return rows


def _diag(label, fn, indent="     "):
    """진단은 TTT 가 이미 기록된 뒤의 부가 정보다 — 여기서 터져 밤새 체인이 서면 안 된다. 실패는 로그에 남기고 계속한다.
    (run() 의 raise 는 그대로 전파되어 체인을 세운다 — 그것이 의도.)"""
    try:
        for row in fn():
            log(indent + row)
    except Exception as e:
        log("%s[진단 %s 실패] %r" % (indent, label, e))


def main():
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    if not (0 <= start < len(RUNGS)):
        raise SystemExit("시작 rung 은 0..%d 이어야 한다: %r" % (len(RUNGS) - 1, sys.argv[1]))
    log("=== B 사다리 시작 · 0단 = canon_0905+RL+B0 (기존 B0) → +METER → +SAT/SAT2 → +PW25 → +B5 · 누적 · GATE %.0f 는 판정만%s ===" % (
        GATE, ("" if start == 0 else " · rung %d 부터 재개" % start)))
    tags = []; prev = None; base0 = None; base_label = None; results = []
    for i, (prefix, add) in enumerate(RUNGS):
        tags = tags + add
        if i < start:
            # 앞 단은 완주 런의 TTT 만 읽어 기준으로 삼는다 (이름 규칙은 아래 실행 분기와 동일: name_of).
            # ttt_of 는 compare_runs_ttt.py 가 완주(5395 s)만 세므로 부분 런은 여기서 '없음' 으로 떨어진다.
            nm = name_of(prefix, tags)
            try:
                ttt = ttt_of(nm)
            except Exception as e:
                log("  (기존) %s 없음 — %s 완주 런이 없어 직전 기준 없이 진행: %s" % (prefix, nm, str(e).splitlines()[0][:60]))
                prev = None
                continue
            results.append((prefix, tags[:], ttt)); prev = ttt
            if base0 is None:
                base0, base_label = ttt, prefix
            log("  (기존) TTT %s(%s) = %.1f" % (prefix, "+".join(tags), ttt))
            continue
        cfg_name = make_config(tags)
        name = name_of(prefix, tags)
        log("--- rung %s: %s%s  run=%s cfg=%s" % (prefix, "+".join(tags), ("" if prev is None else " (직전 %.1f)" % prev), name, cfg_name))
        ttt = run(name, cfg_name)
        if base0 is None:
            base0, base_label = ttt, prefix
        refs = " · ".join("%s 대비 %+.1f" % (k, ttt - v) for k, v in REF.items())
        log("  TTT %s(%s) = %.1f (%s%s)" % (prefix, "+".join(tags), ttt, ("" if prev is None else "직전 대비 %+.1f · " % (ttt - prev)), refs))
        _diag("series", lambda: h2.series(name))
        _diag("b_verdict", lambda: b_verdict(name), indent="   ")
        if "METER" in tags:
            _diag("meter_verdict", lambda: [r for r in h3.meter_verdict(name)[0] if r.startswith(("R_D_W", "R_D_E", "R_F_W", "R_F_E"))])
        if "SAT" in tags:
            _diag("sat_verdict", lambda: h4.sat_verdict(name)[:3])
        if prev is not None:
            log("  관문: %s (%+.1f, GATE %.0f) — 플랫폼은 누적 유지" % ("채택" if ttt <= prev - GATE else "기각", ttt - prev, GATE))
        results.append((prefix, tags[:], ttt)); prev = ttt
    log("=== B 사다리 끝 ===")
    for prefix, tg, ttt in results:
        log("   %s %-40s %.1f  (%s 대비 %+.1f · h7 대비 %+.1f)" % (prefix, "+".join(tg), ttt, base_label or "b0", ttt - (base0 if base0 is not None else ttt),
                                                              ttt - REF["h7(METER+SAT+SAT2+PW25)"]))
    log("B_LADDER_DONE")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # 러너 실패·미완주·미드블록 skips=0 등 run() 의 raise 는 여기서 로그에 남기고 그대로 죽는다 (모니터가 ERROR 를 볼 수 있게).
        log("ERROR B_LADDER %r" % (e,))
        raise
