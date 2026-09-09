# -*- coding: utf-8 -*-
"""결정 1회를 **가격 워커를 실제로 띄운 채** 오프라인에서 잰다 (2026-09-08).

왜 필요한가. 실런으로 재면 한 점 얻는 데 25분(수요 스케일링 8분 + warmup + 결정)이 든다.
그런데 종전 오프라인 하네스는 워커가 못 떠서 늘 직렬로 폴백했다 — 원인은 성능이 아니라
**모듈 이름**이다. 어댑터를 `spec_from_file_location("qb", ...)` 로 열면 부트스트랩 페이로드의
`module` 이 "qb" 가 되고, spawn 워커가 그 이름을 import 하지 못해 `EOFError: Ran out of input`
으로 풀이 깨진다. 패키지 경로로 import 하면 워커가 같은 이름을 다시 찾을 수 있다.

사용: python time_decision_parallel_20260908.py <config> <run> <T> [workers...]
      예) python time_decision_parallel_20260908.py canon_ver2n21_dlit_20260908 \\
              n21_x15_nocontrol_ver2_20260907 900 0 10 16
"""
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
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    # 패키지 경로로 import 해야 spawn 워커가 같은 모듈을 다시 찾는다(위 docstring 참조).
    import evaluation.controllers.vissim_stackelberg_adapter as qb
    import offline_harness_20260904 as OH
    from src.models.state import TrafficState
    from src.models.demand import DemandStep

    CFGN, RUN, T = sys.argv[1], sys.argv[2], int(sys.argv[3])
    WS = [int(x) for x in sys.argv[4:]] or [0]

    D = R / "evaluation/runs" / RUN / ("decisions_%s" % RUN)
    cfg, st, sj, meta, dm, cal, tun = OH.build(
        qb, TrafficState, str(R / "evaluation/configs" / (CFGN + ".json")),
        str(D / ("state_%06d.json" % T)), str(D / ("action_%06d.json" % (T - 150))))
    fc = qb.demand_from_state(dict(sj), cfg, DemandStep, int(cfg.mpc.horizon_steps), cal, dm)
    nseg = {k: len(v) for k, v in (getattr(cfg.network, "freeway_segment_lanes", None) or {}).items()}
    print("어댑터 모듈 = %s" % qb.__name__)
    print("세그먼트 %s · horizon %d · 신호 %d · kbest %s"
          % (nseg, int(cfg.mpc.horizon_steps), len(cfg.network.signals),
             meta.get("fw_vsl_kbest_enabled")), flush=True)

    # 프로세스 풀 계측. 채널마다 새 풀을 만들면 워커가 매번 vendor import(0.34 s) +
    # 3 MB .inpx 재파싱(0.66 s)을 한다 - 그게 병렬 효율을 깎는지 여기서 가린다.
    import concurrent.futures as _cf
    _POOL = {"n": 0, "sec": 0.0, "workers": []}
    _OrigPool = _cf.ProcessPoolExecutor

    class _CountedPool(_OrigPool):
        def __init__(self, *a, **k):
            _POOL["n"] += 1
            _POOL["workers"].append(int(k.get("max_workers") or (a[0] if a else 0)))
            self._rw_t0 = time.time()
            super().__init__(*a, **k)

        def __exit__(self, *a):
            out = super().__exit__(*a)
            _POOL["sec"] += time.time() - self._rw_t0
            return out

    _cf.ProcessPoolExecutor = _CountedPool

    rows = []
    ref = None
    for w in WS:
        _POOL.update({"n": 0, "sec": 0.0, "workers": []})
        ctrl = qb.build_priced_wu_link_controller(cfg, tun)
        ctrl.price_parallel_workers = int(w)
        boot = qb.install_price_worker_bootstrap(ctrl, sj, dm)

        # 병렬 상태에서 가격/비가격을 가른다. 직렬 프로파일의 비율을 병렬에 그대로 옮기면
        # 틀린다 - 가격만 병렬화되므로 병렬에서는 비가격 몫이 훨씬 커진다.
        STAGE = {}

        def _timed(obj, attr, label):
            fn = getattr(obj, attr, None)
            if fn is None:
                return
            def wrap(*a, **k):
                t = time.time()
                try:
                    return fn(*a, **k)
                finally:
                    STAGE[label] = STAGE.get(label, 0.0) + (time.time() - t)
                    STAGE["#" + label] = STAGE.get("#" + label, 0) + 1
            setattr(obj, attr, wrap)

        # 주의: 이 래퍼는 로컬 클로저라 컨트롤러를 피클 불가로 만든다 - 워커가 EOFError 로
        # 깨지고 직렬 폴백한다(2026-09-08 사고). 병렬을 잴 때는 끄고, 단계 분해가 필요할 때만 켠다.
        for attr, label in () if os.environ.get("STAGE") != "1" else (("_maybe_refresh_signal_prices", "가격갱신 전체"),
                            ("_green_price_rollouts", "  green"),
                            ("_vsl_price_rollouts", "  vsl"),
                            ("_phase_price_rollouts", "  phase"),
                            ("_price_batch", "  batch(vsl+meter)")):
            _timed(ctrl, attr, label)

        t0 = time.time()
        act = ctrl.decide(st, fc, None, cfg)
        wall = time.time() - t0
        rerun = float(getattr(ctrl, "price_parallel_serial_rerun_count", -1))
        err = getattr(ctrl, "price_parallel_last_error", None)
        sig = json.dumps({
            "meter": {str(k): round(float(v), 6) for k, v in sorted((act.ramp_metering or {}).items())},
            "vsl": {str(k): round(float(v), 6) for k, v in sorted((act.vsl or {}).items())},
            "green": {str(k): round(float(v), 6) for k, v in sorted((act.green_times or {}).items())},
        }, ensure_ascii=False)
        if ref is None:
            ref = sig
        rows.append((w, wall, rerun, err, sig == ref))
        print("  워커 %2d  %7.1f s   직렬재실행 %.0f  기준과 동일 %s  | 풀 %d개 · 풀 안 체류 %.1f s · max_workers %s  %s"
              % (w, wall, rerun, "예" if sig == ref else "아니오",
                 _POOL["n"], _POOL["sec"], _POOL["workers"],
                 ("오류=" + str(err)[:60]) if err else ""), flush=True)

    print("\n=== 요약 (제어 간격 150 s) ===")
    for w, wall, rerun, err, same in rows:
        print("  워커 %2d  %7.1f s  %s%s" % (w, wall, "150 s 이내" if wall <= 150 else "초과",
                                            "" if same else "  <- 행동 불일치!"))


if __name__ == "__main__":
    main()
