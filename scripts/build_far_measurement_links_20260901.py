"""far 저수지 방류율을 재는 **측정 지점 대장**을 만든다 (2026-09-01).

왜 커넥터인가. VISSIM 링크평가의 Volume 은 요소 전체의 Edie 유량[veh/h]이다. 커넥터는
짧아서 모든 차량이 구간 안에 완주하므로 Volume x interval / 3600 이 **정확히 통과대수**가
된다. 긴 본선 링크에서는 그렇지 않다(구간 평균이라 출구 유량과 다르다).

세 저수지의 방류 지점:
  urban  보호망을 나가는 회전 — pn_boundary_turns 의 class in {outflow, external}
         (CLAUDE.md '보호망 경계 판정 정본': 유출 34 · 외부통과 8 + 비통제 2)
  fw     본선 체인의 하류 끝에서 나가는 커넥터
  ramp_* 램프미터 커넥터 8개 (install_real_world_freeway_controls.vbs:440-447)

산출은 러너 VBS 가 읽는 CSV 한 장이다. 링크 번호를 코드에 박지 않는다.
"""
from __future__ import annotations
import argparse, csv, json, sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / "scripts"))
from audit_plant_wiring_20260831 import parse_network  # noqa: E402

RAMP_CONN = {
    "R_D_W": ["10480", "10482"],
    "R_F_W": ["10646", "10644"],
    "R_F_E": ["10639", "10681"],
    "R_D_E": ["10490", "10484"],
}
CHAIN = {"FW_E": ["74", "10699", "2", "10702", "24"], "FW_W": ["26"]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--network", default="network/real_world_gaepo_modi/modi_eval_rw_control.inpx")
    ap.add_argument("--out", default="evaluation/real_world_modi_inventory/far_measurement_links_20260901.csv")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    links, conns, _heads = parse_network(R / a.network)
    turns = json.loads((R / "outputs/pn_boundary_turns_v1_20260819.json").read_text(encoding="utf-8"))["turns"]

    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def add(reservoir: str, role: str, conn: str, note: str) -> None:
        # dedup 은 (저수지, 링크) 단위다. 전역 dedup 은 틀린다 — on-ramp 미터 커넥터
        # 10482 · 10490 · 10639 은 **보호망 유출인 동시에 램프 합류**다. 한 저수지가
        # 먼저 집으면 다른 쪽이 통째로 사라진다(첫 판에서 램프 셋이 2->1개가 됐다).
        c = str(conn)
        if (reservoir, c) in seen:
            return
        rec = conns.get(c) or links.get(c) or {}
        seen.add((reservoir, c))
        rows.append({"reservoir": reservoir, "role": role, "link": c,
                     "from_link": rec.get("from_link", ""), "to_link": rec.get("to_link", ""),
                     "length_m": "%.1f" % float(rec.get("length_m", 0.0)), "note": note})

    # urban: 보호망 밖으로 나가는 회전
    for t in turns:
        if str(t.get("class")) in ("outflow", "external"):
            add("urban", "outflow", str(t["connector"]),
                "%s %s->%s class=%s" % (t.get("sc", ""), t.get("from_link"), t.get("to_link"), t.get("class")))

    # freeway: 체인 하류 끝에서 체인 밖으로 나가는 커넥터
    fw_all = {x for v in CHAIN.values() for x in v}
    ramp_all = {c for v in RAMP_CONN.values() for c in v}
    #
    # 본선은 **출구 커넥터가 없다** — 체인 하류 끝(FW_W=26, FW_E=24)에서 차량이 망을 떠난다.
    # 링크평가 Volume 은 요소의 공간평균이라 10.7 km 본선에서는 출구 유량이 아니다.
    # 그래서 본선만 방식이 다르다: 그 링크에서의 **이탈 계수**를 쓴다(off-ramp 로 빠진 것 +
    # 망을 떠난 것). VBS 의 winDepart 가 5초 스캔 전이로 이미 그걸 세고, 본선 링크는
    # 체류가 5초보다 훨씬 길어 표본 누락이 없다(짧은 커넥터에서는 반대라 링크평가를 쓴다).
    for name, chain in CHAIN.items():
        tail = chain[-1]
        rec = links.get(tail, {})
        add("freeway", "drain_departures", tail,
            "%s 체인 하류 끝. 링크평가 아님 — 이탈 계수(link_departures_window)" % name)
        for c, crec in conns.items():
            if c in ramp_all:
                continue
            if crec.get("from_link") == tail and crec.get("to_link") not in fw_all:
                add("freeway_offramp", "exit", c,
                    "%s tail=%s -> %s (참고용, freeway 이탈에 이미 포함)" % (name, tail, crec.get("to_link")))

    # ramp: 미터 커넥터
    for ramp, cs in RAMP_CONN.items():
        for c in cs:
            add("ramp_" + ramp, "merge", c, "ramp meter connector")

    out = R / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["reservoir", "role", "link", "from_link", "to_link", "length_m", "note"])
        w.writeheader()
        w.writerows(rows)

    from collections import Counter
    cnt = Counter(r["reservoir"] for r in rows)
    print("측정 지점 %d개 -> %s" % (len(rows), a.out))
    for k, v in sorted(cnt.items()):
        lens = [float(r["length_m"]) for r in rows if r["reservoir"] == k]
        print("  %-12s %3d개  길이 %.1f~%.1f m" % (k, v, min(lens), max(lens)))
    long = [r for r in rows if float(r["length_m"]) > 150.0 and r["role"] != "drain_departures"]
    if long:
        print("\n주의: 150m 초과 측정지점 %d개 — Volume 이 구간평균이라 통과대수와 어긋날 수 있다" % len(long))
        for r in long[:8]:
            print("   %s %s %.0fm  %s" % (r["reservoir"], r["link"], float(r["length_m"]), r["note"]))


if __name__ == "__main__":
    main()
