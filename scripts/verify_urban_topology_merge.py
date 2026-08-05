# 도시부 토폴로지 병합 검증 — 관측이 실제로 모델에 도달하는가.
#
# 배경. 플랜트·매핑·관측은 모두 SC 이름공간(SC1001_E_out ...)인데 모델만 default.yaml 의
# 6노드 격자(A_to_B, C_top_out ...)였다. detector 매핑의 origin 64개 중 60개가 모델 저류링크로
# 번역되지 않아, observable_links 를 22 -> 175 로 넓혀도 투영 도시부가 83.5 대에서 소수점까지
# 그대로였다. 그 결과 J_vissim 이 사실상 고속도로 전용이 되어 도시부로 차를 미는 레버가
# 전부 반대 부호로 채점됐다.
#
# 이 스크립트가 보는 것.
#   1) 투영 도시부 대수와 포착률 (플랜트 실측 대비)
#   2) movement 큐 / 링크 저류 각각 몇 개가 살아 있는가
#   3) 유령 저류링크(구 격자 잔존)가 남아 있는가 — config 병합이 dict 를 합치기 때문
#   4) 램프 큐가 어디에 계상되는가 (freeway 쪽 total_freeway_vehicles 에 들어간다)
#   5) 리더 목적함수 항이 정상 범위인가
#
# 사용:
#   python scripts/verify_urban_topology_merge.py --state-json <앵커 state> \
#       --case "라벨:튜닝.json:control_mapping.json:detector_mapping.json" [--case ...]
import argparse
import io
import json
import os
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
NUMSIM = REPO.parent / "NumSim-mine"
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "evaluation" / "controllers"))
sys.path.insert(0, str(NUMSIM))

DIST = REPO / "evaluation" / "real_world_modi_control_distributed_20260728"
CFG = REPO / "evaluation" / "configs"
DEFAULT_CAL = REPO / "evaluation" / "calibration" / "real_world_modi_control_v4_newdemand_20260804.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--state-json", required=True)
    ap.add_argument("--case", action="append", required=True,
                    help="라벨:튜닝파일명:control_mapping파일명:detector_mapping파일명")
    ap.add_argument("--calibration-json", default=str(DEFAULT_CAL))
    ap.add_argument("--min-capture", type=float, default=0.25,
                    help="포착률 하한. 이 아래면 FAIL")
    ap.add_argument("--link-assignment-json", default="",
                    help="주면 분모를 (urban - 출구 링크 위 차량) 으로 잡는다 = 귀속 기준 포착률")
    args = ap.parse_args()

    from harness.g6 import g6_core as core

    init = json.loads(Path(args.state_json).read_text(encoding="utf-8"))
    plant_urban = float(init.get("urban_vehicles", 0.0))
    plant_freeway = float(init.get("freeway_vehicles", 0.0))
    lc = (init.get("local_observation") or {}).get("link_counts") or {}
    print(f"state       = {args.state_json}")
    print(f"플랜트 실측  urban {plant_urban:.0f}  freeway {plant_freeway:.0f}")
    print(f"관측        link_counts {len(lc)}개 / 합 {sum(float(v) for v in lc.values()):.0f}")

    # 분모 = 귀속 가능한 차량 (사용자 확정 2026-08-05).
    #   출구 링크(하류에 아무것도 없이 종단)는 어느 플레이어에도 귀속하지 않기로 했으므로
    #   포착률 분모에서도 뺀다. 고속도로행 링크는 freeway follower 몫이라 빼지 않는다.
    exit_veh = 0.0
    if args.link_assignment_json:
        asg = json.loads(Path(args.link_assignment_json).read_text(encoding="utf-8"))
        exits = {str(v) for v in (asg.get("monitor_only_exit_links") or [])}
        exit_veh = sum(float(v) for k, v in lc.items() if str(k) in exits)
        n_seen = sum(1 for k in lc if str(k) in exits)
        print(f"출구 제외    링크 {n_seen}/{len(exits)}개 관측, 차량 {exit_veh:.0f} 대를 분모에서 뺀다")
        if n_seen == 0 and exits:
            print("   경고 — 출구 링크가 하나도 관측되지 않았다. 허용목록이 좁으면 분모가 과대평가된다.")
    denom = max(1.0, plant_urban - exit_veh)
    print(f"분모(귀속기준) {denom:.0f} 대")
    print()

    fails = []
    for spec in args.case:
        parts = spec.split(":")
        if len(parts) != 4:
            print(f"SKIP 형식 오류: {spec}")
            continue
        label, tun, mp, det = parts
        rt = core.build_runtime(
            init, mapping_json=DIST / mp, detector_mapping_json=DIST / det,
            calibration_json=args.calibration_json, tuning_json=CFG / tun,
        )
        net = rt.score_cfg.network
        st = core.project_observed_state(rt, init)

        # **리더가 실제로 쓰는 기준**으로 잰다.
        #
        # 2026-08-05: 여기서 exclude_boundary_legs=False 를 하드코딩하고 있었는데,
        # leader._state_accumulation_base(leader.py:767)는
        # cfg.leader.state_accumulation_exclude_boundary_legs(기본 True)를 쓴다.
        # 그래서 보고된 포착률 45.9 % 가 목적함수가 쓰는 값이 아니었다(실제 20.2 %).
        # 두 값을 다 찍어 다시 어긋나지 않게 한다.
        exclude = bool(getattr(rt.score_cfg.leader, "state_accumulation_exclude_boundary_legs", True))
        urban = float(st.objective_urban_vehicles(net, exclude))
        urban_incl = float(st.objective_urban_vehicles(net, False))
        boundary_leg = float(st.boundary_leg_vehicles(net))
        freeway = float(st.total_freeway_vehicles(net))
        seg = float(st.freeway_segment_vehicles(net))
        ramp_q = sum(float(v) for v in st.ramp_queue.values())
        mq = st.urban_movement_queue
        nz_mq = sum(1 for v in mq.values() if float(v) > 1e-9)
        cap = net.urban_link_storage_veh
        occ = {l: max(0.0, c - float(st.urban_link_storage.get(l, c))) for l, c in cap.items()}
        nz_st = sum(1 for v in occ.values() if v > 1e-9)
        zero_cap = [l for l, c in cap.items() if float(c) <= 1e-9]
        capture = urban / denom

        print(f"########## {label}")
        print(f"   투영 도시부        {urban:9.1f}   포착률 {100*capture:5.1f}%   (분모 {denom:.0f})"
              f"   [목적함수 기준, exclude_boundary_legs={exclude}]")
        print(f"     참고 — boundary leg 포함시 {urban_incl:.1f} ({100*urban_incl/denom:.1f}%),"
              f"  leg 분 {boundary_leg:.1f}")
        print(f"     movement 큐      {sum(float(v) for v in mq.values()):9.1f}   비영 {nz_mq}/{len(mq)}")
        print(f"     링크 저류 점유    {sum(occ.values()):9.1f}   비영 {nz_st}/{len(cap)}")
        # 고속도로 포착률 — 도시부와 **의미가 다르다**.
        #   도시부: 관측 링크가 모델 저류에 붙었는가(붙이는 매핑이 불완전하면 샌다).
        #   고속도로: 세그먼트 관측 count -> density(=count/(길이x차로)) -> 다시 count 로
        #     왕복한다(adapter:1857, 884). 체인이 고속도로 링크를 전부 덮으므로 보통 100%이고,
        #     100% 에서 벗어나면 관측 누락이 아니라 **길이·차로 프로파일 불일치**를 뜻한다.
        fw_capture = freeway / plant_freeway if plant_freeway > 0 else 0.0
        print(f"   투영 고속도로      {freeway:9.1f}   포착률 {100*fw_capture:5.1f}%   (플랜트 {plant_freeway:.0f})")
        # total_freeway_vehicles 는 세그먼트 합이다. 램프 큐는 여기 안 들어가고
        # 플랜트에서도 urban/freeway 와 별개인 ramp 버킷이라 따로 찍는다.
        # (예전 표기 "세그먼트 + 램프큐 + origin" 은 잔차를 origin 으로 오인하게 했다.)
        print(f"     세그먼트 {seg:.1f}  (잔차 {freeway-seg:+.1f})   램프 큐 {ramp_q:.1f} — 별도 버킷")
        if plant_freeway > 0 and abs(fw_capture - 1.0) > 0.02:
            fails.append(f"{label}: 고속도로 포착률 {100*fw_capture:.1f}% — 길이·차로 프로파일 불일치 의심")
        print(f"   저류링크 총 {len(cap)}개 중 용량 0 = {len(zero_cap)}개 (무력화된 유령)")
        print(f"   유효 저류 용량     {sum(float(c) for c in cap.values()):9.1f}")

        terms = core.objective_from_states(rt, [st], None)
        print(f"   J(1스텝)          {terms['g6_objective']:9.1f}   base {terms['leader_objective_base']:.1f}"
              f"   벌점 {terms['g6_objective']-terms['leader_objective_base']:.1f}")

        if capture < args.min_capture:
            fails.append(f"{label}: 포착률 {100*capture:.1f}% < {100*args.min_capture:.0f}%")
        live_cap = [l for l, c in cap.items() if float(c) > 1e-9]
        dead = [l for l in live_cap if occ[l] <= 1e-9]
        if dead:
            print(f"   경고 — 용량>0 인데 점유 0 인 저류링크 {len(dead)}개: {sorted(dead)[:6]}")
        print()

    if fails:
        print("RESULT FAIL")
        for f in fails:
            print("  ", f)
        return 1
    print("RESULT PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
