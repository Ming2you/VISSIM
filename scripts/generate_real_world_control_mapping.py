from __future__ import annotations

import argparse
import csv
import json
import math
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Any


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]

# freeway 본선은 링크 하나가 아니라 링크 체인이다. 어떤 링크가 어떤 순서로 이어지는지는
# 아래 CSV 한 곳에만 적혀 있고, 길이는 언제나 네트워크(.inpx)에서 읽는다.
# 설치 스크립트(install_real_world_freeway_controls.vbs)도 같은 CSV를 읽는다.
FREEWAY_MAINLINE_CHAIN_CSV = WORKSPACE_ROOT / "evaluation/real_world_modi_control/freeway_mainline_chain.csv"
FREEWAY_SEGMENTS_PER_LINK = 8


def load_freeway_mainline_chain(path: Path = FREEWAY_MAINLINE_CHAIN_CSV) -> dict[str, dict[str, Any]]:
    """정본 체인 CSV를 model_link -> {direction, links, primary_link} 로 읽는다."""
    text_lines = [
        line
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    chain: dict[str, dict[str, Any]] = {}
    rows = list(csv.DictReader(text_lines))
    for row in sorted(rows, key=lambda r: (str(r["model_link"]), int(r["chain_order"]))):
        model = str(row["model_link"]).strip()
        spec = chain.setdefault(
            model,
            {"direction": str(row["direction"]).strip(), "links": [], "primary_link": None},
        )
        link_no = int(str(row["link_no"]).strip())
        spec["links"].append(link_no)
        if str(row.get("role", "")).strip() == "primary":
            spec["primary_link"] = link_no
    if not chain:
        raise ValueError(f"체인 정의가 비어 있다: {path}")
    for spec in chain.values():
        if spec["primary_link"] is None:
            spec["primary_link"] = spec["links"][0]
    return chain


FREEWAY_MAINLINE_CHAIN = load_freeway_mainline_chain()
# 대표 링크. 매니페스트/CSV의 physical_link 열과 하위 호환을 위해 남긴다.
FREEWAY_MODEL_LINKS = {
    model: int(spec["primary_link"]) for model, spec in FREEWAY_MAINLINE_CHAIN.items()
}
FREEWAY_CHAIN_LINKS = sorted(
    {int(link) for spec in FREEWAY_MAINLINE_CHAIN.values() for link in spec["links"]}
)

RAMP_METER_ORDER = [
    "RM_C10480",
    "RM_C10482",
    "RM_C10646",
    "RM_C10644",
    "RM_C10639",
    "RM_C10681",
    "RM_C10490",
    "RM_C10484",
]

OFF_RAMP_GROUPS = {
    "OR_D_W": [10479, 10491],
    "OR_F_W": [10638, 10645],
    "OR_F_E": [10643, 10682],
    "OR_D_E": [10481, 10483],
}

OFF_RAMP_MOVEMENTS = {
    "OR_D_W": ["D_offW_to_N", "D_offW_to_E", "D_offW_to_W"],
    "OR_D_E": ["D_offE_to_N", "D_offE_to_E", "D_offE_to_W"],
    "OR_F_W": ["F_offW_to_N", "F_offW_to_E", "F_offW_to_W"],
    "OR_F_E": ["F_offE_to_N", "F_offE_to_E", "F_offE_to_W"],
}

MODEL_RAMP_TO_URBAN_SIGNAL = {
    "R_D_W": "D",
    "R_D_E": "D",
    "R_F_W": "F",
    "R_F_E": "F",
}

DEFAULT_ROLES_CSV = "evaluation/real_world_modi_inventory/signal_controller_roles.csv"


def interface_signal_rows(roles_csv: str = DEFAULT_ROLES_CSV) -> list[dict[str, Any]]:
    """freeway 인터페이스 신호제어기를 인벤토리에서 찾아 매핑 항목으로 만든다.

    2026-08-04 정정. 이전에는 sc_no 를 1 로 하드코딩하고 주석에 "SC 1 is the only controller
    inventoried with freeway-interface signal heads" 라고 적어 두었으나 **틀렸다**.
    인벤토리 실측은 이렇다.

        SC    1   interface_head_count = 0   role=urban_signal_controller            (구룡초교)
        SC 1001   interface_head_count = 3   role=urban_freeway_interface_signal_controller

    interface_head_count > 0 인 컨트롤러는 전체 37 개 중 SC 1001 하나뿐이다.
    즉 기본 매핑이 엉뚱한 교차로를 제어하고 있었다. 값을 박아 두지 않고 인벤토리에서 읽는다.

    major_maps_to 는 VISSIM MAJOR(SG1) 접근이 모델의 어느 phase 인지를 뜻한다.
    인터페이스 교차로는 MAJOR 접근이 off-ramp 유출이고 모델은 램프 leg 를 NS 축으로 보아
    p1 에 두므로(NumSim grid_topology._token_leg_dir: off*/on* -> "S") p1 이다.
    일반 간선 교차로는 MAJOR=EW 간선=모델 p2 다.
    """
    path = WORKSPACE_ROOT / roles_csv
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            try:
                ihc = int(float(row.get("interface_head_count") or 0))
            except (TypeError, ValueError):
                ihc = 0
            if ihc <= 0:
                continue
            raw_no = "".join(ch for ch in str(row.get("no") or "") if ch.isdigit())
            if not raw_no:
                continue
            sc_no = int(raw_no)
            rows.append({
                "id": "D",
                "sc_no": sc_no,
                "coverage": ["D", "F"],
                "role": row.get("role", "urban_freeway_interface_signal_controller"),
                "major_maps_to": "p1",
                "phase_map": {
                    "major_axis": "freeway_offramp",
                    "minor_axis": "cross_street",
                    "major_sg_name_prefixes": ["EB", "WB"],
                    "minor_sg_name_prefixes": ["NB", "SB"],
                },
                "interface_head_count": ihc,
                "source": roles_csv,
                "note": (
                    f"SC {sc_no} 는 interface_head_count={ihc} 로 인벤토리에서 유일한 "
                    "freeway 인터페이스 컨트롤러다. 정지선 신호두가 link 32 위에 있고 "
                    "link 32 의 유입은 conn 10481(본선 2) / conn 10491(본선 26) 뿐이므로 "
                    "MAJOR 접근이 곧 off-ramp 유출이다."
                ),
            })
    return rows


# 모듈 로드 시 인벤토리에서 유도한다. 비어 있으면 인벤토리가 없거나 인터페이스 컨트롤러가
# 하나도 식별되지 않은 것이므로, 조용히 넘어가지 말고 사용처에서 소리내어 실패해야 한다.
REAL_WORLD_INTERFACE_SIGNALS = interface_signal_rows()


def freeway_agent_id(model_link: str, segment_index: int) -> str:
    suffix = model_link.split("_")[-1] if "_" in model_link else model_link
    return f"F_{suffix}{int(segment_index)}"


def urban_agent_id(signal: str) -> str:
    return f"U_{signal}"


def clean_int(value: str | None) -> int | None:
    if value is None:
        return None
    text = "".join(ch for ch in str(value) if ch.isdigit() or ch == "-")
    return int(text) if text else None


def clean_float(value: str | None, default: float = 0.0) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return float(default)


def first_int(value: str | None) -> int | None:
    match = re.search(r"-?\d+", str(value or ""))
    return int(match.group(0)) if match else None


def lane_no_from_ref(value: str | None) -> int | None:
    parts = re.findall(r"-?\d+", str(value or ""))
    if len(parts) >= 2:
        return int(parts[1])
    return None


def link_points(link: ET.Element) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for pt in link.findall("./geometry/linkPolyPts/linkPolyPoint"):
        x = clean_float(pt.get("x"), math.nan)
        y = clean_float(pt.get("y"), math.nan)
        if not math.isnan(x) and not math.isnan(y):
            points.append((x, y))
    return points


def polyline_length(points: list[tuple[float, float]]) -> float:
    return sum(
        math.hypot(x2 - x1, y2 - y1)
        for (x1, y1), (x2, y2) in zip(points, points[1:])
    )


def parse_network(path: Path) -> dict[str, Any]:
    root = ET.parse(path).getroot()
    links: dict[int, dict[str, Any]] = {}
    connectors: dict[int, dict[str, Any]] = {}
    dsds: list[dict[str, Any]] = []

    for link in root.iter("link"):
        no = clean_int(link.get("no"))
        if no is None:
            continue
        points = link_points(link)
        from_ep = link.find("./fromLinkEndPt")
        to_ep = link.find("./toLinkEndPt")
        row = {
            "no": no,
            "name": link.get("name", ""),
            "length_m": float(polyline_length(points)),
            "lane_count": len(link.findall("./lanes/lane")),
            "is_connector": from_ep is not None or to_ep is not None,
        }
        if row["is_connector"]:
            row.update(
                {
                    "from_link": first_int(from_ep.get("lane") if from_ep is not None else None),
                    "from_pos": clean_float(from_ep.get("pos") if from_ep is not None else None),
                    "to_link": first_int(to_ep.get("lane") if to_ep is not None else None),
                    "to_pos": clean_float(to_ep.get("pos") if to_ep is not None else None),
                }
            )
            connectors[no] = row
        links[no] = row

    for dsd in root.iter("desSpeedDecision"):
        lane_ref = dsd.get("lane", "")
        dsds.append(
            {
                "no": clean_int(dsd.get("no")),
                "name": dsd.get("name", ""),
                "link": first_int(lane_ref),
                "lane": lane_no_from_ref(lane_ref),
                "pos_m": clean_float(dsd.get("pos")),
            }
        )

    return {"links": links, "connectors": connectors, "dsds": dsds}


def read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def segment_index(pos_m: float, bounds: list[float]) -> int:
    if len(bounds) < 2:
        return 0
    for idx, upper in enumerate(bounds[1:]):
        if float(pos_m) < float(upper):
            return idx
    return len(bounds) - 2


def round3(value: float) -> float:
    return round(float(value), 3)


# 커넥터별 실측 유량 [veh/h] — 램프 대표 세그먼트의 가중치다.
#
# .fzp 고유 차량 직접 계수(무제어 런, 창 900~5400s). 점유 스냅샷 추정이 아니라 그 커넥터를
# 지난 차량을 센 값이고, 수요 x1.0~x2.4 에 걸쳐 안정적이다.
# 근거: scripts/calibrate_ramp_arrival_20260830.py · outputs/ramp_arrival_calibration_20260830.json
MEASURED_CONNECTOR_VPH = {
    "10480": 233.0, "10482": 521.0,     # R_D_W  둘 다 셀 2
    "10646": 431.0, "10644": 781.0,     # R_F_W  4 대 5 로 갈린다 — 하류가 64%
    "10639": 157.0, "10681": 402.0,     # R_F_E  둘 다 셀 3
    "10490": 453.0, "10484": 486.0,     # R_D_E  둘 다 셀 5
}


def representative_segment(
    entries: list[tuple[float, float]],
    bounds: list[float],
) -> tuple[int, list[int]]:
    """(체인 위치, 가중치) 목록 -> (대표 세그먼트, 실제로 걸친 세그먼트 목록).

    가중치 다수결이다. 산술평균 위치를 대표로 쓰면 구성원이 하나도 없는
    세그먼트가 뽑힐 수 있어 쓰지 않는다. 동률이면 상류(index가 작은 쪽)를
    택한다 - 하류를 고르면 상류 세그먼트에서 유입이 통째로 사라져 밀도가
    과소예측되지만, 상류를 고르면 한 세그먼트 일찍 계상될 뿐이라 보존적이다.

    **동률은 가중치가 틀렸다는 신호다** (2026-08-31). 램프 커넥터가 전부 capacity_vph 900
    으로 같아 동률이 나던 자리를 실측 유량으로 바꾸니 R_F_W 가 4 -> 5 로 뒤집혔고,
    그 셀의 밀도 MAPE 가 49.9% -> 16.8% 로 떨어졌다. "보존적" 이라는 위 논거는 소수
    유입일 때만 성립한다 - R_F_W 는 하류 커넥터가 64% 를 날랐다.
    """
    mass: dict[int, float] = defaultdict(float)
    for chain_pos, weight in entries:
        mass[segment_index(chain_pos, bounds)] += float(weight)
    spanned = sorted(mass)
    best = min(spanned, key=lambda idx: (-mass[idx], idx))
    return best, spanned


def build_chain_geometry(network: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """체인 기하를 네트워크에서 산출한다. 하드코딩된 길이는 쓰지 않는다.

    chain_offsets_m[i] 는 체인 좌표계에서 i번째 멤버 링크가 시작하는 위치이므로
    (link, link 위 pos) -> 체인 좌표 = chain_offsets_m[i] + pos 로 환산된다.
    """
    links = network["links"]
    geometry: dict[str, dict[str, Any]] = {}
    for model, spec in FREEWAY_MAINLINE_CHAIN.items():
        offsets: list[float] = []
        member_lengths: list[float] = []
        total = 0.0
        for link_no in spec["links"]:
            row = links.get(int(link_no))
            if row is None:
                raise KeyError(f"체인 링크 {link_no} 가 네트워크에 없다 (model_link={model})")
            offsets.append(total)
            member_lengths.append(float(row["length_m"]))
            total += float(row["length_m"])
        count = FREEWAY_SEGMENTS_PER_LINK
        bounds = [total * i / count for i in range(count + 1)]
        primary = int(spec["primary_link"])
        geometry[model] = {
            "direction": str(spec["direction"]),
            "primary_link": primary,
            "chain_links": [int(v) for v in spec["links"]],
            "chain_offsets_m": offsets,
            "chain_lengths_m": member_lengths,
            "length_m": total,
            "lanes": int(links[primary].get("lane_count", 4) or 4),
            "segment_bounds_m": bounds,
            "segment_lengths_km": [
                max(1.0e-6, (bounds[i + 1] - bounds[i]) / 1000.0) for i in range(count)
            ],
        }
    return geometry


def chain_link_index(geometry: dict[str, dict[str, Any]]) -> dict[int, tuple[str, float]]:
    """physical link -> (model_link, 그 링크 시작점의 체인 오프셋)."""
    index: dict[int, tuple[str, float]] = {}
    for model, geom in geometry.items():
        for link_no, offset in zip(geom["chain_links"], geom["chain_offsets_m"]):
            index[int(link_no)] = (model, float(offset))
    return index


def chain_position(
    index: dict[int, tuple[str, float]],
    link_no: int | None,
    pos_m: float,
) -> tuple[str | None, float | None]:
    """(link, link 위 pos) -> (model_link, 체인 좌표). 본선 체인 밖이면 (None, None)."""
    entry = index.get(int(link_no)) if link_no is not None else None
    if entry is None:
        return None, None
    model, offset = entry
    return model, offset + float(pos_m)


def build_segments(
    manifest_rows: list[dict[str, str]],
    network: dict[str, Any],
    geometry: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """세그먼트 경계는 체인 기하가 정본이다. 매니페스트는 DSD 번호/차로만 제공한다."""
    rows = [r for r in manifest_rows if r.get("category") == "segment_start_vsl"]
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("segment_id", ""))].append(row)

    segments: list[dict[str, Any]] = []
    installed_dsd_nos: set[int] = set()
    link_index = chain_link_index(geometry)

    def segment_sort_key(item: tuple[str, list[dict[str, str]]]) -> tuple[str, int]:
        first = item[1][0]
        return str(first.get("model_link", "")), int(clean_float(first.get("model_segment_index"), 0.0))

    for segment_id, seg_rows in sorted(grouped.items(), key=segment_sort_key):
        first = seg_rows[0]
        model_link = str(first.get("model_link", ""))
        model_idx = int(clean_float(first.get("model_segment_index"), 0.0))
        physical_link = int(clean_float(first.get("link"), 0.0))
        geom = geometry[model_link]
        bounds = geom["segment_bounds_m"]
        start_m = float(bounds[model_idx])
        end_m = float(bounds[model_idx + 1])
        manifest_start = clean_float(first.get("segment_start_m"))
        if abs(manifest_start - start_m) > 1.0:
            print(
                f"WARN=MANIFEST_SEGMENT_BOUND_DRIFT segment={segment_id} "
                f"manifest_start_m={manifest_start:.3f} chain_start_m={start_m:.3f} "
                "(설치 스크립트를 새 체인으로 다시 돌려야 한다)"
            )
        if physical_link not in link_index:
            print(
                f"WARN=SEGMENT_DSD_OFF_CHAIN segment={segment_id} link={physical_link} "
                "(체인 밖 링크에 VSL DSD가 설치돼 있다)"
            )
        dsd_by_lane: dict[str, dict[str, Any]] = {}
        dsds: list[dict[str, Any]] = []
        for row in sorted(seg_rows, key=lambda r: int(clean_float(r.get("lane"), 0.0))):
            dsd_no = int(clean_float(row.get("no"), 0.0))
            lane = int(clean_float(row.get("lane"), 0.0))
            installed_dsd_nos.add(dsd_no)
            dsd = {
                "dsd_no": dsd_no,
                "lane": lane,
                "pos_m": clean_float(row.get("pos")),
                "source": "installed_real_world_segment_start",
                "name": row.get("name", ""),
            }
            dsd_by_lane[str(lane)] = dsd
            dsds.append(dict(dsd))
        # 설치된 DSD의 실제 체인 좌표. 세그먼트 경계와 어긋날 수 있다 - 링크 경계
        # 근처에서 통과 판정이 누락되지 않도록 설치 스크립트가 DSD를 다음 체인
        # 멤버로 스냅하기 때문이다. 측정 격자는 그대로고 물리 위치만 움직인다.
        dsd_chain_pos: float | None = None
        if dsds:
            _, dsd_chain_pos = chain_position(link_index, physical_link, float(dsds[0]["pos_m"]))
        snap_offset = None if dsd_chain_pos is None else round3(dsd_chain_pos - start_m)
        if snap_offset is not None and snap_offset > 1.0:
            print(
                f"NOTE=SEGMENT_DSD_SNAPPED segment={segment_id} link={physical_link} "
                f"chain_start_m={start_m:.3f} dsd_chain_pos_m={dsd_chain_pos:.3f} "
                f"snap_offset_m={snap_offset:.3f} "
                "(측정 격자는 그대로, 물리 DSD만 이동 - 스냅 구간은 상류 세그먼트의 VSL을 받는다)"
            )
        segments.append(
            {
                "segment_id": segment_id,
                "model_link": model_link,
                "model_segment_index": model_idx,
                "link": physical_link,
                "chain_links": list(geom["chain_links"]),
                "direction": first.get("direction", ""),
                "segment_start_m": round3(start_m),
                "segment_end_m": round3(end_m),
                "dsd_chain_pos_m": None if dsd_chain_pos is None else round3(dsd_chain_pos),
                "dsd_snap_offset_m": snap_offset,
                "length_km": round((end_m - start_m) / 1000.0, 6),
                "lanes": int(geom["lanes"]),
                "dsd_by_lane": dsd_by_lane,
                "extra_dsd_controls": [],
                "dsds": dsds,
                "default_speed_kph": clean_float(first.get("default_speed_kph"), 120.0),
            }
        )

    segment_lookup = {(s["model_link"], s["model_segment_index"]): s for s in segments}
    for dsd in network["dsds"]:
        dsd_no = dsd.get("no")
        physical_link = dsd.get("link")
        if not isinstance(dsd_no, int) or dsd_no in installed_dsd_nos:
            continue
        model_link, chain_pos = chain_position(link_index, physical_link, float(dsd.get("pos_m", 0.0)))
        if model_link is None or chain_pos is None:
            continue
        idx = segment_index(chain_pos, geometry[model_link]["segment_bounds_m"])
        segment = segment_lookup.get((model_link, idx))
        if not segment:
            continue
        extra = {
            "dsd_no": dsd_no,
            "lane": dsd.get("lane"),
            "link": physical_link,
            "pos_m": round3(float(dsd.get("pos_m", 0.0))),
            "chain_pos_m": round3(chain_pos),
            "source": "existing_freeway_mainline_dsd",
            "name": dsd.get("name", ""),
        }
        segment["extra_dsd_controls"].append(extra)
        segment["dsds"].append(dict(extra))

    return segments


def build_ramp_meters(
    manifest_rows: list[dict[str, str]],
    network: dict[str, Any],
    geometry: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int], dict[str, int]]:
    """램프 합류/유출 지점을 체인 좌표로 환산해 세그먼트에 붙인다.

    to_link / to_pos 는 네트워크의 커넥터 끝점이 정본이다. 매니페스트에 박힌
    값은 사용자가 .inpx 기하를 고치면 낡으므로 참고용으로만 남긴다.
    """
    connectors = network["connectors"]
    link_index = chain_link_index(geometry)
    rows_by_id = {
        str(row.get("control_id")): row
        for row in manifest_rows
        if row.get("object_type") == "rampMeter"
    }
    meters: list[dict[str, Any]] = []
    for meter_id in RAMP_METER_ORDER:
        row = rows_by_id[meter_id]
        connector_no = int(clean_float(row.get("connector"), 0.0))
        connector = connectors.get(connector_no, {})
        to_link = int(connector.get("to_link", 0) or clean_float(row.get("to_link"), 0.0))
        to_pos = float(connector.get("to_pos", clean_float(row.get("to_pos"), 0.0)))
        model_link, chain_pos = chain_position(link_index, to_link, to_pos)
        if model_link is None or chain_pos is None:
            raise ValueError(
                f"램프미터 {meter_id} 의 합류 링크 {to_link} 가 본선 체인에 없다 "
                f"({FREEWAY_MAINLINE_CHAIN_CSV} 확인)"
            )
        model_key = str(row.get("model_ramp_key", ""))
        meters.append(
            {
                "id": meter_id,
                "connector": connector_no,
                "from_link": int(connector.get("from_link", 0) or clean_float(row.get("from_link"), 0.0)),
                "from_pos_m": round3(float(connector.get("from_pos", clean_float(row.get("from_pos"), 0.0)))),
                "to_link": to_link,
                "to_pos_m": round3(to_pos),
                "to_chain_pos_m": round3(chain_pos),
                "to_model_link": model_link,
                "to_model_segment_index": segment_index(chain_pos, geometry[model_link]["segment_bounds_m"]),
                "sc_no": int(clean_float(row.get("sc_no"), 0.0)),
                "sg_no": int(clean_float(row.get("sg_no"), 1.0)),
                "default_green_sec": clean_float(row.get("default_green_sec"), 10.0),
                "cycle_sec": 10.0,
                "capacity_vph": clean_float(row.get("capacity_vph"), 900.0),
                "model_ramp_key": model_key,
                "purpose": row.get("purpose", ""),
            }
        )

    by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for meter in meters:
        by_key[str(meter["model_ramp_key"])].append(meter)

    ramp_merge: dict[str, int] = {}
    for key, group in by_key.items():
        model_link = str(group[0]["to_model_link"])
        bounds = geometry[model_link]["segment_bounds_m"]
        # 가중치는 **실측 유량**이다(2026-08-31). capacity_vph 는 커넥터 넷이 전부 900 으로
        # 같아 동률이 되고, 그러면 상류 tie-break 가 이겨 물리적으로 틀린 셀이 뽑힌다.
        #
        #   R_F_W  10646 @6072.6m -> 셀 4 · 실측 431 vph
        #          10644 @6774.3m -> 셀 5 · 실측 781 vph   (하류가 64%)
        #   용량 가중은 900:900 동률 -> 상류 4. 유량 가중은 431:781 -> 5.
        #
        # 오프라인 A/B(무제어 5런 150쌍, 실제 plant freeway_step 으로 150s 전진):
        # FW_W|4 밀도 MAPE 49.9% -> 16.8% · 한-스텝-앞 예측점수 +5.44%.
        # 실측이 없는 커넥터는 capacity_vph 로 폴백한다(기존 거동).
        best, spanned = representative_segment(
            [(float(m["to_chain_pos_m"]),
              float(MEASURED_CONNECTOR_VPH.get(str(m["connector"]), m["capacity_vph"])))
             for m in group],
            bounds,
        )
        ramp_merge[key] = best
        if len(spanned) > 1:
            detail = " ".join(
                f"{m['id']}@seg{int(m['to_model_segment_index'])}"
                f"(chain_m={float(m['to_chain_pos_m']):.3f},cap_vph={float(m['capacity_vph']):.0f})"
                for m in group
            )
            print(
                f"WARN=RAMP_GROUP_SEGMENT_STRADDLE ramp={key} model_link={model_link} "
                f"segments={spanned} representative={best} "
                f"rule=capacity_weighted_majority_upstream_tiebreak {detail} "
                "note=zone_ownership_unaffected_prediction_accuracy_only"
            )

    off_ramp_index: dict[str, int] = {}
    for key, connector_nos in OFF_RAMP_GROUPS.items():
        chain_positions: list[float] = []
        model_link = ""
        for connector_no in connector_nos:
            connector = connectors.get(connector_no)
            if not connector:
                continue
            model, chain_pos = chain_position(
                link_index,
                int(connector.get("from_link", 0) or 0),
                float(connector.get("from_pos", 0.0)),
            )
            if model is None or chain_pos is None:
                continue
            model_link = model
            chain_positions.append(chain_pos)
        if chain_positions and model_link:
            # 오프램프는 용량 정보가 없어 동일 가중치다. 규칙은 램프미터와 같다.
            best, spanned = representative_segment(
                [(p, 1.0) for p in chain_positions],
                geometry[model_link]["segment_bounds_m"],
            )
            off_ramp_index[key] = best
            if len(spanned) > 1:
                print(
                    f"WARN=OFF_RAMP_GROUP_SEGMENT_STRADDLE off_ramp={key} model_link={model_link} "
                    f"segments={spanned} representative={best} "
                    "rule=equal_weight_majority_upstream_tiebreak"
                )

    return meters, ramp_merge, off_ramp_index


def build_detector_mapping(
    network: dict[str, Any],
    geometry: dict[str, dict[str, Any]],
    meters: list[dict[str, Any]],
    ramp_merge_index: dict[str, int],
    off_ramp_index: dict[str, int],
) -> dict[str, Any]:
    connectors = network["connectors"]
    link_index = chain_link_index(geometry)
    link_to_origins: dict[str, list[str]] = {}
    link_to_movements: dict[str, list[dict[str, Any]]] = {}
    ramp_link_to_queues: dict[str, list[str]] = {}
    off_ramp_details: dict[str, list[dict[str, Any]]] = {}

    for off_ramp, connector_nos in OFF_RAMP_GROUPS.items():
        entries: list[dict[str, Any]] = []
        signal = off_ramp.split("_")[1] if "_" in off_ramp else ""
        movements = OFF_RAMP_MOVEMENTS.get(off_ramp, [])
        for connector_no in connector_nos:
            connector = connectors.get(connector_no)
            if not connector:
                continue
            link_key = str(connector_no)
            link_to_origins[link_key] = [off_ramp]
            link_to_movements[link_key] = [
                {
                    "movement": movement,
                    "weight": 1.0,
                    "signal": signal,
                    "phase": f"{signal}_p1" if signal else "",
                    "kind": "off_ramp",
                    "origin": off_ramp,
                }
                for movement in movements
            ]
            entries.append(
                {
                    "connector": connector_no,
                    "from_link": int(connector.get("from_link", 0) or 0),
                    "from_pos_m": round3(float(connector.get("from_pos", 0.0) or 0.0)),
                    "to_link": int(connector.get("to_link", 0) or 0),
                    "to_pos_m": round3(float(connector.get("to_pos", 0.0) or 0.0)),
                    "lanes": int(connector.get("lane_count", 0) or 0),
                }
            )
        off_ramp_details[off_ramp] = entries

    for meter in meters:
        ramp_link_to_queues[str(meter["connector"])] = [str(meter["model_ramp_key"])]

    agents: dict[str, dict[str, Any]] = {}
    for signal in ["A", "B", "C", "D", "F"]:
        off_ramps = sorted(
            off_ramp
            for off_ramp in OFF_RAMP_GROUPS
            if off_ramp.startswith(f"OR_{signal}_")
        )
        ramps = sorted(
            ramp
            for ramp, ramp_signal in MODEL_RAMP_TO_URBAN_SIGNAL.items()
            if ramp_signal == signal
        )
        visible_links = sorted(
            {
                str(connector)
                for off_ramp in off_ramps
                for connector in OFF_RAMP_GROUPS.get(off_ramp, [])
            }
            | {
                str(meter["connector"])
                for meter in meters
                if str(meter["model_ramp_key"]) in ramps
            },
            key=lambda value: int(value),
        )
        visible_movements = sorted(
            movement
            for off_ramp in off_ramps
            for movement in OFF_RAMP_MOVEMENTS.get(off_ramp, [])
        )
        agents[urban_agent_id(signal)] = {
            "kind": "urban",
            "signal": signal,
            "visible_links": visible_links,
            "visible_movements": visible_movements,
            "visible_ramps": ramps,
            "visible_off_ramps": off_ramps,
        }

    off_ramp_model_link: dict[str, str] = {}
    for off_ramp, connector_nos in OFF_RAMP_GROUPS.items():
        for connector_no in connector_nos:
            entry = link_index.get(int(connectors.get(connector_no, {}).get("from_link", 0) or 0))
            if entry is not None:
                off_ramp_model_link[off_ramp] = entry[0]
                break
    for model_link, geom in geometry.items():
        for segment_index in range(FREEWAY_SEGMENTS_PER_LINK):
            visible_ramps = sorted(
                ramp
                for ramp, idx in ramp_merge_index.items()
                if int(idx) == segment_index
                and any(
                    str(meter["model_ramp_key"]) == ramp
                    and str(meter["to_model_link"]) == model_link
                    for meter in meters
                )
            )
            visible_off_ramps = sorted(
                off_ramp
                for off_ramp, idx in off_ramp_index.items()
                if int(idx) == segment_index
                and off_ramp_model_link.get(off_ramp) == model_link
            )
            agents[freeway_agent_id(model_link, segment_index)] = {
                "kind": "freeway",
                "model_link": model_link,
                "segment_index": segment_index,
                "visible_links": [str(link) for link in geom["chain_links"]],
                "visible_movements": [],
                "visible_ramps": visible_ramps,
                "visible_off_ramps": visible_off_ramps,
            }

    observable_links = sorted(
        {
            *(int(link) for link in link_to_origins),
            *(int(link) for link in ramp_link_to_queues),
            *FREEWAY_CHAIN_LINKS,
        }
    )
    return {
        "schema_version": 1,
        "mapping_version": "real_world_modi_connector_local_v1_20260720",
        "description": (
            "Real-world Gaepo modi connector-local observation mapping. "
            "Off-ramp connector counts feed OR_* storage/movement queues; "
            "ramp-meter connector counts feed R_* queues."
        ),
        "observable_links": observable_links,
        "link_to_origins": link_to_origins,
        "link_to_movements": link_to_movements,
        "ramp_link_to_queues": ramp_link_to_queues,
        "boundary_link_to_queue": {},
        "freeway_link_to_model_link": {
            str(link): model
            for model, geom in geometry.items()
            for link in geom["chain_links"]
        },
        "off_ramp_connectors": off_ramp_details,
        "agents": agents,
        "guardrails": {
            "leader_visibility": "global_state_allowed",
            "follower_visibility": "real_world_connector_local_links_only",
            "adapter_global_fallback_allowed_only_when_local_observation_absent": True,
            "vissim_internal_scan_is_masked_before_controller": True,
            "urban_signal_actuation": "freeway_interface_sc1_enabled",
        },
    }


def write_vbs_config(
    path: Path,
    geometry: dict[str, dict[str, Any]],
    meters: list[dict[str, Any]],
    detector_mapping_path: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    def csv_nums(values: list[float]) -> str:
        return ",".join(f"{float(v):.6f}" for v in values)

    lines = [
        "' Generated by scripts/generate_real_world_control_mapping.py",
        # 2: 본선이 링크 체인이 되면서 RW_*_CHAIN_LINKS / RW_*_CHAIN_OFFSETS_M 가 필수다.
        "RW_SCHEMA_VERSION = 2",
        'RW_FREEWAY_LINKS = "' + ",".join(str(v) for v in FREEWAY_CHAIN_LINKS) + '"',
        'RW_FREEWAY_INPUT_LINKS = "26,74"',
        "RW_CLASSIFY_UNMATCHED_AS_URBAN = True",
    ]
    for model, geom in geometry.items():
        lines.extend(
            [
                f"RW_{model}_LINK = {int(geom['primary_link'])}",
                f"RW_{model}_LENGTH_M = {float(geom['length_m']):.6f}",
                f"RW_{model}_LANES = {int(geom['lanes'])}",
                f'RW_{model}_CHAIN_LINKS = "' + ",".join(str(v) for v in geom["chain_links"]) + '"',
                f'RW_{model}_CHAIN_OFFSETS_M = "{csv_nums(geom["chain_offsets_m"])}"',
                f'RW_{model}_SEG_BOUNDS = "{csv_nums(geom["segment_bounds_m"])}"',
                f'RW_{model}_SEG_LENGTHS_KM = "{csv_nums(geom["segment_lengths_km"])}"',
            ]
        )
    lines.extend(
        [
            'RW_RAMP_METER_IDS = "' + ",".join(m["id"] for m in meters) + '"',
            'RW_RAMP_METER_SCS = "' + ",".join(str(m["sc_no"]) for m in meters) + '"',
            'RW_RAMP_METER_CONNECTORS = "' + ",".join(str(m["connector"]) for m in meters) + '"',
            'RW_RAMP_METER_MODEL_KEYS = "' + ",".join(str(m["model_ramp_key"]) for m in meters) + '"',
            'RW_SIGNAL_SCS = "'
            + ",".join(str(row["sc_no"]) for row in REAL_WORLD_INTERFACE_SIGNALS)
            + '"',
            'RW_LOCAL_OBSERVABLE_LINKS = "'
            + ",".join(
                str(v)
                for v in sorted(
                    {
                        *FREEWAY_CHAIN_LINKS,
                        *(int(m["connector"]) for m in meters),
                        *(
                            int(connector)
                            for connectors in OFF_RAMP_GROUPS.values()
                            for connector in connectors
                        ),
                    }
                )
            )
            + '"',
            'RW_DETECTOR_MAPPING_PATH = "' + str(detector_mapping_path).replace('"', '""') + '"',
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build_payloads(
    network_path: Path,
    manifest_path: Path,
    mapping_path: Path,
    calibration_path: Path,
    tuning_path: Path,
    player_config_path: Path,
    vbs_config_path: Path,
    detector_mapping_path: Path,
) -> None:
    manifest_rows = read_manifest(manifest_path)
    network = parse_network(network_path)
    geometry = build_chain_geometry(network)
    bounds_by_model = {model: geom["segment_bounds_m"] for model, geom in geometry.items()}
    lengths_km_by_model = {model: geom["segment_lengths_km"] for model, geom in geometry.items()}
    segments = build_segments(manifest_rows, network, geometry)
    meters, ramp_merge_index, off_ramp_index = build_ramp_meters(manifest_rows, network, geometry)
    detector_mapping_payload = build_detector_mapping(
        network, geometry, meters, ramp_merge_index, off_ramp_index
    )

    meters_by_model: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for meter in meters:
        meters_by_model[str(meter["model_ramp_key"])].append(meter)
    ramp_capacity = {
        key: round(sum(float(m["capacity_vph"]) for m in group), 3)
        for key, group in meters_by_model.items()
    }
    for key in ("R_D_W", "R_D_E", "R_F_W", "R_F_E"):
        ramp_capacity.setdefault(key, 1800.0)

    avg_segment_km = sum(sum(v) for v in lengths_km_by_model.values()) / max(
        1,
        sum(len(v) for v in lengths_km_by_model.values()),
    )
    freeway_lanes = min(int(geom["lanes"]) for geom in geometry.values())

    mapping_payload = {
        "schema_version": 1,
        "created_at": "2026-07-19",
        "network": str(network_path),
        "manifest": str(manifest_path),
        "description": (
            "Real-world Gaepo modi freeway control mapping: VSL on the FW_E/FW_W mainline "
            "link chains and physical ramp meters on eight on-ramp connectors."
        ),
        "freeway_mainline_chain_source": str(FREEWAY_MAINLINE_CHAIN_CSV),
        "freeway_model_links": {
            model: {
                "physical_link": int(geom["primary_link"]),
                "chain_links": list(geom["chain_links"]),
                "chain_offsets_m": [round3(v) for v in geom["chain_offsets_m"]],
                "chain_lengths_m": [round3(v) for v in geom["chain_lengths_m"]],
                "length_m": round3(geom["length_m"]),
                "lanes": int(geom["lanes"]),
                "segment_bounds_m": [round3(v) for v in geom["segment_bounds_m"]],
                "segment_length_profile_km": [round(v, 6) for v in geom["segment_lengths_km"]],
            }
            for model, geom in geometry.items()
        },
        "segments": segments,
        "signals": [dict(row) for row in REAL_WORLD_INTERFACE_SIGNALS],
        "ramp_meters": meters,
        "ramp_meter_groups": {
            key: {
                "model_ramp_key": key,
                "physical_meter_ids": [m["id"] for m in group],
                "physical_connectors": [m["connector"] for m in group],
                "physical_segment_indices": [int(m["to_model_segment_index"]) for m in group],
                "representative_segment_index": int(ramp_merge_index[key]),
                "segment_straddle": len({int(m["to_model_segment_index"]) for m in group}) > 1,
                "total_capacity_vph": round(sum(float(m["capacity_vph"]) for m in group), 3),
            }
            for key, group in sorted(meters_by_model.items())
        },
        "model_topology_overrides": {
            "ramp_merge_segment_index": ramp_merge_index,
            "off_ramp_segment_index": off_ramp_index,
            "ramp_capacity_veh_h": ramp_capacity,
            "freeway_lanes": freeway_lanes,
            "freeway_segment_length_km": round(avg_segment_km, 6),
        },
        "excluded_freeway_touching_connectors": [
            {
                "connector": 10699,
                "from_link": 74,
                "to_link": 2,
                "reason": "FW_E mainline chain member (link 74 -> link 2), not isolated ramp metering authority.",
            }
        ],
        # 알고 있고 받아들인 근사. 측정 격자(segment_bounds_m)는 두 항목 모두에서
        # 손대지 않는다 - 움직이는 것은 물리 설치 위치와 모델 주입 세그먼트뿐이다.
        "known_approximations": [
            {
                "id": "vsl_dsd_edge_snap",
                "source": "scripts/install_real_world_freeway_controls.vbs (DSD_EDGE_CLEARANCE_M)",
                "what": (
                    "체인 멤버가 끝나는 지점(커넥터 fromLinkEndPt) 40 m 안에 떨어지는 세그먼트 시작은 "
                    "DSD를 다음 실호스트 멤버의 진입점+40 m 로 옮긴다. 40 m = SimRes 1(dt 1.0 s) x "
                    "자유류 상단 130 km/h(36.1 m/s) 한 스텝 + 여유."
                ),
                "cost": (
                    "세그먼트 시작과 실제 DSD 사이 구간의 차량은 상류 세그먼트의 VSL을 받는다. "
                    "세그먼트별 dsd_snap_offset_m 에 크기가 적혀 있다."
                ),
                "why_accepted": "링크 경계 직전 배치는 통과 판정 누락으로 VSL 채널이 조용히 죽을 수 있고, 액션 CSV readback은 DSD 속성을 되읽으므로 이를 잡지 못한다.",
            },
            {
                "id": "ramp_group_segment_straddle",
                "source": "scripts/generate_real_world_control_mapping.py (build_ramp_meters)",
                "what": (
                    "한 model_ramp_key 의 물리 미터가 서로 다른 세그먼트에 합류하면 용량 가중 다수결로 "
                    "대표 세그먼트 하나를 고른다(동률이면 상류). 산술평균은 미터가 없는 세그먼트를 "
                    "고를 수 있어 쓰지 않는다."
                ),
                "cost": "대표가 아닌 세그먼트로 들어가는 유입이 모델에서는 대표 세그먼트에 주입된다. ramp_meter_groups[*].segment_straddle 로 식별한다.",
                "why_accepted": "제어 배분에는 영향이 없다 - straddle 하는 두 세그먼트가 같은 zone 소유이므로 예측 정확도 항목이다.",
            },
            {
                "id": "vsl_segment0_entry_clearance",
                "source": "scripts/install_real_world_freeway_controls.vbs (segment 0 exception removed)",
                "what": (
                    "세그먼트 0의 DSD도 다른 세그먼트와 동일하게 체인 진입점 + DSD_EDGE_CLEARANCE_M(40 m)에 놓인다. "
                    "이전에는 세그먼트 0만 pos 1.0으로 강제됐고, 그 자리는 원 네트워크의 진입부 DSD"
                    "(no 36~42, pos 1.5~11.9, 분포 100)보다 상류라 우리 VSL이 10 m 뒤에서 덮여 사라졌다"
                    "(실측 자기지문 FW_E S0 1.3%, FW_W S0 21.8%)."
                ),
                "cost": (
                    "체인 [0, 진입점+40 m) 구간에는 VSL이 적용되지 않는다. 상류 세그먼트가 없으므로 그 구간의 차량은 "
                    "유입 구성의 원 희망속도 분포를 유지하고, 레거시 DSD 36~42를 만나는 지점부터는 그 분포를 따른다"
                    "(레거시 DSD도 extra_dsd_controls 로 같은 VSL을 받으므로 실질 개시점은 레거시 DSD 위치다). "
                    "측정 격자(segment_bounds_m)는 손대지 않았다 - 움직인 것은 물리 DSD 위치뿐이며 "
                    "크기는 세그먼트별 dsd_snap_offset_m 에 적혀 있다."
                ),
                "why_accepted": "40 m 미적용 구간은 세그먼트 길이 약 1347 m의 3%이고, 그 대가로 S0 채널 전체가 레거시 DSD 덮어쓰기에서 벗어난다.",
            },
            {
                "id": "vsl_taxi_class70_included",
                "source": (
                    "scripts/install_real_world_freeway_controls.vbs (AddVslDsds), "
                    "scripts/run_real_world_stackelberg_controller.vbs (ApplyActionCsv)"
                ),
                "what": (
                    "차량 클래스 70(TAXI, 차종 150)이 VSL 대상에 편입됐다. RW DSD 64개와 런타임에서 값을 받는 "
                    "레거시 DSD(extra_dsd_controls) 모두 클래스 10/20/30/70 네 개에 같은 분포를 지정한다. "
                    "이전에는 본선 체인 위 71개 DSD 전부가 클래스 70을 비워 두어 택시가 유입 구성의 분포 40"
                    "(40~45 km/h)을 본선 전 구간에서 유지했다."
                ),
                "cost": (
                    "원 네트워크는 택시를 본선에서 40~45 km/h를 희망하는 이동 장애물로 모델링했는데, 이제 택시도 "
                    "지시 VSL(무제어 기본 120)을 희망한다. 즉 플랜트의 자유류 속도와 용량이 올라간다. "
                    "이 변경 이전의 모든 VISSIM 런과 비교 불가다"
                    "(outputs/vsl_class70_plant_change_20260801.md)."
                ),
                "why_accepted": (
                    "본선 표본의 14.45%가 클래스 70이라 편입하지 않으면 VSL의 이론적 최대 적용률이 약 85%로 묶인다. "
                    "제어 권한(authority) 분석이 성립하려면 대상 집합이 본선 차량 전체여야 한다는 사용자 결정. "
                    "다른 클래스와 다른 분포를 물리면(예: min(VSL, 40)) VSL 메뉴 하한이 50 km/h라 택시는 사실상 "
                    "영원히 미적용이 되어 편입 결정과 모순된다."
                ),
            },
        ],
    }

    calibration_payload = {
        "schema_version": 1,
        "created_at": "2026-07-19",
        "calibration_version": "real_world_modi_control_v0_20260719",
        "status": "geometry_and_control_authority_defined_uncalibrated_response",
        "source_network": str(network_path),
        "source_mapping": str(mapping_path),
        "physical_inventory": {
            "notes": [
                "Initial real-world geometry/control-authority profile for Gaepo modi.",
                "Response curves are engineering defaults; run dedicated VISSIM response calibration before treating them as fitted.",
                "Connector 10699 is excluded from ramp metering because it is a freeway feeder/mainline entry.",
            ],
            "freeway_segment_length_profile_km": {
                model: [round(v, 6) for v in values]
                for model, values in lengths_km_by_model.items()
            },
            "freeway_segment_bounds_m": {
                model: [round3(v) for v in values]
                for model, values in bounds_by_model.items()
            },
            "ramp_meter_connectors": meters,
        },
        "operational": {
            "network": {
                "v_free_kph": 100.0,
                "rho_crit_veh_km_lane": 24.0,
                "freeway_capacity_veh_h": 7600.0,
            },
            "ramp_metering": {
                "D_green_to_release_vph_initial_mpc": {"0": 0.0, "10": 1800.0},
                "F_green_to_release_vph_raw": {"0": 0.0, "10": 1800.0},
                "F_status": "real_world_metering_available",
            },
            "signal": {
                "recommended_initial_lost_time_sec": 6.0,
                "recommended_initial_saturation_flow_vph_approach": 1800.0,
            },
            "urban_mfd": {
                "N_P_crit_veh_initial": 600.0,
            },
        },
    }

    tuning_payload = {
        "name": "real_world_modi_pstack_adapter_v0_20260719",
        "description": "Initial real-world Gaepo modi P-Stack adapter config. It keeps original VISSIM demand, maps P-Stack FW_E/FW_W controls to physical links 2/26, and distributes each model ramp-meter rate across two physical on-ramp meters.",
        "mapping_json": str(mapping_path),
        "calibration_json": str(calibration_path),
        "detector_mapping_json": str(detector_mapping_path),
        "config_overrides": {
            "network": {
                "freeway_links": ["FW_W", "FW_E"],
                "freeway_segments_per_link": FREEWAY_SEGMENTS_PER_LINK,
                "freeway_lanes": freeway_lanes,
                "freeway_segment_length_km": round(avg_segment_km, 6),
                "ramp_merge_segment_index": ramp_merge_index,
                "off_ramp_segment_index": off_ramp_index,
                "ramp_capacity_veh_h": ramp_capacity,
            }
        },
        "actuation": {
            "allow_invalid_F_metering": True,
            "F_ramp_mode": "metered",
            "real_world_ramp_metering": {
                "enabled": True,
                "cycle_sec": 10.0,
                "min_green_sec": 0.0,
                "max_green_sec": 10.0,
                "per_meter_capacity_vph": 900.0,
                "distribute_model_rate_across_meters": True,
            },
        },
    }

    player_config_payload = {
        "schema_version": 1,
        "created_at": "2026-07-19",
        "network": str(network_path),
        "players": [
            {
                "id": "leader_network_manager",
                "kind": "leader",
                "state_scope": (
                    "whole network split into the FW_E/FW_W mainline link chains "
                    f"({FREEWAY_CHAIN_LINKS}) and urban remainder"
                ),
                "controlled_followers": ["freeway_follower_real_world", "urban_follower_monitor"],
            },
            {
                "id": "freeway_follower_real_world",
                "kind": "freeway_follower",
                "model_links": sorted(geometry),
                "physical_links": list(FREEWAY_CHAIN_LINKS),
                "vsl_segments": [s["segment_id"] for s in segments],
                "ramp_meters": [m["id"] for m in meters],
                "excluded_connector_controls": [10699],
            },
            {
                "id": "urban_follower_monitor",
                "kind": "urban_follower",
                "state_scope": "all non-freeway links",
                "controlled_signal_controllers": [
                    int(row["sc_no"]) for row in REAL_WORLD_INTERFACE_SIGNALS
                ],
                "local_observation": str(detector_mapping_path),
                "note": "SC 1 is exposed as the D/F freeway-interface signal lever; D/F off-ramp and ramp connector counts are exposed through detector-local observation.",
            },
        ],
    }

    write_json(mapping_path, mapping_payload)
    write_json(detector_mapping_path, detector_mapping_payload)
    write_json(calibration_path, calibration_payload)
    write_json(tuning_path, tuning_payload)
    write_json(player_config_path, player_config_payload)
    write_vbs_config(vbs_config_path, geometry, meters, detector_mapping_path)

    print(f"MAPPING={mapping_path}")
    print(f"DETECTOR_MAPPING={detector_mapping_path}")
    print(f"CALIBRATION={calibration_path}")
    print(f"TUNING={tuning_path}")
    print(f"PLAYER_CONFIG={player_config_path}")
    print(f"VBS_CONFIG={vbs_config_path}")
    print(f"SEGMENTS={len(segments)} RAMP_METERS={len(meters)}")


def workspace_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else WORKSPACE_ROOT / path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--network",
        default="network/real_world_gaepo_modi/modi_eval_rw_control.inpx",
    )
    parser.add_argument(
        "--manifest",
        default="evaluation/real_world_modi_control/freeway_control_manifest.csv",
    )
    parser.add_argument(
        "--mapping-json",
        default="evaluation/real_world_modi_control/control_mapping.json",
    )
    parser.add_argument(
        "--calibration-json",
        default="evaluation/calibration/real_world_modi_control_v0_20260719.json",
    )
    parser.add_argument(
        "--tuning-json",
        default="evaluation/configs/real_world_modi_pstack_adapter_v0_20260719.json",
    )
    parser.add_argument(
        "--player-config-json",
        default="evaluation/real_world_modi_control/player_config.json",
    )
    parser.add_argument(
        "--detector-mapping-json",
        default="evaluation/real_world_modi_control/detector_local_mapping.json",
    )
    parser.add_argument(
        "--vbs-config",
        default="evaluation/generated/real_world_modi_control_config.vbs",
    )
    args = parser.parse_args()

    network = workspace_path(args.network)
    manifest = workspace_path(args.manifest)
    if not network.exists():
        raise FileNotFoundError(network)
    if not manifest.exists():
        raise FileNotFoundError(manifest)

    build_payloads(
        network,
        manifest,
        workspace_path(args.mapping_json),
        workspace_path(args.calibration_json),
        workspace_path(args.tuning_json),
        workspace_path(args.player_config_json),
        workspace_path(args.vbs_config),
        workspace_path(args.detector_mapping_json),
    )


if __name__ == "__main__":
    main()
