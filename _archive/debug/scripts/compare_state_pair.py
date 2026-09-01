from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return sorted(list(csv.DictReader(f)), key=lambda row: to_float(row["sim_sec"]))


def to_float(value: object) -> float:
    try:
        if value is None or value == "":
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def integrate(rows: list[dict[str, str]], key: str, start: float, end: float) -> float:
    total = 0.0
    for i, row in enumerate(rows):
        sim_sec = to_float(row["sim_sec"])
        next_sec = to_float(rows[i + 1]["sim_sec"]) if i + 1 < len(rows) else end
        a = max(sim_sec, start)
        b = min(next_sec, end)
        if b > a:
            total += to_float(row.get(key)) * (b - a)
    return total / 3600.0


def weighted_mean(rows: list[dict[str, str]], key: str, start: float, end: float) -> float:
    num = 0.0
    den = 0.0
    for i, row in enumerate(rows):
        sim_sec = to_float(row["sim_sec"])
        next_sec = to_float(rows[i + 1]["sim_sec"]) if i + 1 < len(rows) else end
        a = max(sim_sec, start)
        b = min(next_sec, end)
        if b > a:
            dt = b - a
            num += to_float(row.get(key)) * dt
            den += dt
    return num / den if den else 0.0


def state_metrics(rows: list[dict[str, str]], start: float, end: float) -> dict[str, float]:
    return {
        "TTT": integrate(rows, "total_vehicles", start, end),
        "urban": integrate(rows, "urban_vehicles", start, end),
        "freeway": integrate(rows, "freeway_vehicles", start, end),
        "ramp": integrate(rows, "ramp_vehicles", start, end),
        "stopped": integrate(rows, "stopped_vehicles", start, end),
        "mean_speed": weighted_mean(rows, "mean_speed_kph", start, end),
        "fw_speed": weighted_mean(rows, "freeway_mean_speed_kph", start, end),
        "peak_total": max(to_float(row.get("total_vehicles")) for row in rows),
        "peak_stopped": max(to_float(row.get("stopped_vehicles")) for row in rows),
        "final_total": to_float(rows[-1].get("total_vehicles")),
        "final_stopped": to_float(rows[-1].get("stopped_vehicles")),
    }


def action_stat(rows: list[dict[str, str]], kind: str, key: str) -> tuple[float, float, float]:
    vals = [
        to_float(row.get(key))
        for row in rows
        if row.get("kind") == kind and str(row.get(key, "")).strip() != ""
    ]
    if not vals:
        return 0.0, 0.0, 0.0
    return min(vals), sum(vals) / len(vals), max(vals)


def delta(base: float, candidate: float) -> tuple[float, float]:
    raw = candidate - base
    pct = raw / base * 100.0 if base else 0.0
    return raw, pct


def fmt(value: float) -> str:
    return f"{value:.3f}"


def pct(value: float) -> str:
    return f"{value:+.3f}%"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-state", required=True)
    parser.add_argument("--candidate-state", required=True)
    parser.add_argument("--candidate-action", default="")
    parser.add_argument("--out-md", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--network", default="")
    parser.add_argument("--baseline-name", default="baseline")
    parser.add_argument("--candidate-name", default="candidate")
    parser.add_argument("--note", default="")
    parser.add_argument("--start-sec", type=float, default=1.0)
    parser.add_argument("--end-sec", type=float, default=7200.0)
    args = parser.parse_args()

    baseline_rows = read_rows(Path(args.baseline_state))
    candidate_rows = read_rows(Path(args.candidate_state))
    base = state_metrics(baseline_rows, args.start_sec, args.end_sec)
    cand = state_metrics(candidate_rows, args.start_sec, args.end_sec)

    segments = [
        ("Build-up", "1-1800", 1.0, 1800.0),
        ("Peak hold", "1800-4500", 1800.0, 4500.0),
        ("Recovery", "4500-6300", 4500.0, 6300.0),
        ("Tail", "6300-7200", 6300.0, 7200.0),
    ]

    action_rows: list[dict[str, str]] = []
    if args.candidate_action:
        action_path = Path(args.candidate_action)
        if action_path.exists():
            with action_path.open(encoding="utf-8-sig", newline="") as f:
                action_rows = list(csv.DictReader(f))

    decision_walls = [
        to_float(row.get("decision_wall_sec"))
        for row in candidate_rows
        if to_float(row.get("decision_wall_sec")) > 0.0
    ]

    lines: list[str] = [
        f"# {args.title}",
        "",
    ]
    if args.network:
        lines.extend([f"Network: `{args.network}`", ""])
    lines.extend(
        [
            "Runs:",
            f"- Baseline: `{args.baseline_name}`",
            f"- Candidate: `{args.candidate_name}`",
        ]
    )
    if args.note:
        lines.append(f"- Note: {args.note}")
    lines.extend(
        [
            "",
            "## Main Metrics",
            "",
            "| Metric | Baseline | Candidate | Delta | Delta % |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for label, key in [
        ("Total TTT (veh-h)", "TTT"),
        ("Urban vehicle-hours", "urban"),
        ("Freeway vehicle-hours", "freeway"),
        ("Ramp vehicle-hours", "ramp"),
        ("Stopped vehicle-hours", "stopped"),
        ("Avg network speed (kph)", "mean_speed"),
        ("Avg freeway speed (kph)", "fw_speed"),
        ("Peak total vehicles", "peak_total"),
        ("Peak stopped vehicles", "peak_stopped"),
        ("Final total vehicles", "final_total"),
        ("Final stopped vehicles", "final_stopped"),
    ]:
        raw, percent = delta(base[key], cand[key])
        lines.append(f"| {label} | {fmt(base[key])} | {fmt(cand[key])} | {raw:+.3f} | {pct(percent)} |")

    lines.extend(
        [
            "",
            "## Segment Metrics",
            "",
            "| Segment | Time (s) | Baseline TTT | Candidate TTT | TTT Delta | TTT Delta % | Baseline stopped h | Candidate stopped h | Stopped Delta % |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    segment_payload = []
    for name, label, start, end in segments:
        base_ttt = integrate(baseline_rows, "total_vehicles", start, end)
        cand_ttt = integrate(candidate_rows, "total_vehicles", start, end)
        base_stopped = integrate(baseline_rows, "stopped_vehicles", start, end)
        cand_stopped = integrate(candidate_rows, "stopped_vehicles", start, end)
        ttt_delta, ttt_pct = delta(base_ttt, cand_ttt)
        stopped_delta, stopped_pct = delta(base_stopped, cand_stopped)
        segment_payload.append(
            {
                "segment": name,
                "time": label,
                "baseline_ttt": base_ttt,
                "candidate_ttt": cand_ttt,
                "ttt_delta": ttt_delta,
                "ttt_delta_pct": ttt_pct,
                "baseline_stopped": base_stopped,
                "candidate_stopped": cand_stopped,
                "stopped_delta": stopped_delta,
                "stopped_delta_pct": stopped_pct,
            }
        )
        lines.append(
            f"| {name} | {label} | {base_ttt:.3f} | {cand_ttt:.3f} | {ttt_delta:+.3f} | {ttt_pct:+.3f}% | "
            f"{base_stopped:.3f} | {cand_stopped:.3f} | {stopped_pct:+.3f}% |"
        )

    if action_rows:
        lines.extend(
            [
                "",
                "## Candidate Action Summary",
                "",
                "| Lever | Min | Mean | Max |",
                "|---|---:|---:|---:|",
            ]
        )
        for label, triple in [
            ("VSL speed (kph)", action_stat(action_rows, "vsl", "speed_kph")),
            ("Ramp green (s)", action_stat(action_rows, "ramp_meter", "green_sec")),
            ("Ramp rate field (vph)", action_stat(action_rows, "ramp_meter", "rate_vph")),
            ("Signal major green (s)", action_stat(action_rows, "signal", "major_green")),
            ("Signal minor green (s)", action_stat(action_rows, "signal", "minor_green")),
            ("Offset (s)", action_stat(action_rows, "signal", "offset")),
        ]:
            lines.append(f"| {label} | {triple[0]:.3f} | {triple[1]:.3f} | {triple[2]:.3f} |")

    if decision_walls:
        lines.extend(
            [
                "",
                f"Decision wall time: average {sum(decision_walls) / len(decision_walls):.3f} s, max {max(decision_walls):.3f} s.",
            ]
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The higher demand produced a stronger residual-congestion case. The candidate lowered total vehicle-hours and final accumulation, with the clearest TTT benefit in recovery/tail. Stopped vehicle-hours improved overall, but the final stopped count is slightly worse, so the controller is still shifting queue timing/location rather than fully discharging the network.",
        ]
    )

    out_md = Path(args.out_md)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "ok",
                "out_md": str(out_md),
                "baseline": base,
                "candidate": cand,
                "segments": segment_payload,
                "decision_wall_avg_sec": sum(decision_walls) / len(decision_walls) if decision_walls else 0.0,
                "decision_wall_max_sec": max(decision_walls) if decision_walls else 0.0,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
