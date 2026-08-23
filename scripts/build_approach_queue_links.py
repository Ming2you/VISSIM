# -*- coding: utf-8 -*-
"""정지선 **상류** 대기행렬을 그 접근로 movement 큐로 잇는다.

문제. 4c 매핑은 정지선 링크의 귀속을 고쳤지만, 정지선 **뒤로 늘어선 큐**는 여전히
저류로 빠진다. `build_local_observation_summary` 가

    if not link_to_movements.get(link):   # movement 매핑 없으면
        storage_fraction = 1.0            # 전량 저류

로 처리하는데, 저류는 리더의 현시 배분에 안 쓰이고 큐만 쓰인다.

실측 (map4c, t=3600, SC5 동쪽 접근로):

    1220018401  정지 76  매핑 O(4개)   ← 정지선. 큐로 잡힘
    1220018404  정지 42  매핑 없음     ← 저류로 빠짐
     121008402  정지 38  매핑 없음     ←   "
           118  정지 17  매핑 없음     ←   "
    1220018403  정지 17  매핑 없음     ←   "

정지차 222대 중 **146대(66%)** 가 큐에서 사라진다. 그래서 모델은 SC5 동서 큐를 64.4 로
보는데 실측은 238 이다(남북은 86.5 vs 116). 동서가 남북의 2배인데 모델은 더 작게 본다.
컨트롤러가 p3(동서 직진)를 47 -> 28.7 로 깎고, 동쪽 정지차가 무제어 31 -> 231 로 쌓인다.
SC5 하나가 남은 초과의 79%(+304 veh*h)를 차지하는 원인이다.

규칙. 통제 신호의 접근로 권역에 속하는 링크는 그 접근로 movement 에 잇는다.
정지선인지 상류인지 구분하지 않는다 — 대기행렬은 원래 링크를 가로질러 늘어선다.
권역은 정본(`urban_player_territory_v1_20260819.json`)을 읽는다.

무엇을 만드나. `link_to_movements` 에 상류 링크 항목을 **추가**한다(기존 항목은 안 건드림).
그러면 `storage_fraction = 1.0` 강제 분기를 안 타고 정상 분할을 거친다. 가중치는
movement 의 `beta`(회전 분율) 다 — 그 접근로에 선 차가 어느 회전으로 갈지의 비율이다.
"""
from __future__ import annotations
import argparse, collections, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = (1, 5, 6, 7, 11, 12, 16, 101, 105, 107, 108, 109, 1001, 1002, 1003, 1004, 1005)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, help="고칠 검지 매핑(원본은 안 건드린다)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--territory", default="outputs/urban_player_territory_v1_20260819.json")
    ap.add_argument("--movements-config",
                    default="evaluation/configs/real_world_modi_pstack_distributed_core17legs4b_20260819.json")
    ap.add_argument("--observable-only", action="store_true", default=True,
                    help="관측되는 링크만 잇는다(기본). 관측 안 되는 링크는 값이 없어 무의미하다.")
    args = ap.parse_args()

    terr = json.loads((ROOT / args.territory).read_text(encoding="utf-8"))["territory"]["urban"]
    ctrl = {f"SC{n}" for n in CONTROLLED}
    owner: dict[str, tuple[str, str]] = {}
    for sig, legs in terr.items():
        if sig not in ctrl:
            continue
        for leg, ids in legs.items():
            for i in ids:
                owner.setdefault(str(i), (sig, leg))

    cfg = json.loads((ROOT / args.movements_config).read_text(encoding="utf-8"))
    um = cfg["config_overrides"]["network"]["urban_movements"]
    by_approach: dict[tuple[str, str], list[tuple[str, float]]] = collections.defaultdict(list)
    for key, spec in um.items():
        sig = str(spec.get("signal", ""))
        app = str(spec.get("approach", ""))
        beta = max(0.0, float(spec.get("beta", 0.0) or 0.0))
        if sig and app:
            by_approach[(sig, app)].append((key, beta))

    doc = json.loads((ROOT / args.source).read_text(encoding="utf-8"))
    l2m = dict(doc.get("link_to_movements") or {})
    observable = {str(x) for x in (doc.get("observable_links") or [])}

    added, skipped = 0, collections.Counter()
    bearing = collections.Counter()
    for link, (sig, leg) in sorted(owner.items()):
        if link in l2m:
            skipped["이미 매핑됨"] += 1
            continue
        if args.observable_only and link not in observable:
            skipped["관측 안 됨"] += 1
            continue
        members = by_approach.get((sig, leg))
        if not members:
            skipped["approach 에 movement 없음"] += 1
            continue
        total = sum(w for _, w in members) or float(len(members))
        l2m[link] = [
            {"movement": m,
             "weight": (w / total) if total > 0 else 1.0 / len(members),
             "source": "territory_approach_upstream",
             "approach": leg}
            for m, w in sorted(members)
        ]
        added += 1
        bearing[leg.split("_")[0]] += 1

    doc["link_to_movements"] = {k: l2m[k] for k in sorted(l2m, key=lambda x: (len(x), x))}
    src = dict(doc.get("link_to_movements_source") or {})
    src["upstream_rule"] = "통제 신호 접근로 권역 링크를 그 접근로 movement 에 beta 로 연결(정지선 상류 대기행렬 회수)"
    src["upstream_added_links"] = added
    src["upstream_generator"] = "scripts/build_approach_queue_links.py"
    doc["link_to_movements_source"] = src
    (ROOT / args.out).write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"상류 링크 {added}개 추가 · 방위 {dict(bearing)}")
    print(f"제외: {dict(skipped)}")
    print(f"link_to_movements 총 {len(doc['link_to_movements'])}개 -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
