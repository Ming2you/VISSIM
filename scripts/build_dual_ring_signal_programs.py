#!/usr/bin/env python3
# N4-0 작업1 생산자 - 실 .sig 15개를 주기 150 s dual-ring 현시 프로그램으로 다시 쓴다
"""Rewrite the 15 controlled VISSIG programs to the N4-0 target spec.

## 목표 스펙 (계획서 커밋 9fa2668 · 0b6f3c3)

주기 150 s · 현시 순서 major 직진 -> major 좌 -> minor 직진 -> minor 좌 ·
green_min 20 s · clearance = amber 3 s 단독(all-red 0).

**현시 수 N 은 하드코딩하지 않는다.** "그 현시에 녹색을 받는 SG 가 있을 때만 그 현시가
존재한다" 로 센다. 영구적색 SG(주기 내내 RED)는 현시를 만들지 않는다. 거기서

    lost_time = N x 3      effective_green = 150 - N x 3      green_max = eff - (N-1) x 20

가 따라 나온다. 실측하면 SC107·SC108·SC109 만 N=3 이고 나머지 12개는 N=4 다.

## 배리어 회계

배리어(major = 직진+좌, minor = 직진+좌)의 native 녹색은 **그 배리어에 속한 살아 있는
main SG 들의 (녹색 ∪ 황색) 합집합 길이 - 그 배리어의 현시 수 x 3** 이다. 합집합을 쓰는
이유는 lead-lag 와 배리어를 넘는 녹색(SC109 의 EBT) 때문에 SG 녹색의 단순 합이 주기를
넘어가기 때문이다. 실 15개 전부에서 이 회계는 정확히 닫힌다 —
`Bmajor + Bminor + N x 3 = native cycle`.

재배분은 두 단계다.

1. 배리어 총량은 `B x f` 로 비례 보존한다 (`f = eff / (Bmajor + Bminor)`).
   주기가 이미 150 이고 N=4 인 7개 SC 는 `f = 1` 이라 절대 초까지 보존된다.
2. 배리어 **안에서**는 현 프로그램의 현시별 평균 녹색 비율로 나눈 뒤 green_min 20 을 맞춘다.

## SC109 만 남는 충돌

SC109 의 minor 배리어는 native 20 s 이고 그 안의 현시는 minor 좌 하나뿐이다. 170 -> 150
축소가 17.516 s 로 만드는데, 현시가 하나라 배리어 안에서 20 을 만들 방법이 없다. 그래서
기본값은 **거부**(`BuildError`)이고, `--allow-green-min-borrow` 를 줄 때만 major 배리어에서
2.484 s 를 빌린 뒤 `green_min_borrow_sec` 로 기록한다. 배리어 총량 보존이 깨지는 유일한
지점이며 산출물과 표에 이름으로 남는다.

## 무엇을 쓰고 무엇을 안 쓰는가

- 활성 프로그램(inpx `progNo`, 15개 모두 1)의 `cycletime` 과 각 SG 의 `cmd` 두 개만 고친다.
- `signaldisplays` · `signalsequences` · `sgs` 선언 · `intergreenmatrices` · 비활성 프로그램
  (prog 2·3) 은 손대지 않는다. 영구적색 SG 의 `<sg>` 는 통째로 그대로 둔다.
- `offset` 과 `switchpoint` 도 그대로 둔다 (offset 승격은 N4-7 잠금 아래에 있다).
- 원본을 덮지 않는다. `<stem>_n4dr150.sig` 라는 새 이름으로 쓴다.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Mapping, Sequence

import survey_signal_programs as survey


SCHEMA_VERSION = "dual-ring-signal-program-plan-v1"

REPO = Path(__file__).resolve().parents[1]
DEFAULT_NETWORK = survey.DEFAULT_NETWORK

TARGET_CYCLE_SEC = 150.0
CLEARANCE_SEC = 3.0
GREEN_MIN_SEC = 20.0

PHASE_ORDER = survey.PHASE_ORDER
BARRIER_OF = {
    "major_through": "major",
    "major_left": "major",
    "minor_through": "minor",
    "minor_left": "minor",
}
BARRIER_ORDER = ("major", "minor")

OUTPUT_SUFFIX = "_n4dr150"

_EPS = 1e-9
_GREEN_DISPLAY = "3"
_RED_DISPLAY = "1"


class BuildError(RuntimeError):
    """Raised when the target spec cannot be met on a real controller."""


# ---------------------------------------------------------------- 순수 산술


def circular_union_sec(spans: Sequence[Sequence[float]], cycle_sec: float) -> tuple[float, int]:
    """[start, end) 구간들의 합집합 길이와 조각 수를 주기 위에서 센다."""
    if not spans:
        return 0.0, 0
    merged: list[list[float]] = []
    for start, end in sorted((float(a), float(b)) for a, b in spans):
        if merged and start <= merged[-1][1] + _EPS:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    if len(merged) > 1 and merged[0][0] <= _EPS and abs(merged[-1][1] - cycle_sec) <= _EPS:
        merged[0][0] = merged[-1][0] - cycle_sec
        merged.pop()
    return sum(end - start for start, end in merged), len(merged)


def overlap_sec(left: Sequence[Sequence[float]], right: Sequence[Sequence[float]]) -> float:
    """두 구간 집합의 겹침 길이."""
    return sum(
        max(0.0, min(a_end, b_end) - max(a_start, b_start))
        for a_start, a_end in left
        for b_start, b_end in right
    )


def integerize(values: Mapping[str, float], total: int, order: Sequence[str]) -> dict[str, int]:
    """최대잔여법으로 정수화한다. 잔여가 같으면 ``order`` 에서 앞선 쪽이 가져간다."""
    keys = [key for key in order if key in values]
    if sorted(keys) != sorted(values):
        raise BuildError(f"integerize order {list(order)} does not cover {sorted(values)}")
    floors = {key: int(math.floor(values[key] + _EPS)) for key in keys}
    short = total - sum(floors.values())
    if short < 0:
        raise BuildError(f"integerize cannot remove {-short}s from {values}")
    ranked = sorted(
        keys,
        key=lambda key: (-(values[key] - floors[key]), order.index(key)),
    )
    for key in ranked[:short]:
        floors[key] += 1
    return floors


def contiguous_run(present: Sequence[str], covered: Sequence[str]) -> list[str]:
    """``covered`` 가 ``present`` 위에서 이루는 순환 연속 구간을 순서대로 낸다."""
    order = list(present)
    wanted = set(covered)
    if not wanted or not wanted.issubset(order):
        raise BuildError(f"phase span {sorted(wanted)} is not inside {order}")
    size = len(order)
    for start in range(size):
        run = [order[(start + step) % size] for step in range(len(wanted))]
        if set(run) == wanted:
            return run
    raise BuildError(f"phase span {sorted(wanted)} is not contiguous in {order}")


# ---------------------------------------------------------------- 분석


def _live_main_groups(row: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [
        group
        for group in row["signal_groups"]
        if group["midblock_parent_sg"] is None and not group["permanent_red"]
    ]


def _present_phases(row: Mapping[str, Any]) -> list[str]:
    live = _live_main_groups(row)
    return [name for name in PHASE_ORDER if any(group["phase"] == name for group in live)]


def _native_phase_windows(row: Mapping[str, Any], phase: str) -> list[list[float]]:
    spans: list[list[float]] = []
    for group in _live_main_groups(row):
        if group["phase"] == phase:
            spans += [list(window) for window in group["green_windows"]]
    return spans


def _native_barriers(row: Mapping[str, Any], present: Sequence[str]) -> dict[str, float]:
    cycle = float(row["cycle_sec"])
    barriers: dict[str, float] = {}
    for barrier in BARRIER_ORDER:
        names = [name for name in present if BARRIER_OF[name] == barrier]
        if not names:
            continue
        spans: list[list[float]] = []
        for group in _live_main_groups(row):
            if group["phase"] in names:
                spans += [list(w) for w in group["green_windows"]]
                spans += [list(w) for w in group["amber_windows"]]
        length, pieces = circular_union_sec(spans, cycle)
        if pieces != 1:
            raise BuildError(
                f"SC{row['sc_no']} {barrier} barrier is not one contiguous block "
                f"({pieces} pieces) - the native program is not ring-barrier"
            )
        barriers[barrier] = length - len(names) * CLEARANCE_SEC
    return barriers


def _phase_means(row: Mapping[str, Any], present: Sequence[str]) -> dict[str, float]:
    means: dict[str, float] = {}
    for name in present:
        greens = [g["green_sec"] for g in _live_main_groups(row) if g["phase"] == name]
        means[name] = sum(greens) / len(greens)
    return means


def _split_barriers(
    *,
    sc_no: int,
    present: Sequence[str],
    native: Mapping[str, float],
    effective_green: float,
    allow_borrow: bool,
) -> tuple[dict[str, float], float, float, str | None]:
    """배리어 목표 총량을 비례 축소한 뒤 green_min 을 맞춘다."""
    factor = effective_green / sum(native.values())
    scaled = {barrier: value * factor for barrier, value in native.items()}
    need = {
        barrier: GREEN_MIN_SEC * sum(1 for name in present if BARRIER_OF[name] == barrier)
        for barrier in scaled
    }
    borrow = 0.0
    borrow_from: str | None = None
    for barrier in BARRIER_ORDER:
        if barrier not in scaled or scaled[barrier] >= need[barrier] - _EPS:
            continue
        donor = next((other for other in scaled if other != barrier), None)
        deficit = need[barrier] - scaled[barrier]
        if donor is None or scaled[donor] - deficit < need[donor] - _EPS:
            raise BuildError(
                f"SC{sc_no} {barrier} barrier holds {scaled[barrier]:.3f}s but its "
                f"{int(need[barrier] / GREEN_MIN_SEC)} phase(s) need {need[barrier]:.0f}s "
                "and no barrier can lend it"
            )
        if not allow_borrow:
            raise BuildError(
                f"SC{sc_no} {barrier} barrier holds {scaled[barrier]:.3f}s but green_min "
                f"needs {need[barrier]:.0f}s; the barrier has a single phase so it cannot be "
                "met inside the barrier. Re-run with allow_green_min_borrow to take "
                f"{deficit:.3f}s from the {donor} barrier and record the deviation."
            )
        scaled[barrier] += deficit
        scaled[donor] -= deficit
        borrow = deficit
        borrow_from = donor
    return scaled, factor, borrow, borrow_from


def _controller_plan(
    row: Mapping[str, Any], *, network_dir: Path, allow_borrow: bool
) -> dict[str, Any]:
    sc_no = int(row["sc_no"])
    present = _present_phases(row)
    if not present:
        raise BuildError(f"SC{sc_no} has no phase that receives green")
    count = len(present)
    effective_green = TARGET_CYCLE_SEC - count * CLEARANCE_SEC
    green_max = effective_green - (count - 1) * GREEN_MIN_SEC

    native = _native_barriers(row, present)
    scaled, factor, borrow, borrow_from = _split_barriers(
        sc_no=sc_no,
        present=present,
        native=native,
        effective_green=effective_green,
        allow_borrow=allow_borrow,
    )
    barrier_int = integerize(scaled, int(round(effective_green)), BARRIER_ORDER)

    means = _phase_means(row, present)
    greens: dict[str, int] = {}
    for barrier in BARRIER_ORDER:
        names = [name for name in present if BARRIER_OF[name] == barrier]
        if not names:
            continue
        share = sum(means[name] for name in names)
        raw = {name: barrier_int[barrier] * means[name] / share for name in names}
        slack = barrier_int[barrier] - GREEN_MIN_SEC * len(names)
        if slack < -_EPS:
            raise BuildError(
                f"SC{sc_no} {barrier} barrier {barrier_int[barrier]}s cannot hold "
                f"{len(names)} phases at green_min {GREEN_MIN_SEC:.0f}s"
            )
        over = {name: max(0.0, raw[name] - GREEN_MIN_SEC) for name in names}
        if any(value < GREEN_MIN_SEC - _EPS for value in raw.values()):
            spare = sum(over.values())
            raw = {
                name: GREEN_MIN_SEC + (slack * over[name] / spare if spare > 0 else slack / len(names))
                for name in names
            }
        greens.update(integerize(raw, barrier_int[barrier], PHASE_ORDER))

    for name, value in greens.items():
        if value < GREEN_MIN_SEC - _EPS:
            raise BuildError(f"SC{sc_no} {name} lands at {value}s < green_min {GREEN_MIN_SEC:.0f}s")
        if value > green_max + _EPS:
            raise BuildError(f"SC{sc_no} {name} lands at {value}s > green_max {green_max:.0f}s")

    cursor = 0.0
    phases: dict[str, dict[str, Any]] = {}
    for name in present:
        phases[name] = {
            "green_start_sec": cursor,
            "green_sec": float(greens[name]),
            "amber_start_sec": cursor + greens[name],
            "native_mean_green_sec": means[name],
            "sg_ids": [g["sg_id"] for g in _live_main_groups(row) if g["phase"] == name],
        }
        cursor += greens[name] + CLEARANCE_SEC
    if abs(cursor - TARGET_CYCLE_SEC) > _EPS:
        raise BuildError(f"SC{sc_no} layout closes at {cursor}s, expected {TARGET_CYCLE_SEC}s")

    groups = [
        _group_plan(group, row=row, present=present, phases=phases)
        for group in row["signal_groups"]
    ]

    return {
        "sc_no": sc_no,
        "sig_file": row["sig_file"],
        "source_sig_path": str(network_dir / row["sig_file"]),
        "source_sig_sha256": row["sig_sha256"],
        "output_sig_name": Path(row["sig_file"]).stem + OUTPUT_SUFFIX + ".sig",
        "prog_no": int(row["prog_no"]),
        "program_name": row["program_name"],
        "native_cycle_sec": float(row["cycle_sec"]),
        "target_cycle_sec": TARGET_CYCLE_SEC,
        "program_offset_sec": float(row["program_offset_sec"]),
        "phase_count": count,
        "phase_order": present,
        "absent_phases": [name for name in PHASE_ORDER if name not in present],
        "lost_time_sec": count * CLEARANCE_SEC,
        "effective_green_total_sec": effective_green,
        "green_max_sec": green_max,
        "scale_factor": factor,
        "native_barrier_green_sec": native,
        "target_barrier_green_sec": {key: float(value) for key, value in barrier_int.items()},
        "green_min_borrow_sec": round(borrow, 3),
        "green_min_borrow_from": borrow_from,
        "phases": phases,
        "signal_groups": groups,
    }


def _group_plan(
    group: Mapping[str, Any],
    *,
    row: Mapping[str, Any],
    present: Sequence[str],
    phases: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    record = {
        "sg_id": group["sg_id"],
        "name": group["name"],
        "phase": group["phase"],
        "head_count": group["head_count"],
        "permanent_red": group["permanent_red"],
        "midblock_parent_sg": group["midblock_parent_sg"],
        "native_green_sec": group["green_sec"],
    }
    if group["permanent_red"]:
        record.update(
            {"phase_span": [], "target_green_sec": 0.0, "green_start_sec": None, "delta_green_sec": 0.0}
        )
        return record

    if group["midblock_parent_sg"] is None:
        span = [group["phase"]]
    else:
        covered = []
        for name in present:
            native_window = _native_phase_windows(row, name)
            length, _ = circular_union_sec(native_window, float(row["cycle_sec"]))
            if length <= 0.0:
                continue
            if overlap_sec(group["green_windows"], native_window) >= 0.5 * length - _EPS:
                covered.append(name)
        span = contiguous_run(present, covered)

    green = sum(phases[name]["green_sec"] for name in span) + (len(span) - 1) * CLEARANCE_SEC
    record.update(
        {
            "phase_span": span,
            "target_green_sec": float(green),
            "green_start_sec": phases[span[0]]["green_start_sec"],
            "delta_green_sec": float(green) - group["green_sec"],
        }
    )
    return record


def build(
    network_path: Path,
    mapping_path: Path,
    *,
    allow_green_min_borrow: bool = False,
) -> dict[str, Any]:
    """15개 제어 SC 의 150 s dual-ring 재작성 계획을 만든다."""

    table = survey.survey(Path(network_path), Path(mapping_path))
    network_dir = Path(network_path).parent
    controllers = [
        _controller_plan(row, network_dir=network_dir, allow_borrow=allow_green_min_borrow)
        for row in table["controllers"]
    ]
    borrowing = [row["sc_no"] for row in controllers if row["green_min_borrow_sec"]]
    return {
        "schema_version": SCHEMA_VERSION,
        "source": dict(table["source"]),
        "target_spec": {
            "cycle_sec": TARGET_CYCLE_SEC,
            "clearance_sec": CLEARANCE_SEC,
            "all_red_sec": 0.0,
            "green_min_sec": GREEN_MIN_SEC,
            "phase_order": list(PHASE_ORDER),
            "phase_count_rule": "a phase exists only when a signal group receives green in it",
        },
        "controllers": controllers,
        "counts": {
            "controllers": len(controllers),
            "signal_groups": sum(len(row["signal_groups"]) for row in controllers),
            "permanent_red_signal_groups": sum(
                1 for row in controllers for g in row["signal_groups"] if g["permanent_red"]
            ),
            "three_phase_controllers": sum(1 for row in controllers if row["phase_count"] == 3),
            "green_min_borrow_controllers": len(borrowing),
        },
        "green_min_borrow_controllers": borrowing,
        "status": "PASS_WITH_BORROW" if borrowing else "PASS",
    }


# ---------------------------------------------------------------- 쓰기


def _serialize(root: ET.Element) -> bytes:
    """원본과 같은 선언·개행으로 직렬화한다 (무수정 파일은 바이트 동일)."""
    body = ET.tostring(root, encoding="unicode")
    text = '<?xml version="1.0" encoding="UTF-8"?>\n' + body
    return text.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8")


def _rewrite_program(root: ET.Element, plan_row: Mapping[str, Any]) -> None:
    prog = None
    for element in root.findall("./progs/prog"):
        if int(element.get("id", "0")) == int(plan_row["prog_no"]):
            prog = element
            break
    if prog is None:
        raise BuildError(f"SC{plan_row['sc_no']}: program {plan_row['prog_no']} is absent")

    cycle_ms = int(round(TARGET_CYCLE_SEC * 1000))
    offset_ms = int(round(plan_row["program_offset_sec"] * 1000))
    if not 0 <= offset_ms < cycle_ms:
        raise BuildError(
            f"SC{plan_row['sc_no']}: native offset {offset_ms}ms does not fit a {cycle_ms}ms cycle"
        )
    prog.set("cycletime", str(cycle_ms))

    by_id = {group["sg_id"]: group for group in plan_row["signal_groups"]}
    for program_sg in prog.findall("./sgs/sg"):
        sg_id = str(program_sg.get("sg_id"))
        group = by_id.get(sg_id)
        if group is None:
            raise BuildError(f"SC{plan_row['sc_no']}: program declares unknown SG {sg_id}")
        if group["permanent_red"]:
            continue
        commands = program_sg.findall("./cmds/cmd")
        if len(commands) != 2:
            raise BuildError(
                f"SC{plan_row['sc_no']} SG{sg_id}: expected 2 commands, found {len(commands)}"
            )
        green_ms = int(round(group["green_start_sec"] * 1000))
        red_ms = (green_ms + int(round(group["target_green_sec"] * 1000))
                  + int(round(CLEARANCE_SEC * 1000))) % cycle_ms
        if green_ms == red_ms:
            raise BuildError(f"SC{plan_row['sc_no']} SG{sg_id}: green and red begin collide")
        schedule = sorted(((green_ms, _GREEN_DISPLAY), (red_ms, _RED_DISPLAY)))
        for element, (begin_ms, display) in zip(commands, schedule):
            element.set("display", display)
            element.set("begin", str(begin_ms))


def write_programs(plan: Mapping[str, Any], out_dir: Path) -> list[Path]:
    """계획대로 새 `.sig` 15개를 쓴다. 원본은 건드리지 않는다."""

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for plan_row in plan["controllers"]:
        source = Path(plan_row["source_sig_path"])
        root = ET.parse(source).getroot()
        _rewrite_program(root, plan_row)
        target = out_dir / plan_row["output_sig_name"]
        if target.resolve() == source.resolve():
            raise BuildError(f"refusing to overwrite the original {source}")
        target.write_bytes(_serialize(root))
        written.append(target)
    return written


# ---------------------------------------------------------------- 표


def render_markdown(plan: Mapping[str, Any]) -> str:
    spec = plan["target_spec"]
    lines = [
        "# N4-0 작업1 - 실 `.sig` 15개의 150 s dual-ring 재작성",
        "",
        f"목표 — 주기 {spec['cycle_sec']:.0f} s · clearance amber {spec['clearance_sec']:.0f} s "
        f"(all-red {spec['all_red_sec']:.0f}) · green_min {spec['green_min_sec']:.0f} s · "
        "현시 순서 major 직진 → major 좌 → minor 직진 → minor 좌.",
        "",
        f"현시 수는 유도된다 — {spec['phase_count_rule']}.",
        "",
        f"판정 — **{plan['status']}**. 제어기 {plan['counts']['controllers']}개 · "
        f"SG {plan['counts']['signal_groups']}개 · 영구적색 "
        f"{plan['counts']['permanent_red_signal_groups']}개 · N=3 인 SC "
        f"{plan['counts']['three_phase_controllers']}개 · green_min 차용 SC "
        f"{plan['counts']['green_min_borrow_controllers']}개"
        + (f" ({plan['green_min_borrow_controllers']})" if plan["green_min_borrow_controllers"] else "")
        + ".",
        "",
        "## SC별 현시 구조",
        "",
        "| SC | `.sig` → 새 파일 | 주기 전→후 | N | 없는 현시 | 유효녹색 | green_max | f |",
        "| ---: | --- | ---: | ---: | --- | ---: | ---: | ---: |",
    ]
    for row in plan["controllers"]:
        lines.append(
            f"| {row['sc_no']} | {row['sig_file']} → {row['output_sig_name']} | "
            f"{row['native_cycle_sec']:.0f} → {row['target_cycle_sec']:.0f} | {row['phase_count']} | "
            f"{', '.join(row['absent_phases']) or '-'} | {row['effective_green_total_sec']:.0f} | "
            f"{row['green_max_sec']:.0f} | {row['scale_factor']:.4f} |"
        )

    lines += [
        "",
        "## 배리어 총량 전/후 (초)",
        "",
        "`목표 = native x f` 가 성립하면 배리어 몫이 보존된 것이다. 정수화 오차는 ±0.5 s 다.",
        "",
        "| SC | major native | major 목표 | major 편차 | minor native | minor 목표 | minor 편차 |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in plan["controllers"]:
        cells = []
        for barrier in BARRIER_ORDER:
            native = row["native_barrier_green_sec"].get(barrier)
            if native is None:
                cells += ["-", "-", "-"]
                continue
            target = row["target_barrier_green_sec"][barrier]
            cells += [f"{native:.1f}", f"{target:.0f}", f"{target - native * row['scale_factor']:+.3f}"]
        lines.append(f"| {row['sc_no']} | " + " | ".join(cells) + " |")

    lines += [
        "",
        "## 현시별 목표 창 (초)",
        "",
        "| SC | major 직진 | major 좌 | minor 직진 | minor 좌 |",
        "| ---: | --- | --- | --- | --- |",
    ]
    for row in plan["controllers"]:
        cells = []
        for name in PHASE_ORDER:
            phase = row["phases"].get(name)
            if phase is None:
                cells.append("없음")
                continue
            start = phase["green_start_sec"]
            cells.append(
                f"{phase['native_mean_green_sec']:.1f} → {phase['green_sec']:.0f} "
                f"[{start:.0f},{start + phase['green_sec']:.0f})"
            )
        lines.append(f"| {row['sc_no']} | " + " | ".join(cells) + " |")

    lines += [
        "",
        "## 접근로(SG)별 녹색 전/후 (초) — 136개 전수",
        "",
        "| SC | SG | 이름 | 현시 | 등두 | 전 | 후 | 증감 |",
        "| ---: | ---: | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in plan["controllers"]:
        for group in row["signal_groups"]:
            if group["permanent_red"]:
                label = "영구적색"
            elif group["midblock_parent_sg"] is not None:
                label = f"midblock→SG{group['midblock_parent_sg']} " + "+".join(
                    name[:9] for name in group["phase_span"]
                )
            else:
                label = group["phase"]
            lines.append(
                f"| {row['sc_no']} | {group['sg_id']} | {group['name']} | {label} | "
                f"{group['head_count']} | {group['native_green_sec']:.1f} | "
                f"{group['target_green_sec']:.1f} | {group['delta_green_sec']:+.1f} |"
            )
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- CLI


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rewrite the controlled VISSIG programs to 150 s")
    parser.add_argument("--network", type=Path, default=DEFAULT_NETWORK)
    parser.add_argument("--mapping", required=True, type=Path)
    parser.add_argument("--sig-out-dir", type=Path, default=None)
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--markdown-out", type=Path, default=None)
    parser.add_argument(
        "--allow-green-min-borrow",
        action="store_true",
        help="배리어 안에서 green_min 을 못 맞추는 SC 에서 다른 배리어의 초를 빌린다",
    )
    args = parser.parse_args(argv)

    try:
        plan = build(
            args.network, args.mapping, allow_green_min_borrow=args.allow_green_min_borrow
        )
        written = write_programs(plan, args.sig_out_dir) if args.sig_out_dir else []
    except (BuildError, survey.SurveyError, OSError, ValueError) as exc:
        print(json.dumps({"status": "FAIL", "reason": str(exc)}, ensure_ascii=False))
        return 1

    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
    if args.markdown_out is not None:
        args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_out.write_text(render_markdown(plan), encoding="utf-8", newline="\n")

    counts = plan["counts"]
    print(
        "status=%s controllers=%d groups=%d permanent_red=%d three_phase=%d borrow=%s written=%d"
        % (
            plan["status"],
            counts["controllers"],
            counts["signal_groups"],
            counts["permanent_red_signal_groups"],
            counts["three_phase_controllers"],
            plan["green_min_borrow_controllers"] or "-",
            len(written),
        )
    )
    for row in plan["controllers"]:
        if row["green_min_borrow_sec"]:
            print(
                f"  SC{row['sc_no']}: borrowed {row['green_min_borrow_sec']:.3f}s "
                f"from the {row['green_min_borrow_from']} barrier to reach green_min"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
