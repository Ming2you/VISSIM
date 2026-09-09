# -*- coding: utf-8 -*-
"""세그먼트별 파라미터 패치 오프라인 검증 (2026-09-07).

무엇을 증명하나
  A. 패치 전: 롤아웃 차로 프로파일이 [freeway_lanes]*8 (기하 무시) — 오전 패치의 한계 재현.
  B. 패치 후: 프로파일이 기하 [4,4,4,4,4,3,3,3] / [3,3,3,4,4,4,4,4], off-ramp/incident 감소분은 보존.
  C. segment_params 를 실으면 세그먼트마다 다른 v_free/rho_crit/a 가 실제 속도 갱신에 반영된다.
  D. config 키가 없으면 비트 동일(회귀 없음).
사용: python test_segparams_offline_20260907.py <adapter_path> <config_name> <mapping_json> <run> <T> [params_json]
"""
import importlib.util
import io
import json
import sys
from pathlib import Path


def main():
    R = Path("C:/Users/TRLAB/Desktop/찐찐막/VISSIM")
    sys.path.insert(0, str(R))
    sys.path.insert(0, str(R / "vendor/NumSim-mine"))
    sys.path.insert(0, str(R / "scripts"))
    sys.path.insert(0, str(R / "evaluation/controllers"))
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ADAPTER, CFGN, MAPJ, RUN, T = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5])
    PARAMS = sys.argv[6] if len(sys.argv) > 6 else None

    sp = importlib.util.spec_from_file_location("qb", ADAPTER)
    qb = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(qb)
    import offline_harness_20260904 as OH
    import src.models.metanet as mn
    from src.models.state import TrafficState

    D = R / "evaluation/runs" / RUN / ("decisions_%s" % RUN)
    cfg, st, sj, meta, dm, cal, tun = OH.build(
        qb, TrafficState, str(R / "evaluation/configs" / (CFGN + ".json")),
        str(D / ("state_%06d.json" % T)), str(D / ("action_%06d.json" % (T - 150))))
    mapping = json.load(io.open(R / MAPJ, encoding="utf-8"))

    print("=== A. 패치 전 롤아웃 차로 프로파일 (vendor 원본) ===")
    prof0, _ = mn.effective_lane_profile(st, cfg, None)
    for link, lanes in sorted(prof0.items()):
        print("   %-6s %s" % (link, [round(x, 3) for x in lanes]))
    print("   cfg.network.freeway_lanes = %s  (링크 공용 스칼라)" % cfg.network.freeway_lanes)

    print("\n=== B. 값 적재 + 런타임 패치 ===")
    tun2 = json.loads(json.dumps(tun))
    tun2.setdefault("freeway", {})["segment_lanes"] = "mapping"
    if PARAMS:
        tun2["freeway"]["segment_params"] = PARAMS
    m1 = qb.install_freeway_segment_lanes(cfg, tun2, mapping)
    m2 = qb.install_freeway_segment_runtime(cfg)
    print("   적재:", {k: v for k, v in m1.items() if "lanes" in k or "enabled" in k})
    print("   패치:", m2)
    prof1, diag1 = mn.effective_lane_profile(st, cfg, None)
    ok_geo = True
    want = {k: [float(x) for x in v] for k, v in (getattr(cfg.network, "freeway_segment_lanes", None) or {}).items()}
    for link, lanes in sorted(prof1.items()):
        got = [round(x, 3) for x in lanes]
        exp = want.get(link)
        mark = "OK" if exp and got == [round(x, 3) for x in exp] else "감소분 적용됨/불일치"
        if exp and got != [round(x, 3) for x in exp]:
            ok_geo = False
        print("   %-6s %s   기대 %s  → %s" % (link, got, exp, mark))

    if PARAMS:
        print("\n=== C. 세그먼트별 파라미터가 속도식에 실제로 들어가나 ===")
        tbl = getattr(cfg.network, "freeway_segment_params", None) or {}
        for link in sorted(tbl):
            print("   %s:" % link)
            for i, row in enumerate(tbl[link]):
                if not row:
                    print("     S%d  (비어 있음 → 링크 스칼라)" % i)
                    continue
                vsl = mn.segment_vsl(None, link, i, cfg) if False else None
                # 문맥 무장은 segment_vsl 이 한다. 여기서는 직접 무장해 v_eff 를 비교한다.
                qb._FW_SEG_CTX["p"] = row
                qb._FW_SEG_CTX["armed"] = True
                v_seg = mn.effective_desired_speed_kmh(20.0, cfg.network.v_free, cfg.network.rho_crit,
                                                       120.0, cfg.network.alpha_vsl, False,
                                                       cfg.network.metanet_a_m, False, cfg.network.rho_max, 0.0)
                qb._FW_SEG_CTX["armed"] = False
                v_lnk = mn.effective_desired_speed_kmh(20.0, cfg.network.v_free, cfg.network.rho_crit,
                                                       120.0, cfg.network.alpha_vsl, False,
                                                       cfg.network.metanet_a_m, False, cfg.network.rho_max, 0.0)
                print("     S%d  v_free %6.1f  rho_crit %5.1f  a %.2f  →  V(k=20) 세그먼트 %6.2f vs 링크 %6.2f  (차 %+6.2f)"
                      % (i, row.get("v_free", float("nan")), row.get("rho_crit", float("nan")),
                         row.get("metanet_a_m", float("nan")), v_seg, v_lnk, v_seg - v_lnk))

        print("\n=== C2. 문맥 해제 확인 (완충 셀 퇴화) ===")
        qb._FW_SEG_CTX["p"] = tbl[sorted(tbl)[0]][0]
        qb._FW_SEG_CTX["armed"] = True
        mn.metanet_speed_update_kmh(80.0, 80.0, 20.0, 20.0, 100.0, 0.001, 1.35,
                                    cfg.network.metanet_tau_h, 48.0, 25.0, cfg.network.v_min)
        print("   metanet_speed_update_kmh 호출 뒤 armed =", qb._FW_SEG_CTX["armed"], "(False 여야 한다)")

    print("\n=== D. 롤아웃 한 스텝 — 세그먼트별 파라미터 유무 비교 ===")
    import copy
    from src.models.demand import DemandStep
    from src.models.state import ControlAction
    ctl = ControlAction.uncontrolled(cfg)
    for tag, table in (("세그먼트 파라미터 OFF", {}), ("세그먼트 파라미터 ON", getattr(cfg.network, "freeway_segment_params", {}))):
        st2 = copy.deepcopy(st)
        cfg2 = copy.deepcopy(cfg)
        setattr(cfg2.network, "freeway_segment_params", table)
        d = DemandStep(freeway_mainline={}, urban_boundary={}, ramp_arrival={})
        try:
            ttt, diag = mn.freeway_substep(st2, ctl, d, cfg2)
        except Exception as exc:
            print("   %s: 롤아웃 예외 %s" % (tag, exc))
            continue
        for link in sorted(st2.freeway_speed):
            print("   %-22s %-6s 속도 %s" % (tag, link, [round(x, 1) for x in st2.freeway_speed[link]]))
            print("   %-22s %-6s 차로 %s" % ("", link, [round(x, 2) for x in st2.freeway_effective_lanes[link]]))

    print("\n판정: 기하 프로파일 %s" % ("PASS" if ok_geo else "확인 필요"))


if __name__ == "__main__":
    main()
