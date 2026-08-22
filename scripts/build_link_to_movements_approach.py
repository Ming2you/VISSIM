# -*- coding: utf-8 -*-
"""검지 매핑의 `link_to_movements` 를 **권역 정본의 접근로 기준**으로 다시 유도한다.

왜. 기존 생성기(`generate_real_world_distributed_players.py:911-926`)는 링크의 축을
보고 movement 를 고르는데, 필터가 `_p1`·`_p2` 만 검사한다. 2026-08-12 4현시 전환
(`grid_topology.movement_phase_id`: p1=주축직진 p2=주축좌 p3=부축직진 p4=부축좌) 이후
이 필터의 의미가 조용히 바뀌었다:

    NS 링크 -> `_p1`  = 남북 **직진만**   (남북 좌회전 p2 를 잃는다)
    EW 링크 -> `_p2`  = **남북 좌회전**   (축도 회전도 틀렸다)

결과로 동서 접근로 링크의 차량이 남북 좌회전 movement 로 귀속되고, p3·p4 는 17개 신호
전부에서 영구히 큐 0 이 된다. 리더는 빈 현시를 굶기는 비용이 0 이므로 p3·p4 를
green_min 으로 밀고 남북에 몰아준다 (실측: 동서축이 정지차의 45~55% 를 진다).

규칙. 정지선 링크는 **자기 접근로의 movement 에만** 귀속한다.

    링크 L 이 신호 S 의 leg X 정지선이면 -> {m : m.signal == S and m.approach == X}

권역은 정본(`urban_player_territory_v1_20260819.json`)을 읽는다. 자동 규칙 재유도 금지.
`approach` 필드는 권역 leg 이름과 123개 중 119개가 그대로 일치한다.

범위. 통제 대상 SC 의 권역이고 그 SC 의 SG 1-8(주교차로) 신호헤드를 단 링크만. 실측상
동서 접근로 50개 전부 SG 1-8 이 구동하므로 미드블록(SG 9+) 규칙과 충돌하지 않는다.
대상 65개 링크는 전부 이미 observable_links 와 link_to_movements 에 있다 —
관측 범위는 그대로고 **귀속만** 바뀐다. 범위 밖 항목(off_ramp 커넥터 등)은 그대로 둔다.
"""
from __future__ import annotations
import argparse, collections, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = (1, 5, 6, 7, 11, 12, 16, 101, 105, 107, 108, 109, 1001, 1002, 1003, 1004, 1005)
# NEMA 이름 -> 현시. 진행방향 기준이라 접근로는 반대다(SBT = 남행 직진 = **북**쪽 접근로).
NEMA_PHASE = {"NBT": "p1", "SBT": "p1", "NBL": "p2", "SBL": "p2",
              "EBT": "p3", "WBT": "p3", "EBL": "p4", "WBL": "p4"}


def signal_group_names(network_path: Path) -> dict[int, dict[int, str]]:
    """{SC 번호: {SG 번호: 이름}}. 이 망의 SG 이름은 완전한 NEMA(EBT/NBL/...)다."""
    import xml.etree.ElementTree as ET
    root = ET.parse(network_path).getroot()
    out: dict[int, dict[int, str]] = {}
    for sc in root.iter("signalController"):
        try:
            sc_no = int(str(sc.get("no")))
        except (TypeError, ValueError):
            continue
        names: dict[int, str] = {}
        for sg in sc.findall("./sgs/signalGroup"):
            try:
                names[int(str(sg.get("no")))] = str(sg.get("name", "")).strip().upper()
            except (TypeError, ValueError):
                continue
        out[sc_no] = names
    return out


def signal_heads(network_path: Path) -> dict[str, set[tuple[int, int]]]:
    raw = network_path.read_text(encoding="utf-8", errors="replace")
    out: dict[str, set[tuple[int, int]]] = collections.defaultdict(set)
    for m in re.finditer(r"<signalHead\b[^>]*>", raw):
        tag = m.group(0)
        lane = re.search(r'lane="(\d+)\s+(\d+)"', tag)
        sg = re.search(r'sg="(\d+)\s+(\d+)"', tag)
        if lane and sg:
            out[lane.group(1)].add((int(sg.group(1)), int(sg.group(2))))
    return dict(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--network", default="network/real_world_gaepo_modi/modi_eval_userfix_20260814e.inpx")
    ap.add_argument("--territory", default="outputs/urban_player_territory_v1_20260819.json")
    ap.add_argument("--movements-config", default="evaluation/configs/real_world_modi_pstack_distributed_core17legs4b_20260819.json")
    ap.add_argument("--source", required=True, help="고칠 검지 매핑(원본은 안 건드린다)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-sg", type=int, default=8, help="주교차로 SG 상한(9+ 는 미드블록)")
    args = ap.parse_args()

    terr = json.loads((ROOT / args.territory).read_text(encoding="utf-8"))["territory"]["urban"]
    owner: dict[str, tuple[str, str]] = {}
    for sig, legs in terr.items():
        for leg, ids in legs.items():
            for i in ids:
                owner.setdefault(str(i), (sig, leg))

    cfg = json.loads((ROOT / args.movements_config).read_text(encoding="utf-8"))
    um = cfg["config_overrides"]["network"]["urban_movements"]
    by_approach: dict[tuple[str, str], list[str]] = collections.defaultdict(list)
    by_phase: dict[tuple[str, str], list[str]] = collections.defaultdict(list)
    for key, spec in um.items():
        sig = str(spec.get("signal", ""))
        by_approach[(sig, str(spec.get("approach", "")))].append(key)
        by_phase[(sig, str(spec.get("phase", "")).rpartition("_")[2])].append(key)

    heads = signal_heads(ROOT / args.network)
    sg_names = signal_group_names(ROOT / args.network)
    ctrl = {f"SC{n}" for n in CONTROLLED}
    doc = json.loads((ROOT / args.source).read_text(encoding="utf-8"))
    l2m = dict(doc.get("link_to_movements") or {})

    stats = collections.Counter()
    bearing = collections.Counter()
    for link, sgs in sorted(heads.items()):
        own = owner.get(link)
        if not own or own[0] not in ctrl:
            stats["범위밖_권역"] += 1
            continue
        sig, leg = own
        mine = {g for sc, g in sgs if f"SC{sc}" == sig and g <= args.max_sg}
        if not mine:
            stats["범위밖_SG"] += 1
            continue
        movements = sorted(by_approach.get((sig, leg), ()))
        source = "territory_approach_stopline"
        if not movements:
            # 권역 leg 가 approach 목록에 없을 때만. 신호헤드 SG 의 NEMA 이름 -> 현시로 폴백.
            sc_no = int(sig[2:])
            phases = {NEMA_PHASE[n] for g in mine
                      for n in [sg_names.get(sc_no, {}).get(g, "")] if n in NEMA_PHASE}
            movements = sorted({k for p in phases for k in by_phase.get((sig, p), ())})
            source = "nema_phase_fallback"
            if movements:
                stats["현시폴백"] += 1
        if not movements:
            stats["movement_없음"] += 1
            continue
        l2m[link] = [{"movement": k, "weight": 1.0, "source": source, "approach": leg}
                     for k in movements]
        stats["재귀속"] += 1
        bearing[leg.split("_")[0]] += 1

    doc["link_to_movements"] = {k: l2m[k] for k in sorted(l2m, key=lambda x: (len(x), x))}
    doc["link_to_movements_source"] = {
        "rule": "정지선 링크 -> 같은 신호·같은 접근로(leg) movement",
        "territory": args.territory,
        "movements_config": args.movements_config,
        "network": args.network,
        "max_sg": args.max_sg,
        "replaces": "signal_head_phase_axis (generate_real_world_distributed_players.py:911, _p1/_p2 만 검사)",
        "generator": "scripts/build_link_to_movements_approach.py",
    }
    (ROOT / args.out).write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"재귀속 {stats['재귀속']}개 링크 · 방위 {dict(bearing)}")
    print(f"제외: {({k: v for k, v in stats.items() if k != '재귀속'})}")
    print(f"link_to_movements 총 {len(doc['link_to_movements'])}개 -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
