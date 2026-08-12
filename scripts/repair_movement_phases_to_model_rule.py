# config 의 urban_movements[*].phase 만 상류 movement_phase_id 로 다시 계산해 새 config 를 낸다
"""왜 생성기를 안 쓰는가.

`generate_real_world_distributed_players.py` 는 링크 배정에 미해결 tie 가 있으면
승인 매니페스트 없이는 산출을 거부한다. 그런데 movement 의 현시는 `approach`/`exit`
**leg 키**에만 달렸고 leg 키는 격자 기하에서 온다 — 링크가 어느 플레이어 소유인가와
무관하다. 그래서 배정을 한 글자도 안 건드리고 이 필드만 고칠 수 있다.

고치는 이유는 그 값이 **낡은 파생값**이라서다. 8/5 산출 당시 상류는 2현시였고,
지금 vendor 는 major 직진 p1 · major 좌 p2 · minor 직진 p3 · minor 좌 p4 다.
leg 키는 그대로인데 규칙만 바뀌었으므로 다시 계산하면 된다.

원본은 안 덮는다. `--out` 으로 새 파일을 낸다.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.generate_real_world_distributed_players import (  # noqa: E402
    ensure_numsim_importable,
)

DEFAULT_IN = (
    REPO / "evaluation" / "configs"
    / "real_world_modi_pstack_distributed_core15n41_20260805.json"
)
DEFAULT_OUT = (
    REPO / "evaluation" / "configs"
    / "real_world_modi_pstack_distributed_core15n41p4_20260812.json"
)


def repair(config: dict) -> tuple[dict, dict[str, int]]:
    """`urban_movements[*].phase` 만 갈아 끼운 새 config 를 돌려준다."""
    ensure_numsim_importable()
    from src.models.grid_topology import movement_phase_id

    out = json.loads(json.dumps(config))
    movements = out["config_overrides"]["network"]["urban_movements"]
    moved = collections.Counter()
    for spec in movements.values():
        old = str(spec.get("phase", ""))
        if not old:
            continue
        node = old.rpartition("_")[0]
        axis = movement_phase_id(str(spec["approach"]), str(spec["exit"]))
        spec["phase"] = f"{node}_{axis}"
        moved["changed" if old != spec["phase"] else "same"] += 1
        moved[axis] += 1
    return out, dict(moved)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_IN)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--name", default="real_world_modi_pstack_distributed_core15n41p4_20260812")
    args = parser.parse_args()

    source = json.loads(args.config.read_text(encoding="utf-8"))
    fixed, counts = repair(source)
    fixed["name"] = args.name
    fixed["description"] = (
        "core15n41 의 urban_movements[*].phase 만 상류 movement_phase_id(4현시)로 다시 "
        "계산한 것. leg 키·링크 배정·저류·신호 목록은 부모와 비트 동일하다. 8/5 판은 "
        "상류가 2현시일 때 굳은 파생값이라 p1/p2 만 있었다."
    )
    args.out.write_text(json.dumps(fixed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OUT={args.out}")
    print(f"movement phase: {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
