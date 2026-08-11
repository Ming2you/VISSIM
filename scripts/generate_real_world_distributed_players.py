from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SIGNAL_ROLES = ROOT / "evaluation/real_world_modi_inventory/signal_controller_roles.csv"
DEFAULT_CONTROL_MAPPING = ROOT / "evaluation/real_world_modi_control/control_mapping.json"
DEFAULT_DETECTOR_MAPPING = ROOT / "evaluation/real_world_modi_control/detector_local_mapping.json"
DEFAULT_NETWORK = ROOT / "network/real_world_gaepo_modi/modi_eval_rw_control.inpx"
DEFAULT_PREDICTION_CALIBRATION = ROOT / "evaluation/calibration/real_world_prediction_calibration_pshb4500fix_20260724.json"
OUT_DIR = ROOT / "evaluation/real_world_modi_control_distributed_20260728"
CONFIG_DIR = ROOT / "evaluation/configs"
GENERATED_DIR = ROOT / "evaluation/generated"
OUTPUTS_DIR = ROOT / "outputs"

# ---------------------------------------------------------------------------
# Urban Follower ID ↔ VISSIM SC (2026-07-31 정정)
#
# 이전 구현은 사용자가 표시한 플레이어 번호를 VISSIM SC 번호로 착각해 그대로
# 박아넣었다(구 CORE15_SC_NUMBERS 주석 "Manual interpretation of the user's
# 2026-07-28 marked-up 15-player core"). 두 체계는 다르다 — UF1→SC1004,
# UF8→SC1, UF15→SC5. 그 결과 15core는 15개 중 8개가, primary19는 SC 1~19를
# 그대로 써서 19개 중 14개가 엉뚱한 신호기를 제어하고 있었다.
#
# 이제 매핑은 사용자 검증 원본(Urban-Follower.xlsx)에서 기계 추출한 CSV가
# 유일한 근거다(scripts/extract_urban_follower_map.py). 수동 해석 금지.
# ---------------------------------------------------------------------------
DEFAULT_URBAN_FOLLOWER_MAP = ROOT / "evaluation/real_world_modi_inventory/urban_follower_sc_map.csv"

# 사용자 지정 코어 15 플레이어 = Urban Follower ID 1~16 중 11 제외.
# ★ 이 값은 UF ID다. SC 번호가 아니다.
CORE15_URBAN_FOLLOWER_IDS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14, 15, 16]


def load_urban_follower_sc_map(path: Path = DEFAULT_URBAN_FOLLOWER_MAP) -> dict[int, int]:
    """UF ID → SC 번호. CSV가 없으면 추출 스크립트를 실행하라고 알린다."""
    if not path.exists():
        raise SystemExit(
            f"UF→SC 매핑 CSV가 없다: {path}\n"
            "  python scripts/extract_urban_follower_map.py 를 먼저 실행할 것."
        )
    return {int(row["urban_follower_id"]): int(row["sc_no"]) for row in read_csv(path)}


def urban_follower_scs(uf_ids: list[int], uf_map: dict[int, int]) -> list[int]:
    unknown = sorted(set(uf_ids) - set(uf_map))
    if unknown:
        raise ValueError(f"매핑에 없는 Urban Follower ID: {unknown}")
    return sorted(uf_map[uf] for uf in uf_ids)


# ---------------------------------------------------------------------------
# VISSIM vehicle input -> 모델 경계 leg (2026-08-11)
#
# 유입 이름의 **진행방향** 접미사가 접근 leg 의 정본이다. NB(북행)로 들어오는 차는
# 교차로의 **남쪽** 접근로에 선다 -> NB->S. 이름이 없으면 기하 추정을 쓴다
# (`outputs/boundary_input_alignment_20260811.json` 의 `leg.link_geometry`).
#
# 이 우선순위를 뒤집으면 안 된다. 기하를 primary 로 두면 정렬되는 유입이 22개 중
# 11개로 줄고(같은 산출물 summary.by_estimator.link_geometry.aligned = 11),
# 이름이 있는 14개 중 9개가 대각 방위로 잘못 떨어진다.
TRAVEL_SUFFIX_TO_APPROACH_LEG = {"NB": "S", "SB": "N", "EB": "W", "WB": "E"}
TRAVEL_SUFFIX_RE = re.compile(r"(?<![A-Za-z])(NB|SB|EB|WB)(?![A-Za-z])")


def boundary_gate_plan_from_alignment(
    alignment: dict[str, Any],
) -> tuple[dict[str, list[str]], list[dict[str, Any]]]:
    """정렬 산출물 -> {노드: [경계 leg 방위]} 와 근거 행.

    센다/안 센다 규칙은 사용자 확정 사실을 그대로 따른다.
      - `role != "urban_input"` (고속도로 본선·피더)은 도시부 경계 게이트가 아니다.
      - `entry_class == "dummy"` (Dummy Link 1~12, 10개)는 **내부 발생**이라 망 입구가 아니다.
    남는 것이 진짜 망 입구 22개다.
    """
    plan: dict[str, list[str]] = {}
    evidence: list[dict[str, Any]] = []
    for entry in alignment.get("vehicle_inputs") or []:
        if str(entry.get("role", "")) != "urban_input":
            continue
        if str(entry.get("entry_class", "")) == "dummy":
            continue
        vi_no = str(entry.get("vehicle_input_no", ""))
        name = str(entry.get("name") or "")
        node = entry.get("model_node")
        suffixes = TRAVEL_SUFFIX_RE.findall(name)
        if suffixes:
            leg, source = TRAVEL_SUFFIX_TO_APPROACH_LEG[suffixes[-1]], "name_suffix"
        else:
            leg, source = (entry.get("leg") or {}).get("link_geometry"), "link_geometry"
        if not node or not leg:
            raise SystemExit(
                f"경계 유입 {vi_no}({name!r})의 접근 leg 을 정할 수 없다: "
                f"node={node!r} leg={leg!r}. 정렬 산출물을 다시 만들 것."
            )
        legs = plan.setdefault(str(node), [])
        if leg not in legs:
            legs.append(str(leg))
        evidence.append({
            "vehicle_input_no": vi_no,
            "name": name,
            "node": str(node),
            "leg": str(leg),
            "source": source,
            "volumes_vph": list(entry.get("volumes_vph") or []),
        })
    return {node: sorted(legs) for node, legs in sorted(plan.items())}, evidence


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def ensure_numsim_importable() -> Path:
    """NumSim 소스를 `sys.path` 에 올리고 그 루트를 돌려준다."""
    candidates = [
        Path(os.environ["NUMSIM_REPO_ROOT"]) if os.environ.get("NUMSIM_REPO_ROOT") else None,
        ROOT / "vendor" / "NumSim-mine",
        ROOT.parent / "NumSim-mine",
    ]
    numsim_path = next(
        (candidate for candidate in candidates if candidate and (candidate / "src").is_dir()),
        None,
    )
    if numsim_path is None:
        raise SystemExit("NumSim source not found; set NUMSIM_REPO_ROOT or restore vendor/NumSim-mine")
    numsim = str(numsim_path)
    if numsim not in sys.path:
        sys.path.insert(0, numsim)
    return numsim_path


# ---------------------------------------------------------------------------
# 녹색 예산 계약 (2026-08-11)
#
# 다섯 값 중 자유 파라미터는 셋뿐이다 — 계약 원문은 `evaluation/controllers/plant_cycle.py`
# 모듈 docstring 에 한 번만 적혀 있다.
#
#     자유  cycle_length  부모 config 체인 (없으면 NumSim NetworkConfig 기본값)
#     자유  green_min     같음
#     자유  lost_time     러너 원문의 2 x (AMBER_SEC + ALL_RED_SEC)
#     유도  effective_green_total = cycle_length - lost_time
#     유도  green_max             = effective_green_total - green_min
#
# 유도값 둘은 **생성기가 산출물에 실어야 한다.** 안 실으면 모델이 NetworkConfig 기본값
# (lost_time=8.0, green_max=92.0)으로 떨어지는데, 그 기본값은 자기들끼리는 항등식을
# 만족해서(20 + 92 == 120 - 8) 예산 검사로는 아무것도 안 걸린다. 어긋나는 것은 플랜트
# 주기다 — 러너 clearance 가 10 s 라 모델 주기가 2 s 짧아진다(a1e73da 가 생산 config 에
# 손으로 넣어 닫았던 그 간극).
# ---------------------------------------------------------------------------
PARENT_CONFIG = "real_world_modi_pstack_vsl_rollout_vissimdsd_20260725.json"


def resolved_parent_network(parent_path: Path) -> dict[str, Any]:
    """부모 config 체인이 실제로 정한 `config_overrides.network`.

    자식(이 생성기가 쓰는 config)이 아무것도 안 얹은 상태의 기준선이다. 어댑터의
    `load_optional_json` 과 같은 순서로 조상부터 덮어쓴다.
    """
    chain: list[dict[str, Any]] = []
    path = Path(parent_path)
    while True:
        cfg = read_json(path)
        chain.append(cfg)
        extends = str(cfg.get("extends") or "")
        if not extends:
            break
        parent = Path(extends)
        path = parent if parent.is_absolute() else path.parent / parent
    merged: dict[str, Any] = {}
    for cfg in reversed(chain):
        merged.update((cfg.get("config_overrides") or {}).get("network") or {})
    return merged


def green_budget_contract(parent_path: Path) -> dict[str, float]:
    """녹색 예산 계약의 **유도값 둘** — `lost_time` 과 `green_max` [s].

    숫자를 복사해 두지 않는다. `lost_time` 은 러너 VBS 원문에서 읽고,
    `cycle_length` / `green_min` 은 부모 체인(없으면 NumSim `NetworkConfig` 기본값)에서
    읽는다. 어느 한쪽이 바뀌면 여기서 나오는 값이 따라 움직인다.
    """
    ensure_numsim_importable()
    from src.models.state import NetworkConfig

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from evaluation.controllers.plant_cycle import plant_lost_time_sec

    defaults = NetworkConfig()
    parent = resolved_parent_network(parent_path)
    cycle_length = float(parent.get("cycle_length", defaults.cycle_length))
    green_min = float(parent.get("green_min", defaults.green_min))
    lost_time = float(plant_lost_time_sec())
    return {
        "lost_time": lost_time,
        "green_max": cycle_length - lost_time - green_min,
    }


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_link_assignment(
    path: Path,
    assignment: dict[str, Any],
    approval_manifest_path: Path | None,
) -> dict[str, Any]:
    assignment_sha256 = file_sha256(path)
    if assignment.get("unresolved_tie_count") == 0 and str(assignment.get("tie_status", "")).upper() == "CLEAR":
        return {
            "status": "clear",
            "assignment_sha256": assignment_sha256,
            "approval_manifest": "",
            "approval_manifest_sha256": "",
        }

    if approval_manifest_path is None:
        raise SystemExit(
            "link assignment has unresolved or unverifiable topology ties; refusing to generate live artifacts. "
            "Regenerate a CLEAR assignment or pass --assignment-approval-manifest with an explicit, hash-bound approval."
        )
    approval = read_json(approval_manifest_path)
    if approval.get("approved") is not True:
        raise SystemExit(f"assignment approval is not approved: {approval_manifest_path}")
    if str(approval.get("assignment_sha256", "")).lower() != assignment_sha256:
        raise SystemExit(f"assignment approval hash mismatch: {approval_manifest_path}")
    if not str(approval.get("approved_by", "")).strip() or not str(approval.get("reason", "")).strip():
        raise SystemExit("assignment approval must identify approved_by and reason")
    return {
        "status": "approved_override",
        "assignment_sha256": assignment_sha256,
        "approval_manifest": str(approval_manifest_path.resolve()),
        "approval_manifest_sha256": file_sha256(approval_manifest_path),
    }


def parse_int_csv(text: str) -> list[int]:
    out: list[int] = []
    for part in str(text or "").replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.append(int(float(part)))
        except ValueError:
            continue
    return out


def first_int(text: str | None) -> int | None:
    match = re.search(r"-?\d+", str(text or ""))
    return int(match.group(0)) if match else None


def parse_sg_ref(text: str | None) -> tuple[int, int] | None:
    parts = [int(v) for v in re.findall(r"-?\d+", str(text or ""))]
    if len(parts) < 2:
        return None
    return parts[0], parts[1]


def signal_group_axis(name: str, sg_no: int) -> str:
    upper = str(name or "").upper()
    if "EB" in upper or "WB" in upper:
        return "EW"
    if "NB" in upper or "SB" in upper:
        return "NS"
    if int(sg_no) == 1:
        return "EW"
    if int(sg_no) == 2:
        return "NS"
    return "unknown"


def signal_head_link_axes(network_path: Path) -> dict[int, dict[str, set[str]]]:
    root = ET.parse(network_path).getroot()
    sg_axis_by_sc: dict[int, dict[int, str]] = {}
    for sc in root.iter("signalController"):
        sc_no = first_int(sc.get("no"))
        if sc_no is None:
            continue
        by_sg: dict[int, str] = {}
        for sg in sc.findall("./sgs/signalGroup"):
            sg_no = first_int(sg.get("no"))
            if sg_no is None:
                continue
            by_sg[sg_no] = signal_group_axis(str(sg.get("name", "")), sg_no)
        sg_axis_by_sc[sc_no] = by_sg

    axes: dict[int, dict[str, set[str]]] = {}
    for sh in root.iter("signalHead"):
        sg_ref = parse_sg_ref(sh.get("sg"))
        link_no = first_int(sh.get("lane"))
        if sg_ref is None or link_no is None:
            continue
        sc_no, sg_no = sg_ref
        axis = sg_axis_by_sc.get(sc_no, {}).get(sg_no, "unknown")
        axes.setdefault(sc_no, {}).setdefault(str(link_no), set()).add(axis)
    return axes


def signal_head_link_max_pos(network_path: Path) -> dict[int, dict[str, float]]:
    root = ET.parse(network_path).getroot()
    out: dict[int, dict[str, float]] = {}
    for sh in root.iter("signalHead"):
        sg_ref = parse_sg_ref(sh.get("sg"))
        link_no = first_int(sh.get("lane"))
        if sg_ref is None or link_no is None:
            continue
        sc_no = sg_ref[0]
        try:
            pos = float(str(sh.get("pos", "0")).strip())
        except ValueError:
            pos = 0.0
        by_link = out.setdefault(sc_no, {})
        link_key = str(link_no)
        by_link[link_key] = max(float(by_link.get(link_key, 0.0)), pos)
    return out


def controlled_link_owner(
    rows: list[dict[str, str]],
    head_pos_by_sc: dict[int, dict[str, float]],
) -> dict[str, int]:
    candidates: dict[str, list[tuple[float, int]]] = {}
    for row in rows:
        sc_no = int(row["no"])
        for link in parse_int_csv(row.get("unique_head_links", "")):
            candidates.setdefault(str(link), []).append((float(head_pos_by_sc.get(sc_no, {}).get(str(link), 0.0)), sc_no))
    owners: dict[str, int] = {}
    for link, values in candidates.items():
        owners[link] = sorted(values, key=lambda item: (item[0], -item[1]), reverse=True)[0][1]
    return owners


def owned_links_for_signal(
    row: dict[str, str],
    link_owner_by_link: dict[str, int],
) -> list[str]:
    sc_no = int(row["no"])
    return [
        str(link)
        for link in parse_int_csv(row.get("unique_head_links", ""))
        if link_owner_by_link.get(str(link), sc_no) == sc_no
    ]


def active_fixedtime_signal_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return sorted(
        [
            row
            for row in rows
            if row.get("active", "").lower() == "true"
            and row.get("type", "").upper() == "FIXEDTIME"
            and int(float(row.get("signal_head_count") or 0)) > 0
        ],
        key=lambda row: int(row["no"]),
    )


def _select_by_sc(rows: list[dict[str, str]], wanted: set[int], label: str) -> list[dict[str, str]]:
    """지정 SC만 고른다. 하나라도 인벤토리에 없으면 조용히 빠뜨리지 않고 실패시킨다."""
    selected = [
        row for row in active_fixedtime_signal_rows(rows) if int(row.get("no", "0")) in wanted
    ]
    missing = sorted(wanted - {int(row["no"]) for row in selected})
    if missing:
        raise ValueError(
            f"{label}: 인벤토리에 없거나 비활성인 signal controller {missing}\n"
            "  네트워크를 수정했다면 인벤토리를 먼저 재생성할 것:\n"
            "  python scripts/inventory_real_world_modi.py --inpx network/real_world_gaepo_modi/modi.inpx"
        )
    return selected


def selected_signal_rows(rows: list[dict[str, str]], selector: str) -> list[dict[str, str]]:
    if selector == "primary19":
        # Urban Follower 1~19 전체(SC 번호 1~19가 아니다 — 위 매핑 주석 참조).
        uf_map = load_urban_follower_sc_map()
        selected = _select_by_sc(rows, set(uf_map.values()), "primary19")
    elif selector == "core15":
        uf_map = load_urban_follower_sc_map()
        wanted = set(urban_follower_scs(CORE15_URBAN_FOLLOWER_IDS, uf_map))
        selected = _select_by_sc(rows, wanted, "core15")
    elif selector == "all-active-heads":
        selected = active_fixedtime_signal_rows(rows)
    else:
        wanted = {int(x) for x in parse_int_csv(selector)}
        selected = [row for row in active_fixedtime_signal_rows(rows) if int(row.get("no", "0")) in wanted]
    if not selected:
        raise ValueError(f"No signal controllers matched selector={selector!r}")
    return sorted(selected, key=lambda row: int(row["no"]))


def selector_slug(selector: str, count: int) -> str:
    if selector == "primary19":
        return "19sc"
    if selector == "core15":
        return "15core"
    if selector == "all-active-heads":
        return f"{count}sc_all"
    return f"{count}sc_custom"


def signal_id(sc_no: int) -> str:
    return f"SC{sc_no}"


def movement(signal: str, suffix: str, phase: str, origin: str, receiving: str, kind: str = "boundary_in",
             controlled: bool = True) -> dict[str, Any]:
    """movement spec. controlled=False 면 phase="" 로 둔다.

    grid_topology.build_urban_movements 와 같은 규약이다 — 신호가 없는 노드는 phase 를
    빈 문자열로 두면 green=1 상당으로 신호 없이 통과한다(같은 파일 docstring:
    "E(비통제)는 phase=''(green=1 상당)로 신호 없이 통과"). 덕분에 비통제 교차로도
    movement 큐·링크 저류를 통제 교차로와 **동일한 모델**로 예측하면서 제어만 받지 않는다.
    """
    return {
        "intersection": signal,
        "approach": suffix,
        "exit": "out",
        "beta": 1.0,
        "signal": signal,
        "phase": f"{signal}_{phase}" if controlled else "",
        "origin": origin,
        "destination": receiving,
        "receiving_link": receiving,
        "kind": kind,
    }


def build_network_override(rows: list[dict[str, str]], include_freeway_interface_coupling: bool = True,
                           ramp_interface_sc: "dict[str, str] | None" = None,
                           monitor_rows: "list[dict[str, str]] | None" = None,
                           adjacency_legs: "dict[str, dict[str, int]] | None" = None,
                           storage_capacity: "dict[str, float] | None" = None,
                           ramp_queue_by_ramp: "dict[str, float] | None" = None,
                           boundary_gates: "dict[str, list[str]] | None" = None) -> dict[str, Any]:
    # 통제 대상(rows)과 비통제(monitor_rows)를 **같은 모델로** 세운다.
    #
    # 왜. 나중에 컨트롤러 분석은 "통제 교차로의 TTT 절감 대 인접 비통제 구간의 TTT 증가"를
    # 비교한다. 비통제 교차로를 모델에서 아예 빼 버리면 그 증가분을 잴 수가 없고,
    # 관측된 차량이 어느 저류에도 귀속되지 않아 관측 목적함수에서 사라진다
    # (2026-08-04 실측: 도시부 포착률 1.7 %의 주된 원인).
    #
    # grid_node_legs 에는 전부 넣고 signals 에는 통제 대상만 넣는다. 그러면
    # grid_topology.build_urban_movements 와 같은 규약으로 비통제 노드의 movement 는
    # phase="" 가 되어 신호 없이 통과하면서도 큐·저류는 동일하게 계상된다.
    # uncontrolled_nodes 로 내보내면 state.uncontrolled_node_movement_queue_veh /
    # uncontrolled_node_storage_occupancy_veh 로 인접부 TTT 를 따로 집계할 수 있다.
    signals = [signal_id(int(row["no"])) for row in rows]
    uncontrolled = [signal_id(int(row["no"])) for row in (monitor_rows or [])]
    all_nodes = signals + uncontrolled
    node_set = set(all_nodes)
    grid_node_legs: dict[str, Any] = {}
    urban_movements: dict[str, Any] = {}
    boundary_in: list[str] = []
    boundary_out: list[str] = []
    storage: dict[str, float] = {}

    # 교차로 간 인접(2026-08-04). adjacency_legs 는 scripts/derive_intersection_adjacency.py 가
    # 네트워크에서 유도한 {SC번호: {"방위_SC이웃": 이웃SC번호}} 다.
    # 관대(㉮) 대칭화 — 한쪽 방향만 잡힌 인접도 양방향 leg 로 심는다(일방통행·회전제한으로
    # 역방향 탐색이 끊긴 경우가 많아, 버리면 연결이 과소해진다).
    adj: dict[str, dict[str, str]] = {}
    for sc_txt, legmap in (adjacency_legs or {}).items():
        a = signal_id(int(sc_txt))
        for leg_key, nb in legmap.items():
            b = signal_id(int(nb))
            if a not in node_set or b not in node_set:
                continue
            base = str(leg_key).split("_", 1)[0]
            adj.setdefault(a, {})[f"{base}_{b}"] = b
            # 역방향이 없으면 만들어 준다. 방위는 정반대로 둔다.
            opp = {"N": "S", "S": "N", "E": "W", "W": "E",
                   "NE": "SW", "SW": "NE", "NW": "SE", "SE": "NW"}.get(base, base)
            adj.setdefault(b, {}).setdefault(f"{opp}_{a}", a)

    # 램프 leg 를 어느 노드에 심을 것인가 — ramp_interface_sc 의 역방향.
    # default.yaml 의 D·F 노드와 같은 형태로 두면 movement 도 모델이 자동 유도한다
    # ({"type":"ramp","on":{"W":..,"E":..},"off":{"W":..,"E":..}}).
    ramp_legs_by_node: dict[str, dict[str, Any]] = {}
    if include_freeway_interface_coupling:
        for ramp, sid in (ramp_interface_sc or {}).items():
            side = ramp.rsplit("_", 1)[-1]          # R_D_W -> W
            off_ramp = "OR_" + ramp[2:]            # R_D_W -> OR_D_W
            spec = ramp_legs_by_node.setdefault(sid, {"type": "ramp", "on": {}, "off": {}})
            spec["on"][side] = ramp
            spec["off"][side] = off_ramp

    # 경계 게이트를 어디에 심을 것인가.
    #
    # boundary_gates 가 None 이면 예전 규칙 그대로 — 이웃이 안 쓴 정방위마다 기계적으로 하나씩
    # 만든다. 그 규칙은 VISSIM 을 안 보므로 실제 유입이 없는 유령 게이트를 낳는다(2026-08-11
    # 실측: 경계 leg 119개 중 100개가 대응 유입 없음). 정렬 입력을 주면 **그 (노드, 방위)
    # 조합에만** 만든다.
    if boundary_gates is not None:
        unknown = sorted(set(boundary_gates) - node_set)
        if unknown:
            raise SystemExit(
                f"경계 게이트 계획에 이 네트워크에 없는 노드가 있다: {unknown}\n"
                f"  노드 {len(node_set)}개, selector 밖이거나 정렬 산출물이 낡았다."
            )

    CARDINAL = ("N", "S", "E", "W")
    merged_gates: list[str] = []
    for sid in all_nodes:
        legs: dict[str, Any] = {}
        for leg_key, nb in sorted(adj.get(sid, {}).items()):
            legs[leg_key] = {"type": "grid", "node": nb}
        used_base = {k.split("_", 1)[0] for k in legs}
        free = [d for d in CARDINAL if d not in used_base]
        # 램프 인터페이스 노드는 빈 기본 방위 하나(가능하면 S)를 램프 leg 로 쓴다.
        ramp_spec = ramp_legs_by_node.get(sid)
        if ramp_spec and free:
            slot = "S" if "S" in free else free[0]
            legs[slot] = ramp_spec
            free = [d for d in free if d != slot]
            for r in ramp_spec["on"].values():
                storage[f"{sid}_{r}_queue"] = 180.0
            for o in ramp_spec["off"].values():
                storage[f"{o}_storage"] = 120.0
        # 경계 게이트 — 수요 유입·유출 경로.
        gate_dirs = list(free) if boundary_gates is None else list(boundary_gates.get(sid, ()))
        for leg in gate_dirs:
            # leg 병합(2026-08-11 사용자 결정). 그 방위를 이미 grid 이웃이 쓰고 있으면
            # 게이트를 버리지 않고 **같은 방위에 나란히** 심는다. 물리적으로 "이웃에서 오는
            # 차 + 외부에서 오는 차"가 같은 접근로를 쓰기 때문이다.
            #
            # 상류 모델은 이 형태를 이미 지원한다. grid leg 키는 항상 '방위_이웃ID' 라
            # 맨 방위 키가 비어 있고, `grid_topology.leg_base_dir` 이 두 키에서 같은 방위를
            # 뽑는다(:189-198). `derive_turning_ratios` 도 같은 방위 leg 이 여럿인 경우를
            # 직진 후보 균등분배로 처리한다(:143-151). phase 도 방위로 정해지므로 병합된
            # 두 접근로는 같은 phase 로 서비스된다. 새 leg type 을 만들지 않는다 —
            # 상류 `_approach_tokens` 는 grid/boundary/ramp 외의 type 을 조용히 버린다.
            #
            # 맨 방위 키가 이미 차 있는 경우는 램프 leg 뿐이다(grid 는 항상 복합 키).
            # 램프 방위에 도시부 게이트를 얹는 건 사용자가 결정한 적 없는 상황이라 끊는다 —
            # 그냥 대입하면 램프 leg 를 조용히 덮어써서 고속도로 결합이 사라진다.
            if leg in legs:
                raise SystemExit(
                    f"{sid} 의 {leg} 방위는 이미 {legs[leg].get('type')} leg 이 쓰고 있다.\n"
                    "  격자 이웃과의 병합은 지원하지만 램프 leg 와의 병합은 결정된 바 없다."
                )
            if any(str(k).split("_", 1)[0] == leg for k in legs):
                merged_gates.append(f"{sid}_{leg}")
            legs[leg] = {"type": "boundary", "in": f"in_{sid}_{leg}",
                         "out": f"out_{sid}_{leg}", "out_link": f"{sid}_{leg}_out"}
            boundary_in.append(f"in_{sid}_{leg}")
            boundary_out.append(f"out_{sid}_{leg}")
            storage[f"{sid}_{leg}_out"] = 220.0
        grid_node_legs[sid] = legs
    if merged_gates:
        print(f"   경계 게이트 병합 {len(merged_gates)}곳(기존 leg 과 같은 방위): {sorted(merged_gates)}")
    # urban_movements / turning_ratios / 내부링크 저류는 **모델이 grid_node_legs 에서 자동 유도**한다
    # (NetworkConfig.__post_init__ L298-316). 수동 나열은 저장소가 명시적으로 금한다.

    # 램프를 어느 urban player 에 붙일 것인가 (2026-08-04 일반화).
    #
    # 기존에는 네 램프를 전부 SC1 하나에 붙였다. 그러면 D/F 구분이 모델에서 사라져
    # 램프별 한계가격이 다시 퇴화한다. 실제 플랜트 구조는 인터체인지가 둘이다.
    #   D측 = SC1001 — 신호두가 링크 32 위, 링크 32 는 오프램프 커넥터 10481/10491 이 직접 물린다.
    #   F측 = SC1004 — 링크 71(SG 2,5)이 링크 70(오프램프 10638/10643 수용)을 배수하고,
    #                  링크 52/46/66 이 링크 68 을 먹이는데 링크 68 의 출구는 온램프 10646/10681 뿐이다.
    # ramp_interface_sc 로 램프별 귀속 SC 를 받는다. 값이 signals 에 없으면 그 램프는 결합 없음.
    ramp_interface_sc = dict(ramp_interface_sc or {})
    ramp_phase = {"R_D_W": "p1", "R_D_E": "p2", "R_F_W": "p1", "R_F_E": "p2"}
    off_phase = {"OR_D_W": "p1", "OR_D_E": "p2", "OR_F_W": "p1", "OR_F_E": "p2"}
    ramp_to_freeway = {"R_D_W": "FW_W", "R_F_W": "FW_W", "R_D_E": "FW_E", "R_F_E": "FW_E"}
    off_to_on = {"OR_D_W": "R_D_W", "OR_D_E": "R_D_E", "OR_F_W": "R_F_W", "OR_F_E": "R_F_E"}

    on_ramp_to_movement: dict[str, list[str]] = {r: [] for r in ramp_phase}
    off_ramp_to_movement: dict[str, list[str]] = {o: [] for o in off_phase}

    # movement 는 **모델 자신의 유도 함수**로 여기서도 한 번 돌린다.
    #
    # 왜 필요한가. detector_local_mapping 의 link_to_movements 는 movement **이름**을 참조하는데,
    # 그 이름은 grid_node_legs 에서 유도돼야 알 수 있다. 생성기가 이름을 모르면 매핑이 비고,
    # 투영이 movement 큐를 하나도 못 채운다(2026-08-04 실측: 0/1406, 포착률 37.6% -> 13.2% 로 후퇴).
    # 모델과 같은 함수를 쓰므로 이름이 어긋날 수 없다. config 에는 그대로 실어 보내
    # 매핑과 모델이 같은 이름을 보게 한다.
    ensure_numsim_importable()
    from src.models.grid_topology import build_urban_movements, derive_turning_ratios

    ramp_to_freeway = {"R_D_W": "FW_W", "R_F_W": "FW_W", "R_D_E": "FW_E", "R_F_E": "FW_E"}
    turning_ratios = derive_turning_ratios(grid_node_legs)
    urban_movements = build_urban_movements(grid_node_legs, turning_ratios, signals, ramp_to_freeway)
    # 램프 movement 의 receiving 저류가 유도 이름을 쓰므로 용량을 그 이름으로 다시 깐다.
    for spec in urban_movements.values():
        recv = str(spec.get("receiving_link") or "")
        if not recv or recv in storage:
            continue
        if spec.get("kind") == "on_ramp":
            storage[recv] = 180.0
        elif spec.get("kind") == "off_ramp":
            storage[recv] = 120.0
    # 실측 기하에서 유도한 저류 용량으로 덮어쓴다(scripts/derive_urban_storage_capacity.py).
    #
    # 왜. 위의 220/180/120 은 전부 상수라 실제 기하와 무관하다. 특히 내부 저류가 오프램프
    # 기본값 120 을 물려받아 SC1001_to_SC1004 가 모든 상태에서 v/c=1.000 이 됐다. 또한
    # 상수로는 저류 이름이 12개밖에 안 생겨서 아래 storage_keys 필터가 내부 구간 93개 중
    # 81개를 떨어뜨린다. 유도값은 상류-하류 쌍마다 이름이 있어 두 문제를 같이 없앤다.
    if storage_capacity:
        known = set(storage)
        nodes_all = set(signals) | set(uncontrolled or ())
        # 경계 저류는 **leg 이 실제로 만든 이름**만 존재한다. 유도 대장의 이름은
        # 배정 산출물의 8방위 링크 기하로 지어지므로(derive_urban_storage_capacity.py:124)
        # 격자에 그 방위 게이트가 있는지와 무관하다. 예전에는 노드 이름만 맞으면 전부
        # 받아서, 어느 leg 도 뒷받침하지 않는 유령 저류가 생겼다(2026-08-11 실측:
        # 생산 격자 56개, 22게이트 후보 62개). 유령은 movement 가 채우지도 비우지도
        # 않는데 `total_urban_vehicles` 는 저류 키 전수를 세므로, 어댑터가 적재한
        # 관측 차량이 얼어붙은 채 리더 목적함수에 남는다(생산 실측 평균 360.9 대).
        gate_out_links = {
            str(spec["out_link"])
            for legs in grid_node_legs.values()
            for spec in legs.values()
            if spec.get("type") == "boundary"
        }
        rejected: list[str] = []
        for name, cap in storage_capacity.items():
            # 유도 이름 중 모델이 실제로 세우는 저류만 받는다: 이미 있는 이름이거나,
            # 양끝이 모두 이 네트워크의 신호인 내부 링크(SCa_to_SCb).
            if name in known:
                storage[name] = float(cap)
                continue
            # 비통제 노드도 같은 모델로 세우므로(사용자 요구) 그 사이 구간도 저류를 갖는다.
            a, sep, b = name.partition("_to_")
            if sep and a in nodes_all and b in nodes_all:
                storage[name] = float(cap)
                continue
            # 유입 경계 저류 SC{n}_{leg}_out — 그 방위에 **게이트가 있을 때만** 존재한다.
            if name.endswith("_out"):
                if name in gate_out_links:
                    storage[name] = float(cap)
                elif name.split("_", 1)[0] in nodes_all:
                    rejected.append(name)
        print(f"   저류 용량: 유도 {len(storage_capacity)}개 중 {len(storage)-len(known)}개 신규 + "
              f"{len(known & set(storage_capacity))}개 갱신 -> 총 {len(storage)}개")
        if rejected:
            print(f"   경계 leg 이 없어 저류를 만들지 않은 유도 이름 {len(rejected)}개: "
                  f"{sorted(rejected)[:6]}{' ...' if len(rejected) > 6 else ''}")

    return {
        "signals": signals,
        "uncontrolled_nodes": uncontrolled,
        "urban_links": [],
        "grid_node_legs": grid_node_legs,
        # urban_movements 는 램프 결합분만 명시한다. 비어 있으면 모델이 legs 에서 전부 유도하는데,
        # 램프는 legs 에 ramp leg 를 안 만들었으므로 결합 movement 만 여기서 얹는다.
        "urban_movements": urban_movements,
        "boundary_in_links": boundary_in,
        "boundary_out_links": boundary_out,
        "urban_link_storage_veh": storage,
        # 램프별 큐 상한. 비면 NetworkConfig 가 스칼라 ramp_queue_max_veh 로 폴백한다.
        **({"ramp_queue_max_veh_by_ramp": dict(ramp_queue_by_ramp)} if ramp_queue_by_ramp else {}),
        "on_ramp_to_movement": {},
        "off_ramp_to_movement": {},
    }


def prune_network_movements_to_observed_axes(
    network_override: dict[str, Any],
    rows: list[dict[str, str]],
    head_axes_by_sc: dict[int, dict[str, set[str]]],
    link_owner_by_link: dict[str, int],
) -> dict[str, Any]:
    observed_axes_by_signal: dict[str, set[str]] = {}
    for row in rows:
        sc_no = int(row["no"])
        sid = signal_id(sc_no)
        axes: set[str] = set()
        for link in owned_links_for_signal(row, link_owner_by_link):
            axes.update(axis for axis in head_axes_by_sc.get(sc_no, {}).get(str(link), set()) if axis in {"NS", "EW"})
        observed_axes_by_signal[sid] = axes

    urban_movements: dict[str, Any] = {}
    removed: dict[str, list[str]] = {}
    for movement_key, spec in network_override["urban_movements"].items():
        signal = str(spec.get("signal", ""))
        phase = str(spec.get("phase", ""))
        axes = observed_axes_by_signal.get(signal, {"NS", "EW"})
        keep = True
        if phase.endswith("_p1") and axes and "NS" not in axes:
            keep = False
        if phase.endswith("_p2") and axes and "EW" not in axes:
            keep = False
        if keep:
            urban_movements[movement_key] = spec
        else:
            removed.setdefault(signal, []).append(movement_key)

    network_override["urban_movements"] = urban_movements
    network_override["on_ramp_to_movement"] = {
        ramp: [movement for movement in movements if movement in urban_movements]
        for ramp, movements in network_override.get("on_ramp_to_movement", {}).items()
    }
    network_override["off_ramp_to_movement"] = {
        off_ramp: [movement for movement in movements if movement in urban_movements]
        for off_ramp, movements in network_override.get("off_ramp_to_movement", {}).items()
    }
    return network_override


def build_control_mapping(
    base: dict[str, Any],
    rows: list[dict[str, str]],
    monitor_rows: list[dict[str, str]],
    detector_path: Path,
    selector: str,
) -> dict[str, Any]:
    out = dict(base)
    out["description"] = (
        "Distributed real-world Gaepo modi control mapping: freeway/ramp controls copied "
        "from the validated base mapping; selected core urban signals expanded to "
        "individual SC players while peripheral signals are monitored only."
    )
    out["detector_mapping_json"] = str(detector_path.relative_to(ROOT))
    out["urban_signal_selector"] = selector
    out["controlled_signal_controllers"] = [int(row["no"]) for row in rows]
    out["monitoring_only_signal_controllers"] = [int(row["no"]) for row in monitor_rows]
    out["signals"] = [
        {
            "id": signal_id(int(row["no"])),
            "sc_no": int(row["no"]),
            "name": row.get("name", ""),
            "role": row.get("role", ""),
            # major_maps_to — VISSIM MAJOR(SG1) 접근이 모델의 어느 phase 에 대응하는가.
            # 일반 간선 교차로는 MAJOR 가 EW 간선이고 모델도 p2 로 서비스한다.
            # freeway 인터페이스 교차로는 MAJOR 접근이 off-ramp 유출이고, 모델은 램프 leg 를
            # NS 축으로 보아 p1 에 둔다(NumSim grid_topology._token_leg_dir: off*/on* -> "S").
            # 이 값을 명시하지 않으면 어댑터가 p2 로 가정해 인터페이스 교차로에서 부호가 뒤집힌다.
            "major_maps_to": major_phase_for_role(row),
            "source": "evaluation/real_world_modi_inventory/signal_controller_roles.csv",
        }
        for row in rows
    ]
    return out


def major_phase_for_role(row: dict[str, Any]) -> str:
    """이 신호제어기의 VISSIM MAJOR(SG1) 가 모델의 어느 phase 인지 판정한다.

    판정 근거는 인벤토리의 interface_head_count 다. 이 값이 0 보다 크면 그 컨트롤러의
    정지선 신호두가 **freeway 에 접한 도로 링크** 위에 있다는 뜻이고, 개포동 네트워크에서
    그 접근은 off-ramp 유출이다. 모델은 램프 leg 를 NS 축으로 보아 p1 에 배정하므로
    (NumSim grid_topology._token_leg_dir: off*/on* -> "S"), MAJOR 는 p1 에 대응한다.

    일반 간선 교차로는 MAJOR 가 EW 간선이고 모델도 p2 로 서비스한다.

    2026-08-04 실측: 전체 37 개 SC 중 interface_head_count > 0 인 것은 SC 1001 하나뿐이고,
    그 정지선 신호두는 link 32 위에 있으며 link 32 의 유입 커넥터는 conn 10481(본선 2에서)과
    conn 10491(본선 26에서) 뿐이다.
    """
    try:
        if int(float(row.get("interface_head_count") or 0)) > 0:
            return "p1"
    except (TypeError, ValueError):
        pass
    if "interface" in str(row.get("role", "")).lower():
        return "p1"
    return "p2"


def movements_for_link_axes(signal_movements: list[str], link_axes: set[str]) -> list[str]:
    if not link_axes or "unknown" in link_axes:
        return list(signal_movements)
    wanted_phases: set[str] = set()
    if "NS" in link_axes:
        wanted_phases.add("_p1")
    if "EW" in link_axes:
        wanted_phases.add("_p2")
    selected = [
        movement_key
        for movement_key in signal_movements
        if any(str(movement_key).endswith(phase) or phase in str(movement_key) for phase in wanted_phases)
    ]
    # Synthetic on/off-ramp movements at SC1 are attached to p1/p2 by suffix
    # names, not by the movement key, so match against their spec below.
    return selected if selected else list(signal_movements)


def build_detector_mapping(
    base: dict[str, Any],
    rows: list[dict[str, str]],
    monitor_rows: list[dict[str, str]],
    network_override: dict[str, Any],
    selector: str,
    head_axes_by_sc: dict[int, dict[str, set[str]]],
    link_owner_by_link: dict[str, int],
    internal_link_members: "dict[str, list[str]] | None" = None,
    link_assignment: "dict[str, Any] | None" = None,
    link_assignment_evidence: "dict[str, Any] | None" = None,
) -> dict[str, Any]:
    out = dict(base)
    out["mapping_version"] = f"real_world_modi_distributed_{selector}_v1_20260728"
    out["description"] = (
        "Distributed connector/local observation mapping. Base freeway/ramp/off-ramp "
        "observations are preserved; selected core signal-head links are added as "
        "urban-agent local queues and peripheral signal-head links are monitored only."
    )
    link_to_movements = {str(k): list(v) for k, v in dict(base.get("link_to_movements", {})).items()}
    link_to_origins = {str(k): list(v) for k, v in dict(base.get("link_to_origins", {})).items()}
    agents = dict(base.get("agents", {}))
    observable = {str(v) for v in base.get("observable_links", [])}
    movement_keys_by_signal: dict[str, list[str]] = {}
    movement_phase_by_key: dict[str, str] = {}
    for movement_key, spec in network_override["urban_movements"].items():
        movement_keys_by_signal.setdefault(str(spec.get("signal")), []).append(movement_key)
        movement_phase_by_key[movement_key] = str(spec.get("phase", ""))

    for row in rows:
        sc_no = int(row["no"])
        sid = signal_id(sc_no)
        links = owned_links_for_signal(row, link_owner_by_link)
        signal_movements = movement_keys_by_signal.get(sid, [])
        for link in links:
            observable.add(link)
            link_to_origins.setdefault(link, [])
            for leg in ("N", "S", "E", "W"):
                origin = f"{sid}_{leg}_out"
                if origin not in link_to_origins[link]:
                    link_to_origins[link].append(origin)
            entries = link_to_movements.setdefault(link, [])
            existing = {str(item.get("movement")) for item in entries if isinstance(item, dict)}
            link_axes = head_axes_by_sc.get(sc_no, {}).get(str(link), set())
            phase_filtered = [
                movement_key
                for movement_key in signal_movements
                if (
                    "unknown" in link_axes
                    or not link_axes
                    or (
                        "NS" in link_axes
                        and str(movement_phase_by_key.get(movement_key, "")).endswith("_p1")
                    )
                    or (
                        "EW" in link_axes
                        and str(movement_phase_by_key.get(movement_key, "")).endswith("_p2")
                    )
                )
            ] or list(signal_movements)
            for movement_key in phase_filtered:
                if movement_key not in existing:
                    entries.append({
                        "movement": movement_key,
                        "weight": 1.0,
                        "source": "signal_head_phase_axis",
                        "axes": sorted(link_axes) if link_axes else ["unknown"],
                    })
        agents[f"U_{sid}"] = {
            "kind": "urban",
            "signal": sid,
            "sc_no": sc_no,
            "name": row.get("name", ""),
            "control_enabled": True,
            "monitoring_only": False,
            "visible_links": links,
            "visible_movements": signal_movements,
            "visible_link_axes": {
                link: sorted(head_axes_by_sc.get(sc_no, {}).get(str(link), {"unknown"}))
                for link in links
            },
            "visible_ramps": [
                ramp for ramp, movements in network_override["on_ramp_to_movement"].items()
                if any(m in signal_movements for m in movements)
            ],
            "visible_off_ramps": [
                off for off, movements in network_override["off_ramp_to_movement"].items()
                if any(m in signal_movements for m in movements)
            ],
        }
    for row in monitor_rows:
        sc_no = int(row["no"])
        sid = signal_id(sc_no)
        links = [str(v) for v in parse_int_csv(row.get("unique_head_links", ""))]
        for link in links:
            observable.add(link)
            link_to_origins.setdefault(link, [])
        agents[f"MON_{sid}"] = {
            "kind": "urban_monitor",
            "signal": sid,
            "sc_no": sc_no,
            "name": row.get("name", ""),
            "control_enabled": False,
            "monitoring_only": True,
            "visible_links": links,
            "visible_link_axes": {
                link: sorted(head_axes_by_sc.get(sc_no, {}).get(str(link), {"unknown"}))
                for link in links
            },
            "visible_movements": [],
            "visible_ramps": [],
            "visible_off_ramps": [],
        }
    # 교차로 **사이** 구간의 VISSIM 링크를 내부 directed link(SCa_to_SCb) 저류에 귀속시킨다.
    #
    # 이게 없으면 연결형 토폴로지를 세워도 내부 링크 저류가 영원히 0 이다 — 관측 차량이
    # 경계 out 링크와 movement 큐로만 들어가기 때문이다(2026-08-04 실측: 내부 140개 중 점유 0,
    # 포착률이 독립섬 37.6% 에서 한 발도 못 올라갔다). 구간 링크는 인접 유도 때 훑은
    # 커넥터 경로에서 나온다(derive_intersection_adjacency.py 의 internal_link_members).
    storage_keys = set(network_override.get("urban_link_storage_veh", {}))
    for internal_link, members in (internal_link_members or {}).items():
        if internal_link not in storage_keys:
            continue
        for link in members:
            link = str(link)
            observable.add(link)
            link_to_origins.setdefault(link, [])
            if internal_link not in link_to_origins[link]:
                link_to_origins[link].append(internal_link)
    # ---- 권위 라우팅: 관측 링크를 **상류 SC 기준**으로 모델 저류에 붙인다 ----
    #
    # 왜. 위(585~595행)는 소유 링크마다 {sid}_{leg}_out 을 N/S/E/W **네 개 전부** 박는다.
    # 실제 기하와 무관한 살포이고, 전부 경계 sink 다. 실측(2026-08-05): 경계 sink 로 가는
    # 관측 링크 66개 중 65개가 플레이어 배정 링크였고, 그중 53개는 모델에 내부 링크가
    # 멀쩡히 있는데도 경계로 샜다. SC15/SC107/SC9002/SC2 -> SC1 네 접근로가 전부 같은
    # SC1_N_out 으로 접혔다(방위 복합키가 맨 방위로 접히는 그 문제).
    # 리더는 경계 leg 를 설계대로 목적함수에서 빼므로(leader.py:767), 제어 가능한
    # approach queue 651 대가 통째로 목적함수 밖으로 나갔다 — 포착률 20.7% 의 주원인이다.
    #
    # 규칙은 사용자 확정 분할 그대로다: 링크는 하류 첫 신호(owner)의 approach 이고,
    # 그 차가 담기는 모델 저류는 상류->owner 방향의 내부 링크다.
    if link_assignment:
        owner_of = link_assignment.get("link_owner") or {}
        upstream_of = link_assignment.get("link_upstream") or {}
        leg_of = link_assignment.get("link_leg") or {}
        storages = set(network_override.get("urban_link_storage_veh", {}))
        stat = {"내부": 0, "경계": 0, "저류없음": 0}
        missing: dict[str, int] = {}
        unrouted: dict[str, str] = {}
        for link, sc in owner_of.items():
            link = str(link)
            up = upstream_of.get(link)
            name = (f"{signal_id(int(up))}_to_{signal_id(int(sc))}" if up is not None
                    else f"{signal_id(int(sc))}_{leg_of.get(link, '?')}_out")
            if name not in storages:
                # 모델에 그 저류가 없다. 예전에는 `continue` 라 위(757행)의 방위 살포가
                # 그대로 남아 링크가 **엉뚱한 저류**(주로 유령)로 흘러들어갔다. 권위
                # 라우팅이 실패했으면 origin 을 비우고 명시적으로 계상한다 —
                # 그래야 그 관측분이 어디로도 안 가는 것이 `unrepresented` 로 드러난다.
                stat["저류없음"] += 1
                missing[name] = missing.get(name, 0) + 1
                unrouted[link] = name
                observable.add(link)
                link_to_origins[link] = []
                continue
            observable.add(link)
            link_to_origins[link] = [name]      # 방위 살포를 덮어쓴다(권위)
            stat["내부" if "_to_" in name else "경계"] += 1
        print(f"   링크->저류 라우팅: 내부 {stat['내부']}개, 경계 {stat['경계']}개,"
              f" 저류 없어 건너뜀 {stat['저류없음']}개")
        if missing:
            top = sorted(missing.items(), key=lambda kv: -kv[1])[:5]
            print(f"      없는 저류 상위: {top}")
        # 출구 링크는 관측만 하고 origin 을 주지 않는다(사용자 규칙: 플레이어 귀속 없음).
        for link in link_assignment.get("monitor_only_exit_links") or []:
            observable.add(str(link))
            link_to_origins.setdefault(str(link), [])

        # 도시부 분할 밖의 링크에서 도시부 origin 을 걷어낸다.
        #
        # internal_link_members 는 커넥터 **경로 기반** 이라 SC 사이 경로가 고속도로를
        # 타고 지나가면 고속도로 본선 링크까지 멤버로 넣는다(예: SC1001_to_SC1004 의
        # 멤버가 링크 2, 26). 실측 2026-08-05: 링크 2(178대)·26(510대)이 도시부 내부
        # 저류 origin 을 갖고 있어, 고속도로 차량 688 대가 도시부 저류로 흘러들어
        # 포착률이 114.6% 로 100% 를 넘었다.
        urban_universe = (set(owner_of)
                          | {str(v) for v in (link_assignment.get("monitor_only_exit_links") or [])}
                          | set(link_assignment.get("freeway_bound_links") or {}))
        stripped = {l: link_to_origins[l] for l in list(link_to_origins)
                    if link_to_origins[l] and str(l) not in urban_universe}
        for l in stripped:
            link_to_origins[l] = []
        if stripped:
            print(f"   도시부 분할 밖인데 origin 이 붙어 있던 링크 {len(stripped)}개 제거: "
                  f"{sorted(stripped)[:8]}")

    if link_assignment:
        out["link_partition"] = {
            "owned_links": sorted((str(value) for value in owner_of), key=int),
            "owned_link_legs": {
                str(link): str(leg)
                for link, leg in sorted(
                    (link_assignment.get("link_leg") or {}).items(),
                    key=lambda item: int(item[0]),
                )
                if str(link) in owner_of
            },
            "freeway_bound_links": sorted(
                (str(value) for value in (link_assignment.get("freeway_bound_links") or {})),
                key=int,
            ),
            "monitor_only_exit_links": sorted(
                (str(value) for value in (link_assignment.get("monitor_only_exit_links") or [])),
                key=int,
            ),
            # 권위 라우팅이 저류를 못 찾아 origin 을 비운 링크와, 그 링크가 원했던 이름.
            # 비어 있어야 정상이다 — 값이 있으면 그만큼의 관측이 모델 상태에 안 실린다.
            "unrouted_links": {
                str(link): str(name)
                for link, name in sorted(unrouted.items(), key=lambda item: int(item[0]))
            },
            "source": "outputs/link_player_assignment_20260805.json",
            "assignment_evidence": dict(link_assignment_evidence or {}),
        }

    out["observable_links"] = sorted(int(v) for v in observable if str(v).strip().isdigit())
    out["link_to_movements"] = link_to_movements
    out["link_to_origins"] = link_to_origins
    out["agents"] = agents
    out["guardrails"] = {
        **dict(base.get("guardrails", {})),
        "distributed_urban_signal_players": {
            "enabled": True,
            "selector": selector,
            "controlled_signal_controllers": [int(row["no"]) for row in rows],
            "monitoring_only_signal_controllers": [int(row["no"]) for row in monitor_rows],
            "note": "Only controlled_signal_controllers enter the P-Stack urban follower/action space.",
        },
    }
    return out


def prune_permanent_red_monitor_movements(
    network_override: dict[str, Any],
    detector_mapping: dict[str, Any],
) -> dict[str, list[str]]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from evaluation.controllers.fixed_signal_schedule import compile_fixed_signal_schedules

    monitor_nodes = {str(value) for value in network_override.get("uncontrolled_nodes", [])}
    schedules, errors = compile_fixed_signal_schedules(
        DEFAULT_NETWORK,
        monitor_nodes,
        detector_mapping,
    )
    if errors or set(schedules) != monitor_nodes:
        missing = sorted(monitor_nodes - set(schedules))
        raise SystemExit(f"monitor fixed-signal compile failed: errors={errors} missing={missing}")

    removed: dict[str, list[str]] = {}
    kept: dict[str, Any] = {}
    removed_origins: set[str] = set()
    for movement_key, spec in network_override.get("urban_movements", {}).items():
        node = str(spec.get("intersection", ""))
        schedule = schedules.get(node)
        if schedule is not None and not str(spec.get("phase", "")):
            if schedule.movement_green_fraction(spec) <= 1.0e-9:
                removed.setdefault(node, []).append(str(movement_key))
                removed_origins.add(str(spec.get("origin", "")))
                continue
        kept[str(movement_key)] = spec

    surviving_origins = {str(spec.get("origin", "")) for spec in kept.values()}
    network_override["urban_movements"] = kept
    network_override["boundary_in_links"] = [
        link
        for link in network_override.get("boundary_in_links", [])
        if str(link) not in removed_origins or str(link) in surviving_origins
    ]
    network_override["on_ramp_to_movement"] = {
        ramp: [movement for movement in movements if movement in kept]
        for ramp, movements in network_override.get("on_ramp_to_movement", {}).items()
    }
    network_override["off_ramp_to_movement"] = {
        off_ramp: [movement for movement in movements if movement in kept]
        for off_ramp, movements in network_override.get("off_ramp_to_movement", {}).items()
    }
    return {node: sorted(movements) for node, movements in sorted(removed.items())}


def build_tuning_config(
    network_override: dict[str, Any],
    control_mapping_path: Path,
    detector_mapping_path: Path,
    selector: str,
    slug: str,
    monitor_rows: list[dict[str, str]],
    stamp: str = "20260728",
    boundary_gate_notes: "list[str] | None" = None,
) -> dict[str, Any]:
    signals = network_override["signals"]
    # 유도값 둘을 앞에 세워 부모 체인 위에 다시 깐다. 이 두 키가 없으면 모델이
    # NetworkConfig 기본값으로 떨어져 플랜트 주기와 2 s 어긋난다(위 계약 주석 참조).
    network_override = {
        **green_budget_contract(CONFIG_DIR / PARENT_CONFIG),
        **network_override,
    }
    return {
        "extends": PARENT_CONFIG,
        "name": f"real_world_modi_pstack_distributed_{slug}_{stamp}",
        "description": (
            "Copy-only distributed urban-follower experiment. Keeps the validated real-world freeway/VSL/"
            "ramp setup, but expands urban signal control from one SC1 interface lever to selected "
            "individual core urban follower agents. Peripheral signal controllers remain observation-only."
        ),
        "mapping_json": str(control_mapping_path.relative_to(ROOT)),
        "detector_mapping_json": str(detector_mapping_path.relative_to(ROOT)),
        "urban_signal_selector": selector,
        "config_overrides": {
            "network": network_override,
            "mpc": {
                "follower_solver_mode": "distributed",
                "distributed_coupling_tol": 0.05,
                "stackelberg_allocation_mode": "simplified",
                "leader_candidate_count": 9,
                "leader_refinement_candidate_count": 5,
                "max_nash_iter": 4,
                "stackelberg_prefilter_top_k": 3,
                "stackelberg_prefilter_local_top_k": 3,
            },
            "urban_follower": {
                "allocation_pso_particles": 6,
                "allocation_pso_iterations": 8,
                "max_offset_step": 15.0,
                "offset_smoothness_weight": 0.08,
                "green_smoothness_weight": 0.08,
            },
        },
        "actuation": {
            "active_lever_mask": {
                "enabled": False,
                "allowed_signals": signals,
                "monitoring_only_signals": [signal_id(int(row["no"])) for row in monitor_rows],
            },
            "real_world_signal_control": {
                "enabled": True,
                "apply_to_no_control": False,
            },
        },
        "safety": {
            "original_files_unchanged": True,
            "copy_only_outputs": [
                str(control_mapping_path.relative_to(ROOT)),
                str(detector_mapping_path.relative_to(ROOT)),
            ],
        },
        "notes": [
            "This is an experiment config, not a promoted baseline.",
            "SC1 receives the freeway-interface ramp/off-ramp coupling when included in the selected control set.",
            "Monitoring-only signal controllers are scanned into local observations but are not listed in network.signals, so they do not get green/offset actions.",
            "The first smoke should be short because distributed urban agents enlarge the signal action space.",
        ] + list(boundary_gate_notes or ()),
    }


def _vbs_long_string_assignment(name: str, value: str, chunk_size: int = 600) -> list[str]:
    chunks = [value[index : index + chunk_size] for index in range(0, len(value), chunk_size)] or [""]
    lines: list[str] = []
    for index, chunk in enumerate(chunks):
        prefix = f"{name} = " if index == 0 else "    "
        suffix = " & _" if index < len(chunks) - 1 else ""
        lines.append(f'{prefix}"{chunk}"{suffix}')
    return lines


def write_generated_vbs(path: Path, base: dict[str, Any], detector_path: Path, observable_links: list[int], rows: list[dict[str, str]]) -> None:
    # 본선 체인/기하는 control_mapping.json이 정본이다(체인 정의는
    # evaluation/real_world_modi_control/freeway_mainline_chain.csv). 여기서 다시 계산하지 않는다.
    fw = base["freeway_model_links"]
    ramp_meters = base.get("ramp_meters", [])
    missing_chain = sorted(model for model, spec in fw.items() if "chain_links" not in spec)
    if missing_chain:
        raise SystemExit(
            f"control_mapping.json에 본선 체인 정보가 없다: {missing_chain}\n"
            "  python scripts/generate_real_world_control_mapping.py 를 먼저 다시 돌릴 것."
        )
    chain_links_all = sorted({int(link) for spec in fw.values() for link in spec["chain_links"]})
    expected_vsl_action_rows = sum(len(segment.get("dsds", [])) for segment in base.get("segments", []))
    expected_vsl_dsd_ids = sorted(
        {int(dsd["dsd_no"]) for segment in base.get("segments", []) for dsd in segment.get("dsds", [])}
    )
    expected_vsl_action_keys = [
        "|".join(
            (
                str(segment["segment_id"]),
                str(int(dsd["dsd_no"])),
                str(int(segment["link"])),
                str(int(dsd["lane"])),
            )
        )
        for segment in base.get("segments", [])
        for dsd in segment.get("dsds", [])
    ]
    if len(expected_vsl_dsd_ids) != expected_vsl_action_rows:
        raise SystemExit("control mapping contains duplicate VSL DSD identifiers")
    if len(set(expected_vsl_action_keys)) != expected_vsl_action_rows:
        raise SystemExit("control mapping contains duplicate VSL action tuples")
    lines = [
        "' Generated by scripts/generate_real_world_distributed_players.py",
        # 2: 본선이 링크 체인이 되면서 RW_*_CHAIN_LINKS / RW_*_CHAIN_OFFSETS_M 가 필수다.
        "RW_SCHEMA_VERSION = 3",
        'RW_FREEWAY_LINKS = "' + ",".join(str(v) for v in chain_links_all) + '"',
        'RW_FREEWAY_INPUT_LINKS = "26,74"',
        "RW_CLASSIFY_UNMATCHED_AS_URBAN = True",
    ]
    for model_link, var in (("FW_E", "RW_FW_E"), ("FW_W", "RW_FW_W")):
        spec = fw[model_link]
        chain_links = [int(v) for v in spec["chain_links"]]
        chain_offsets = [float(v) for v in spec["chain_offsets_m"]]
        lines.extend([
            f"{var}_LINK = {int(spec['physical_link'])}",
            f"{var}_LENGTH_M = {float(spec['length_m']):.6f}",
            f"{var}_LANES = {int(spec['lanes'])}",
            f'{var}_CHAIN_LINKS = "' + ",".join(str(v) for v in chain_links) + '"',
            f'{var}_CHAIN_OFFSETS_M = "' + ",".join(f"{v:.6f}" for v in chain_offsets) + '"',
            f'{var}_SEG_BOUNDS = "' + ",".join(f"{float(v):.6f}" for v in spec["segment_bounds_m"]) + '"',
            f'{var}_SEG_LENGTHS_KM = "' + ",".join(f"{float(v):.6f}" for v in spec["segment_length_profile_km"]) + '"',
        ])
    lines.extend([
        'RW_RAMP_METER_IDS = "' + ",".join(str(r["id"]) for r in ramp_meters) + '"',
        'RW_RAMP_METER_SCS = "' + ",".join(str(int(r["sc_no"])) for r in ramp_meters) + '"',
        'RW_RAMP_METER_CONNECTORS = "' + ",".join(str(int(r["connector"])) for r in ramp_meters) + '"',
        'RW_RAMP_METER_MODEL_KEYS = "' + ",".join(str(r["model_ramp_key"]) for r in ramp_meters) + '"',
        'RW_RAMP_METER_CAPACITIES_VPH = "' + ",".join(str(float(r["capacity_vph"])) for r in ramp_meters) + '"',
        'RW_SIGNAL_SCS = "' + ",".join(str(int(row["no"])) for row in rows) + '"',
        f"RW_EXPECTED_VSL_ACTION_ROWS = {expected_vsl_action_rows}",
        'RW_EXPECTED_VSL_DSD_IDS = "' + ",".join(str(value) for value in expected_vsl_dsd_ids) + '"',
    ])
    lines.extend(_vbs_long_string_assignment("RW_EXPECTED_VSL_ACTION_KEYS", ";".join(expected_vsl_action_keys)))
    lines.extend([
        'RW_ALLOWED_VSL_SPEEDS = "50,60,70,80,90,100,115,120"',
        'RW_LOCAL_OBSERVABLE_LINKS = "' + ",".join(str(int(v)) for v in observable_links) + '"',
        f'RW_DETECTOR_MAPPING_PATH = "{detector_path.relative_to(ROOT)}"',
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_wrapper(
    path: Path,
    tuning_path: Path,
    mapping_path: Path,
    generated_path: Path,
    calibration_path: Path,
) -> None:
    text = (ROOT / "scripts/run_real_world_single_watchdog.ps1").read_text(encoding="utf-8")
    text = text.replace(
        'evaluation\\configs\\real_world_modi_pstack_adapter_v0_20260719.json',
        str(tuning_path.relative_to(ROOT)).replace("/", "\\"),
    )
    text = text.replace(
        'evaluation\\calibration\\real_world_modi_control_v0_20260719.json',
        str(calibration_path.relative_to(ROOT)).replace("/", "\\"),
    )
    text = text.replace(
        'evaluation\\real_world_modi_control\\control_mapping.json',
        str(mapping_path.relative_to(ROOT)).replace("/", "\\"),
    )
    text = text.replace(
        'evaluation\\generated\\real_world_modi_control_config.vbs',
        str(generated_path.relative_to(ROOT)).replace("/", "\\"),
    )
    path.write_text(text, encoding="utf-8")


def write_report(
    path: Path,
    rows: list[dict[str, str]],
    monitor_rows: list[dict[str, str]],
    files: dict[str, Path],
    detector: dict[str, Any],
    tuning: dict[str, Any],
) -> None:
    lines = [
        "# Real-world distributed urban followers, copy-only config",
        "",
        "Generated on 2026-07-28.",
        "",
        "## Selected Urban Signal Players",
        "",
        "| player | sc_no | name | signal heads | observed links |",
        "| --- | ---: | --- | ---: | ---: |",
    ]
    for row in rows:
        links = parse_int_csv(row.get("unique_head_links", ""))
        lines.append(
            f"| U_SC{int(row['no'])} | {int(row['no'])} | {row.get('name', '')} | "
            f"{int(float(row.get('signal_head_count') or 0))} | {len(links)} |"
        )
    lines.extend([
        "",
        "## Monitoring-Only Signal Controllers",
        "",
        "| monitor | sc_no | name | signal heads | observed links |",
        "| --- | ---: | --- | ---: | ---: |",
    ])
    for row in monitor_rows:
        links = parse_int_csv(row.get("unique_head_links", ""))
        lines.append(
            f"| MON_SC{int(row['no'])} | {int(row['no'])} | {row.get('name', '')} | "
            f"{int(float(row.get('signal_head_count') or 0))} | {len(links)} |"
        )
    lines.extend([
        "",
        "## Files",
        "",
    ])
    for label, file_path in files.items():
        lines.append(f"- {label}: `{file_path.relative_to(ROOT)}`")
    lines.extend([
        "",
        "## Structure",
        "",
        f"- Urban follower count in model config: `{len(tuning['config_overrides']['network']['signals'])}`",
        f"- Controlled urban SC agent count in detector mapping: `{len([k for k, v in detector.get('agents', {}).items() if str(k).startswith('U_SC') and v.get('control_enabled')])}`",
        f"- Monitoring-only SC agent count in detector mapping: `{len([k for k, v in detector.get('agents', {}).items() if str(k).startswith('MON_SC') and v.get('monitoring_only')])}`",
        f"- Observable links scanned by VBS: `{len(detector.get('observable_links', []))}`",
        "- Freeway/ramp VSL and metering mapping are copied from the validated base mapping.",
        "- Signal-head link queue attribution is derived from `.inpx` signal-head/SG names: EB/WB links feed EW/major movements and NB/SB links feed NS/minor movements.",
        "- In `core15`, SC1 is strict approach-only; ramp/off-ramp observations stay in freeway/base local observation rather than the SC1 urban follower.",
        "- `.layx` is treated as visual/layout validation only; `.inpx` is the plant and topology source.",
        "- Monitoring-only signals are not emitted as `kind=signal` rows in the action CSV.",
        "- Original files are not overwritten; use the distributed wrapper/config paths explicitly.",
    ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selector", default="primary19", help="primary19, core15, all-active-heads, or comma-separated SC numbers")
    # 2026-08-04: SC1 결합을 selector 이름에서 떼어낸다.
    #   기존에는 `include_sc1_coupling = selector != "core15"` 로 하드코딩돼 있어,
    #   core15 아티팩트의 on_ramp_to_movement / off_ramp_to_movement 가 전부 빈 리스트였다.
    #   그 config 를 모델에 병합하면 도시부->온램프 연결이 사라져 metering 이 조일 대상 자체를
    #   잃는다(2026-08-04 확인). 임의 SC 집합을 쓰면서도 결합을 켤 수 있어야 한다.
    #   auto = 기존 규칙 그대로(core15 만 off) — 하위호환.
    parser.add_argument("--sc1-coupling", choices=("auto", "on", "off"), default="auto",
                        help="freeway-urban 램프 결합. auto=기존 규칙(core15 만 off)")
    # 램프별 귀속 인터페이스 SC (2026-08-04). 기본값은 실측 플랜트 구조를 따른다 —
    # D측은 SC1001(신호두가 링크 32, 오프램프 10481/10491 직결), F측은 SC1004(링크 71 이
    # 링크 70 배수, 링크 52/46/66 이 링크 68 공급, 링크 68 출구는 온램프 10646/10681 뿐).
    # 넷을 한 SC 로 몰면 D/F 구분이 모델에서 사라져 램프별 한계가격이 퇴화한다.
    parser.add_argument("--ramp-interface-sc", default="R_D_W:1001,R_D_E:1001,R_F_W:1004,R_F_E:1004",
                        help="램프->인터페이스 SC 귀속. 'R_D_W:1001,R_F_W:1004' 형식")
    parser.add_argument("--slug", default="", help="산출물 이름의 슬러그를 직접 지정한다(기본은 selector 유래)")
    parser.add_argument("--stamp", default="20260728", help="산출물 파일명의 날짜 스탬프")
    parser.add_argument("--adjacency-json", default="",
                        help="scripts/derive_intersection_adjacency.py 산출 JSON. 주면 교차로 간 grid leg 를 심는다")
    parser.add_argument("--link-assignment-json", default="",
                        help="scripts/assign_links_to_players.py 산출 JSON. 주면 관측 링크를 상류 SC 기준으로 저류에 붙인다")
    parser.add_argument(
        "--assignment-approval-manifest",
        default="",
        help="explicit approval JSON for a hash-bound assignment that still has unresolved topology ties",
    )
    parser.add_argument("--storage-capacity-json", default="",
                        help="scripts/derive_urban_storage_capacity.py 산출 JSON. 주면 상수 대신 실측 기하 용량을 쓴다")
    parser.add_argument("--boundary-input-alignment", default="",
                        help="scripts/derive_boundary_input_alignment.py 산출 JSON. 주면 VISSIM 유입이 "
                             "있는 (노드, 방위)에만 경계 leg 을 만든다(없으면 정방위 전수 = 기존 동작)")
    args = parser.parse_args()

    all_signal_rows = active_fixedtime_signal_rows(read_csv(DEFAULT_SIGNAL_ROLES))
    rows = selected_signal_rows(all_signal_rows, args.selector)
    slug = args.slug or selector_slug(args.selector, len(rows))
    stamp = args.stamp
    controlled_sc = {int(row["no"]) for row in rows}
    monitor_rows = [row for row in all_signal_rows if int(row["no"]) not in controlled_sc]
    base_mapping = read_json(DEFAULT_CONTROL_MAPPING)
    base_detector = read_json(DEFAULT_DETECTOR_MAPPING)
    head_axes_by_sc = signal_head_link_axes(DEFAULT_NETWORK)
    head_pos_by_sc = signal_head_link_max_pos(DEFAULT_NETWORK)
    # 인벤토리(modi.inpx 기준)에는 있지만 eval 네트워크에는 아직 없는 SC가 있으면
    # movement가 빈 채로 조용히 생성된다 — 2026-07-31 UF/SC 혼동과 같은 부류의
    # 침묵 실패라 여기서 끊는다. 네트워크 재빌드 순서는 아래 안내 참조.
    stale = sorted(controlled_sc - set(head_axes_by_sc))
    if stale:
        raise SystemExit(
            f"eval 네트워크에 없는 signal controller {stale}\n"
            f"  네트워크: {DEFAULT_NETWORK}\n"
            "  modi.inpx를 수정했다면 eval 네트워크를 먼저 재빌드할 것:\n"
            "    1) python scripts/prepare_real_world_modi_eval_copy.py\n"
            "    2) cscript //nologo scripts\\install_real_world_freeway_controls.vbs "
            "<sanitized.inpx> <sanitized.layx> <rw_control.inpx> <rw_control.layx> "
            "evaluation\\real_world_modi_control\\freeway_control_manifest.csv   (VISSIM COM 필요)\n"
            "    3) python scripts/generate_real_world_control_mapping.py\n"
            "    4) 이 스크립트 재실행"
        )
    link_owner_by_link = controlled_link_owner(rows, head_pos_by_sc)

    if args.sc1_coupling == "auto":
        include_sc1_coupling = args.selector != "core15"
    else:
        include_sc1_coupling = args.sc1_coupling == "on"
    adjacency_legs = None
    internal_link_members = None
    if args.adjacency_json:
        _adj = read_json(Path(args.adjacency_json))
        adjacency_legs = _adj.get("legs") or {}
        internal_link_members = _adj.get("internal_link_members") or {}
        print(f"인접 JSON: {args.adjacency_json}  SC {len(adjacency_legs)}개, 내부구간 {len(internal_link_members)}개")
    link_assignment = None
    link_assignment_evidence = None
    if args.link_assignment_json:
        link_assignment_path = Path(args.link_assignment_json)
        link_assignment = read_json(link_assignment_path)
        approval_path = Path(args.assignment_approval_manifest) if args.assignment_approval_manifest else None
        link_assignment_evidence = validate_link_assignment(link_assignment_path, link_assignment, approval_path)
        print(f"배정 JSON: {args.link_assignment_json}  귀속 {len(link_assignment.get('link_owner') or {})}개,"
              f" 상류확정 {len(link_assignment.get('link_upstream') or {})}개,"
              f" 출구 {len(link_assignment.get('monitor_only_exit_links') or [])}개")
    storage_capacity = None
    ramp_queue_by_ramp = None
    if args.storage_capacity_json:
        _cap = read_json(Path(args.storage_capacity_json))
        storage_capacity = _cap.get("urban_link_storage_veh") or {}
        ramp_queue_by_ramp = _cap.get("ramp_queue_max_veh_by_ramp") or {}
        print(f"용량 JSON: {args.storage_capacity_json}  저류 {len(storage_capacity)}개,"
              f" jam {_cap.get('jam_density_veh_km_lane')} veh/km/lane")
        if ramp_queue_by_ramp:
            print(f"   램프별 큐 상한 {len(ramp_queue_by_ramp)}개: {ramp_queue_by_ramp}")
    boundary_gates = None
    boundary_gate_evidence: list[dict[str, Any]] = []
    if args.boundary_input_alignment:
        _alignment = read_json(Path(args.boundary_input_alignment))
        boundary_gates, boundary_gate_evidence = boundary_gate_plan_from_alignment(_alignment)
        _by_source: dict[str, int] = {}
        for _row in boundary_gate_evidence:
            _by_source[_row["source"]] = _by_source.get(_row["source"], 0) + 1
        print(f"정렬 JSON: {args.boundary_input_alignment}  유입 {len(boundary_gate_evidence)}개 -> "
              f"게이트 {sum(len(v) for v in boundary_gates.values())}개, 노드 {len(boundary_gates)}개")
        print(f"   방위 근거: {dict(sorted(_by_source.items()))}")
    ramp_interface_sc: dict[str, str] = {}
    for part in str(args.ramp_interface_sc or "").split(","):
        part = part.strip()
        if not part or ":" not in part:
            continue
        ramp, sc_txt = part.split(":", 1)
        ramp_interface_sc[ramp.strip()] = f"SC{int(sc_txt.strip())}"
    if include_sc1_coupling:
        # 귀속 SC 가 selector 밖이면 그 램프는 결합 없이 조용히 생성된다 — 침묵 실패라 끊는다.
        missing = sorted({int(v[2:]) for v in ramp_interface_sc.values()} - controlled_sc)
        if missing:
            raise SystemExit(
                "램프 결합을 켰는데 귀속 SC 가 selector 에 없다.\n"
                f"  --ramp-interface-sc = {args.ramp_interface_sc}\n"
                f"  누락 SC {missing},  selector={args.selector!r} -> SC {sorted(controlled_sc)}\n"
                "  selector 에 포함시키거나 --ramp-interface-sc 를 바꿀 것."
            )
    network_override = build_network_override(
        rows,
        include_freeway_interface_coupling=include_sc1_coupling,
        ramp_interface_sc=ramp_interface_sc,
        monitor_rows=monitor_rows,
        adjacency_legs=adjacency_legs,
        storage_capacity=storage_capacity,
        ramp_queue_by_ramp=ramp_queue_by_ramp,
        boundary_gates=boundary_gates,
    )
    network_override = prune_network_movements_to_observed_axes(
        network_override,
        rows,
        head_axes_by_sc,
        link_owner_by_link,
    )
    detector_path = OUT_DIR / f"detector_local_mapping_distributed_{slug}_{stamp}.json"
    mapping_path = OUT_DIR / f"control_mapping_distributed_{slug}_{stamp}.json"
    player_path = OUT_DIR / f"player_config_distributed_{slug}_{stamp}.json"
    tuning_path = CONFIG_DIR / f"real_world_modi_pstack_distributed_{slug}_{stamp}.json"
    generated_path = GENERATED_DIR / f"real_world_modi_control_config_distributed_{slug}_{stamp}.vbs"
    wrapper_name = "run_real_world_single_watchdog_distributed.ps1" if slug == "19sc" else f"run_real_world_single_watchdog_distributed_{slug}.ps1"
    report_name = "real_world_distributed_urban_followers_20260728.md" if slug == "19sc" else f"real_world_distributed_urban_followers_{slug}_{stamp}.md"
    wrapper_path = ROOT / f"scripts/{wrapper_name}"
    report_path = OUTPUTS_DIR / report_name

    detector = build_detector_mapping(
        base_detector,
        rows,
        monitor_rows,
        network_override,
        args.selector,
        head_axes_by_sc,
        link_owner_by_link,
        internal_link_members=internal_link_members,
        link_assignment=link_assignment,
        link_assignment_evidence=link_assignment_evidence,
    )
    permanent_red_removed = prune_permanent_red_monitor_movements(network_override, detector)
    if permanent_red_removed:
        print(
            "monitor permanent-red movements removed: "
            + ", ".join(f"{node}={len(movements)}" for node, movements in permanent_red_removed.items())
        )
    mapping = build_control_mapping(base_mapping, rows, monitor_rows, detector_path, args.selector)
    boundary_gate_notes: list[str] = []
    if boundary_gates is not None:
        merged = sorted(
            f"{node}_{str(key).split('_', 1)[0]}"
            for node, node_legs in network_override["grid_node_legs"].items()
            for key, spec in node_legs.items()
            if spec.get("type") == "boundary"
            and any(
                other is not spec and str(other_key).split("_", 1)[0] == str(key).split("_", 1)[0]
                for other_key, other in node_legs.items()
            )
        )
        boundary_gate_notes = [
            "Boundary legs are restricted to the (node, bearing) pairs that actually receive a VISSIM "
            f"vehicle input: {Path(args.boundary_input_alignment).name}. Approach bearing comes from the "
            "input name's travel-direction suffix (NB->S, SB->N, EB->W, WB->E); geometry is used only for "
            "unnamed inputs.",
            "Merged boundary legs (a gate sharing its bearing with a grid neighbour leg, i.e. neighbour "
            f"traffic and external traffic use the same approach): {merged or 'none'}.",
        ]
    tuning = build_tuning_config(network_override, mapping_path, detector_path, args.selector, slug,
                                monitor_rows, stamp, boundary_gate_notes)
    player_config = {
        "schema_version": 1,
        "created_at": "2026-07-28",
        "mode": f"distributed_urban_signal_players_{slug}",
        "urban_signal_selector": args.selector,
        "controlled_signal_controllers": sorted(controlled_sc),
        "monitoring_only_signal_controllers": [int(row["no"]) for row in monitor_rows],
        "players": [
            {
                "id": "leader_network_manager",
                "kind": "leader",
                "state_scope": "whole network split into freeway links 2/26 and urban signal-player local observations",
                "controlled_followers": ["freeway_follower_real_world"] + [f"urban_follower_SC{int(row['no'])}" for row in rows],
            },
            {
                "id": "freeway_follower_real_world",
                "kind": "freeway_follower",
                "physical_links": [26, 2],
                "vsl_segments": [seg["segment_id"] for seg in base_mapping.get("segments", [])],
                "ramp_meters": [rm["id"] for rm in base_mapping.get("ramp_meters", [])],
            },
        ] + [
            {
                "id": f"urban_follower_SC{int(row['no'])}",
                "kind": "urban_follower",
                "signal_id": signal_id(int(row["no"])),
                "sc_no": int(row["no"]),
                "name": row.get("name", ""),
                "control_enabled": True,
                "local_observation_agent": f"U_{signal_id(int(row['no']))}",
            }
            for row in rows
        ] + [
            {
                "id": f"urban_monitor_SC{int(row['no'])}",
                "kind": "urban_monitor",
                "signal_id": signal_id(int(row["no"])),
                "sc_no": int(row["no"]),
                "name": row.get("name", ""),
                "control_enabled": False,
                "monitoring_only": True,
                "local_observation_agent": f"MON_{signal_id(int(row['no']))}",
            }
            for row in monitor_rows
        ],
        "source_files": {
            "signal_roles": str(DEFAULT_SIGNAL_ROLES.relative_to(ROOT)),
            "network_inpx": str(DEFAULT_NETWORK.relative_to(ROOT)),
            "base_control_mapping": str(DEFAULT_CONTROL_MAPPING.relative_to(ROOT)),
            "base_detector_mapping": str(DEFAULT_DETECTOR_MAPPING.relative_to(ROOT)),
            "prediction_calibration": str(DEFAULT_PREDICTION_CALIBRATION.relative_to(ROOT)),
        },
    }

    write_json(detector_path, detector)
    write_json(mapping_path, mapping)
    write_json(player_path, player_config)
    write_json(tuning_path, tuning)
    write_generated_vbs(generated_path, base_mapping, detector_path, detector["observable_links"], rows)
    write_wrapper(wrapper_path, tuning_path, mapping_path, generated_path, DEFAULT_PREDICTION_CALIBRATION)
    write_report(report_path, rows, monitor_rows, {
        "control mapping": mapping_path,
        "detector mapping": detector_path,
        "player config": player_path,
        "P-Stack tuning": tuning_path,
        "generated VBS config": generated_path,
        "watchdog wrapper": wrapper_path,
    }, detector, tuning)

    print(f"signals={len(rows)}")
    print(f"monitoring_only_signals={len(monitor_rows)}")
    print(f"observable_links={len(detector['observable_links'])}")
    print(f"mapping={mapping_path}")
    print(f"detector={detector_path}")
    print(f"tuning={tuning_path}")
    print(f"wrapper={wrapper_path}")
    print(f"report={report_path}")


if __name__ == "__main__":
    main()
