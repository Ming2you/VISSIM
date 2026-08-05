# 모델의 forecast ramp_arrival 이 플랜트 실측 온램프 유량과 맞는지 검증한다.
#
# 왜 필요한가.
#   모델 램프 수요는 관측이 아니라 calibration.prediction.local_ramp_arrival_forecast 가
#   `ramp_counts × 3600/queue_drain_horizon_sec` 로 만드는 추정값이다
#   (adapter:1714-1767). 이 환산이 틀리면 모델 세계에서 미터가 수요를 구속하지 않게 되고
#   dTTT/d(meter) 가 정의상 0 이 되어 램프 축 전체가 무의미해진다.
#   2026-08-04 실측에서 모델 1,290 veh/h 대 플랜트 4,496 veh/h (3.5배 과소)가 확인됐다.
#
# 실측 기준은 scripts/measure_ramp_connector_flow.py 의 JSON 산출물이다.
#
# 사용:
#   python scripts/verify_ramp_arrival_calibration.py \
#       --state-json <앵커 state_002700.json> --observed-json outputs/ramp_flow_*.json \
#       --calibration-json <cal> --tuning-json <tun> [--tolerance 0.15]
import argparse
import io
import json
import os
import sys
from pathlib import Path

# 파이프·리다이렉트 시 Windows 기본 stdout 이 cp949 라 한글·기호가 죽는다.
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
NUMSIM = REPO.parent / "NumSim-mine"
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "evaluation" / "controllers"))
sys.path.insert(0, str(NUMSIM))

DIST = REPO / "evaluation" / "real_world_modi_control_distributed_20260728"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--state-json", required=True,
                    help="런타임 조립 기준 state (보통 앵커 t0). --decisions-dir 이 있으면 스텝별로 다시 돈다")
    ap.add_argument("--decisions-dir", default="",
                    help="state_*.json 디렉터리. 주면 시각별로 모델 대 실측을 대조한다(권장)")
    ap.add_argument("--observed-json", required=True)
    ap.add_argument("--calibration-json", required=True)
    ap.add_argument("--tuning-json", required=True)
    ap.add_argument("--mapping-json", default=str(DIST / "control_mapping_distributed_15core_20260728.json"))
    ap.add_argument("--detector-mapping-json",
                    default=str(DIST / "detector_local_mapping_distributed_15core_20260728.json"))
    ap.add_argument("--tolerance", type=float, default=0.15, help="그룹별 상대오차 허용")
    args = ap.parse_args()

    from harness.g6 import g6_core as core

    init = json.loads(Path(args.state_json).read_text(encoding="utf-8"))
    observed = json.loads(Path(args.observed_json).read_text(encoding="utf-8"))
    obs = {str(k): float(v) for k, v in (observed.get("on_ramp_vph_by_group") or {}).items()}
    if not obs:
        print("ERROR: observed-json 에 on_ramp_vph_by_group 이 없다")
        return 2

    rt = core.build_runtime(
        init,
        mapping_json=args.mapping_json,
        detector_mapping_json=args.detector_mapping_json,
        calibration_json=args.calibration_json,
        tuning_json=args.tuning_json,
    )
    series = observed.get("on_ramp_vph_by_group_at_time") or {}
    if args.decisions_dir and series:
        # 시각별 대조 — 모델은 그 시각의 ramp_counts 로 예보하므로 같은 시각의 실측 q 와 견준다.
        import glob as _glob
        import statistics as _st

        per_group = {}
        n_steps = 0
        acc = {}
        for path in sorted(_glob.glob(os.path.join(args.decisions_dir, "state_*.json"))):
            sj = json.loads(Path(path).read_text(encoding="utf-8"))
            t = float(sj.get("sim_sec", -1.0))
            if t < float(observed.get("t0", 0.0)):
                continue
            key = min(series, key=lambda x: abs(float(x) - t))
            if abs(float(key) - t) > 30.0:
                continue
            fc = core.build_forecast(rt, sj, 1)
            n_steps += 1
            for g, mv in fc[0].ramp_arrival.items():
                ov = float(series[key].get(str(g), 0.0))
                if ov > 0.0:
                    acc.setdefault(str(g), []).append((float(mv), ov))
        if not acc:
            print("ERROR: 시각이 맞는 표본이 없다")
            return 2
        model = {g: _st.median([m for m, _ in v]) for g, v in acc.items()}
        obs = {g: _st.median([o for _, o in v]) for g, v in acc.items()}
        per_group = {g: _st.median([(m - o) / o for m, o in v]) for g, v in acc.items()}
        print(f"시각별 대조 — 표본 {n_steps} 스텝")
        print(f"{'그룹':<9}{'상대오차 중앙':>14}")
        for g in sorted(per_group):
            print(f"{g:<9}{per_group[g]*100:>13.1f}%")
        print()
    else:
        forecast = core.build_forecast(rt, init, 3)
        model = {str(k): float(v) for k, v in forecast[0].ramp_arrival.items()}

    print(f"state     = {args.state_json}")
    print(f"observed  = {args.observed_json}")
    print(f"calib     = {os.path.basename(args.calibration_json)}")
    print(f"tuning    = {os.path.basename(args.tuning_json)}")
    print(f"tolerance = +-{args.tolerance*100:.0f}%")
    print()
    print(f"{'그룹':<9}{'모델':>10}{'실측':>10}{'상대오차':>11}  판정")
    fails = []
    for g in sorted(set(model) | set(obs)):
        m = model.get(g, 0.0)
        o = obs.get(g, 0.0)
        if o <= 0.0:
            print(f"{g:<9}{m:>10.0f}{o:>10.0f}{'n/a':>11}  SKIP(실측 0)")
            continue
        rel = (m - o) / o
        ok = abs(rel) <= args.tolerance
        if not ok:
            fails.append(g)
        print(f"{g:<9}{m:>10.0f}{o:>10.0f}{rel*100:>10.1f}%  {'OK' if ok else 'FAIL'}")

    tm, to = sum(model.values()), sum(obs.values())
    rel_tot = (tm - to) / to if to > 0 else 0.0
    tot_ok = abs(rel_tot) <= args.tolerance
    print(f"{'합계':<9}{tm:>10.0f}{to:>10.0f}{rel_tot*100:>10.1f}%  {'OK' if tot_ok else 'FAIL'}")
    if not tot_ok:
        fails.append("합계")

    print()
    if fails:
        print(f"RESULT FAIL  ({len(fails)}건: {fails})")
        return 1
    print("RESULT PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
