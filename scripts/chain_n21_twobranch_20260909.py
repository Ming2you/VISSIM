# -*- coding: utf-8 -*-
"""two-branch FD 팔 — **n7 위에서 분기** (2026-09-09).

왜 n7 인가. n 사다리 전수:

    n0 canon 7433.7 (+29.8) · n1 SPILL 7390.1 (−13.8) · n2 SPILL+RL 7346.5 (−57.4)
    n3 +METER+MF1 7550.3 (+146.4) · n4 +PW25 7469.0 (+65.1) · n5 +B5 7483.8 (+79.9)
    n6 +B0 7429.8 (+25.9) · **n7 +SATV2 7248.5 (−155.4, 직전 −181.3)** · n8 +SAT3 7436.0 (+32.1)

**n7 이 Ver2 최고다.** METER 가 +203.8 을 붙이는 건 맞지만 SATV2 가 −181.3 으로 뒤집는다.
(2026-09-09 오후에 "n2 가 유일한 승자"라고 잘못 판단해 사다리를 f4 에서 끊었는데, 그 사다리의
f7 이 바로 SATV2 의 Ver2 상수판이었다. 그 rung 은 아직 안 돌았다 — 별도 후보로 남긴다.)

무엇을 바꾸나. **키 두 개뿐이다.**

    config_overrides.network.vsl_fd_two_branch   = true
    config_overrides.network.rho_crit_two_branch = 15.16

`rho_max` 는 **건드리지 않는다** — 이미 180.0 이고, 무제어 런 혼잡가지 적합이 낸 중앙값
171.4 와 사실상 같으며 관측 최대 ρ(128.0)보다 충분히 크다.

적합 근거 (`scripts/fit_two_branch_fd_ver2_20260909.py` · `outputs/two_branch_fd_ver2_20260909.json`,
무제어 런 `n21_x15_nocontrol_ver2_20260907` 의 42셀 × 37상태):

    삼각형 nominal ρ_crit_tb = q_cap / v_free   (D-lit 표가 이미 적합한 두 값에서 파생)
      42셀 전부 15.16 ~ 15.56 → 스칼라 15.16 로 충분하다
      (`metanet.py:621` 이 net.rho_crit_two_branch 를 **네트워크 스칼라**로 읽으므로 셀별 불가)
    혼잡가지 q_lane = w(ρ_jam − ρ) 최소자승 → ρ_jam 중앙값 171.4 (유효 적합 15개)

왜 rho_crit(27)을 그대로 쓰면 안 되나. 삼각형 용량 = v_free × ρ_crit 이라 27 이면
3240 veh/h/lane = 4차로 12,960 으로 **기존 6937 의 1.87배**가 된다. 적합값 15.16 이면
1820/lane = 7278 = **+4.9%** 로 정합한다(vendor docstring 이 경고한 그 함정).

기대 기구 — VSL 이 임계밀도를 옮긴다 (지금은 `effective_rho_crit` 이 고정 27 을 반환):

    ρ_c(vsl) = w·ρ_jam/(vsl+w),  w = v_free·ρ_crit_tb/(ρ_jam − ρ_crit_tb) = 11.04 (ρ_jam 180)
      vsl 120 → ρ_c 15.16 (앵커)   vsl 100 → 17.9   vsl 80 → 21.8

현재 `vsl_set = [80, 100, 120]` 이 단일가지에서는 **용량 권한이 정확히 0** 이었다
(FW_E 전 셀의 V(ρ_crit)=52~73 < 80). two-branch 에서는 vsl 80 이 임계밀도를 +44% 올린다 —
문헌이 말하는 breakdown 회피 기구가 처음으로 생긴다.

capacity_drop_discharge_phi 는 **얹지 않는다.** g1 에서 단독으로 켜 +128.8 로 졌고, 회피 수단
(=이 팔)이 먼저 서야 짝이 맞는다. 다음 rung 후보다.

사용: python chain_n21_twobranch_20260909.py
"""
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

CFG = R / "evaluation/configs"
BASE_CFG = CFG / "n21_n7_20260908.json"          # n7 을 그대로 받는다(조각 재구성 없음)
FIT_JSON = R / "outputs/two_branch_fd_ver2_20260909.json"
RUNNER = R / "scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1"
NET = R / "network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx"
D21 = R / "evaluation/real_world_modi_control_ver2n21_20260907"
MAPPING = D21 / "control_mapping_ver2n21.json"
VBSCFG = D21 / "real_world_modi_control_config_ver2n21.vbs"
GATEMAP = R / "evaluation/real_world_modi_inventory/urban_input_gate_map_ver2_20260907.csv"
LOG = R / "evaluation/runs/chain_n21x15_twobranch_20260909.log"
PROFILE = R / "evaluation/configs/demand_profiles/ver2_fdsweep_x15_20260907.csv"
V0 = "n21_x15_nocontrol_ver2_20260907"
BRANCH = "n21x15_n7_spill_rl_meter_mf1_pw25_b5_b0_satv2_20260908"
SEED = 13
FULL = 37
STALL_SEC = int(os.environ.get("N21_STALL_SEC", "2400"))
ARM = os.environ.get("N21_ARM", "i1")


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


def build_cfg():
    base = json.load(io.open(BASE_CFG, encoding="utf-8"), object_pairs_hook=OD)
    fit = json.load(io.open(FIT_JSON, encoding="utf-8"))["scalars"]
    # **`config_overrides.network` 에 넣으면 안 된다.** 두 키 모두 NetworkConfig 필드가 아니라
    # vendor 가 getattr 로만 읽는 런타임 속성이다 — 넣으면 NetworkConfig(**raw) 언팩에서
    # TypeError 로 첫 결정에서 죽는다(2026-09-09 확인). 어댑터 `install_freeway_two_branch_fd`
    # 가 이 `freeway.two_branch` 절을 읽어 cfg.network 에 심는다.
    base.setdefault("freeway", OD())["two_branch"] = OD([
        ("enabled", True),
        ("rho_crit_two_branch", float(fit["rho_crit_two_branch"])),
        # rho_max 는 두지 않는다 — 이미 180.0 이고 적합 중앙값 171.4 와 사실상 같다.
    ])
    base.setdefault("_notes", OD())["two_branch_fd"] = (
        "vsl_fd_two_branch 를 켜면 effective_rho_crit 이 고정 rho_crit(27) 대신 rho_c(VSL) 을 낸다 "
        "— VSL 이 임계밀도를 옮기는 문헌 기구. rho_crit_two_branch 는 삼각형 nominal 이고 "
        "q_cap/v_free 로 유도했다(42셀 전부 15.16~15.56). rho_crit 27 을 그대로 쓰면 삼각형 용량이 "
        "4차로 12,960 = 기존 6937 의 1.87배로 뻥튀기된다. rho_max 는 이미 180.0 이라 두지 않는다 "
        "(무제어 혼잡가지 적합 중앙값 171.4, 관측 최대 128.0). 근거 %s" % FIT_JSON.name)
    base["name"] = "n21x15i_%s" % ARM
    base["description"] = "n7 + two-branch FD (VSL 이 임계밀도를 옮긴다)"
    p = CFG / ("n21i_%s_20260909.json" % ARM)
    io.open(p, "w", encoding="utf-8").write(json.dumps(base, ensure_ascii=False, indent=1))
    return p


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
        raise RuntimeError("미드블록 SG 가 COM 으로 넘어갔다 — 중단 (%s)" % name)
    if bad and int(bad.group(1)) > 0:
        raise RuntimeError("결정 %s건 미적용 — 중단 (%s)" % (bad.group(1), name))


def main():
    base = ttt_of(V0)
    try:
        prev = ttt_of(BRANCH)
    except Exception as exc:
        log("분기 런 TTT 를 못 읽었다(%s) — 무제어만 기준으로 간다: %s" % (BRANCH, exc))
        prev = float("nan")
    log("=== two-branch FD · x15 · 무제어 %.1f · 분기 n7 = %.1f ===" % (base, prev))
    cfg_path = build_cfg()
    name = "n21x15i_%s_twobranch_20260909" % ARM
    outdir = R / "evaluation/runs" / name
    if outdir.exists() and len(list(outdir.glob("decisions_*/action_*.json"))) < FULL:
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
    t = ttt_of(name)
    log("RESULT %-3s TWO-BRANCH FD   TTT %8.1f  무제어 %+8.1f (%+.2f%%)  n7 대비 %+8.1f"
        % (ARM, t, t - base, 100 * (t - base) / base, t - prev))
    log("N21X15_TWOBRANCH_DONE")


if __name__ == "__main__":
    main()
