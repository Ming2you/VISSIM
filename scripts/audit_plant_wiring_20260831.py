# -*- coding: utf-8 -*-
"""플랜트 배선이 실제 VISSIM 망과 맞는지 전수 검사한다. 그림용 자료도 같이 낸다.

왜 (2026-08-31).

플랜트 기반 numerical sim 을 배선하기 전에 플랜트가 실제 VISSIM 망과 맞는지 확인한다.
검증 못 한 플랜트를 더 빠른 루프에 배선하면 틀린 답을 더 빨리 얻는다.

무엇을 검사하나 (전부 .inpx 원본 대조).

    A 커넥터 실재       선언한 (from_link, connector, to_link) 가 .inpx 에 그대로 있는가
    B 방향 정합         커넥터 기하로 계산한 방위가 선언 heading 과 맞는가
                        — "서쪽 직진 링크가 남향 링크에 붙어 있다" 류를 잡는 검사
    C 권역 대 신호두     권역이 어떤 SC 에 준 링크의 신호두가 실제로 그 SC 인가
    D 본선 체인 연속성   FW_E/FW_W 체인 링크가 실제로 이어지는가 · 오프셋이 길이와 맞는가
    E 램프 합류 위치     램프 커넥터가 붙는 체인 좌표가 선언 세그먼트와 맞는가

정본은 재유도하지 않는다(CLAUDE.md) — 읽어서 대조만 한다.

산출: outputs/plant_wiring_audit_20260831.json  (그림 렌더링 입력)
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent

# 본선 체인 (러너 VBS 상수와 같아야 한다)
CHAIN = {
    "FW_E": (["74", "10699", "2", "10702", "24"],
             [0.0, 2701.577, 2734.527232, 7426.126232, 7427.127732], 10773.109163),
    "FW_W": (["26"], [0.0], 10777.693079),
}
RAMP_CONNECTORS = {
    "R_D_W": ["10480", "10482"], "R_F_W": ["10646", "10644"],
    "R_D_E": ["10490", "10484"], "R_F_E": ["10639", "10681"],
}
# 커넥터별 실측 유량 [veh/h] — .fzp 고유차량 직접계수.
# 생성기의 대표 세그먼트 가중치와 같은 값이다.
MEASURED_VPH = {"10480": 233.0, "10482": 521.0, "10646": 431.0, "10644": 781.0,
                "10639": 157.0, "10681": 402.0, "10490": 453.0, "10484": 486.0}
# 생성기(generate_real_world_control_mapping.py)가 실측 유량 가중으로 내는 값.
RAMP_MERGE_DECLARED = {"R_D_W": 2, "R_F_W": 5, "R_D_E": 5, "R_F_E": 3}
SEGMENTS = 8


def parse_network(path):
    """링크 기하 · 커넥터 연결 · 신호두 SC 를 뽑는다."""
    text = path.read_text(encoding="utf-8", errors="replace")
    links, conns = {}, {}
    for m in re.finditer(r"<link\b([^>]*)>(.*?)</link>", text, re.S):
        attrs, body = m.group(1), m.group(2)
        no = re.search(r'\bno="(\d+)"', attrs)
        if not no:
            continue
        no = no.group(1)
        pts = [(float(p.group(1)), float(p.group(2)))
               for p in re.finditer(r'<linkPolyPoint x="([-\d.eE+]+)" y="([-\d.eE+]+)"', body)]
        length = sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)) if len(pts) > 1 else 0.0
        fr = re.search(r'<fromLinkEndPt[^>]*\blane="(\d+)\s+\d+"[^>]*\bpos="([\d.eE+-]+)"', body)
        to = re.search(r'<toLinkEndPt[^>]*\blane="(\d+)\s+\d+"[^>]*\bpos="([\d.eE+-]+)"', body)
        rec = {"no": no, "points": pts, "length_m": length,
               "name": (re.search(r'\bname="([^"]*)"', attrs) or [None, ""])[1] if re.search(r'\bname="([^"]*)"', attrs) else "",
               "lanes": len(re.findall(r"<lane\b", body))}
        if fr and to:
            rec["from_link"], rec["from_pos"] = fr.group(1), float(fr.group(2))
            rec["to_link"], rec["to_pos"] = to.group(1), float(to.group(2))
            conns[no] = rec
        links[no] = rec

    heads = {}
    for m in re.finditer(r"<signalHead\b([^>]*)>", text):
        a = m.group(1)
        lane = re.search(r'\blane="(\d+)\s+\d+"', a)
        sg = re.search(r'\bsg="(\d+)\s+(\d+)"', a)
        if lane and sg:
            heads.setdefault(lane.group(1), set()).add(sg.group(1))
    return links, conns, heads


def bearing(pts):
    """폴리라인 진행 방위(도, 북=0 시계방향). 점이 부족하면 None."""
    if len(pts) < 2:
        return None
    dx = pts[-1][0] - pts[0][0]
    dy = pts[-1][1] - pts[0][1]
    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        return None
    return (math.degrees(math.atan2(dx, dy)) + 360.0) % 360.0


def compass(deg):
    if deg is None:
        return "?"
    return ["N", "NE", "E", "SE", "S", "SW", "W", "NW"][int(((deg + 22.5) % 360) // 45)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--network", default="network/real_world_gaepo_modi/modi_eval_userfix_20260814e.inpx")
    ap.add_argument("--out", default="outputs/plant_wiring_audit_20260831.json")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    links, conns, heads = parse_network(R / args.network)
    print("망: 링크 %d · 커넥터 %d · 신호두를 가진 링크 %d" % (len(links), len(conns), len(heads)))

    terr = json.loads((R / "outputs/urban_player_territory_v1_20260819.json").read_text(encoding="utf-8"))
    turns = json.loads((R / "outputs/pn_boundary_turns_v1_20260819.json").read_text(encoding="utf-8"))
    # 통제 SC 17개 (config signals). 권역의 26 player 중 나머지는 monitor/mid-block 이다.
    _cfgp = R / "evaluation/configs/canon_fdfit3_20260828.json"
    _sig = json.loads(_cfgp.read_text(encoding="utf-8"))["config_overrides"]["network"]["signals"]
    CONTROLLED = [str(x) for x in _sig]
    CONTROLLED_NUMS = {x[2:] if x.upper().startswith("SC") else x for x in CONTROLLED}
    urban_t = terr["territory"]["urban"]
    fw_t = terr["territory"]["freeway"]
    rows = turns["turns"]

    audit = {"schema_version": "plant-wiring-audit/1", "generated": "2026-08-31",
             "network": args.network,
             "counts": {"links": len(links), "connectors": len(conns), "signal_head_links": len(heads)}}

    # ---- A 커넥터 실재 ----
    missing, mismatched = [], []
    for t in rows:
        c, f, to = str(t.get("connector")), str(t.get("from_link")), str(t.get("to_link"))
        rec = conns.get(c)
        if rec is None:
            missing.append({"connector": c, "from": f, "to": to})
        elif rec.get("from_link") != f or rec.get("to_link") != to:
            mismatched.append({"connector": c, "declared": [f, to],
                               "actual": [rec.get("from_link"), rec.get("to_link")]})
    audit["A_connector_existence"] = {"turns": len(rows), "missing": missing, "mismatched": mismatched}
    print()
    print("A 커넥터 실재    회전 %d개 · 없음 %d · 연결 불일치 %d"
          % (len(rows), len(missing), len(mismatched)))
    for x in (missing + mismatched)[:5]:
        print("     %s" % x)

    # ---- B 방향 정합 ----
    bad_dir, dirs = [], []
    for t in rows:
        c = str(t.get("connector"))
        rec = conns.get(c)
        decl = str(t.get("heading") or "").strip().upper()
        if rec is None or not decl:
            continue
        # heading 정의: **하류 링크의 첫 구간 방향** (derive_pn_boundary_turns.py:149).
        # 커넥터 자체의 현으로 재면 좌회전이 진입·진출의 평균이라 45도로 뭉개진다.
        dl = links.get(str(t.get("to_link")), {})
        b = bearing(dl.get("points") or [])
        got = compass(b)
        dirs.append({"connector": c, "declared": decl, "geometry": got,
                     "bearing_deg": round(b, 1) if b is not None else None,
                     "sc": t.get("sc"), "class": t.get("class")})
        if got == "?":
            continue
        # 선언은 4방위, 기하는 8방위 — 인접(45도)까지는 일치로 본다
        idx = {"N": 0, "NE": 1, "E": 2, "SE": 3, "S": 4, "SW": 5, "W": 6, "NW": 7}
        if decl in idx and got in idx:
            d = abs(idx[decl] - idx[got])
            d = min(d, 8 - d)
            if d > 1:
                bad_dir.append(dirs[-1] | {"octant_gap": d})
    audit["B_direction"] = {"checked": len(dirs), "mismatch": bad_dir, "samples": dirs[:40]}
    print()
    print("B 방향 정합      검사 %d개 · 45도 초과 어긋남 **%d개**" % (len(dirs), len(bad_dir)))
    for x in bad_dir[:8]:
        print("     %-8s %-8s 선언 %-3s 기하 %-3s (%.0f도) gap %d"
              % (x["sc"], x["connector"], x["declared"], x["geometry"], x["bearing_deg"], x["octant_gap"]))

    # ---- C 권역 대 신호두 ----
    conflicts, owned = [], 0
    for sc, legs in urban_t.items():
        for leg, lks in legs.items():
            for lk in lks:
                owned += 1
                sgs = heads.get(str(lk))
                if not sgs:
                    continue
                # 판정 규칙 셋 (권역 정본 derivation · config signals 기준).
                #  1) 신호두는 SC 번호를 접두사 없이 저장한다 — '108'.
                #  2) 권역은 정지선 접근로 + **상류로 앞 교차로까지**를 포함하므로 leg 이 지목한
                #     이웃 SC 의 신호두가 그 안에 있는 것이 정상이다 ('N_SC7' -> SC7 허용).
                #  3) 권역은 player 26개인데 통제는 17개다. 나머지(monitor·mid-block 강등)의
                #     신호두는 통제 권역 안에 있어도 정상이다.
                # 따라서 이상 = 소유도 이웃도 아닌 **통제 SC** 의 신호두.
                num = str(sc)[2:] if str(sc).upper().startswith("SC") else str(sc)
                mm = re.search(r"_SC(\d+)", str(leg))
                allowed = {num} | ({mm.group(1)} if mm else set())
                foreign = {g for g in sgs if g in CONTROLLED_NUMS} - allowed
                if foreign:
                    conflicts.append({"sc": sc, "leg": leg, "link": str(lk), "head_sc": sorted(sgs), "foreign_controlled": sorted(foreign), "expected": sorted(allowed)})
    audit["C_territory_vs_signalhead"] = {"owned_links": owned, "controlled": CONTROLLED, "conflicts": conflicts}
    print()
    print("C 권역 대 신호두  소유 링크 %d · 신호두 SC 불일치 **%d개**" % (owned, len(conflicts)))
    for x in conflicts[:8]:
        print("     %-8s %-16s link %-14s 신호두 %-12s 외래통제 %-8s 기대 %s"
              % (x["sc"], x["leg"], x["link"], str(x["head_sc"]), str(x["foreign_controlled"]), str(x["expected"])))

    # ---- D 본선 체인 연속성 ----
    chain_rep = {}
    for lk, (members, offsets, total) in CHAIN.items():
        seg_len = total / SEGMENTS
        rec = {"members": members, "declared_total_m": total, "segment_len_m": seg_len, "issues": []}
        acc = 0.0
        for i, mem in enumerate(members):
            L = links.get(mem, {}).get("length_m", 0.0)
            if abs(acc - offsets[i]) > 5.0:
                rec["issues"].append("멤버 %s 오프셋 선언 %.1f 대 누적 %.1f" % (mem, offsets[i], acc))
            acc += L
        if abs(acc - total) > 20.0:
            rec["issues"].append("체인 길이 선언 %.1f 대 기하 합 %.1f (차 %.1f)" % (total, acc, total - acc))
        rec["geometry_total_m"] = acc
        chain_rep[lk] = rec
    audit["D_freeway_chain"] = chain_rep
    print()
    print("D 본선 체인")
    for lk, r in chain_rep.items():
        print("     %-5s 멤버 %d · 선언 %.1f m · 기하 %.1f m · 세그 %.1f m · 문제 %d"
              % (lk, len(r["members"]), r["declared_total_m"], r["geometry_total_m"],
                 r["segment_len_m"], len(r["issues"])))
        for s in r["issues"][:3]:
            print("        %s" % s)

    # ---- E 램프 합류 위치 ----
    #
    # 판정 기준은 "커넥터마다 선언 셀과 같은가" 가 **아니다.**
    # `ramp_merge_segment_index` 는 램프당 정수 하나인데 커넥터가 둘이면 서로 다른 셀에
    # 붙을 수 있다(straddle). 그건 모델 표현력의 구조적 제약이지 배선 오류가 아니다.
    # 옳은 기준은 **선언이 실측 유량 다수결 셀과 같은가** 이고, 그것이 생성기 규칙이다.
    ramp_rep, straddle = [], []
    for ramp, cs in RAMP_CONNECTORS.items():
        mass, rows_r = {}, []
        for c in cs:
            rec = conns.get(c)
            if rec is None:
                rows_r.append({"connector": c, "error": "커넥터 없음"})
                continue
            to_link, pos = rec["to_link"], rec["to_pos"]
            link = "FW_W" if to_link in CHAIN["FW_W"][0] else ("FW_E" if to_link in CHAIN["FW_E"][0] else "?")
            if link == "?":
                rows_r.append({"connector": c, "to_link": to_link, "error": "본선 체인 밖"})
                continue
            members, offsets, total = CHAIN[link]
            chain_pos = offsets[members.index(to_link)] + pos
            seg = min(SEGMENTS - 1, int(chain_pos / (total / SEGMENTS)))
            q = MEASURED_VPH.get(c, 0.0)
            mass[seg] = mass.get(seg, 0.0) + q
            rows_r.append({"connector": c, "freeway": link, "to_link": to_link,
                           "chain_pos_m": round(chain_pos, 1), "segment": seg, "flow_vph": q})
        decl = RAMP_MERGE_DECLARED[ramp]
        major = min(sorted(mass), key=lambda i: (-mass[i], i)) if mass else None
        tot = sum(mass.values()) or 1.0
        ramp_rep.append({"ramp": ramp, "connectors": rows_r, "mass_by_segment": mass,
                         "flow_majority_segment": major, "declared_segment": decl,
                         "match": major == decl,
                         "straddles": len(mass) > 1,
                         "off_segment_flow_frac": round(1.0 - (mass.get(decl, 0.0) / tot), 3)})
        if len(mass) > 1:
            straddle.append(ramp)
    audit["E_ramp_merge"] = {"ramps": ramp_rep, "straddling": straddle,
                             "rule": "선언 == 실측 유량 다수결 셀"}
    print()
    print("E 램프 합류 위치   (판정 = 선언이 실측 유량 다수결 셀과 같은가)")
    print("     %-8s %-26s %8s %8s %9s %s" % ("램프", "셀별 유량[veh/h]", "다수결", "선언", "타셀몫", "판정"))
    for x in ramp_rep:
        print("     %-8s %-26s %8s %8d %8.0f%% %s"
              % (x["ramp"], str(x["mass_by_segment"]), x["flow_majority_segment"],
                 x["declared_segment"], 100 * x["off_segment_flow_frac"],
                 "OK" if x["match"] else "**어긋남**"))
    if straddle:
        print("     걸침(커넥터가 두 셀에 붙는 램프): %s — 모델은 램프당 정수 하나라" % ", ".join(straddle))
        print("     다수결 셀로 전량을 보낸다. 배선 오류가 아니라 표현력의 구조적 제약이다.")

    # ---- 그림용 요약 ----
    audit["players"] = {
        "urban": {sc: {"legs": {leg: len(lks) for leg, lks in legs.items()},
                       "links": sum(len(v) for v in legs.values())}
                  for sc, legs in urban_t.items()},
        "freeway": {k: len(v) for k, v in fw_t.items()},
    }
    audit["boundary_counts"] = turns.get("counts", {})
    audit["constant_load"] = turns.get("constant_load", {})
    (R / args.out).write_text(json.dumps(audit, ensure_ascii=False, indent=1), encoding="utf-8")
    print()
    print("-> %s" % args.out)
    bad = len(missing) + len(mismatched) + len(bad_dir) + len(conflicts) + \
        sum(len(r["issues"]) for r in chain_rep.values()) + sum(1 for x in ramp_rep if not x.get('match', True))
    print("총 이상 %d건" % bad)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
