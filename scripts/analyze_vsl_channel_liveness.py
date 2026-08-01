# VSL 채널 실집행 프로브(probe_vsl_channel_liveness.vbs) 산출물을 채널별 판정으로 환산하는 분석기.
"""프로브가 남긴 원시 차량 표를 읽어 16개 VSL 채널의 생사를 판정한다.

판정 논리.
  각 채널은 폭 0.01 km/h짜리 고유 지문 분포를 갖는다. 어떤 차량의 DesSpeed가 채널 k의
  대역 안에 있으면 그 차량은 채널 k의 DSD를 마지막으로 통과한 것이다. 세그먼트 i 안에
  있는 차량 중 '자기 채널 지문'을 가진 비율이 곧 그 채널의 집행률이다.

  살아있음(live)   : own_share >= 0.5
  부분(partial)    : 0.02 <= own_share < 0.5
  죽음(dead)       : own_share < 0.02 이고 표본이 있음
  표본없음(no_data): 세그먼트 표본 0

  세그먼트 안에 있어도 자기 지문을 못 가지는 정상 사유가 하나 남는다.
  온램프에서 세그먼트 중간으로 합류한 차량은 그 세그먼트의 DSD를 지나친 적이 없다.
  그래서 대상 클래스 차량만으로 계산한 own_share_eligible 을 따로 낸다.

  2026-08-01 수정. 클래스 70(TAXI)이 VSL 대상에 편입됐다(RW DSD 64개 + 러너
  ApplyActionCsv 가 클래스 10/20/30/70 에 모두 지시값을 건다). 따라서 클래스 70은
  더 이상 '대상 아님'으로 제외하지 않고 DSD_TARGET_CLASSES 에 포함한다. 1차 실측
  (outputs/vsl_channel_live_execution_20260801.md 3절)은 70을 제외한 정의였다.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# vehType -> vehClass (network/real_world_gaepo_modi/modi_eval_rw_control.inpx 의 vehicleClass 정의)
VEHTYPE_TO_CLASS = {100: 10, 150: 70, 200: 20, 300: 30, 400: 40, 510: 50, 520: 50, 600: 60}
DSD_TARGET_CLASSES = {10, 20, 30, 70}
# 지문 분포의 지지집합은 정확히 [v, v+0.01]이라 허용오차는 0.02면 충분하다.
# 넓히면 기본 분포 100(88~130 연속)에서 우연히 대역에 들어오는 오염이 늘어난다.
BAND_TOL_KMH = 0.02
BAND_WIDTH = 0.01  # make_vsl_probe_network.BAND_WIDTH_KMH 와 같아야 한다

LIVE_THRESHOLD = 0.5
PARTIAL_THRESHOLD = 0.02
# install_real_world_freeway_controls.vbs 의 DSD_EDGE_CLEARANCE_M 과 같아야 한다.
# 세그먼트 0 DSD가 이 지점에 놓이므로 체인 [0, 이 값) 이 VSL 미적용 근사 구간이다.
APPROACH_ZONE_M = 40.0


def load_channels(path: Path) -> list[dict]:
    with path.open(encoding="ascii", newline="") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        r["channel_index"] = int(r["channel_index"])
        r["segment_index"] = int(r["segment_index"])
        for k in ("segment_start_m", "segment_end_m", "dsd_pos_m", "dsd_chain_pos_m",
                  "dsd_snap_offset_m", "distr_speed_kmh"):
            r[k] = float(r[k])
        r["host_link"] = int(r["host_link"])
        r["distr_no"] = int(r["distr_no"])
    return rows


def load_chain(path: Path) -> dict:
    out = {}
    with path.open(encoding="ascii", newline="") as fh:
        for r in csv.DictReader(fh):
            out[r["model_link"]] = {
                "links": [int(x) for x in r["chain_links"].split(";")],
                "offsets": [float(x) for x in r["chain_offsets_m"].split(";")],
                "bounds": [float(x) for x in r["segment_bounds_m"].split(";")],
            }
    return out


def chain_pos(link_no: int, pos: float, chain: dict) -> float | None:
    for link, off in zip(chain["links"], chain["offsets"]):
        if link == link_no:
            return off + pos
    return None


def segment_index(cpos: float, bounds: list[float]) -> int:
    for i in range(len(bounds) - 1):
        if cpos < bounds[i + 1]:
            return i
    return len(bounds) - 2


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", default=str(REPO / "evaluation/runs/vsl_channel_com_smoke_20260801"))
    ap.add_argument("--out-json", default=None)
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    channels = load_channels(run_dir / "vsl_probe_channels.csv")
    chain = load_chain(run_dir / "vsl_probe_chain.csv")

    # band lookup: fingerprint speed -> channel index
    bands = sorted((c["distr_speed_kmh"], c["channel_index"]) for c in channels)

    def band_of(des: float) -> int | None:
        for speed, k in bands:
            if speed - BAND_TOL_KMH <= des <= speed + BAND_WIDTH + BAND_TOL_KMH:
                return k
        return None

    by_key = {(c["model_link"], c["segment_index"]): c for c in channels}

    # per-segment tallies
    tally = defaultdict(lambda: {
        "samples": 0, "own": 0, "other_band": defaultdict(int), "unbanded": 0,
        "eligible": 0, "eligible_own": 0, "taxi": 0, "taxi_own": 0,
        "taxi_entry40": 0, "by_lane_own": defaultdict(int),
        "by_lane_samples": defaultdict(int), "speed_sum": 0.0,
        "unbanded_legacy100": 0, "unbanded_entry40": 0, "unbanded_other": 0,
    })
    # S0 진입 근사 구간 [0, DSD_EDGE_CLEARANCE_M) 에서 차량이 실제로 무엇을 받는지.
    approach = defaultdict(lambda: {"n": 0, "own_band": 0, "other_band": 0,
                                    "legacy100": 0, "entry40": 0, "other": 0, "taxi": 0})
    link_seg_counts = defaultdict(int)          # (sim_sec, model_link, seg) -> n  (independent rebin)
    link74_seg = defaultdict(int)
    veh_rows = 0

    # 완결된 표본 시각만 쓴다. 세그먼트 카운트 파일에 그 초의 16행이 다 있으면
    # 그 초의 차량 행도 전부 기록된 것이다(프로브가 차량 행을 먼저 쓴다).
    seg_sec_rows = defaultdict(int)
    with (run_dir / "probe_segment_counts.csv").open(encoding="ascii", newline="") as fh:
        for r in csv.DictReader(fh):
            seg_sec_rows[int(r["sim_sec"])] += 1
    complete_secs = {s for s, n in seg_sec_rows.items() if n == 16}

    with (run_dir / "probe_vehicles.csv").open(encoding="ascii", newline="") as fh:
        for r in csv.DictReader(fh):
            sim_sec = int(r["sim_sec"])
            if sim_sec not in complete_secs:
                continue
            veh_rows += 1
            link_no = int(r["link_no"])
            lane_no = int(r["lane_no"])
            pos = float(r["pos_m"])
            des = float(r["des_speed_kph"])
            vtype = int(r["veh_type"])
            vclass = VEHTYPE_TO_CLASS.get(vtype, 0)

            model_link = None
            cpos = chain_pos(link_no, pos, chain["FW_E"])
            if cpos is not None:
                model_link = "FW_E"
            else:
                cpos = chain_pos(link_no, pos, chain["FW_W"])
                if cpos is not None:
                    model_link = "FW_W"
            if model_link is None:
                continue
            seg = segment_index(cpos, chain[model_link]["bounds"])
            link_seg_counts[(sim_sec, model_link, seg)] += 1
            if link_no == 74:
                link74_seg[(model_link, seg)] += 1

            t = tally[(model_link, seg)]
            t["samples"] += 1
            t["speed_sum"] += float(r["speed_kph"])
            t["by_lane_samples"][lane_no] += 1
            if vclass == 70:
                t["taxi"] += 1
            if vclass in DSD_TARGET_CLASSES:
                t["eligible"] += 1
            k = band_of(des)
            own_k = by_key[(model_link, seg)]["channel_index"]
            if cpos < APPROACH_ZONE_M:
                a = approach[model_link]
                a["n"] += 1
                if vclass == 70:
                    a["taxi"] += 1
                if k == own_k:
                    a["own_band"] += 1
                elif k is not None:
                    a["other_band"] += 1
                elif 88.0 <= des <= 130.0:
                    a["legacy100"] += 1
                elif 40.0 <= des <= 45.0:
                    a["entry40"] += 1
                else:
                    a["other"] += 1
            if k is None:
                t["unbanded"] += 1
                if vclass == 70 and 40.0 <= des <= 45.0:
                    t["taxi_entry40"] += 1
                # 지문이 없는 차량의 사유를 분리한다. 88~130은 기본 분포 100(레거시 DSD가
                # 덮어쓴 값), 40~45는 유입 구성 분포 40(어떤 DSD도 건드리지 못한 값)이다.
                if 88.0 <= des <= 130.0:
                    t["unbanded_legacy100"] += 1
                elif 40.0 <= des <= 45.0:
                    t["unbanded_entry40"] += 1
                else:
                    t["unbanded_other"] += 1
            elif k == own_k:
                t["own"] += 1
                t["by_lane_own"][lane_no] += 1
                if vclass in DSD_TARGET_CLASSES:
                    t["eligible_own"] += 1
                if vclass == 70:
                    t["taxi_own"] += 1
            else:
                t["other_band"][k] += 1

    # cross check: probe's own (runner-verbatim) segment counts vs independent rebin
    recorder = defaultdict(int)
    recorder_secs = set()
    with (run_dir / "probe_segment_counts.csv").open(encoding="ascii", newline="") as fh:
        for r in csv.DictReader(fh):
            recorder[(int(r["sim_sec"]), r["model_link"], int(r["seg_index"]))] = int(r["count"])
            recorder_secs.add(int(r["sim_sec"]))
    # 세그먼트 카운트는 그 초의 차량 행을 다 쓴 뒤에 기록된다. 두 파일 모두에 완결된
    # sim_sec 만 비교해야 중간에 잘린 표본이 가짜 불일치로 잡히지 않는다.
    mismatches = []
    keys = {k for k in list(recorder.keys()) + list(link_seg_counts.keys()) if k[0] in recorder_secs}
    for key in keys:
        a = recorder.get(key, 0)
        b = link_seg_counts.get(key, 0)
        if a != b:
            mismatches.append({"sim_sec": key[0], "model_link": key[1], "seg": key[2],
                               "recorder": a, "rebin": b})

    ch_by_index = {c["channel_index"]: c for c in channels}
    results = []
    for c in sorted(channels, key=lambda x: (x["model_link"], x["segment_index"])):
        t = tally.get((c["model_link"], c["segment_index"]))
        if t is None or t["samples"] == 0:
            results.append({**{k: c[k] for k in ("segment_id", "model_link", "segment_index",
                                                 "channel_index", "host_link", "dsd_pos_m",
                                                 "dsd_chain_pos_m", "dsd_snap_offset_m",
                                                 "distr_no", "distr_speed_kmh")},
                            "samples": 0, "verdict": "no_data"})
            continue
        own_share = t["own"] / t["samples"]
        elig_share = (t["eligible_own"] / t["eligible"]) if t["eligible"] else 0.0
        if own_share >= LIVE_THRESHOLD:
            verdict = "live"
        elif own_share >= PARTIAL_THRESHOLD:
            verdict = "partial"
        else:
            verdict = "dead"
        top_other = sorted(t["other_band"].items(), key=lambda kv: -kv[1])[:3]
        results.append({
            **{k: c[k] for k in ("segment_id", "model_link", "segment_index", "channel_index",
                                 "host_link", "dsd_pos_m", "dsd_chain_pos_m", "dsd_snap_offset_m",
                                 "distr_no", "distr_speed_kmh")},
            "samples": t["samples"],
            "own": t["own"],
            "own_share": round(own_share, 4),
            "eligible": t["eligible"],
            "eligible_own_share": round(elig_share, 4),
            "unbanded": t["unbanded"],
            "unbanded_share": round(t["unbanded"] / t["samples"], 4),
            "unbanded_legacy100": t["unbanded_legacy100"],
            "unbanded_legacy100_share": round(t["unbanded_legacy100"] / t["samples"], 4),
            "unbanded_entry40": t["unbanded_entry40"],
            "unbanded_other": t["unbanded_other"],
            "taxi_class70": t["taxi"],
            "taxi_share": round(t["taxi"] / t["samples"], 4),
            "taxi_own": t["taxi_own"],
            "taxi_own_share": round(t["taxi_own"] / t["taxi"], 4) if t["taxi"] else None,
            "taxi_entry40": t["taxi_entry40"],
            "mean_speed_kph": round(t["speed_sum"] / t["samples"], 2),
            "top_foreign_bands": [
                {"channel_index": k, "segment_id": ch_by_index[k]["segment_id"], "n": n,
                 "share": round(n / t["samples"], 4)} for k, n in top_other
            ],
            "per_lane_own_share": {
                str(ln): round(t["by_lane_own"].get(ln, 0) / t["by_lane_samples"][ln], 4)
                for ln in sorted(t["by_lane_samples"])
            },
            "verdict": verdict,
        })

    summary = {
        "run_dir": str(run_dir),
        "complete_sample_secs": sorted(complete_secs),
        "vehicle_rows": veh_rows,
        "channels_total": len(results),
        "live": sum(1 for r in results if r["verdict"] == "live"),
        "partial": sum(1 for r in results if r["verdict"] == "partial"),
        "dead": sum(1 for r in results if r["verdict"] == "dead"),
        "no_data": sum(1 for r in results if r["verdict"] == "no_data"),
        "recorder_vs_rebin_mismatches": len(mismatches),
        "recorder_mismatch_examples": mismatches[:10],
        "link74_segment_counts": {f"{k[0]}_S{k[1]}": v for k, v in sorted(link74_seg.items())},
        "dsd_target_classes": sorted(DSD_TARGET_CLASSES),
        "approach_zone_m": APPROACH_ZONE_M,
        "s0_approach_zone": {k: dict(v) for k, v in sorted(approach.items())},
        "channels": results,
    }

    out_json = Path(args.out_json) if args.out_json else run_dir / "vsl_channel_liveness_summary.json"
    out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"VEHICLE_ROWS={veh_rows}")
    print(f"RECORDER_VS_REBIN_MISMATCHES={len(mismatches)}")
    print(f"LINK74_SEG_COUNTS={summary['link74_segment_counts']}")
    print(f"DSD_TARGET_CLASSES={sorted(DSD_TARGET_CLASSES)}")
    for ml, a in summary["s0_approach_zone"].items():
        print(f"APPROACH_ZONE {ml} [0,{APPROACH_ZONE_M:.0f}) " + " ".join(f"{k}={v}" for k, v in a.items()))
    print(f"VERDICT live={summary['live']} partial={summary['partial']} dead={summary['dead']} no_data={summary['no_data']}")
    hdr = ("segment_id", "host", "dsd_pos", "n", "own%", "elig_own%", "unband%", "taxi%",
           "taxiown%", "verdict", "top_foreign")
    print("%-12s %5s %9s %7s %7s %9s %8s %6s %8s %8s  %s" % hdr)
    for r in results:
        if r["samples"] == 0:
            print("%-12s %5s %9s %7d %7s %9s %8s %6s %8s %8s" %
                  (r["segment_id"], r["host_link"], f"{r['dsd_pos_m']:.1f}", 0, "-", "-", "-", "-", "-",
                   r["verdict"]))
            continue
        tf = ",".join(f"{b['segment_id']}:{b['share']:.2f}" for b in r["top_foreign_bands"])
        to = "-" if r["taxi_own_share"] is None else f"{r['taxi_own_share']:.3f}"
        print("%-12s %5s %9s %7d %7.3f %9.3f %8.3f %6.3f %8s %8s  %s" %
              (r["segment_id"], r["host_link"], f"{r['dsd_pos_m']:.1f}", r["samples"],
               r["own_share"], r["eligible_own_share"], r["unbanded_share"], r["taxi_share"],
               to, r["verdict"], tf))
    print("SUMMARY_JSON=" + str(out_json))


if __name__ == "__main__":
    main()
