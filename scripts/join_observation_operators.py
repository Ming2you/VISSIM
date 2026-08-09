#!/usr/bin/env python3
# canonical topology 의 관측 연산자(측정소·통행시간·큐카운터)를 도로링크에 조인하는 모듈 (v3 N3-1a W2)
"""Resolve `observation_operators` onto the canonical road-link table.

The operators reference VISSIM link numbers, but a number can name either a road
link (`links`) or a connector (`connectors`) - they are disjoint namespaces in the
compiled topology. Only road links are joinable here.

Whatever fails to resolve is **not** dropped. Every operator lands in exactly one of
`resolved` / `unresolved`, and each unresolved entry carries a classified reason, so
the plan invariant "unresolved is zero or explicitly accounted" is checkable rather
than balanced by residual.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


UNRESOLVED_ON_CONNECTOR = "endpoint_on_connector"
UNRESOLVED_NOT_IN_TOPOLOGY = "endpoint_not_in_topology"
UNRESOLVED_UNSUPPORTED_KIND = "unsupported_operator_kind"


@dataclass(frozen=True)
class JoinResult:
    resolved: tuple[dict[str, Any], ...]
    unresolved: tuple[dict[str, Any], ...]

    @property
    def total(self) -> int:
        return len(self.resolved) + len(self.unresolved)


def _index_by_vissim_no(entries: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    return {str(entry["source"]["vissim_no"]): str(entry["id"]) for entry in entries}


def _endpoints(operator: Mapping[str, Any]) -> list[dict[str, Any]] | None:
    """관측 연산자를 (역할, 링크번호, 위치) 끝점 목록으로 편다. 미지원 종류면 None."""
    kind = operator.get("kind")
    if kind == "data_collection_point":
        lane_ref = operator.get("lane_ref", {})
        return [
            {
                "role": "point",
                "link_no": str(lane_ref.get("link_no")),
                "position_m": operator.get("position_m"),
                "lane_no": lane_ref.get("lane_no"),
            }
        ]
    if kind == "queue_counter":
        return [
            {
                "role": "point",
                "link_no": str(operator.get("link_no")),
                "position_m": operator.get("position_m"),
            }
        ]
    if kind == "travel_time_measurement":
        return [
            {
                "role": role,
                "link_no": str(operator.get(role, {}).get("link_no")),
                "position_m": operator.get(role, {}).get("position_m"),
            }
            for role in ("start", "end")
        ]
    return None


def _operator_identity(operator: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": operator.get("id"),
        "kind": operator.get("kind"),
        "vissim_no": operator.get("vissim_no"),
    }


def join_observation_operators(topology: Mapping[str, Any]) -> JoinResult:
    """관측 연산자 전체를 도로링크에 조인한다. 해석 실패분은 사유와 함께 그대로 남긴다."""
    road_by_no = _index_by_vissim_no(topology.get("links", ()))
    connector_by_no = _index_by_vissim_no(topology.get("connectors", ()))

    resolved: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []

    for operator in topology.get("observation_operators", ()):
        entry = _operator_identity(operator)
        endpoints = _endpoints(operator)
        if endpoints is None:
            entry["reasons"] = [{"reason": UNRESOLVED_UNSUPPORTED_KIND}]
            unresolved.append(entry)
            continue

        joined: list[dict[str, Any]] = []
        reasons: list[dict[str, Any]] = []
        for endpoint in endpoints:
            link_no = endpoint["link_no"]
            link_id = road_by_no.get(link_no)
            if link_id is not None:
                joined.append({**endpoint, "link_id": link_id})
                continue
            reason = {
                "role": endpoint["role"],
                "link_no": link_no,
                "reason": (
                    UNRESOLVED_ON_CONNECTOR
                    if link_no in connector_by_no
                    else UNRESOLVED_NOT_IN_TOPOLOGY
                ),
            }
            if link_no in connector_by_no:
                reason["connector_id"] = connector_by_no[link_no]
            reasons.append(reason)

        if reasons:
            entry["reasons"] = reasons
            unresolved.append(entry)
        else:
            entry["link_ids"] = [point["link_id"] for point in joined]
            entry["endpoints"] = joined
            resolved.append(entry)

    return JoinResult(resolved=tuple(resolved), unresolved=tuple(unresolved))


def summarize_join(result: JoinResult) -> dict[str, Any]:
    """종류별 계수와 미해석 사유 분포를 낸다. 항등식 점검용 보고서."""
    by_kind: dict[str, dict[str, int]] = {}
    for bucket, field in ((result.resolved, "resolved"), (result.unresolved, "unresolved")):
        for item in bucket:
            counts = by_kind.setdefault(
                str(item["kind"]), {"total": 0, "resolved": 0, "unresolved": 0}
            )
            counts["total"] += 1
            counts[field] += 1
    reasons = Counter(
        reason["reason"] for item in result.unresolved for reason in item["reasons"]
    )
    return {
        "total": result.total,
        "resolved": len(result.resolved),
        "unresolved": len(result.unresolved),
        "by_kind": by_kind,
        "unresolved_reasons": dict(reasons),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("topology", type=Path, help="canonical_topology.json 경로")
    parser.add_argument("--output", type=Path, default=None, help="조인 결과 JSON 출력 경로")
    args = parser.parse_args(argv)

    topology = json.loads(args.topology.read_text(encoding="utf-8"))
    result = join_observation_operators(topology)
    summary = summarize_join(result)

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(
                {
                    "summary": summary,
                    "resolved": list(result.resolved),
                    "unresolved": list(result.unresolved),
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )

    json.dump(summary, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
