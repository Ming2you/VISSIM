# -*- coding: utf-8 -*-
"""망에 `110 km/h` 희망속도 분포를 추가한다. 원본은 안 건드리고 새 파일로 낸다.

왜 (2026-08-31).

VSL 격자를 10 단위로 넓히려다 런이 두 번 죽었다 —
`ERROR=VSL_COM_WRITE_READBACK dsd=40 speed=110`. **망에 110 km/h 분포가 없기 때문이다.**

    modi_eval_userfix_20260814e.inpx 의 차량 희망속도 분포
        50 · 60 · 70 · 80 · 85 · 90 · 100 · 120 · 130 · 140

`DesSpeedDecision` 은 임의 숫자가 아니라 **정의된 분포를 번호로 지정**하는 것이라 없는 값은
VISSIM 이 거부한다. 러너의 `RW_ALLOWED_VSL_SPEEDS` 는 정책 목록이 아니라 **망 자산의 열거**였고,
기존 값 "50,60,70,80,90,100,115,120" 은 이미 망과 어긋나 있었다(115 분포도 없다). 모델이
[80,100,120] 만 내던 동안 드러나지 않았을 뿐이다.

왜 110 이 필요한가. 실패한 런(canon_mergefix_x18)에서 모델이 고른 값은
70×1 · 80×6 · 100×4 · **110×19** · 120×44 였다 — 110 이 26% 다. 100 과 120 사이 간격이
20 kph(17%)로 유일하게 크고, 모델이 그 자리를 실제로 원한다.

무엇을 만드나.

    <desSpeedDistribution no="110" name="110 km/h"> 를 100 과 120 분포의 **중간 보간**으로.
    분포는 이름값이 아니라 실제 속도의 누적분포다 — "100 km/h" 의 중앙이 약 107,
    "120" 이 약 128 이므로 110 도 그 가족의 형태를 따라야 한다.

        fx     100분포   120분포   -> 110(보간)
        0.00     88       85         86.5
        0.03     95      105        100.0
        0.10    100      110        105.0
        0.69    110      125        117.5     (0.70 대 0.68 의 중간)
        0.91    120      140        130.0
        1.00    130      155        142.5

**추가는 거동상 불활성이다** — 어떤 vehicleInput·route·DSD 도 이 분포를 참조하지 않는다.
컨트롤러가 런타임에 COM 으로 지정할 때만 쓰인다. 그래서 이 망의 무제어 기준선은 그대로 유효하다.
원본 inpx 는 덮지 않는다(CLAUDE.md).

사용:
  python scripts/add_desspeed_110_20260831.py --networks <inpx> [<inpx> ...]
"""
import argparse
import json
import re
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent

NEW_NO = "110"
NEW_BLOCK = (
    '<desSpeedDistribution name="110 km/h" no="110">\n'
    '\t\t\t<speedDistrDatPts>\n'
    '\t\t\t\t<speedDistributionDataPoint fx="0" x="86.5" />\n'
    '\t\t\t\t<speedDistributionDataPoint fx="0.03" x="100" />\n'
    '\t\t\t\t<speedDistributionDataPoint fx="0.1" x="105" />\n'
    '\t\t\t\t<speedDistributionDataPoint fx="0.69" x="117.5" />\n'
    '\t\t\t\t<speedDistributionDataPoint fx="0.91" x="130" />\n'
    '\t\t\t\t<speedDistributionDataPoint fx="1" x="142.5" />\n'
    '\t\t\t</speedDistrDatPts>\n'
    '\t\t</desSpeedDistribution>\n\t\t'
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--networks", nargs="+", required=True)
    ap.add_argument("--suffix", default="_dsd110")
    ap.add_argument("--manifest", default="outputs/desspeed_110_20260831.json")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    made = []
    for rel in args.networks:
        src = R / rel
        if not src.is_file():
            print("!! 없음: %s" % rel)
            return 1
        text = src.read_text(encoding="utf-8")
        if re.search(r'<desSpeedDistribution[^>]*\bno="%s"' % NEW_NO, text):
            print("!! %s 에 이미 no=110 이 있다 — 건너뜀" % src.name)
            continue

        # 120 분포 **바로 앞**에 끼운다 (번호 순서 유지).
        anchor = re.search(r'<desSpeedDistribution\s+[^>]*\bno="120"[^>]*>', text)
        if not anchor:
            print("!! %s: no=120 분포를 못 찾았다" % src.name)
            return 1
        new_text = text[:anchor.start()] + NEW_BLOCK + text[anchor.start():]

        dst = src.with_name(src.stem + args.suffix + src.suffix)
        if dst.resolve() == src.resolve():
            print("!! 원본을 덮으려 한다 — 중단")
            return 1
        dst.write_text(new_text, encoding="utf-8")

        # 검증: 줄 단위로 추가분만 늘었는지, 그 줄이 전부 분포 정의인지
        a = text.splitlines()
        b = dst.read_text(encoding="utf-8").splitlines()
        added = len(b) - len(a)
        ok = True
        if added != NEW_BLOCK.count("\n"):
            ok = False
            print("!! %s: 줄 증가 %d, 기대 %d" % (dst.name, added, NEW_BLOCK.count("\n")))
        # 삽입 지점 앞뒤가 동일한지
        i = anchor.start()
        pre_lines = text[:i].count("\n")
        if a[:pre_lines] != b[:pre_lines]:
            ok = False
            print("!! %s: 삽입 지점 앞이 바뀌었다" % dst.name)
        if a[pre_lines:] != b[pre_lines + added:]:
            ok = False
            print("!! %s: 삽입 지점 뒤가 바뀌었다" % dst.name)
        # 분포 개수
        n_before = len(re.findall(r"<desSpeedDistribution\s", text))
        n_after = len(re.findall(r"<desSpeedDistribution\s", new_text))
        if n_after != n_before + 1:
            ok = False
            print("!! %s: 분포 개수 %d -> %d" % (dst.name, n_before, n_after))

        made.append({"source": rel, "output": str(dst.relative_to(R)).replace("\\", "/"),
                     "bytes": dst.stat().st_size, "lines_added": added,
                     "distributions": [n_before, n_after], "verified": ok})
        print("  %-58s %s · 분포 %d -> %d · +%d줄"
              % (dst.name, "OK" if ok else "**실패**", n_before, n_after, added))

    doc = {
        "schema_version": "desspeed-110/1",
        "generated": "2026-08-31",
        "why": "VSL 격자를 10 단위로 넓히려면 110 km/h 분포가 필요한데 망에 없어 "
               "VSL_COM_WRITE_READBACK 으로 런이 두 번 죽었다. 실패 런에서 모델이 110 을 26% 골랐다.",
        "distribution": {"no": 110, "name": "110 km/h",
                         "points": [[0, 86.5], [0.03, 100], [0.1, 105],
                                    [0.69, 117.5], [0.91, 130], [1, 142.5]],
                         "method": "100 분포와 120 분포의 중간 보간"},
        "inert": "어떤 vehicleInput·route·DSD 도 이 분포를 참조하지 않는다. 컨트롤러가 런타임 "
                 "COM 으로 지정할 때만 쓰이므로 무제어 기준선은 그대로 유효하다.",
        "networks": made,
    }
    (R / args.manifest).write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    bad = [m for m in made if not m["verified"]]
    print()
    print("망 %d개 생성 · 검증 실패 %d개" % (len(made), len(bad)))
    print("-> %s" % args.manifest)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
