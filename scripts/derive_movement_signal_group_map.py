#!/usr/bin/env python3
# v3 N4-2 - movement <-> (SC, SG번호) 귀속과 (SC, SG번호) -> 모델 phase 를 토폴로지에서 유도한다
"""Derive the movement ↔ signal-group map that `native_phase_green` needs.

## 왜 필요한가

N4-3 은 movement 의 native 녹색배분을 실 `.sig` 에서 뽑는다. 그 계산은 두 가지를 알아야 한다.

    분자   movement 가 잡는 SG 집합
    분모   그 movement 의 **모델 phase** 가 잡는 SG 집합

직전 판은 둘 다 이름에 기대고 있었다. 분자는 링크 leg 문자(`owned_link_legs`)로,
분모는 SG 이름 부분문자열(`_axis_for_signal_group`: EB/WB→p2, NB/SB→p1)로 골랐다.
실측 결과 698개 제어 movement 중 304개(43.6%)가 미해결로 남았다.

    no_signal_group_mapping  282   origin/leg 가 조인표에 없다
    axis_mismatch             22   분자 SG 가 이름 규칙이 만든 분모 축에 안 들어간다

## 무엇을 하는가

근거를 이름에서 **토폴로지**로 옮긴다. signalHead 는 링크/차로에 붙어 있고 SG 를 가리키므로
링크가 유일한 물리 조인축이다.

1. `movement -> (sc_no, sg_id)`  origin 이 소유한 링크의 신호두를 쓴다. 링크에 신호두가
   없으면(오프램프·합류 회랑) 커넥터를 따라 내려가 그 SC 의 첫 신호두까지 간다. 다른 SC 의
   신호두를 만나면 그 가지는 죽인다 - 안 그러면 아무 movement 나 이어붙일 수 있다.
2. `(sc_no, sg_id) -> 모델 phase`  SG 신호두가 붙은 링크의 origin 을 잡는 movement 들의
   phase 를 쓴다. 이름 규칙은 **명시적 폴백**으로만 남고 산출물에 method 로 기록된다.

2번이 축 어긋남을 없애는 자리다. 예로 SC1001 의 링크 32 는 SG 2,5(EBT/EBL)를 달고 있어
이름 규칙이면 p2 다. 그러나 모델은 그 접근로를 `S_SC1004` 로 보므로 movement phase 는 p1 이다.
이름 규칙을 쓰면 분자와 분모가 서로 다른 현시를 재게 되고 그 15건이 통째로 버려졌다.

## 무엇을 하지 않는가

모델이 심은 **경계 leg**(`in_<SC>_<방위>`)는 여기서 풀지 않는다. 그것은 인접이 없는 기본
방위에 수요를 넣으려고 `generate_real_world_distributed_players.py` 가 만든 가상 접근로라
VISSIM 에 대응 링크가 없다. 잔차로 뭉개지 않고 `synthetic_boundary_leg` 로 따로 센다.

## SG 목록은 어디서 오는가

`.inpx` 의 `signalController/@supplyFile2` 가 그 SC 의 `.sig` 를 가리키는 유일한 근거다.
토폴로지 컴파일러가 그 선언을 그대로 싣고 있으므로 SG 목록·이름은 토폴로지에서 읽는다.

`outputs/signal_group_timing_v3.json` 은 **교차검사에만** 쓴다. 그 생산자가 파일명 끝자리
숫자로 `.sig` 를 고르던 동안 실측(2026-08-10) 4/15 가 불일치였다.

    SC5  timing=test-bed5.sig  inpx=test-bed7.sig   SG 8 vs 24
    SC6  timing=test-bed6.sig  inpx=test-bed9.sig   SG 16 vs 8
    SC11 timing=test-bed11.sig inpx=test-bed3.sig
    SC12 timing=test-bed12.sig inpx=test-bed5.sig

생산자가 `supplyFile2` 를 읽도록 고쳐 지금은 전부 일치한다. 교차검사는 그대로 둔다 -
`timing_cross_check.agrees` 가 두 출처가 같은 프로그램을 본다는 유일한 증거다.

그래서 타이밍 표의 SG 목록으로 걸러내면 SC5 의 SG 10·24 같은 실 SG 가 사라진다.
여기서는 고치지 않고 `timing_cross_check` 로 산출물에 남긴다.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


REPO = Path(__file__).resolve().parents[1]
DEFAULT_TOPOLOGY = REPO / "outputs" / "canonical_topology_v3.json"
DEFAULT_TIMING = REPO / "outputs" / "signal_group_timing_v3.json"
DEFAULT_CONFIG = (
    REPO
    / "evaluation"
    / "configs"
    / "real_world_modi_pstack_distributed_core15n41_20260805.json"
)
DEFAULT_DETECTOR_MAPPING = (
    REPO
    / "evaluation"
    / "real_world_modi_control_distributed_20260728"
    / "detector_local_mapping_distributed_core15n41_20260805.json"
)
DEFAULT_OUT = REPO / "outputs" / "movement_signal_group_map_v3.json"

SCHEMA_VERSION = "movement-signal-group-map-v3"

# 커넥터 추적 예산. 실측 최장은 SC2005_to_SC1002 의 9 홉(링크 316 -> ... -> 329)이다.
# 무한 추적은 합류 회랑 끝의 아무 신호두나 집어오므로 상한을 둔다.
MAX_CONNECTOR_HOPS = 12


def _sort_id(value: str) -> tuple[int, str]:
    try:
        return int(value), value
    except ValueError:
        return 2**31 - 1, value


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@dataclass(frozen=True)
class NetworkIndex:
    """토폴로지에서 뽑은 조인축 셋. 이 세 개 말고는 유도에 쓰지 않는다."""

    # node -> link -> SG 번호들
    heads_by_node: Mapping[str, Mapping[str, tuple[str, ...]]]
    # link -> 그 링크에 신호두를 가진 node 들
    head_nodes_by_link: Mapping[str, frozenset[str]]
    # link/connector -> 하류 link/connector 들
    successors: Mapping[str, tuple[str, ...]]


def build_network_index(topology: Mapping[str, Any]) -> NetworkIndex:
    heads: dict[str, dict[str, set[str]]] = {}
    head_nodes: dict[str, set[str]] = {}
    for head in topology.get("signal_heads", ()):
        reference = head.get("signal_group_ref") or {}
        lane = head.get("lane_ref") or {}
        controller = str(reference.get("controller_no", ""))
        sg_no = str(reference.get("sg_no", ""))
        link_no = str(lane.get("link_no", ""))
        if not controller or not sg_no or not link_no:
            continue
        node = f"SC{controller}"
        heads.setdefault(node, {}).setdefault(link_no, set()).add(sg_no)
        head_nodes.setdefault(link_no, set()).add(node)

    successors: dict[str, set[str]] = {}
    for connector in topology.get("connectors", ()):
        source = str((connector.get("from_endpoint") or {}).get("link_no", ""))
        target = str((connector.get("to_endpoint") or {}).get("link_no", ""))
        own = str((connector.get("source") or {}).get("vissim_no", ""))
        if not source or not target or not own:
            continue
        # 커넥터도 자기 링크 번호를 갖고 그 위에 신호두가 놓일 수 있어 그래프 마디로 둔다.
        successors.setdefault(source, set()).add(own)
        successors.setdefault(own, set()).add(target)

    return NetworkIndex(
        heads_by_node={
            node: {
                link: tuple(sorted(groups, key=_sort_id))
                for link, groups in sorted(links.items(), key=lambda item: _sort_id(item[0]))
            }
            for node, links in heads.items()
        },
        head_nodes_by_link={link: frozenset(nodes) for link, nodes in head_nodes.items()},
        successors={
            link: tuple(sorted(targets, key=_sort_id)) for link, targets in successors.items()
        },
    )


@dataclass(frozen=True)
class OriginResolution:
    """origin 하나의 귀속 결과. 실패하면 `signal_groups` 가 None 이고 사유가 남는다."""

    signal_groups: tuple[str, ...] | None
    method: str
    hops: int
    links: tuple[str, ...]
    reason: str = ""


def _resolve(
    index: NetworkIndex,
    node: str,
    origin_links: Sequence[str],
    max_hops: int,
    allowed_groups: frozenset[str] | None,
) -> OriginResolution:
    node_heads = index.heads_by_node.get(node, {})
    start = tuple(dict.fromkeys(str(link) for link in origin_links))
    if not start:
        return OriginResolution(None, "", -1, (), "origin_link_unknown")

    frontier = list(start)
    visited = set(frontier)
    for hop in range(0, max_hops + 1):
        if not frontier:
            break
        hits = [link for link in frontier if link in node_heads]
        if hits:
            groups: set[str] = set()
            for link in hits:
                groups.update(node_heads[link])
            if allowed_groups is not None:
                groups &= allowed_groups
            if groups:
                return OriginResolution(
                    tuple(sorted(groups, key=_sort_id)),
                    "origin_link_head" if hop == 0 else "connector_chain",
                    hop,
                    tuple(sorted(hits, key=_sort_id)),
                )
        following: list[str] = []
        for link in frontier:
            # 다른 SC 의 신호두를 만난 가지는 여기서 끊는다.
            if index.head_nodes_by_link.get(link):
                continue
            for target in index.successors.get(link, ()):
                if target not in visited:
                    visited.add(target)
                    following.append(target)
        frontier = following
    return OriginResolution(None, "", -1, (), "no_signal_head_downstream")


def resolve_origin_signal_groups(
    node: str,
    origin_links: Sequence[str],
    topology: Mapping[str, Any],
    max_hops: int = MAX_CONNECTOR_HOPS,
    allowed_groups: Iterable[str] | None = None,
) -> OriginResolution:
    """origin 이 소유한 링크에서 그 SC 의 신호두까지 내려가 SG 집합을 잡는다."""
    return _resolve(
        build_network_index(topology),
        node,
        origin_links,
        max_hops,
        frozenset(str(value) for value in allowed_groups) if allowed_groups is not None else None,
    )


# VISSIM 이 선언한 SG 이름은 진행 방위(NB/SB/EB/WB)와 회전(T 직진 · L 좌 · R 우)을 둘 다
# 담는다. 통제 15 SC 의 SG 136개가 예외 없이 이 꼴이고, 그 축은 신호두 링크 기하와도
# 93/95 에서 같다(`tests/test_native_phase_axis_composition.physical_axis_groups`).
_SG_NAME_MOVEMENT = re.compile(r"([NSEW])B([TLR])")


def _phase_from_signal_group_name(name: str) -> str:
    """SG 이름 -> 모델 4현시. 상류 `movement_phase_id` 와 같은 배정이다.

    major 축은 상류 `MAJOR_AXIS_LEGS = NS_AXIS` 를 따른다 - NS 가 p1/p2, EW 가 p3/p4.
    우회전은 상류와 같이 같은 축의 직진 현시에 붙인다.
    """
    match = _SG_NAME_MOVEMENT.search(str(name).upper())
    if match is None:
        return ""
    approach, turn = match.groups()
    left = turn == "L"
    if approach in ("N", "S"):
        return "p2" if left else "p1"
    return "p4" if left else "p3"


def derive_signal_group_phase(
    group_names: Mapping[str, str],
    head_links_by_group: Mapping[str, Sequence[str]],
    link_to_origins: Mapping[str, Sequence[str]],
    origin_phases: Mapping[str, set[str]],
) -> dict[str, dict[str, Any]]:
    """(SC, SG) -> 모델 phase. origin 이 먼저고 SG 이름은 폴백이다."""
    table: dict[str, dict[str, Any]] = {}
    for sg_id in sorted(group_names, key=_sort_id):
        links = tuple(str(link) for link in head_links_by_group.get(sg_id, ()))
        origins: list[str] = []
        for link in links:
            for origin in link_to_origins.get(link, ()):
                if str(origin) not in origins:
                    origins.append(str(origin))
        phases: set[str] = set()
        for origin in origins:
            phases |= set(origin_phases.get(origin, ()))

        if len(phases) == 1:
            table[sg_id] = {
                "phase": next(iter(phases)),
                "method": "origin_movement",
                "links": list(links),
                "origins": origins,
            }
            continue
        fallback = _phase_from_signal_group_name(group_names[sg_id])
        if not fallback:
            method = "unassigned"
        elif len(phases) > 1:
            method = "signal_group_name_after_conflict"
        else:
            method = "signal_group_name"
        table[sg_id] = {
            "phase": fallback,
            "method": method,
            "links": list(links),
            "origins": origins,
        }
    return table


@dataclass
class _NodeAccount:
    origins: dict[str, OriginResolution] = field(default_factory=dict)
    unresolved: dict[str, str] = field(default_factory=dict)


def origin_leg_bearings(
    grid_node_legs: Mapping[str, Mapping[str, Any]]
) -> dict[str, dict[str, str]]:
    """node -> origin -> 모델 leg 방위. 모델이 이웃을 심은 방향이 유일한 근거다."""
    bearings: dict[str, dict[str, str]] = {}
    for node, legs in grid_node_legs.items():
        table = bearings.setdefault(str(node), {})
        for leg_key, leg in legs.items():
            if not isinstance(leg, Mapping):
                continue
            bearing = str(leg_key).split("_", 1)[0]
            kind = str(leg.get("type", ""))
            if kind == "grid":
                table[f"{leg.get('node')}_to_{node}"] = bearing
            elif kind == "boundary":
                table[str(leg.get("in", ""))] = bearing
            elif kind == "ramp":
                for origin in (leg.get("off") or {}).values():
                    table[str(origin)] = bearing
        table.pop("", None)
    return bearings


def derive(
    topology_path: Path = DEFAULT_TOPOLOGY,
    timing_path: Path = DEFAULT_TIMING,
    config_path: Path = DEFAULT_CONFIG,
    detector_mapping_path: Path = DEFAULT_DETECTOR_MAPPING,
    max_hops: int = MAX_CONNECTOR_HOPS,
) -> dict[str, Any]:
    topology = json.loads(Path(topology_path).read_text(encoding="utf-8"))
    timing = json.loads(Path(timing_path).read_text(encoding="utf-8"))
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    detector_mapping = json.loads(Path(detector_mapping_path).read_text(encoding="utf-8"))

    network = config["config_overrides"]["network"]
    movements: Mapping[str, Mapping[str, Any]] = network["urban_movements"]
    grid_node_legs: Mapping[str, Mapping[str, Any]] = network.get("grid_node_legs", {})
    link_to_origins: Mapping[str, Sequence[str]] = detector_mapping.get("link_to_origins", {})

    index = build_network_index(topology)
    origin_to_links: dict[str, list[str]] = collections.defaultdict(list)
    for link, origins in link_to_origins.items():
        for origin in origins:
            origin_to_links[str(origin)].append(str(link))
    # 오프램프는 커넥터가 둘인데 `link_to_origins` 가 그중 하나만 이름 붙인다
    # (OR_D_W -> 10479 만, 링크 32 로 들어가는 10491 은 SC1004_to_SC1001 로 붙어 있다).
    # 램프 정의 자체가 물리 근거이므로 두 커넥터를 다 출발점으로 쓴다.
    for origin, entries in (detector_mapping.get("off_ramp_connectors") or {}).items():
        for entry in entries:
            link = str(entry.get("connector", ""))
            if link and link not in origin_to_links[str(origin)]:
                origin_to_links[str(origin)].append(link)

    # SG 목록·이름은 `.inpx` 선언(=supplyFile2 가 가리키는 프로그램)을 실은 토폴로지에서 읽는다.
    node_group_names: dict[str, dict[str, str]] = collections.defaultdict(dict)
    for group in topology.get("signal_groups", ()):
        node = f"SC{group['controller_no']}"
        node_group_names[node][str(group["sg_no"])] = str(group.get("name", ""))
    supply_file: dict[str, str] = {}
    for controller in topology.get("signal_controllers", ()):
        node = f"SC{(controller.get('source') or {}).get('vissim_no', '')}"
        # VISSIM 은 네트워크 상대경로를 `#data#` 접두사로 적는다.
        raw = str((controller.get("source_attributes") or {}).get("supplyFile2", "")).strip()
        supply_file[node] = Path(raw[6:] if raw.lower().startswith("#data#") else raw).name

    # 타이밍 표는 교차검사 전용이다. 위 docstring 의 `.sig` 선택 불일치를 여기서 드러낸다.
    timing_groups: dict[str, set[str]] = {}
    timing_sig: dict[str, str] = {}
    cycle_by_node: dict[str, float] = {}
    for controller in timing.get("controllers", ()):
        node = f"SC{controller['sc_no']}"
        timing_groups[node] = {str(group["sg_id"]) for group in controller.get("groups", ())}
        timing_sig[node] = Path(str(controller.get("sig_path", ""))).name
        cycle_by_node[node] = float(controller.get("cycle_sec", 0.0))

    # 모델이 심은 경계 게이트. VISSIM 에 대응 링크가 없는 가상 접근로다.
    boundary_origins: set[str] = set()
    for legs in grid_node_legs.values():
        for leg in legs.values():
            if isinstance(leg, Mapping) and str(leg.get("type", "")) == "boundary":
                boundary_origins.add(str(leg.get("in", "")))
    boundary_origins.discard("")

    # (node, origin) -> 그 origin 을 쓰는 movement 들의 모델 축 집합.
    origin_phases_by_node: dict[str, dict[str, set[str]]] = collections.defaultdict(
        lambda: collections.defaultdict(set)
    )
    phase_movements: list[tuple[str, str, str, str]] = []  # name, node, origin, axis
    for name, spec in movements.items():
        phase = str(spec.get("phase", ""))
        if not phase:
            continue
        node = str(spec.get("intersection", ""))
        origin = str(spec.get("origin", ""))
        axis = phase.rpartition("_")[2]
        origin_phases_by_node[node][origin].add(axis)
        phase_movements.append((str(name), node, origin, axis))

    bearings = origin_leg_bearings(grid_node_legs)

    controllers: dict[str, Any] = {}
    accounts: dict[str, _NodeAccount] = {}
    controlled = [str(value) for value in network.get("signals", ())]
    for node in sorted(controlled, key=lambda value: _sort_id(value[2:])):
        group_names = node_group_names.get(node, {})
        allowed = frozenset(group_names)
        node_heads = index.heads_by_node.get(node, {})
        head_links_by_group: dict[str, list[str]] = collections.defaultdict(list)
        for link, groups in node_heads.items():
            for sg_id in groups:
                if sg_id in allowed:
                    head_links_by_group[sg_id].append(link)

        signal_group_phase = derive_signal_group_phase(
            group_names=group_names,
            head_links_by_group=head_links_by_group,
            link_to_origins=link_to_origins,
            origin_phases={
                origin: axes for origin, axes in origin_phases_by_node.get(node, {}).items()
            },
        )
        phase_signal_groups: dict[str, list[str]] = collections.defaultdict(list)
        for sg_id, entry in signal_group_phase.items():
            if entry["phase"]:
                phase_signal_groups[entry["phase"]].append(sg_id)

        account = _NodeAccount()
        for origin in sorted(origin_phases_by_node.get(node, {})):
            if origin in boundary_origins:
                account.unresolved[origin] = "synthetic_boundary_leg"
                continue
            resolution = _resolve(
                index, node, origin_to_links.get(origin, ()), max_hops, allowed
            )
            if resolution.signal_groups is None:
                account.unresolved[origin] = resolution.reason
            else:
                account.origins[origin] = resolution

        # 같은 방위에 이웃이 둘 심긴 leg 는 물리 접근로가 하나다(관대 대칭화의 결과).
        # 예: SC1001 은 NW_SC2001 과 NW_SC2002 를 다 갖지만 NW 접근 링크는 37 하나다.
        # 링크가 아예 없는 origin 만 같은 방위의 해결된 origin 에서 SG 를 물려받는다.
        node_bearings = bearings.get(node, {})
        for origin, reason in sorted(account.unresolved.items()):
            if reason != "origin_link_unknown":
                continue
            bearing = node_bearings.get(origin, "")
            donors = [
                other
                for other, other_bearing in node_bearings.items()
                if other_bearing == bearing and other in account.origins
            ]
            if not bearing or not donors:
                continue
            groups: set[str] = set()
            links: set[str] = set()
            for donor in donors:
                groups.update(account.origins[donor].signal_groups or ())
                links.update(account.origins[donor].links)
            account.origins[origin] = OriginResolution(
                tuple(sorted(groups, key=_sort_id)),
                "shared_leg_bearing",
                0,
                tuple(sorted(links, key=_sort_id)),
            )
            account.unresolved.pop(origin)
        accounts[node] = account

        controllers[node] = {
            "cycle_sec": cycle_by_node.get(node, 0.0),
            "timing_cross_check": {
                "inpx_supply_file": supply_file.get(node, ""),
                "timing_sig_file": timing_sig.get(node, ""),
                "inpx_signal_groups": len(group_names),
                "timing_signal_groups": len(timing_groups.get(node, ())),
                "agrees": (
                    supply_file.get(node, "") == timing_sig.get(node, "")
                    and set(group_names) == set(timing_groups.get(node, ()))
                ),
            },
            "signal_group_phase": signal_group_phase,
            "phase_signal_groups": {
                phase: sorted(group_ids, key=_sort_id)
                for phase, group_ids in sorted(phase_signal_groups.items())
            },
            "origin_signal_groups": {
                origin: {
                    "signal_groups": list(resolution.signal_groups or ()),
                    "method": resolution.method,
                    "hops": resolution.hops,
                    "links": list(resolution.links),
                }
                for origin, resolution in sorted(account.origins.items())
            },
            "unresolved_origins": dict(sorted(account.unresolved.items())),
        }

    unresolved_by_reason: collections.Counter[str] = collections.Counter()
    method_counts: collections.Counter[str] = collections.Counter()
    unresolved_movements: dict[str, str] = {}
    resolved = 0
    for name, node, origin, _axis in phase_movements:
        account = accounts.get(node)
        if account is None:
            unresolved_movements[name] = "no_signal_controller"
            unresolved_by_reason["no_signal_controller"] += 1
            continue
        resolution = account.origins.get(origin)
        if resolution is None:
            reason = account.unresolved.get(origin, "origin_link_unknown")
            unresolved_movements[name] = reason
            unresolved_by_reason[reason] += 1
            continue
        resolved += 1
        method_counts[resolution.method] += 1

    phase_method_counts: collections.Counter[str] = collections.Counter()
    for payload in controllers.values():
        for entry in payload["signal_group_phase"].values():
            phase_method_counts[entry["method"]] += 1

    return {
        "schema_version": SCHEMA_VERSION,
        "source": {
            "topology": str(Path(topology_path)),
            "topology_compiler_version": str(topology.get("compiler_version", "")),
            "inpx_path": str((topology.get("source") or {}).get("inpx_path", "")),
            "inpx_sha256": str((topology.get("source") or {}).get("inpx_sha256", "")),
            "timing": str(Path(timing_path)),
            "timing_sha256": sha256_file(Path(timing_path)),
            "config": str(Path(config_path)),
            "config_sha256": sha256_file(Path(config_path)),
            "detector_mapping": str(Path(detector_mapping_path)),
            "detector_mapping_sha256": sha256_file(Path(detector_mapping_path)),
            "max_connector_hops": max_hops,
        },
        "controllers": controllers,
        "unresolved_movements": dict(sorted(unresolved_movements.items())),
        "counts": {
            "controllers": len(controllers),
            "phase_movements": len(phase_movements),
            "resolved_movements": resolved,
            "unresolved_movements": len(unresolved_movements),
            "resolved_by_method": dict(sorted(method_counts.items())),
            "unresolved_by_reason": dict(sorted(unresolved_by_reason.items())),
            "signal_group_phase_by_method": dict(sorted(phase_method_counts.items())),
            "timing_cross_check_disagreements": sorted(
                node
                for node, payload in controllers.items()
                if not payload["timing_cross_check"]["agrees"]
            ),
        },
        "status": "PASS",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--topology", type=Path, default=DEFAULT_TOPOLOGY)
    parser.add_argument("--timing", type=Path, default=DEFAULT_TIMING)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--detector-mapping", type=Path, default=DEFAULT_DETECTOR_MAPPING)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--max-hops", type=int, default=MAX_CONNECTOR_HOPS)
    args = parser.parse_args(argv)

    payload = derive(
        topology_path=args.topology,
        timing_path=args.timing,
        config_path=args.config,
        detector_mapping_path=args.detector_mapping,
        max_hops=args.max_hops,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8"
    )
    counts = payload["counts"]
    print(
        "status=%s out=%s movements=%d resolved=%d unresolved=%d"
        % (
            payload["status"],
            args.out,
            counts["phase_movements"],
            counts["resolved_movements"],
            counts["unresolved_movements"],
        )
    )
    print("resolved_by_method=%s" % json.dumps(counts["resolved_by_method"], ensure_ascii=False))
    print("unresolved_by_reason=%s" % json.dumps(counts["unresolved_by_reason"], ensure_ascii=False))
    print(
        "signal_group_phase_by_method=%s"
        % json.dumps(counts["signal_group_phase_by_method"], ensure_ascii=False)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
