# -*- coding: utf-8 -*-
"""용량강하 + 미터 가격 탐침 2단 미니 사다리 — f3 위에서 분기 (2026-09-09).

왜. 2026-09-09 진단에서 미터링이 일을 안 하는 이유가 둘로 갈렸다.

  (물리) `capacity_drop_discharge_phi` 가 **1.0 = 꺼짐**이다. 이 값이 <1 이면 혼잡(ρ>ρ_cr) 셀의
         송출이 용량의 φ배로 제한된다 — 즉 "임계 아래로 지키면 방류를 지킨다"는 payoff 가 생긴다.
         적용 위치가 결정적이다: `local_freeway_plant.freeway_substep_local` 은 팔로워가
         VSL·미터 후보를 채점하는 바로 그 함수다(wu_faithful_follower.py:2329).
         vendor 주석의 문헌 근거 = breakdown 후 배출률 5~18% 감소(Hall & Agyemang-Duah 1991;
         Cassidy & Bertini 1999), 권장 민감도 arm φ=0.85. 같은 주석이 δ_merge 를 두고
         "metering 의 교과서적 payoff 신설"이라 적었다 — δ 는 켜져 있고(0.3) φ 만 꺼져 있었다.

  (신호) 미터 가격이 붕괴 창(t=900~1650) 내내 **정확히 0.000e+00** 이다. 작동점이
         previous.ramp_metering = 1800(램프 용량)인데 실측 램프 수요는 428~571 vph 라,
         탐침 폭 d_r = max(δ 300, trust 0.20 × cap 1800) = 360 -> m_lo 1440 이 여전히 수요보다
         한참 위다. 두 코너의 롤아웃이 동일해 유한차분이 0 이 된다.
         `metering_price_trust_frac` 0.75 면 d_r = 1350 -> m_lo 450 으로 **수요를 가로지른다**.
         vendor 주석이 이 손잡이의 용도를 그대로 적어 뒀다: "B3TR: trust 설정 시 측정폭을
         trust 반경에 맞춘다 — 가격이 유효해야 하는 바로 그 구간을 측정하는 secant".

분리해서 잰다. 한 번에 둘 다 넣으면 어느 쪽이 일했는지 못 가린다.

  분기 기준 = n21x15f_f3 (SPILL+RL+METER+MF1, Ver2 전달함수, TTT 7496.6)
  g1  +CAPDROP(φ=0.85)          물리
  g2  +METERPROBE(trust 0.75)   신호

기준선: 무제어 7403.9 · n2(SPILL+RL) 7346.5 · f3 7496.6.

사용: python chain_n21_capdrop_meterprobe_20260909.py [시작 rung 번호]
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
LOG = R / "evaluation/runs/chain_n21x15_capdrop_20260909.log"
PROFILE = R / "evaluation/configs/demand_profiles/ver2_fdsweep_x15_20260907.csv"
V0 = "n21_x15_nocontrol_ver2_20260907"
BRANCH_BASE_RUN = "n21x15f_f3_spill_rl_meter_mf1_20260909"
METER_TABLE_JSON = R / "outputs/meter_transfer_ver2_20260909.json"
FULL = 37
GATE = 50.0
STALL_SEC = int(os.environ.get("N21_STALL_SEC", "2400"))

BASE_FRAGS = ["SPILL", "RL", "METER", "MF1"]
RUNGS = [("g1", "CAPDROP"), ("g2", "METERPROBE")]
CAP_DROP_PHI = float(os.environ.get("N21_CAPDROP_PHI", "0.85"))
METER_TRUST_FRAC = float(os.environ.get("N21_METER_TRUST", "0.75"))


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


def build_cfg(tag, switches):
    base = json.load(io.open(CFG / (BASE_CFG + ".json"), encoding="utf-8"), object_pairs_hook=OD)
    for f in BASE_FRAGS:
        base = deep_merge(base, FRAG[f])
    # f3 와 같은 Ver2 전달함수를 얹는다(이 가지는 f3 위에서 분기한다).
    tbl = json.load(io.open(METER_TABLE_JSON, encoding="utf-8"))["per_lane_veh_per_cycle"]
    sec = base["actuation"]["real_world_ramp_metering"]
    sec["per_lane_veh_per_cycle"] = OD((k, float(v)) for k, v in sorted(tbl.items(), key=lambda x: int(x[0])))
    sec["_note_per_lane_veh_per_cycle"] = (
        "Ver2 재측정 (%s). 옛 lcd1000 표는 낮은 green 을 절반으로 과소평가하고 green=10 까지 "
        "선형 상승을 가정했다. 계측기 = VISSIM 링크평가 150 s, 통계 = p95 상위 포락선 + 단조 보정 "
        "(완전개방 칸은 수요 제약이라 하한)." % METER_TABLE_JSON.name)
    notes = ["METER 표 Ver2"]
    if "CAPDROP" in switches:
        base["config_overrides"]["network"]["capacity_drop_discharge_phi"] = CAP_DROP_PHI
        # 주석은 `config_overrides.network` 안에 넣으면 **안 된다.** 그 절은
        # `NetworkConfig(**raw["network"])` 로 그대로 풀리므로 모르는 키 하나가
        # `TypeError: unexpected keyword argument` 로 첫 결정에서 런을 죽인다
        # (2026-09-09 에 이걸로 g1 을 한 번 버렸다). tuning 최상위 `_notes` 는
        # `tuning_to_config_overrides` 가 읽는 5개 절이 아니라 그냥 무시된다.
        base.setdefault("_notes", OD())["capacity_drop"] = (
            "혼잡(ρ>ρ_cr) 셀의 송출을 용량의 %.2f 배로 제한. vendor 기본 1.0 = 꺼짐이었다. "
            "적용 위치가 팔로워의 후보 채점 함수(local_freeway_plant.freeway_substep_local)라 "
            "미터·VSL 이 '임계 아래로 지키면 방류를 지킨다'는 payoff 를 처음으로 갖는다. "
            "문헌 근거 = breakdown 후 배출률 5~18%% 감소, vendor 권장 arm 0.85." % CAP_DROP_PHI)
        notes.append("CAPDROP φ=%.2f" % CAP_DROP_PHI)
    if "METERPROBE" in switches:
        base.setdefault("adapter", OD()).setdefault("flagship", OD())
        base["adapter"]["flagship"]["metering_price_trust_frac"] = METER_TRUST_FRAC
        base["adapter"]["flagship"]["_note_metering_price_trust_frac"] = (
            "미터 가격 탐침 폭. 종전 0.20 이면 d_r = max(300, 0.20×1800) = 360 -> m_lo 1440 인데 "
            "실측 램프 수요가 428~571 vph 라 두 코너의 롤아웃이 같아 가격이 정확히 0 이었다"
            "(붕괴 창 t=900~1650 전 구간 실측). %.2f 면 d_r = 1350 -> m_lo 450 으로 수요를 가로지른다."
            % METER_TRUST_FRAC)
        notes.append("METERPROBE trust=%.2f" % METER_TRUST_FRAC)
    base["name"] = "n21x15g_%s" % tag
    base["description"] = "%s + %s (%s)" % (BASE_CFG, "+".join(BASE_FRAGS), ", ".join(notes))
    p = CFG / ("n21g_%s_20260909.json" % tag)
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
        raise RuntimeError("결정 %s건이 플랜트에 적용되지 않았다 — 체인 중단 (%s)" % (bad.group(1), name))


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
    log("=== 용량강하·미터탐침 · x15 · 무제어 %.1f · 분기 %s(f3) = %.1f ==="
        % (base, BRANCH_BASE_RUN, prev))
    switches, results = [], []
    for i, (tag, sw) in enumerate(RUNGS):
        switches = switches + [sw]
        if i < start:
            continue
        name = "n21x15g_%s_%s_20260909" % (tag, "_".join(s.lower() for s in switches))
        cfg_path, notes = build_cfg(tag, switches)
        try:
            t = run(name, cfg_path)
        except Exception as exc:
            log("ERROR %s: %s" % (tag, exc))
            break
        log("RESULT %-3s %-30s TTT %8.1f  무제어 %+8.1f (%+.2f%%)  f3 대비 %+8.1f  직전 %+8.1f"
            % (tag, "+".join(switches), t, t - base, 100 * (t - base) / base,
               t - ttt_of(BRANCH_BASE_RUN), t - prev))
        results.append((tag, "+".join(switches), t))
        prev = t
    log("=== 요약 (무제어 %.1f · f3 %.1f) ===" % (base, ttt_of(BRANCH_BASE_RUN)))
    for tag, s, t in results:
        log("  %-3s %-30s %8.1f  %+8.1f" % (tag, s, t, t - base))
    log("N21X15_CAPDROP_DONE")


if __name__ == "__main__":
    main()
