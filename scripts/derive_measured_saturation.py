# -*- coding: utf-8 -*-
"""VISSIM 노드평가(.knr)에서 정지선 **차로군별 포화유량**을 유도한다.

왜. 모델은 두 군데서 서로 다른, 둘 다 틀린 용량을 쓴다.
  `phase_shape_local_cost` : movement 당 전역 1400 (직진 과소·소수회전 과대, 게다가
                             sat = len(movements) x 1400 이라 신호 합이 4배 과대)
  플랜트/GNE               : 차로수 x 330 (실측 직진 1,600~4,500 대비 3~5배 과소)
리더가 녹색을 나눌 때 쓰는 건 movement 간 **상대** 용량이라 이 왜곡이 그대로 배분이 된다.

추정. 무제어 런(고정계획이라 녹색이 알려져 있다)의 주기별 통과대수를 그 차로군을
서비스하는 SG 녹색초로 나눈다. 주기의 **상위 3개 평균**을 쓴다 — 대부분의 주기는
수요제약이라 평균·중앙값을 쓰면 용량이 아니라 수요를 재게 된다(실측: 중앙값 기준
차로환산 0.52, 상위3 기준 0.86).

기하 하한. 그래도 90개 중 54개가 1차로 미만으로 나온다 — 관측 구간 내내 수요가
차로 하나를 못 채운 곳이다. 그런 곳에 실측을 그대로 심으면 용량이 바닥으로 박혀
수요가 옮겨왔을 때 대응을 못 한다. 그래서 **max(실측, 차로수 x 1800)** 을 쓴다.
차로수는 그 정지선 링크에 달린 해당 SG 신호헤드의 서로 다른 lane index 수다
(VISSIM 자신의 정의라 커넥터 기하 역산보다 직접적이다).
"""
from __future__ import annotations
import argparse, collections, glob, io, json, re, statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPASS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
IDX = {c: i for i, c in enumerate(COMPASS)}
NEMA_DIR = {"N": "SB", "S": "NB", "E": "WB", "W": "EB"}
CONTROLLED = (1, 5, 6, 7, 11, 12, 16, 101, 105, 107, 108, 109, 1001, 1002, 1003, 1004, 1005)
PER_LANE_VEH_H = 1800.0


def turn_kind(mv: str):
    try:
        a, b = mv.split("-")
        d = (IDX[b] - IDX[a]) % 8
    except (ValueError, KeyError):
        return None
    return "T" if d == 4 else ("L" if d in (5, 6, 7) else ("R" if d in (1, 2, 3) else None))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="nocontrol_native_20260821")
    ap.add_argument("--network", default="network/real_world_gaepo_modi/modi_eval_userfix_20260814e.inpx")
    ap.add_argument("--territory", default="outputs/urban_player_territory_v1_20260819.json")
    ap.add_argument("--timing", default="outputs/signal_group_timing_core17legs4b_20260819.json")
    ap.add_argument("--cycle", type=float, default=150.0)
    ap.add_argument("--top", type=int, default=3)
    ap.add_argument("--out", default="outputs/movement_saturation_measured_20260822.json")
    args = ap.parse_args()

    terr = json.loads((ROOT / args.territory).read_text(encoding="utf-8"))["territory"]["urban"]
    owner = {}
    for sig, legs in terr.items():
        for leg, ids in legs.items():
            for i in ids:
                owner.setdefault(str(i), (sig, leg.split("_")[0]))

    raw = (ROOT / args.network).read_text(encoding="utf-8", errors="replace")
    ctrl = {f"SC{n}" for n in CONTROLLED}
    heads = collections.defaultdict(set)
    head_rows = []
    for m in re.finditer(r"<signalHead\b[^>]*>", raw):
        tag = m.group(0)
        ln = re.search(r'lane="(\d+)\s+(\d+)"', tag)
        sg = re.search(r'sg="(\d+)\s+(\d+)"', tag)
        if ln and sg:
            heads[ln.group(1)].add((int(sg.group(1)), int(sg.group(2))))
            head_rows.append((ln.group(1), int(ln.group(2)), int(sg.group(1)), int(sg.group(2))))
    stop = {}
    for link, sgs in heads.items():
        o = owner.get(link)
        if o and o[0] in ctrl and any(f"SC{sc}" == o[0] and g <= 8 for sc, g in sgs):
            stop[link] = o

    timing = json.loads((ROOT / args.timing).read_text(encoding="utf-8"))
    green, sg_name = {}, {}
    for c in timing["controllers"]:
        sid = f"SC{c['sc_no']}"
        g = collections.defaultdict(float)
        for grp in c["groups"]:
            nm = str(grp.get("name", "")).upper()
            g[nm] = max(g[nm], float(grp.get("green_sec", 0.0)))
            raw_sg = str(grp.get("sg_id", ""))
            if raw_sg.isdigit():
                sg_name[(sid, int(raw_sg))] = nm
        green[sid] = dict(g)

    # 차로 수: 정지선 링크 x SG이름 -> 서로 다른 lane index
    lanes = collections.defaultdict(set)
    for link, lane_idx, sc_no, sg_no in head_rows:
        o = stop.get(link)
        if not o or f"SC{sc_no}" != o[0] or sg_no > 8:
            continue
        nm = sg_name.get((o[0], sg_no))
        if nm:
            lanes[(link, nm)].add(lane_idx)

    knr = glob.glob(str(ROOT / "evaluation/runs" / args.run / "vissim_eval" / "*.knr"))
    if not knr:
        print(f"knr 없음: {args.run}")
        return 1
    counts = collections.defaultdict(collections.Counter)
    hdr = False
    with io.open(knr[0], encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not hdr:
                if line.startswith("VehNo;"):
                    hdr = True
                continue
            p = [x.strip() for x in line.split(";")]
            if len(p) < 13:
                continue
            o = stop.get(p[9])
            if not o:
                continue
            k = turn_kind(p[8])
            if k is None:
                continue
            try:
                t = float(p[3])
            except ValueError:
                continue
            nm = NEMA_DIR[o[1]] + ("L" if k == "L" else "T")
            counts[(o[0], o[1], nm, p[9])][int(t // args.cycle)] += 1

    rows, stats = [], collections.Counter()
    for (sig, bear, nm, link), cyc in sorted(counts.items()):
        gsec = green.get(sig, {}).get(nm, 0.0)
        if gsec <= 0.0 or len(cyc) < 5:
            stats["제외"] += 1
            continue
        r = sorted((n / gsec * 3600.0 for n in cyc.values()), reverse=True)
        obs = statistics.mean(r[: max(1, args.top)])
        n_lane = max(1, len(lanes.get((link, nm), {1})))
        geo = n_lane * PER_LANE_VEH_H
        sat = max(obs, geo)
        stats["실측 채택" if obs >= geo else "기하 채택"] += 1
        rows.append({
            "signal": sig, "bearing": bear, "sg_name": nm, "stopline_link": link,
            "green_sec": gsec, "cycles": len(r), "total_veh": sum(cyc.values()),
            "lanes_from_heads": n_lane,
            "observed_top_veh_h": round(obs, 1),
            "geometric_veh_h": round(geo, 1),
            "saturation_veh_h": round(sat, 1),
        })
    out = ROOT / args.out
    out.write_text(json.dumps({
        "schema": "movement_saturation_measured/core17legs4b",
        "generated": "2026-08-22",
        "source_run": args.run,
        "per_lane_veh_h": PER_LANE_VEH_H,
        "top_cycles": args.top,
        "definition": "차로군(정지선링크 x SG이름) 포화유량 = max(주기별 통과/녹색초 상위N 평균, 신호헤드 차로수 x 1800)",
        "lane_groups": rows,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    sats = sorted(x["saturation_veh_h"] for x in rows)
    print(f"차로군 {len(rows)}개 · {dict(stats)}")
    print(f"포화유량: 중앙 {statistics.median(sats):,.0f} · 25% {sats[len(sats)//4]:,.0f} · 75% {sats[3*len(sats)//4]:,.0f} veh/h")
    ln = collections.Counter(x["lanes_from_heads"] for x in rows)
    print(f"신호헤드 차로수 분포: {dict(sorted(ln.items()))}")
    print(f"저장: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
