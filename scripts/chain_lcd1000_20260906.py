# -*- coding: utf-8 -*-
"""관문형 체인 v5 (B = B3: leg_split + 실측 방향분율 + offramp_direct) (2026-09-05). B 는 목표 구조 — 기각하지 않고 진단한다.

  1 기준(canon_default_20260905)
  2 B(leg_split)
       B ≤ 기준 + GATE  → B 채택(잡음 이내면 목표 구조 우선). 플랫폼 = 정본+B
       B >  기준 + GATE  → **B 진단 정지**: 두 런을 맞댄 재료를 로그에 남기고 종료(사람/Claude 가 B 를 고쳐 재발사)
  3 uni1800(플랫폼 위)      → 기준보다 GATE 이상 좋을 때만 채택
  4 **판단 정지**: cap/λ0 를 쌓을 가치가 있는지 재료(λ_P 활성 비율, 램프 큐/상한, B 채택 여부)를 남기고 종료

GATE = 50 veh·h (무제어 5시드 σ 50.7 ≈ 1σ). 완주(37결정)한 런은 재개 시 건너뛴다.
러너는 PowerShell 로만 띄운다(Vissim COM). 런로그 SIGNAL_MIDBLOCK_COM_SKIPS=0 이면 즉시 중단.
"""
import collections
import csv
import io
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

R = Path(r"C:\Users\TRLAB\Desktop\찐찐막\VISSIM")
CFG = R / "evaluation/configs"
RUNNER = R / "scripts/run_real_world_single_watchdog_distributed_core17legs4b.ps1"
NET = R / "network/real_world_gaepo_modi/modi_eval_userfix_20260814e_fwsweep_x18_rampbn_qc_lcd1000.inpx"
LOG = R / "evaluation/runs/chain_lcd1000_20260906.log"
GATE = 50.0
SEED = 13
FULL = 37
RAMPS = ("R_D_W", "R_D_E", "R_F_W", "R_F_E")
OD = collections.OrderedDict


def log(msg):
    line = "%s  %s" % (time.strftime("%m-%d %H:%M:%S"), msg)
    with io.open(LOG, "a", encoding="utf-8") as f:
        f.write(line + chr(10))
    try:
        print(line, flush=True)
    except UnicodeEncodeError:
        print(line.encode("cp949", "replace").decode("cp949"), flush=True)


def load(name):
    return json.load(io.open(CFG / ("%s.json" % name), encoding="utf-8"), object_pairs_hook=OD)


def deep_merge(dst, src):
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            deep_merge(dst[k], v)
        else:
            dst[k] = json.loads(json.dumps(v), object_pairs_hook=OD)
    return dst


CANON = load("canon_default_20260905")
FRAG = {
    # v4 (2026-09-05 19:2x): B = leg_split + 실측 램프 방향분율 표(B2). 경로결정 표는 D 에서 W/E 가 실측과 뒤집혀 있다.
    # v5 (2026-09-05 19:5x): B = B3 = leg_split + 실측 방향분율 + off-ramp W_out 착지 무신호 꼬리 sink(offramp_direct).
    # v7 (2026-09-06 02:xx): B = B4c v2 = B4b + landing_storage(착지 접근로 점유를 plant 링크 재차에서; 같은 링크의 저장고는 λ_eff 를 총량으로).
    "B": OD([("urban", OD([("ramp", OD([("leg_split", True), ("offramp_direct", True),
                                          ("landing_storage", OD([
                                              ("OR_D_W", OD([("links", ["32"]), ("queue_prefix", "SC1001_W_"), ("cap_veh", 296), ("share", 0.62), ("group", "D32")])),
                                              ("OR_D_E", OD([("links", ["32"]), ("queue_prefix", "SC1001_W_"), ("cap_veh", 179), ("share", 0.38), ("group", "D32")])),
                                              ("OR_F_W", OD([("links", ["70", "71"]), ("queue_prefix", "SC1004_W_"), ("cap_veh", 143), ("share", 0.40), ("group", "F70")])),
                                              ("OR_F_E", OD([("links", ["70", "71"]), ("queue_prefix", "SC1004_W_"), ("cap_veh", 60), ("share", 0.60), ("group", "F70")]))]))])),
                           ("boundary_out", OD([("ramp_split_json", "outputs/boundary_out_ramp_split_20260905_measured.json")]))]))]),
    # v6 (2026-09-05 23:1x): B = B4b = leg_split + 실측 방향분율 + off-ramp 착지 시점 분할(OR_*_W 직행→꼬리, OR_*_E 직행→W_out pool).
    #   B3(무신호 movement 가 저장고 잔여 46% 를 매 substep 인출) 는 9115.0 으로 기각·격리(g2_B3fail).
    # RL = has_ramps 신호(SC1001·SC1004)의 현시가격 국소항을 GNE 와 같은 ramp-aware 물리로(정본은 drain=항등 0 → 꼭짓점 래칫).
    #   t=900 오프라인: 기준 22/23/71/23(p3 꼭짓점) · B4b 21/21/21/75(p4 꼭짓점) · B4b+RL 21/21/51/45(내부해).
    "RL": OD([("phase_price", OD([("ramp_local_model", "ramp_aware")]))]),
    # RS: has_ramps 신호(SC1001·SC1004)의 현시가격 0 — RL 국소(ramp-aware) 채점만으로 정련. 가격이 국소 압력을 덮어 서측 hold-back 을 만들었다.
    "RS": OD([("phase_price", OD([("ramp_signal_price", "off")]))]),
    # P0 = 현시가격 가중 0 (정련은 GNE 국소 채점만). t=2700 전 신호 |ΔG|/G 중앙 0.0005%(평평), 가격 ≈ −0.75·ΔL/δ 라 국소 1차항을 지운다.
    "P0": OD([("phase_price", OD([("weight", 0.0)]))]),
    # B5 = 게이트발 on-ramp 접근 큐(SC1001_W_to_onW/onE·SC1004_W_to_onE 무신호, 저수지 등록, β=실측 peel/게이트, peel-off 차감 off). 미터 폐쇄의 링크 32 비용을 전역 롤아웃에 보이게.
    "B5": OD([("urban", OD([("ramp", OD([("gate_onramp_queue", True)])), ("gate", OD([("ramp_peeloff", False)]))]))]),
    # B0 = B4b (leg_split + offramp_direct + 실측 방향분율), landing_storage 없음 — B4c 는 도착 seed 와 이중계상이라 뺀다.
    "B0": OD([("urban", OD([("ramp", OD([("leg_split", True), ("offramp_direct", True)])),
                            ("boundary_out", OD([("ramp_split_json", "outputs/boundary_out_ramp_split_20260905_measured.json")]))]))]),
    "uni1800": OD([("urban", OD([("capacity", load("arm_c0905_uni1800_20260905")["urban"]["capacity"])]))]),
    "cap": OD([("urban", OD([("ramp", OD([("local_queue_cap", True)]))]))]),
    "lam0": OD([("dual", load("arm_c0905_lam0_20260905")["dual"])]),
}


def make_config(tags):
    name = "h_" + ("_".join(tags) if tags else "base") + "_20260906"
    c = json.loads(json.dumps(CANON), object_pairs_hook=OD)
    for t in tags:
        deep_merge(c, FRAG[t])
    c["_arm_note"] = ("canon_default_20260905 + " + " + ".join(tags)) if tags else "canon_default_20260905 (관문 체인 기준)"
    io.open(CFG / ("%s.json" % name), "w", encoding="utf-8").write(json.dumps(c, ensure_ascii=False, indent=2) + "\n")
    out = subprocess.run([sys.executable, str(R / "scripts/verify_parameters.py"), str(CFG / ("%s.json" % name))],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    last = (out.stdout.strip().splitlines() or ["?"])[-1]
    if "PASS" not in last:
        raise RuntimeError("verify 실패 %s: %s" % (name, last))
    return name


def n_actions(outdir):
    return len(list(outdir.glob("decisions_*/action_*.json")))


def run(name, cfg_name, controller="wu-link"):
    outdir = R / "evaluation/runs" / name
    if n_actions(outdir) >= FULL:
        log("RESUME %s (완주 런 존재, 건너뜀)" % name)
        return ttt_of(name)
    if outdir.exists():
        shutil.rmtree(outdir, ignore_errors=True)
        log("  부분 런 삭제 %s" % name)
    ps = ("& '%s' -Name '%s' -OutDir '%s' -Network '%s' -Tuning '%s' -Controller '%s'%s -SimPeriod 5400 "
          "-ControlIntervalSec 150 -Seed %d -ControlStartSec 900 -WarmupController 'no-control' "
          "-StateLogIntervalSec 30 -DemandScale 1.0") % (RUNNER, name, outdir, NET, CFG / ("%s.json" % cfg_name), controller, (" -ForceStepwise" if controller == "no-control" else ""), SEED)
    log("START %s  config=%s" % (name, cfg_name))
    t0 = time.time()
    with io.open(R / "evaluation/runs" / ("%s.chainlog.txt" % name), "w", encoding="utf-8") as lf:
        rc = subprocess.call(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
                             stdout=lf, stderr=subprocess.STDOUT)
    n = n_actions(outdir)
    log("DONE  %s  exit=%s  %.0f min  결정 %d" % (name, rc, (time.time() - t0) / 60, n))
    rl = list(outdir.glob("runlog_*.txt"))
    if rl:
        t = io.open(rl[0], encoding="utf-8", errors="replace").read()
        m = re.search(r"SIGNAL_MIDBLOCK_COM_SKIPS=(\d+)", t)
        log("  SIGNAL_MIDBLOCK_COM_SKIPS=%s" % (m.group(1) if m else "없음"))
        if controller != "no-control" and m and int(m.group(1)) == 0:
            raise RuntimeError("미드블록 SG 가 COM 으로 넘어갔다(skips=0) — 체인 중단")
    if controller == "no-control":
        n_states = len(list(outdir.glob("decisions_*/state_*.json")))
        log("  무제어 런 state 파일 %d개" % n_states)
        if n_states < FULL:
            raise RuntimeError("%s 무제어 미완주(state %d) — 체인 중단" % (name, n_states))
        return ttt_of(name)
    if n < FULL:
        raise RuntimeError("%s 미완주(결정 %d) — 체인 중단" % (name, n))
    return ttt_of(name)


def ttt_of(name):
    out = subprocess.run([sys.executable, str(R / "scripts/compare_runs_ttt.py"), name, "--base", name],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    for line in out.stdout.splitlines():
        if line.strip().startswith(name):
            m = re.search(r"\s(\d+\.\d+)\s", line)
            if m:
                return float(m.group(1))
    raise RuntimeError("TTT 파싱 실패 %s\n%s" % (name, out.stdout[-400:]))


# ---------------------------------------------------------------- 재료 추출 유틸
def _outdir(name):
    return R / "evaluation/runs" / name


def _state_rows(name):
    f = list(_outdir(name).glob("state_*.csv"))
    return list(csv.DictReader(io.open(f[0], encoding="utf-8", errors="replace"))) if f else []


def _split_ttt(name):
    """state CSV(30 s)로 도시/본선/램프 TTT[veh·h] 적분."""
    rows = _state_rows(name)
    acc = {"urban": 0.0, "freeway": 0.0, "ramp": 0.0}
    prev = None
    for x in rows:
        t = float(x["sim_sec"])
        dt = (t - prev) if prev is not None else 30.0
        prev = t
        if t > 5400:
            break
        for k, col in (("urban", "urban_vehicles"), ("freeway", "freeway_vehicles"), ("ramp", "ramp_vehicles")):
            acc[k] += float(x.get(col) or 0) * dt / 3600.0
    return acc


def _actions(name):
    return sorted(_outdir(name).glob("decisions_*/action_*.json"))


def _states(name):
    return sorted(_outdir(name).glob("decisions_*/state_*.json"))


def _links_at(name, t):
    f = list(_outdir(name).glob("bottleneck_links_*.csv"))
    o = {}
    if not f:
        return o
    for x in csv.DictReader(io.open(f[0], encoding="utf-8", errors="replace")):
        if int(float(x["sim_sec"])) == t:
            o[str(x["link"])] = float(x["count"] or 0)
    return o


def _ramp_series(name):
    per = {r_: [] for r_ in RAMPS}
    for s_ in _states(name):
        j = json.load(io.open(s_, encoding="utf-8"))
        rc = j.get("ramp_counts") or {}
        for r_ in RAMPS:
            if r_ in rc:
                per[r_].append(float(rc[r_]))
    return per


def _greens(name, sig):
    out = {}
    for a in _actions(name):
        t = int(a.name[-11:-5])
        if t < 900:
            continue
        g = json.load(io.open(a, encoding="utf-8")).get("green_times") or {}
        out[t] = "/".join("%.0f" % float(g.get("%s_p%d" % (sig, k), 0)) for k in (1, 2, 3, 4))
    return out


def _meter_series(name):
    per = {r_: [] for r_ in RAMPS}
    for a in _actions(name):
        if int(a.name[-11:-5]) < 900:
            continue
        m = json.load(io.open(a, encoding="utf-8")).get("ramp_metering") or {}
        for r_ in RAMPS:
            if r_ in m:
                per[r_].append(float(m[r_]))
    return per


def _diag_series(name, pattern):
    pat = re.compile(pattern)
    out = collections.defaultdict(list)
    for a in _actions(name):
        d = json.load(io.open(a, encoding="utf-8")).get("diagnostics") or {}
        for k, v in d.items():
            if pat.search(k):
                try:
                    out[k].append(float(v))
                except Exception:
                    pass
    return out


def diagnose_B(base, bname, ttt_base, ttt_B):
    """B 가 기준보다 나쁠 때: 두 런을 맞댄 재료. 결론은 사람/Claude 가."""
    log("=== B 진단 재료 (기준 %.1f · B %.1f · Δ %+.1f) ===" % (ttt_base, ttt_B, ttt_B - ttt_base))
    sb, sB = _split_ttt(base), _split_ttt(bname)
    log("  TTT 분해  도시 %.1f→%.1f (%+.1f) · 본선 %.1f→%.1f (%+.1f) · 램프 %.1f→%.1f (%+.1f)" % (
        sb["urban"], sB["urban"], sB["urban"] - sb["urban"], sb["freeway"], sB["freeway"], sB["freeway"] - sb["freeway"],
        sb["ramp"], sB["ramp"], sB["ramp"] - sb["ramp"]))
    rb, rB = _ramp_series(base), _ramp_series(bname)
    for r_ in RAMPS:
        if rb[r_] and rB[r_]:
            log("  램프 %s 관측 큐  평균 %.1f→%.1f · 최대 %.0f→%.0f" % (r_, sum(rb[r_]) / len(rb[r_]), sum(rB[r_]) / len(rB[r_]), max(rb[r_]), max(rB[r_])))
    mb, mB = _meter_series(base), _meter_series(bname)
    for r_ in RAMPS:
        if mb[r_] and mB[r_]:
            log("  미터 %s  평균 %.0f→%.0f vph · 최소 %.0f→%.0f" % (r_, sum(mb[r_]) / len(mb[r_]), sum(mB[r_]) / len(mB[r_]), min(mb[r_]), min(mB[r_])))
    uB = _diag_series(bname, r"leg_ramp_split_u_on_last|u_on_R_")
    for k, v in sorted(uB.items())[:6]:
        log("  B 진단 %s: 평균 %.1f · 최대 %.1f" % (k, sum(v) / len(v), max(v)))
    injB = _diag_series(bname, r"leg_ramp_split_injected_veh")
    for k, v in injB.items():
        log("  B 주입 누적 %s: 마지막 %.1f veh" % (k, v[-1]))
    for sig in ("SC1001", "SC1004", "SC5"):
        gb, gB = _greens(base, sig), _greens(bname, sig)
        ts = [t for t in (900, 1800, 2700, 3600, 4500) if t in gb and t in gB]
        log("  %s 녹색  " % sig + "  ".join("%d: %s→%s" % (t, gb[t], gB[t]) for t in ts))
    dm = json.load(io.open(CANON["detector_mapping_json"] if Path(CANON["detector_mapping_json"]).is_absolute()
                           else R / CANON["detector_mapping_json"], encoding="utf-8"))
    l2o = dm.get("link_to_origins") or {}

    def origin(L):
        o = l2o.get(L)
        return (o[0] if isinstance(o, list) and o else o) or "-"
    for t in (2700, 4500):
        A, B_ = _links_at(base, t), _links_at(bname, t)
        agg = collections.defaultdict(float)
        for L in set(A) | set(B_):
            d = B_.get(L, 0) - A.get(L, 0)
            o = str(origin(L))
            m = re.search(r"_to_(SC\d+)|^in_(SC\d+)", o)
            agg[(m.group(1) or m.group(2)) if m else "기타"] += d
        top = sorted(agg.items(), key=lambda x: -x[1])[:5]
        log("  t=%d 손실(B−기준) 합 %+.0f · 하류신호별 상위: %s" % (t, sum(agg.values()), " · ".join("%s %+.0f" % kv for kv in top)))
        for L in ("32", "31", "68", "71", "66", "1220014203", "1210014303"):
            if L in A or L in B_:
                log("    링크 %-11s %-16s %5.0f → %5.0f" % (L, origin(L)[:16], A.get(L, 0), B_.get(L, 0)))
    log("  B 진단 정지. 원인 판단 후 B 를 고쳐(B1, B2 …) 다시 걸어라 — 기각 아님.")


def _find_ramp_dicts(obj, path=""):
    out = []
    if isinstance(obj, dict):
        if all(k in obj and isinstance(obj[k], (int, float)) for k in RAMPS):
            out.append((path, {k: float(obj[k]) for k in RAMPS}))
        for k, v in obj.items():
            out.extend(_find_ramp_dicts(v, path + "/" + str(k)))
    return out


def assess(platform, run_name, ttt):
    """cap/λ0 를 쌓을 가치 판단 재료."""
    outdir = _outdir(run_name)
    lam = []
    for a in _actions(run_name):
        d = json.load(io.open(a, encoding="utf-8")).get("diagnostics") or {}
        if "wu_faithful_lambda_P" in d:
            lam.append(float(d["wu_faithful_lambda_P"]))
    nz = sum(1 for v in lam if v > 1e-9)
    log("=== 판단 재료 (플랫폼 %s · 런 %s · TTT %.1f) ===" % ("+".join(platform) or "기준", run_name, ttt))
    if lam:
        log("  λ_P: 결정 %d 중 비영 %d (%.0f%%) · 평균 %.2f · 상한(10) 도달 %d" % (
            len(lam), nz, 100.0 * nz / len(lam), sum(lam) / len(lam), sum(1 for v in lam if v >= 9.99)))
    caps = {}
    try:
        sys.path.insert(0, str(R)); sys.path.insert(0, str(R / "vendor/NumSim-mine")); sys.path.insert(0, str(R / "scripts"))
        import importlib.util
        sp = importlib.util.spec_from_file_location("qb", R / "evaluation/controllers/vissim_stackelberg_adapter.py")
        qb = importlib.util.module_from_spec(sp); sp.loader.exec_module(qb)
        import offline_harness_20260904 as OH
        from src.models.state import TrafficState
        S = _states(run_name); A = _actions(run_name)
        cfg = OH.build(qb, TrafficState, str(CFG / ("g_%s_20260905.json" % ("_".join(platform) if platform else "base"))),
                       str(S[10]), str(A[9]))[0]
        for r_ in RAMPS:
            caps[r_] = float(cfg.network.ramp_queue_cap(r_))
    except Exception as e:
        log("  램프 상한 읽기 실패: %r" % (e,))
    per = _ramp_series(run_name)
    hot = 0
    if caps:
        log("  램프 상한 %s" % {k: round(v, 1) for k, v in caps.items()})
        for r_ in RAMPS:
            q = per[r_]
            if q and caps.get(r_, 0) > 0:
                n80 = sum(1 for v in q if v >= 0.8 * caps[r_]); hot += n80
                log("    %s: 최대 %.1f (%.0f%% of cap) · ≥80%% 결정 %d/%d" % (r_, max(q), 100.0 * max(q) / caps[r_], n80, len(q)))
    else:
        hot = -1
    b_on = "B" in platform
    if lam and nz / max(len(lam), 1) >= 0.2:
        log("  권고 → λ0: 검정 가치 있음 (λ_P 활성 %.0f%%)" % (100.0 * nz / len(lam)))
    elif lam:
        log("  권고 → λ0: 무가치에 가까움 (λ_P 활성 %.0f%%, 팔이 비트 동일에 수렴)" % (100.0 * nz / len(lam)))
    if b_on:
        log("  권고 → cap: 무의미 — 플랫폼에 B 채택(on_ramp movement 없음)")
    elif hot > 0:
        log("  권고 → cap: 검정 가치 있음 (램프 큐 ≥80%% 상한 결정 %d건)" % hot)
    elif hot == 0:
        log("  권고 → cap: 무가치에 가까움 (램프 큐가 상한 근처에 간 적 없음)")
    log("  판단 정지. 다음 런은 판단 후 make_config(플랫폼+[...]) 로 이어라.")


def main():
    log("=== lcd1000 체인 시작 · 망 %s · seed %d · h0 무제어(native) → h1 기준(정본 wu-link, 현시가격 ON) → 진단 ===" % (NET.name, SEED))
    ttt = {}
    ttt["nocontrol"] = run("h0_nocontrol_lcd1000_x18_20260906", make_config([]), controller="no-control")
    log("  TTT 무제어(native, lcd1000) = %.1f" % ttt["nocontrol"])
    ttt["base"] = run("h1_base_lcd1000_x18_20260906", make_config([]))
    log("  TTT 기준(정본 컨트롤러, lcd1000) = %.1f (무제어 대비 %+.1f)" % (ttt["base"], ttt["base"] - ttt["nocontrol"]))
    diagnose_B("h0_nocontrol_lcd1000_x18_20260906", "h1_base_lcd1000_x18_20260906", ttt["nocontrol"], ttt["base"])
    log("=== lcd1000 기준 확보. TTT %s — 환경 판단·B 구조 재검토 후 다음 런 ===" % json.dumps({k: round(v, 1) for k, v in ttt.items()}))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log("ERROR %r" % (e,))
        raise
