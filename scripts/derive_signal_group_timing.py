#!/usr/bin/env python3
# 실 .sig 에서 SC별 주기·SG별 녹색분율·충돌 SG 쌍을 뽑는 정본 생산자 (v3 N4-1/N4-2/N4-3)
"""Derive the canonical signal-group timing table from the real VISSIG programs.

N4-1(SC별 native 주기), N4-2(충돌 SG 쌍), N4-3(SG별 녹색분율)이 같은 `.sig` 를 필요로 한다.
셋을 따로 파싱하면 서로 어긋난 표가 세 개 생긴다. 그래서 하나로 만든다.

## 무엇을 드러내는가

실런에서 SG 상태를 정하는 **유일한** 경로는 이름 부분문자열이다 —
`run_real_world_stackelberg_controller.vbs:1285-1299` 의 `SignalStateForGroup` 이 이름에
EB/WB 가 있으면 major, NB/SB 면 minor 를 준다. `(SC, SG번호) -> 모델 phase` 매핑은 없다.

SC1001(주기 150 s, SG 8개) 실측이다.

    WBL 0.160  EBT 0.300  NBL 0.193  SBT 0.267
    EBL 0.160  WBT 0.300  SBL 0.120  NBT 0.340

이름 규칙은 이를 major 0.300 / minor 0.340 두 값으로 뭉갠다. 좌회전이 1.76~2.83 배
과대평가되고, 실제로 녹색창이 겹치지 않는 쌍(WBL 48-72 s vs EBT 0-45 s)이 같은 축을 받아
**동시녹색**이 된다. `.sig` 의 `<intergreenmatrices />` 가 비어 있어 VISSIM 도 막지 않는다.

이 표가 그 두 사실을 수치로 남긴다. 고치는 것은 별건이고, 여기서는 **정본을 만들고 규모를
드러내는 것**까지다.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Sequence


SCHEMA_VERSION = "signal-group-timing-v3"

# VBS SignalStateForGroup 의 이름 판정을 그대로 미러링한다.
MAJOR_PREFIXES = ("EB", "WB")
MINOR_PREFIXES = ("NB", "SB")

# 겹침 판정 허용오차[초]. 경계가 맞닿는 것은 겹침이 아니다 - 아니면 연속 현시가 전부 충돌로 잡힌다.
TOUCH_EPS_SEC = 1.0e-9


class TimingError(RuntimeError):
    """Raised when a controller cannot be resolved to a program we can read."""


def axis_for_name(name: str) -> str | None:
    """이름 접두사로 major/minor 를 고른다. 어느 쪽도 아니면 None 이다.

    조용히 major 로 떨어뜨리지 않는다 - 축이 없는 SG(보행 등)를 차량 축에 넣으면
    그 자체가 새로운 동시녹색을 만든다.
    """
    upper = str(name or "").upper()
    if any(prefix in upper for prefix in MAJOR_PREFIXES):
        return "major"
    if any(prefix in upper for prefix in MINOR_PREFIXES):
        return "minor"
    return None


def windows_overlap(
    a: Sequence[tuple[float, float]], b: Sequence[tuple[float, float]]
) -> bool:
    """두 녹색창 집합이 실제로 겹치는가."""
    for a0, a1 in a:
        for b0, b1 in b:
            if min(a1, b1) - max(a0, b0) > TOUCH_EPS_SEC:
                return True
    return False


def _green_windows(timeline) -> list[tuple[float, float]]:
    return [
        (float(interval.start_sec), float(interval.end_sec))
        for interval in timeline.intervals
        if interval.state == "GREEN"
    ]


def _sig_path_for(network_dir: Path, sc_no: int) -> Path | None:
    """`.sig` 파일명은 한글 접두사 + 컨트롤러 번호다(예: '개포동 test-bed1001.sig').

    번호가 부분문자열로 겹치므로(1 vs 1001) 끝자리 정확 일치를 요구한다.
    """
    pattern = re.compile(r"(\d+)\.sig$", re.IGNORECASE)
    for path in sorted(network_dir.glob("*.sig")):
        match = pattern.search(path.name)
        if match and int(match.group(1)) == int(sc_no):
            return path
    return None


def _controlled_controllers(mapping_path: Path) -> list[int]:
    payload = json.loads(Path(mapping_path).read_text(encoding="utf-8"))
    numbers = []
    for signal in payload.get("signals", []):
        raw = signal.get("sc_no")
        if raw is None:
            continue
        numbers.append(int(raw))
    if not numbers:
        raise TimingError(f"{mapping_path} declares no controlled signals")
    return numbers


def derive(network_dir: Path, mapping_path: Path, active_prog_no: int = 1) -> dict[str, Any]:
    # plant 컴파일러가 정본 파서를 들고 있다. 여기서 다시 짜면 두 파서가 갈린다.
    plant_root = Path(__file__).resolve().parents[1] / "plant"
    if str(plant_root) not in sys.path:
        sys.path.insert(0, str(plant_root))
    from src.vissim_strict.signal_program import parse_sig  # noqa: E402

    controllers: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []

    for sc_no in _controlled_controllers(mapping_path):
        path = _sig_path_for(Path(network_dir), sc_no)
        if path is None:
            unresolved.append({"sc_no": sc_no, "reason": "no .sig file"})
            continue
        try:
            program = parse_sig(str(path), active_prog_no)
        except Exception as exc:  # 파서가 제 예외 계층을 쓰므로 넓게 받고 사유를 남긴다
            unresolved.append({"sc_no": sc_no, "reason": f"{type(exc).__name__}: {exc}"})
            continue

        cycle = float(program.cycle_length_sec)
        groups: list[dict[str, Any]] = []
        windows: dict[str, list[tuple[float, float]]] = {}
        for key, timeline in program.sg_timelines.items():
            green = _green_windows(timeline)
            total = sum(end - start for start, end in green)
            name = str(timeline.name or key)
            windows[name] = green
            groups.append(
                {
                    "sg_id": key,
                    "name": name,
                    "green_sec": total,
                    "green_fraction": total / cycle if cycle > 0 else 0.0,
                    "green_windows": green,
                    "axis": axis_for_name(name),
                }
            )

        # 축별 최대 분율이 이름 규칙이 실제로 내보내는 값이다.
        axis_max = {"major": 0.0, "minor": 0.0}
        for group in groups:
            if group["axis"]:
                axis_max[group["axis"]] = max(
                    axis_max[group["axis"]], group["green_fraction"]
                )
        for group in groups:
            axis = group["axis"]
            fraction = group["green_fraction"]
            group["axis_green_fraction"] = axis_max[axis] if axis else None
            group["axis_overestimate"] = (
                axis_max[axis] / fraction if axis and fraction > 0 else None
            )

        # 같은 축인데 실제로는 안 겹치는 쌍 = 이름 규칙이 만드는 동시녹색.
        by_axis: dict[str, list[str]] = {"major": [], "minor": []}
        for group in groups:
            if group["axis"]:
                by_axis[group["axis"]].append(group["name"])
        for axis, names in by_axis.items():
            for i, first in enumerate(names):
                for second in names[i + 1 :]:
                    if not windows_overlap(windows[first], windows[second]):
                        conflicts.append(
                            {
                                "sc_no": sc_no,
                                "axis": axis,
                                "a": first,
                                "b": second,
                                "a_windows": windows[first],
                                "b_windows": windows[second],
                                "actually_overlaps": False,
                            }
                        )

        controllers.append(
            {
                "sc_no": sc_no,
                "sig_path": str(path.relative_to(Path(network_dir).parents[1])),
                "cycle_sec": cycle,
                "program_offset_sec": float(program.program_offset_sec),
                "groups": sorted(groups, key=lambda item: str(item["sg_id"])),
            }
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "active_prog_no": active_prog_no,
        "controllers": controllers,
        "unresolved": unresolved,
        "conflicting_pairs": conflicts,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Derive canonical signal-group timing")
    parser.add_argument("--network-dir", required=True, type=Path)
    parser.add_argument("--mapping", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--active-prog-no", type=int, default=1)
    args = parser.parse_args(argv)

    try:
        table = derive(args.network_dir, args.mapping, args.active_prog_no)
    except (TimingError, OSError, ValueError) as exc:
        print(json.dumps({"status": "FAIL", "reason": str(exc)}, ensure_ascii=False))
        return 1

    cycles = sorted({controller["cycle_sec"] for controller in table["controllers"]})
    worst = max(
        (
            group["axis_overestimate"] or 0.0
            for controller in table["controllers"]
            for group in controller["groups"]
        ),
        default=0.0,
    )
    table["sample_dimensions"] = {
        "controllers": len(table["controllers"]),
        "unresolved": len(table["unresolved"]),
        "signal_groups": sum(len(c["groups"]) for c in table["controllers"]),
        "conflicting_pairs": len(table["conflicting_pairs"]),
        "distinct_cycles": cycles,
        "worst_axis_overestimate": worst,
    }
    table["status"] = "PASS" if not table["unresolved"] else "FAIL"

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(table, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    dims = table["sample_dimensions"]
    print(
        "status=%s controllers=%d unresolved=%d groups=%d"
        % (table["status"], dims["controllers"], dims["unresolved"], dims["signal_groups"])
    )
    print("native cycles = %s" % cycles)
    print(
        "name-rule simultaneous-green pairs = %d, worst green overestimate = %.2fx"
        % (dims["conflicting_pairs"], worst)
    )
    return 0 if table["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
