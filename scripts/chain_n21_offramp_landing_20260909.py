# -*- coding: utf-8 -*-
"""off-ramp spillback 차로폐쇄(λ_eff)를 실제로 발동시키는 팔 — f3 위에서 분기 (2026-09-09).

왜. METANET 에 off-ramp spillback lane closure 가 **이미 구현돼 있고 기본 ON 이다**
(`metanet.effective_lane_profile` + `offramp_spillback_lambda_eff`, 팔로워 복제는
`local_freeway_plant._local_lane_profile`). 식도 문헌 그대로다

    N_eff = N − lane_reduction·(1 − exp[−(1/b)·(n_o /(γ·n_o^max))^b])   lane_reduction=1.0 · γ=0.5 · b=2.0

그런데 **방아쇠가 굶어 있다.** λ_eff 의 점유는 `off_ramp_storage_link` → `OR_*_storage` 저장고
점유인데, 실런 진단이 `local_observation_offramp_storage_occupancy = 0.0` 이고 어댑터 주석이
이유를 적어놨다 — 관측 채널 `off_ramp_storage_veh` 가 39/39 표본 전부 0 이다. 점유가 0 이면
`offramp_spillback_lambda_eff` 가 `capacity_veh <= 0` 에서 nominal 차로를 그대로 돌려주므로
**차로폐쇄가 한 번도 발동하지 않는다.**

실측은 정반대다 (무제어 런, 2026-09-09):
  * FW_E 붕괴는 셀 8 에서 시작해 상류로만 번진다(t=1350 → 7 → 6 → 5). 하류 셀 10·11 은 끝까지 자유류.
  * 합류셀(셀 9)은 1,050 초 늦게 걸린다 — on-ramp 가 원인이 아니다.
  * 붕괴 시점에 **차로 1 만** 죽는다: t=1200 셀8 차로1 = 30대 20.0 km/h 인데 차로3·4 는 126·104 km/h.
    전 차로가 잠기는 건 t=2700 이고 그건 결과다.
  * 셀 8 은 `off_ramp_segment_index` 상 OR_F_E 다이버지이고, 착지 커넥터 10682 는
    **t=600 부터 19~23 대로 포화**한다(본선이 아직 완전 자유류일 때). 하류 도시 회랑은 끝까지 안 막힌다.

즉 물리는 정확히 이 항이 모형화하는 현상인데 모형이 그걸 못 본다.

무엇을 심나. `urban.ramp.landing_storage` 로 착지 **커넥터 재차**를 저장고 점유로 심는다.
용량은 정본 규칙(길이[km] × 차로수 × jam 168.18) 실측이다
(`outputs/offramp_landing_cap_ver2_20260909.json`).

  OR_F_E  커넥터 10682  226.5 m × 1차로 → 38.1 veh   실측 평균 18.8 · 최대 24   포화율 49%
  OR_D_E  커넥터 10483  302.3 m × 1차로 → 50.8 veh   실측 평균  2.7             5%
  OR_D_W  커넥터 10479  258.4 m × 1차로 → 43.5 veh   실측 평균  2.2             5%
  OR_F_W  커넥터 10645  350.4 m × 1차로 → 58.9 veh   실측 평균  3.8             6%

넷 다 넣지만 실제로 발동하는 건 OR_F_E 뿐이다(나머지는 5~6% 라 λ_eff 손실 ≈ 0). 그게 맞다.
예상 효과: 점유 49~63% → 셀 8 에서 0.39~0.55 차로 폐쇄.

이중계상 회피. 옛 B4c 가 기각된 이유는 **도시 접근로**(링크 32 등) 재차를 심어 어댑터 도착 seed 와
겹친 것이었다. 여기서는 **off-ramp 커넥터 자신**만 센다 — 그 차량은 어떤 도시 movement 큐에도,
도착 버퍼에도 없다. `queue_prefix` 를 비워 정지큐 차감도 하지 않는다.

분기 = n21x15f_f3 (7496.6). 기준선 무제어 7403.9 · n2 7346.5.
capdrop(φ=0.85)은 g1 에서 +128.8 로 기각됐으므로 얹지 않는다.

사용: python chain_n21_offramp_landing_20260909.py
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
LOG = R / "evaluation/runs/chain_n21x15_landing_20260909.log"
PROFILE = R / "evaluation/configs/demand_profiles/ver2_fdsweep_x15_20260907.csv"
V0 = "n21_x15_nocontrol_ver2_20260907"
BRANCH = os.environ.get("N21_BRANCH", "n21x15f_f3_spill_rl_meter_mf1_20260909")
METER_TABLE_JSON = R / "outputs/meter_transfer_ver2_20260909.json"
CAP_JSON = R / "outputs/offramp_landing_cap_ver2_20260909.json"
FULL = 37
STALL_SEC = int(os.environ.get("N21_STALL_SEC", "2400"))
# 조각 집합·분기점을 env 로 바꿀 수 있다. 기본은 f3 분기(기존 h1 재현).
BASE_FRAGS = [s for s in os.environ.get("N21_FRAGS", "SPILL,RL,METER,MF1").split(",") if s]
ARM = os.environ.get("N21_ARM", "h1")


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
    base = json.load(io.open(CFG / (BASE_CFG + ".json"), encoding="utf-8"), object_pairs_hook=OD)
    for f in BASE_FRAGS:
        base = deep_merge(base, FRAG[f])
    # Ver2 미터 전달함수는 METER 조각이 있을 때만 의미가 있다(allocation=measured_table 이 그 조각에 있다).
    # 없는데 넣으면 METER 를 뺀 팔에 죽은 키를 심게 되고, 절 자체가 없으면 KeyError 다.
    if "METER" in BASE_FRAGS:
        tbl = json.load(io.open(METER_TABLE_JSON, encoding="utf-8"))["per_lane_veh_per_cycle"]
        sec = base["actuation"]["real_world_ramp_metering"]
        sec["per_lane_veh_per_cycle"] = OD((k, float(v)) for k, v in sorted(tbl.items(), key=lambda x: int(x[0])))
        sec["_note_per_lane_veh_per_cycle"] = "Ver2 재측정 (%s). f3 와 동일." % METER_TABLE_JSON.name

    caps = json.load(io.open(CAP_JSON, encoding="utf-8"))["ramps"]
    landing = OD()
    for ramp in ("OR_F_E", "OR_D_E", "OR_D_W", "OR_F_W"):
        e = caps[ramp]
        landing[ramp] = OD([
            ("links", [str(e["connector"])]),
            # 정지큐 차감 없음 — 커넥터 위 차량은 어떤 도시 movement 큐에도 없다(옛 B4c 이중계상 회피).
            ("queue_prefix", ""),
            ("cap_veh", float(e["cap_veh"])),
            ("share", 1.0),
            ("group", str(e["connector"])),
        ])
    base.setdefault("urban", OD()).setdefault("ramp", OD())["landing_storage"] = landing
    base["urban"]["ramp"]["_note_landing_storage"] = (
        "off-ramp 착지 커넥터 재차를 OR_*_storage 점유로 심는다. 이게 없으면 관측 채널이 39/39 표본 0 이라 "
        "metanet.effective_lane_profile 의 lambda_eff 가 영원히 nominal 차로를 반환하고 "
        "off-ramp spillback 차로폐쇄가 한 번도 발동하지 않는다. 용량은 길이x차로x jam 168.18 실측 "
        "(%s). 실측 포화는 OR_F_E(커넥터 10682, 셀 8) 뿐 49%%, 나머지 셋은 5~6%%." % CAP_JSON.name)
    base["name"] = "n21x15h_%s" % ARM
    base["description"] = ("%s + %s + off-ramp 착지저장고 시드(lambda_eff 발동)"
                           % (BASE_CFG, "+".join(BASE_FRAGS)))
    p = CFG / ("n21h_%s_20260909.json" % ARM)
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
    prev = ttt_of(BRANCH)
    log("=== off-ramp 착지저장고(lambda_eff 발동) · x15 · 무제어 %.1f · 분기 %s = %.1f ===" % (base, BRANCH, prev))
    cfg_path = build_cfg()
    name = "n21x15h_%s_landing_20260909" % ARM
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
    log("RESULT %-3s LANDING(lambda_eff)  [%s]  TTT %8.1f  무제어 %+8.1f (%+.2f%%)  분기 대비 %+8.1f"
        % (ARM, "+".join(BASE_FRAGS), t, t - base, 100 * (t - base) / base, t - prev))
    log("N21X15_LANDING_DONE")


if __name__ == "__main__":
    main()
