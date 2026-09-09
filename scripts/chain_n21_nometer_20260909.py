# -*- coding: utf-8 -*-
"""METER 를 뺀 가지 — n2(SPILL+RL) 위에 나머지를 직접 얹는다 (2026-09-09).

왜. 2026-09-08 사다리에서 **METER+MF1 이 혼자 +203.8** 을 까먹었다(무제어 7403.9 기준):

    n0 canon 7433.7 (+29.8) · n1 +SPILL 7390.1 (-13.8) · n2 +RL 7346.5 (-57.4)  <- 최고점
    n3 +METER+MF1 7550.3 (+146.4, 직전 +203.8)  <- 관문
    n4 +PW25 7469.0 · n5 +B5 7483.8 · n6 +B0 7429.8   (넷이 합쳐 -120 회복, 원복 실패)

n4~n8 은 전부 "이미 +203.8 손해를 안은 상태"에서 잰 값이라 그 단들의 고유 효과가 METER 손실에
가려진다. 이 가지는 같은 조각을 **METER 없이** 같은 순서로 얹어 그 둘을 가른다.

  기준 = n2 (SPILL+RL, TTT 7346.5) — 이미 돌았으므로 다시 안 돌린다.
  m1 +PW25   m2 +B5   m3 +B0   m4 +SATV2   m5 +SAT3

판정. 각 단의 "직전 대비"를 2026-09-08 사다리의 같은 조각과 맞대면 된다.
  같으면  -> 그 조각의 효과는 METER 와 무관(가법)
  다르면  -> 상호작용이 있고, METER 손실의 일부는 그 조각이 되받아치던 것이다

무결성. 원 사다리와 같은 관문을 쓴다 — 결정 37/37, `SIGNAL_MIDBLOCK_COM_SKIPS>0`.
그리고 여기서는 `DECISIONS_FAILED` 도 본다: 2026-09-08 에 매핑 `signals` 결함으로 wu-link
결정 31/31 이 CSV 단계에서 죽었는데 시뮬은 완주해 **조용히 무제어**가 된 적이 있다.

사용: python chain_n21_nometer_20260909.py [시작 rung 번호]
"""
import importlib.util
import io
import json
import os
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
LOG = R / "evaluation/runs/chain_n21x15_nometer_20260909.log"
PROFILE = R / "evaluation/configs/demand_profiles/ver2_fdsweep_x15_20260907.csv"
V0 = "n21_x15_nocontrol_ver2_20260907"
BRANCH_BASE_RUN = "n21x15_n2_spill_rl_20260908"          # 이 가지의 0단 = 원 사다리 n2
FULL = 37
GATE = 50.0
STALL_SEC = int(os.environ.get("N21_STALL_SEC", "2400"))

# 원 사다리의 같은 조각과 맞대기 위해 순서를 그대로 둔다 — METER·MF1 만 뺐다.
RUNGS = [("m1", ["PW25"]), ("m2", ["B5"]), ("m3", ["B0"]), ("m4", ["SATV2"]), ("m5", ["SAT3"])]
BASE_FRAGS = ["SPILL", "RL"]
# 2026-09-08 사다리의 같은 조각 "직전 대비" — 보고할 때 옆에 세운다.
REF_DELTA = {"m1": -81.3, "m2": +14.8, "m3": -54.0, "m4": None, "m5": None}


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
    base["description"] = "%s + %s (METER 없는 가지 %s)" % (BASE_CFG, " ".join(frags), tag)
    p = CFG / ("n21nm_%s_20260909.json" % tag)
    io.open(p, "w", encoding="utf-8").write(json.dumps(base, ensure_ascii=False, indent=1))
    return p


def integrity(outdir, name):
    """완주만으로는 부족하다 — 결정이 실제로 플랜트에 적용됐는지까지 본다."""
    rl = list(outdir.glob("runlog_*.txt"))
    if not rl:
        raise RuntimeError("%s 런로그 없음" % name)
    t = io.open(rl[0], encoding="utf-8", errors="replace").read()
    m = re.search(r"SIGNAL_MIDBLOCK_COM_SKIPS=(\d+)", t)
    ok = re.search(r"DECISIONS_OK=(\d+)", t)
    bad = re.search(r"DECISIONS_FAILED=(\d+)", t)
    log("  SKIPS=%s DECISIONS_OK=%s FAILED=%s"
        % (m.group(1) if m else "없음", ok.group(1) if ok else "?", bad.group(1) if bad else "?"))
    if not m or int(m.group(1)) == 0:
        raise RuntimeError("미드블록 SG 가 COM 으로 넘어갔다 — 체인 중단 (%s)" % name)
    if bad and int(bad.group(1)) > 0:
        raise RuntimeError("결정 %s건이 플랜트에 적용되지 않았다(조용한 무제어) — 체인 중단 (%s)"
                           % (bad.group(1), name))


def run(name, cfg_path):
    outdir = R / "evaluation/runs" / name
    if len(list(outdir.glob("decisions_*/action_*.json"))) >= FULL:
        log("RESUME %s (완주 존재)" % name)
        return ttt_of(name)
    if outdir.exists():
        shutil.rmtree(outdir, ignore_errors=True)
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
    integrity(outdir, name)
    if n < FULL:
        raise RuntimeError("%s 미완주(결정 %d)" % (name, n))
    return ttt_of(name)


def main():
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    base = ttt_of(V0)
    prev = ttt_of(BRANCH_BASE_RUN)
    log("=== METER 없는 가지 · 수요 x15 · 무제어 %s = %.1f · 분기 기준 %s(SPILL+RL) = %.1f ==="
        % (V0, base, BRANCH_BASE_RUN, prev))
    frags, results = list(BASE_FRAGS), []
    for i, (tag, add) in enumerate(RUNGS):
        frags = frags + add
        if i < start:
            continue
        name = "n21x15_%s_%s_20260909" % (tag, "_".join(f.lower() for f in frags))
        cfg_path = build_cfg(tag, frags)
        try:
            t = run(name, cfg_path)
        except Exception as exc:
            log("ERROR %s: %s" % (tag, exc))
            break
        d_base, d_prev = t - base, t - prev
        ref = REF_DELTA.get(tag)
        cmp_txt = ""
        if ref is not None:
            cmp_txt = "  | METER 사다리 같은 조각 %+.1f · 차이 %+.1f" % (ref, d_prev - ref)
        flag = "  ← 직전 대비 악화" if d_prev > GATE else ""
        log("RESULT %-4s %-42s TTT %8.1f  무제어 대비 %+8.1f (%+.2f%%)  직전 대비 %+8.1f%s%s"
            % (tag, "+".join(frags), t, d_base, 100 * d_base / base, d_prev, cmp_txt, flag))
        results.append((tag, "+".join(frags), t, d_base, d_prev, ref))
        prev = t
    log("=== 가지 요약 (무제어 %.1f · 분기 기준 %.1f) ===" % (base, ttt_of(BRANCH_BASE_RUN)))
    for tag, f, t, db, dp, ref in results:
        log("  %-4s %-42s %8.1f  %+8.1f  %+8.1f%s"
            % (tag, f, t, db, dp, ("  (METER판 %+.1f)" % ref) if ref is not None else ""))
    log("N21X15_NOMETER_DONE")


if __name__ == "__main__":
    main()
