# VSL 채널 진단 재현 스크립트 — 구속력/이득기전/타이브레이크를 한 번에 실측한다.
"""실행:
    "C:/Users/alsrj/anaconda3/python.exe" scripts/diagnose_vsl_channel_20260801.py [part]

part = binding | gain | tiebreak | fd | all (기본 all)

outputs/vsl_sensitivity_20260801.md 의 모든 수치가 이 스크립트에서 나온다.
plant는 NumSim `freeway_substep`(실제 플랜트)을 직접 돌리고, 타이브레이크는
WuFaithfulFollower._solve_freeway_segment_agents(실제 솔버)를 호출한다.

주의 — gain 표의 `best` 열은 동률이면 메뉴 순서상 가장 낮은 VSL을 표시한다.
`dJ_best`가 0.000e+00이면 "그 VSL이 최적"이 아니라 "그 값 이상이 전부 동률"이라는 뜻이다.
"""
from __future__ import annotations

import copy
import csv
import io
import math
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import test_freeway_zone_followers as T  # noqa: E402
from src.models.metanet import desired_speed_kmh, freeway_substep  # noqa: E402
from src.models.state import ControlAction  # noqa: E402

FD_POINTS = SCRIPTS.parent / "outputs" / "no_control_fd_mfd_20260724_freeway_fd_points.csv"
MENU = [50.0, 60.0, 70.0, 80.0, 90.0, 100.0, 120.0]
# two_branch 삼각형 FD의 nominal 임계밀도 = 차로당 용량 / v_free (6900/4/120).
RHO_CRIT_TB = 6900.0 / 4.0 / 120.0
VARIANTS = {
    "a_current": {},
    "b_tb": dict(vsl_fd_two_branch=True, rho_crit_two_branch=RHO_CRIT_TB),
    "c_tb_capdrop": dict(vsl_fd_two_branch=True, rho_crit_two_branch=RHO_CRIT_TB,
                         capacity_drop_anticipation=True),
    "d_tb_capdrop_phi": dict(vsl_fd_two_branch=True, rho_crit_two_branch=RHO_CRIT_TB,
                             capacity_drop_anticipation=True,
                             capacity_drop_discharge_phi=0.9),
    "e_phi_only": dict(capacity_drop_discharge_phi=0.9),
    "f_capdrop_only": dict(capacity_drop_anticipation=True),
}


def build(tuning=None, **netover):
    cfg, _ = T._build_cfg(tuning or T.SEGVSL_TUNING)
    for key, val in netover.items():
        setattr(cfg.network, key, val)
    return cfg


def rollout_ttt(cfg, rho_profile, vsl_vec, steps):
    """균일/계단 밀도 상태에서 세그먼트별 VSL 벡터로 plant를 steps substep 전진한 TTT."""
    state, demand, _snap, _prev, _cp = T._make_solver_inputs(cfg)
    n_seg = int(cfg.network.freeway_segments_per_link)
    for link in cfg.network.freeway_links:
        state.freeway_density[link] = [float(r) for r in rho_profile]
        state.freeway_speed[link] = [
            desired_speed_kmh(r, cfg.network.v_free, cfg.network.rho_crit,
                              cfg.network.metanet_a_m) for r in rho_profile
        ]
        state.freeway_effective_lanes[link] = [float(cfg.network.freeway_lanes)] * n_seg
        state.mainline_origin_queue[link] = 0.0
    for ramp in cfg.network.ramps:
        state.ramp_queue[ramp] = 0.0
    ctrl = ControlAction.uncontrolled(cfg)
    for link in cfg.network.freeway_links:
        ctrl.vsl[link] = float(vsl_vec[0])
        for i in range(n_seg):
            ctrl.vsl[f"{link}__seg{i}"] = float(vsl_vec[i])
    working = copy.deepcopy(state)
    total = 0.0
    for _ in range(steps):
        ttt, _diag = freeway_substep(working, ctrl, demand, cfg,
                                     include_ramp_queue_ttt=False)
        total += float(ttt)
    return total


def binding_rho(vsl, v_free, rho_crit, a_m):
    if vsl >= v_free:
        return 0.0
    return rho_crit * (a_m * math.log(v_free / vsl)) ** (1.0 / a_m)


def part_binding():
    net = build().network
    print("== [1] VSL 구속 상한 rho_bind (V(rho)=VSL) ==")
    print(f"v_free={net.v_free} rho_crit={net.rho_crit} a={net.metanet_a_m} "
          f"alpha_vsl={net.alpha_vsl}")
    print("VSL | rho_bind | ratio")
    for vsl in MENU + [110.0]:
        rho_b = binding_rho(vsl, net.v_free, net.rho_crit, net.metanet_a_m)
        print(f"{vsl:5.0f} | {rho_b:8.3f} | {rho_b/net.rho_crit:6.3f}")


def part_gain():
    cfg0 = build()
    n_seg = int(cfg0.network.freeway_segments_per_link)
    k_cf = int(cfg0.simulation.T_c_sec / cfg0.simulation.T_f_sec)
    print(f"\n== [2] 이득 기전 격리 (T_f={cfg0.simulation.T_f_sec}s, K_cf={k_cf}) ==")
    for steps in (6, 18, 36):
        print(f"\n#### K={steps} substeps ({steps*cfg0.simulation.T_f_sec:.0f}s)")
        for name, over in VARIANTS.items():
            cfg = build(**over)
            print(f"-- {name}")
            print("rho | " + " | ".join(f"{v:.0f}" for v in MENU)
                  + " | best | dJ_best | rel% | dJ(80) rel%")
            for rho in (12, 16, 20, 24, 28, 32, 36, 45):
                costs = {v: rollout_ttt(cfg, [rho] * n_seg, [v] * n_seg, steps)
                         for v in MENU}
                base = costs[120.0]
                best = min(costs.values())
                best_v = [v for v in MENU if costs[v] <= best + 1.0e-12][0]
                print(f"{rho:3d} | " + " | ".join(f"{costs[v]:.4f}" for v in MENU)
                      + f" | {best_v:.0f} | {best-base:+.3e} | "
                      f"{100*(best-base)/base:+.4f}% | "
                      f"{100*(costs[80.0]-base)/base:+.4f}%")


def _zone_groups():
    return {
        "FW_E": [{"id": "fw_yangjae_E", "segments": [0, 1, 2, 3]},
                 {"id": "fw_seocho_E", "segments": [4, 5, 6, 7]}],
        "FW_W": [{"id": "fw_seocho_W", "segments": [0, 1, 2, 3]},
                 {"id": "fw_yangjae_W", "segments": [4, 5, 6, 7]}],
    }


def _solver_call(tuning, rho, prev_vsl, zone):
    cfg, _ = T._build_cfg(tuning)
    if zone:
        cfg.mpc.freeway_agent_groups = _zone_groups()
    n_seg = int(cfg.network.freeway_segments_per_link)
    state, demand, snapshot, previous, coupling = T._make_solver_inputs(cfg)
    for link in cfg.network.freeway_links:
        state.freeway_density[link] = [float(rho)] * n_seg
        state.freeway_speed[link] = [desired_speed_kmh(
            rho, cfg.network.v_free, cfg.network.rho_crit,
            cfg.network.metanet_a_m)] * n_seg
        state.freeway_effective_lanes[link] = [float(cfg.network.freeway_lanes)] * n_seg
        previous.vsl[link] = float(prev_vsl)
        snapshot.vsl[link] = float(prev_vsl)
        for i in range(n_seg):
            previous.vsl[f"{link}__seg{i}"] = float(prev_vsl)
            snapshot.vsl[f"{link}__seg{i}"] = float(prev_vsl)
    follower = T._make_follower(cfg)
    vsl, _meter, evals = follower._solve_freeway_segment_agents(
        "FW_E", state, coupling, demand, snapshot, None, previous)
    segs = [vsl.get(f"FW_E__seg{i}", vsl.get("FW_E")) for i in range(n_seg)]
    return segs, evals


def part_tiebreak():
    print("\n== [3] spread=0 구간 타이브레이크 (leader 없음, 가격 0) ==")
    for rho in (12, 20, 28, 35, 45):
        for prev in (120.0, 100.0, 80.0):
            flag, e1 = _solver_call(T.SEGVSL_TUNING, rho, prev, zone=False)
            zone, e2 = _solver_call(T.ZONE4_TUNING, rho, prev, zone=True)
            print(f"rho={rho:2d} prev={prev:5.0f} | flagship={flag} (evals={e1})")
            print(f"{'':17s}| zone4   ={zone} (evals={e2})")
    print("\n-- 다단계 래칫 (rho=35 고정, previous=직전 결정) --")
    for tag, tuning, zone in (("flagship", T.SEGVSL_TUNING, False),
                              ("zone4", T.ZONE4_TUNING, True)):
        prev, traj = 120.0, [120.0]
        for _ in range(5):
            segs, _e = _solver_call(tuning, 35.0, prev, zone=zone)
            prev = float(segs[3])
            traj.append(prev)
        print(f"{tag}: seg3 VSL 궤적 = {traj}")


def part_fd():
    print("\n== [4] 내부 FD vs VISSIM 실측 ==")
    if not FD_POINTS.exists():
        print(f"실측 파일 없음: {FD_POINTS}")
        return
    rows = list(csv.DictReader(FD_POINTS.open(encoding="utf-8-sig")))
    speeds = [float(r["mean_speed_kph"]) for r in rows]
    rhos = [float(r["density_veh_km_lane"]) for r in rows]
    net = build().network

    def pct(values, q):
        srt = sorted(values)
        return srt[min(len(srt) - 1, int(q / 100.0 * len(srt)))]

    print(f"n={len(rows)}  speed p50={pct(speeds,50):.1f} p90={pct(speeds,90):.1f} "
          f"max={max(speeds):.1f}")
    for thr in (80.0, 100.0, 120.0):
        frac = sum(1 for s in speeds if s > thr) / len(speeds)
        print(f"  실측 speed > {thr:.0f} 비율 = {frac:.4f}")
    print(f"rho p50={pct(rhos,50):.2f} p90={pct(rhos,90):.2f} max={max(rhos):.2f}")
    for thr in (16.844, 25.844, 30.0):
        frac = sum(1 for r in rhos if r <= thr) / len(rhos)
        print(f"  실측 rho <= {thr:.3f} 비율 = {frac:.4f}")
    print("밀도대 | n | 실측속도 | 모델 V(rho) | 편차")
    for lo, hi in ((0, 5), (5, 10), (10, 15), (15, 20), (20, 25), (25, 30), (30, 40)):
        sel = [s for s, r in zip(speeds, rhos) if lo <= r < hi]
        if not sel:
            continue
        model = desired_speed_kmh((lo + hi) / 2.0, net.v_free, net.rho_crit,
                                  net.metanet_a_m)
        obs = sum(sel) / len(sel)
        print(f"{lo:2d}-{hi:2d} | {len(sel):3d} | {obs:6.1f} | {model:6.1f} | {obs-model:+6.1f}")


def main():
    part = sys.argv[1] if len(sys.argv) > 1 else "all"
    if part in ("binding", "all"):
        part_binding()
    if part in ("gain", "all"):
        part_gain()
    if part in ("tiebreak", "all"):
        part_tiebreak()
    if part in ("fd", "all"):
        part_fd()


if __name__ == "__main__":
    main()
