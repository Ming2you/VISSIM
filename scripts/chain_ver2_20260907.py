# -*- coding: utf-8 -*-
"""Ver2 망(링크 분할·본선 3차로) 위 B 수정 재검토 ablation (2026-09-07).
기준 = v0 무제어(Ver2). 사다리(누적): a0 canon_ver2(가격 ON, B 없음) → a1 +SPILL(스필백 관측+미터 가드) → a2 +RL → a3 +METER+MF1
→ a4 +PW25 → a5 +B5 → a6 +B0. LG(리더 OFF)·SAT/SAT2(B 위 해로움)·QB(B5 충돌) 는 뺀다. 관문 GATE 50 은 판정만, 플랫폼은 누적.
Ver2 러너 인자(-Mapping/-VbsConfig/-UrbanInputGateMap/-Network) 를 넘기는 run2 를 쓴다.
사용: python chain_ver2_20260907.py [시작 rung 번호]"""
import io, json, sys, glob, re, importlib.util, subprocess, time, shutil
from pathlib import Path
from collections import OrderedDict as OD

R = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sp = importlib.util.spec_from_file_location("ch", R / "scripts/chain_lcd1000_20260906.py"); ch = importlib.util.module_from_spec(sp); sp.loader.exec_module(ch)
spb = importlib.util.spec_from_file_location("bl", R / "scripts/chain_b_ladder_20260907.py"); bl = importlib.util.module_from_spec(spb); spb.loader.exec_module(bl)
log, ttt_of, FRAG, deep_merge, RUNNER, SEED = ch.log, ch.ttt_of, ch.FRAG, ch.deep_merge, ch.RUNNER, ch.SEED
CFG = R / "evaluation/configs"
NET2 = R / "network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx"
D2 = R / "evaluation/real_world_modi_control_ver2_20260907"
MAPPING2 = D2 / "control_mapping_ver2.json"
VBSCFG2 = D2 / "real_world_modi_control_config_ver2.vbs"
GATEMAP2 = R / "evaluation/real_world_modi_inventory/urban_input_gate_map_ver2_20260907.csv"
CANON2 = json.load(io.open(CFG / "canon_ver2_20260907.json", encoding="utf-8"), object_pairs_hook=OD)
V0 = "v0_nocontrol_ver2_x18_20260907"
GATE = 50.0
FULL = 37
RUNGS = [("a0", []), ("a1", ["SPILL"]), ("a2", ["RL"]), ("a3", ["METER", "MF1"]), ("a4", ["PW25"]), ("a5", ["B5"]), ("a6", ["B0"])]


def make_config2(tags):
    name = "v_" + ("_".join(tags) if tags else "canon") + "_ver2_20260907"
    c = json.loads(json.dumps(CANON2), object_pairs_hook=OD)
    for t in tags:
        deep_merge(c, FRAG[t])
    c["_arm_note"] = ("canon_ver2_20260907 + " + " + ".join(tags)) if tags else "canon_ver2_20260907 (Ver2 ablation 기준)"
    io.open(CFG / ("%s.json" % name), "w", encoding="utf-8").write(json.dumps(c, ensure_ascii=False, indent=2) + "\n")
    out = subprocess.run([sys.executable, str(R / "scripts/verify_parameters.py"), str(CFG / ("%s.json" % name))],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    last = (out.stdout.strip().splitlines() or ["?"])[-1]
    if "PASS" not in last:
        raise RuntimeError("verify 실패 %s: %s" % (name, last))
    return name


def n_actions(outdir):
    return len(list(outdir.glob("decisions_*/action_*.json")))


def run2(name, cfg_name, controller="wu-link"):
    outdir = R / "evaluation/runs" / name
    if n_actions(outdir) >= FULL:
        log("RESUME %s (완주 런 존재, 건너뜀)" % name)
        return ttt_of(name)
    if outdir.exists():
        shutil.rmtree(outdir, ignore_errors=True)
        log("  부분 런 삭제 %s" % name)
    ps = ("& '%s' -Name '%s' -OutDir '%s' -Network '%s' -Tuning '%s' -Mapping '%s' -VbsConfig '%s' -UrbanInputGateMap '%s' -Controller '%s'%s "
          "-SimPeriod 5400 -ControlIntervalSec 150 -Seed %d -ControlStartSec 900 -WarmupController 'no-control' -StateLogIntervalSec 30 -DemandScale 1.0") % (
        RUNNER, name, outdir, NET2, CFG / ("%s.json" % cfg_name), MAPPING2, VBSCFG2, GATEMAP2, controller,
        (" -ForceStepwise" if controller == "no-control" else ""), SEED)
    log("START %s  config=%s  (Ver2)" % (name, cfg_name))
    t0 = time.time()
    with io.open(R / "evaluation/runs" / ("%s.chainlog.txt" % name), "w", encoding="utf-8") as lf:
        rc = subprocess.call(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps], stdout=lf, stderr=subprocess.STDOUT)
    n = n_actions(outdir)
    log("DONE  %s  exit=%s  %.0f min  결정 %d" % (name, rc, (time.time() - t0) / 60, n))
    rl = list(outdir.glob("runlog_*.txt"))
    if rl:
        t = io.open(rl[0], encoding="utf-8", errors="replace").read()
        m = re.search(r"SIGNAL_MIDBLOCK_COM_SKIPS=(\d+)", t)
        log("  SIGNAL_MIDBLOCK_COM_SKIPS=%s" % (m.group(1) if m else "없음"))
        if controller != "no-control" and m and int(m.group(1)) == 0:
            raise RuntimeError("미드블록 SG 가 COM 으로 넘어갔다(skips=0) — 체인 중단")
    if n < FULL:
        raise RuntimeError("%s 미완주(결정 %d) — 체인 중단" % (name, n))
    return ttt_of(name)


def spill_verdict(name):
    rows = []
    D = R / "evaluation/runs" / name / ("decisions_%s" % name)
    forced = {}; spill = {}; n = 0
    for f in sorted(D.glob("action_*.json")):
        t = int(re.search(r"action_(\d+)", f.name).group(1))
        if t < 900:
            continue
        md = json.load(io.open(f, encoding="utf-8")).get("metadata") or {}
        n += 1
        for r in ("R_D_W", "R_D_E", "R_F_W", "R_F_E"):
            forced[r] = forced.get(r, 0) + int(float(md.get("rw_spill_guard_%s" % r, 0) or 0))
            spill.setdefault(r, []).append(float(md.get("rw_spill_%s_veh" % r, 0) or 0))
    if n:
        rows.append("  스필백 가드 강제 (결정 %d): %s · spill 최대 %s · spill 평균 %s" % (
            n, forced, {r: round(max(v)) for r, v in spill.items()}, {r: round(sum(v) / len(v)) for r, v in spill.items()}))
    return rows


def _diag(label, fn):
    try:
        return fn()
    except Exception as e:  # noqa: BLE001
        return ["  [진단 %s 실패] %r" % (label, e)]


def main():
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    try:
        base = ttt_of(V0)
        log("=== Ver2 ablation 시작 · 기준 v0 무제어(Ver2) = %.1f · GATE %.0f 판정만 ===" % (base, GATE))
    except Exception as e:  # noqa: BLE001
        base = None
        log("=== Ver2 ablation 시작 · v0 TTT 없음(%s) — 기준 없이 진행 ===" % str(e)[:60])
    tags = []; prev = None; results = []
    for i, (prefix, add) in enumerate(RUNGS):
        tags = tags + add
        if i < start:
            nm = "%s_%s_ver2_x18_20260907" % (prefix, "_".join(t.lower() for t in tags) or "canon")
            try:
                ttt = ttt_of(nm); results.append((prefix, tags[:], ttt)); prev = ttt
                log("  (기존) TTT %s(%s) = %.1f" % (prefix, "+".join(tags) or "canon", ttt))
            except Exception as e:  # noqa: BLE001
                log("  (기존) %s 없음: %s" % (prefix, str(e)[:60]))
            continue
        cfg_name = make_config2(tags)
        name = "%s_%s_ver2_x18_20260907" % (prefix, "_".join(t.lower() for t in tags) or "canon")
        log("--- rung %s: %s%s" % (prefix, "+".join(tags) or "canon_ver2", ("" if prev is None else " (직전 %.1f)" % prev)))
        ttt = run2(name, cfg_name)
        log("  TTT %s(%s) = %.1f (%s%s)" % (prefix, "+".join(tags) or "canon_ver2", ttt,
                                           ("" if prev is None else "직전 대비 %+.1f · " % (ttt - prev)),
                                           ("v0 무제어 대비 %+.1f" % (ttt - base)) if base is not None else ""))
        for row in _diag("series", lambda: bl.h2.series(name)):
            log("     " + row)
        for row in _diag("b", lambda: bl.b_verdict(name)):
            log("   " + row)
        if "SPILL" in tags:
            for row in _diag("spill", lambda: spill_verdict(name)):
                log("   " + row)
        if "METER" in tags:
            rows, _ = bl.h3.meter_verdict(name)
            for r in rows:
                if r[:5] in ("R_D_W", "R_F_E", "R_F_W", "R_D_E"):
                    log("     " + r)
        if prev is not None:
            log("  관문: %s (%+.1f, GATE %.0f) — 플랫폼은 누적 유지" % ("채택" if ttt <= prev - GATE else "기각", ttt - prev, GATE))
        results.append((prefix, tags[:], ttt)); prev = ttt
    log("=== Ver2 ablation 끝 ===")
    for prefix, tg, ttt in results:
        log("   %s %-36s %.1f%s" % (prefix, "+".join(tg) or "canon_ver2", ttt, ("  (v0 대비 %+.1f)" % (ttt - base)) if base is not None else ""))
    log("VER2_LADDER_DONE")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        log("ERROR VER2_LADDER %r" % (e,))
        raise
