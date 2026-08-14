#!/usr/bin/env python3
# movement 의 **진출** 경로가 그 SC 의 신호두를 지나는지 망에서 판정한다
"""우회전이 직진 현시에 얹히는 것을 기하 규칙이 아니라 신호두 근거로 고친다.

## 무엇을 푸는가

`src/models/grid_topology.movement_phase_id` 는 현시를 **기하**로 정한다.

    major 직진 p1 · major 좌 p2 · minor 직진 p3 · minor 좌 p4
    "우회전·미상 회전은 같은 축의 직진 현시에 붙인다"

그런데 실제 VISSIM 신호그룹 이름에는 `R` 이 없다 — 통제 15 SC 의 SG 136개가
`NBT/NBL/EBT/EBL/...` 뿐이고 **우회전 전용 SG 가 아예 없다.** 우회전은 둘 중 하나다.

    직진과 같은 차로에 있다      적색에 앞차가 막아 물리적으로도 못 나간다 → 지금 배정이 맞다
    별도 슬립으로 먼저 빠진다     신호두를 안 지난다 → phase="" 여야 한다

기하로는 이 둘을 못 가른다. **망에서 신호두를 지나는지 보면 갈린다.**

## 판정 규약

movement (노드 N, 진입 leg A, 진출 leg E) 를 VISSIM 링크에 이렇게 잇는다.

    진입 링크 = link_owner 가 N 이고 link_upstream 이 A 의 이웃인 링크
    진출 링크 = link_owner 가 E 의 이웃이고 link_upstream 이 N 인 링크

그 사이를 커넥터로 걸어가며 **N 의 신호두가 붙은 링크를 지나는지** 본다. 지나면
그 SG 를 기록하고 phase 를 유지, 안 지나면 `phase=""` 후보로 낸다.

`phase=""` 는 `urban_queue_model._phase_green_fraction` 에서 green_fraction 1.0 이다
(비통제 노드가 쓰는 길과 같다).

## 무엇을 하지 않는가

경계 movement(`boundary_in`/`boundary_out`)는 판정하지 않는다. 모델이 심은 가상
접근로라 VISSIM 에 대응 링크가 없다 — `derive_movement_signal_group_map.py` 가
`synthetic_boundary_leg` 로 따로 세는 것과 같은 이유다.

## 실측 (2026-08-14, pedovr 격자)

    internal movement 200개 전부 해석됨(링크 못 찾음 0)
    직진 52 / 좌 72 는 예외 없이 신호두를 지난다
    우회전 72개 중 69개가 지난다 — 기하 규칙이 대부분 맞다
    안 지나는 우회전 3개 (beta 합 0.75 = 신호 movement 의 1.9%)
    U턴 4개는 전부 안 지난다 — 별건으로 기록만 한다
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Mapping
import xml.etree.ElementTree as ET


def load_network(path: Path):
    root = ET.parse(path).getroot()
    conn: dict[str, dict[str, Any]] = {}
    down: dict[str, set[str]] = defaultdict(set)
    for link in root.iter("link"):
        no = link.get("no")
        if no is None:
            continue
        no = str(no)
        src, dst = link.find("./fromLinkEndPt"), link.find("./toLinkEndPt")
        if src is None or dst is None:
            continue
        a = (src.get("lane") or "").split()
        b = (dst.get("lane") or "").split()
        if len(a) == 2 and len(b) == 2:
            conn[no] = {"from": a[0], "lane": int(a[1]), "to": b[0]}
            down[a[0]].add(no)
            down[no].add(b[0])
    heads: dict[str, set[str]] = defaultdict(set)
    for head in root.iter("signalHead"):
        lane = (head.get("lane") or "").split()
        sg = head.get("sg") or ""
        if len(lane) == 2 and sg:
            heads[lane[0]].add(sg)
    return conn, down, heads


def node_number(token: str) -> int | None:
    """`NE_SC11` -> 11, `SC5` -> 5. 방위만 있는 경계 leg 은 None."""
    tail = str(token).split("_")[-1]
    if not tail.startswith("SC"):
        return None
    try:
        return int(tail[2:])
    except ValueError:
        return None


def walk(starts, goals, node, down, heads, max_hops):
    """starts -> goals 경로가 node 의 신호두를 지나는가. (지남, SG 목록, 경로)"""
    goal_set = set(goals)
    seen = set(starts)
    queue = deque((s, [s], False, frozenset()) for s in starts)
    fallback = None
    while queue:
        cur, path, hit, sgs = queue.popleft()
        if len(path) > max_hops:
            continue
        mine = {s for s in heads.get(cur, ()) if s.split()[0] == str(node)}
        if mine:
            hit, sgs = True, sgs | frozenset(mine)
        if cur in goal_set and len(path) > 1:
            if hit:
                return True, sorted(sgs), path
            if fallback is None:
                fallback = (False, [], path)
            continue
        for nxt in down.get(cur, ()):
            if nxt in seen:
                continue
            seen.add(nxt)
            queue.append((nxt, path + [nxt], hit, sgs))
    return fallback if fallback else (False, [], None)


def derive(network: Path, assignment: Mapping[str, Any], config: Mapping[str, Any],
           max_hops: int) -> dict[str, Any]:
    conn, down, heads = load_network(network)
    movements = config["config_overrides"]["network"]["urban_movements"]
    owner = assignment["link_owner"]
    upstream = assignment.get("link_upstream") or {}

    # (소유 SC, 상류 SC) -> 링크들. 진입·진출 양쪽을 이걸로 특정한다.
    by_pair: dict[tuple[int, int], list[str]] = defaultdict(list)
    for link, sc in owner.items():
        up = upstream.get(link)
        if up is not None:
            by_pair[(int(sc), int(up))].append(str(link))

    rows: list[dict[str, Any]] = []
    unresolved: list[dict[str, str]] = []
    for key, spec in movements.items():
        if spec.get("kind") != "internal":
            continue
        node = node_number(str(spec["intersection"]))
        appr = node_number(str(spec["approach"]))
        exit_ = node_number(str(spec["exit"]))
        if node is None or appr is None or exit_ is None:
            unresolved.append({"movement": key, "reason": "leg 토큰에 SC 가 없다"})
            continue
        starts = by_pair.get((node, appr), [])
        goals = by_pair.get((exit_, node), [])
        if not starts or not goals:
            unresolved.append({"movement": key, "reason": "진입/진출 링크를 못 찾음"})
            continue
        hit, sgs, path = walk(starts, goals, node, down, heads, max_hops)
        rows.append({
            "movement": key, "signal": spec.get("signal"), "turn": spec.get("turn"),
            "phase_geometric": spec.get("phase"), "beta": spec.get("beta"),
            "passes_head": hit, "signal_groups": sgs,
            "path": path[:8] if path else None,
        })

    free = [r for r in rows if not r["passes_head"] and r["phase_geometric"]]
    beta_free = sum(float(r["beta"] or 0) for r in free)
    beta_all = sum(float(r["beta"] or 0) for r in rows if r["phase_geometric"])
    return {
        "network": network.name,
        "rule": "movement 진입->진출 경로가 그 SC 의 신호두를 지나면 phase 유지, 안 지나면 phase=''",
        "counts": {
            "resolved": len(rows), "unresolved": len(unresolved),
            "by_turn": {
                t: {
                    "passes": sum(1 for r in rows if r["turn"] == t and r["passes_head"]),
                    "free": sum(1 for r in rows if r["turn"] == t and not r["passes_head"]),
                }
                for t in sorted({str(r["turn"]) for r in rows})
            },
            "phase_override_count": len(free),
            "beta_freed": round(beta_free, 4),
            "beta_signalled_total": round(beta_all, 4),
            "beta_freed_share": round(beta_free / beta_all, 5) if beta_all else 0.0,
        },
        "phase_override": {r["movement"]: "" for r in free},
        "movements": rows,
        "unresolved": unresolved,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--network", required=True, type=Path)
    ap.add_argument("--assignment", required=True, type=Path)
    ap.add_argument("--config", required=True, type=Path)
    ap.add_argument("--max-hops", type=int, default=8)
    ap.add_argument("--json-out", default="")
    args = ap.parse_args()

    out = derive(
        args.network,
        json.loads(args.assignment.read_text(encoding="utf-8")),
        json.loads(args.config.read_text(encoding="utf-8")),
        args.max_hops,
    )
    c = out["counts"]
    print(f"internal movement 해석 {c['resolved']}개 / 미해석 {c['unresolved']}개")
    print(f"{'회전':<10}{'신호두 지남':>12}{'안 지남':>10}")
    for turn, v in c["by_turn"].items():
        print(f"{turn:<10}{v['passes']:>12}{v['free']:>10}")
    print(f"\nphase='' 로 풀 movement {c['phase_override_count']}개 "
          f"(beta {c['beta_freed']} / {c['beta_signalled_total']} = "
          f"{c['beta_freed_share']*100:.2f}%)")
    for m in out["phase_override"]:
        r = next(x for x in out["movements"] if x["movement"] == m)
        print(f"   {m:<46} {r['phase_geometric']:<12} turn={r['turn']} beta={r['beta']}")
    if args.json_out:
        p = Path(args.json_out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\nJSON={p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
