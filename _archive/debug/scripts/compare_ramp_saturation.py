# 수요 수준별로 (1) 온램프 포화도와 (2) 합류 세그먼트 병목화를 함께 비교한다.
#
# 왜 필요한가.
#   ramp metering 이 의미를 가지려면 두 조건이 동시에 있어야 한다.
#     (a) 램프가 미터 용량에 근접 = 조일 여지가 있다
#     (b) 그 램프의 합류 세그먼트가 실제 병목 = 조여서 구할 게 있다
#   2026-08-04 기준선(mixed_critical, urban 1.45)에서는 램프가 용량의 62 % 였고
#   네 합류 중 FW_W seg4(R_F_W) 하나만 capdrop 74.7 % 였다. 나머지 셋은 합류 지점이
#   이미 자유류(FW_E seg5 는 초임계 0 %)라 조여도 개선할 병목이 없다.
#   이 스크립트는 "네 합류가 전부 병목이 되는 최소 urban 수요"를 찾기 위한 것이다.
#
# 사용:
#   python scripts/compare_ramp_saturation.py \
#       --case "기준:evaluation/runs/g6_v6_newdemand_20260804:v6_c00_anchor_seed13" \
#       --case "urban1.90:evaluation/runs/rampsat_probe_20260804:rampsat_p1_urban190" \
#       [--t0 2700]
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
sys.path.insert(0, os.path.join(REPO, "scripts"))
from measure_ramp_connector_flow import load_geometry  # noqa: E402

DEFAULT_NET = os.path.join(REPO, "network", "real_world_gaepo_modi", "modi_eval_rw_control.inpx")
DEFAULT_MAPPING = os.path.join(REPO, "evaluation", "real_world_modi_control", "control_mapping.json")


def fd_params(calibration_path):
    """rho_crit / v_free / a 를 캘리브레이션에서 읽는다. 없으면 v4 재적합값."""
    try:
        c = json.load(open(calibration_path, encoding="utf-8"))
        net = c["operational"]["network"]
        return (float(net["rho_crit_veh_km_lane"]), float(net["v_free_kph"]),
                float(net["desired_speed_shape_a"]))
    except Exception:
        return 28.925358, 133.805727, 1.2443215


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", action="append", required=True,
                    help="label:run_dir:run_name 형식. 여러 번 지정")
    ap.add_argument("--t0", type=float, default=2700.0)
    ap.add_argument("--network", default=DEFAULT_NET)
    ap.add_argument("--mapping", default=DEFAULT_MAPPING)
    ap.add_argument("--calibration", default=os.path.join(
        REPO, "evaluation", "calibration", "real_world_modi_control_v4_newdemand_20260804.json"))
    ap.add_argument("--capdrop-frac", type=float, default=0.95,
                    help="flow < frac*q_cap 이면 capacity drop 으로 본다")
    args = ap.parse_args()

    rc, vf, a = fd_params(args.calibration)
    q_cap = rc * vf * math.exp(-(1.0 / a) * 1.0)
    geom = load_geometry(args.network)
    mapping = json.load(open(args.mapping, encoding="utf-8"))
    meters = {str(m["connector"]): m for m in mapping["ramp_meters"]}
    merge_of = {}
    cap_of_group = defaultdict(float)
    for m in mapping["ramp_meters"]:
        merge_of.setdefault((m["to_model_link"], int(m["to_model_segment_index"])), set()).add(
            m["model_ramp_key"])
        cap_of_group[m["model_ramp_key"]] += float(m["capacity_vph"])

    print(f"rho_crit={rc:.2f}  v_free={vf:.1f}  a={a:.4f}  ->  q_cap={q_cap:.0f} veh/h/lane")
    print(f"capdrop 기준: rho>rho_crit 이면서 flow < {args.capdrop_frac:.2f}*q_cap")
    print()

    summary = []
    for spec in args.case:
        parts = spec.split(":", 2)
        if len(parts) != 3:
            print(f"SKIP 형식 오류: {spec}")
            continue
        label, run_dir, run_name = parts
        links_csv = os.path.join(run_dir, f"bottleneck_links_{run_name}.csv")
        segs_csv = os.path.join(run_dir, f"bottleneck_segments_{run_name}.csv")
        if not (os.path.exists(links_csv) and os.path.exists(segs_csv)):
            print(f"SKIP {label}: CSV 없음 ({run_name})")
            continue

        # (1) 램프 그룹 유량
        gq = defaultdict(list)
        for r in csv.DictReader(open(links_csv, newline="", encoding="utf-8")):
            if float(r["sim_sec"]) < args.t0:
                continue
            link = r["link"]
            if link not in meters:
                continue
            L_km = geom.get(link, {}).get("len_m", 0.0) / 1000.0
            if L_km <= 0:
                continue
            gq[meters[link]["model_ramp_key"]].append(
                (r["sim_sec"], float(r["count"]) / L_km * float(r["mean_speed_kph"])))
        group_q = {}
        for g, rows in gq.items():
            per_t = defaultdict(float)
            for t, q in rows:
                per_t[t] += q
            group_q[g] = st.median(per_t.values())

        # (2) 합류 세그먼트 병목화
        seg = defaultdict(list)
        for r in csv.DictReader(open(segs_csv, newline="", encoding="utf-8")):
            if float(r["sim_sec"]) < args.t0:
                continue
            seg[(r["model_link"], int(r["segment_index"]))].append(
                (float(r["density_veh_km_lane"]), float(r["mean_speed_kph"])))
        merge_stat = {}
        for key, groups in merge_of.items():
            vv = seg.get(key)
            if not vv:
                continue
            drop = sum(1 for d, s in vv if d > rc and d * s < args.capdrop_frac * q_cap)
            over = sum(1 for d, s in vv if d > rc)
            merge_stat[key] = (100.0 * over / len(vv), 100.0 * drop / len(vv),
                               st.median([d for d, _ in vv]), sorted(groups))

        print(f"########## {label}   ({run_name})")
        print(f"  {'그룹':<9}{'q(veh/h)':>10}{'미터cap':>9}{'q/cap':>8}   합류세그  초임계%  capdrop%  rho중앙")
        n_ok = 0
        for g in sorted(cap_of_group):
            q = group_q.get(g, 0.0)
            cap = cap_of_group[g]
            key = next((k for k, v in merge_of.items() if g in v), None)
            ms = merge_stat.get(key)
            if ms:
                over, drop, rho_med, _ = ms
                bad = drop >= 30.0
                n_ok += 1 if (bad and q / cap >= 0.80) else 0
                print(f"  {g:<9}{q:>10.0f}{cap:>9.0f}{q/cap:>8.2f}   "
                      f"{key[0]} s{key[1]}  {over:>7.1f}  {drop:>8.1f}  {rho_med:>7.1f}"
                      f"{'   <= 대상' if (bad and q/cap >= 0.80) else ''}")
            else:
                print(f"  {g:<9}{q:>10.0f}{cap:>9.0f}{q/cap:>8.2f}   (합류 세그 없음)")
        tq = sum(group_q.values())
        tc = sum(cap_of_group.values())
        print(f"  {'합계':<9}{tq:>10.0f}{tc:>9.0f}{tq/tc:>8.2f}     metering 대상 그룹 {n_ok}/4")
        print()
        summary.append((label, tq, tq / tc, n_ok))

    if summary:
        print("=== 요약")
        print(f"  {'수요':<16}{'온램프 합계':>12}{'포화도':>8}{'대상 그룹':>10}")
        for label, tq, sat, n_ok in summary:
            print(f"  {label:<16}{tq:>12.0f}{sat:>8.2f}{n_ok:>8}/4")
        print()
        print("  판정 기준: q/cap >= 0.80 이면서 합류 세그 capdrop >= 30 % 인 그룹을 metering 대상으로 센다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
