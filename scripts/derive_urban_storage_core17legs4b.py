# -*- coding: utf-8 -*-
"""저류 용량을 core17legs4b 정본 위에서 다시 유도한다.

왜 새로 쓰나
------------
`scripts/derive_urban_storage_capacity.py` 의 기본 입력이 저장소 최고령 세대다
(`link_player_assignment_20260805` · `intersection_adjacency8_20260804`). 인자 없이 돌리면
2026-08-04 근거로 재유도하고, 경로만 바꿔도 링크배정 아티팩트가 옛 8방위라
`SC1004_SE_out` 같은 이름을 뱉는다(그 산출물은 격리해 뒀다).

그리고 인접표의 `internal_link_members` 는 구간 링크를 덜 모은다 — 그것으로 재면
`SC5_to_SC101` 이 0.08 km 로 나온다(실제 0.69 km). 그래서 **권역 정본**을 구간 정의로 쓴다.

  구간 `SCa_to_SCb`  =  SCb 의 leg 중 이웃이 SCa 인 것의 권역 링크
`SCx_D_out`(진출 링크) 은 **손대지 않는다.** 경계 회전의 도착 링크로 재보면 freeway 본선
(link 26 등)까지 물려 `SC1004_S_out` 이 1,790 veh 로 나온다. 진출 링크는 보호망 밖이라
리더의 누적에 들어가지도 않는다. 기존 값(대개 기본 220)을 그대로 둔다.

검증: 이 정의로 jam168 산출물과 공유하는 64구간을 재계산하면 비율 중앙값 1.07 로 재현된다.
차이는 jam168 이 `link_split` 지분으로 링크를 나눠 가진 것이고, 여기서는 링크를 통째로 센다.

jam density 는 실측값(`urban_storage_capacity_jam168_20260815.json`, 168.18 veh/km/lane,
표본 20,338)을 쓴다. 여기서 다시 추정하지 않는다.
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import statistics
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEF_INPX = ROOT / "network/real_world_gaepo_modi/modi_eval_userfix_20260814e.inpx"
DEF_CFG = ROOT / "evaluation/configs/real_world_modi_pstack_distributed_core17legs4b_20260819.json"
DEF_TERR = ROOT / "outputs/urban_player_territory_v1_20260819.json"
DEF_TURNS = ROOT / "outputs/pn_boundary_turns_v1_20260819.json"
DEF_JAM = ROOT / "outputs/urban_storage_capacity_jam168_20260815.json"
DEF_OUT = ROOT / "outputs/urban_storage_capacity_core17legs4b_20260819.json"


def read_net(inpx: Path):
    lanes, pts = {}, {}
    for _, el in ET.iterparse(str(inpx), events=("end",)):
        if el.tag == "link":
            no = el.get("no")
            p = [(float(q.get("x")), float(q.get("y"))) for q in el.iter("linkPolyPoint")]
            if p:
                pts[no] = p
            n = len(list(el.iter("lane")))
            if n:
                lanes[no] = n
            el.clear()
    return lanes, pts


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--inpx", type=Path, default=DEF_INPX)
    ap.add_argument("--config", type=Path, default=DEF_CFG)
    ap.add_argument("--territory", type=Path, default=DEF_TERR)
    ap.add_argument("--turns", type=Path, default=DEF_TURNS)
    ap.add_argument("--jam-source", type=Path, default=DEF_JAM)
    ap.add_argument("--out", type=Path, default=DEF_OUT)
    ap.add_argument("--min-capacity", type=float, default=10.0)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    lanes, pts = read_net(a.inpx)
    J = json.loads(a.jam_source.read_text(encoding="utf-8"))
    jam = float(J["jam_density_veh_km_lane"])
    ref = J.get("urban_link_storage_veh") or {}
    urb = json.loads(a.territory.read_text(encoding="utf-8"))["territory"]["urban"]
    turns = json.loads(a.turns.read_text(encoding="utf-8"))["turns"]
    netcfg = json.loads(a.config.read_text(encoding="utf-8"))["config_overrides"]["network"]
    want = list(netcfg.get("urban_link_storage_veh") or {})

    def length_km(link):
        p = pts.get(link) or []
        return sum(math.dist(p[i], p[i + 1]) for i in range(len(p) - 1)) / 1000.0

    def capacity(links):
        km = sum(length_km(l) for l in links)
        veh = sum(length_km(l) * lanes.get(l, 1) for l in links) * jam
        return round(max(veh, a.min_capacity), 1), round(km, 4)

    # --- 구간: SCa_to_SCb = SCb 의 (이웃이 SCa 인) leg 권역 --------------------
    seg = {}
    for sc, legs in urb.items():
        for k, links in legs.items():
            if "_" not in k:
                continue
            nb = k.split("_", 1)[1]
            if nb.startswith("SC"):
                seg.setdefault(f"{nb}_to_{sc}", set()).update(links)

    storage, length, source, missing = {}, {}, {}, []
    for key in want:
        if key in seg:
            storage[key], length[key] = capacity(seg[key])
            source[key] = "territory_segment"
        else:
            missing.append(key)          # 대부분 *_out — 기존 값을 유지한다
    for key in seg:                                  # config 에 없던 구간도 채운다
        if key not in storage:
            storage[key], length[key] = capacity(seg[key])
            source[key] = "territory_segment"

    ratios = [storage[k] / ref[k] for k in storage if k in ref and ref[k]]
    print(f"jam {jam} veh/km/lane (표본 {J.get('jam_sample_count')})")
    print(f"config 가 요구하는 키 {len(want)}  구간으로 채움 {len(want)-len(missing)}  "
          f"손대지 않음 {len(missing)} (진출 링크 *_out 등)")
    print(f"산출 총 {len(storage)}  ({collections.Counter(source.values())})")
    if ratios:
        print(f"jam168 과 공유 {len(ratios)}개 — 비율 중앙값 {statistics.median(ratios):.3f}")
    prev = netcfg.get("urban_link_storage_veh") or {}
    ch = [(k, prev[k], storage[k]) for k in storage if k in prev and abs(float(prev[k]) - storage[k]) > 0.5]
    add = [k for k in storage if k not in prev]
    print(f"config 대비 — 신규 {len(add)}  값 변경 {len(ch)}")
    for k in sorted(add)[:20]:
        print(f"   신규 {k:24s} {storage[k]:8.1f}")
    b220 = [(k, p, n) for k, p, n in ch if abs(float(p) - 220) < 1e-9]
    print(f"   그중 220 폴백이던 것 {len(b220)}:")
    for k, p, n in sorted(b220)[:20]:
        print(f"        {k:24s} 220 -> {n:8.1f}")

    if a.dry_run:
        return 0
    payload = {
        "schema": "urban_storage_capacity/core17legs4b",
        "generated": "2026-08-19",
        "generator": "scripts/derive_urban_storage_core17legs4b.py",
        "jam_density_veh_km_lane": jam,
        "jam_source": a.jam_source.name,
        "definition": {
            "segment": "SCa_to_SCb = SCb 의 leg 중 이웃이 SCa 인 것의 권역 링크 (권역 정본 기준)",
            "boundary_out": "손대지 않음 — 진출 링크는 보호망 밖이라 리더 누적에 안 들어간다",
            "capacity": "sum(link_length_km * lanes) * jam_density, 하한 min-capacity",
        },
        "sources": {"inpx": a.inpx.name, "config": a.config.name,
                    "territory": a.territory.name, "turns": a.turns.name},
        "urban_link_storage_veh": {k: storage[k] for k in sorted(storage)},
        "urban_link_length_km": {k: length[k] for k in sorted(length)},
        "source_by_key": {k: source[k] for k in sorted(source)},
        "untouched_keys": missing,
    }
    a.out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n-> {a.out}  ({a.out.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
