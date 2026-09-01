# -*- coding: utf-8 -*-
"""램프 병목을 만들 수 있는지 검정할 망 둘을 만든다. 원본은 안 덮는다.

왜 (2026-08-31).

실측으로 **램프 합류가 병목이 안 된다**. 원인 후보가 둘이고 각각 망 하나로 가른다.

  (1) 차로변경이 너무 관대하다
      램프 커넥터 8개가 전부 lnChgDist = 1000 m 다 (VISSIM 기본 200 m 의 5배).
      합류 교란이 1 km 에 퍼져 세그먼트(1.347 km) 안에서 국소 밀도가 안 오른다.
      **결정적 증거**: FW_W|2 는 상류 유량 6466 + 램프 752 = 7218 로 4차로 용량 6937 을
      104% 넘는데 임계 초과가 23.5% 에 그친다. 산술로는 막혀야 하는데 안 막힌다.

  (2) 램프 유입 자체가 작다
      램프별 실측이 용량의 31~67%(합 3457 / 7200 = 48%).
      합류 셀이 용량을 넘으려면 R_F_W 1.4배 · R_F_E 1.7배 · R_D_E 2.8배가 필요하다.

만드는 망.

  A  ..._lcd200.inpx    램프 커넥터 8개의 lnChgDist 1000 -> 200. **그것만** 바꾼다.
                        유입·경로·기하 불변이라 (1)의 단일변수 검정이다.

  B  ..._rampmax.inpx   유입 신설 없이 경로만 손봐 램프 몫을 최대로.
                        (a) 결정 1134 의 지하차도행(경로 2, 몫 14.3%)을 R_F_W 로 돌린다
                        (b) 램프행 경로의 relFlow 를 올린다
                        (c) 공급 링크(31·32·68·69)로 가는 상류 경로의 relFlow 를 올린다
                        relFlow 만으로는 한계가 있다 — fw14_ramp2 가 램프 relFlow 를 5배
                        키우고도 램프 유입이 +9.5%(3378 -> 3700)에 그쳤다. 1135·1136·1137 은
                        **모든 경로가 램프행**이라 재배분일 뿐이고, 총량은 공급 링크 통과량이
                        정하기 때문이다. 그래서 (c)가 핵심이다.

**B 는 도시부 흐름 분포를 바꾼다.** 기존 무제어 기준선(6692.0 등)을 그대로 쓸 수 없고
같은 망의 무제어를 새로 잡아야 한다.

사용:
  python scripts/make_ramp_probe_networks_20260831.py
"""
import argparse
import json
import re
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent

RAMP_CONNECTORS = ["10480", "10482", "10646", "10644", "10639", "10681", "10490", "10484"]

# B: (결정 no, 경로 no) -> 새 relFlow 값.
# 램프행·공급링크행을 올리고 비램프 형제는 그대로 둔다(빈 relFlow = 1).
ROUTE_BOOST = {
    # --- 램프 직결 결정 ---
    ("1134", "1"): 12.0,   # link 69 -> R_F_W (지금 5, 몫 71.4%)
    ("1134", "3"): 3.0,    # link 69 -> R_F_E (지금 1, 몫 14.3%)
    #  1134 경로 2(지하차도 dest 75)는 건드리지 않는다 — 상대적으로 몫이 줄어든다
    ("1135", "2"): 3.0,    # link 68 -> R_F_W
    ("1136", "1"): 6.0,    # link 32 -> R_D_W (지금 3)
    ("1137", "1"): 3.0,    # link 31 -> R_D_E
    # --- 공급 링크로 보내는 상류 결정 ---
    ("1116", "3"): 4.0,    # 37 -> 31   (지금 1, 몫 14.3%)
    ("1118", "2"): 10.0,   # 29 -> 31   (지금 5, 몫 45.5%)
    ("1119", "1"): 10.0,   # 40 -> 31   (지금 5, 몫 71.4%)
    ("1123", "2"): 10.0,   # 52 -> 68   (지금 5, 몫 71.4%)
    ("1124", "1"): 6.0,    # 66 -> 68   (지금 3, 몫 60.0%)
    ("1125", "1"): 6.0,    # 46 -> 68   (지금 3, 몫 60.0%)
    ("1130", "3"): 4.0,    # 74 -> 68   (지금 1.2, 몫 11.1%)
    ("1131", "2"): 4.0,    # 2  -> 32   (지금 1.4, 몫 13.5%)
    ("1131", "3"): 3.0,    # 2  -> 31   (지금 1, 몫 9.6%)
    ("1132", "1"): 3.0,    # 26 -> 31
    ("1132", "2"): 3.0,    # 26 -> 32
    ("1133", "1"): 3.0,    # 26 -> 68
}


def set_lnchgdist(text, connectors, value):
    """지정 커넥터의 lnChgDist 만 바꾼다. 다른 속성·바이트는 안 건드린다."""
    changed = []
    out, pos = [], 0
    for m in re.finditer(r"<link\b([^>]*)>", text):
        attrs = m.group(1)
        no = re.search(r'\bno="(\d+)"', attrs)
        if not no or no.group(1) not in connectors:
            continue
        cur = re.search(r'\blnChgDist="([^"]*)"', attrs)
        if not cur:
            changed.append({"connector": no.group(1), "error": "lnChgDist 속성 없음"})
            continue
        new_attrs = attrs[:cur.start(1)] + str(value) + attrs[cur.end(1):]
        out.append(text[pos:m.start(1)])
        out.append(new_attrs)
        pos = m.end(1)
        changed.append({"connector": no.group(1), "before": cur.group(1), "after": str(value)})
    out.append(text[pos:])
    return "".join(out), changed


def _relval(s):
    if not s or not s.strip():
        return 1.0
    m = re.findall(r":([\d.]+)", s)
    return float(m[0]) if m else 1.0


def set_relflows(text, boosts):
    """(결정, 경로) 의 relFlow 를 바꾼다. 빈 값이면 '2 0:<v>' 형식으로 새로 넣는다."""
    changed = []
    body_m = re.search(r"<vehicleRoutingDecisionsStatic>(.*?)</vehicleRoutingDecisionsStatic>",
                       text, re.S)
    body = body_m.group(1)
    new_body = body
    for (dec, route), val in boosts.items():
        dm = re.search(r'(<vehicleRoutingDecisionStatic\s[^>]*\bno="%s"[^>]*>)(.*?)(</vehicleRoutingDecisionStatic>)'
                       % re.escape(dec), new_body, re.S)
        if not dm:
            changed.append({"decision": dec, "route": route, "error": "결정 없음"})
            continue
        inner = dm.group(2)
        rm = re.search(r'(<vehicleRouteStatic\s)([^>]*\bno="%s"[^>]*)(>)' % re.escape(route), inner)
        if not rm:
            changed.append({"decision": dec, "route": route, "error": "경로 없음"})
            continue
        ra = rm.group(2)
        cur = re.search(r'\brelFlow="([^"]*)"', ra)
        before = cur.group(1) if cur else ""
        newval = "2 0:%s" % (("%g" % val))
        if cur:
            new_ra = ra[:cur.start(1)] + newval + ra[cur.end(1):]
        else:
            new_ra = ra + ' relFlow="%s"' % newval
        new_inner = inner[:rm.start(2)] + new_ra + inner[rm.end(2):]
        new_body = new_body[:dm.start(2)] + new_inner + new_body[dm.end(2):]
        changed.append({"decision": dec, "route": route,
                        "before": before or "(빈값=1)", "after": newval,
                        "before_val": _relval(before), "after_val": val})
    return text[:body_m.start(1)] + new_body + text[body_m.end(1):], changed


def shares(text, decisions):
    """결정별 경로 몫을 계산해 검증에 쓴다."""
    body = re.search(r"<vehicleRoutingDecisionsStatic>(.*?)</vehicleRoutingDecisionsStatic>",
                     text, re.S).group(1)
    out = {}
    for dec in decisions:
        dm = re.search(r'<vehicleRoutingDecisionStatic\s[^>]*\bno="%s"[^>]*>(.*?)</vehicleRoutingDecisionStatic>'
                       % re.escape(dec), body, re.S)
        if not dm:
            continue
        rows = []
        for r in re.finditer(r"<vehicleRouteStatic\s([^>]*)>", dm.group(1)):
            ra = r.group(1)
            no = re.search(r'\bno="(\d+)"', ra)
            dl = re.search(r'\bdestLink="(\d+)"', ra)
            rel = re.search(r'\brelFlow="([^"]*)"', ra)
            rows.append((no.group(1) if no else "?", dl.group(1) if dl else "?",
                         _relval(rel.group(1) if rel else "")))
        tot = sum(x[2] for x in rows) or 1.0
        out[dec] = {x[0]: {"dest": x[1], "rel": x[2], "share_pct": round(100 * x[2] / tot, 1)}
                    for x in rows}
    return out


def verify_only_expected(a, b, allow_tags):
    """줄 단위로 바뀐 줄이 전부 기대한 태그인지 확인한다."""
    la, lb = a.splitlines(), b.splitlines()
    if len(la) != len(lb):
        return False, "줄 수 %d != %d" % (len(la), len(lb))
    bad = [i for i, (x, y) in enumerate(zip(la, lb))
           if x != y and not any(t in la[i] for t in allow_tags)]
    n = sum(1 for x, y in zip(la, lb) if x != y)
    return (not bad), ("바뀐 줄 %d · 예상 밖 %d%s" % (n, len(bad),
                       (" — 예: " + la[bad[0]].strip()[:70]) if bad else ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="network/real_world_gaepo_modi/modi_eval_userfix_20260814e.inpx")
    ap.add_argument("--lnchgdist", type=float, default=200.0)
    ap.add_argument("--manifest", default="outputs/ramp_probe_networks_20260831.json")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    src = R / args.source
    text = src.read_text(encoding="utf-8")
    print("원본 %s · %d 바이트" % (src.name, len(text)))
    doc = {"schema_version": "ramp-probe-networks/1", "generated": "2026-08-31",
           "source": args.source, "networks": []}

    # ---- A: lnChgDist ----
    a_text, a_changed = set_lnchgdist(text, set(RAMP_CONNECTORS), args.lnchgdist)
    ok, msg = verify_only_expected(text, a_text, ["<link "])
    dst_a = src.with_name(src.stem + "_lcd200" + src.suffix)
    dst_a.write_text(a_text, encoding="utf-8")
    print()
    print("A  %s" % dst_a.name)
    print("   램프 커넥터 %d개 lnChgDist -> %g   검증 %s (%s)"
          % (len([c for c in a_changed if "after" in c]), args.lnchgdist, "OK" if ok else "**실패**", msg))
    for c in a_changed[:3]:
        print("      %s: %s -> %s" % (c.get("connector"), c.get("before"), c.get("after")))
    doc["networks"].append({"kind": "lnChgDist", "output": dst_a.name,
                            "value": args.lnchgdist, "changed": a_changed,
                            "verified": ok, "verify_note": msg})

    # ---- B: 경로 relFlow ----
    decs = sorted({d for d, _ in ROUTE_BOOST})
    before_sh = shares(text, decs)
    b_text, b_changed = set_relflows(text, ROUTE_BOOST)
    after_sh = shares(b_text, decs)
    ok2, msg2 = verify_only_expected(text, b_text, ["<vehicleRouteStatic "])
    dst_b = src.with_name(src.stem + "_rampmax" + src.suffix)
    dst_b.write_text(b_text, encoding="utf-8")
    print()
    print("B  %s" % dst_b.name)
    print("   경로 %d개 relFlow 변경   검증 %s (%s)"
          % (len([c for c in b_changed if "after" in c]), "OK" if ok2 else "**실패**", msg2))
    err = [c for c in b_changed if "error" in c]
    for e in err:
        print("      !! %s" % e)
    print()
    print("   %-7s %-6s %-8s %14s %14s" % ("결정", "경로", "목적", "몫 전", "몫 후"))
    for d in decs:
        for rno in sorted(before_sh.get(d, {}), key=lambda x: int(x)):
            b0 = before_sh[d][rno]
            b1 = after_sh.get(d, {}).get(rno, {})
            mark = " <-" if (d, rno) in ROUTE_BOOST else ""
            print("   %-7s %-6s %-8s %13.1f%% %13.1f%%%s"
                  % (d, rno, b0["dest"], b0["share_pct"], b1.get("share_pct", 0.0), mark))
    doc["networks"].append({"kind": "route_relflow", "output": dst_b.name,
                            "boosts": {"%s/%s" % k: v for k, v in ROUTE_BOOST.items()},
                            "shares_before": before_sh, "shares_after": after_sh,
                            "changed": b_changed, "verified": ok2, "verify_note": msg2,
                            "caveat": "도시부 흐름 분포가 바뀐다 — 같은 망의 무제어 기준선을 새로 잡아야 한다."})
    (R / args.manifest).write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print()
    print("-> %s" % args.manifest)
    return 0 if (ok and ok2 and not err) else 1


if __name__ == "__main__":
    raise SystemExit(main())
