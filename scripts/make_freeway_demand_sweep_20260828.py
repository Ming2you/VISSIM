# -*- coding: utf-8 -*-
"""본선 수요 배율 sweep 망을 만든다. 원본에서 **본선 진입 둘만** 곱한다.

왜 (2026-08-28).

수요를 x1.4 까지 올려도 본선이 용량의 78% 라 붕괴가 안 온다(밀도 중앙 12.25, 임계 21.25).
붕괴 영역에서 VSL·램프미터링을 검정하려면 더 올려야 하고, FD 혼잡부 표본도 지금 1.7%뿐이라
그 구간을 채워야 한다.

**한 변수만 바꾼다.** 기존 fw12/fw14 망은 본선 수요와 온램프 relFlow 를 **같이** 바꿨다
(원본 5/3/2/2 -> ramp1 11.07/2.21/6.6/4.4 -> ramp2 24.9/4.98/14.4/9.6). 두 변수라 배율 효과를
못 가른다. 여기서는 `경부_NB`(link 26) · `경부_EB`(link 74) 의 `timeIntervalVehVolume` 만 곱하고
나머지는 원본 바이트 그대로 둔다.

유입을 **신설하지 않는다** — 기존 vehicleInput 의 volume 값만 바꾼다(사용자 지시).
원본 inpx 는 덮지 않는다(CLAUDE.md).

참고. 원본 link 26 구간유량은 [3080, 4400, 4620, 3960, 3080, 2200] veh/h 이고 적합 FD 의
4차로 용량은 6218 veh/h 다. 그래서 x1.35 부터 첨두 구간이 용량을 넘기 시작하고, 그 위에서는
VISSIM 이 다 못 넣어 진입 큐가 생긴다 — 그것이 곧 붕괴의 관측이다.

사용: python scripts/make_freeway_demand_sweep_20260828.py --mults 1.6 1.7 1.8 1.9 2.0 2.1 2.2 2.3 2.4
"""
import argparse
import json
import re
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
MAINLINE_LINKS = ("26", "74")          # 경부_NB · 경부_EB


def scale_network(text: str, links, mult: float):
    """지정 link 의 vehicleInput volume 만 곱한다. 그 외 바이트는 안 건드린다."""
    out = []
    pos = 0
    changed = []
    for m in re.finditer(r"<vehicleInput ([^>]*)>(.*?)</vehicleInput>", text, re.S):
        lk = re.search(r'link="([^"]+)"', m.group(1))
        if not lk or lk.group(1) not in links:
            continue
        body = m.group(2)
        vols_before = [float(x) for x in re.findall(r'volume="([\d.]+)"', body)]

        def repl(mm):
            return 'volume="%s"' % ("%.6f" % (float(mm.group(1)) * mult)).rstrip("0").rstrip(".")

        new_body = re.sub(r'volume="([\d.]+)"', repl, body)
        out.append(text[pos:m.start(2)])
        out.append(new_body)
        pos = m.end(2)
        changed.append({"link": lk.group(1),
                        "volumes_before": vols_before,
                        "volumes_after": [round(v * mult, 4) for v in vols_before]})
    out.append(text[pos:])
    return "".join(out), changed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="network/real_world_gaepo_modi/modi_eval_userfix_20260814e.inpx")
    ap.add_argument("--mults", nargs="+", type=float,
                    default=[1.6, 1.7, 1.8, 1.9, 2.0, 2.1, 2.2, 2.3, 2.4])
    ap.add_argument("--links", nargs="+", default=list(MAINLINE_LINKS))
    ap.add_argument("--tag", default="fwsweep")
    ap.add_argument("--manifest", default="outputs/freeway_demand_sweep_20260828.json")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    src = R / args.source
    if not src.is_file():
        print("!! 원본 없음: %s" % src)
        return 1
    raw = src.read_bytes()
    text = raw.decode("utf-8", errors="strict")
    print("원본 %s · %d 바이트" % (src.name, len(raw)))

    made = []
    for mult in args.mults:
        name = "%s_%s_x%s.inpx" % (src.stem, args.tag, ("%.1f" % mult).replace(".", ""))
        dst = src.with_name(name)
        if dst.resolve() == src.resolve():
            print("!! 원본을 덮으려 한다 — 중단"); return 1
        new_text, changed = scale_network(text, set(args.links), mult)
        if not changed:
            print("!! x%.1f: 대상 link 를 못 찾았다" % mult); return 1
        dst.write_bytes(new_text.encode("utf-8"))
        # 되읽어 검증
        chk = dst.read_text(encoding="utf-8", errors="strict")
        ok = True
        for c in changed:
            m = re.search(r'<vehicleInput [^>]*link="%s"[^>]*>(.*?)</vehicleInput>' % re.escape(c["link"]),
                          chk, re.S)
            got = [round(float(x), 4) for x in re.findall(r'volume="([\d.]+)"', m.group(1))] if m else []
            if got != c["volumes_after"]:
                ok = False
                print("!! x%.1f link %s 검증 실패: %s != %s" % (mult, c["link"], got, c["volumes_after"]))
        # 대상 외가 안 바뀌었는지 — 줄 단위로 직접 센다.
        # (블록을 정규식으로 도려내 비교하는 방식은 2026-08-28 에 오탐을 냈다. 파일은 멀쩡했다.)
        la, lb = text.splitlines(), chk.splitlines()
        if len(la) != len(lb):
            ok = False
            print("!! x%.1f: 줄 수가 다르다 %d != %d" % (mult, len(la), len(lb)))
        else:
            diff_idx = [i for i, (x, y) in enumerate(zip(la, lb)) if x != y]
            expect = sum(len(c["volumes_before"]) for c in changed)
            bad_lines = [i for i in diff_idx if "timeIntervalVehVolume" not in la[i]]
            if bad_lines:
                ok = False
                print("!! x%.1f: volume 이 아닌 줄이 바뀌었다 %d개 — 예 %s"
                      % (mult, len(bad_lines), la[bad_lines[0]].strip()[:90]))
            elif len(diff_idx) != expect:
                ok = False
                print("!! x%.1f: 바뀐 volume 줄 %d개, 기대 %d개" % (mult, len(diff_idx), expect))
        peak = max(max(c["volumes_after"]) for c in changed)
        made.append({"mult": mult, "network": str(dst.relative_to(R)).replace("\\", "/"),
                     "bytes": dst.stat().st_size, "verified": ok,
                     "peak_volume_veh_h": peak, "changed": changed})
        print("  x%-4.1f -> %-58s %s · 첨두 %.0f veh/h%s"
              % (mult, dst.name, "OK" if ok else "**실패**", peak,
                 "  (4차로 용량 6218 초과)" if peak > 6218 else ""))

    doc = {
        "schema_version": "freeway-demand-sweep/1",
        "generated": "2026-08-28",
        "why": "x1.4 에서도 본선이 용량의 78% 라 붕괴가 없다. 붕괴 영역에서 VSL·램프미터링을 "
               "검정하고 FD 혼잡부 표본(현재 1.7%)을 채우려면 더 올려야 한다.",
        "single_variable": "본선 vehicleInput volume 만 곱한다 (link %s). 램프 relFlow 는 원본 그대로." % ", ".join(args.links),
        "source": args.source,
        "fd_reference": {"model": "V=v_free*exp(-(1/a)(rho/rho_crit)^a)",
                         "fit_20260828": {"v_free": 113.0, "rho_crit": 21.25, "a": 2.300,
                                          "capacity_veh_h_4lane": 6218.3}},
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
