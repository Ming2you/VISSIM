#!/usr/bin/env python3
# v3 N4-5 - inpx 가 실제로 읽는 .sig 에서 SG 단위 액추에이션 계획과 충돌 쌍을 뽑는 생산자
"""Derive the per-signal-group actuation plan the runner drives from.

## 출처가 왜 inpx 인가

VISSIM 이 SC 마다 어떤 프로그램을 도는지는 `.inpx` 의 `signalController/@supplyFile2` 하나가
정한다. 모델의 `compile_fixed_signal_schedules` 도 같은 것을 읽는다.

`outputs/signal_group_timing_v3.json` 이 **파일명 번호**로 `.sig` 를 고르던 동안 실측(2026-08-10)
4/15 SC 에서 그 선택이 inpx 와 달랐다.

    SC5  timing=test-bed5.sig(140 s)  inpx=test-bed7.sig(160 s)
    SC6  timing=test-bed6.sig(100 s)  inpx=test-bed9.sig(160 s)
    SC11 timing=test-bed11.sig(160 s) inpx=test-bed3.sig(150 s)
    SC12 timing=test-bed12.sig(150 s) inpx=test-bed5.sig(140 s)

표 생산자가 inpx 를 읽도록 고쳐 지금은 일치한다. 교차검사는 지우지 않고 남긴다 -
`timing_table_disagreements` 가 비어 있는 것이 두 출처가 같은 프로그램을 본다는 증거다.

## 무엇이 나오는가

  outputs/signal_group_actuation_plan_v3.json    어댑터가 읽어 action CSV 의 signal_sg 행을 만든다
  evaluation/generated/<config>_sgplan.vbs       러너가 ExecuteGlobal 해 계약을 검사한다

러너가 계약(기대 SG 집합·충돌 쌍)을 **행이 아니라 config** 에서 받는 것이 요점이다.
행이 자기 자신을 인증하면 fail-closed 가 아니다.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from evaluation.controllers import plant_cycle, signal_group_plan  # noqa: E402
from evaluation.controllers.fixed_signal_schedule import (  # noqa: E402
    compile_fixed_signal_schedules,
)


SCHEMA_VERSION = "signal-group-actuation-plan-v3"
VBS_SCHEMA = 1

# 러너 원문에서 읽는다. 숫자를 복사해 두면 러너가 바뀌었을 때 조용히 어긋나는데, 그 어긋남은
# 여기서 끝나지 않는다 - 이 두 값이 그대로 계획 주기(`plan_cycle_sec`)에 실려 action CSV 로
# 나가고, 러너는 그것을 자기 축 주기와 대조해(:1453) 다르면 그 SC 를 통째로 거부한다.
AMBER_SEC, ALL_RED_SEC = plant_cycle.runner_clearance_sec()

DEFAULT_NETWORK = REPO / "network" / "real_world_gaepo_modi" / "modi_eval_rw_control.inpx"
DEFAULT_MOVEMENT_MAP = REPO / "outputs" / "movement_signal_group_map_v3.json"
DEFAULT_TIMING = REPO / "outputs" / "signal_group_timing_v3.json"
DEFAULT_OUT = REPO / "outputs" / "signal_group_actuation_plan_v3.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _signal_group_ids(network_path: Path) -> dict[str, list[str]]:
    """inpx 가 SC 마다 선언한 SG 번호. 계획은 이 전부를 덮어야 한다."""
    root = ET.parse(Path(network_path)).getroot()
    table: dict[str, list[str]] = {}
    for controller in root.findall(".//signalControllers/signalController"):
        node = f"SC{controller.get('no', '')}"
        table[node] = [
            str(group.get("no", ""))
            for group in controller.findall("./sgs/signalGroup")
        ]
    return table


def uncovered_signal_groups(
    node: str,
    window_counts: Mapping[str, int],
    native_green_sec: Mapping[str, float],
) -> list[str]:
    """계획이 **떨어뜨린** SG. native 에 녹색이 있는데 계획에는 창이 없는 것들이다.

    예전 식은 `sg_no not in window_counts` 였는데 `window_counts` 가 같은 sg_id 목록으로
    초기화되므로 구조적으로 항상 0 이었다 - 통과해도 아무것도 보장하지 않는 검사였다.
    native 가 영원히 적색인 SG 가 창 0 인 것은 정상이므로 여기서 세지 않는다.
    """
    return [
        f"{node}:{sg_no}"
        for sg_no, count in sorted(window_counts.items())
        if int(count) == 0 and float(native_green_sec.get(sg_no, 0.0)) > 0.0
    ]


def _controlled_signals(mapping_path: Path) -> list[dict[str, Any]]:
    payload = json.loads(Path(mapping_path).read_text(encoding="utf-8-sig"))
    rows: list[dict[str, Any]] = []
    for item in payload.get("signals", []):
        sc_no = int(item.get("sc_no", 0))
        if sc_no <= 0:
            continue
        maps_to = str(item.get("major_maps_to", "p2")).strip().lower()
        if maps_to not in signal_group_plan.MODEL_PHASES:
            maps_to = "p2"
        rows.append({"node_id": str(item.get("id", f"SC{sc_no}")), "sc_no": sc_no, "major_maps_to": maps_to})
    if not rows:
        raise SystemExit(f"{mapping_path} declares no controlled signals")
    return rows


def derive(
    network_path: Path,
    mapping_path: Path,
    movement_map_path: Path,
    timing_path: Path | None = DEFAULT_TIMING,
) -> dict[str, Any]:
    signals = _controlled_signals(Path(mapping_path))
    nodes = [row["node_id"] for row in signals]
    movement_map = json.loads(Path(movement_map_path).read_text(encoding="utf-8"))
    schedules, errors = compile_fixed_signal_schedules(Path(network_path), nodes)
    missing = [node for node in nodes if node not in schedules]
    if missing:
        raise SystemExit(f"no compiled schedule for {missing}: {errors}")

    declared = _signal_group_ids(Path(network_path))
    controllers: dict[str, Any] = {}
    total_groups = 0
    total_windows = 0
    total_conflicts = 0
    total_violations = 0
    uncovered = 0
    never_green: list[str] = []

    for row in signals:
        node = row["node_id"]
        schedule = schedules[node]
        entry = (movement_map.get("controllers") or {}).get(node)
        if entry is None:
            raise SystemExit(f"{node} is controlled but absent from {movement_map_path}")
        sg_ids = declared.get(node, [])
        if not sg_ids:
            raise SystemExit(f"{node} declares no signal groups in {network_path}")
        plan = signal_group_plan.build_node_plan(
            node_id=node,
            program=schedule.program,
            phase_signal_groups=entry.get("phase_signal_groups") or {},
            signal_group_ids=sg_ids,
        )
        payload = signal_group_plan.node_plan_to_json(plan)
        payload["sc_no"] = row["sc_no"]
        payload["major_maps_to"] = row["major_maps_to"]
        payload["native_green_sec"] = {
            sg_no: sum(
                end - start
                for start, end in _native_windows(schedule.program, sg_no)
            )
            for sg_no in sg_ids
        }
        controllers[str(row["sc_no"])] = payload

        total_groups += len(sg_ids)
        total_windows += sum(plan.window_counts.get(sg_no, 0) for sg_no in sg_ids)
        total_conflicts += len(plan.conflict_pairs)
        uncovered += len(
            uncovered_signal_groups(node, plan.window_counts, payload["native_green_sec"])
        )
        never_green.extend(
            f"{node}:{sg_no}"
            for sg_no in sg_ids
            if float(payload["native_green_sec"].get(sg_no, 0.0)) <= 0.0
        )
        # 계획이 스스로 충돌을 만들지 않는지, 대표 지시값으로 확인한다.
        windows = signal_group_plan.plan_windows(
            plan,
            phase_greens={
                phase: (60.0 if plan.phase_signal_groups.get(phase) else 0.0)
                for phase in signal_group_plan.MODEL_PHASES
            },
            phase_order=signal_group_plan.phase_layout_order(row["major_maps_to"]),
            amber_sec=AMBER_SEC,
            all_red_sec=ALL_RED_SEC,
        )
        total_violations += len(
            signal_group_plan.conflict_violations(windows, plan.conflict_pairs)
        )

    disagreements = sorted(
        node
        for node, entry in (movement_map.get("controllers") or {}).items()
        if not (entry.get("timing_cross_check") or {}).get("agrees", True)
    )

    table: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "amber_sec": AMBER_SEC,
        "all_red_sec": ALL_RED_SEC,
        "source": {
            "network": str(Path(network_path)),
            "network_sha256": _sha256(Path(network_path)),
            "control_mapping": str(Path(mapping_path)),
            "control_mapping_sha256": _sha256(Path(mapping_path)),
            "movement_signal_group_map": str(Path(movement_map_path)),
            "movement_signal_group_map_sha256": _sha256(Path(movement_map_path)),
            "program_source": "inpx supplyFile2 (not signal_group_timing_v3.json)",
        },
        "controllers": controllers,
        "timing_table_disagreements": disagreements,
        "counts": {
            "controllers": len(controllers),
            "signal_groups": total_groups,
            "planned_windows": total_windows,
            "uncovered_signal_groups": uncovered,
            "never_green_signal_groups": len(never_green),
            "conflict_pairs": total_conflicts,
            "conflict_violations": total_violations,
        },
        "never_green_signal_groups": sorted(never_green),
    }
    table["status"] = "PASS" if uncovered == 0 and total_violations == 0 else "FAIL"
    if timing_path is not None and Path(timing_path).is_file():
        table["source"]["signal_group_timing_v3_sha256"] = _sha256(Path(timing_path))
    return table


def _native_windows(program, sg_no: str) -> tuple[tuple[float, float], ...]:
    timeline = program.sg_timelines.get(str(sg_no))
    if timeline is None:
        return ()
    return tuple(
        (float(interval.start_sec), float(interval.end_sec))
        for interval in timeline.intervals
        if interval.state == "GREEN"
    )


def expected_token_list(table: Mapping[str, Any]) -> list[str]:
    """`sc:sg:window_count` 토큰. 러너의 커버리지 게이트가 이걸 쓴다."""
    tokens: list[str] = []
    for sc_no, plan in sorted(table["controllers"].items(), key=lambda item: int(item[0])):
        counts = plan["window_counts"]
        for sg_no in sorted(counts, key=lambda value: (int(value) if str(value).isdigit() else 1 << 30, value)):
            tokens.append(f"{int(sc_no)}:{sg_no}:{int(counts[sg_no])}")
    return tokens


def conflict_token_list(table: Mapping[str, Any]) -> list[str]:
    """`sc:a-b` 토큰. 이 쌍은 어떤 시각에도 동시에 GREEN 이면 안 된다."""
    tokens: list[str] = []
    for sc_no, plan in sorted(table["controllers"].items(), key=lambda item: int(item[0])):
        for first, second in plan["conflict_pairs"]:
            tokens.append(f"{int(sc_no)}:{first}-{second}")
    return tokens


def action_windows(
    table: Mapping[str, Any], sc_no: int, phase_greens: Mapping[str, float]
) -> tuple[signal_group_plan.PlanWindow, ...]:
    """어댑터가 쓰는 것과 같은 경로로 한 SC 의 녹색창을 만든다."""
    payload = table["controllers"][str(int(sc_no))]
    plan = signal_group_plan.node_plan_from_json(payload)
    return signal_group_plan.plan_windows(
        plan,
        phase_greens=phase_greens,
        phase_order=signal_group_plan.phase_layout_order(str(payload["major_maps_to"])),
        amber_sec=float(table.get("amber_sec", AMBER_SEC)),
        all_red_sec=float(table.get("all_red_sec", ALL_RED_SEC)),
    )


def _long_string_assignment(name: str, value: str, chunk_size: int = 600) -> list[str]:
    chunks = [value[index : index + chunk_size] for index in range(0, len(value), chunk_size)] or [""]
    lines: list[str] = []
    for index, chunk in enumerate(chunks):
        prefix = f"{name} = " if index == 0 else "    "
        suffix = " & _" if index < len(chunks) - 1 else ""
        lines.append(f'{prefix}"{chunk}"{suffix}')
    return lines


def render_vbs(table: Mapping[str, Any], plan_sha256: str = "") -> str:
    payload = json.dumps(table, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = plan_sha256 or hashlib.sha256(payload.encode("utf-8")).hexdigest()
    lines = [
        "' Generated by scripts/derive_signal_group_actuation_plan.py - do not edit by hand.",
        "' N4-5: the runner drives signal groups from the delivered plan, not from the name rule.",
        f"RW_SIGNAL_SG_PLAN_SCHEMA = {VBS_SCHEMA}",
        f'RW_SIGNAL_SG_PLAN_SOURCE_SHA256 = "{digest}"',
    ]
    lines.extend(_long_string_assignment("RW_SIGNAL_SG_EXPECTED", ",".join(expected_token_list(table))))
    lines.extend(_long_string_assignment("RW_SIGNAL_SG_CONFLICTS", ";".join(conflict_token_list(table))))
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Derive the per-signal-group actuation plan")
    parser.add_argument("--network", type=Path, default=DEFAULT_NETWORK)
    parser.add_argument("--mapping", type=Path, default=None)
    parser.add_argument("--movement-map", type=Path, default=DEFAULT_MOVEMENT_MAP)
    parser.add_argument("--timing", type=Path, default=DEFAULT_TIMING)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--out-vbs", type=Path, default=None)
    # 러너의 sgplan 은 config 마다 형제 파일(<config>_sgplan.vbs)이라 config 를 하나
    # 더 붙일 때마다 형제 파일이 하나 더 필요하다. 그때 계획을 **다시 유도하면** 추적
    # 산출물을 덮어쓰게 되므로, 이미 있는 계획에서 형제 파일만 뽑는 길을 따로 둔다.
    # 실리는 sha 는 어댑터가 실제로 읽는 그 파일의 sha 다.
    parser.add_argument("--from-plan", type=Path, default=None)
    args = parser.parse_args(argv)

    if args.from_plan is not None:
        if args.out_vbs is None:
            parser.error("--from-plan requires --out-vbs")
        table = json.loads(Path(args.from_plan).read_text(encoding="utf-8"))
        if str(table.get("status")) != "PASS":
            print(f"refusing to render a sibling from a {table.get('status')} plan: {args.from_plan}")
            return 1
        args.out_vbs.parent.mkdir(parents=True, exist_ok=True)
        args.out_vbs.write_text(
            render_vbs(table, _sha256(Path(args.from_plan))), encoding="utf-8", newline="\n"
        )
        counts = table["counts"]
        print(
            "rendered=%s from=%s groups=%d windows=%d conflicts=%d"
            % (
                args.out_vbs,
                args.from_plan,
                counts["signal_groups"],
                counts["planned_windows"],
                counts["conflict_pairs"],
            )
        )
        return 0

    if args.mapping is None:
        parser.error("--mapping is required unless --from-plan is given")
    table = derive(args.network, args.mapping, args.movement_map, args.timing)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(table, ensure_ascii=False, indent=2) + "\n"
    args.out.write_text(text, encoding="utf-8", newline="\n")
    if args.out_vbs is not None:
        args.out_vbs.parent.mkdir(parents=True, exist_ok=True)
        args.out_vbs.write_text(render_vbs(table, _sha256(args.out)), encoding="utf-8", newline="\n")

    counts = table["counts"]
    print(
        "status=%s controllers=%d groups=%d windows=%d uncovered=%d never_green=%d "
        "conflicts=%d violations=%d"
        % (
            table["status"],
            counts["controllers"],
            counts["signal_groups"],
            counts["planned_windows"],
            counts["uncovered_signal_groups"],
            counts["never_green_signal_groups"],
            counts["conflict_pairs"],
            counts["conflict_violations"],
        )
    )
    if table["timing_table_disagreements"]:
        print(
            "signal_group_timing_v3.json disagrees with the inpx supply file for %s"
            % ", ".join(table["timing_table_disagreements"])
        )
    return 0 if table["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
