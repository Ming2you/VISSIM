#!/usr/bin/env python3
# N4-0 작업1 관문 - 실 .sig 15개를 전수 분석하고 4현시 150 s 재배분 가능성을 판정하는 생산자
"""Survey the 15 controlled VISSIG programs and dry-run the 4-phase 150 s target.

## 왜 재작성 전에 이 표가 먼저인가

목표 스펙은 주기 150 · dual-ring 4현시 · 현시 순서 major 직진 -> major 좌 -> minor 직진 ->
minor 좌 · clearance 3 s · green_min 20 s 다. 이 스펙이 성립하려면 네 현시 각각에
**차량이 실제로 지나는 이동류**가 있어야 한다.

`.sig` 만 읽으면 그것을 알 수 없다. SG 는 이름이 있고 녹색창이 있어도 `signalHead` 가
하나도 안 걸려 있으면 VISSIM 에서 차량에 아무 영향을 주지 않는다. 그래서 이 생산자는
`.sig` 와 `.inpx` 의 `signalHead` 를 **같이** 읽는다.

실측 결과는 스펙이 15 SC 전부에 그대로 서지 않는다는 것이다. 자세한 것은 출력 표와
`scripts/tests/test_survey_signal_programs.py` 에 수치로 박혀 있다.

## 출처

프로그램 선택은 `.inpx` 의 `signalController/@supplyFile2` + `@progNo` 하나뿐이다
(`evaluation/controllers/fixed_signal_schedule.py` 와 같은 경로). 파일명 끝자리로 고르면
SC5/6/11/12 에서 갈린다.

## 재배분 규칙

현시별 목표 녹색 = 그 현시에 속한 SG 들의 현 녹색 **평균**을, 유효녹색 총량이 138 s 가
되도록 비례 축소한 값이다. 평균을 쓰는 이유는 dual-ring 의 lead-lag 를 하나로 접기
때문이다 - 두 링이 같은 배리어 안에서 각각 총량 B 를 채우므로, 현시별 평균의 합은
자동으로 배리어 총량 B 를 보존한다. 주기가 이미 150 인 7 SC 에서는 축소율이 1.0 이라
절대 초까지 그대로 남는다.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "signal-program-survey-v1"

REPO = Path(__file__).resolve().parents[1]
DEFAULT_NETWORK = REPO / "network" / "real_world_gaepo_modi" / "modi_eval_rw_control.inpx"

# N4-0 목표 스펙 (계획서 커밋 9fa2668).
TARGET_CYCLE_SEC = 150.0
TARGET_PHASE_COUNT = 4
TARGET_CLEARANCE_SEC = 3.0
TARGET_LOST_SEC = TARGET_PHASE_COUNT * TARGET_CLEARANCE_SEC
TARGET_EFFECTIVE_GREEN_SEC = TARGET_CYCLE_SEC - TARGET_LOST_SEC
GREEN_MIN_SEC = 20.0
GREEN_MAX_SEC = TARGET_EFFECTIVE_GREEN_SEC - (TARGET_PHASE_COUNT - 1) * GREEN_MIN_SEC

PHASE_ORDER = ("major_through", "major_left", "minor_through", "minor_left")
PHASE_BY_MOVEMENT = {
    "EBT": "major_through",
    "WBT": "major_through",
    "EBL": "major_left",
    "WBL": "major_left",
    "NBT": "minor_through",
    "SBT": "minor_through",
    "NBL": "minor_left",
    "SBL": "minor_left",
}
# SC5 만 SG 가 24개다. 9-24 는 같은 SC 의 midblock 슬레이브로,
# 부모 SG = ((n-1) mod 8)+1 이다 (outputs/urban_follower_midblock_signal_mapping_20260731.md).
MAIN_SG_COUNT = 8


class SurveyError(RuntimeError):
    """Raised when a controller cannot be surveyed against the target spec."""


def phase_for_movement(name: str) -> str | None:
    """SG 이름을 목표 4현시 중 하나로 접는다. 차량 이동류가 아니면 None 이다."""
    return PHASE_BY_MOVEMENT.get(str(name or "").strip().upper())


def scale_to_total(values: Mapping[str, float], total: float) -> dict[str, float]:
    """현재 배분을 총량 ``total`` 로 비례 축소한다. 배리어 몫이 그대로 보존된다."""
    current = sum(float(value) for value in values.values())
    if current <= 0.0:
        raise SurveyError("cannot scale a distribution whose total is zero")
    factor = float(total) / current
    return {key: float(value) * factor for key, value in values.items()}


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _parse_sig():
    try:
        from plant.src.vissim_strict.signal_program import parse_sig
    except ModuleNotFoundError:
        plant_root = REPO / "plant"
        if str(plant_root) not in sys.path:
            sys.path.insert(0, str(plant_root))
        from src.vissim_strict.signal_program import parse_sig
    return parse_sig


def _controlled_sc_numbers(mapping_path: Path) -> list[int]:
    payload = json.loads(Path(mapping_path).read_text(encoding="utf-8-sig"))
    numbers = [int(item["sc_no"]) for item in payload.get("signals", []) if item.get("sc_no")]
    if not numbers:
        raise SurveyError(f"{mapping_path} declares no controlled signals")
    return numbers


def _supply_file(controller: ET.Element) -> str:
    raw = str(controller.get("supplyFile2") or "").strip()
    if not raw:
        raise SurveyError(f"SC{controller.get('no')} declares no supplyFile2")
    return Path(raw[6:] if raw.lower().startswith("#data#") else raw).name


def _head_counts(root: ET.Element) -> dict[int, dict[str, int]]:
    counts: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for head in root.findall(".//signalHeads/signalHead"):
        reference = str(head.get("sg", "")).split()
        if len(reference) >= 2:
            counts[int(reference[0])][reference[1]] += 1
    return counts


def _windows(timeline, state: str) -> list[list[float]]:
    return [
        [float(interval.start_sec), float(interval.end_sec)]
        for interval in timeline.intervals
        if interval.state == state
    ]


def _survey_controller(
    *,
    sc_no: int,
    controller: ET.Element,
    network_path: Path,
    heads: Mapping[str, int],
    parse_sig,
) -> dict[str, Any]:
    sig_name = _supply_file(controller)
    sig_path = Path(network_path).parent / sig_name
    prog_no = int(controller.get("progNo", "1"))
    program = parse_sig(sig_path, prog_no)

    declared = [
        (str(group.get("no", "")), str(group.get("name", "")))
        for group in controller.findall("./sgs/signalGroup")
    ]
    groups: list[dict[str, Any]] = []
    phase_greens: dict[str, list[float]] = {name: [] for name in PHASE_ORDER}
    phase_ids: dict[str, list[str]] = {name: [] for name in PHASE_ORDER}
    phase_heads: dict[str, int] = {name: 0 for name in PHASE_ORDER}

    for sg_id, sg_name in declared:
        timeline = program.sg_timelines.get(sg_id)
        if timeline is None:
            raise SurveyError(f"SC{sc_no} SG{sg_id} is declared in the inpx but absent from {sig_name}")
        green = _windows(timeline, "GREEN")
        green_sec = sum(end - start for start, end in green)
        head_count = int(heads.get(sg_id, 0))
        midblock_parent = (
            str((int(sg_id) - 1) % MAIN_SG_COUNT + 1)
            if sg_id.isdigit() and int(sg_id) > MAIN_SG_COUNT
            else None
        )
        phase = phase_for_movement(sg_name)
        groups.append(
            {
                "sg_id": sg_id,
                "name": sg_name,
                "phase": phase,
                "head_count": head_count,
                "green_sec": green_sec,
                "green_windows": green,
                "amber_windows": _windows(timeline, "AMBER"),
                "permanent_red": bool(timeline.permanent_red),
                "midblock_parent_sg": midblock_parent,
            }
        )
        # midblock 슬레이브는 부모 SG 를 따라가는 반복 등두다. 현시 평균에 넣으면
        # 같은 이동류를 두 번 세고 SC5 의 major 직진이 50 -> 61 s 로 부풀어 오른다.
        if phase is not None and midblock_parent is None:
            phase_greens[phase].append(green_sec)
            phase_ids[phase].append(sg_id)
            phase_heads[phase] += head_count

    phases = {
        name: {
            "sg_ids": phase_ids[name],
            "greens_sec": phase_greens[name],
            "mean_green_sec": (
                sum(phase_greens[name]) / len(phase_greens[name]) if phase_greens[name] else 0.0
            ),
            "head_count": phase_heads[name],
        }
        for name in PHASE_ORDER
    }

    means = {name: phases[name]["mean_green_sec"] for name in PHASE_ORDER}
    effective_green = sum(means.values())
    cycle = float(program.cycle_length_sec)
    lost = cycle - effective_green
    stages = lost / TARGET_CLEARANCE_SEC
    # 단계 수가 정수가 아니면 어떤 SG 가 단계 경계를 넘어 녹색을 이어간다는 뜻이다
    # (SC109 의 EBT 가 그렇다). 그런 프로그램은 현시 개념 자체가 성립하지 않는다.
    stage_count = int(round(stages)) if abs(stages - round(stages)) < 1e-9 else None

    target_greens = scale_to_total(means, TARGET_EFFECTIVE_GREEN_SEC)
    violations: list[str] = []
    for name in PHASE_ORDER:
        value = target_greens[name]
        if value < GREEN_MIN_SEC - 1e-9:
            violations.append(f"{name} green {value:.2f}s < green_min {GREEN_MIN_SEC:.0f}s")
        if value > GREEN_MAX_SEC + 1e-9:
            violations.append(f"{name} green {value:.2f}s > green_max {GREEN_MAX_SEC:.0f}s")

    target = {
        name: {
            "green_sec": target_greens[name],
            "delta_vs_native_sec": target_greens[name] - means[name],
            "head_count": phases[name]["head_count"],
        }
        for name in PHASE_ORDER
    }

    return {
        "sc_no": sc_no,
        "sig_file": sig_name,
        "sig_sha256": _sha256(sig_path),
        "prog_no": prog_no,
        "program_name": program.program_name,
        "cycle_sec": cycle,
        "program_offset_sec": float(program.program_offset_sec),
        "controller_offset_sec": float(controller.get("offset", "0") or 0.0),
        "signal_groups": groups,
        "phases": phases,
        "barrier_major_green_sec": means["major_through"] + means["major_left"],
        "barrier_minor_green_sec": means["minor_through"] + means["minor_left"],
        "effective_green_total_sec": effective_green,
        "implied_lost_sec": lost,
        "implied_stage_count": stage_count,
        "empty_target_phases": [name for name in PHASE_ORDER if phases[name]["head_count"] == 0],
        "target": target,
        "violations": violations,
    }


def survey(network_path: Path, mapping_path: Path) -> dict[str, Any]:
    """15개 제어 SC 의 현 프로그램과 4현시 목표 재배분을 한 표로 만든다."""

    parse_sig = _parse_sig()
    root = ET.parse(Path(network_path)).getroot()
    controllers = {
        int(element.get("no")): element
        for element in root.findall(".//signalControllers/signalController")
        if element.get("no")
    }
    heads = _head_counts(root)

    rows: list[dict[str, Any]] = []
    for sc_no in _controlled_sc_numbers(Path(mapping_path)):
        element = controllers.get(sc_no)
        if element is None:
            raise SurveyError(f"{network_path} declares no SC{sc_no}")
        rows.append(
            _survey_controller(
                sc_no=sc_no,
                controller=element,
                network_path=Path(network_path),
                heads=heads.get(sc_no, {}),
                parse_sig=parse_sig,
            )
        )

    violating = [row["sc_no"] for row in rows if row["violations"]]
    empty_phase = [row["sc_no"] for row in rows if row["empty_target_phases"]]
    table = {
        "schema_version": SCHEMA_VERSION,
        "source": {
            "network": str(Path(network_path)),
            "network_sha256": _sha256(Path(network_path)),
            "control_mapping": str(Path(mapping_path)),
            "control_mapping_sha256": _sha256(Path(mapping_path)),
            "program_source": "inpx supplyFile2 + progNo",
        },
        "target_spec": {
            "cycle_sec": TARGET_CYCLE_SEC,
            "phase_count": TARGET_PHASE_COUNT,
            "clearance_sec": TARGET_CLEARANCE_SEC,
            "lost_time_sec": TARGET_LOST_SEC,
            "effective_green_sec": TARGET_EFFECTIVE_GREEN_SEC,
            "green_min_sec": GREEN_MIN_SEC,
            "green_max_sec": GREEN_MAX_SEC,
            "phase_order": list(PHASE_ORDER),
        },
        "controllers": rows,
        "counts": {
            "controllers": len(rows),
            "signal_groups": sum(len(row["signal_groups"]) for row in rows),
            "signal_groups_without_head": sum(
                1 for row in rows for group in row["signal_groups"] if group["head_count"] == 0
            ),
            "controllers_violating_target": len(violating),
            "controllers_with_empty_phase": len(empty_phase),
        },
        "controllers_violating_target": violating,
        "controllers_with_empty_phase": empty_phase,
    }
    table["status"] = "PASS" if not violating and not empty_phase else "FAIL"
    return table


def render_markdown(table: Mapping[str, Any]) -> str:
    """전/후 대조를 사람이 읽는 표로 낸다. 접근로(SG) 단위까지 전수로 낸다."""
    spec = table["target_spec"]
    lines = [
        "# N4-0 작업1 - 실 `.sig` 15개 전수 분석과 4현시 재배분 시산",
        "",
        f"목표 스펙 — 주기 {spec['cycle_sec']:.0f} s · 현시 {spec['phase_count']}개 · "
        f"clearance {spec['clearance_sec']:.0f} s · 유효녹색 {spec['effective_green_sec']:.0f} s · "
        f"green_min {spec['green_min_sec']:.0f} s · green_max {spec['green_max_sec']:.0f} s",
        "",
        f"판정 — **{table['status']}**. "
        f"목표 위반 SC {table['counts']['controllers_violating_target']}개, "
        f"빈 현시를 가진 SC {table['counts']['controllers_with_empty_phase']}개, "
        f"등두 없는 SG {table['counts']['signal_groups_without_head']}/"
        f"{table['counts']['signal_groups']}개.",
        "",
        "## SC별 현 프로그램",
        "",
        "| SC | `.sig` | 주기 | SG | 단계 | major 배리어 | minor 배리어 | 유효녹색 | 손실 |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in table["controllers"]:
        stage = row["implied_stage_count"]
        lines.append(
            f"| {row['sc_no']} | {row['sig_file']} | {row['cycle_sec']:.0f} | "
            f"{len(row['signal_groups'])} | {stage if stage is not None else '비정수'} | "
            f"{row['barrier_major_green_sec']:.1f} | {row['barrier_minor_green_sec']:.1f} | "
            f"{row['effective_green_total_sec']:.1f} | {row['implied_lost_sec']:.1f} |"
        )

    lines += [
        "",
        "## 현시별 전/후 (초)",
        "",
        "| SC | major 직진 | major 좌 | minor 직진 | minor 좌 | 위반 |",
        "| ---: | --- | --- | --- | --- | --- |",
    ]
    for row in table["controllers"]:
        cells = []
        for name in PHASE_ORDER:
            native = row["phases"][name]["mean_green_sec"]
            after = row["target"][name]["green_sec"]
            mark = " ⚠등두0" if row["phases"][name]["head_count"] == 0 else ""
            cells.append(f"{native:.1f} → {after:.1f}{mark}")
        lines.append(
            f"| {row['sc_no']} | " + " | ".join(cells) + " | "
            + ("; ".join(row["violations"]) or "-") + " |"
        )

    lines += [
        "",
        "## 접근로(SG)별 전/후 (초)",
        "",
        "등두 0 인 SG 는 VISSIM 에서 차량에 닿지 않는다. 녹색을 줘도 처리량이 늘지 않는다.",
        "",
        "| SC | SG | 이름 | 현시 | 등두 | 현 녹색 | 목표 녹색 | 증감 |",
        "| ---: | ---: | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in table["controllers"]:
        for group in row["signal_groups"]:
            phase = group["phase"]
            if phase is None or group["midblock_parent_sg"] is not None:
                after = "-"
                delta = "-"
            else:
                value = row["target"][phase]["green_sec"]
                after = f"{value:.1f}"
                delta = f"{value - group['green_sec']:+.1f}"
            label = phase or "-"
            if group["midblock_parent_sg"] is not None:
                label = f"midblock→SG{group['midblock_parent_sg']}"
            lines.append(
                f"| {row['sc_no']} | {group['sg_id']} | {group['name']} | {label} | "
                f"{group['head_count']} | {group['green_sec']:.1f} | {after} | {delta} |"
            )
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Survey the controlled VISSIG programs")
    parser.add_argument("--network", type=Path, default=DEFAULT_NETWORK)
    parser.add_argument("--mapping", required=True, type=Path)
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--markdown-out", type=Path, default=None)
    args = parser.parse_args(argv)

    try:
        table = survey(args.network, args.mapping)
    except (SurveyError, OSError, ValueError) as exc:
        print(json.dumps({"status": "FAIL", "reason": str(exc)}, ensure_ascii=False))
        return 1

    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(table, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
    if args.markdown_out is not None:
        args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_out.write_text(render_markdown(table), encoding="utf-8", newline="\n")

    counts = table["counts"]
    print(
        "status=%s controllers=%d groups=%d headless=%d violating=%d empty_phase=%d"
        % (
            table["status"],
            counts["controllers"],
            counts["signal_groups"],
            counts["signal_groups_without_head"],
            counts["controllers_violating_target"],
            counts["controllers_with_empty_phase"],
        )
    )
    for row in table["controllers"]:
        if row["violations"]:
            print(f"  SC{row['sc_no']}: " + "; ".join(row["violations"]))
        if row["empty_target_phases"]:
            print(f"  SC{row['sc_no']}: no signal head in " + ", ".join(row["empty_target_phases"]))
    return 0 if table["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
