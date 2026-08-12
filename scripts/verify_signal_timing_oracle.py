#!/usr/bin/env python3
# v3 N4-6 - 실 런의 readback 로그와 전달된 계획을 대조해 D-core 판정을 낸다
"""Run the signal timing oracle over a run's artifacts and emit a verdict.

    python scripts/verify_signal_timing_oracle.py \
        --run-dir evaluation/runs/<run>/<hash>/<attempt> \
        --out outputs/signal_timing_oracle_<run>.json

`--run-dir` 은 `decisions/signal_readback.csv` 와 action 로그 CSV 를 담은 폴더다.
둘 중 없는 것이 있으면 그 게이트는 **PASS 가 아니라** `NOT_EVALUATED` 로 남고,
무엇이 있어야 판정할 수 있는지가 `needs` 에 적힌다.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Sequence

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from evaluation.controllers import action_csv_schema  # noqa: E402
from evaluation.controllers import signal_group_plan  # noqa: E402
from evaluation.controllers import signal_timing_oracle  # noqa: E402
from evaluation.controllers.vissim_stackelberg_adapter import (  # noqa: E402
    signal_group_action_rows,
)


DEFAULT_PLAN = REPO / "outputs" / "signal_group_actuation_plan_v3.json"


def simulated_action_rows(
    plan_table: dict[str, Any], major_green: float, minor_green: float, offset: float = 0.0
) -> list[dict[str, Any]]:
    """실 런 없이 run-free 게이트를 재기 위해, 어댑터와 **같은 경로**로 행을 만든다.

    이것은 런의 대체물이 아니다. readback 게이트는 여전히 NOT_EVALUATED 로 남는다.
    여기서 얻는 것은 계획 자체의 성질(동시녹색·주기 wrap·경계 양자화·최소녹색)뿐이다.
    """
    rows: list[dict[str, Any]] = []
    for sc_no in sorted((plan_table.get("controllers") or {}), key=int):
        node = (plan_table.get("controllers") or {})[str(sc_no)]
        # N4-6. 계획이 4현시가 됐으므로 축 인자 두 개를 그 SC 가 **켤 수 있는 현시**에
        # 번갈아 편다. `major_maps_to` 와 그 짝에만 놓으면 어댑터가 fail-closed 로 죽는다.
        # 현시 수를 여기 적지 않는다 - SC107·108·109 는 셋이고 나머지는 넷이다.
        live = tuple(
            phase
            for phase in signal_group_plan.MODEL_PHASES
            if (node.get("phase_signal_groups") or {}).get(phase)
            and float((node.get("axis_green_sec") or {}).get(phase, 0.0)) > 0.0
        )
        values = (float(major_green), float(minor_green))
        phase_greens = {phase: 0.0 for phase in signal_group_plan.MODEL_PHASES}
        for index, phase in enumerate(live):
            phase_greens[phase] = values[index % 2]
        signal_row: dict[str, Any] = {
            "sim_sec": "0", "kind": "signal", "id": f"SC{sc_no}", "sc_no": sc_no,
            "offset": str(offset), "green_sec": "", "dsd_no": "", "link": "",
        }
        for phase, field in zip(
            signal_group_plan.MODEL_PHASES, action_csv_schema.PHASE_GREEN_FIELDS
        ):
            signal_row[field] = str(phase_greens[phase])
        rows.append(signal_row)
        for row in signal_group_action_rows(
            plan_table, sc_no=int(sc_no), phase_greens=phase_greens,
            offset=offset, metadata="simulated",
        ):
            simulated = {key: str(value) for key, value in row.items()}
            simulated["sim_sec"] = "0"
            rows.append(simulated)
    return rows


def read_csv_rows(path: Path | None) -> list[dict[str, Any]] | None:
    if path is None or not Path(path).is_file():
        return None
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def find_readback(run_dir: Path) -> Path | None:
    candidate = Path(run_dir) / "decisions" / "signal_readback.csv"
    return candidate if candidate.is_file() else None


def find_action_log(run_dir: Path) -> Path | None:
    """러너의 action 로그. 파일명은 런마다 다르니 헤더로 고른다."""
    for candidate in sorted(Path(run_dir).glob("*.csv")):
        try:
            with candidate.open(encoding="utf-8-sig", newline="") as handle:
                header = handle.readline().strip()
        except OSError:
            continue
        # N4-0. v3(축 2열)·v4(현시 4열) 두 세대의 로그를 다 고른다. 옛 런을 읽는
        # 도구이기도 하므로 v4 만 고르게 하면 저장소의 로그 8천여 개를 못 읽는다.
        for prefix in (
            "sim_sec," + ",".join(action_csv_schema.ACTION_CSV_FIELDS[:8]),
            "sim_sec," + ",".join(action_csv_schema.LEGACY_ACTION_CSV_FIELDS[:8]),
        ):
            if header.startswith(prefix):
                return candidate
    return None


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Signal timing oracle (v3 N4-6 D-core)")
    parser.add_argument("--run-dir", type=Path, default=None)
    parser.add_argument("--readback-csv", type=Path, default=None)
    parser.add_argument("--action-log-csv", type=Path, default=None)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--min-green-sec", type=float, default=None)
    parser.add_argument("--simulate-major-green", type=float, default=None)
    parser.add_argument("--simulate-minor-green", type=float, default=None)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    readback_path = args.readback_csv
    action_path = args.action_log_csv
    if args.run_dir is not None:
        if readback_path is None:
            readback_path = find_readback(args.run_dir)
        if action_path is None:
            action_path = find_action_log(args.run_dir)

    plan_table = json.loads(Path(args.plan).read_text(encoding="utf-8")) if Path(args.plan).is_file() else {}
    action_data = read_csv_rows(action_path)
    simulated = False
    if not action_data and args.simulate_major_green is not None and args.simulate_minor_green is not None:
        action_data = simulated_action_rows(
            plan_table, args.simulate_major_green, args.simulate_minor_green
        )
        simulated = True
    report = signal_timing_oracle.evaluate(
        plan_table,
        action_data,
        read_csv_rows(readback_path),
        min_green_sec=args.min_green_sec,
    )
    report["sources"] = {
        "plan": str(args.plan),
        "readback_csv": str(readback_path) if readback_path else "",
        "action_log_csv": str(action_path) if action_path else "",
        "action_rows_simulated": simulated,
    }
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.out is not None:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8", newline="\n")

    print("status=%s" % report["status"])
    for gate in report["gates"]:
        print("  %-28s %-14s %s" % (gate["name"], gate["status"], gate["detail"]))
        if gate["needs"]:
            print("      needs: %s" % gate["needs"])
    return 0 if report["status"] == signal_timing_oracle.PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
