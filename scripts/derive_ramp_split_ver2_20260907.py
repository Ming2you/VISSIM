# -*- coding: utf-8 -*-
"""모형 램프 4개 → 물리 램프 8개 분해 정본 산출 (2026-09-07).

왜 — `R_F_E` 하나가 289 m 떨어진 커넥터 둘(10639←70, 10681←68)을 묶은 객체다. 그래서 세그먼트를 아무리
잘게 나눠도 두 램프의 유입이 한 셀에 들어간다. 균등 21분할(L≈513 m)이면 각 셀에 on ≤1 · off ≤1 이 되므로
(2026-09-07 전수 탐색: N=8~20 은 전부 위반, N=21 이 가장 성긴 해) 램프 객체도 1:1 로 쪼갠다.

이름 규칙: 기존 이름 + 사슬 위치순 일련번호. R_D_W → R_D_W1(상류) · R_D_W2(하류). off 도 같다.
  D = SC1001 인터체인지 · F = SC1004 인터체인지 (기존 이름 규칙 유지)

산출: outputs/freeway_ramp_split_v2_20260907.json
사용: python derive_ramp_split_ver2_20260907.py [inpx] [mapping_json] [N] [out_json]
"""
import io
import json
import re
import sys
import datetime
from pathlib import Path

R = Path(__file__).resolve().parents[1]


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    net_path = Path(sys.argv[1]) if len(sys.argv) > 1 else R / "network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx"
    map_path = Path(sys.argv[2]) if len(sys.argv) > 2 else R / "evaluation/real_world_modi_control_ver2_20260907/control_mapping_ver2.json"
    N = int(sys.argv[3]) if len(sys.argv) > 3 else 21
    out_path = Path(sys.argv[4]) if len(sys.argv) > 4 else R / "outputs/freeway_ramp_split_v2_20260907.json"

    x = io.open(net_path, encoding="utf-8", errors="replace").read()
    M = json.load(io.open(map_path, encoding="utf-8"))
    fl = M["freeway_model_links"]
    chain, lengths = {}, {}
    for d, spec in fl.items():
        for lk, off in zip(spec["chain_links"], spec["chain_offsets_m"]):
            chain[str(lk)] = (d, float(off))
        lengths[d] = float(spec["length_m"])

    # 링크 차로수와 커넥터 끝점
    lanes_of = {}
    conns = []
    for m in re.finditer(r'<link\s([^>]*?)no="(\d+)"([^>]*?)>(.*?)</link>', x, re.S):
        no, body = m.group(2), m.group(4)
        lanes_of[no] = len(re.findall(r"<lane\b", body))
        fr = re.search(r'<fromLinkEndPt\s+lane="(\d+) (\d+)"\s+pos="([\d.\-]+)"', body)
        to = re.search(r'<toLinkEndPt\s+lane="(\d+) (\d+)"\s+pos="([\d.\-]+)"', body)
        if fr and to:
            conns.append((no, fr.group(1), float(fr.group(3)), to.group(1), float(to.group(3)),
                          len(re.findall(r"<lane\b", body))))

    # 기존 4개 그룹 = 미터 매핑의 model_ramp_key
    group_of_conn = {str(r["connector"]): r["model_ramp_key"] for r in M.get("ramp_meters", [])}

    on_ramps, off_ramps = [], []
    for cno, fl_, fpos, tl_, tpos, nl in conns:
        if tl_ in chain and fl_ not in chain:            # on-ramp
            d, off = chain[tl_]
            on_ramps.append({"connector": cno, "from_link": fl_, "to_link": tl_, "direction": d,
                             "chain_pos_m": off + tpos, "connector_lanes": nl,
                             "from_link_lanes": lanes_of.get(fl_), "legacy_group": group_of_conn.get(cno)})
        elif fl_ in chain and tl_ not in chain:          # off-ramp
            d, off = chain[fl_]
            off_ramps.append({"connector": cno, "from_link": fl_, "to_link": tl_, "direction": d,
                              "chain_pos_m": off + fpos, "connector_lanes": nl,
                              "to_link_lanes": lanes_of.get(tl_)})

    # 기존 off-ramp 그룹은 미터가 없으니 인터체인지(D/F)로 가른다 — on-ramp 그룹의 사슬 위치로 판정.
    inter = {}
    for d in fl:
        grp = {}
        for r in on_ramps:
            if r["direction"] != d or not r["legacy_group"]:
                continue
            grp.setdefault(r["legacy_group"], []).append(r["chain_pos_m"])
        inter[d] = {g: (min(v), max(v)) for g, v in grp.items()}

    def legacy_off_group(r):
        best, bd = None, 1e18
        for g, (lo, hi) in inter[r["direction"]].items():
            dist = 0.0 if lo <= r["chain_pos_m"] <= hi else min(abs(r["chain_pos_m"] - lo), abs(r["chain_pos_m"] - hi))
            if dist < bd:
                best, bd = g, dist
        return "OR_" + best.split("R_", 1)[1] if best else None

    for r in off_ramps:
        r["legacy_group"] = legacy_off_group(r)

    # 사슬 위치순 일련번호 부여 + 21분할 세그먼트 인덱스
    def number(rows):
        by = {}
        for r in sorted(rows, key=lambda r: (r["legacy_group"] or "", r["chain_pos_m"])):
            by.setdefault(r["legacy_group"], []).append(r)
        for g, lst in by.items():
            for i, r in enumerate(lst, 1):
                r["name"] = "%s%d" % (g, i)
        return sorted(rows, key=lambda r: (r["direction"], r["chain_pos_m"]))

    on_ramps = number(on_ramps)
    off_ramps = number(off_ramps)
    for r in on_ramps + off_ramps:
        L = lengths[r["direction"]] / N
        r["segment_index"] = min(N - 1, int(r["chain_pos_m"] // L))
        r["segment_length_m"] = round(L, 3)

    # 셀당 on<=1 off<=1 검사
    viol = []
    for d in fl:
        for kind, rows in (("on", on_ramps), ("off", off_ramps)):
            seen = {}
            for r in rows:
                if r["direction"] != d:
                    continue
                seen.setdefault(r["segment_index"], []).append(r["name"])
            for si, names in seen.items():
                if len(names) > 1:
                    viol.append((d, kind, si, names))

    doc = {"schema": "freeway_ramp_split_v2", "generated": datetime.date.today().isoformat(),
           "network": net_path.name, "mapping": map_path.name, "segments_per_link": N,
           "segment_length_km": {d: round(lengths[d] / N / 1000.0, 6) for d in fl},
           "definition": "모형 램프를 VISSIM 커넥터 1:1 로 분해한 정본. 이름 = 기존 그룹명 + 사슬 위치순 번호. "
                         "segment_index 는 균등 N 분할 기준. 이 파일이 config 의 ramps/off_ramps/"
                         "ramp_merge_segment_index/off_ramp_segment_index 의 단일 출처다.",
           "on_ramps": on_ramps, "off_ramps": off_ramps,
           "one_per_cell_violations": viol}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    io.open(out_path, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1))

    print("=== on-ramp %d개 ===" % len(on_ramps))
    print("  %-10s %-9s %10s %4s %-14s %-8s %s" % ("이름", "방향", "사슬[m]", "S", "커넥터←링크", "차로", "옛 그룹"))
    for r in on_ramps:
        print("  %-10s %-9s %10.1f %4d  c%-6s←%-4s %-8s %s"
              % (r["name"], r["direction"], r["chain_pos_m"], r["segment_index"],
                 r["connector"], r["from_link"], "%dcl/%dln" % (r["connector_lanes"], r["from_link_lanes"] or 0),
                 r["legacy_group"]))
    print("=== off-ramp %d개 ===" % len(off_ramps))
    for r in off_ramps:
        print("  %-10s %-9s %10.1f %4d  c%-6s→%-4s %-8s %s"
              % (r["name"], r["direction"], r["chain_pos_m"], r["segment_index"],
                 r["connector"], r["to_link"], "%dcl/%dln" % (r["connector_lanes"], r["to_link_lanes"] or 0),
                 r["legacy_group"]))
    print("\n셀당 on<=1 off<=1 위반: %s" % (viol if viol else "없음 (PASS)"))
    print("세그먼트 길이: %s" % doc["segment_length_km"])
    print("→ %s" % out_path)


if __name__ == "__main__":
    main()
