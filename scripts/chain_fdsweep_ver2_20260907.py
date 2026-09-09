# -*- coding: utf-8 -*-
"""Ver2 본선 수요 sweep — 무제어 런으로 세그먼트별 q-k 기본도를 제대로 채우기 위한 발사기 (2026-09-07).

왜. x18 한 점(v0)만으로는 FD 가 축퇴한다 — FW_E S0~S3 과 FW_W S0~S2 는 처음부터 끝까지 정체 가지에만 있고
(자유류 표본 0), 나머지 열 개 세그먼트는 병목 하류라 영원히 자유류다(k_p95 < 19). 그래서 v_free 와 k_crit 이
서로 상쇄돼 적합이 v_free 상한에 붙는다. 수요를 낮춰 같은 세그먼트를 자유 → 용량 → 정체로 훑어야 한다.

무엇을. 도시 수요(urban_input)는 1.00 으로 **고정**하고 본선 두 입력(1098 경부_EB · 1099 경부_NB)만 배율을
건다. 그래야 램프 유입(도시발)은 그대로인 채 본선/램프 유량비만 바뀌어 합류·위빙 항이 식별된다.
배율은 망의 현재 값(첨두 8316 vph = x18) 대비이므로 x15/x12/x08/x04 는 첨두 6930/5544/3696/1848 vph.

전제. VISSIM 1인스턴스 라이선스 → 순차 실행. 한 런 약 13분.
사용: python chain_fdsweep_ver2_20260907.py
"""
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
RUNGS = [("a0", []), ("a1", ["SPILL"]), ("a2", ["RL"]), ("a3", ["METER", "MF1"]), ("a4", ["PW25"]), ("a5", ["B5"]), ("a6", ["B0"]),
         # 2026-09-07 사용자: SAT 계열도 이 사다리에 곁들임 — v0(Ver2 무제어) 뒤 씨앗 재생성 후 start=7 로 이어 돈다.
         ("a7", ["SATV2"]), ("a8", ["SAT3"])]


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



LEVELS = [("x15", "0.8333"), ("x12", "0.6667"), ("x08", "0.4444"), ("x04", "0.2222")]
PROF = R / "evaluation/configs/demand_profiles"


def run_fd(tag, mult):
    """무제어 + 본선 전용 수요배율. 도시(urban_input)는 1.0 고정이라 본선 FD 만 쓸어본다."""
    name = "fd_%s_nocontrol_ver2_20260907" % tag
    outdir = R / "evaluation/runs" / name
    if n_actions(outdir) >= FULL:
        log("RESUME %s (완주 런 존재, 건너뜀)" % name)
        return name
    if outdir.exists():
        shutil.rmtree(outdir, ignore_errors=True)
        log("  부분 런 삭제 %s" % name)
    prof = PROF / ("ver2_fdsweep_%s_20260907.csv" % tag)
    ps = ("& '%s' -Name '%s' -OutDir '%s' -Network '%s' -Tuning '%s' -Mapping '%s' -VbsConfig '%s' "
          "-UrbanInputGateMap '%s' -Controller 'no-control' -ForceStepwise -SimPeriod 5400 "
          "-ControlIntervalSec 150 -Seed %d -ControlStartSec 900 -WarmupController 'no-control' "
          "-StateLogIntervalSec 30 -DemandScale 1.0 -DemandProfile '%s'") % (
        RUNNER, name, outdir, NET2, CFG / "canon_ver2_20260907.json", MAPPING2, VBSCFG2, GATEMAP2, SEED, prof)
    log("START %s  본선 배율 %s (기준 x18 대비)" % (name, mult))
    t0 = time.time()
    with io.open(R / "evaluation/runs" / ("%s.chainlog.txt" % name), "w", encoding="utf-8") as lf:
        rc = subprocess.call(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
                             stdout=lf, stderr=subprocess.STDOUT)
    n = n_actions(outdir)
    log("DONE  %s  exit=%s  %.0f min  결정 %d" % (name, rc, (time.time() - t0) / 60, n))
    rl = list(outdir.glob("runlog_*.txt"))
    if rl:
        t = io.open(rl[0], encoding="utf-8", errors="replace").read()
        for key in ("DEMAND_PROFILE_APPLIED", "DEMAND_PROFILE_INPUT no=1098", "DEMAND_PROFILE_INPUT no=1099"):
            for ln in t.splitlines():
                if ln.startswith(key):
                    log("  %s" % ln.strip()[:190])
                    break
    if n < FULL:
        raise RuntimeError("%s 미완주(결정 %d)" % (name, n))
    return name


def main():
    log("=== Ver2 본선 수요 sweep (무제어) — FD 재보정용. 도시 수요 고정, 본선만 배율 ===")
    log("    x18(=v0, 첨두 8316 vph) 은 이미 완주 · 여기서는 x15/x12/x08/x04 를 순차로 돈다")
    done = []
    for tag, mult in LEVELS:
        try:
            done.append(run_fd(tag, mult))
        except Exception as exc:
            log("ERROR %s: %s" % (tag, exc))
            break
    log("FD_SWEEP_DONE 완주 %d/%d: %s" % (len(done), len(LEVELS), ", ".join(done)))


if __name__ == "__main__":
    main()
