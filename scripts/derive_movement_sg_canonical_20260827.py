# -*- coding: utf-8 -*-
"""movement -> SG 정본 매핑. 정지선 커넥터 제안 + 신호두 교차검증 + 판정 필요 목록.

배경 (2026-08-27).

죽은 현시 판정이 `signal_group_actuation_plan_v3.json` 의 `axis_green_sec[phase] <= 0`
(현시의 **축** 단위 값)을 movement 단위 beta 판정에 썼다. VISSIM 전수 차량 추적이
그것을 반증한다 — 그 movement 17개 중 4개에서 실제로 차가 지난다(33건). 폐루프 TTT 도
+80.6 나빠졌다(4742.6 -> 4823.2).

두 정본이 이미 있었고 죽은현시 판정만 안 썼다.

  outputs/movement_connector_map_20260824.json   정지선 커넥터로 유도한 movement -> sg (276개)
  network/.../*.inpx  <signalHead lane="링크 차로" sg="SC SG">   VISSIM 직접 선언 (537개)

이 스크립트는 둘을 교차검증한다. 규칙으로 메우지 않는다 — 두 근거가 갈리거나 어느
쪽도 답을 못 주는 자리만 `needs_decision` 으로 뽑아 사람이 판정하게 한다
(player 권역·link_to_origins 과 같은 방식).

산출: outputs/movement_sg_canonical_20260827.json
"""
import argparse
import io
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

R = Path(__file__).resolve().parent.parent


def parse_signal_heads(inpx: Path):
    """신호두 -> {(링크, 차로): {(sc, sg)}} 와 {링크: {(sc, sg)}}."""
    text = inpx.read_text(encoding="utf-8", errors="replace")
    by_lane, by_link = defaultdict(set), defaultdict(set)
    n = 0
    for m in re.finditer(r"<signalHead\b[^>]*/>", text):
        s = m.group(0)
        lane = re.search(r'lane="([^"]+)"', s)
        sg = re.search(r'sg="([^"]+)"', s)
        if not lane or not sg:
            continue
        lp, sp = lane.group(1).split(), sg.group(1).split()
        if not lp or len(sp) < 2:
            continue
        n += 1
        by_lane[(lp[0], lp[1] if len(lp) > 1 else "")].add((sp[0], sp[1]))
        by_link[lp[0]].add((sp[0], sp[1]))
    return by_lane, by_link, n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inpx", default="network/real_world_gaepo_modi/modi_eval_userfix_20260814e.inpx")
    ap.add_argument("--connector-map", default="outputs/movement_connector_map_20260824.json")
    ap.add_argument("--out", default="outputs/movement_sg_canonical_20260827.json")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    by_lane, by_link, n_heads = parse_signal_heads(R / args.inpx)
    cm = json.loads((R / args.connector_map).read_text(encoding="utf-8"))
    approaches = cm.get("approaches") or {}
    proposal = cm.get("proposal") or {}
    print("신호두 %d개 · 커넥터 제안 %d개 · 접근로 %d개" % (n_heads, len(proposal), len(approaches)))

    # 접근로 -> 정지선 링크
    stoplines = {}
    for key, spec in approaches.items():
        sig = str(spec.get("signal") or "")
        app = str(spec.get("approach") or "")
        stoplines[(sig, app)] = [str(x) for x in (spec.get("stoplines") or [])]

    plan = json.loads((R / "outputs/signal_group_actuation_plan_v3.json").read_text(encoding="utf-8"))
    never = set(plan.get("never_green_signal_groups") or [])

    resolved, needs, conflicts = {}, {}, []
    for mv, spec in sorted(proposal.items()):
        sig = str(spec.get("signal") or "")
        app = str(spec.get("approach") or "")
        sgs = [str(x) for x in (spec.get("sg") or [])]
        sls = stoplines.get((sig, app)) or []
        sc_no = re.sub(r"^SC", "", sig)
        head_sgs = set()
        for lk in sls:
            head_sgs |= {sg for (sc, sg) in by_link.get(lk, set()) if sc == sc_no}

        if len(sgs) == 1 and sgs[0] in head_sgs:
            sg = sgs[0]
            resolved[mv] = {"signal": sig, "sg": sg, "approach": app,
                            "dest": spec.get("dest"), "connectors": spec.get("connectors"),
                            "lanes": spec.get("lanes"), "stoplines": sls,
                            "sg_key": "%s:%s" % (sig, sg),
                            "never_green": ("%s:%s" % (sig, sg)) in never,
                            "agreement": "커넥터 제안 == 신호두"}
        elif len(sgs) == 1 and head_sgs and sgs[0] not in head_sgs:
            conflicts.append({"movement": mv, "signal": sig, "approach": app,
                              "connector_sg": sgs[0], "signalhead_sgs": sorted(head_sgs),
                              "stoplines": sls,
                              "reason": "커넥터 제안과 신호두가 다르다"})
        elif len(sgs) == 1 and not head_sgs:
            # 신호두가 정지선 링크에 없다 — 상시허용이거나 정지선 목록이 비었다.
            sg = sgs[0]
            resolved[mv] = {"signal": sig, "sg": sg, "approach": app,
                            "dest": spec.get("dest"), "connectors": spec.get("connectors"),
                            "lanes": spec.get("lanes"), "stoplines": sls,
                            "sg_key": "%s:%s" % (sig, sg),
                            "never_green": ("%s:%s" % (sig, sg)) in never,
                            "agreement": "커넥터 제안만 (정지선 링크에 신호두 없음)"}
        else:
            needs[mv] = {"signal": sig, "approach": app, "dest": spec.get("dest"),
                         "connector_sgs": sgs, "signalhead_sgs": sorted(head_sgs),
                         "connectors": spec.get("connectors"), "lanes": spec.get("lanes"),
                         "stoplines": sls,
                         "reason": ("커넥터 제안에 SG 가 여럿" if len(sgs) > 1
                                    else "커넥터 제안에 SG 가 없다")}

    doc = {
        "schema_version": "movement-sg-canonical/1",
        "generated": "2026-08-27",
        "why": "axis_green_sec(현시 축 단위)로 movement 단위 beta 를 판정하다 실측과 어긋났다. "
               "정지선 커넥터 제안과 inpx 신호두를 교차검증해 근거를 movement 해상도로 되돌린다.",
        "sources": {"inpx": args.inpx, "signal_heads": n_heads,
                    "connector_map": args.connector_map, "proposals": len(proposal)},
        "counts": {"resolved": len(resolved), "needs_decision": len(needs),
                   "conflicts": len(conflicts)},
        "never_green_signal_groups": sorted(never),
        "resolved": resolved,
        "needs_decision": needs,
        "conflicts": conflicts,
    }
    out = R / args.out
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")

    print()
    print("해결 %d · 판정 필요 %d · 충돌 %d" % (len(resolved), len(needs), len(conflicts)))
    agree = defaultdict(int)
    for v in resolved.values():
        agree[v["agreement"]] += 1
    for k, n in sorted(agree.items(), key=lambda kv: -kv[1]):
        print("   해결 %3d  %s" % (n, k))
    rs = defaultdict(int)
    for v in needs.values():
        rs[v["reason"]] += 1
    for k, n in sorted(rs.items(), key=lambda kv: -kv[1]):
        print("   판정 %3d  %s" % (n, k))
    nz = [m for m, v in resolved.items() if v["never_green"]]
    print("   해결분 중 never_green SG 에 붙은 movement %d개%s"
          % (len(nz), (": " + ", ".join(sorted(nz)[:6])) if nz else ""))
    print("-> %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
