# -*- coding: utf-8 -*-
"""k-best VSL 시퀀스 생성 검증 (2026-09-08).

무엇을 증명하나
  A. **동치**: 자유 세그먼트가 적어 원본이 돌 수 있는 설정에서, 패치 전/후 후보 목록이 같다.
     (자유 세그먼트 수는 off_ramp_segment_index 를 임시로 낮춰 만든다 - 원본이 k^s 를 실제로
      전개할 수 있는 크기여야 하므로.)
  B. **폭발 제거**: 진짜 21셀 설정(FW_E 자유 8 -> 10^8)에서 패치본이 즉시 끝나고 limit 이내를 낸다.
     원본은 여기서 MemoryError 로 죽는다 - 그래서 원본은 호출하지 않는다.

사용: python test_vsl_kbest_offline_20260908.py
"""
import importlib.util
import io
import json
import os
import sys
import time
from pathlib import Path

R = Path("C:/Users/TRLAB/Desktop/찐찐막/VISSIM")


def main():
    sys.path.insert(0, str(R))
    sys.path.insert(0, str(R / "vendor/NumSim-mine"))
    sys.path.insert(0, str(R / "scripts"))
    sys.path.insert(0, str(R / "evaluation/controllers"))
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    sp = importlib.util.spec_from_file_location("qb", R / "evaluation/controllers/vissim_stackelberg_adapter.py")
    qb = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(qb)
    import offline_harness_20260904 as OH
    from src.models.state import TrafficState
    from src.controllers import wu_faithful_follower as wff

    ORIGINAL = wff.WuFaithfulFollower._freeway_vsl_sequence_candidates
    assert not getattr(ORIGINAL, "_rw_vsl_kbest", False), "원본을 먼저 잡아야 한다"

    RUN = "n21_x15_nocontrol_ver2_20260907"
    D = R / "evaluation/runs" / RUN / ("decisions_%s" % RUN)
    cfg, st, sj, meta, dm, cal, tun = OH.build(
        qb, TrafficState, str(R / "evaluation/configs/canon_ver2n21_dlit_20260908.json"),
        str(D / "state_000900.json"), str(D / "action_000750.json"))
    print("k-best 설치 메타:", {k: v for k, v in meta.items() if k.startswith("fw_vsl_kbest")})
    PATCHED = wff.WuFaithfulFollower._freeway_vsl_sequence_candidates
    assert getattr(PATCHED, "_rw_vsl_kbest", False), "패치가 안 걸렸다"

    net = cfg.network
    ff = cfg.freeway_follower
    horizon = max(1, ff.freeway_prediction_horizon_steps or cfg.mpc.horizon_steps)

    class Shim:
        pass
    shim = Shim()
    shim.cfg = cfg

    from src.models.state import ControlAction
    prev = ControlAction(
        ramp_metering={r: float(net.ramp_capacity_veh_h[r]) for r in net.ramps},
        vsl={lk: float(net.v_free) for lk in net.freeway_links},
        green_times={}, offsets={}, inflow_outflow_allocation={})

    def free_count(link, n_seg, osi):
        bi = {int(osi.get(o, n_seg - 1)) for o in net.off_ramps
              if net.off_ramp_from_freeway.get(o) == link} or {n_seg - 1}
        return max(0, min(bi))

    osi_real = dict(getattr(net, "off_ramp_segment_index", {}) or {})

    print("\n=== A. 동치 (자유 세그먼트를 줄여 원본이 돌 수 있게) ===")
    ok_all = True
    for shrink in (2, 3, 4):
        osi_small = {k: (shrink if net.off_ramp_from_freeway.get(k) else v) for k, v in osi_real.items()}
        # 모든 off-ramp 를 같은 셀로 몰아 min = shrink 가 되게 한다
        osi_small = {k: shrink for k in osi_real}
        net.off_ramp_segment_index = osi_small
        for link in net.freeway_links:
            n_seg = len(getattr(net, "freeway_segment_lanes", {}).get(link, [])) or net.freeway_segments
            base = [[float(net.v_free)] * n_seg]
            t0 = time.time()
            a = ORIGINAL(shim, link, n_seg, prev, base, horizon)
            t1 = time.time()
            b = PATCHED(shim, link, n_seg, prev, base, horizon)
            t2 = time.time()
            same = (a == b)
            ok_all = ok_all and same
            print("   자유=%d %-5s 원본 %2d개 %6.2f s | k-best %2d개 %6.3f s | 동일 %s"
                  % (free_count(link, n_seg, osi_small), link, len(a), t1 - t0, len(b), t2 - t1,
                     "예" if same else "아니오"))
            if not same:
                for i, (x, y) in enumerate(zip(a, b)):
                    if x != y:
                        print("      첫 불일치 idx=%d\n        원본 %s\n        kbest %s" % (i, x, y))
                        break
    net.off_ramp_segment_index = osi_real

    print("\n=== B. 진짜 21셀 설정 (원본은 MemoryError) ===")
    for link in net.freeway_links:
        n_seg = len(getattr(net, "freeway_segment_lanes", {}).get(link, [])) or net.freeway_segments
        fc = free_count(link, n_seg, osi_real)
        base = [[float(net.v_free)] * n_seg]
        t0 = time.time()
        b = PATCHED(shim, link, n_seg, prev, base, horizon)
        dt = time.time() - t0
        print("   %-5s n_seg=%d 자유=%d (원본 조합 10^%d)  ->  k-best %d개 %.3f s  limit=%d"
              % (link, n_seg, fc, fc, len(b), dt, int(ff.vsl_sequence_candidate_limit)))
        assert len(b) <= max(len(base), int(ff.vsl_sequence_candidate_limit)), "limit 초과"
        assert dt < 5.0, "여전히 느리다"

    print("\n판정:", "동치 확인 + 폭발 제거" if ok_all else "동치 실패 - 확인 필요")
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
