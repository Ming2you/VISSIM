# -*- coding: utf-8 -*-
"""현재 망(core17legs4b)의 urban MFD 를 **완주한 런의 상태 JSON에서** 만든다. VISSIM 재실행 없음.

왜 (2026-08-28).

리더 목적함수에서 perimeter control 항(`target_penalty = w_P * max(0, N_P - N_P_crit)`)이
`mfd_penalty_mode = all_urban_halfcap` 때문에 **분기 자체가 안 돈다**. 그리고 그 임계값
`N_P_crit_veh = 509.449` 는 적합값이 아니라 폴백 상수다(`parameters.json` 이 그렇게 적고 있다:
"그 파일에 키가 없어 항상 폴백이 발동했다"). 실측 보호망 누적은 중앙 2336.6 으로 임계의 4.6배다.

그런데 저장소의 urban MFD 산출물 18개는 **전부 2026-08-02~04** 생성이다. 2026-08-19 토폴로지
재생성 이전 세대라 현재 망의 임계누적 근거가 될 수 없다.

무엇을 하는가.

    누적 n = sum_i count_i            [veh]
    생산 P = sum_i count_i * v_i      [veh*km/h]

옛 스크립트 `extract_no_control_fd_mfd.py:139` 의 `production = count * speed` 와 같은 정의다.
링크별 count/mean_speed_kph 는 모든 상태 JSON 의 `local_observation` 에 있다(관측 670링크).
분류는 정본 검지매핑으로만 한다 — `link_to_origins` 에 있는 링크가 도시부이고 freeway 모델
링크와 램프 큐 링크는 뺀다. 규칙을 새로 만들지 않는다.

산출: outputs/urban_mfd_core17legs4b_20260828.{json,csv}
"""
import argparse
import csv
import io
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

R = Path(__file__).resolve().parent.parent

SKIP_SUFFIXES = ("_FAILED_merge_conflict", "_INVALID_no_observation", "_PRE_BETAFIX", "_OLD")


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def urban_link_set(det):
    """도시부 링크 집합. 정본 검지매핑에서만 유도한다."""
    urban = {str(k) for k in (det.get("link_to_origins") or {})}
    fw = {str(k) for k in (det.get("freeway_link_to_model_link") or {})}
    ramp = {str(k) for k in (det.get("ramp_link_to_queues") or {})}
    bnd = {str(k) for k in (det.get("boundary_link_to_queue") or {})}
    core = urban - fw - ramp
    return core, {"link_to_origins": len(urban), "freeway": len(fw), "ramp": len(ramp),
                  "boundary": len(bnd), "core": len(core)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="*", default=None, help="비우면 완주한 런 전부")
    ap.add_argument("--detector", default="evaluation/real_world_modi_control_distributed_20260728/"
                                          "detector_local_mapping_distributed_core17legs4f_20260826.json")
    ap.add_argument("--min-decisions", type=int, default=30)
    ap.add_argument("--bins", type=int, default=14)
    # 세대 필터. **비우지 마라.** 저장소에는 관측 링크 수가 다른 세대가 넷 섞여 있고
    # (4b 293 · 4e 626 · 4f 670 · pedovrx 1208), 생산은 관측 링크 합이라 세대를 섞으면
    # 서로 다른 망의 점이 한 MFD 로 뭉친다. 2026-08-28 첫 판이 그렇게 나와서
    # 2878 veh 위 구간에서 생산이 갑자기 뛰고 속도가 되레 오르는 가짜 모양이 나왔다.
    ap.add_argument("--network", default="modi_eval_userfix_20260814e.inpx")
    ap.add_argument("--mapping-tag", default="core17legs4f_20260826")
    ap.add_argument("--expect-links", type=int, default=670)
    ap.add_argument("--out", default="outputs/urban_mfd_core17legs4b_20260828")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    det = load(R / args.detector)
    core, counts = urban_link_set(det)
    print("검지매핑 %s" % Path(args.detector).name)
    print("   link_to_origins %d - freeway %d - ramp %d  =  도시부 core %d  (경계 %d)"
          % (counts["link_to_origins"], counts["freeway"], counts["ramp"],
             counts["core"], counts["boundary"]))

    runs = args.runs
    if not runs:
        runs = []
        for d in sorted((R / "evaluation/runs").glob("*")):
            if not d.is_dir() or d.name.endswith(SKIP_SUFFIXES):
                continue
            if len(list(d.glob("decisions_*/state_*.json"))) >= args.min_decisions:
                runs.append(d.name)

    rows = []
    per_run = defaultdict(int)
    skipped = defaultdict(int)
    for run in runs:
        for f in sorted((R / "evaluation/runs" / run).glob("decisions_*/state_*.json")):
            sj = load(f)
            lo = sj.get("local_observation") or {}
            lc = lo.get("link_counts") or {}
            ls = lo.get("link_speeds_kph") or {}
            if not lc or not ls:
                skipped["관측 없음"] += 1
                continue
            if not lo.get("scan_ok", True):
                skipped["scan 실패"] += 1
                continue
            net_name = Path(str(sj.get("network_path") or "").replace("\\", "/")).name
            dm_name = Path(str(lo.get("detector_mapping_json") or "").replace("\\", "/")).name
            if args.network and net_name != args.network:
                skipped["다른 망 %s" % net_name] += 1
                continue
            if args.mapping_tag and args.mapping_tag not in dm_name:
                skipped["다른 매핑 %s" % dm_name] += 1
                continue
            if args.expect_links and len(lc) != args.expect_links:
                skipped["관측 링크 %d" % len(lc)] += 1
                continue
            n = p = 0.0
            seen = 0
            for link, cnt in lc.items():
                if str(link) not in core:
                    continue
                c = float(cnt or 0.0)
                v = float(ls.get(link, 0.0) or 0.0)
                n += c
                p += c * v
                seen += 1
            if n <= 0.0:
                skipped["누적 0"] += 1
                continue
            rows.append({
                "run": run,
                "sim_sec": float(sj.get("sim_sec") or 0.0),
                "core_accumulation_veh": n,
                "core_production_veh_km_h": p,
                "core_mean_speed_kph": p / n,
                "core_links_seen": seen,
                "urban_vehicles_state": float(sj.get("urban_vehicles") or 0.0),
                "total_vehicles_state": float(sj.get("total_vehicles") or 0.0),
                "stopped_vehicles_state": float(sj.get("stopped_vehicles") or 0.0),
            })
            per_run[run] += 1

    if not rows:
        print("!! 점이 하나도 없다")
        return 1
    print("런 %d개 - 점 %d개%s" % (len(per_run), len(rows),
                                 ("  건너뜀 %s" % dict(skipped)) if skipped else ""))

    acc = [r["core_accumulation_veh"] for r in rows]
    lo_a, hi_a = min(acc), max(acc)
    ratio = st.median([r["core_accumulation_veh"] / r["urban_vehicles_state"]
                       for r in rows if r["urban_vehicles_state"] > 0])
    print("   core 누적 / state urban_vehicles 중앙비 %.3f  (1 근처여야 분류가 맞다)" % ratio)

    nb = args.bins
    w = (hi_a - lo_a) / nb if hi_a > lo_a else 1.0
    binned = []
    for i in range(nb):
        a0, a1 = lo_a + i * w, lo_a + (i + 1) * w
        seg = [r for r in rows if (a0 <= r["core_accumulation_veh"] < a1)
               or (i == nb - 1 and r["core_accumulation_veh"] == hi_a)]
        if not seg:
            continue
        binned.append({
            "bin_lo": a0, "bin_hi": a1, "n_points": len(seg),
            "mean_accumulation_veh": st.mean(r["core_accumulation_veh"] for r in seg),
            "mean_production_veh_km_h": st.mean(r["core_production_veh_km_h"] for r in seg),
            "mean_speed_kph": st.mean(r["core_mean_speed_kph"] for r in seg),
        })

    peak = max(binned, key=lambda b: b["mean_production_veh_km_h"])
    peak_pt = max(rows, key=lambda r: r["core_production_veh_km_h"])
    turned = peak["mean_accumulation_veh"] < lo_a + 0.85 * (hi_a - lo_a)

    print()
    print("%-23s %7s %14s %10s" % ("core 누적 구간", "점수", "평균 생산", "평균속도"))
    pmax = max(b["mean_production_veh_km_h"] for b in binned)
    for b in binned:
        bar = "#" * int(44 * b["mean_production_veh_km_h"] / pmax)
        print("%8.0f~%-14.0f %7d %14.0f %10.1f %s"
              % (b["bin_lo"], b["bin_hi"], b["n_points"],
                 b["mean_production_veh_km_h"], b["mean_speed_kph"], bar))
    print()
    print("누적 범위 %.0f ~ %.0f veh" % (lo_a, hi_a))
    print("최고 생산 구간 중심 %.0f veh (평균 생산 %.0f)"
          % (peak["mean_accumulation_veh"], peak["mean_production_veh_km_h"]))
    print("단일 최고점 누적 %.0f - 생산 %.0f - %s @ %.0fs"
          % (peak_pt["core_accumulation_veh"], peak_pt["core_production_veh_km_h"],
             peak_pt["run"], peak_pt["sim_sec"]))
    if turned:
        print("MFD 가 꺾이는가: **예** - 임계누적 추정 %.0f veh" % peak["mean_accumulation_veh"])
    else:
        print("MFD 가 꺾이는가: **아니오** - 관측 범위 끝까지 생산이 는다(비혼잡 분지)")
    print("리더의 현행 N_P_crit_veh = 509.449")

    doc = {
        "schema_version": "urban-mfd/core17legs4b/1",
        "generated": "2026-08-28",
        "why": "리더의 perimeter 항 임계 N_P_crit_veh=509.449 가 적합값이 아니라 폴백 상수이고, "
               "저장소의 urban MFD 산출물은 전부 2026-08-19 토폴로지 재생성 이전 세대다.",
        "method": {"accumulation": "sum_i count_i over core links",
                   "production": "sum_i count_i * mean_speed_kph_i [veh*km/h]",
                   "core_links": "detector link_to_origins - freeway - ramp",
                   "source": "완주 런의 상태 JSON local_observation (VISSIM 재실행 없음)"},
        "detector_mapping": args.detector,
        "link_counts": counts,
        "runs": dict(sorted(per_run.items())),
        "point_count": len(rows),
        "accumulation_range_veh": [lo_a, hi_a],
        "core_over_state_urban_ratio_median": ratio,
        "peak_bin": peak,
        "peak_point": {k: peak_pt[k] for k in
                       ("run", "sim_sec", "core_accumulation_veh", "core_production_veh_km_h")},
        "turned_over": bool(turned),
        "current_leader_N_P_crit_veh": 509.448830418254,
        "binned": binned,
    }
    (R / (args.out + ".json")).write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    with io.open(R / (args.out + ".csv"), "w", encoding="utf-8", newline="") as fh:
        w2 = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w2.writeheader()
        w2.writerows(rows)
    print()
    print("-> %s.json / .csv" % args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
