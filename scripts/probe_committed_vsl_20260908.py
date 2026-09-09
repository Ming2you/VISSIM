# -*- coding: utf-8 -*-
"""커밋되는 행동에 VSL 이 어떤 키로 실리는지 본다 (2026-09-08).

왜. 플랜트 action CSV writer 는 세그먼트마다 `segment_vsl(control, link, i, cfg)` 를 부른다.
행동이 링크 키만 가지면 표지판 8개가 전부 같은 속도를 받는다 — 실측한 N=8 제어런(b4)의
커밋 행동이 `{'FW_E':120.0,'FW_W':80.0}` 뿐이었다. 반면 팔로워 코드는
`vsl_dict[f"{link}__seg{i}"]` 를 만든다고 문서에 적혀 있다. 어느 쪽이 실제인지 여기서 가린다.

출력: 커밋 vsl 키 목록 + 그 행동으로 `segment_vsl` 을 셀마다 물었을 때의 값
      (= 플랜트가 각 표지판에 쓰게 될 값).

사용: python probe_committed_vsl_20260908.py [config] [run] [T] [workers]
"""
import sys
from pathlib import Path

R = Path("C:/Users/TRLAB/Desktop/찐찐막/VISSIM")


def main():
    sys.path.insert(0, str(R))
    sys.path.insert(0, str(R / "vendor/NumSim-mine"))
    sys.path.insert(0, str(R / "scripts"))
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    import evaluation.controllers.vissim_stackelberg_adapter as qb
    import offline_harness_20260904 as OH
    from src.models.state import TrafficState, segment_vsl
    from src.models.demand import DemandStep

    CFGN = sys.argv[1] if len(sys.argv) > 1 else "canon_ver2n21_dlit_20260908"
    RUN = sys.argv[2] if len(sys.argv) > 2 else "n21_x15_nocontrol_ver2_20260907"
    T = int(sys.argv[3]) if len(sys.argv) > 3 else 900
    W = int(sys.argv[4]) if len(sys.argv) > 4 else 10

    D = R / "evaluation/runs" / RUN / ("decisions_%s" % RUN)
    cfg, st, sj, meta, dm, cal, tun = OH.build(
        qb, TrafficState, str(R / "evaluation/configs" / (CFGN + ".json")),
        str(D / ("state_%06d.json" % T)), str(D / ("action_%06d.json" % (T - 150))))
    fc = qb.demand_from_state(dict(sj), cfg, DemandStep, int(cfg.mpc.horizon_steps), cal, dm)
    c = qb.build_priced_wu_link_controller(cfg, tun)
    c.price_parallel_workers = W
    qb.install_price_worker_bootstrap(c, sj, dm)
    act = c.decide(st, fc, None, cfg)

    v = dict(act.vsl or {})
    heads = getattr(cfg.network, "freeway_vsl_zone_heads", {}) or {}
    print("커밋 vsl 키 %d개" % len(v))
    for lk in cfg.network.freeway_links:
        n = len((getattr(cfg.network, "freeway_vsl_zone_head_of_cell", {}) or {}).get(str(lk))
                or [None] * int(cfg.network.freeway_segments_per_link))
        segs = [round(float(segment_vsl(act, lk, i, cfg)), 1) for i in range(n)]
        seg_keys = sorted(k for k in v if str(k).startswith(str(lk) + "__seg"))
        print("  %-5s 링크키 = %s" % (lk, v.get(lk)))
        print("        구역 머리 %s" % (heads.get(str(lk)) or "(구역 없음)"))
        print("        세그먼트 키 %d개: %s" % (len(seg_keys), seg_keys[:8]))
        print("        플랜트가 쓸 셀별 값: %s" % segs)
        print("        서로 다른 값 %d종" % len(set(segs)))


if __name__ == "__main__":
    main()
