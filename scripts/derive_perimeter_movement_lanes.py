"""perimeter movement 의 **정지선 차로수**를 VISSIM 커넥터 기하에서 뽑는다.

문제
----
`install_movement_capacity_by_lanes`(어댑터 1675행)는 **internal 184개만** 차로비례로
재정규화한다. `per_lane = equiv x 184 / Σlanes(internal)` 로 뽑은 값을 internal 에만
심고, perimeter 290개(boundary_in 157 · boundary_out 115 · off_ramp 18)는 맵 밖에 남는다.
그러면 `urban_queue_model._movement_capacity_flow` 가 그들에게 전역 스칼라
`movement_capacity_veh_h = 1400` 을 준다.

결과: 실측 internal 평균 ~330 대 perimeter 1400 — **없던 4배 비대칭**이 생겼다.
lanes 팔 이전엔 둘 다 1400 이라 상대 비교가 최소한 공정했다.

이게 왜 TTT 에 닿나. 방류가 `min(available, T_u_h x green_fraction x cap_flow)` 라
cap 에 **선형**이다. 즉 녹색 1초의 한계 이득이 cap 에 정비례하고, 리더가 현시를 고를 때
쓰는 게 정확히 그 상대값이다. 경계 접근로에 과배분하고 내부를 굶는 방향이다.
라이브 진단 `leader_boundary_in_queue_veh` 가 1,084대라 물량도 작지 않다.

유도
----
`outputs/pn_boundary_turns_v1_20260819.json` 의 `turns` 306개가 이미
`(from_link, connector, to_link, sc, legs)` 를 갖고 있다 — 이게 **물리 회전 정본**이다
(CLAUDE.md: config 의 urban_movements 474개를 회전 목록으로 쓰지 마라, leg 교차곱
선언이라 물리보다 많다). 커넥터 번호로 `.inpx` 의 `<lanes>` 자식 수를 세면 그 회전을
담당하는 차로수가 나온다. 306개 전부 확보된다.

movement 매칭은 beta v2 와 같은 규칙이다 — `legs[0]` 이 (신호, 접근로),
`to_link` 의 권역이 하류 신호. (signal, approach, 하류신호) 는 하류가 실재하면 유일하다.

**검산이 하나 붙는다**: 이 유도가 내는 internal 170개는 기존
`outputs/movement_lanes_core17legs4b_20260821.json`(171개, 다른 경로로 유도)과
독립적으로 만들어졌다. 두 값이 어긋나면 둘 중 하나가 틀린 것이니 리포트에 찍는다.

유령 movement
-------------
boundary_in 157개 중 물리 회전으로 실재하는 것은 61개뿐이다(모호 포함해도 100 미만).
나머지는 leg 교차곱 선언의 유령인데 지금 전부 1400 을 들고 있다. 여기서는 실재가
확인된 것만 값을 주고, 유령은 **목록으로 남긴다** — 무엇을 모르는지 보이게 두는 게
임의값을 넣는 것보다 낫다. 설치기가 회전 종류 중앙값으로 채울지는 그쪽에서 정한다.
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PERIMETER_KINDS = {"boundary_in", "off_ramp", "boundary_out", "on_ramp"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--network", default="network/real_world_gaepo_modi/modi_eval_userfix_20260814e.inpx")
    ap.add_argument("--turns", default="outputs/pn_boundary_turns_v1_20260819.json")
    ap.add_argument("--territory", default="outputs/urban_player_territory_v1_20260819.json")
    ap.add_argument("--movements-config",
                    default="evaluation/configs/real_world_modi_pstack_distributed_core17legs4b_20260819.json")
    ap.add_argument("--cross-check", default="outputs/movement_lanes_core17legs4b_20260821.json")
    ap.add_argument("--out", default="outputs/movement_lanes_perimeter_20260824.json")
    args = ap.parse_args()

    root = ET.parse(ROOT / args.network).getroot()
    lanes_of_link: dict[str, int] = {}
    for link in root.iter("link"):
        node = link.find("lanes")
        lanes_of_link[str(link.get("no"))] = len(list(node)) if node is not None else 0

    terr = json.loads((ROOT / args.territory).read_text(encoding="utf-8"))["territory"]["urban"]
    owner: dict[str, tuple[str, str]] = {}
    for sig, legs in terr.items():
        for leg, ids in legs.items():
            for link_id in ids:
                owner.setdefault(str(link_id), (sig, leg))

    um = json.loads((ROOT / args.movements_config).read_text(encoding="utf-8")) \
        ["config_overrides"]["network"]["urban_movements"]

    def downstream_of(movement: str) -> str | None:
        spec = um[movement]
        if str(spec.get("kind", "")) == "boundary_out":
            return None
        dest = str(spec.get("destination", ""))
        return dest.split("_to_", 1)[1] if "_to_" in dest else None

    index: dict[tuple[str, str, str | None], list[str]] = collections.defaultdict(list)
    for movement in um:
        spec = um[movement]
        index[(str(spec.get("signal", "")), str(spec.get("approach", "")),
               downstream_of(movement))].append(movement)

    turns = json.loads((ROOT / args.turns).read_text(encoding="utf-8"))["turns"]

    resolved: dict[str, float] = {}
    ambiguous, unmatched = 0, 0
    conflicts: list[dict] = []
    for turn in turns:
        legs = turn.get("legs") or []
        if not legs or "·" not in str(legs[0]):
            unmatched += 1
            continue
        sig, approach = str(legs[0]).split("·", 1)
        dest_owner = owner.get(str(turn.get("to_link")))
        dest_sig = dest_owner[0] if dest_owner and dest_owner[0] != sig else None
        hits = index.get((sig, approach, dest_sig)) or []
        if len(hits) != 1:
            ambiguous += len(hits) > 1
            unmatched += not hits
            continue
        movement = hits[0]
        lanes = float(lanes_of_link.get(str(turn.get("connector")), 0))
        if lanes <= 0.0:
            unmatched += 1
            continue
        # 같은 movement 에 회전이 둘 이상 붙으면 차로를 더한다(분리된 접속부).
        resolved[movement] = resolved.get(movement, 0.0) + lanes

    kinds = collections.Counter(str(um[m].get("kind", "")) for m in resolved)
    perimeter = {m: v for m, v in resolved.items()
                 if str(um[m].get("kind", "")) in PERIMETER_KINDS}
    internal = {m: v for m, v in resolved.items()
                if str(um[m].get("kind", "")) not in PERIMETER_KINDS}

    # ---- 독립 유도와의 대조 ----
    cross_path = ROOT / args.cross_check
    agree = disagree = 0
    if cross_path.is_file():
        prev = json.loads(cross_path.read_text(encoding="utf-8")).get("movement_lanes") or {}
        for movement, value in internal.items():
            if movement not in prev:
                continue
            if abs(float(prev[movement]) - value) < 1.0e-6:
                agree += 1
            else:
                disagree += 1
                if len(conflicts) < 12:
                    conflicts.append({"movement": movement, "기존": float(prev[movement]),
                                      "이번": value, "turn": um[movement].get("turn")})

    missing = sorted(m for m, sp in um.items()
                     if str(sp.get("kind", "")) in PERIMETER_KINDS and m not in resolved)
    missing_kinds = collections.Counter(str(um[m].get("kind", "")) for m in missing)

    doc = {
        "schema": "movement_lanes_perimeter/v1",
        "generated": "2026-08-24",
        "derivation": ("pn_boundary_turns_v1 의 물리 회전 306개에서 커넥터 번호를 받아 "
                       ".inpx <link><lanes> 자식 수를 센다. movement 매칭은 "
                       "(signal, approach, 하류신호) — 하류가 실재하면 유일하다."),
        "note": ("perimeter 만 쓰려고 만들었지만 internal 도 함께 나온다. internal 은 "
                 "기존 movement_lanes_core17legs4b_20260821 과 독립 유도라 대조용이다."),
        "movement_lanes_perimeter": perimeter,
        "movement_lanes_internal_crosscheck": internal,
        "perimeter_unresolved": missing,
    }
    (ROOT / args.out).write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"물리 회전 {len(turns)} -> movement 유일 매칭 {len(resolved)}"
          f" (모호 {ambiguous} · 미매칭 {unmatched})")
    print(f"  kind 분포: {dict(kinds)}")
    print(f"\nperimeter 해결 {len(perimeter)}개 · 미해결 {len(missing)}개 {dict(missing_kinds)}")
    if perimeter:
        vals = sorted(perimeter.values())
        print(f"  차로수 min {vals[0]:.0f} · 중앙 {vals[len(vals) // 2]:.0f} · max {vals[-1]:.0f}")
        dist = collections.Counter(perimeter.values())
        print(f"  분포: {dict(sorted(dist.items()))}")
    print(f"\n독립 대조(internal {len(internal)}개 중 기존 파일에도 있는 것):"
          f" 일치 {agree} · 불일치 {disagree}")
    for c in conflicts:
        print(f"    {c['movement']:40s} 기존 {c['기존']:.0f} vs 이번 {c['이번']:.0f} ({c['turn']})")
    print(f"\n저장: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
