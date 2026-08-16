#!/usr/bin/env python3
"""VISSIM 관측에서 **분기율(beta)** 과 **포화유율**을 역산해 모델 값과 대조한다.

## 왜 커넥터인가

`bottleneck_links_*.csv` 가 관측하는 링크 1208개 중 933개가 커넥터다
(category=local_observable_connector). 커넥터 하나가 곧 하나의 회전이므로, 커넥터 위
차량 수에서 그 회전의 유량을 역산할 수 있다.

    Little 법칙   N = q * t_traverse,   t_traverse = length / speed
    =>            q [veh/h] = N * speed[km/h] / length[km]

접근 링크에서 나가는 커넥터들의 유량을 정규화하면 그것이 **관측된 분기율**이다.

## 왜 이걸 먼저 재는가

구간 예측 오차 45% 가 한 스텝(60초) 만에 생기고 평평하다. 60초면 포화유율 1800 veh/h
에서 movement 당 30대가 빠지는 시간이다. 즉 이 오차는 링크 내부 전파(여러 스텝에 걸쳐
누적)가 아니라 **첫 스텝의 방출률·분기율**을 가리킨다.

그리고 이 두 값은 **모델을 CTM 으로 바꿔도 그대로 입력으로 들어간다.** 틀려 있으면
CTM 도 같은 오차를 낸다. 그래서 모델 교체를 논하기 전에 여기부터 확인해야 한다.

## 대조 방법

모델 movement 는 (approach_leg, exit_leg) 로 정의되고 beta 를 갖는다. 관측 커넥터는
(from_link, to_link) 다. 둘을 **하류 SC** 로 묶어 맞춘다 - `link_owner[to_link]` 가
그 회전이 향하는 교차로이고, movement 의 exit 도 그 교차로를 담고 있다.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import statistics as st
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Any, Sequence

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
REPO = Path(__file__).resolve().parent.parent

MIN_SPEED_KPH = 1.0
MIN_COUNT = 0.2          # 이 밑은 표본이 없다고 본다
MIN_LENGTH_M = 3.0       # 너무 짧은 스텁은 유량 역산이 불안정하다


def connector_geometry(inpx: Path) -> dict[str, dict[str, Any]]:
    """커넥터 번호 -> {from_link, to_link, length_m, lanes}"""
    root = ET.parse(inpx).getroot()
    out: dict[str, dict[str, Any]] = {}
    for link in root.iter("link"):
        no = str(link.get("no"))
        frm = link.find("fromLinkEndPt")
        to = link.find("toLinkEndPt")
        if frm is None or to is None:
            continue
        pts = [
            (float(p.get("x", 0)), float(p.get("y", 0)), float(p.get("zOffset", 0) or 0))
            for p in link.iter("linkPolyPoint")
        ]
        length = 0.0
        for a, b in zip(pts, pts[1:]):
            length += math.dist(a, b)
        lanes = len(list(link.iter("laneWidth"))) or 1
        out[no] = {
            "from_link": str(frm.get("link")),
            "to_link": str(to.get("link")),
            "length_m": length,
            "lanes": lanes,
        }
    return out


def observed_connector_flow(csv_path: Path, geo: dict[str, dict[str, Any]], t0: float, t1: float):
    """커넥터별 평균 유량[veh/h] 을 Little 법칙으로 역산한다."""
    acc: dict[str, list[float]] = defaultdict(list)
    with open(csv_path, encoding="utf-8", errors="replace", newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                sec = float(row["sim_sec"])
            except (KeyError, TypeError, ValueError):
                continue
            if sec < t0 or sec > t1:
                continue
            link = str(row["link"])
            g = geo.get(link)
            if not g or g["length_m"] < MIN_LENGTH_M:
                continue
            try:
                n = float(row["count"])
                v = float(row["mean_speed_kph"])
            except (KeyError, TypeError, ValueError):
                continue
            if n < MIN_COUNT or v < MIN_SPEED_KPH:
                continue
            acc[link].append(n * v / (g["length_m"] / 1000.0))
    return {k: st.mean(v) for k, v in acc.items() if v}


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--cell", required=True, help="부모런 셀 이름")
    ap.add_argument("--t0", type=float, default=900.0)
    ap.add_argument("--t1", type=float, default=3600.0)
    ap.add_argument(
        "--network", type=Path,
        default=REPO / "network/real_world_gaepo_modi/modi_eval_userfix_20260814e.inpx")
    ap.add_argument(
        "--assignment", type=Path,
        default=REPO / "outputs/link_player_assignment_pedfold_20260814.json")
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args(argv)

    geo = connector_geometry(args.network)
    assign = json.loads(args.assignment.read_text(encoding="utf-8"))
    owner = assign.get("link_owner") or {}

    flow = observed_connector_flow(
        args.run_dir / f"bottleneck_links_{args.cell}.csv", geo, args.t0, args.t1
    )
    print(f"유량을 역산한 커넥터 {len(flow)}개 (기하 있는 커넥터 {len(geo)}개 중)")

    # 접근 링크별로 하류 SC 로 묶어 관측 분기율을 만든다.
    by_from: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for conn, q in flow.items():
        g = geo[conn]
        down = owner.get(str(g["to_link"]))
        if down is None:
            continue
        by_from[str(g["from_link"])][f"SC{int(down)}"] += q

    observed_beta: list[float] = []
    per_approach: list[dict[str, Any]] = []
    for frm, dests in by_from.items():
        total = sum(dests.values())
        if total <= 0 or len(dests) < 2:
            continue
        shares = {k: v / total for k, v in sorted(dests.items())}
        observed_beta.extend(shares.values())
        per_approach.append({"from_link": frm, "total_flow_vph": total, "shares": shares})

    # 모델 beta
    sys.path.insert(0, str(REPO / "evaluation" / "controllers"))
    import vissim_stackelberg_adapter as ad  # noqa: E402

    rr = Path(ad.DEFAULT_REPO_ROOT)
    ad.repo_imports(rr)
    tun = ad.load_optional_json(str(REPO / "evaluation/configs/real_world_modi_pstack_distributed_pedovrx_20260814.json"))
    cal = ad.load_optional_json(str(REPO / "evaluation/calibration/real_world_prediction_calibration_pshb4500fix_20260724.json"))
    ov = tun.get("calibration_override", {})
    if isinstance(ov, dict):
        cal = ad.deep_update(dict(cal), ov)
    cfg = ad.build_config(rr, 60.0, 3600.0, "local_observation", cal, tun,
                          local_observation=True, flagship=False)
    model_beta = [float(s.get("beta", 0.0)) for s in cfg.network.urban_movements.values()]

    def dist(v):
        v = sorted(x for x in v if x == x)
        if not v:
            return {}
        return {
            "n": len(v), "min": v[0], "p25": v[int(0.25 * (len(v) - 1))],
            "median": st.median(v), "p75": v[int(0.75 * (len(v) - 1))], "max": v[-1],
        }

    # 포화유율 - 커넥터 유량 상위값이 사실상 포화 상태의 방출률이다.
    per_lane = []
    for conn, q in flow.items():
        lanes = max(1, int(geo[conn]["lanes"]))
        per_lane.append(q / lanes)
    per_lane.sort()
    sat = {
        "n": len(per_lane),
        "p50": per_lane[len(per_lane) // 2] if per_lane else float("nan"),
        "p90": per_lane[int(0.9 * (len(per_lane) - 1))] if per_lane else float("nan"),
        "p95": per_lane[int(0.95 * (len(per_lane) - 1))] if per_lane else float("nan"),
        "max": per_lane[-1] if per_lane else float("nan"),
        "model_assumed_vph": 1800.0,
    }

    payload = {
        "schema_version": "observed-turn-ratio-v1",
        "cell": args.cell,
        "window_sec": [args.t0, args.t1],
        "method": "q = N * speed / length (Little). 접근 링크별로 하류 SC 로 묶어 정규화",
        "connectors_with_flow": len(flow),
        "approaches_with_split": len(per_approach),
        "observed_beta_dist": dist(observed_beta),
        "model_beta_dist": dist(model_beta),
        "saturation_flow_per_lane_vph": sat,
        "per_approach_sample": per_approach[:15],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
                        encoding="utf-8", newline="\n")

    print(f"\n분기 가능한 접근 링크 {len(per_approach)}개")
    print(f"{'':10s} {'n':>5s} {'min':>7s} {'p25':>7s} {'median':>7s} {'p75':>7s} {'max':>7s}")
    for lbl, d in (("관측 beta", payload["observed_beta_dist"]), ("모델 beta", payload["model_beta_dist"])):
        if d:
            print(f"{lbl:10s} {d['n']:5d} {d['min']:7.3f} {d['p25']:7.3f} {d['median']:7.3f} {d['p75']:7.3f} {d['max']:7.3f}")
    print(f"\n차로당 유량[veh/h]  p50={sat['p50']:.0f}  p90={sat['p90']:.0f}  p95={sat['p95']:.0f}  max={sat['max']:.0f}")
    print(f"  모델 가정 포화유율 = {sat['model_assumed_vph']:.0f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
