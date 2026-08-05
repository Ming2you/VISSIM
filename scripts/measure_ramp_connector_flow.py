# 온/오프램프 커넥터의 실측 유량을 q = (N/L)*v 로 구한다.
#
# 왜 이 스크립트가 필요한가.
#   bottleneck_links CSV 의 `count` 는 스냅샷 점유(대수)지 유량이 아니다
#   (run_real_world_stackelberg_controller.vbs:1277 `AddDictNumber linkCounts, key, 1.0`).
#   그래서 "플랜트가 온램프로 몇 대를 보내는가"를 직접 읽을 수단이 없었고,
#   모델의 ramp_arrival 이 맞는지 검증할 방법도 없었다.
#
#   커넥터 길이는 .inpx 의 <geometry><linkPolyPts><linkPolyPoint x y zOffset> 로 구한다.
#   (일반 링크의 point3D 가 아니라 이 태그다 — 예전 감사가 여기서 0 을 읽고 실패했다.)
#   길이가 있으면 밀도 k = N/L 이고 q = k*v 로 유량이 나온다. VISSIM 재실행도
#   .inpx 수정(데이터수집점 신설)도 필요 없다 — 이미 수집된 CSV 로 닫힌다.
#
# 사용:
#   python scripts/measure_ramp_connector_flow.py --run-dir evaluation/runs/<run> \
#       --run-name <name> [--t0 2700] [--network <inpx>] [--json-out out.json]
import argparse
import csv
import json
import math
import os
import statistics as st
import sys
from collections import defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_NET = os.path.join(REPO, "network", "real_world_gaepo_modi", "modi_eval_rw_control.inpx")
DEFAULT_MAPPING = os.path.join(REPO, "evaluation", "real_world_modi_control", "control_mapping.json")
DEFAULT_DETECTOR = os.path.join(
    REPO, "evaluation", "real_world_modi_control_distributed_20260728",
    "detector_local_mapping_distributed_15core_20260728.json")


def poly_len_m(link_el):
    pts = [(float(p.get("x")), float(p.get("y")), float(p.get("zOffset") or 0.0))
           for p in link_el.iter("linkPolyPoint")]
    if len(pts) < 2:
        return 0.0
    return sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def load_geometry(network_path):
    import xml.etree.ElementTree as ET
    root = ET.parse(network_path).getroot()
    out = {}
    for ln in root.iter("link"):
        no = ln.get("no")
        if no is None:
            continue
        out[str(no)] = {
            "len_m": poly_len_m(ln),
            "lanes": max(1, len(ln.findall("./lanes/lane"))),
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--run-name", required=True,
                    help="bottleneck_links_<run-name>.csv 의 <run-name>")
    ap.add_argument("--t0", type=float, default=2700.0)
    ap.add_argument("--network", default=DEFAULT_NET)
    ap.add_argument("--mapping", default=DEFAULT_MAPPING)
    ap.add_argument("--detector-mapping", default=DEFAULT_DETECTOR)
    ap.add_argument("--json-out", default="")
    args = ap.parse_args()

    csv_path = os.path.join(args.run_dir, f"bottleneck_links_{args.run_name}.csv")
    if not os.path.exists(csv_path):
        print(f"ERROR: not found {csv_path}")
        return 2

    geom = load_geometry(args.network)
    mapping = json.load(open(args.mapping, encoding="utf-8"))
    meters = {str(m["connector"]): m for m in mapping["ramp_meters"]}
    detector = json.load(open(args.detector_mapping, encoding="utf-8"))
    offramp = {}
    for key, entries in (detector.get("off_ramp_connectors") or {}).items():
        for e in entries:
            offramp[str(e["connector"])] = key

    rows = [r for r in csv.DictReader(open(csv_path, newline="", encoding="utf-8"))
            if float(r["sim_sec"]) >= args.t0]
    samples = defaultdict(list)
    for r in rows:
        link = r["link"]
        if link not in meters and link not in offramp:
            continue
        length_km = geom.get(link, {}).get("len_m", 0.0) / 1000.0
        if length_km <= 0.0:
            continue
        n = float(r["count"])
        v = float(r["mean_speed_kph"])
        samples[link].append((n, v, n / length_km * v))

    if not samples:
        print("ERROR: 램프 커넥터 표본이 없다 (기하 0 또는 링크 불일치)")
        return 3

    print(f"run={args.run_name}  t>={args.t0:.0f}  표본행={len(rows)}")
    print(f"{'커넥터':<9}{'구분':<9}{'그룹':<8}{'L(m)':>8}{'N중앙':>7}{'v중앙':>8}{'q중앙':>9}{'q평균':>9}")
    on_by_group = defaultdict(float)
    off_by_group = defaultdict(float)
    per_connector = {}
    for link in sorted(samples, key=int):
        ns = [a for a, _, _ in samples[link]]
        vs = [b for _, b, _ in samples[link]]
        qs = [c for _, _, c in samples[link]]
        is_on = link in meters
        group = meters[link]["model_ramp_key"] if is_on else offramp[link]
        (on_by_group if is_on else off_by_group)[group] += st.median(qs)
        per_connector[link] = {
            "kind": "on_ramp" if is_on else "off_ramp", "group": group,
            "length_m": geom[link]["len_m"], "lanes": geom[link]["lanes"],
            "count_median": st.median(ns), "speed_kph_median": st.median(vs),
            "q_vph_median": st.median(qs), "q_vph_mean": st.mean(qs),
        }
        print(f"{link:<9}{'온램프' if is_on else '오프램프':<9}{group:<8}"
              f"{geom[link]['len_m']:>8.1f}{st.median(ns):>7.1f}{st.median(vs):>8.1f}"
              f"{st.median(qs):>9.0f}{st.mean(qs):>9.0f}")

    print()
    print(f"{'모델 그룹':<10}{'온램프 유입':>12}{'오프램프 유출':>14}{'순':>10}")
    for g in sorted(on_by_group | off_by_group):
        pass
    groups = sorted({*on_by_group} | {k.replace("OR_", "R_") for k in off_by_group})
    for g in groups:
        on = on_by_group.get(g, 0.0)
        off = off_by_group.get(g.replace("R_", "OR_"), 0.0)
        print(f"{g:<10}{on:>12.0f}{off:>14.0f}{on - off:>10.0f}")
    tot_on = sum(on_by_group.values())
    tot_off = sum(off_by_group.values())
    print(f"{'합계':<10}{tot_on:>12.0f}{tot_off:>14.0f}{tot_on - tot_off:>10.0f}")

    if args.json_out:
        # 시각별 그룹 유량도 함께 낸다. 모델 forecast 검증은 같은 시각의 ramp_counts 와
        # 대조해야 한다 — 스냅샷 count 대 구간 중앙값 q 를 비교하면 워밍업 경계에서 크게 어긋난다.
        series = defaultdict(lambda: defaultdict(float))
        for r in rows:
            link = r["link"]
            if link not in meters:
                continue
            length_km = geom.get(link, {}).get("len_m", 0.0) / 1000.0
            if length_km <= 0.0:
                continue
            series[r["sim_sec"]][meters[link]["model_ramp_key"]] += (
                float(r["count"]) / length_km * float(r["mean_speed_kph"]))
        payload = {
            "run_name": args.run_name, "t0": args.t0, "csv": csv_path,
            "per_connector": per_connector,
            "on_ramp_vph_by_group": dict(on_by_group),
            "off_ramp_vph_by_group": dict(off_by_group),
            "on_ramp_vph_total": tot_on, "off_ramp_vph_total": tot_off,
            "on_ramp_vph_by_group_at_time": {k: dict(v) for k, v in sorted(series.items(), key=lambda kv: float(kv[0]))},
        }
        os.makedirs(os.path.dirname(os.path.abspath(args.json_out)) or ".", exist_ok=True)
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=1)
        print(f"\nJSON={args.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
