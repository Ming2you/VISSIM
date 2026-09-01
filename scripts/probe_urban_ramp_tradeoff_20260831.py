# -*- coding: utf-8 -*-
"""도시 agent 가 램프 미터링의 대가를 실제로 보는가 — 실런 상태에서 재현해 잰다.

왜 (2026-08-31).

수정을 세 번 넣었는데 매번 같은 모양으로 진다.

    망      수정        freeway    urban       합
    x1.0   mergefix     -4.3     +32.1    +27.7
    x1.0   mergedyn     -2.5      +7.4     +4.5
    x1.8   mergefix     -4.8     +18.4     +9.6

고속도로는 조금 좋아지고 도시부가 그보다 많이 나빠진다. 가설은 "그 상충이 GNE 안에서
저울질되지 않는다" 인데, 지금까지 근거가 결과의 모양뿐이었다. 직접 잰다.

설계상으로는 통로가 있다. `_frozen_reservoir_drain` 주석:

    "국소 rollout이 reservoir 유출을 0으로 동결하면 w_r이 ramp_queue_max에 고정돼 on_ramp
     green이 무력해진다(잘못된 flat 비용). 따라서 freeway 본선 ρ로 결정되는 이 방출률을
     동결 결합값으로 받아 substep마다 reservoir를 비운다(green→reservoir 적재 vs
     freeway→reservoir 배출의 상충이 보이게)."

즉 미터링이 바뀌면 -> `compute_ramp_release_flows` 가 바뀌고 -> `reservoir_drain` 이 바뀌고
-> 램프를 먹이는 도시 신호의 국소 비용이 바뀌어야 한다. 그 사슬을 한 마디씩 잰다.

무엇을 재는가 (실런 상태 그대로, VISSIM 재실행 없음).

    1) 미터링 -> reservoir_drain      반응하는가. 안 하면 사슬이 여기서 끊긴 것이다.
    2) 미터링 -> 도시 agent 목적값     램프를 먹이는 신호의 국소 비용이 움직이는가.
    3) 미터링 -> 도시 agent 선택 green 실제로 다른 답을 내는가. 이것이 저울질의 정의다.

램프를 먹이는 신호는 config 의 ramp 소유 관계로 고른다. 대조로 램프와 무관한 신호도 같이
재서, 반응이 있다면 그것이 램프 경로 때문인지 전역 잡음인지 가른다.

산출: outputs/urban_ramp_tradeoff_20260831.json
"""
import argparse
import glob
import importlib.util
import json
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R))
sys.path.insert(0, str(R / "vendor/NumSim-mine"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="canon_mergefix_x18_20260831")
    ap.add_argument("--tuning", default="evaluation/configs/canon_mergefix_x18_20260830.json")
    ap.add_argument("--decisions", type=int, default=5, help="표본으로 쓸 결정 수")
    ap.add_argument("--out", default="outputs/urban_ramp_tradeoff_20260831.json")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    sp = importlib.util.spec_from_file_location(
        "qb", R / "evaluation/controllers/vissim_stackelberg_adapter.py")
    qb = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(qb)
    from src.models.state import ControlAction, TrafficState
    from src.models.demand import DemandStep
    from src.models.metanet import compute_ramp_release_flows

    tun = qb.load_optional_json(str(R / args.tuning))
    cal = qb.load_optional_json(
        str(R / "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json"))
    qb.install_config_switches(tun)
    cfg = qb.build_config(R / "vendor/NumSim-mine", 150.0, 5400.0, "wu-link",
                          cal, tun, local_observation=True, flagship=True)
    qb._plant_rollout_far_into(cfg, tun)
    dm = qb.load_optional_json(
        str(R / "evaluation/real_world_modi_control/detector_local_mapping.json"))
    controller = qb.build_priced_wu_link_controller(cfg, tun)
    follower = controller.nash_solver
    net = cfg.network

    # 램프를 먹이는 신호 = config 의 movement 중 목적지가 on-ramp 인 것을 가진 신호
    ramp_signals = set()
    for mv, spec in (net.urban_movements or {}).items():
        dest = str((spec or {}).get("destination", ""))
        if dest in set(net.ramps) or dest.startswith("R_"):
            sig = str(mv).split("_")[0]
            if sig in set(net.signals):
                ramp_signals.add(sig)
    if not ramp_signals:
        # 폴백: freeway agent 이웃으로 알려진 SC1001 · SC1004 (CLAUDE.md)
        ramp_signals = {s for s in ("SC1001", "SC1004") if s in set(net.signals)}
    other = [s for s in net.signals if s not in ramp_signals][:3]
    print("램프를 먹이는 신호 %s · 대조 신호 %s" % (sorted(ramp_signals), other))
    print()

    sfs = sorted(glob.glob(str(R / "evaluation/runs" / args.run / "decisions_*/state_*.json")))
    afs = sorted(glob.glob(str(R / "evaluation/runs" / args.run / "decisions_*/action_*.json")))
    pairs = [(s, a) for s, a in zip(sfs, afs)][6::max(1, len(sfs) // max(args.decisions, 1))]
    pairs = pairs[:args.decisions]

    SCALES = [0.25, 0.5, 0.75, 1.0]      # 커밋된 미터링에 곱한다 (조이는 방향)
    rows = []
    for sf, af in pairs:
        sj = json.loads(Path(sf).read_text(encoding="utf-8"))
        aj = json.loads(Path(af).read_text(encoding="utf-8"))
        t = float(sj.get("sim_sec") or 0.0)
        st = qb.traffic_state_from_vissim(sj, cfg, TrafficState, detector_mapping=dm, calibration=cal)
        base_meter = {k: float(v) for k, v in (aj.get("ramp_metering") or {}).items()}
        if not base_meter:
            continue
        vsl = {k: float(v) for k, v in (aj.get("vsl") or {}).items()}
        green = {k: float(v) for k, v in (aj.get("green_times") or {}).items()}
        _fm, _ub, ramp_arr, _p = qb.profiled_demand_rates(sj, cfg, cal, dm)
        demand = DemandStep(
            freeway_mainline={lk: float(sj.get("demand", {}).get("freeway_volume_vph", 0.0))
                              for lk in net.freeway_links},
            urban_boundary=dict(_ub), ramp_arrival=dict(ramp_arr))

        per_scale = {}
        for sc in SCALES:
            ctrl = ControlAction(
                ramp_metering={k: v * sc for k, v in base_meter.items()},
                vsl=dict(vsl), green_times=dict(green), offsets={},
                inflow_outflow_allocation={})
            drain = follower._frozen_reservoir_drain(st, ctrl, demand)
            release, _ = compute_ramp_release_flows(st, ctrl, demand, cfg)
            per_scale[sc] = {"meter_sum": sum(ctrl.ramp_metering.values()),
                             "drain": {k: float(v) for k, v in drain.items()},
                             "drain_sum": float(sum(drain.values())),
                             "release_sum": float(sum(release.values()))}
        rows.append({"sim_sec": t, "base_meter_sum": sum(base_meter.values()),
                     "ramp_arrival_sum": float(sum(ramp_arr.values())), "scales": per_scale})
        print("t=%-6.0f 커밋 미터링합 %6.0f · 도착합 %6.0f" % (t, sum(base_meter.values()), sum(ramp_arr.values())))
        for sc in SCALES:
            p = per_scale[sc]
            print("    x%-5.2f 미터링 %7.0f -> reservoir_drain %8.1f · release %8.1f"
                  % (sc, p["meter_sum"], p["drain_sum"], p["release_sum"]))
        print()

    # 1단계 판정: 미터링 -> drain 이 반응하는가
    resp = []
    for r in rows:
        lo = r["scales"][SCALES[0]]["drain_sum"]
        hi = r["scales"][1.0]["drain_sum"]
        resp.append(abs(hi - lo) / max(abs(hi), 1e-9))
    verdict1 = ("**끊겼다** — 미터링을 4분의 1로 조여도 reservoir_drain 이 안 변한다"
                if max(resp, default=0) < 1e-6 else
                "반응한다 (최대 상대변화 %.1f%%)" % (100 * max(resp, default=0)))
    print("1단계 미터링 -> reservoir_drain : %s" % verdict1)

    doc = {
        "schema_version": "urban-ramp-tradeoff/1",
        "generated": "2026-08-31",
        "why": "고속도로 모델 수정마다 freeway 가 좋아지고 urban 이 그보다 나빠진다. "
               "그 상충이 GNE 안에서 저울질되는지 실런 상태에서 직접 잰다.",
        "run": args.run, "tuning": args.tuning,
        "ramp_signals": sorted(ramp_signals), "control_signals": other,
        "scales": SCALES, "rows": rows,
        "stage1_metering_to_drain": verdict1,
        "stage1_relative_response": resp,
    }
    (R / args.out).write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print("-> %s" % args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
