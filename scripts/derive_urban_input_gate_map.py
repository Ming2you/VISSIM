# VISSIM 도시부 vehicle input 을 모델 경계 게이트에 1:1 로 잇는 대장(CSV)을 만든다
"""`state.demand.urban_volume_vph_by_gate` 의 조인 키를 만드는 생성기.

러너는 `.inpx` 를 이미 읽는다. 모자란 것은 **어느 유입이 어느 게이트인가** 하나뿐이고,
그것이 이 대장이다. 러너가 이 CSV 로 조인해서 게이트별 유량을 state 에 쓴다.

방위 규칙 (실측으로 정한 정본).

1. 유입 이름의 진행방향 접미사가 **정본**이다. 진행방향의 반대가 진입 leg 다.
   `NB -> S`, `SB -> N`, `EB -> W`, `WB -> E`.
   (`구룡터널_NB(터널직진)` 처럼 접미사 뒤에 괄호가 붙어도 잡는다.)
2. 이름이 없으면 기하 추정 `leg.link_geometry` 를 쓴다
   (`outputs/boundary_input_alignment_20260811.json`, 정렬 산출물의 1순위 추정자).

게이트 이름은 문자열로 짓지 않는다. tuning config 의
`config_overrides.network.grid_node_legs[node][<leg>_*]["in"]` 에서 **읽어 온다**.
그 leg 에 boundary 가 없으면 사유를 status 에 남긴다 - 조용히 버리지 않는다.

    python scripts/derive_urban_input_gate_map.py --out <csv>
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
DEFAULT_ALIGNMENT = REPO / "outputs/boundary_input_alignment_20260811.json"
DEFAULT_CONFIG = REPO / "evaluation/configs/real_world_modi_pstack_distributed_core15n41_20260805.json"

# 러너 vbs:125 RW_FREEWAY_INPUT_LINKS. 고속부 유입은 게이트가 아니라 freeway_links 로 간다.
FREEWAY_INPUT_LINKS = frozenset({"26", "74"})

SUFFIX_TO_LEG = {"NB": "S", "SB": "N", "EB": "W", "WB": "E"}
NAME_SUFFIX = re.compile(r"_(NB|SB|EB|WB)(?![A-Za-z])", re.IGNORECASE)

FIELDS = [
    "no",
    "gate",
    "status",
    "leg",
    "leg_source",
    "model_node",
    "link",
    "entry_class",
    "role",
    "first_volume_vph",
    "peak_volume_vph",
    "name",  # 이름에 콤마가 들어간다(`개포3,4단지_WB`). 러너의 Split(line,",") 때문에 **마지막**.
]


def leg_from_name(name: str) -> str | None:
    """진행방향 접미사에서 진입 leg 을 뽑는다. 없으면 None."""
    matches = NAME_SUFFIX.findall(str(name or ""))
    if not matches:
        return None
    return SUFFIX_TO_LEG[matches[-1].upper()]


def gate_on_leg(node: str, leg: str | None, grid_node_legs: dict[str, Any]) -> tuple[str, str]:
    """(gate, status). 게이트 이름은 config 에서 읽는다 - 문자열로 짓지 않는다."""
    if not node or node not in grid_node_legs:
        return "", "node_absent_from_model"
    if leg is None:
        return "", "leg_undetermined"
    kinds: set[str] = set()
    for key, spec in grid_node_legs[node].items():
        if str(key).split("_", 1)[0] != leg or not isinstance(spec, dict):
            continue
        kind = str(spec.get("type", ""))
        kinds.add(kind)
        if kind == "boundary":
            return str(spec.get("in", "")), "mapped"
    if "grid" in kinds:
        return "", "leg_occupied_by_grid_neighbour"
    if "ramp" in kinds:
        return "", "leg_occupied_by_ramp"
    return "", "leg_absent_at_node"


def build_rows(alignment: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    network = (config.get("config_overrides") or {}).get("network") or {}
    grid_node_legs = network.get("grid_node_legs") or {}
    rows: list[dict[str, Any]] = []
    for vi in alignment["vehicle_inputs"]:
        name = str(vi.get("name") or "")
        role = str(vi.get("role") or "")
        entry_class = str(vi.get("entry_class") or "")
        volumes = [float(v) for v in vi.get("volumes_vph") or [0.0]]
        row = {
            "no": str(vi["vehicle_input_no"]),
            "gate": "",
            "status": "",
            "leg": "",
            "leg_source": "",
            "model_node": str(vi.get("model_node") or ""),
            "link": str(vi.get("link") or ""),
            "entry_class": entry_class,
            "role": role,
            "first_volume_vph": f"{volumes[0]:.4f}",
            "peak_volume_vph": f"{max(volumes):.4f}",
            "name": name,
        }
        if role.startswith("freeway") or row["link"] in FREEWAY_INPUT_LINKS:
            row["status"] = "freeway_excluded"
            rows.append(row)
            continue
        if entry_class == "dummy":
            # 사용자 확정 - Dummy Link 유입은 망 입구가 아니라 **내부 발생**이다.
            row["status"] = "internal"
            rows.append(row)
            continue
        leg = leg_from_name(name)
        row["leg_source"] = "name_suffix" if leg else "link_geometry"
        if leg is None:
            leg = (vi.get("leg") or {}).get("link_geometry")
        row["leg"] = str(leg or "")
        row["gate"], row["status"] = gate_on_leg(row["model_node"], leg, grid_node_legs)
        rows.append(row)
    return rows


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_status: dict[str, dict[str, float]] = {}
    for row in rows:
        bucket = by_status.setdefault(row["status"], {"count": 0, "peak_volume_vph": 0.0})
        bucket["count"] += 1
        bucket["peak_volume_vph"] += float(row["peak_volume_vph"])
    gates = [row["gate"] for row in rows if row["status"] == "mapped"]
    duplicates = sorted({gate for gate in gates if gates.count(gate) > 1})
    return {
        "by_status": {k: by_status[k] for k in sorted(by_status)},
        "duplicate_gates": duplicates,
    }


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path: Path, rows: list[dict[str, Any]], provenance: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        for line in provenance:
            handle.write(f"# {line}\n")
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--alignment", default=str(DEFAULT_ALIGNMENT))
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    alignment_path = Path(args.alignment)
    config_path = Path(args.config)
    alignment = json.loads(alignment_path.read_text(encoding="utf-8"))
    config = json.loads(config_path.read_text(encoding="utf-8"))

    rows = build_rows(alignment, config)
    summary = summarize(rows)
    provenance = [
        "generated by scripts/derive_urban_input_gate_map.py",
        f"alignment={alignment_path.as_posix()} sha256={sha256(alignment_path)}",
        f"config={config_path.as_posix()} sha256={sha256(config_path)}",
        "leg rule: name suffix NB->S SB->N EB->W WB->E; unnamed -> leg.link_geometry",
        # 러너가 이 값을 읽어 자기가 실제로 매핑한 개수와 대조한다. 어긋나면 부분 stale 이라
        # 그만큼만 주입되고 조용히 지나가므로, 개수를 대장이 선언하는 것이 유일한 방어다.
        f"expected_mapped={sum(1 for row in rows if row['status'] == 'mapped')}",
    ]
    write_csv(Path(args.out), rows, provenance)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if summary["duplicate_gates"]:
        print("ERROR=DUPLICATE_GATES " + ",".join(summary["duplicate_gates"]), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
