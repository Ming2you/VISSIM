# -*- coding: utf-8 -*-
"""VSL 가격 채널의 롤아웃 중복을 실측한다 (2026-09-08).

의심. `_vsl_price_rollouts` 는 세그먼트마다 hi/lo 두 개의 전역 롤아웃을 돌린다 —
21셀이면 2링크 x 21셀 x 2 = **84회**(8셀이면 32회). 그런데 커밋된 행동의 `vsl` 은
링크 키(`FW_W`·`FW_E`)만 갖고(실측), `rollout_endpoint.apply_action_schedule` 은
세그먼트 하나를 건드릴 때

    control.vsl[seg_key] = value
    control.vsl[link]    = min(control.vsl.get(link, value), value)

를 한다. 그리고 `segment_vsl` 은 세그먼트 키가 없으면 링크 키로 떨어진다. 따라서
**값을 내리는 쪽(lo)은 링크 전체를 내린다** — 어느 세그먼트를 지목했든 결과 제어가 같다.
올리는 쪽(hi)은 링크 키가 min 으로 안 바뀌므로 그 세그먼트만 달라지지만, 작동점이 이미
상한(v_free)이면 그것도 무변화라 전부 같아진다.

여기서 재는 것: 태스크 84개의 **실효 VSL 벡터**가 몇 종인지, 그리고 돌아온 TTT 가 몇 종인지.
같은 제어면 롤아웃은 순수 함수라 같은 값이 나온다 — 즉 중복분은 **비트 동치로 제거 가능**하다.

사용: python probe_vsl_price_dupes_20260908.py <config> <run> <T>
"""
import collections
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
    from src.models.state import TrafficState
    from src.models.demand import DemandStep

    CFGN, RUN, T = sys.argv[1], sys.argv[2], int(sys.argv[3])
    D = R / "evaluation/runs" / RUN / ("decisions_%s" % RUN)
    cfg, st, sj, meta, dm, cal, tun = OH.build(
        qb, TrafficState, str(R / "evaluation/configs" / (CFGN + ".json")),
        str(D / ("state_%06d.json" % T)), str(D / ("action_%06d.json" % (T - 150))))
    fc = qb.demand_from_state(dict(sj), cfg, DemandStep, int(cfg.mpc.horizon_steps), cal, dm)
    ctrl = qb.build_priced_wu_link_controller(cfg, tun)
    ctrl.price_parallel_workers = 0          # 직렬 - 태스크와 결과를 그대로 본다

    from src.models.state import segment_vsl
    net = cfg.network
    n_seg = {lk: len(getattr(net, "freeway_segment_lanes", {}).get(lk, [])) or net.freeway_segments
             for lk in net.freeway_links}

    captured = {}
    orig = ctrl._vsl_price_rollouts

    def effective_vector(previous, link, seg_key, value):
        """이 태스크가 만드는 실효 세그먼트 VSL 벡터. apply_action_schedule 규약 그대로."""
        base = dict(previous.vsl or {})
        base[seg_key] = float(value)
        base[link] = min(float(base.get(link, value)), float(value))
        out = []
        for i in range(n_seg[link]):
            k = "%s__seg%d" % (link, i)
            out.append(round(float(base.get(k, base.get(link, 0.0))), 6))
        return (link, tuple(out))

    def wrapped(state, previous, forecast, v_corners, vsl_upper):
        tasks = []
        for key, (_x0, v_lo, v_hi, link, _req) in v_corners.items():
            if float(v_hi) - float(v_lo) <= 1.0e-9:
                continue
            tasks.append((key, "lo", link, float(v_lo)))
            tasks.append((key, "hi", link, float(v_hi)))
        vecs = collections.Counter(effective_vector(previous, lk, k, v) for k, _w, lk, v in tasks)
        captured["corners"] = len(v_corners)
        captured["tasks"] = len(tasks)
        captured["distinct_controls"] = len(vecs)
        captured["prev_link_vsl"] = {lk: float((previous.vsl or {}).get(lk, float("nan")))
                                     for lk in net.freeway_links}
        captured["prev_seg_keys"] = sum(1 for k in (previous.vsl or {}) if "__seg" in str(k))
        out = orig(state, previous, forecast, v_corners, vsl_upper)
        captured["distinct_ttt"] = len({round(float(v), 9) for v in out.values()})
        captured["results"] = len(out)
        return out

    ctrl._vsl_price_rollouts = wrapped
    ctrl.decide(st, fc, None, cfg)

    print("=== VSL 가격 채널 (config %s · %s t=%d) ===" % (CFGN, RUN, T))
    print("  세그먼트 수            %s" % n_seg)
    print("  previous 링크 VSL      %s" % captured.get("prev_link_vsl"))
    print("  previous 세그먼트 키 수 %s   (0 이면 전부 링크 키로 폴백)" % captured.get("prev_seg_keys"))
    print("  코너 %d개 -> 롤아웃 태스크 %d개" % (captured.get("corners", 0), captured.get("tasks", 0)))
    print("  그중 **서로 다른 제어**  %d개" % captured.get("distinct_controls", 0))
    print("  실제로 나온 서로 다른 TTT %d개 (결과 %d개)"
          % (captured.get("distinct_ttt", 0), captured.get("results", 0)))
    t, dc = captured.get("tasks", 0), captured.get("distinct_controls", 0)
    if t:
        print("\n  -> 중복 %d/%d (%.0f%%). 같은 제어면 롤아웃은 순수 함수라 값이 같다 —"
              " 비트 동치로 제거할 수 있다." % (t - dc, t, 100.0 * (t - dc) / t))


if __name__ == "__main__":
    main()
