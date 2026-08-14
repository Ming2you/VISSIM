#!/usr/bin/env python3
# 정적 경로가 커넥터로 실제로 이어지는지 검사한다 — 커넥터 삭제가 경로를 끊는 함정용
"""망을 편집한 뒤 VISSIM 이 시뮬레이션을 시작조차 못 하는 경우를 미리 잡는다.

## 왜 필요한가

VISSIM 에서 커넥터를 지우면 그 커넥터를 명시로 지나던 `vehicleRouteStatic` 의
`linkSeq` 에서 **그 항목만 빠지고 경로는 남는다.** 링크 사이에 대체 커넥터가 있어도
VISSIM 은 `Static Vehicle Route N-M is not complete` 로 판정하고 시뮬레이션을 시작하지
않는다. 그러면 `RunSingleStep` 이 시계를 못 움직이고(before=0 after=0), 그 상태에서
모든 COM 속성 설정이 거부된다.

2026-08-14 실측: 커넥터 10613 삭제 하나가 램프미터 SC 8개의 `ContrByCOM` 실패 +
차량 캡처 실패로 나타났다. **램프는 증상이지 원인이 아니다.** 세 시간을 램프 쪽에서
헤맸다 — 링크 연결성만 보고 "대체 경로가 있으니 안전"이라 판단한 것이 원인이다.

## 판정 규약 — 기준선 대비 델타만 본다

엄격 규칙(`[결정.link] + linkSeq + [destLink]` 가 커넥터로 정확히 이어져야 한다)은
정상 망에서도 9건을 과검출한다(결정 283/1126/1138). VISSIM 이 Error 로 잡는 것과
이 규칙이 잡는 것이 완전히 같지는 않다. 그래서 **정상 망을 기준선으로 주고 늘어난
것만** 본다. 2026-08-14 실측에서 이 방식이 VISSIM 판정과 정확히 일치했다.

    legfix(정상)  9건        userfix(실패) 10건
    늘어난 1건 = 결정 1061 경로 1 = VISSIM 이 잡은 그 오류

## 쓰는 법

    python scripts/check_route_completeness.py --network <편집한.inpx> \
        --baseline <정상.inpx>

`--baseline` 을 주면 델타가 0 일 때만 PASS 다. 안 주면 절대 건수만 낸다.
"""
from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def connector_map(root: ET.Element) -> dict[str, tuple[str, str]]:
    """커넥터 번호 -> (출발 링크, 도착 링크). 실링크는 담지 않는다."""
    conn: dict[str, tuple[str, str]] = {}
    for link in root.iter("link"):
        no = link.get("no")
        if no is None:
            continue
        src, dst = link.find("./fromLinkEndPt"), link.find("./toLinkEndPt")
        if src is None or dst is None:
            continue
        a = (src.get("lane") or "").split()
        b = (dst.get("lane") or "").split()
        if len(a) == 2 and len(b) == 2:
            conn[str(no)] = (a[0], b[0])
    return conn


def broken_routes(root: ET.Element) -> list[tuple[str, str, str, str]]:
    """끊긴 경로 목록 — (결정no, 경로no, 경로이름, 사유)."""
    conn = connector_map(root)
    out: list[tuple[str, str, str, str]] = []
    for dec in root.iter("vehicleRoutingDecisionStatic"):
        start = str(dec.get("link"))
        for route in dec.iter("vehicleRouteStatic"):
            chain = [start] + [x.get("key") for x in route.iter("intObjectRef")]
            dest = str(route.get("destLink"))
            if chain[-1] != dest:
                chain.append(dest)
            cur, why = chain[0], None
            for step in chain[1:]:
                if step in conn:
                    a, b = conn[step]
                    if a != cur:
                        why = f"커넥터 {step} 은 {a} 출발인데 현재 {cur}"
                        break
                    cur = b
                elif step != cur:
                    why = f"{cur} 다음이 실링크 {step} — 잇는 커넥터가 순서에 없다"
                    break
            if why:
                out.append((str(dec.get("no")), str(route.get("no")),
                            route.get("name") or "", why))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--network", required=True, help="검사할 .inpx")
    ap.add_argument("--baseline", default="", help="정상으로 알려진 .inpx. 주면 델타로 판정한다")
    ap.add_argument("--show", type=int, default=10, help="출력할 항목 수")
    args = ap.parse_args()

    target = broken_routes(ET.parse(args.network).getroot())
    print(f"검사 대상 {Path(args.network).name}: 끊긴 경로 {len(target)}건")

    if not args.baseline:
        for d, r, n, w in target[: args.show]:
            print(f"   결정 {d} 경로 {r} «{n}»: {w}")
        print("기준선을 안 줬으므로 판정하지 않는다(엄격 규칙은 정상 망도 과검출한다).")
        return 0

    base = broken_routes(ET.parse(args.baseline).getroot())
    base_keys = {(d, r) for d, r, _, _ in base}
    added = [x for x in target if (x[0], x[1]) not in base_keys]
    fixed = len(base) - (len(target) - len(added))
    print(f"기준선 {Path(args.baseline).name}: {len(base)}건")
    print(f"   늘어난 것 {len(added)}건 / 없어진 것 {max(0, fixed)}건")
    for d, r, n, w in added[: args.show]:
        print(f"   + 결정 {d} 경로 {r} «{n}»: {w}")
    if added:
        print("FAIL — 늘어난 끊김이 있다. VISSIM 이 시뮬레이션을 시작하지 못할 수 있다.",
              file=sys.stderr)
        return 1
    print("PASS — 기준선 대비 늘어난 끊김이 없다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
