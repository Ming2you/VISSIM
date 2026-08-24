# -*- coding: utf-8 -*-
"""VISSIM 노드평가(.knr)에서 접근로별 **실측 회전분율(beta)** 을 유도한다.

문제. 모델의 `urban_movements[*].beta` 는 전부 **균등 분배 기본값**이다. 474개 값이
0.5 / 0.25 / 0.167 / 0.125 / 0.1 — 전부 1/2, 1/4, 1/6, 1/8, 1/10 이고, 패턴도
"(movement 3개, 직진 0.5)" 처럼 규칙적이다. 실측 산출물은 저장소에 없다.

증상 (SC5 동쪽 접근로, 정지선 1220018401, 무제어 1,694대):

    movement                  모델 beta   실측
    to_W_SC101 (직진)           0.500    0.764
    to_N_SC102 (우)             0.167    0.125
    to_S_SC11 + to_S (좌 2개)   0.334    0.111

좌회전 수요를 **3배로 부풀린다**. 그 결과 현시별 "큐/용량" 이
p4(좌) 102.3초 > p3(직진) 76.8초 로 역전되어, `local` 이 좌회전을 더 급하다고 본다.
가격이 p3 를 1위(+0.043)로 가리켜도 정련이 `local` 벌점 때문에 못 옮긴다 — 실측
conv 런에서 정련은 SC5 를 48초씩 활발히 움직이면서 **p3 만 건너뛴다**.
SC5 동쪽 실측 정지차가 231대까지 쌓이는 원인이고, SC5 는 남은 초과의 대부분이다.

유도. `.knr` 의 `FromLink`/`ToLink` 는 실제 통과 경로다. 정지선 링크별로 ToLink 분포를
세고, 그 링크가 속한 접근로의 movement 에 `destination` 으로 대응시켜 분율을 만든다.

대응 규칙 — **이름이 뒤집혀 있다.** movement 의 `exit` 는 자기 기준 방위이고(SC5 에서
서쪽으로 나가면 `W_SC101`), ToLink 가 속한 권역은 하류 신호 기준이다(그 링크는
`('SC101', 'E_SC5')`). leg 이름을 직접 비교하면 전부 어긋난다 — 실측: 접근로 61개 중
53개가 매칭 0 이었다.

올바른 대응은 **이웃 신호 이름**이다. movement 의 `destination` 에서 뽑는다:

    destination = "SC5_to_SC101"  ->  SC101   (하류 신호)
    destination = "out_SC5_S"     ->  OUT     (경계 유출)

ToLink 쪽도 그 링크가 속한 **신호 이름**으로 접는다. 권역 밖이거나 자기 신호 권역이면
망 밖으로 나간 것으로 보고 OUT 에 넣는다.
"""
from __future__ import annotations
import argparse, collections, glob, io, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTROLLED = (1, 5, 6, 7, 11, 12, 16, 101, 105, 107, 108, 109, 1001, 1002, 1003, 1004, 1005)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="nocontrol_native_20260821")
    ap.add_argument("--territory", default="outputs/urban_player_territory_v1_20260819.json")
    ap.add_argument("--movements-config",
                    default="evaluation/configs/real_world_modi_pstack_distributed_core17legs4b_20260819.json")
    ap.add_argument("--network", default="network/real_world_gaepo_modi/modi_eval_userfix_20260814e.inpx")
    ap.add_argument("--min-veh", type=int, default=30, help="이보다 적게 통과한 접근로는 안 건드린다")
    ap.add_argument("--out", default="outputs/movement_beta_measured_20260824.json")
    args = ap.parse_args()

    terr = json.loads((ROOT / args.territory).read_text(encoding="utf-8"))["territory"]["urban"]
    ctrl = {f"SC{n}" for n in CONTROLLED}
    owner: dict[str, tuple[str, str]] = {}
    for sig, legs in terr.items():
        for leg, ids in legs.items():
            for i in ids:
                owner.setdefault(str(i), (sig, leg))

    cfg = json.loads((ROOT / args.movements_config).read_text(encoding="utf-8"))
    um = cfg["config_overrides"]["network"]["urban_movements"]
    # 접근로 -> movement 들, movement -> exit leg
    by_app: dict[tuple[str, str], list[str]] = collections.defaultdict(list)
    exit_key: dict[str, str] = {}     # movement -> 목적 식별자(이웃 신호명 또는 "OUT")
    for key, spec in um.items():
        sig, app = str(spec.get("signal", "")), str(spec.get("approach", ""))
        if not (sig and app):
            continue
        by_app[(sig, app)].append(key)
        dest = str(spec.get("destination", ""))
        exit_key[key] = dest.split("_to_", 1)[1] if "_to_" in dest else "OUT"

    # 정지선 링크(자기 SC 의 SG 1-8 헤드)
    raw = (ROOT / args.network).read_text(encoding="utf-8", errors="replace")
    heads = collections.defaultdict(set)
    for m in re.finditer(r"<signalHead\b[^>]*>", raw):
        t = m.group(0)
        ln = re.search(r'lane="(\d+)\s+(\d+)"', t)
        sg = re.search(r'sg="(\d+)\s+(\d+)"', t)
        if ln and sg:
            heads[ln.group(1)].add((int(sg.group(1)), int(sg.group(2))))
    stop: dict[str, tuple[str, str]] = {}
    for link, sgs in heads.items():
        o = owner.get(link)
        if o and o[0] in ctrl and any(f"SC{sc}" == o[0] and g <= 8 for sc, g in sgs):
            stop[link] = o

    knr = glob.glob(str(ROOT / "evaluation/runs" / args.run / "vissim_eval" / "*.knr"))
    if not knr:
        print(f"knr 없음: {args.run}")
        return 1
    flow: dict[tuple[str, str], collections.Counter] = collections.defaultdict(collections.Counter)
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
            if o:
                flow[o][p[10]] += 1   # (신호, 접근로) -> ToLink 별 통과

    out: dict[str, float] = {}
    report, stats = [], collections.Counter()
    for (sig, app), tos in sorted(flow.items()):
        total = sum(tos.values())
        movs = by_app.get((sig, app)) or []
        if total < args.min_veh or not movs:
            stats["표본 부족/movement 없음"] += 1
            continue
        # ToLink -> exit leg 로 접어 movement 에 배분
        by_exit: collections.Counter = collections.Counter()
        unmatched = 0
        for to, c in tos.items():
            t = owner.get(str(to))
            if not t or t[0] == sig:
                by_exit["OUT"] += c       # 권역 밖 또는 자기 권역 = 망 밖으로
                if not t:
                    unmatched += c
                continue
            by_exit[t[0]] += c            # **하류 신호 이름**으로 접는다
        matched = sum(by_exit.values())
        if matched < args.min_veh:
            stats["목적 leg 매칭 부족"] += 1
            continue
        share: dict[str, float] = {}
        for mv in movs:
            share[mv] = float(by_exit.get(exit_key.get(mv, ""), 0))
        s = sum(share.values())
        if s <= 0:
            stats["exit 매칭 0"] += 1
            continue
        for mv in movs:
            out[mv] = round(share[mv] / s, 4)
        stats["적용"] += 1
        report.append({
            "signal": sig, "approach": app, "veh": total,
            "unmatched": unmatched,
            "beta": {mv: out[mv] for mv in movs},
            "beta_prev": {mv: round(float(um[mv].get("beta", 0.0)), 4) for mv in movs},
        })

    dst = ROOT / args.out
    dst.write_text(json.dumps({
        "schema": "movement_beta_measured/core17legs4b",
        "generated": "2026-08-24",
        "source_run": args.run,
        "min_veh": args.min_veh,
        "definition": "정지선 링크의 ToLink 분포를 권역 정본으로 목적 leg 에 접고, 그 leg 로 가는 movement 에 배분",
        "beta": out,
        "approaches": report,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"접근로 {stats['적용']}개 · movement {len(out)}개 · 제외 {dict((k,v) for k,v in stats.items() if k!='적용')}")
    diffs = []
    for r in report:
        for mv, b in r["beta"].items():
            diffs.append(abs(b - r["beta_prev"][mv]))
    if diffs:
        diffs.sort()
        print(f"기존 beta 와의 차이: 중앙 {diffs[len(diffs)//2]:.3f} · 90% {diffs[int(0.9*len(diffs))]:.3f} · 최대 {diffs[-1]:.3f}")
    for r in report:
        if r["signal"] == "SC5" and r["approach"] == "E_SC6":
            print(f"\nSC5 E_SC6 ({r['veh']}대, 미매칭 {r['unmatched']}):")
            for mv in r["beta"]:
                print(f"   {mv[:36]:>36s}  {r['beta_prev'][mv]:.3f} -> {r['beta'][mv]:.3f}")
    print(f"저장: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
