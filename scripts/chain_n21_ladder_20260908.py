# -*- coding: utf-8 -*-
"""Ver2 · 본선 21셀 · D-lit 보정 위에서 도는 ablation 사다리 (2026-09-08).

기준 = `n21_x15_nocontrol_ver2_20260907` (무제어, TTT 7403.9 — 같은 망·시드·수요).
수요는 **x15**(본선 배율 1.5, 도시는 그대로) 다 — 2026-09-08 사용자 결정. x18 은 FW_E 수요의 절반이
진입조차 못 해 TTT 가 제어에 구조적으로 불리한 지표가 된다(방류를 개선하면 차가 더 들어와 TTT 가 오른다).
0단은 `canon_ver2n21_dlit_20260908` 자체다: 21셀 격자 + 42셀 v_free 실측 + 급 형상 + 문헌 제약 동역학
(tau 18 s · nu 30 · kappa 40 · delta_merge 0.3 · lane_drop_phi 3.0).

사다리(누적):
  n0  canon_dlit            21셀 + 재보정만
  n1  +SPILL                램프 스필백 관측 + 미터 가드
  n2  +RL                   has_ramps 신호의 ramp-aware 국소 채점
  n3  +METER +MF1           실측 미터 전달함수 + 수요 기반 폐쇄 벌점
  n4  +PW25                 현시가격 가중 0.25
  n5  +B5                   게이트발 on-ramp 큐
  n6  +B0                   leg_split + offramp_direct + 실측 램프 분율
  n7  +SATV2                실측 포화유량(차로군 지속 방류)
  n8  +SAT3                 경계 kind 까지 확장

관문: 각 단이 직전 단 대비 GATE(50 veh·h) 이상 나빠지면 그 단을 알리고 계속한다(판정용, 플랫폼은 누적).
사용: python chain_n21_ladder_20260908.py [시작 rung 번호]
"""
import importlib.util
import io
import os
import json
import re
import shutil
import subprocess
import sys
import time
from collections import OrderedDict as OD
from pathlib import Path

R = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_sp = importlib.util.spec_from_file_location("ch", R / "scripts/chain_lcd1000_20260906.py")
ch = importlib.util.module_from_spec(_sp)
_sp.loader.exec_module(ch)
FRAG, deep_merge, RUNNER, SEED = ch.FRAG, ch.deep_merge, ch.RUNNER, ch.SEED

CFG = R / "evaluation/configs"
BASE_CFG = "canon_ver2n21_dlit_20260908"
NET = R / "network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx"
D21 = R / "evaluation/real_world_modi_control_ver2n21_20260907"
MAPPING = D21 / "control_mapping_ver2n21.json"
VBSCFG = D21 / "real_world_modi_control_config_ver2n21.vbs"
GATEMAP = R / "evaluation/real_world_modi_inventory/urban_input_gate_map_ver2_20260907.csv"
LOG = R / "evaluation/runs/chain_n21x15_ladder_20260908.log"
PROFILE = R / "evaluation/configs/demand_profiles/ver2_fdsweep_x15_20260907.csv"
V0 = "n21_x15_nocontrol_ver2_20260907"
FULL = 37
GATE = 50.0
STALL_SEC = int(os.environ.get("N21_STALL_SEC", "2400"))

RUNGS = [("n0", []), ("n1", ["SPILL"]), ("n2", ["RL"]), ("n3", ["METER", "MF1"]),
         ("n4", ["PW25"]), ("n5", ["B5"]), ("n6", ["B0"]), ("n7", ["SATV2"]), ("n8", ["SAT3"])]


def log(msg):
    line = "%s  %s" % (time.strftime("%m-%d %H:%M:%S"), msg)
    print(line, flush=True)
    with io.open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def ttt_of(name):
    out = subprocess.run([sys.executable, str(R / "scripts/compare_runs_ttt.py"), name, "--base", name],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    for line in out.stdout.splitlines():
        if line.strip().startswith(name):
            m = re.search(r"\s(\d+\.\d+)\s", line)
            if m:
                return float(m.group(1))
    raise RuntimeError("TTT 파싱 실패 %s" % name)


def build_cfg(tag, frags):
    base = json.load(io.open(CFG / (BASE_CFG + ".json"), encoding="utf-8"), object_pairs_hook=OD)
    for f in frags:
        base = deep_merge(base, FRAG[f])
    base["name"] = "n21x15_%s" % tag
    base["description"] = "%s + %s (21셀 D-lit 사다리 %s)" % (BASE_CFG, " ".join(frags) or "없음", tag)
    p = CFG / ("n21_%s_20260908.json" % tag)
    io.open(p, "w", encoding="utf-8").write(json.dumps(base, ensure_ascii=False, indent=1))
    return p


def run(name, cfg_path):
    outdir = R / "evaluation/runs" / name
    if len(list(outdir.glob("decisions_*/action_*.json"))) >= FULL:
        log("RESUME %s (완주 존재)" % name)
        return ttt_of(name)
    if outdir.exists():
        shutil.rmtree(outdir, ignore_errors=True)
    # 무진행 임계 300 s 로는 시뮬이 시작조차 못 한다. 죽는 자리는 결정이 아니라 **수요 스케일링**이다:
    #   DEMAND_INTERVAL_SCHEDULE 직후 COM 한 번에 VISSIM 이 5분 넘게 붙잡혀 있고(2026-09-08 실측:
    #   cscript CPU 0.5 s / VISSIM 240 s+), 그동안 감시 대상 파일이 하나도 안 바뀐다.
    #   run_lane_narrow_ab_20260816.ps1 이 같은 이유로 이미 2400 을 쓴다 — 같은 값으로 맞춘다.
    ps = ("& '%s' -Name '%s' -OutDir '%s' -Network '%s' -Tuning '%s' -Mapping '%s' -VbsConfig '%s' "
          "-UrbanInputGateMap '%s' -Controller 'wu-link' -SimPeriod 5400 -ControlIntervalSec 150 "
          "-Seed %d -ControlStartSec 900 -WarmupController 'no-control' -StateLogIntervalSec 30 "
          "-DemandScale 1.0 -DemandProfile '%s' -StallSec %d") % (RUNNER, name, outdir, NET, cfg_path, MAPPING,
                                                                  VBSCFG, GATEMAP, SEED, PROFILE, STALL_SEC)
    log("START %s  config=%s" % (name, cfg_path.name))
    t0 = time.time()
    with io.open(R / "evaluation/runs" / ("%s.chainlog.txt" % name), "w", encoding="utf-8") as lf:
        rc = subprocess.call(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
                             stdout=lf, stderr=subprocess.STDOUT)
    n = len(list(outdir.glob("decisions_*/action_*.json")))
    log("DONE  %s exit=%s %.0f min 결정 %d/%d" % (name, rc, (time.time() - t0) / 60, n, FULL))
    rl = list(outdir.glob("runlog_*.txt"))
    if rl:
        t = io.open(rl[0], encoding="utf-8", errors="replace").read()
        m = re.search(r"SIGNAL_MIDBLOCK_COM_SKIPS=(\d+)", t)
        log("  SIGNAL_MIDBLOCK_COM_SKIPS=%s" % (m.group(1) if m else "없음"))
        if not m or int(m.group(1)) == 0:
            raise RuntimeError("미드블록 SG 가 COM 으로 넘어갔다 — 체인 중단 (%s)" % name)
    if n < FULL:
        raise RuntimeError("%s 미완주(결정 %d)" % (name, n))
    return ttt_of(name)


def main():
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    base = ttt_of(V0)
    log("=== 21셀 D-lit 사다리 · 수요 x15 · 무제어 기준 %s = %.1f ===" % (V0, base))
    frags, prev, results = [], None, []
    for i, (tag, add) in enumerate(RUNGS):
        frags = frags + add
        if i < start:
            continue
        name = "n21x15_%s_%s_20260908" % (tag, "_".join(f.lower() for f in frags) or "canon")
        cfg_path = build_cfg(tag, frags)
        try:
            t = run(name, cfg_path)
        except Exception as exc:
            log("ERROR %s: %s" % (tag, exc))
            break
        d_base = t - base
        d_prev = (t - prev) if prev is not None else 0.0
        flag = "  ← 직전 대비 악화" if (prev is not None and d_prev > GATE) else ""
        log("RESULT %-4s %-46s TTT %8.1f  무제어 대비 %+8.1f (%+.2f%%)  직전 대비 %+8.1f%s"
            % (tag, "+".join(frags) or "canon", t, d_base, 100 * d_base / base, d_prev, flag))
        results.append((tag, "+".join(frags) or "canon", t, d_base, d_prev))
        prev = t
    log("=== 사다리 요약 (무제어 %.1f) ===" % base)
    for tag, f, t, db, dp in results:
        log("  %-4s %-46s %8.1f  %+8.1f  %+8.1f" % (tag, f, t, db, dp))
    log("N21X15_LADDER_DONE")


if __name__ == "__main__":
    main()
