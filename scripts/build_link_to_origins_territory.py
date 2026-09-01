# -*- coding: utf-8 -*-
"""`link_to_origins` 를 권역 정본에서 다시 만든다.

무엇이 문제였나
---------------
`link_to_origins` 는 "VISSIM 링크 -> 모델 origin 이름" 표다. 쓰이는 데가 둘인데 성격이 다르다.

  파생 시점  `derive_movement_signal_group_map.py` 가 "이 origin 은 어느 링크인가" 를 물어
             거기서 신호두까지 걸어가 어느 SG 가 그 회전을 담당하는지 알아낸다.
  런타임     어댑터(`vissim_stackelberg_adapter.py:1834`)가 관측 링크 대수를
             `_link_storage_split_fraction` 으로 저류/대기로 나눌 때 쓴다.

core17legs4b 세대 대장이 얇다 — 링크 279개, config 가 쓰는 origin 이름 123개 중 **56개**만 안다
(pedovrx 는 1,194 링크). 그래서 movement map 을 재유도하면 해석이 194 -> 149 로 떨어지고,
`SC1001_to_SC1003` 의 실측 근거(링크 39 가 SG 4·7 을 단다)를 잃어 SG4 가 이름 규칙으로
엉뚱한 현시에 붙는다. 그 결과 SC1003 의 p2 에 금지쌍 (3,4)·(4,7) 이 함께 들어간다.

전수 수집으로는 안 풀린다 — "링크 39가 SC1001_to_SC1003 에 속한다" 는 소유 관계 선언이지
차량을 세어서 나오는 사실이 아니다. 그 선언은 이미 권역 정본에 있다.

규칙
----
  구간 `SCa_to_SCb`  =  SCb 의 leg 중 이웃이 SCa 인 것의 권역 링크
  경계 `in_SCx_D`    =  SCx 의 방위 D 경계 leg 의 권역 링크

측정 (2026-08-19)
-----------------
  config origin 이름 인식   56 -> 119 / 123   (남은 4개 OR_* 는 off_ramp_connectors 가 처리)
  movement 해석             149 -> 254        미해결은 전부 synthetic_boundary_leg
  origin_link_head            0 -> 228        실측 경로 복원
  SC1003 금지쌍 동거          2 -> 0
  관측 링크가 닿는 origin 중 모델이 모르는 것  44 -> 0
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEF_TERR = ROOT / "outputs/urban_player_territory_v1_20260819.json"
DEF_CFG = ROOT / "evaluation/configs/real_world_modi_pstack_distributed_core17legs4b_20260819.json"
DEF_DM = (ROOT / "evaluation/real_world_modi_control_distributed_20260728"
          / "detector_local_mapping_distributed_core17legs4b_20260819.json")


def build(terr: dict) -> dict[str, list[str]]:
    urb = terr["territory"]["urban"]
    out: dict[str, set[str]] = collections.defaultdict(set)
    for sc, legs in urb.items():
        for key, links in legs.items():
            nb = key.split("_", 1)[1] if "_" in key else None
            if nb and nb.startswith("SC"):
                name = f"{nb}_to_{sc}"          # 구간: 상류 SC -> 소유 SC
            else:
                name = f"in_{sc}_{key.split('_')[0]}"   # 경계 leg
            for link in links:
                out[str(link)].add(name)
    return {k: sorted(v) for k, v in sorted(out.items(), key=lambda kv: int(kv[0]))}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--territory", type=Path, default=DEF_TERR)
    ap.add_argument("--config", type=Path, default=DEF_CFG)
    ap.add_argument("--detector-mapping", type=Path, default=DEF_DM,
                    help="여기의 link_to_origins 를 교체한다")
    ap.add_argument("--out", type=Path, default=None, help="생략하면 --detector-mapping 을 덮어쓴다")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    terr = json.loads(a.territory.read_text(encoding="utf-8"))
    dm = json.loads(a.detector_mapping.read_text(encoding="utf-8"))
    netcfg = json.loads(a.config.read_text(encoding="utf-8"))["config_overrides"]["network"]
    model = {str(s["origin"]) for s in netcfg["urban_movements"].values() if s.get("origin")}
    model |= {str(s["receiving_link"]) for s in netcfg["urban_movements"].values()
              if s.get("receiving_link")}

    new = build(terr)
    old = dm.get("link_to_origins") or {}
    obs = {str(x) for x in (dm.get("observable_links") or [])}

    def names(table, keys):
        s: set[str] = set()
        for k in keys:
            s |= set(map(str, table.get(k, [])))
        return s

    on, nn = names(old, obs), names(new, obs)
    print(f"link_to_origins  링크 {len(old)} -> {len(new)}")
    print(f"  config origin 이름 인식  {len(names(old, old) & model)} -> {len(names(new, new) & model)} / {len(model)}")
    print(f"  관측 링크 {len(obs)} 중 매핑됨  {len(obs & set(old))} -> {len(obs & set(new))}")
    print(f"  관측이 닿는 origin        {len(on)} -> {len(nn)}"
          f"   그중 모델이 모르는 것 {len(on - model)} -> {len(nn - model)}")
    ch = [k for k in set(old) | set(new) if sorted(old.get(k, [])) != sorted(new.get(k, []))]
    print(f"  매핑이 달라지는 링크 {len(ch)}  (그중 관측 링크 {len(set(ch) & obs)})")

    if a.dry_run:
        return 0
    dm["link_to_origins"] = new
    dm["link_to_origins_source"] = {
        "generator": "scripts/build_link_to_origins_territory.py",
        "territory": a.territory.name,
        "rule": "SCa_to_SCb = SCb 의 leg 중 이웃이 SCa 인 것의 권역 링크 · in_SCx_D = 경계 leg 권역",
        "replaced_on": "2026-08-19",
        "why": ("옛 표가 링크 279개뿐이고 config origin 이름 123개 중 56개만 알아, movement map "
                "재유도 시 SC1001_to_SC1003 의 실측 근거(링크 39 -> SG 4·7)를 잃고 SC1003 의 p2 에 "
                "금지쌍 (3,4)·(4,7) 이 함께 들어갔다."),
    }
    out = a.out or a.detector_mapping
    out.write_text(json.dumps(dm, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"\n-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
