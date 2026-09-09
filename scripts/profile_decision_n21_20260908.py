# -*- coding: utf-8 -*-
"""N=21 격자에서 결정 1회의 벽시계 시간과 그 내부 분포를 잰다 (2026-09-08).

왜. 21셀 사다리 0단이 워치독(무진행 300 s)에 죽었다. 결정이 실제로 얼마나 걸리는지,
그리고 그 시간이 어디로 가는지 모르면 임계만 올리는 건 증상 가리기다.

무엇을. 실제 무제어 런 상태를 먹여 `decide()` 를 한 번 돌린다.
  - 벽시계 전체
  - main 프로세스 cProfile 누적 상위 (가격 워커는 자식 프로세스라 풀 호출 하나로 뭉쳐 보인다
    -> 그 항목의 누적시간이 곧 '병렬 가격'의 벽시계, 나머지가 직렬 잔여다)
사용: python profile_decision_n21_20260908.py <config_name> <run> <T> [workers]
"""
import cProfile
import importlib.util
import io
import json
import os
import pstats
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
    CFGN, RUN, T = sys.argv[1], sys.argv[2], int(sys.argv[3])
    WORKERS = int(sys.argv[4]) if len(sys.argv) > 4 else -1

    sp = importlib.util.spec_from_file_location("qb", R / "evaluation/controllers/vissim_stackelberg_adapter.py")
    qb = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(qb)
    import offline_harness_20260904 as OH
    from src.models.state import TrafficState
    from src.models.demand import DemandStep

    D = R / "evaluation/runs" / RUN / ("decisions_%s" % RUN)
    t0 = time.time()
    cfg, st, sj, meta, dm, cal, tun = OH.build(
        qb, TrafficState, str(R / "evaluation/configs" / (CFGN + ".json")),
        str(D / ("state_%06d.json" % T)), str(D / ("action_%06d.json" % (T - 150))))
    print("설치 %.1f s" % (time.time() - t0), flush=True)

    steps = int(cfg.mpc.horizon_steps)
    fc = qb.demand_from_state(dict(sj), cfg, DemandStep, steps, cal, dm)
    ctrl = qb.build_priced_wu_link_controller(cfg, tun)
    if WORKERS >= 0:
        ctrl.price_parallel_workers = WORKERS
    # 실런 main() 은 여기서 워커 부트스트랩을 싣는다(어댑터 12191행). 안 실으면 워커가
    # 패치 대조에 걸려 raise 하고 풀이 깨져 **직렬로 조용히 폴백**한다 - 그러면 병렬 경로를
    # 재는 게 아니라 직렬을 재게 된다(2026-09-08 첫 측정이 그랬다).
    boot = qb.install_price_worker_bootstrap(ctrl, sj, dm)
    print("워커 부트스트랩:", boot, flush=True)

    # 단계별 벽시계. 어느 채널이 지배하는지 cProfile 없이도 보이게 한다.
    STAGE = {}

    def _timed(obj, attr, label):
        fn = getattr(obj, attr, None)
        if fn is None:
            return False
        def wrap(*a, **k):
            t = time.time()
            try:
                return fn(*a, **k)
            finally:
                STAGE[label] = STAGE.get(label, 0.0) + (time.time() - t)
                STAGE[label + "#"] = STAGE.get(label + "#", 0) + 1
        setattr(obj, attr, wrap)
        return True

    for attr, label in (("_maybe_refresh_signal_prices", "가격갱신"),
                        ("_green_price_rollouts", "  가격:green"),
                        ("_vsl_price_rollouts", "  가격:vsl"),
                        ("_meter_price_rollouts", "  가격:meter"),
                        ("_offset_price_rollouts", "  가격:offset"),
                        ("_phase_price_rollouts", "  가격:phase"),
                        ("_price_batch", "  가격:batch"),
                        ("_global_rollout_metrics_with_green", "  가격:green직렬1회")):
        _timed(ctrl, attr, label)
    w = int(getattr(ctrl, "price_parallel_workers", 0) or 0)
    nseg = {k: len(v) for k, v in (getattr(cfg.network, "freeway_segment_lanes", None) or {}).items()}
    print("horizon_steps=%d  가격워커=%d  세그먼트=%s  신호=%d  본선링크=%d"
          % (steps, w, nseg, len(cfg.network.signals), len(cfg.network.freeway_links)), flush=True)

    # NOPROF=1 이면 cProfile 을 끄고 순수 벽시계만 잰다 - 프로파일러 오버헤드(약 2배)가
    # 섞이면 '150 s 안에 드는가' 판정을 못 한다.
    noprof = os.environ.get("NOPROF", "") == "1"
    pr = cProfile.Profile()
    t1 = time.time()
    if not noprof:
        pr.enable()
    ctrl.decide(st, fc, None, cfg)
    if not noprof:
        pr.disable()
    wall = time.time() - t1
    print("\n=== 결정 1회 = %.1f s (워커 %d) ===" % (wall, w), flush=True)

    if noprof:
        print("(NOPROF=1 - cProfile 생략)")
        print("PROFILE_DONE wall=%.1f workers=%d" % (wall, w))
        return
    out = io.StringIO()
    pstats.Stats(pr, stream=out).sort_stats("cumulative").print_stats(45)
    print(out.getvalue()[:14000])
    print("=== 단계별 벽시계 ===")
    for k in sorted(STAGE):
        if k.endswith("#"):
            continue
        print("   %-22s %8.1f s   (%d회)" % (k, STAGE[k], STAGE.get(k + "#", 0)))
    print("   %-22s %8.1f s" % ("직렬재실행 카운트", float(getattr(ctrl, "price_parallel_serial_rerun_count", -1))))
    print("   마지막 병렬 오류:", getattr(ctrl, "price_parallel_last_error", None))

    out2 = io.StringIO()
    pstats.Stats(pr, stream=out2).sort_stats("tottime").print_stats(30)
    print("=== tottime 상위 (직렬 CPU가 실제로 타는 곳) ===")
    print(out2.getvalue()[:9000])
    pr.dump_stats(str(R / "outputs/decision_profile_%s_t%d_w%d.prof" % (CFGN, T, w)))
    print("PROFILE_DONE wall=%.1f workers=%d" % (wall, w))


if __name__ == "__main__":
    main()
