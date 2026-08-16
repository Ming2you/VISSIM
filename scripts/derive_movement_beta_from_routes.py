#!/usr/bin/env python3
"""VISSIM 정적 경로에서 movement 의 **분기율 beta** 를 유도한다.

## 왜 필요한가 (2026-08-16 실측)

지금 모델의 beta 는 **542개 전부가 1/n 균등분할**이다(고유값 8개: 1/1 1/2 1/3 1/4 1/5
1/6 1/8 1/10). `grid_topology.py:150-175` 가 순수 기하 휴리스틱으로 만들기 때문이다 —
"직진(정반대 방위)에 0.5, 나머지가 0.5 를 균등분할, 직진 없으면 전부 1/n". 경로 정보가
들어갈 자리가 없다.

그런데 VISSIM 의 실제 회전 비율은 `vehicleRouteStatic.relFlow` 가 **정의**한다. 실측
분포는 0.005 ~ 0.963 으로 크게 비대칭이다. 즉 모델은 질량을 엉뚱한 진출로로 보낸다.

구간 예측 오차 45% 의 증상과 정확히 맞는다 — **총량 보존, 구간별 재배치 오류**, 한
스텝에 즉시 발생, 스텝 따라 안 커짐(파동 전파가 아님).

**이 값은 모델을 CTM 으로 바꿔도 그대로 입력으로 들어간다.** 구조를 바꾸기 전에 여기부터
맞춰야 한다.

## 유도 방법

movement 는 `(origin 저류 -> receiving 저류)` 다(예: SC11_to_SC1 -> SC1_to_SC9001).
그래서 경로의 링크열을 **저류열**로 바꾸면 분기가 그대로 드러난다.

    경로 = decision.link + linkSeq + destLink
    각 링크 -> 저류(SC{상류}_to_SC{소유}, 없으면 SC{소유}_{방위}_out)
    연속 중복 제거 -> 저류열
    연속 쌍 (s1, s2) 마다 relFlow 가중치 누적
    beta(s1->s2) = w(s1,s2) / sum_s2' w(s1,s2')

**`relFlow` 가 비어 있으면 VISSIM 기본값 1 이다(0 아님).** 이 저장소에서 이미 한 번
겪은 함정이라 명시로 처리한다.

## 한계 (산출물에 같이 적는다)

- 같은 저류로 들어오는 결정이 여럿이면 결정별 실제 유입량으로 가중해야 정확한데,
  여기서는 relFlow 만 쓴다. 결정들의 규모가 비슷하다는 가정이다.
- 경로에 안 실린 저류는 유도값이 없다. 그런 movement 는 기존 beta 를 유지한다.
"""

from __future__ import annotations

import argparse
import io
import json
import statistics as st
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Any, Sequence

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
REPO = Path(__file__).resolve().parent.parent


def parse_rel_flow(raw: str | None) -> float:
    """'2 0:122' -> 122.0.  빈 값은 VISSIM 기본 1.0 (0 이 아니다)."""
    text = (raw or "").strip()
    if not text:
        return 1.0
    try:
        return max(0.0, float(text.split(":")[-1]))
    except ValueError:
        return 1.0


def link_storage_map(assignment: dict[str, Any]) -> dict[str, list[tuple[str, float]]]:
    """링크 -> [(저류 이름, 지분)]. derive_urban_storage_capacity.py 와 같은 규칙."""
    owner = assignment.get("link_owner") or {}
    upstream = assignment.get("link_upstream") or {}
    leg = assignment.get("link_leg") or {}
    dsplit = assignment.get("link_split") or {}
    usplit = assignment.get("link_upstream_split") or {}

    def parts(spec_map, link, key, fallback_map):
        spec = spec_map.get(link)
        if spec:
            out = []
            for part in spec.get(key, []):
                to = str(part.get("to", ""))
                if to.startswith("SC"):
                    out.append((int(to[2:]), float(part.get("share", 0.0))))
            if out:
                return out
        v = fallback_map.get(link)
        return [(int(v), 1.0)] if v is not None else [(None, 1.0)]

    out: dict[str, list[tuple[str, float]]] = {}
    for link in owner:
        acc: dict[str, float] = defaultdict(float)
        for own, ds in parts(dsplit, link, "parts", owner):
            if own is None:
                continue
            for up, us in parts(usplit, link, "upstream", upstream):
                w = ds * us
                if w <= 0:
                    continue
                name = f"SC{up}_to_SC{own}" if up is not None else f"SC{own}_{leg.get(link,'?')}_out"
                acc[name] += w
        if acc:
            out[str(link)] = sorted(acc.items())
    return out


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--network", type=Path,
                    default=REPO / "network/real_world_gaepo_modi/modi_eval_userfix_20260814e.inpx")
    ap.add_argument("--assignment", type=Path,
                    default=REPO / "outputs/link_player_assignment_pedfold_20260814.json")
    ap.add_argument("--tuning", type=Path,
                    default=REPO / "evaluation/configs/real_world_modi_pstack_distributed_pedovrx_20260814.json")
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args(argv)

    assignment = json.loads(args.assignment.read_text(encoding="utf-8"))
    lsm = link_storage_map(assignment)
    root = ET.parse(args.network).getroot()

    transition: dict[tuple[str, str], float] = defaultdict(float)
    routes_used = 0
    for dec in root.iter("vehicleRoutingDecisionStatic"):
        start = str(dec.get("link"))
        for rt in dec.iter("vehicleRouteStatic"):
            w = parse_rel_flow(rt.get("relFlow"))
            if w <= 0:
                continue
            path = [start]
            path += [str(p.get("key")) for p in rt.iter("intObjectRef")]
            dest = rt.get("destLink")
            if dest:
                path.append(str(dest))
            # 링크열 -> 저류열 (지분 있는 링크는 가장 큰 지분 하나로 대표)
            seq: list[str] = []
            for link in path:
                cand = lsm.get(link)
                if not cand:
                    continue
                name = max(cand, key=lambda kv: kv[1])[0]
                if not seq or seq[-1] != name:
                    seq.append(name)
            if len(seq) < 2:
                continue
            routes_used += 1
            for a, b in zip(seq, seq[1:]):
                transition[(a, b)] += w

    by_origin: dict[str, dict[str, float]] = defaultdict(dict)
    for (a, b), w in transition.items():
        by_origin[a][b] = w
    derived = {
        a: {b: w / tot for b, w in dests.items()}
        for a, dests in by_origin.items()
        if (tot := sum(dests.values())) > 0
    }

    # 모델 movement 와 대조
    sys.path.insert(0, str(REPO / "evaluation" / "controllers"))
    import vissim_stackelberg_adapter as ad  # noqa: E402

    tun = ad.load_optional_json(str(args.tuning))
    movements = (tun.get("config_overrides") or {}).get("network", {}).get("urban_movements") or {}

    updated, unmatched, deltas = {}, [], []
    for name, spec in movements.items():
        origin = str(spec.get("origin", ""))
        recv = str(spec.get("receiving_link", "") or spec.get("destination", ""))
        got = derived.get(origin, {}).get(recv)
        if got is None:
            unmatched.append(name)
            continue
        old = float(spec.get("beta", 0.0))
        updated[name] = got
        deltas.append(abs(got - old))

    def dist(v):
        v = sorted(v)
        if not v:
            return {}
        return {"n": len(v), "min": v[0], "median": st.median(v),
                "p90": v[int(0.9 * (len(v) - 1))], "max": v[-1]}

    payload = {
        "schema_version": "movement-beta-from-routes-v1",
        "network": args.network.name,
        "routes_used": routes_used,
        "storage_transitions": len(transition),
        "origins_with_split": sum(1 for d in derived.values() if len(d) > 1),
        "movements_total": len(movements),
        "movements_updated": len(updated),
        "movements_unmatched": len(unmatched),
        "beta_change_abs": dist(deltas),
        "derived_beta": updated,
        "unmatched_sample": unmatched[:20],
        "limits": [
            "같은 저류로 들어오는 결정이 여럿이면 결정별 실제 유입량 가중이 정확하나 relFlow 만 썼다",
            "경로에 안 실린 movement 는 기존 beta 를 유지한다",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
                        encoding="utf-8", newline="\n")

    print(f"경로 {routes_used}개에서 저류 전이 {len(transition)}개 유도")
    print(f"분기 있는 origin {payload['origins_with_split']}개")
    print(f"movement {len(movements)}개 중 갱신 {len(updated)} / 미매칭 {len(unmatched)}")
    d = payload["beta_change_abs"]
    if d:
        print(f"beta 변화량 |Δ|  중앙값 {d['median']:.3f}  p90 {d['p90']:.3f}  최대 {d['max']:.3f}")
    if unmatched:
        print("미매칭 예:", unmatched[:4])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
