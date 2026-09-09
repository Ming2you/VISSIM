# -*- coding: utf-8 -*-
"""옛 망 상수를 Ver2 실측으로 갈아끼운 사다리 — n2 에서 분기 (2026-09-09).

왜. 2026-09-08 사다리에서 조각의 성패가 **상수의 출처**와 갈렸다.

    Ver2 에서 재측정한 조각   SATV2  -181.3  (최대 이득)
    옛 망 상수를 쓰는 조각    METER  +203.8  (최대 손해) · B0 는 옛 분할

그래서 손해가 아이디어인지 상수인지 가른다. 두 상수를 Ver2 자료로 다시 만들어 얹는다.

  (1) METER `per_lane_veh_per_cycle`  <- outputs/meter_transfer_ver2_20260909.json
      옛 표는 낮은 green 유량을 절반으로 과소평가하고(green=2 에서 0.71 vs 실측 1.33)
      높은 green 을 4.20 까지 선형 상승으로 본다(실측은 green≈7 에서 3.54 로 포화).
      과소평가하면 배분기가 목표 rate 를 맞추려 **필요보다 큰 green** 을 골라 더 흘린다 —
      실측 거동과 맞는다(n3 평균 rate 687 -> 823 vph, 폐쇄 3~6% -> 0%).
      계측기는 VISSIM 링크평가(150 s)이고 용량이라 **상위 포락선(p95) + 단조 보정**을 쓴다.
      완전개방(green=10)은 수요 제약이라 그 칸은 하한이다.

  (2) B0 `boundary_out.ramp_split_json` <- outputs/boundary_out_ramp_split_ver2_20260909.json
      옛 분할은 옛 망 x18 에서 잰 것이고, 옛 생성기를 Ver2 에 그냥 돌리면 R_D_W·R_F_W 를
      통째로 잃는다(경로의 첫 커넥터만 봐서 Ver2 의 중간 커넥터 뒤 램프를 놓친다).
      Ver2 경로 총량: 자유 0.250->0.167 · 0.333->0.200 으로 램프행이 늘었다.

분기 기준 = n21x15_n2_spill_rl (SPILL+RL, TTT 7346.5). n0~n2 는 METER·B0 를 안 쓰므로 동일하다.
사다리: f3 +METER+MF1 · f4 +PW25 · f5 +B5 · f6 +B0 · f7 +SATV2 · f8 +SAT3
각 단의 '직전 대비'를 2026-09-08 사다리의 같은 조각과 나란히 찍는다 — 그 차이가 상수 교체의 효과다.

사용: python chain_n21_ver2fix_20260909.py [시작 rung 번호]
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
LOG = R / "evaluation/runs/chain_n21x15_ver2fix_20260909.log"
PROFILE = R / "evaluation/configs/demand_profiles/ver2_fdsweep_x15_20260907.csv"
V0 = "n21_x15_nocontrol_ver2_20260907"
BRANCH_BASE_RUN = "n21x15_n2_spill_rl_20260908"
METER_TABLE_JSON = R / "outputs/meter_transfer_ver2_20260909.json"
BOUNDARY_SPLIT_JSON = "outputs/boundary_out_ramp_split_ver2_20260909.json"
FULL = 37
GATE = 50.0
STALL_SEC = int(os.environ.get("N21_STALL_SEC", "2400"))

RUNGS = [("f3", ["METER", "MF1"]), ("f4", ["PW25"]), ("f5", ["B5"]),
         ("f6", ["B0"]), ("f7", ["SATV2"]), ("f8", ["SAT3"])]
BASE_FRAGS = ["SPILL", "RL"]
# 2026-09-08 사다리의 같은 조각 '직전 대비' — 옆에 세워 상수 교체 효과를 읽는다.
REF_DELTA = {"f3": +203.8, "f4": -81.3, "f5": +14.8, "f6": -54.0, "f7": -181.3, "f8": None}


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


def ver2_overrides(base, frags):
    """옛 망 상수를 Ver2 실측으로 교체한다. 해당 조각이 없으면 아무것도 안 한다."""
    notes = []
    if "METER" in frags:
        tbl = json.load(io.open(METER_TABLE_JSON, encoding="utf-8"))["per_lane_veh_per_cycle"]
        if not tbl:
            raise RuntimeError("Ver2 미터 전달함수 표가 비어 있다: %s" % METER_TABLE_JSON)
        sec = base["actuation"]["real_world_ramp_metering"]
        sec["per_lane_veh_per_cycle"] = OD((k, float(v)) for k, v in sorted(tbl.items(), key=lambda x: int(x[0])))
        sec["_note_per_lane_veh_per_cycle"] = (
            "Ver2 재측정 (%s). 옛 lcd1000 표는 낮은 green 을 절반으로 과소평가하고 green=10 까지 "
            "선형 상승을 가정했다. 계측기 = VISSIM 링크평가 150 s, 통계 = p95 상위 포락선 + 단조 보정 "
            "(완전개방 칸은 수요 제약이라 하한)." % METER_TABLE_JSON.name)
        notes.append("METER 표 %d칸" % len(tbl))
    if "B0" in frags:
        base["urban"]["boundary_out"]["ramp_split_json"] = BOUNDARY_SPLIT_JSON
        base["urban"]["boundary_out"]["_note_ramp_split_json"] = (
            "Ver2 경로결정에서 재생성 (2026-09-09). 옛 20260905 판은 옛 망 x18 이고, 옛 생성기를 "
            "Ver2 에 돌리면 linkSeq 첫 커넥터만 봐서 R_D_W·R_F_W 를 통째로 잃는다.")
        notes.append("B0 분할 Ver2")
    return notes


def build_cfg(tag, frags):
    base = json.load(io.open(CFG / (BASE_CFG + ".json"), encoding="utf-8"), object_pairs_hook=OD)
    for f in frags:
        base = deep_merge(base, FRAG[f])
    notes = ver2_overrides(base, frags)
    base["name"] = "n21x15f_%s" % tag
    base["description"] = "%s + %s (Ver2 상수 교체 사다리 %s: %s)" % (
        BASE_CFG, " ".join(frags), tag, ", ".join(notes) or "교체 없음")
    p = CFG / ("n21f_%s_20260909.json" % tag)
    io.open(p, "w", encoding="utf-8").write(json.dumps(base, ensure_ascii=False, indent=1))
    return p, notes


def integrity(outdir, name):
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
    log("=== Ver2 상수 교체 사다리 · x15 · 무제어 %s = %.1f · 분기 %s(SPILL+RL) = %.1f ==="
        % (V0, base, BRANCH_BASE_RUN, prev))
    frags, results = list(BASE_FRAGS), []
    for i, (tag, add) in enumerate(RUNGS):
        frags = frags + add
        if i < start:
            continue
        name = "n21x15f_%s_%s_20260909" % (tag, "_".join(f.lower() for f in frags))
        cfg_path, notes = build_cfg(tag, frags)
        try:
            t = run(name, cfg_path)
        except Exception as exc:
            log("ERROR %s: %s" % (tag, exc))
            break
        d_base, d_prev = t - base, t - prev
        ref = REF_DELTA.get(tag)
        cmp_txt = ("  | 옛 상수판 %+.1f · 차이 %+.1f" % (ref, d_prev - ref)) if ref is not None else ""
        flag = "  ← 직전 대비 악화" if d_prev > GATE else ""
        log("RESULT %-4s %-38s TTT %8.1f  무제어 %+8.1f (%+.2f%%)  직전 %+8.1f%s%s"
            % (tag, "+".join(frags), t, d_base, 100 * d_base / base, d_prev, cmp_txt, flag))
        results.append((tag, "+".join(frags), t, d_base, d_prev, ref))
        prev = t
    log("=== 요약 (무제어 %.1f · 분기 %.1f) ===" % (base, ttt_of(BRANCH_BASE_RUN)))
    for tag, f, t, db, dp, ref in results:
        log("  %-4s %-38s %8.1f  %+8.1f  %+8.1f%s"
            % (tag, f, t, db, dp, ("  (옛 상수판 %+.1f)" % ref) if ref is not None else ""))
    log("N21X15_VER2FIX_DONE")


if __name__ == "__main__":
    main()
