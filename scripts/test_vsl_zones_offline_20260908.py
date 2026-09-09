# -*- coding: utf-8 -*-
"""VSL 구역 패치 검증 (2026-09-08).

무엇을 증명하나
  A. 구역 지도가 config 대로다 — 머리 셀이 **실제 표지판 자리**이고, 셀마다 머리가 맞다.
  B. `segment_vsl` 이 구역 인식이다 — 구역 안 어느 셀을 물어도 머리 값이 나온다.
     (플랜트 action CSV writer 가 세그먼트마다 이 함수를 부르므로, 이게 곧 표지판에 써질 값이다.)
  C. 후보가 구역 상수다 — 어떤 후보도 한 구역 안에서 값이 갈리지 않고, 고정 구역은 vsl_max 다.
  D. 행동 공간이 줄었다 — 자유 변수가 셀 수가 아니라 자유 구역 수다.

사용: python test_vsl_zones_offline_20260908.py [config] [run] [T]
"""
import io
import json
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
    from src.models.state import TrafficState, ControlAction

    CFGN = sys.argv[1] if len(sys.argv) > 1 else "canon_ver2n21_dlit_20260908"
    RUN = sys.argv[2] if len(sys.argv) > 2 else "n21_x15_nocontrol_ver2_20260907"
    T = int(sys.argv[3]) if len(sys.argv) > 3 else 900

    D = R / "evaluation/runs" / RUN / ("decisions_%s" % RUN)
    cfg, st, sj, meta, dm, cal, tun = OH.build(
        qb, TrafficState, str(R / "evaluation/configs" / (CFGN + ".json")),
        str(D / ("state_%06d.json" % T)), str(D / ("action_%06d.json" % (T - 150))))
    net = cfg.network
    ok = True

    print("설치 메타:", {k: v for k, v in meta.items() if k.startswith("fw_vsl_zone")})

    print("\n=== A. 구역 지도 ===")
    mapping = json.load(io.open(R / "evaluation/real_world_modi_control_ver2n21_20260907"
                                / "control_mapping_ver2n21.json", encoding="utf-8"))
    dsd_cells = {}
    for r in mapping["segments"]:
        if r.get("dsds"):
            dsd_cells.setdefault(r["model_link"], set()).add(int(r["model_segment_index"]))
    heads = getattr(net, "freeway_vsl_zone_heads", {})
    head_of = getattr(net, "freeway_vsl_zone_head_of_cell", {})
    zone_of = getattr(net, "freeway_vsl_zone_of_cell", {})
    free = getattr(net, "freeway_vsl_zone_free", None)
    print("   자유 구역 %s" % free)
    for link in net.freeway_links:
        hs = heads.get(str(link), [])
        phys = sorted(dsd_cells.get(link, set()))
        on_sign = all(h in dsd_cells.get(link, set()) for h in hs)
        ok = ok and on_sign
        spans = []
        for z, h in enumerate(hs):
            end = (hs[z + 1] - 1) if z + 1 < len(hs) else len(head_of[str(link)]) - 1
            prof = getattr(net, "freeway_segment_length_profile_km", None) or {}
            arr = prof.get(str(link)) if isinstance(prof, dict) else None
            km = sum(float(x) for x in arr[h:end + 1]) if arr else 0.0
            spans.append("%d:[%d-%d]%s" % (z, h, end, (" %.2fkm" % km) if km else ""))
        print("   %-5s 머리 %s  (물리 표지판 %s)  머리가 전부 표지판 위: %s"
              % (link, hs, phys, "예" if on_sign else "아니오"))
        print("        구역 %s" % "  ".join(spans))

    print("\n=== B. segment_vsl 이 구역 머리 값을 돌려주나 ===")
    from src.models import state as _st
    prev = ControlAction(
        ramp_metering={r: float(net.ramp_capacity_veh_h[r]) for r in net.ramps},
        vsl={}, green_times={}, offsets={}, inflow_outflow_allocation={})
    for link in net.freeway_links:
        hs = heads.get(str(link), [])
        # 각 구역 머리에 서로 다른 값을 심고, 구역 안 모든 셀이 그 값을 읽는지 본다.
        probe = [80.0, 100.0, 120.0, 100.0]
        for z, h in enumerate(hs):
            prev.vsl["%s__seg%d" % (link, h)] = probe[z % len(probe)]
        got = [round(float(_st.segment_vsl(prev, link, i, cfg)), 3) for i in range(len(head_of[str(link)]))]
        want = [probe[int(zone_of[str(link)][i]) % len(probe)] for i in range(len(got))]
        same = got == want
        ok = ok and same
        print("   %-5s %s" % (link, "OK" if same else "불일치"))
        if not same:
            print("      얻음 %s\n      기대 %s" % (got, want))

    print("\n=== C. 후보가 구역 상수인가 ===")
    from src.controllers import wu_faithful_follower as wff

    class Shim:
        pass
    shim = Shim(); shim.cfg = cfg
    prev2 = ControlAction(
        ramp_metering={r: float(net.ramp_capacity_veh_h[r]) for r in net.ramps},
        vsl={lk: float(net.v_free) for lk in net.freeway_links},
        green_times={}, offsets={}, inflow_outflow_allocation={})
    ff = cfg.freeway_follower
    horizon = max(1, ff.freeway_prediction_horizon_steps or cfg.mpc.horizon_steps)
    vmax = max(float(v) for v in ff.vsl_set)
    for link in net.freeway_links:
        n = len(head_of[str(link)])
        cands = wff.WuFaithfulFollower._freeway_vsl_sequence_candidates(
            shim, link, n, prev2, [[float(net.v_free)] * n], horizon)
        bad_zone, bad_pin, distinct = 0, 0, set()
        for seq in cands:
            for vec in seq:
                for i in range(n):
                    if abs(vec[i] - vec[int(head_of[str(link)][i])]) > 1e-9:
                        bad_zone += 1
                    if free is not None and int(zone_of[str(link)][i]) not in free \
                            and abs(vec[i] - vmax) > 1e-9:
                        bad_pin += 1
            distinct.add(tuple(round(v, 3) for v in seq[0]))
        ok = ok and bad_zone == 0 and bad_pin == 0
        print("   %-5s 후보 %d개 · 구역 위반 %d · 고정구역 위반 %d · 첫 스텝 서로 다른 벡터 %d개"
              % (link, len(cands), bad_zone, bad_pin, len(distinct)))

    print("\n=== D. 행동 공간 ===")
    for link in net.freeway_links:
        nfree = sum(1 for z in range(len(heads.get(str(link), []))) if free is None or z in free)
        print("   %-5s 자유 변수 %d개 (구역) · 종전 규칙이면 셀 %d개까지"
              % (link, nfree, len(head_of[str(link)])))

    print("\n판정:", "구역 정합 확인" if ok else "실패 - 확인 필요")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
