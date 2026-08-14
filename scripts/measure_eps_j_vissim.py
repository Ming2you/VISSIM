#!/usr/bin/env python3
"""N5 의 eps_J_vissim 을 base replay 들에서 잰다.

## eps_J_vissim 이 무엇을 재는가 — 수요 실현 분산이 아니라 **재현성**이다

계획이 말하는 "독립 t=0 base replay 20회" 는 시드를 바꾼 20회가 아니다. 같은 .inpx,
같은 시드, 같은 수요 배율, 같은 no-control 설정으로 **똑같이 20번 다시 돌리는 것**이다.
근거 셋:

1. 하한이 `1e-6 veh·h` 다. J 는 수천 veh·h 규모다. 시드를 바꾼 수요 실현 분산이라면
   하한이 1e-6 일 이유가 없다 - 그 값은 "움직이면 안 되는 양" 의 하한이다.
2. 형제 값 `eps_J_endpoint`(하한 `1e-9`)가 플랜트 endpoint **재현성** 잡음이다.
   둘은 같은 성격의 값이고 대상만 다르다(VISSIM 대 endpoint).
3. 계획 N9-1 이 스냅샷 복원을 금지하고 모든 branch 를 t=0 부터 재실행하도록 못 박은 이유가
   접두를 바이트 단위로 같게 만들기 위해서다. 시드 분산을 재려 했다면 접두 동일성에
   신경 쓸 이유가 없다. 실측도 있다 - `outputs/gates_config_grid_20260802/g6_flip_analysis.json`
   의 arm 14개가 t=900 에서 `distinct_state_hashes=1`.

따라서 **spread 가 0 으로 나오는 것이 정상이고 의미 있는 결과다.** 그것이 "VISSIM 이
재현된다" 는 증명이고, 이후 ΔJ 가 0 이 아니면 실재한다고 말할 근거가 된다. 0 이 아니게
나오면 그 자체가 발견이다 - 그때는 값이 그대로 잡음 바닥이 된다.

## J

`state_<run>.csv` 의 `total_vehicles` 를 anchor 부터 런 끝까지 사다리꼴 적분해 3600 으로
나눈 veh·h(= TTT). `scripts/summarize_real_world_lever_sensitivity.py:88-127` 과 같은 산식이다.
anchor 마다 창이 다르므로 한 번의 replay 가 4개 anchor 의 J 를 전부 준다 - 그래서 replay 는
부모-anchor 당 20회가 아니라 **부모당 20회**면 된다.

## 섞지 마라

`eps_J_endpoint`(N8-1) 는 여기서 계산하지 않는다. 두 값을 합치면 `eps_g` 가 과대해져
`|intercept| <= median(eps_g)` 가 느슨해지고 재료 표본이 줄어 지지 요건이 무너진다.
v3 초판이 실제로 그렇게 합쳤다.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Sequence

SCHEMA_VERSION = "development-noise-v3"
EPS_J_VISSIM_FLOOR_VEH_H = 1.0e-6
ANCHORS_SEC = (900, 1500, 2100, 2700)
VISSIM_SOURCE = "vissim_base_replay"


def _fnum(value: Any) -> float | None:
    try:
        out = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return None if math.isnan(out) else out


def read_state_series(path: Path, column: str = "total_vehicles") -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    with open(path, encoding="utf-8", errors="replace", newline="") as fh:
        for row in csv.DictReader(fh):
            sec = _fnum(row.get("sim_sec"))
            val = _fnum(row.get(column))
            if sec is not None and val is not None:
                points.append((sec, val))
    points.sort(key=lambda item: item[0])
    return points


def integrate_veh_hours(points: Sequence[tuple[float, float]], start_sec: float, end_sec: float) -> float:
    """[start,end] 구간의 사다리꼴 적분 / 3600. 경계는 선형보간한다."""
    if len(points) < 2 or end_sec <= start_sec:
        return math.nan

    def value_at(target: float) -> float:
        if target <= points[0][0]:
            return points[0][1]
        if target >= points[-1][0]:
            return points[-1][1]
        for (t0, y0), (t1, y1) in zip(points, points[1:]):
            if t0 <= target <= t1:
                if t1 <= t0:
                    return y1
                return y0 + (target - t0) / (t1 - t0) * (y1 - y0)
        return points[-1][1]

    window = (
        [(start_sec, value_at(start_sec))]
        + [(t, y) for t, y in points if start_sec < t < end_sec]
        + [(end_sec, value_at(end_sec))]
    )
    area = 0.0
    for (t0, y0), (t1, y1) in zip(window, window[1:]):
        area += (t1 - t0) * (y0 + y1) / 2.0
    return area / 3600.0


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def eps_from_values(values: Sequence[float]) -> float:
    live = [v for v in values if v is not None and not math.isnan(v)]
    if len(live) < 2:
        raise ValueError("need at least two base replays to measure spread")
    return max(EPS_J_VISSIM_FLOOR_VEH_H, max(live) - min(live))


def measure(
    run_dir: Path,
    replay_names: Sequence[str],
    *,
    anchors: Sequence[int] = ANCHORS_SEC,
    end_sec: float | None = None,
    require_count: int = 0,
) -> dict[str, Any]:
    reasons: list[str] = []
    replays: list[dict[str, Any]] = []

    for name in replay_names:
        state = run_dir / f"state_{name}.csv"
        if not state.is_file():
            reasons.append(f"{name}: 상태 CSV 없음")
            continue
        points = read_state_series(state)
        if len(points) < 2:
            reasons.append(f"{name}: 상태 행이 부족하다({len(points)})")
            continue
        run_end = end_sec if end_sec is not None else points[-1][0]
        objectives = {
            str(anchor): integrate_veh_hours(points, float(anchor), float(run_end))
            for anchor in anchors
            if anchor < run_end
        }
        missing = [str(a) for a in anchors if str(a) not in objectives]
        if missing:
            reasons.append(f"{name}: anchor {','.join(missing)} 가 런 끝({run_end}s) 밖이다")
        replays.append(
            {
                "name": name,
                "source": VISSIM_SOURCE,
                "state_csv_sha256": file_sha256(state),
                "state_rows": len(points),
                "last_sim_sec": run_end,
                "objective_veh_h_by_anchor": objectives,
            }
        )

    if require_count and len(replays) < require_count:
        reasons.append(f"base replay {len(replays)}회 < 요구 {require_count}회")

    per_anchor: dict[str, Any] = {}
    for anchor in anchors:
        key = str(anchor)
        values = [
            r["objective_veh_h_by_anchor"].get(key)
            for r in replays
            if key in r["objective_veh_h_by_anchor"]
        ]
        values = [v for v in values if v is not None and not math.isnan(v)]
        if len(values) < 2:
            reasons.append(f"anchor {anchor}: 표본 {len(values)}개로는 격차를 못 잰다")
            continue
        spread = max(values) - min(values)
        per_anchor[key] = {
            "replays": len(values),
            "j_min_veh_h": min(values),
            "j_max_veh_h": max(values),
            "j_spread_veh_h": spread,
            "eps_j_vissim_veh_h": max(EPS_J_VISSIM_FLOOR_VEH_H, spread),
            "at_floor": spread <= EPS_J_VISSIM_FLOOR_VEH_H,
            # 상태 CSV 해시가 전부 같으면 VISSIM 이 바이트 단위로 재현된 것이다.
            "identical_state_csv": len({r["state_csv_sha256"] for r in replays}) == 1,
        }

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS" if not reasons else "FAIL",
        "reasons": sorted(set(reasons)),
        "floor_veh_h": EPS_J_VISSIM_FLOOR_VEH_H,
        "scope": "VISSIM 런간 재현성. N9 의 ΔJ 재료성 판정 전용",
        "never_mix": "eps_J_endpoint(하한 1e-9, N8-1)와 섞지 마라",
        "objective": "TTT = trapezoid(total_vehicles) over [anchor, run_end] / 3600 (veh·h)",
        "run_dir": str(run_dir),
        "sample_dimensions": {
            "replays": len(replays),
            "anchors": len(per_anchor),
        },
        "per_anchor": per_anchor,
        "replays": replays,
    }
    payload["semantic_sha256"] = hashlib.sha256(
        json.dumps(
            {k: v for k, v in payload.items() if k != "run_dir"},
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="eps_J_vissim 을 base replay 들에서 잰다")
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument(
        "--replay",
        action="append",
        default=[],
        help="base replay 의 런 이름. 여러 번 준다. 비우면 --prefix 로 찾는다.",
    )
    ap.add_argument("--prefix", default="", help="state_<prefix>*.csv 로 replay 를 찾는다")
    ap.add_argument("--end-sec", type=float, default=None)
    ap.add_argument("--require-count", type=int, default=0, help="이보다 적으면 FAIL")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args(argv)

    run_dir = args.run_dir.resolve()
    names = list(args.replay)
    if not names and args.prefix:
        names = sorted(
            path.name[len("state_") : -len(".csv")]
            for path in run_dir.glob(f"state_{args.prefix}*.csv")
        )
    if not names:
        print(json.dumps({"status": "FAIL", "reason": "replay 이름이 하나도 없다"}, ensure_ascii=False))
        return 1

    payload = measure(
        run_dir, names, end_sec=args.end_sec, require_count=args.require_count
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(
        "status=%s replays=%d anchors=%d hash=%s"
        % (
            payload["status"],
            payload["sample_dimensions"]["replays"],
            payload["sample_dimensions"]["anchors"],
            payload["semantic_sha256"][:16],
        )
    )
    for anchor, rec in sorted(payload["per_anchor"].items(), key=lambda kv: int(kv[0])):
        print(
            "  anchor %-5s n=%-3d J=[%.6f, %.6f]  spread=%.3e  eps=%.3e%s"
            % (
                anchor,
                rec["replays"],
                rec["j_min_veh_h"],
                rec["j_max_veh_h"],
                rec["j_spread_veh_h"],
                rec["eps_j_vissim_veh_h"],
                "  (바닥)" if rec["at_floor"] else "",
            )
        )
    for reason in payload["reasons"][:10]:
        print("  " + reason)
    return 2 if args.strict and payload["status"] != "PASS" else 0


if __name__ == "__main__":
    raise SystemExit(main())
