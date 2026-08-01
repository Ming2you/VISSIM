# 새 기준선 A/B(무제어 vs 컨트롤러) 비교 지표와 제어 활성화 지표를 산출하는 분석 스크립트.
"""새 기준선 A/B 분석.

두 가지를 낸다.
1. arm 별 windowed 성능 지표 - TTT(veh-h), 정지 차량-시간, 시간가중 평균속도, 세그먼트별 밀도/속도.
2. 컨트롤러 arm 의 제어 활성화 지표 - metering_active_steps, vsl_active_steps, N_UF_star 분포.

무제어 arm 은 결정 산출물이 없으므로 활성화 지표는 컨트롤러 arm 에만 적용된다.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path


def fnum(value: object, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def integrate(rows: list[dict[str, str]], key: str, start: float, end: float) -> float:
    """구간 [start, end] 에서 key 를 시간적분해 veh-h 로 돌려준다.

    각 행은 다음 행까지 유지된다고 본다(zero-order hold). 마지막 행은 end 까지.
    """
    total = 0.0
    ordered = sorted(rows, key=lambda r: fnum(r["sim_sec"]))
    for i, row in enumerate(ordered):
        t0 = fnum(row["sim_sec"])
        t1 = fnum(ordered[i + 1]["sim_sec"]) if i + 1 < len(ordered) else end
        a = max(t0, start)
        b = min(t1, end)
        if b > a:
            total += fnum(row.get(key)) * (b - a)
    return total / 3600.0


def weighted_mean(rows: list[dict[str, str]], key: str, start: float, end: float) -> float:
    num = 0.0
    den = 0.0
    ordered = sorted(rows, key=lambda r: fnum(r["sim_sec"]))
    for i, row in enumerate(ordered):
        t0 = fnum(row["sim_sec"])
        t1 = fnum(ordered[i + 1]["sim_sec"]) if i + 1 < len(ordered) else end
        a = max(t0, start)
        b = min(t1, end)
        if b > a:
            num += fnum(row.get(key)) * (b - a)
            den += b - a
    return num / den if den else 0.0


def state_metrics(rows: list[dict[str, str]], start: float, end: float) -> dict[str, float]:
    window = [r for r in rows if start <= fnum(r["sim_sec"]) <= end]
    return {
        "ttt_veh_h": integrate(rows, "total_vehicles", start, end),
        "urban_veh_h": integrate(rows, "urban_vehicles", start, end),
        "freeway_veh_h": integrate(rows, "freeway_vehicles", start, end),
        "ramp_veh_h": integrate(rows, "ramp_vehicles", start, end),
        "stopped_veh_h": integrate(rows, "stopped_vehicles", start, end),
        "mean_speed_kph": weighted_mean(rows, "mean_speed_kph", start, end),
        "freeway_mean_speed_kph": weighted_mean(rows, "freeway_mean_speed_kph", start, end),
        "peak_total_veh": max((fnum(r.get("total_vehicles")) for r in window), default=0.0),
        "peak_stopped_veh": max((fnum(r.get("stopped_vehicles")) for r in window), default=0.0),
        "final_total_veh": fnum(window[-1].get("total_vehicles")) if window else 0.0,
        "final_stopped_veh": fnum(window[-1].get("stopped_vehicles")) if window else 0.0,
        "n_rows_in_window": float(len(window)),
    }


def segment_metrics(rows: list[dict[str, str]], start: float, end: float) -> dict[str, dict[str, float]]:
    """세그먼트별 평균 밀도/속도. 속도는 대수(count) 가중, 빈 표본은 제외한다."""
    acc: dict[str, dict[str, float]] = defaultdict(
        lambda: {"dens_sum": 0.0, "dens_n": 0.0, "spd_num": 0.0, "spd_den": 0.0, "cnt_sum": 0.0, "stop_sum": 0.0, "dens_max": 0.0}
    )
    for row in rows:
        t = fnum(row["sim_sec"])
        if not (start <= t <= end):
            continue
        seg = row["segment_id"]
        a = acc[seg]
        dens = fnum(row.get("density_veh_km_lane"))
        cnt = fnum(row.get("count"))
        a["dens_sum"] += dens
        a["dens_n"] += 1.0
        a["dens_max"] = max(a["dens_max"], dens)
        a["cnt_sum"] += cnt
        a["stop_sum"] += fnum(row.get("stopped_count"))
        if cnt > 0:
            a["spd_num"] += fnum(row.get("mean_speed_kph")) * cnt
            a["spd_den"] += cnt
    out: dict[str, dict[str, float]] = {}
    for seg, a in acc.items():
        out[seg] = {
            "mean_density_veh_km_lane": a["dens_sum"] / a["dens_n"] if a["dens_n"] else 0.0,
            "max_density_veh_km_lane": a["dens_max"],
            "mean_speed_kph": a["spd_num"] / a["spd_den"] if a["spd_den"] else 0.0,
            "mean_count": a["cnt_sum"] / a["dens_n"] if a["dens_n"] else 0.0,
            "mean_stopped": a["stop_sum"] / a["dens_n"] if a["dens_n"] else 0.0,
        }
    return out


def control_activation(
    decision_dir: Path,
    start: float,
    end: float,
    ramp_capacity_vph: float,
    vsl_anchor_kph: float,
    tol: float = 1e-6,
) -> dict[str, object]:
    """결정 action_*.json 을 읽어 제어 활성화 지표를 만든다.

    - metering_active: 램프 키 중 하나라도 용량(1800 vph) 미만이면 활성.
    - vsl_active: 세그먼트 VSL 중 하나라도 무제어 앵커(메뉴 최대값) 미만이면 활성.
    """
    files = sorted(decision_dir.glob("action_*.json"))
    steps: list[dict[str, object]] = []
    for path in files:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        sim_sec = fnum(path.stem.split("_")[-1])
        if not (start <= sim_sec <= end):
            continue
        ramp = {k: fnum(v) for k, v in (payload.get("ramp_metering") or {}).items()}
        vsl_all = {k: fnum(v) for k, v in (payload.get("vsl") or {}).items()}
        vsl_seg = {k: v for k, v in vsl_all.items() if "__seg" in k}
        vsl_link = {k: v for k, v in vsl_all.items() if "__seg" not in k}
        metering_on = [k for k, v in ramp.items() if v < ramp_capacity_vph - tol]
        vsl_on = [k for k, v in vsl_seg.items() if v < vsl_anchor_kph - tol]
        steps.append(
            {
                "sim_sec": sim_sec,
                "N_UF_star": fnum(payload.get("N_UF_star")),
                "N_P_star": fnum(payload.get("N_P_star")),
                "ramp": ramp,
                "ramp_min_vph": min(ramp.values()) if ramp else float("nan"),
                "ramp_mean_vph": sum(ramp.values()) / len(ramp) if ramp else float("nan"),
                "metering_active": bool(metering_on),
                "metering_active_keys": metering_on,
                "vsl_seg": vsl_seg,
                "vsl_link": vsl_link,
                "vsl_min_kph": min(vsl_seg.values()) if vsl_seg else float("nan"),
                "vsl_active": bool(vsl_on),
                "vsl_active_segments": vsl_on,
                "vsl_active_count": len(vsl_on),
                "green_times": {k: fnum(v) for k, v in (payload.get("green_times") or {}).items()},
                "offsets": {k: fnum(v) for k, v in (payload.get("offsets") or {}).items()},
            }
        )
    steps.sort(key=lambda s: s["sim_sec"])
    n = len(steps)
    nuf = [s["N_UF_star"] for s in steps]
    vsl_values: list[float] = []
    for s in steps:
        vsl_values.extend(s["vsl_seg"].values())
    ramp_values: list[float] = []
    for s in steps:
        ramp_values.extend(s["ramp"].values())
    green_values: list[float] = []
    for s in steps:
        green_values.extend(s["green_times"].values())
    return {
        "decision_steps": n,
        "metering_active_steps": sum(1 for s in steps if s["metering_active"]),
        "vsl_active_steps": sum(1 for s in steps if s["vsl_active"]),
        "vsl_active_channel_fraction": (
            sum(s["vsl_active_count"] for s in steps) / (n * 16) if n else 0.0
        ),
        "ramp_capacity_vph": ramp_capacity_vph,
        "vsl_anchor_kph": vsl_anchor_kph,
        "ramp_min_vph_overall": min(ramp_values) if ramp_values else None,
        "ramp_value_histogram": dict(sorted({round(v, 1): ramp_values.count(v) for v in set(ramp_values)}.items())),
        "vsl_value_histogram": dict(sorted({round(v, 1): vsl_values.count(v) for v in set(vsl_values)}.items())),
        "green_min_sec": min(green_values) if green_values else None,
        "green_max_sec": max(green_values) if green_values else None,
        "N_UF_star_min": min(nuf) if nuf else None,
        "N_UF_star_max": max(nuf) if nuf else None,
        "N_UF_star_mean": sum(nuf) / n if n else None,
        "N_UF_star_histogram": dict(sorted({round(v, 1): nuf.count(v) for v in set(nuf)}.items())),
        "steps": steps,
    }


def runlog_decisions(runlog: Path) -> dict[str, object]:
    if not runlog.exists():
        return {"present": False}
    text = runlog.read_text(encoding="utf-8", errors="replace")
    out: dict[str, object] = {"present": True, "sim_done": "STAGE=SIM_DONE" in text}
    for token in ("DECISIONS_OK=", "DECISIONS_FAILED=", "PYTHON=", "PYTHON_VERSION=", "RUN_MODE="):
        for line in text.splitlines():
            if line.startswith(token):
                out[token.rstrip("=").lower()] = line[len(token):].strip() if token.endswith("=") else line.strip()
                break
    walls = []
    for line in text.splitlines():
        if line.startswith("CONTROLLER_DECISION") and " wall_sec=" in line:
            try:
                walls.append(float(line.split(" wall_sec=")[1].split(" ")[0]))
            except (IndexError, ValueError):
                pass
    if walls:
        out["decision_wall_sec_count"] = len(walls)
        out["decision_wall_sec_mean"] = sum(walls) / len(walls)
        out["decision_wall_sec_max"] = max(walls)
        out["decision_wall_sec_total"] = sum(walls)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--arm", action="append", required=True,
                    help="label=run_name 형식. 첫 arm 이 기준(baseline)이다.")
    ap.add_argument("--start-sec", type=float, required=True)
    ap.add_argument("--end-sec", type=float, required=True)
    ap.add_argument("--ramp-capacity-vph", type=float, default=1800.0)
    ap.add_argument("--vsl-anchor-kph", type=float, default=120.0)
    ap.add_argument("--out-json", required=True)
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    arms: list[tuple[str, str]] = []
    for spec in args.arm:
        label, _, name = spec.partition("=")
        arms.append((label, name))

    result: dict[str, object] = {
        "run_dir": str(run_dir),
        "window_sec": [args.start_sec, args.end_sec],
        "arms": {},
    }
    for label, name in arms:
        state = run_dir / f"state_{name}.csv"
        segs = run_dir / f"bottleneck_segments_{name}.csv"
        decisions = run_dir / f"decisions_{name}"
        runlog = run_dir / f"runlog_{name}.txt"
        entry: dict[str, object] = {"run_name": name, "state_csv": str(state)}
        if state.exists():
            entry["state"] = state_metrics(read_csv(state), args.start_sec, args.end_sec)
        if segs.exists():
            entry["segments"] = segment_metrics(read_csv(segs), args.start_sec, args.end_sec)
        if decisions.exists():
            entry["control"] = control_activation(
                decisions, args.start_sec, args.end_sec, args.ramp_capacity_vph, args.vsl_anchor_kph
            )
        entry["runlog"] = runlog_decisions(runlog)
        result["arms"][label] = entry

    base_label = arms[0][0]
    base = result["arms"][base_label].get("state", {})
    for label, _ in arms[1:]:
        cand = result["arms"][label].get("state", {})
        deltas = {}
        for key in base:
            if key == "n_rows_in_window":
                continue
            b = base[key]
            c = cand.get(key, 0.0)
            deltas[key] = {
                "baseline": b,
                "candidate": c,
                "delta": c - b,
                "delta_pct": (c - b) / b * 100.0 if b else float("nan"),
            }
        result["arms"][label]["vs_baseline"] = deltas

    out = Path(args.out_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"WROTE {out}")
    for label, entry in result["arms"].items():
        st = entry.get("state", {})
        ct = entry.get("control", {})
        print(
            f"{label}: TTT={st.get('ttt_veh_h', float('nan')):.2f} "
            f"stopped={st.get('stopped_veh_h', float('nan')):.2f} "
            f"v={st.get('mean_speed_kph', float('nan')):.2f} "
            f"vfw={st.get('freeway_mean_speed_kph', float('nan')):.2f} "
            f"decisions={ct.get('decision_steps', 0)} "
            f"met_on={ct.get('metering_active_steps', 0)} vsl_on={ct.get('vsl_active_steps', 0)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
