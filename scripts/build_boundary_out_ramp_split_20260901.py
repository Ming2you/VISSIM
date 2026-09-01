"""경계 out 링크의 램프행 분할 대장 (2026-09-01).

정본은 `.inpx` 정적 경로결정의 relFlow 다(CLAUDE.md '균등 beta 결함' 절).
**relFlow 가 비어 있으면 1 이다(0 이 아니다)** — 여기서 결정적이다. 0 으로 읽으면
`linkSeq` 없이 같은 링크에 머무는 '자유 이탈' 경로가 통째로 사라진다.

  decision 1135  링크 68 pos 7.49   route2 via 10646 -> R_F_W  relFlow "" = 1
                                    route3 destLink 68 (경유 없음) = 자유  = 1
                                    route4 via 10681 -> R_F_E  = 1
  decision 1137  링크 31 pos 28.55  route1 via 10484 -> R_D_E  = 1
                                    route2 destLink 31 (경유 없음) = 자유  = 1
                                    route3 via 10480 -> R_D_W  relFlow "2 0:2" = 2

왜 자유 경로가 있나. 링크 31 은 1,959.5 m 인데 마지막 램프 분기가 pos 734.9 라
그 뒤 1,224.5 m 에 나가는 커넥터가 없다 — 끝까지 가면 망을 이탈한다. 링크 68 도
1,990.2 m 에 마지막 분기가 352.0 이라 1,638.2 m 가 남는다.

상류 귀속. SC1001 서향 3개(10119·10121·10698)가 링크 31 의 pos 1.9~2.9 에,
SC1004 서향 3개(10625·10629·10633)가 링크 68 의 pos 2.1~2.4 에 붙는다. 둘 다
결정점(28.5 · 7.5)보다 상류라 전부 이 분할을 탄다. 반면 본선 off-ramp 유입
(10479@871 · 10483@614 · 10703@351 · 10645@573 · 10682@237)은 결정점 하류라
이 분할과 무관하다 — 그래서 도시 out 링크의 분할로 쓰는 것이 맞다.

제외. `SC1004_S_out` 은 넣지 않는다 — 링크 67 만 받아야 하는데 모델에서
`N_SC1003_to_S` 가 링크 68 로도 걸려 있어 out 링크 하나가 램프 있는 링크와 없는
링크를 섞는다(2026-09-01 사용자 확인: "S_out 은 67만 있다").
"""
from __future__ import annotations
import argparse, json, math, re, sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]

# out 링크 -> (경로결정 번호, 물리 링크, {커넥터: 램프})
TARGETS = {
    "SC1001_W_out": ("1137", "31", {"10484": "R_D_E", "10480": "R_D_W"}),
    "SC1004_W_out": ("1135", "68", {"10646": "R_F_W", "10681": "R_F_E"}),
}


def parse_decision(text: str, no: str) -> list[dict[str, object]]:
    i = text.find('no="%s"' % no)
    while i >= 0:
        s = text.rfind("<vehicleRoutingDecisionStatic", 0, i)
        if s >= 0 and i - s < 400:
            e = text.find("</vehicleRoutingDecisionStatic>", i)
            block = text[s:e]
            break
        i = text.find('no="%s"' % no, i + 1)
    else:
        raise SystemExit("경로결정 %s 를 못 찾았다" % no)
    routes: list[dict[str, object]] = []
    for m in re.finditer(r"<vehicleRouteStatic\b([^>]*?)(/?)>", block):
        attrs, closed = m.group(1), m.group(2)
        rno = re.search(r'\bno="(\d+)"', attrs)
        rel = re.search(r'\brelFlow="([^"]*)"', attrs)
        raw = (rel.group(1) if rel else "").strip()
        # relFlow 빈 값 = 1. "2 0:2" 같은 구간 표기는 마지막 수치를 쓴다.
        if raw == "":
            weight = 1.0
        else:
            nums = re.findall(r"[\d.]+", raw)
            weight = float(nums[-1]) if nums else 1.0
        via = ""
        if not closed:
            tail = block[m.end():]
            stop = tail.find("</vehicleRouteStatic>")
            seq = re.findall(r'key="(\d+)"', tail[:stop])
            via = seq[0] if seq else ""
        routes.append({"no": rno.group(1) if rno else "?", "relFlow_raw": raw,
                       "weight": weight, "via": via})
    return routes


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--network", default="network/real_world_gaepo_modi/modi_eval_rw_control.inpx")
    ap.add_argument("--out", default="outputs/boundary_out_ramp_split_20260901.json")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    text = (R / a.network).read_text(encoding="utf-8", errors="replace")
    doc: dict[str, object] = {
        "schema_version": "boundary-out-ramp-split/1",
        "generated": "2026-09-01",
        "source": "%s 의 vehicleRoutingDecisionStatic relFlow" % a.network,
        "rule": "relFlow 빈 값 = 1 (0 아님). linkSeq 없는 route = 자유 이탈.",
        "excluded": {"SC1004_S_out": "링크 67 만 받아야 하는데 모델이 68 도 섞는다 — 분할 불가"},
        "links": {},
    }
    for out_link, (dec, phys, conn2ramp) in TARGETS.items():
        routes = parse_decision(text, dec)
        total = sum(float(r["weight"]) for r in routes)
        ramps: dict[str, float] = {}
        free = 0.0
        detail = []
        for r in routes:
            share = float(r["weight"]) / total
            ramp = conn2ramp.get(str(r["via"]), "")
            if ramp:
                ramps[ramp] = ramps.get(ramp, 0.0) + share
            else:
                free += share
            detail.append({"route": r["no"], "relFlow_raw": r["relFlow_raw"],
                           "weight": r["weight"], "via": r["via"] or "(없음=자유)",
                           "ramp": ramp or "free", "share": round(share, 6)})
        s = free + sum(ramps.values())
        if abs(s - 1.0) > 1.0e-9:
            raise SystemExit("%s 분할 합이 %.9f" % (out_link, s))
        # 반올림하지 않는다 — 어댑터가 합=1 을 1e-6 로 검사하는데 1/3 을 6자리로 자르면
        # 합이 0.999999 가 되어 경계에 걸린다. 질량 보존은 반올림보다 우선한다.
        doc["links"][out_link] = {
            "decision": dec, "physical_link": phys,
            "free": free,
            "ramps": {k: v for k, v in sorted(ramps.items())},
            "routes": detail,
        }

    (R / a.out).write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print("-> %s" % a.out)
    for link, spec in doc["links"].items():
        print("\n%s  (결정 %s · 물리 링크 %s)" % (link, spec["decision"], spec["physical_link"]))
        print("   자유 %.4f · %s  합 %.6f"
              % (spec["free"], " · ".join("%s %.4f" % kv for kv in spec["ramps"].items()),
                 spec["free"] + sum(spec["ramps"].values())))
        for d in spec["routes"]:
            print("      route %-3s relFlow=%-8r via %-10s -> %-6s share %.4f"
                  % (d["route"], d["relFlow_raw"], d["via"], d["ramp"], d["share"]))


if __name__ == "__main__":
    main()
