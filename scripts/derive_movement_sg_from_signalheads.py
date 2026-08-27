# -*- coding: utf-8 -*-
"""movement -> 신호군(SG) 매핑을 `.inpx` 신호두에서 직접 유도한다.

왜 이 스크립트가 필요한가 (2026-08-27).

죽은 현시 판정(`apply_dead_phase_beta_zero`)이 `signal_group_actuation_plan_v3.json` 의
`axis_green_sec[phase] <= 0` 을 근거로 movement 17개의 beta 를 0 으로 만들었다.
그런데 VISSIM 전수 차량 추적으로 보면 그 movement 중 **4개에서 실제로 차가 지나간다**
(SC108_S_to_W_SC107 16건 · SC108_N_SC7_to_E_SC109 9건 · SC7_E_SC16_to_N_SC11 7건 ·
SC107_N_SC1_to_W_SC1004 1건). 폐루프 TTT 도 +80.6 나빠졌다(4742.6 -> 4823.2).

원인은 **근거의 해상도**다. `axis_green_sec` 은 현시의 **축** 단위 값인데 그것을
movement 단위 판정에 썼다. 한 현시는 SG 여러 개를 묶고, 축이 죽어도 그 현시에 매달린
다른 SG 는 살아 있을 수 있다. 실제로 위 4개의 origin 링크에 붙은 SG 는
SC107:7 · SC108:8 · SC108:4 · SC7:1 이고, 넷 다 `never_green_signal_groups` 에 없다.

정답은 추론이 아니라 선언으로 이미 망에 있다.

    <signalHead lane="1220007104 2" sg="1 2" pos="290.05" .../>
                     ^링크 ^차로        ^SC ^SG

VISSIM 이 "어느 SG 가 어느 링크의 어느 차로를 제어하는가" 를 직접 갖고 있다.
이 스크립트는 그것만 읽는다. 규칙으로 메우지 않는다 — 갈리지 않는 자리는
`needs_decision` 으로 뽑아 사람이 판정하게 한다(player 권역·link_to_origins 과 같은 방식).

산출: outputs/movement_sg_from_signalheads_<날짜>.json
    resolved        movement -> {"sc","sg","link","lane","evidence"}
    needs_decision  movement -> 후보 여럿 또는 없음 + 이유
    never_green     계획이 말하는 죽은 SG 목록(대조용)
    disagreements   현재 movement_signal_group_map 과 다른 자리
"""
import argparse
import io
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

R = Path(__file__).resolve().parent.parent


def parse_signal_heads(inpx: Path) -> list[dict]:
    """신호두를 읽는다. lane="<링크> <차로>" · sg="<SC> <SG>"."""
    text = inpx.read_text(encoding="utf-8", errors="replace")
    out = []
    for m in re.finditer(r"<signalHead\b[^>]*/>", text):
        s = m.group(0)
        lane = re.search(r'lane="([^"]+)"', s)
        sg = re.search(r'sg="([^"]+)"', s)
        if not lane or not sg:
            continue
        lparts = lane.group(1).split()
        sparts = sg.group(1).split()
        if not lparts or not sparts:
            continue
        pos = re.search(r'pos="([^"]+)"', s)
        no = re.search(r'\bno="([^"]+)"', s)
        out.append({
            "head_no": no.group(1) if no else "",
            "link": lparts[0],
            "lane": lparts[1] if len(lparts) > 1 else "",
            "sc": sparts[0],
            "sg": sparts[1] if len(sparts) > 1 else "",
            "pos_m": float(pos.group(1)) if pos else None,
        })
    return out


def load_adapter(tuning: Path, state_json: Path):
    """정본 부트스트랩으로 cfg·detector mapping 을 얻는다."""
    import importlib.util as ilu
    sys.path.insert(0, str(R))
    spec = ilu.spec_from_file_location(
        "vsa", R / "evaluation/controllers/vissim_stackelberg_adapter.py")
    qb = ilu.module_from_spec(spec)
    spec.loader.exec_module(qb)
    tun = qb.load_optional_json(str(tuning))
    cal = qb.load_optional_json(str(
        R / "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json"))
    det = qb.load_optional_json(str(qb.WORKSPACE_ROOT / str(tun["detector_mapping_json"])))
    qb.install_config_switches(tun)
    cfg = qb.build_config(R / "vendor/NumSim-mine", 150.0, 5400.0, "wu-link", cal, tun,
                          local_observation=True, flagship=True)
    return qb, cfg, det, tun


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inpx", default="network/real_world_gaepo_modi/modi_eval_userfix_20260814e.inpx")
    ap.add_argument("--tuning", default="evaluation/configs/canon_plantfix_20260827.json")
    ap.add_argument("--state", default="")
    ap.add_argument("--out", default="outputs/movement_sg_from_signalheads_20260827.json")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    inpx = R / args.inpx
    if not inpx.is_file():
        raise SystemExit("!! inpx 없음: %s" % inpx)
    heads = parse_signal_heads(inpx)
    by_link = defaultdict(set)
    detail = defaultdict(list)
    for h in heads:
        by_link[h["link"]].add((h["sc"], h["sg"]))
        detail[h["link"]].append(h)
    print("신호두 %d개 · 링크 %d개 · SC %d개" % (
        len(heads), len(by_link), len({h["sc"] for h in heads})))

    qb, cfg, det, tun = load_adapter(R / args.tuning, None)
    MV = dict(cfg.network.urban_movements)
    print("movement %d개 (병합 전 원본 사양)" % len(MV))

    # origin 저류 -> 그 저류를 구성하는 링크들
    l2o = {str(k): (v if isinstance(v, list) else [v])
           for k, v in (det.get("link_to_origins") or {}).items()}
    o2l = defaultdict(set)
    for lk, os_ in l2o.items():
        for o in os_:
            o2l[str(o)].add(lk)

    plan = json.loads((R / "outputs/signal_group_actuation_plan_v3.json").read_text(encoding="utf-8"))
    never = set(plan.get("never_green_signal_groups") or [])

    resolved, needs = {}, {}
    for mv, sp in sorted(MV.items()):
        node = str(sp.get("intersection") or "")
        origin = str(sp.get("origin") or "")
        links = o2l.get(origin, set())
        # 그 교차로 번호의 신호두만 본다 — 링크가 여러 교차로에 걸칠 수 있다.
        sc_no = re.sub(r"^SC", "", node)
        cands = []
        for lk in links:
            for h in detail.get(lk, []):
                if h["sc"] == sc_no:
                    cands.append(h)
        if not cands:
            needs[mv] = {"reason": "그 교차로의 신호두가 origin 링크에 없다 "
                                   "(상시허용 회전이거나 origin 링크 집합이 정지선을 안 담는다)",
                         "node": node, "origin": origin, "origin_link_count": len(links),
                         "phase_declared": sp.get("phase")}
            continue
        sgs = sorted({h["sg"] for h in cands})
        if len(sgs) == 1:
            h = cands[0]
            resolved[mv] = {"sc": sc_no, "sg": sgs[0], "link": h["link"], "lane": h["lane"],
                            "phase_declared": sp.get("phase"),
                            "sg_key": "%s:%s" % (node, sgs[0]),
                            "never_green": ("%s:%s" % (node, sgs[0])) in never,
                            "evidence": "signalHead no=%s pos=%s" % (h["head_no"], h["pos_m"])}
        else:
            needs[mv] = {"reason": "origin 링크에 SG 가 여럿 — 회전별 차로 배정이 필요하다",
                         "node": node, "origin": origin,
                         "phase_declared": sp.get("phase"),
                         "turn": sp.get("turn"), "exit": sp.get("exit"),
                         "candidates": [{"sg": h["sg"], "link": h["link"], "lane": h["lane"],
                                         "pos_m": h["pos_m"],
                                         "never_green": ("%s:%s" % (node, h["sg"])) in never}
                                        for h in sorted(cands, key=lambda x: (x["link"], x["lane"]))]}

    # 현행 매핑과 대조
    cur_path = R / "outputs/movement_signal_group_map_v3.json"
    disagree = []
    if cur_path.is_file():
        cur = json.loads(cur_path.read_text(encoding="utf-8"))
        cm = cur.get("movement_signal_group") or cur
        for mv, info in resolved.items():
            old = cm.get(mv)
            if isinstance(old, dict):
                old_sg = str(old.get("sg") or old.get("signal_group") or "")
            else:
                old_sg = str(old) if old is not None else ""
            if old_sg and old_sg != info["sg"]:
                disagree.append({"movement": mv, "current_sg": old_sg,
                                 "signalhead_sg": info["sg"], "node": info["sc"]})

    doc = {
        "schema_version": "movement-sg-from-signalheads/1",
        "generated": "2026-08-27",
        "source": {"inpx": str(args.inpx), "signal_heads": len(heads),
                   "tuning": str(args.tuning)},
        "why": "axis_green_sec(축 단위)로 movement 단위를 판정하다 실측과 어긋났다. "
               "signalHead 는 링크·차로 -> SG 를 VISSIM 이 직접 선언한 값이라 추론이 없다.",
        "counts": {"movements": len(MV), "resolved": len(resolved),
                   "needs_decision": len(needs), "disagreements": len(disagree)},
        "never_green_signal_groups": sorted(never),
        "resolved": resolved,
        "needs_decision": needs,
        "disagreements": disagree,
    }
    out = R / args.out
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")

    print()
    print("해결 %d · 판정 필요 %d · 현행과 불일치 %d" % (len(resolved), len(needs), len(disagree)))
    reasons = defaultdict(int)
    for v in needs.values():
        reasons[v["reason"]] += 1
    for r, n in sorted(reasons.items(), key=lambda kv: -kv[1]):
        print("   판정필요 %3d  %s" % (n, r))
    nz = [m for m, v in resolved.items() if v["never_green"]]
    print("   해결분 중 never_green SG 에 붙은 movement %d개" % len(nz))
    print("-> %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
