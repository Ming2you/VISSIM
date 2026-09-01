# -*- coding: utf-8 -*-
"""`urban_input_gate_map` 을 core17legs4b 세대로 재기준한다.

왜 필요한가
-----------
러너 VBS 가 vehicleInput 을 게이트에 조인해 `state.demand.urban_volume_vph_by_gate` 를
만들고, 어댑터(`vissim_stackelberg_adapter.py:3120`)가 그 게이트 이름이 config 의
`boundary_in_links`/`boundary_out_links` 에 없으면 **ValueError 로 런을 세운다.**

기존 대장 셋은 legs4b config 가 모르는 이름을 내보낸다.
  urban_input_gate_map_20260811.csv   (VBS 기본값) mapped 19 중 미지 1  in_SC9001_S
  urban_input_gate_map_legfix_…       mapped 18 중 미지 1  in_SC9001_S
  urban_input_gate_map_pedovr_…       mapped 22 중 미지 4  in_SC1004_SE · in_SC1004_SW
                                                          · in_SC13_S · in_SC9001_S
미지 4개의 원인은 둘뿐이다 — 8방위 잔재(SE/SW)와, 2026-08-18 에 mid-block 으로 강등한
노드(SC13 · SC9001)를 아직 가리키는 것.

무엇을 하는가
-------------
pedovr 대장(가장 완전, mapped 22)을 바탕으로 미지 게이트만 legs4b 로 옮긴다.

  게이트 = **진입 링크를 소유한 경계면 leg**  (권역 정본 기준)
  소유가 둘 이상이면 `boundary_extra_legs_legs4b_20260819.csv` 의 분담이 큰 쪽

VBS 는 `no · gate · status` 세 열만 읽는다(`LoadUrbanInputGateMap`). 나머지 열과
주석은 사람이 읽는 근거다. 주석의 `expected_mapped=` 는 부분 stale 을 잡는 유일한
장치라 반드시 실제 mapped 수와 맞아야 한다.
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEF_BASE = ROOT / "evaluation/real_world_modi_inventory/urban_input_gate_map_pedovr_20260814.csv"
DEF_CFG = ROOT / "evaluation/configs/real_world_modi_pstack_distributed_core17legs4b_20260819.json"
DEF_TERR = ROOT / "outputs/urban_player_territory_v1_20260819.json"
DEF_LEGS = ROOT / "evaluation/real_world_modi_inventory/boundary_extra_legs_legs4b_20260819.csv"
DEF_OUT = ROOT / "evaluation/real_world_modi_inventory/urban_input_gate_map_legs4b_20260819.csv"

FOLD = {"NE": "E", "NW": "N", "SW": "W", "SE": "S"}


def read_gate_map(p: Path):
    rows, hdr = [], None
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        if hdr is None:
            hdr = line.split(",")
            continue
        f = line.split(",", len(hdr) - 1)          # name 열에 콤마가 있다 — 마지막 열은 통째로
        rows.append(dict(zip(hdr, f)))
    return hdr, rows


def read_extra_legs(p: Path):
    """(node, leg) 별 분담. 같은 source_link 를 여러 player 가 나눠 가질 수 있다."""
    out = collections.defaultdict(list)
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip() or line.startswith("model_node,"):
            continue
        f = line.split(",", 6)
        node, leg, _st, veh, inflow, links, note = (f + [""] * 7)[:7]
        for lk in links.split():
            out[lk].append({"node": node, "leg": leg,
                            "veh": float(veh or 0), "inflow": float(inflow or 0), "note": note})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base", type=Path, default=DEF_BASE)
    ap.add_argument("--config", type=Path, default=DEF_CFG)
    ap.add_argument("--territory", type=Path, default=DEF_TERR)
    ap.add_argument("--extra-legs", type=Path, default=DEF_LEGS)
    ap.add_argument("--out", type=Path, default=DEF_OUT)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    netcfg = json.loads(a.config.read_text(encoding="utf-8"))["config_overrides"]["network"]
    KEYS = {str(x) for x in netcfg["boundary_in_links"]} | {str(x) for x in netcfg["boundary_out_links"]}
    LEGS, CTL = netcfg["grid_node_legs"], set(netcfg["signals"])
    URB = json.loads(a.territory.read_text(encoding="utf-8"))["territory"]["urban"]

    # 링크 -> 그 링크를 가진 (node, leg)
    own = collections.defaultdict(list)
    for sc, legs in URB.items():
        for k, lks in legs.items():
            for lk in lks:
                own[lk].append((sc, k))

    extra = read_extra_legs(a.extra_legs)
    hdr, rows = read_gate_map(a.base)

    # leg 구역 — 경계면 leg 를 우선한다 (권역 정본과 같은 규칙)
    def leg_zone(sc, k):
        if sc not in CTL:
            return "외부"
        nb = k.split("_", 1)[1] if "_" in k else None
        inner_dirs = {kk.split("_")[0] for kk in LEGS.get(sc, {})
                      if "_" in kk and kk.split("_", 1)[1] in CTL}
        if nb in CTL:
            return "내부"
        if nb is None and k.split("_")[0] in inner_dirs:
            return "내부"
        return "경계면"

    def rehost(link, old_gate):
        """진입 링크를 소유한 경계 leg 로 게이트를 옮긴다.

        1순위는 **권역 정본**이다 (재유도 금지 원칙). 그중 통제 SC 의 경계면 leg 를
        먼저 쓴다 — 리더가 실제로 조일 수 있는 자리이기 때문이다.
        권역만으로 못 가리면 boundary_extra_legs 의 분담이 큰 쪽으로 간다.
        """
        cands = sorted(extra.get(str(link), []), key=lambda r: (-r["veh"], -r["inflow"]))
        share = [f"{x['node']}·{x['leg']}({x['veh']:.0f}veh/{x['inflow']:.0f}vph)" for x in cands]

        owners = own.get(str(link), [])
        ranked = []
        for sc, k in owners:
            g = f"in_{sc}_{k.split('_')[0]}"
            if g not in KEYS:
                continue
            z = leg_zone(sc, k)
            ranked.append((0 if (z == "경계면" and sc in CTL) else (1 if sc in CTL else 2), g, z))
        # 동률이면 알파벳순으로 갈리지 않게 extra_legs 분담을 2차 키로 쓴다
        pref = {f"in_{c['node']}_{c['leg']}": i for i, c in enumerate(cands)}
        ranked.sort(key=lambda r: (r[0], pref.get(r[1], 99), r[1]))
        if ranked:
            best = ranked[0]
            alts = sorted({r[1] for r in ranked} - {best[1]})
            return best[1], f"territory_v1({best[2]})", (share if len(cands) > 1 else []), alts

        for c in cands:
            g = f"in_{c['node']}_{c['leg']}"
            if g in KEYS:
                return g, "boundary_extra_legs_legs4b", (share if len(cands) > 1 else []), []

        parts = old_gate.rsplit("_", 1)
        if len(parts) == 2 and parts[1] in FOLD:
            g = f"{parts[0]}_{FOLD[parts[1]]}"
            if g in KEYS:
                return g, "fold_8dir", [], []
        return None, "", [], []

    changed, unknown_left, splits, stems = [], [], [], []
    for r in rows:
        if r["status"] != "mapped":
            continue
        if r["gate"] in KEYS:
            continue
        # 분기 전 공용 줄기(어느 leg 도 소유하지 않는 진입 링크)는 게이트가 없다.
        # 억지로 한 게이트에 몰면 그 게이트 도착량이 통째로 부풀려진다 — link 69 는
        # 1400 veh/h 중 966(69%)이 램프미터를 타고 freeway 로 빠지고 도시부로 가는 건
        # 434 뿐이다. 회계는 unmapped 버킷으로 닫고(게이트합+미배정+내부발생==도시부 총량)
        # state 의 urban_unmapped_volume_vph 로 보이게 둔다.
        if not own.get(str(r["link"])):
            r["status"] = "shared_stem_unmapped"
            r["leg_source"] = "no_single_owner"
            stems.append((r["no"], r["gate"], r["link"], r["name"]))
            continue
        g, how, share, alts = rehost(r["link"], r["gate"])
        if g is None:
            unknown_left.append(r)
            continue
        changed.append((r["no"], r["gate"], g, how, r["link"], r["name"]))
        if share or alts:
            splits.append((r["no"], r["gate"], g, r["link"], share, alts))
        node, leg = g[3:].rsplit("_", 1)
        r["gate"], r["model_node"], r["leg"] = g, node, leg
        r["leg_source"] = how

    mapped = [r for r in rows if r["status"] == "mapped"]
    bad = sorted({r["gate"] for r in mapped if r["gate"] not in KEYS})

    print(f"기준 대장 {a.base.name}  행 {len(rows)}  mapped {len(mapped)}")
    print(f"재배치 {len(changed)}건")
    for no, old, new, how, link, name in changed:
        print(f"   no {no:5s} {old:16s} -> {new:14s}  link {link:12s} [{how}] {name}")
    if splits:
        print("\n분담이 갈리는 진입 링크 — 큰 쪽에 귀속했다 (대장 형식이 유입당 게이트 하나다)")
        for no, old, new, link, share, alts in splits:
            print(f"   no {no:5s} link {link:12s} {old} -> {new}")
            if alts:  print(f"          권역이 아는 다른 게이트: {', '.join(alts)}")
            if share: print(f"          extra_legs 분담: {' · '.join(share)}")
    print(f"\nconfig 가 모르는 게이트: {len(bad)} {bad if bad else '(없음 — 어댑터 통과)'}")
    if unknown_left:
        print("재배치 실패:", [(r["no"], r["gate"]) for r in unknown_left])
    if bad or unknown_left:
        print("\n미지 게이트가 남아 있다. 쓰지 마라.")
        return 1
    if a.dry_run:
        return 0

    lines = [
        "# generated by scripts/build_urban_input_gate_map_legs4b.py",
        f"# base={a.base.name}",
        f"# config={a.config.name}",
        f"# territory={a.territory.name}",
        f"# extra_legs={a.extra_legs.name}",
        "# 게이트 = 진입 링크를 소유한 경계면 leg. 소유가 둘 이상이면 boundary_extra_legs 분담이 큰 쪽.",
        "# 8방위 잔재(SE/SW)와 mid-block 강등 노드(SC13·SC9001)를 legs4b 로 옮겼다.",
        f"# expected_mapped={len(mapped)}",
        ",".join(hdr),
    ]
    for r in rows:
        lines.append(",".join(str(r.get(h, "")) for h in hdr))
    a.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n-> {a.out}  (mapped {len(mapped)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
