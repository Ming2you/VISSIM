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
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evaluation.controllers import action_csv_schema  # noqa: E402


def fnum(value: object, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def histogram(values: list[float], ndigits: int = 1) -> dict[float, int]:
    out: dict[float, int] = {}
    for v in values:
        key = round(v, ndigits)
        out[key] = out.get(key, 0) + 1
    return dict(sorted(out.items()))


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
        diag = payload.get("diagnostics") or {}
        ramp = {k: fnum(v) for k, v in (payload.get("ramp_metering") or {}).items()}
        vsl_all = {k: fnum(v) for k, v in (payload.get("vsl") or {}).items()}
        # 세그먼트 VSL 을 내는 컨트롤러(pstack-flagship segvsl)는 __seg 키를 쓰고,
        # 링크 VSL 만 내는 컨트롤러(stackelberg)는 FW_E/FW_W 키만 쓴다. 후자를
        # "채널 없음"으로 세면 활성 0 으로 잘못 보고되므로 있는 쪽을 제어 채널로 삼는다.
        vsl_link = {k: v for k, v in vsl_all.items() if "__seg" not in k}
        vsl_seg = {k: v for k, v in vsl_all.items() if "__seg" in k} or vsl_link
        metering_on = [k for k, v in ramp.items() if v < ramp_capacity_vph - tol]
        vsl_on = [k for k, v in vsl_seg.items() if v < vsl_anchor_kph - tol]
        steps.append(
            {
                "sim_sec": sim_sec,
                "N_UF_star": fnum(payload.get("N_UF_star")),
                "N_P_star": fnum(payload.get("N_P_star")),
                # 리더가 유입을 실제로 고른 값과 그 탐색 상한. 둘이 같으면
                # 리더 목적함수가 과잉 유입을 벌하지 않는다는 신호다.
                "N_UF_applied": fnum(diag.get("leader_pfo_incumbent_N_UF_star")),
                "N_UF_raw": fnum(diag.get("leader_pfo_incumbent_raw_N_UF_star")),
                "N_UF_min": fnum(diag.get("N_UF_min")),
                "N_UF_max": fnum(diag.get("N_UF_max")),
                "N_UF_clipped": fnum(diag.get("leader_pfo_incumbent_N_UF_clipped")),
                # 감독자가 리더 해 대신 PFO 로 기권한 스텝. 이때는 리더 진단이 없어
                # N_UF_* 가 0 으로 남으므로 상한 고착 통계에서 빼야 한다.
                "sup_pick_pfo": fnum(diag.get("sup_pick_pfo")),
                "leader_diag_present": "leader_pfo_incumbent_N_UF_star" in diag,
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
        "vsl_channels": max((len(s["vsl_seg"]) for s in steps), default=0),
        "vsl_active_channel_fraction": (
            sum(s["vsl_active_count"] for s in steps) / len(vsl_values) if vsl_values else 0.0
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
        "N_UF_applied_histogram": histogram([s["N_UF_applied"] for s in steps]),
        "N_UF_max_histogram": histogram([s["N_UF_max"] for s in steps]),
        "leader_steps": sum(1 for s in steps if s["leader_diag_present"]),
        "sup_pick_pfo_steps": sum(1 for s in steps if s["sup_pick_pfo"] >= 1.0),
        "N_UF_at_search_upper_bound_steps": sum(
            1 for s in steps if s["N_UF_max"] > 0 and abs(s["N_UF_applied"] - s["N_UF_max"]) <= tol
        ),
        "N_UF_raw_above_upper_bound_steps": sum(
            1 for s in steps if s["N_UF_max"] > 0 and s["N_UF_raw"] > s["N_UF_max"] + tol
        ),
        "steps": steps,
    }


def applied_actions(action_csv: Path, start: float, end: float) -> dict[str, object]:
    """러너가 실제로 VISSIM 에 인가한 action 행을 종류별로 센다.

    VSL/램프가 앵커에 붙어 있어도 signal 행이 있으면 도시 신호 채널은 살아 있다.
    무제어 arm 은 signal 행을 내지 않아 SC 가 VISSIM 자체 계획으로 돈다 - 그 차이를
    "제어 없음"으로 뭉뚱그리면 안 되므로 따로 센다.
    """
    if not action_csv.exists():
        return {"present": False}
    rows = [r for r in read_csv(action_csv) if start <= fnum(r.get("sim_sec")) <= end]
    kinds: dict[str, int] = {}
    signal_plans: dict[str, int] = {}
    signal_scs: set[str] = set()
    for row in rows:
        kind = (row.get("kind") or "").strip()
        kinds[kind] = kinds.get(kind, 0) + 1
        if kind == "signal":
            signal_scs.add((row.get("sc_no") or "").strip())
            # N4-0. v3 은 축 2열, v4 는 현시 4열이다. 헤더로 세대를 가려 읽는다.
            fields = (
                action_csv_schema.PHASE_GREEN_FIELDS
                if action_csv_schema.row_is_v4(row)
                else action_csv_schema.LEGACY_AXIS_GREEN_FIELDS
            )
            greens = "/".join(f"{fnum(row.get(field)):.1f}" for field in fields)
            plan = f"{greens}/{fnum(row.get('offset')):.1f}"
            signal_plans[plan] = signal_plans.get(plan, 0) + 1
    return {
        "present": True,
        "rows_in_window": len(rows),
        "rows_by_kind": dict(sorted(kinds.items())),
        "signal_sc_nos": sorted(signal_scs),
        "signal_plan_histogram": dict(sorted(signal_plans.items())),
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


METRIC_ROWS = [
    ("ttt_veh_h", "TTT (veh-h)", "낮을수록 좋다"),
    ("stopped_veh_h", "정지 차량-시간 (veh-h)", "낮을수록 좋다"),
    ("mean_speed_kph", "평균속도 전체 (km/h)", "높을수록 좋다"),
    ("freeway_mean_speed_kph", "평균속도 freeway (km/h)", "높을수록 좋다"),
    ("urban_veh_h", "urban veh-h", "구성"),
    ("freeway_veh_h", "freeway veh-h", "구성"),
    ("ramp_veh_h", "ramp veh-h", "구성"),
    ("peak_total_veh", "최대 재차량 (veh)", "낮을수록 좋다"),
    ("peak_stopped_veh", "최대 정지대수 (veh)", "낮을수록 좋다"),
    ("final_total_veh", "창 종료시 재차량 (veh)", "낮을수록 좋다"),
]


def fmt(value: object, digits: int = 2) -> str:
    if value is None:
        return "—"
    if isinstance(value, float) and math.isnan(value):
        return "—"
    if isinstance(value, (int, float)):
        return f"{value:,.{digits}f}"
    return str(value)


def render_markdown(result: dict, labels: list[str]) -> str:
    arms = result["arms"]
    start, end = result["window_sec"]
    lines: list[str] = []
    lines.append(f"<!-- 자동 생성: scripts/analyze_new_baseline_ab_20260801.py, 분석창 {start:.0f}-{end:.0f} s -->")
    lines.append("")

    lines.append("### 성능 지표 (분석창 시간적분)")
    lines.append("")
    header = "| 지표 | " + " | ".join(labels) + " | 방향 |"
    lines.append(header)
    lines.append("|---" * (len(labels) + 2) + "|")
    for key, name, direction in METRIC_ROWS:
        cells = [fmt(arms[a].get("state", {}).get(key)) for a in labels]
        lines.append(f"| {name} | " + " | ".join(cells) + f" | {direction} |")
    lines.append("")

    base = labels[0]
    if len(labels) > 1:
        lines.append(f"### 기준선({base}) 대비 변화")
        lines.append("")
        lines.append("| 지표 | " + " | ".join(f"{a} Δ | {a} Δ%" for a in labels[1:]) + " |")
        lines.append("|---" * (1 + 2 * (len(labels) - 1)) + "|")
        for key, name, _ in METRIC_ROWS:
            cells: list[str] = []
            for a in labels[1:]:
                d = arms[a].get("vs_baseline", {}).get(key, {})
                cells.append(fmt(d.get("delta"), 3))
                cells.append(fmt(d.get("delta_pct"), 3))
            lines.append(f"| {name} | " + " | ".join(cells) + " |")
        lines.append("")

    lines.append("### 세그먼트별 평균 밀도 (veh/km/lane) · 평균속도 (km/h)")
    lines.append("")
    seg_ids = sorted({s for a in labels for s in arms[a].get("segments", {})})
    lines.append("| 세그먼트 | " + " | ".join(f"{a} 밀도 | {a} 속도" for a in labels) + " |")
    lines.append("|---" * (1 + 2 * len(labels)) + "|")
    for seg in seg_ids:
        cells = []
        for a in labels:
            entry = arms[a].get("segments", {}).get(seg, {})
            cells.append(fmt(entry.get("mean_density_veh_km_lane"), 3))
            cells.append(fmt(entry.get("mean_speed_kph"), 2))
        lines.append(f"| {seg} | " + " | ".join(cells) + " |")
    lines.append("")

    lines.append("### 결정 성공 · 제어 활성화")
    lines.append("")
    rows = [
        ("runlog", "decisions_ok", "DECISIONS_OK"),
        ("runlog", "decisions_failed", "DECISIONS_FAILED"),
        ("runlog", "run_mode", "RUN_MODE"),
        ("control", "decision_steps", "분석창 내 결정 스텝"),
        ("control", "metering_active_steps", "metering_active_steps"),
        ("control", "vsl_active_steps", "vsl_active_steps"),
        ("control", "vsl_channels", "VSL 채널 수"),
        ("control", "vsl_active_channel_fraction", "VSL 활성 채널 비율"),
        ("control", "ramp_min_vph_overall", "램프 최소 방류율 (vph)"),
        ("control", "N_UF_star_min", "N_UF_star 최소"),
        ("control", "N_UF_star_max", "N_UF_star 최대"),
        ("control", "leader_steps", "리더 해가 나온 스텝"),
        ("control", "sup_pick_pfo_steps", "감독자가 PFO 로 기권한 스텝"),
        ("control", "N_UF_at_search_upper_bound_steps", "N_UF 탐색 상한 고착 스텝"),
        ("control", "N_UF_raw_above_upper_bound_steps", "N_UF 원값이 상한 초과한 스텝"),
        ("runlog", "decision_wall_sec_mean", "결정 1회 평균 wall (s)"),
        ("runlog", "decision_wall_sec_total", "결정 총 wall (s)"),
    ]
    lines.append("| 항목 | " + " | ".join(labels) + " |")
    lines.append("|---" * (len(labels) + 1) + "|")
    for section, key, name in rows:
        cells = [fmt(arms[a].get(section, {}).get(key)) for a in labels]
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    lines.append("")

    for a in labels:
        ctl = arms[a].get("control")
        if not ctl:
            continue
        lines.append(f"### {a} 값 분포")
        lines.append("")
        lines.append(f"- VSL 값 히스토그램 (세그먼트 채널): `{ctl.get('vsl_value_histogram')}`")
        lines.append(f"- 램프 방류율 히스토그램: `{ctl.get('ramp_value_histogram')}`")
        lines.append(f"- N_UF_star 히스토그램: `{ctl.get('N_UF_star_histogram')}`")
        lines.append(f"- 리더가 고른 N_UF 히스토그램: `{ctl.get('N_UF_applied_histogram')}`")
        lines.append(f"- N_UF 탐색 상한 히스토그램: `{ctl.get('N_UF_max_histogram')}`")
        lines.append("")

    lines.append("### 실제 인가된 action 행 (분석창)")
    lines.append("")
    lines.append("| 항목 | " + " | ".join(labels) + " |")
    lines.append("|---" * (len(labels) + 1) + "|")
    for key, name in (
        ("rows_by_kind", "종류별 행 수"),
        ("signal_sc_nos", "도시 신호 SC"),
        ("signal_plan_histogram", "신호안(major/minor/offset)"),
    ):
        cells = [f"`{arms[a].get('applied', {}).get(key)}`" for a in labels]
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--extra-run-dir", action="append", default=[],
                    help="arm 산출물을 추가로 찾을 디렉터리. 무제어 기준선이 다른 배치에 있을 때 쓴다.")
    ap.add_argument("--arm", action="append", required=True,
                    help="label=run_name 형식. 첫 arm 이 기준(baseline)이다.")
    ap.add_argument("--start-sec", type=float, required=True)
    ap.add_argument("--end-sec", type=float, required=True)
    ap.add_argument("--ramp-capacity-vph", type=float, default=1800.0)
    ap.add_argument("--vsl-anchor-kph", type=float, default=120.0)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-md", default="", help="보고서에 붙일 표 조각을 마크다운으로 쓴다.")
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    search_dirs = [run_dir] + [Path(d) for d in args.extra_run_dir]

    def locate(filename: str) -> Path:
        """arm 산출물을 search_dirs 순서로 찾는다. 없으면 run_dir 경로를 돌려준다."""
        for base in search_dirs:
            candidate = base / filename
            if candidate.exists():
                return candidate
        return run_dir / filename

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
        state = locate(f"state_{name}.csv")
        segs = locate(f"bottleneck_segments_{name}.csv")
        decisions = locate(f"decisions_{name}")
        runlog = locate(f"runlog_{name}.txt")
        entry: dict[str, object] = {"run_name": name, "state_csv": str(state)}
        if state.exists():
            entry["state"] = state_metrics(read_csv(state), args.start_sec, args.end_sec)
        if segs.exists():
            entry["segments"] = segment_metrics(read_csv(segs), args.start_sec, args.end_sec)
        if decisions.exists():
            entry["control"] = control_activation(
                decisions, args.start_sec, args.end_sec, args.ramp_capacity_vph, args.vsl_anchor_kph
            )
        entry["applied"] = applied_actions(locate(f"action_{name}.csv"), args.start_sec, args.end_sec)
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
    if args.out_md:
        md = Path(args.out_md)
        md.parent.mkdir(parents=True, exist_ok=True)
        md.write_text(render_markdown(result, [a for a, _ in arms]), encoding="utf-8")
        print(f"WROTE {md}")
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
