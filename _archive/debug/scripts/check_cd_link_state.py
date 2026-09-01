# C-D(collector-distributor) 링크의 혼잡 상태를 잰다.
#
# 왜 필요한가.
#   램프 미터 커넥터는 짧아서 물리 상한에 포화한다(실측 10646 k=94.4, 10638 k=95.4).
#   실제 대기행렬은 그 뒤 C-D 링크(31/32/68/69/70/71)에 쌓이는데 이 링크들은
#   observable_links 에 대부분 없어 관측 목적함수에도, 커넥터 점유에도 안 잡힌다.
#   램프 수요를 키우거나 route 를 바꾼 뒤에는 여기가 먼저 터진다 — 그래서 따로 본다.
#
# 링크 70 이 특히 중요하다. 2차로 338 m 로 가장 짧은데 오프램프 2개(10638/10643)와
# 링크 69 유입을 함께 받고, 온램프 10639 와 링크 71 출구로 갈린다.
#
# 사용:
#   python scripts/check_cd_link_state.py --case "라벨:run_dir:run_name" [--case ...] [--t0 2700]
import argparse
import csv
import io
import json
import math
import os
import statistics as st
import sys
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_NET = os.path.join(REPO, "network", "real_world_gaepo_modi", "modi_eval_rw_control.inpx")
CD_LINKS = {
    "31": "D측 C-D (오프램프 2 + 도시부 4)",
    "32": "D측 C-D (오프램프 2 + 자체 input 1102)",
    "68": "F측 C-D (오프램프 2 + 도시부 3, 출구는 온램프뿐)",
    "69": "F측 기점 (input 1101, 유입 커넥터 0)",
    "70": "F측 C-D (오프램프 2 + 링크69, 2차로 최단)",
    "71": "F측 방류 (SC 1004 신호두)",
}
JAM_K = 130.0  # veh/km/lane 대략적 jam density


def geometry(path):
    import xml.etree.ElementTree as ET
    root = ET.parse(path).getroot()
    out = {}
    for ln in root.iter("link"):
        no = ln.get("no")
        if no not in CD_LINKS:
            continue
        pts = [(float(p.get("x")), float(p.get("y"))) for p in ln.iter("linkPolyPoint")]
        length = sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)) if len(pts) > 1 else 0.0
        out[no] = {"len_m": length, "lanes": max(1, len(ln.findall("./lanes/lane")))}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", action="append", required=True, help="라벨:run_dir:run_name")
    ap.add_argument("--t0", type=float, default=2700.0)
    ap.add_argument("--network", default=DEFAULT_NET)
    ap.add_argument("--json-out", default="")
    args = ap.parse_args()

    geom = geometry(args.network)
    print("=== C-D 링크 제원")
    for lk in sorted(CD_LINKS, key=int):
        g = geom.get(lk, {})
        print(f"   링크 {lk:<4} {g.get('lanes','?')}차로 {g.get('len_m',0):7.0f} m   {CD_LINKS[lk]}")
    print()

    payload = {}
    for spec in args.case:
        parts = spec.split(":", 2)
        if len(parts) != 3:
            print(f"SKIP 형식 오류: {spec}")
            continue
        label, run_dir, run_name = parts
        path = os.path.join(run_dir, f"bottleneck_links_{run_name}.csv")
        if not os.path.exists(path):
            print(f"SKIP {label}: {path} 없음")
            continue
        per = defaultdict(lambda: defaultdict(list))
        for r in csv.DictReader(open(path, newline="", encoding="utf-8")):
            if float(r["sim_sec"]) < args.t0 or r["link"] not in CD_LINKS:
                continue
            per[r["link"]]["n"].append(float(r["count"]))
            per[r["link"]]["v"].append(float(r["mean_speed_kph"]))
            per[r["link"]]["s"].append(float(r["stopped_count"]))
        print(f"########## {label}   ({run_name})")
        print(f"   {'링크':<5}{'N중앙':>7}{'N최대':>7}{'v중앙':>8}{'v최소':>8}{'k/ln':>8}{'k/jam':>8}{'정지율':>8}   판정")
        rows = {}
        for lk in sorted(CD_LINKS, key=int):
            d = per.get(lk)
            if not d:
                continue
            g = geom.get(lk, {"len_m": 0.0, "lanes": 1})
            lkm = g["len_m"] / 1000.0
            k = st.median(d["n"]) / lkm / g["lanes"] if lkm > 0 else 0.0
            ratio = k / JAM_K
            stopped = 100.0 * st.median(d["s"]) / max(st.median(d["n"]), 1e-9)
            if ratio >= 0.60:
                verdict = "*** 정체"
            elif ratio >= 0.35:
                verdict = "혼잡"
            else:
                verdict = "양호"
            print(f"   {lk:<5}{st.median(d['n']):>7.1f}{max(d['n']):>7.0f}{st.median(d['v']):>8.1f}"
                  f"{min(d['v']):>8.1f}{k:>8.1f}{ratio:>8.2f}{stopped:>7.0f}%   {verdict}")
            rows[lk] = {"n_median": st.median(d["n"]), "n_max": max(d["n"]),
                        "v_median": st.median(d["v"]), "v_min": min(d["v"]),
                        "k_per_lane": k, "k_over_jam": ratio, "stopped_pct": stopped}
        payload[label] = rows
        print()

    if args.json_out:
        os.makedirs(os.path.dirname(os.path.abspath(args.json_out)) or ".", exist_ok=True)
        json.dump(payload, open(args.json_out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"JSON={args.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
