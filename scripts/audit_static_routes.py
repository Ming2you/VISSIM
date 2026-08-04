# VISSIM 정적경로가 '위치제약'을 지켜 완주 가능한지 전수 감사하는 도구.
#
# 배경. 링크 위에서 차량은 상류->하류로만 간다. 링크 L 에 pos p 로 진입했다면 그 링크의 출구
# 커넥터 중 frmpos >= p 인 것만 쓸 수 있다. 경로가 요구하는 커넥터가 진입점보다 상류에 있으면
# 그 경로는 물리적으로 완주 불가이고, VISSIM 은 차량을 링크 끝에서 삭제하며 다음 경고를 남긴다.
#
#   "Vehicle N (on Static Vehicle Route V - R) arrived at the end of link L
#    without having found the next link (C) of its route."
#
# 이 결함은 GUI 에서 커넥터 끝점을 몇 미터 끌어당기는 것만으로도 생기고, 눈으로는 보이지 않는다.
# 실제로 개포동 네트워크에서 VRD 1135 가 이 형태로 런당 278 대를 삭제하고 있었다.
#
# 사용법:  python audit_static_routes.py <network.inpx>
# 종료코드: 실행불가 경로가 있으면 1, 없으면 0.

import math
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict, deque

TOL = 1e-6
MAXHOP = 12          # 경유지 잇기용 경로탐색의 최대 커넥터 홉


def load_network(path):
    root = ET.parse(path).getroot()
    links, conns = {}, {}
    for ln in root.iter("link"):
        no = ln.get("no")
        if no is None:
            continue
        no = int(no)
        fr, to = ln.find("./fromLinkEndPt"), ln.find("./toLinkEndPt")
        if fr is not None and to is not None:
            fl, fln = fr.get("lane").split()
            tl, tln = to.get("lane").split()
            conns[no] = dict(frm=int(fl), frmpos=float(fr.get("pos")), frmlane=int(fln),
                             to=int(tl), topos=float(to.get("pos")), tolane=int(tln),
                             nl=len(ln.findall("./lanes/lane")))
        else:
            pts = [(float(q.get("x")), float(q.get("y"))) for q in ln.iter("linkPolyPoint")]
            links[no] = dict(len=sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)),
                             nl=len(ln.findall("./lanes/lane")))
    return root, links, conns


def build_index(conns):
    outof = defaultdict(list)
    for c, r in conns.items():
        outof[r["frm"]].append((r["frmpos"], c))
    for k in outof:
        outof[k].sort()
    return outof


def reach(outof, conns, src_link, src_pos, dst_link):
    """(link,pos) 에서 dst_link 까지 최소 홉 경로. 반환 (도착pos, [커넥터...]) 또는 None."""
    if src_link == dst_link:
        return (src_pos, [])
    seen = {src_link: src_pos}
    q = deque([(src_link, src_pos, [])])
    while q:
        L, p, path = q.popleft()
        if len(path) >= MAXHOP:
            continue
        for frmpos, c in outof.get(L, []):
            if frmpos < p - TOL:
                continue
            r = conns[c]
            t, tp = r["to"], r["topos"]
            if t == dst_link:
                return (tp, path + [c])
            if t not in seen or tp < seen[t] - 1.0:
                seen[t] = tp
                q.append((t, tp, path + [c]))
    return None


def audit(path):
    root, links, conns = load_network(path)
    outof = build_index(conns)
    bad, ok = [], 0

    for v in root.iter("vehicleRoutingDecisionStatic"):
        vno, vlink, vpos = int(v.get("no")), int(v.get("link")), float(v.get("pos"))
        for rt in v.iter("vehicleRouteStatic"):
            rno = rt.get("no")
            seq = [int(e.get("key")) for e in rt.iter("intObjectRef")]
            dest, dpos = int(rt.get("destLink")), float(rt.get("destPos"))

            # VRD 가 커넥터 위면 그 커넥터를 마저 타고 도착 링크로 진입한다
            if vlink in conns:
                cur, curpos = conns[vlink]["to"], conns[vlink]["topos"]
                trace = [f"conn{vlink}@{vpos:.1f}->L{cur}@{curpos:.1f}"]
            else:
                cur, curpos = vlink, vpos
                trace = [f"L{cur}@{curpos:.1f}"]

            fail = None
            for key in seq:
                if key in conns:
                    c = conns[key]
                    if c["frm"] != cur:
                        r = reach(outof, conns, cur, curpos, c["frm"])
                        if r is None:
                            fail = f"커넥터 {key}(시작 링크 {c['frm']}) 로 갈 방법이 없음 — 현재 L{cur}@{curpos:.1f}"
                            break
                        cur, curpos = c["frm"], r[0]
                        trace.append(f"~{r[1]}~>L{cur}@{curpos:.1f}")
                    if c["frmpos"] < curpos - TOL:
                        fail = (f"커넥터 {key} 는 링크 {cur} @{c['frmpos']:.3f} 인데 차량은 @{curpos:.3f} "
                                f"— {curpos - c['frmpos']:.3f} m 지나침")
                        break
                    cur, curpos = c["to"], c["topos"]
                    trace.append(f"-[{key}]->L{cur}@{curpos:.1f}")
                elif key in links:
                    if key == cur:
                        continue
                    r = reach(outof, conns, cur, curpos, key)
                    if r is None:
                        fail = f"경유 링크 {key} 에 도달 불가 — 현재 L{cur}@{curpos:.1f}"
                        break
                    cur, curpos = key, r[0]
                    trace.append(f"~{r[1]}~>L{cur}@{curpos:.1f}")
                else:
                    fail = f"존재하지 않는 객체 {key}"
                    break

            if not fail:
                if dest in conns:
                    c = conns[dest]
                    if c["frm"] != cur:
                        r = reach(outof, conns, cur, curpos, c["frm"])
                        if r is None:
                            fail = f"목적 커넥터 {dest} 의 시작 링크 {c['frm']} 에 도달 불가"
                        else:
                            curpos = r[0]
                    if not fail and c["frmpos"] < curpos - TOL:
                        fail = f"목적 커넥터 {dest} 진입점 @{c['frmpos']:.3f} 을 @{curpos:.3f} 에서 지나침"
                elif dest != cur:
                    r = reach(outof, conns, cur, curpos, dest)
                    if r is None:
                        fail = f"목적 링크 {dest} 에 도달 불가 (현재 L{cur}@{curpos:.1f})"
                    elif dpos < r[0] - TOL:
                        fail = f"목적 링크 {dest} 진입 pos {r[0]:.1f} 인데 목적 pos 는 {dpos:.1f} (상류)"
                elif dpos < curpos - TOL:
                    fail = f"목적 pos {dpos:.1f} 가 현재 pos {curpos:.1f} 보다 상류"

            if fail:
                bad.append((vno, rno, fail, " ".join(trace), seq, dest, dpos))
            else:
                ok += 1

    print(f"정적경로 감사 — 정상 {ok} / 실행불가 {len(bad)}   [{path}]")
    for vno, rno, why, tr, seq, d, dp in bad:
        print(f"\n  VRD {vno} route {rno}: {why}")
        print(f"     seq={seq}  dest={d}@{dp:.1f}")
        print(f"     추적: {tr}")
    return bad


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python audit_static_routes.py <network.inpx>")
        raise SystemExit(2)
    raise SystemExit(1 if audit(sys.argv[1]) else 0)
