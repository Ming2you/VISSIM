# G5 잔차를 세그먼트별로 분해한다 — 세그먼트별 파라미터화가 필요한지, 어느 파라미터부터인지의 근거.
"""구성 (b) 기준으로 H=1(60 s) 셀 잔차를 세그먼트 단위로 쪼갠다.

두 가지를 본다.
  * bias_v(세그먼트) — 계통 속도 편향. 세그먼트마다 부호가 갈리고 크기가 크면
    단일 v_free 로는 원리적으로 못 맞춘다는 뜻이다.
  * 관측 자유류 속도(저밀도 표본의 관측 속도) — 세그먼트 고유 v_free 의 대리값.
    이것이 세그먼트마다 다르면 v_free 가 세그먼트별 파라미터의 1순위다.
  * 셀 count MAE 의 세그먼트별 기여 — 어느 셀이 임계 초과를 만드는가.
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import episode as ep  # noqa: E402
import g5_metrics as g5  # noqa: E402
import g6_core as core  # noqa: E402
import run_config_grid as grid  # noqa: E402

CONFIG = core.VISSIM_ROOT / "evaluation/configs/gates_scoring/gates_cfgB_post.json"
OUT = core.VISSIM_ROOT / "outputs/gates_config_grid_20260802/g5_segment_residuals.json"
FREE_FLOW_RHO_MAX = 12.0  # veh/km/lane 이하를 자유류 표본으로 본다


def main() -> int:
    samples: list[g5.Sample] = []
    free_flow: dict[str, list[float]] = {}
    for decision_dir in grid.G5_RUN_DIRS:
        observed = ep.state_series(decision_dir)
        anchor_json = ep.read_json(observed[min(observed)])
        rt = core.build_runtime(anchor_json, tuning_json=CONFIG)
        episodes, _, _ = grid.rg.collect_g5_episodes(
            rt, decision_dir, [1], t_min=900, t_max=None, stride=1)
        for episode in episodes:
            samples.extend(g5.freeway_samples(episode))
            geometry = episode.geometry
            for _, _, obs in episode.pairs():
                for link in geometry.links:
                    for index in range(geometry.segment_count(link)):
                        rho = float(obs.freeway_density[link][index])
                        if 0.5 < rho <= FREE_FLOW_RHO_MAX:
                            free_flow.setdefault(f"{link}_S{index}", []).append(
                                float(obs.freeway_speed[link][index]))

    entities = sorted({s.entity for s in samples})
    rows = []
    for entity in entities:
        count = [s for s in samples if s.level == "cell_count" and s.entity == entity]
        speed = [s for s in samples if s.level == "cell_speed" and s.entity == entity]
        observed_speeds = free_flow.get(entity, [])
        rows.append({
            "segment": entity,
            "count_mae": statistics.fmean([s.abs_error for s in count]) if count else None,
            "count_bias": statistics.fmean([s.predicted - s.observed for s in count]) if count else None,
            "mean_observed_count": statistics.fmean([s.observed for s in count]) if count else None,
            "speed_mae": statistics.fmean([s.abs_error for s in speed]) if speed else None,
            "speed_bias": statistics.fmean([s.predicted - s.observed for s in speed]) if speed else None,
            "speed_mape": statistics.fmean([s.ape for s in speed if s.ape is not None]) if speed else None,
            "mean_observed_speed": statistics.fmean([s.observed for s in speed]) if speed else None,
            "observed_free_flow_speed_p50": (statistics.median(observed_speeds)
                                             if observed_speeds else None),
            "free_flow_sample_count": len(observed_speeds),
        })

    free_speeds = [r["observed_free_flow_speed_p50"] for r in rows
                   if r["observed_free_flow_speed_p50"] is not None]
    payload = {
        "config": "b_FDA_post",
        "horizon_steps": 1,
        "horizon_sec": 60,
        "model_v_free_kph": 119.505,
        "segments": rows,
        "observed_free_flow_speed_spread": {
            "min": min(free_speeds), "max": max(free_speeds),
            "range": max(free_speeds) - min(free_speeds),
            "note": "세그먼트별 관측 자유류(rho<=12) 속도 중앙값. 단일 v_free 로 덮을 수 "
                    "있는 범위인지 보는 값이다.",
        },
        "speed_bias_spread": {
            "min": min(r["speed_bias"] for r in rows if r["speed_bias"] is not None),
            "max": max(r["speed_bias"] for r in rows if r["speed_bias"] is not None),
        },
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    header = ("segment", "cnt_MAE", "cnt_bias", "obs_cnt", "spd_MAE", "spd_bias",
              "spd_MAPE", "obs_spd", "obs_vfree")
    print("%-12s %8s %9s %8s %8s %9s %9s %8s %10s" % header)
    for row in rows:
        if any(row[key] is None for key in ("count_mae", "speed_mae", "speed_mape")):
            print(f"{row['segment']:<12} 표본 부족: {row}")
            continue
        print("%-12s %8.2f %9.2f %8.1f %8.2f %9.2f %9.4f %8.1f %10s" % (
            row["segment"], row["count_mae"], row["count_bias"], row["mean_observed_count"],
            row["speed_mae"], row["speed_bias"], row["speed_mape"], row["mean_observed_speed"],
            "-" if row["observed_free_flow_speed_p50"] is None
            else round(row["observed_free_flow_speed_p50"], 1)))
    print(f"\n관측 자유류 속도 세그먼트 간 범위 = "
          f"{payload['observed_free_flow_speed_spread']['range']:.1f} km/h "
          f"({payload['observed_free_flow_speed_spread']['min']:.1f} ~ "
          f"{payload['observed_free_flow_speed_spread']['max']:.1f}), 모델 단일 v_free = 119.5")
    print(f"OUT={OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
