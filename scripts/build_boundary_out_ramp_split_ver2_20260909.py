# -*- coding: utf-8 -*-
"""경계 out 링크의 램프행 분할 — **Ver2 판** (2026-09-09).

왜 새로 쓰나. `build_boundary_out_ramp_split_20260901.py` 는 경로의 **첫 커넥터만** 본다
(`via = seq[0]`). Ver2 는 GUI 링크 분할로 중간 커넥터(10772·10774)가 앞에 붙어서, 그 판정이
램프행 경로를 통째로 '자유'로 오분류한다. 실측:

    Ver2 결정 1137  route3 linkSeq=[10774, 124, 10480]  -> 옛 판정 '자유', 실제 R_D_W
    Ver2 결정 1135  route2 linkSeq=[10772, 121, 10646]  -> 옛 판정 '자유', 실제 R_F_W

그 결과 옛 생성기를 Ver2 에 돌리면 `SC1001_W_out` 에서 R_D_W 가, `SC1004_W_out` 에서 R_F_W 가
사라진다. 여기서는 **linkSeq 전체**를 훑어 램프 커넥터가 어디에 있든 잡는다.

정본 규약(그대로 유지):
  * relFlow 가 비어 있으면 **1** 이다(0 이 아니다). 0 으로 읽으면 자유 이탈 경로가 사라진다.
  * "2 0:3" 같은 구간 표기는 마지막 수치를 쓴다.
  * `SC1004_S_out` 은 넣지 않는다(링크 67 만이어야 하는데 모델이 68 을 섞는다).

램프 사이 배분. 경로 가중치가 이미 램프별로 갈리므로 기본은 **경로 그대로**다.
`--measured-runs` 를 주면 그 런들의 VISSIM 링크평가(`far_measurement.link_volume_veh_h`)로
같은 램프군 안의 W/E 배분만 실측으로 덮는다(램프행 총량과 자유 몫은 경로가 정본).
계측기를 링크평가로 두는 이유는 커넥터가 짧아 5초 스캔이 통과를 놓치기 때문이다.

사용:
  python build_boundary_out_ramp_split_ver2_20260909.py \
      --network "network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx" \
      --out outputs/boundary_out_ramp_split_ver2_20260909.json \
      [--measured-runs n21_x15_nocontrol_ver2_20260907 ...]
"""
from __future__ import annotations

import argparse
import io
import json
import re
import statistics
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]

# out 링크 -> (경로결정 번호, 물리 링크, {커넥터: 램프})
TARGETS = {
    "SC1001_W_out": ("1137", "31", {"10484": "R_D_E", "10480": "R_D_W"}),
    "SC1004_W_out": ("1135", "68", {"10646": "R_F_W", "10681": "R_F_E"}),
}


def decision_block(text: str, no: str) -> str:
    i = text.find('no="%s"' % no)
    while i >= 0:
        s = text.rfind("<vehicleRoutingDecisionStatic", 0, i)
        if s >= 0 and i - s < 400:
            e = text.find("</vehicleRoutingDecisionStatic>", i)
            return text[s:e]
        i = text.find('no="%s"' % no, i + 1)
    raise SystemExit("경로결정 %s 를 못 찾았다" % no)


def routes_of(block: str) -> list[dict]:
    out = []
    for m in re.finditer(r"<vehicleRouteStatic\b([^>]*?)(/?)>", block):
        attrs, closed = m.group(1), m.group(2)
        rno = re.search(r'\bno="(\d+)"', attrs)
        rel = re.search(r'\brelFlow="([^"]*)"', attrs)
        dest = re.search(r'\bdestLink="(\d+)"', attrs)
        raw = (rel.group(1) if rel else "").strip()
        if raw == "":
            weight = 1.0                       # 빈 relFlow = 1
        else:
            nums = re.findall(r"[\d.]+", raw)
            weight = float(nums[-1]) if nums else 1.0
        seq = []
        if not closed:
            tail = block[m.end():]
            stop = tail.find("</vehicleRouteStatic>")
            seq = re.findall(r'key="(\d+)"', tail[:stop])
        out.append({"no": rno.group(1) if rno else "?", "relFlow_raw": raw,
                    "weight": weight, "dest_link": dest.group(1) if dest else "",
                    "link_seq": seq})
    return out


def measured_ramp_shares(runs: list[str], conns: dict) -> dict:
    """같은 out 링크가 먹이는 램프 커넥터들의 실측 볼륨 비율. 링크평가(150 s)를 쓴다."""
    tot = {c: [] for c in conns}
    for run in runs:
        dd = list((R / "evaluation/runs" / run).glob("decisions_*"))
        if not dd:
            continue
        for sp in sorted(dd[0].glob("state_*.json")):
            try:
                js = json.load(io.open(sp, encoding="utf-8"))
            except Exception:
                continue
            lv = (((js.get("local_observation") or {}).get("far_measurement") or {})
                  .get("link_volume_veh_h") or {})
            for c in conns:
                if c in lv:
                    tot[c].append(float(lv[c]))
    med = {c: (statistics.median(v) if v else 0.0) for c, v in tot.items()}
    s = sum(med.values())
    if s <= 0:
        return {}
    return {conns[c]: med[c] / s for c in conns}, {conns[c]: len(tot[c]) for c in conns}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--network", default="network/real_world_gaepo_modi/modi_eval_userfix Ver2.inpx")
    ap.add_argument("--out", default="outputs/boundary_out_ramp_split_ver2_20260909.json")
    ap.add_argument("--measured-runs", nargs="*", default=[])
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    text = io.open(a.network, encoding="utf-8", errors="replace").read()
    links = {}
    for name, (dno, phys, conns) in TARGETS.items():
        rs = routes_of(decision_block(text, dno))
        total = sum(r["weight"] for r in rs) or 1.0
        ramps, free = {}, 0.0
        detail = []
        for r in rs:
            hit = [c for c in r["link_seq"] if c in conns]     # 전 구간을 훑는다
            share = r["weight"] / total
            if hit:
                ramp = conns[hit[-1]]                          # 마지막 램프 커넥터가 착지
                ramps[ramp] = ramps.get(ramp, 0.0) + share
                detail.append(dict(r, resolved=ramp, share=round(share, 6)))
            else:
                free += share
                detail.append(dict(r, resolved="free", share=round(share, 6)))
        entry = {"decision": dno, "physical_link": phys,
                 "free": round(free, 6),
                 "ramps": {k: round(v, 6) for k, v in sorted(ramps.items())},
                 "routes": detail}
        if a.measured_runs and len(conns) > 1:
            got = measured_ramp_shares(a.measured_runs, conns)
            if got:
                frac, nsamp = got
                ramp_total = sum(ramps.values())
                entry["ramps"] = {k: round(ramp_total * frac.get(k, 0.0), 6) for k in sorted(ramps)}
                entry["measured_ramp_share"] = {k: round(v, 4) for k, v in frac.items()}
                entry["measured_samples"] = nsamp
                entry["measured_runs"] = a.measured_runs
        links[name] = entry
        print("%s  (결정 %s · 물리 링크 %s)" % (name, dno, phys))
        print("   자유 %.4f · %s  합 %.6f"
              % (entry["free"], " · ".join("%s %.4f" % kv for kv in entry["ramps"].items()),
                 entry["free"] + sum(entry["ramps"].values())))
        for r in detail:
            print("      route %-3s relFlow=%-10r linkSeq=%-28s -> %-8s %.4f"
                  % (r["no"], r["relFlow_raw"], ",".join(r["link_seq"]) or "-",
                     r["resolved"], r["share"]))
        if "measured_ramp_share" in entry:
            print("      실측 램프 배분: %s (표본 %s)"
                  % (entry["measured_ramp_share"], entry["measured_samples"]))

    doc = {"schema_version": "boundary-out-ramp-split/1",
           "generated": "2026-09-09",
           "network": a.network,
           "source": "Ver2 .inpx 정적 경로결정 relFlow (linkSeq 전 구간 탐색)"
                     + ((" + 링크평가 실측 램프 배분 " + ",".join(a.measured_runs)) if a.measured_runs else ""),
           "rule": "빈 relFlow = 1. 구간 표기는 마지막 수치. linkSeq 어디에든 램프 커넥터가 있으면 램프행. "
                   "옛 생성기는 seq[0] 만 봐서 Ver2 의 중간 커넥터(10772·10774) 뒤에 오는 램프를 놓친다.",
           "excluded": "SC1004_S_out — 링크 67 만이어야 하는데 모델이 68 을 섞는다",
           "links": links}
    io.open(a.out, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1))
    print("\n-> %s" % a.out)


if __name__ == "__main__":
    main()
