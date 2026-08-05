# 본선 혼잡 탐침(구/신) 런을 분석창 기준으로 비교해 혼잡 수준/지속성/도시부 상태를 산출한다.
"""실행:
    "C:/Users/alsrj/anaconda3/python.exe" scripts/analyze_freeway_congestion_probe_20260802.py \
        --old evaluation/runs/freeway_congestion_probe_20260802 \
        --new evaluation/runs/freeway_congestion_probe_fixed_20260802 \
        --out outputs/freeway_congestion_probe_compare_20260802.json

산출:
  - 분석창(900 < t <= 4500) freeway 세그먼트 밀도의 rho_crit 초과 비율
  - 600 s bin 평균 밀도(전 구간) -> 지속성 판정
  - freeway 평균 속도 / 정지 차량 / 램프 링크 점유
  - urban 상태(대수, 평균 속도, 정지 차량)
  - rho > 20 표본수(FD 용량 식별용)
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

RHO_CRIT = 16.353642734374997
TAGS = ("breakdown", "lowurban", "extreme")
WARMUP = 900.0
END = 4500.0
BIN = 600.0


def fnum(v: object, d: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def pct(xs: list[float], q: float) -> float:
    if not xs:
        return 0.0
    o = sorted(xs)
    pos = (len(o) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(o) - 1)
    fr = pos - lo
    return o[lo] * (1.0 - fr) + o[hi] * fr


def run_name(tag: str) -> str:
    return f"no_control_fw_{tag}_warm900_eval3600_seed13"


def analyze_arm(root: Path, tag: str) -> dict | None:
    name = run_name(tag)
    seg_p = root / f"bottleneck_segments_{name}.csv"
    lnk_p = root / f"bottleneck_links_{name}.csv"
    st_p = root / f"state_{name}.csv"
    if not seg_p.exists() or not st_p.exists():
        return None

    seg = read_csv(seg_p)
    # freeway 세그먼트만. 빈 세그먼트(count==0)는 mean_speed=0 이라 속도 통계에서 제외한다.
    fw = [r for r in seg if str(r.get("model_link", "")).startswith("FW_")]

    def in_win(r) -> bool:
        t = fnum(r.get("sim_sec"))
        return WARMUP < t <= END

    win_all = [r for r in fw if in_win(r)]
    win_occ = [r for r in win_all if fnum(r.get("count")) > 0.0]

    rho_all = [fnum(r.get("density_veh_km_lane")) for r in win_all]
    rho_occ = [fnum(r.get("density_veh_km_lane")) for r in win_occ]
    spd_occ = [fnum(r.get("mean_speed_kph")) for r in win_occ]

    over_all = sum(1 for x in rho_all if x > RHO_CRIT) / len(rho_all) if rho_all else 0.0
    over_occ = sum(1 for x in rho_occ if x > RHO_CRIT) / len(rho_occ) if rho_occ else 0.0

    # 600 s bin 평균 밀도(전 구간, 점유 세그먼트 기준 + 전체 기준 둘 다)
    bins_occ: dict[int, list[float]] = defaultdict(list)
    bins_all: dict[int, list[float]] = defaultdict(list)
    bins_spd: dict[int, list[float]] = defaultdict(list)
    for r in fw:
        t = fnum(r.get("sim_sec"))
        if t <= 0 or t > END:
            continue
        b = int((t - 1e-9) // BIN)
        rho = fnum(r.get("density_veh_km_lane"))
        bins_all[b].append(rho)
        if fnum(r.get("count")) > 0.0:
            bins_occ[b].append(rho)
            bins_spd[b].append(fnum(r.get("mean_speed_kph")))
    nb = max(bins_all) + 1 if bins_all else 0
    bin_rho_occ = [mean(bins_occ.get(i, [])) for i in range(nb)]
    bin_rho_all = [mean(bins_all.get(i, [])) for i in range(nb)]
    bin_spd = [mean(bins_spd.get(i, [])) for i in range(nb)]

    # 지속성: 분석창 안의 bin(1..) 만 보고 마지막/최대 비율을 낸다.
    win_bins = [i for i in range(nb) if i * BIN >= WARMUP]
    wb_rho = [bin_rho_occ[i] for i in win_bins]
    persistence = {
        "window_bins": win_bins,
        "window_bin_rho": wb_rho,
        "max": max(wb_rho) if wb_rho else 0.0,
        "last": wb_rho[-1] if wb_rho else 0.0,
        "last_over_max": (wb_rho[-1] / max(wb_rho)) if wb_rho and max(wb_rho) > 0 else 0.0,
        "decay_ratio_first_to_last": (wb_rho[-1] / wb_rho[0]) if wb_rho and wb_rho[0] > 0 else 0.0,
    }

    # 세그먼트 정지 차량(분석창 합/평균)
    stopped = [fnum(r.get("stopped_count")) for r in win_all]

    # state CSV
    st = [r for r in read_csv(st_p) if WARMUP < fnum(r.get("sim_sec")) <= END]
    state = {
        "total_vehicles_mean": mean([fnum(r.get("total_vehicles")) for r in st]),
        "freeway_vehicles_mean": mean([fnum(r.get("freeway_vehicles")) for r in st]),
        "urban_vehicles_mean": mean([fnum(r.get("urban_vehicles")) for r in st]),
        "ramp_vehicles_mean": mean([fnum(r.get("ramp_vehicles")) for r in st]),
        "mean_speed_kph": mean([fnum(r.get("mean_speed_kph")) for r in st]),
        "freeway_mean_speed_kph": mean([fnum(r.get("freeway_mean_speed_kph")) for r in st]),
        "stopped_vehicles_mean": mean([fnum(r.get("stopped_vehicles")) for r in st]),
        "stopped_vehicles_max": max([fnum(r.get("stopped_vehicles")) for r in st], default=0.0),
    }
    # state 600 s bin (지속성 교차확인)
    sb: dict[int, list[float]] = defaultdict(list)
    sbs: dict[int, list[float]] = defaultdict(list)
    for r in read_csv(st_p):
        t = fnum(r.get("sim_sec"))
        if t <= 0 or t > END:
            continue
        b = int((t - 1e-9) // BIN)
        sb[b].append(fnum(r.get("freeway_vehicles")))
        sbs[b].append(fnum(r.get("stopped_vehicles")))
    state_bin_fw = [mean(sb.get(i, [])) for i in range(nb)]
    state_bin_stopped = [mean(sbs.get(i, [])) for i in range(nb)]

    # 링크: 램프 미터 커넥터 / 도시부
    ramp = {}
    urban = {}
    if lnk_p.exists():
        lnk = [r for r in read_csv(lnk_p) if WARMUP < fnum(r.get("sim_sec")) <= END]
        rl = [r for r in lnk if str(r.get("is_ramp_meter_connector", "")).strip() in ("1", "1.0", "True")]
        ul = [r for r in lnk if str(r.get("category", "")) == "urban_or_other"]
        if rl:
            per_t: dict[float, float] = defaultdict(float)
            per_t_stop: dict[float, float] = defaultdict(float)
            for r in rl:
                per_t[fnum(r.get("sim_sec"))] += fnum(r.get("count"))
                per_t_stop[fnum(r.get("sim_sec"))] += fnum(r.get("stopped_count"))
            occ = [r for r in rl if fnum(r.get("count")) > 0]
            ramp = {
                "n_ramp_links": len({r.get("link") for r in rl}),
                "total_count_mean": mean(list(per_t.values())),
                "total_count_max": max(per_t.values(), default=0.0),
                "total_stopped_mean": mean(list(per_t_stop.values())),
                "total_stopped_max": max(per_t_stop.values(), default=0.0),
                "per_link_count_mean": mean([fnum(r.get("count")) for r in rl]),
                "per_link_count_p95": pct([fnum(r.get("count")) for r in rl], 0.95),
                "occupied_mean_speed_kph": mean([fnum(r.get("mean_speed_kph")) for r in occ]),
            }
        if ul:
            uocc = [r for r in ul if fnum(r.get("count")) > 0]
            per_t_u: dict[float, float] = defaultdict(float)
            per_t_us: dict[float, float] = defaultdict(float)
            for r in ul:
                per_t_u[fnum(r.get("sim_sec"))] += fnum(r.get("count"))
                per_t_us[fnum(r.get("sim_sec"))] += fnum(r.get("stopped_count"))
            urban = {
                "n_urban_links": len({r.get("link") for r in ul}),
                "total_count_mean": mean(list(per_t_u.values())),
                "total_stopped_mean": mean(list(per_t_us.values())),
                "total_stopped_max": max(per_t_us.values(), default=0.0),
                "occupied_mean_speed_kph": mean([fnum(r.get("mean_speed_kph")) for r in uocc]),
                "stopped_share": (sum(per_t_us.values()) / sum(per_t_u.values())
                                  if sum(per_t_u.values()) > 0 else 0.0),
            }

    return {
        "tag": tag,
        "dir": str(root),
        "window": [WARMUP, END],
        "rho_crit": RHO_CRIT,
        "n_samples_all": len(rho_all),
        "n_samples_occupied": len(rho_occ),
        "frac_rho_gt_rho_crit_all": over_all,
        "frac_rho_gt_rho_crit_occupied": over_occ,
        "rho_mean_occupied": mean(rho_occ),
        "rho_p90_occupied": pct(rho_occ, 0.90),
        "rho_p95_occupied": pct(rho_occ, 0.95),
        "rho_max": max(rho_all, default=0.0),
        "n_rho_gt_20": sum(1 for x in rho_occ if x > 20.0),
        "frac_rho_gt_20": (sum(1 for x in rho_occ if x > 20.0) / len(rho_occ)) if rho_occ else 0.0,
        "n_rho_gt_25": sum(1 for x in rho_occ if x > 25.0),
        "n_rho_gt_30": sum(1 for x in rho_occ if x > 30.0),
        "seg_mean_speed_kph_occupied": mean(spd_occ),
        "seg_stopped_sum": sum(stopped),
        "seg_stopped_mean": mean(stopped),
        "bin_rho_occupied_600s": bin_rho_occ,
        "bin_rho_all_600s": bin_rho_all,
        "bin_speed_600s": bin_spd,
        "state_bin_freeway_vehicles_600s": state_bin_fw,
        "state_bin_stopped_600s": state_bin_stopped,
        "persistence": persistence,
        "state": state,
        "ramp": ramp,
        "urban": urban,
    }


def fmt_list(xs: list[float], p: int = 1) -> str:
    return "/".join(f"{x:.{p}f}" for x in xs)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", type=Path, required=True)
    ap.add_argument("--new", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    result = {"rho_crit": RHO_CRIT, "old": {}, "new": {}}
    for tag in TAGS:
        for key, root in (("old", args.old), ("new", args.new)):
            a = analyze_arm(root, tag)
            if a:
                result[key][tag] = a

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"rho_crit = {RHO_CRIT:.3f}   window = ({WARMUP:.0f}, {END:.0f}]\n")
    hdr = f"{'arm':<10} {'ver':<4} {'over%(occ)':>10} {'over%(all)':>10} {'rho_mean':>9} {'rho_p95':>8} {'rho_max':>8} {'n>20':>6} {'fwspd':>7} {'stop':>7}"
    print(hdr)
    print("-" * len(hdr))
    for tag in TAGS:
        for key in ("old", "new"):
            a = result[key].get(tag)
            if not a:
                continue
            print(f"{tag:<10} {key:<4} {a['frac_rho_gt_rho_crit_occupied']*100:>9.1f}% "
                  f"{a['frac_rho_gt_rho_crit_all']*100:>9.1f}% {a['rho_mean_occupied']:>9.2f} "
                  f"{a['rho_p95_occupied']:>8.2f} {a['rho_max']:>8.2f} {a['n_rho_gt_20']:>6d} "
                  f"{a['state']['freeway_mean_speed_kph']:>7.1f} {a['state']['stopped_vehicles_mean']:>7.1f}")
    print("\n=== 600 s bin mean density (freeway, occupied segments) ===")
    for tag in TAGS:
        for key in ("old", "new"):
            a = result[key].get(tag)
            if not a:
                continue
            p = a["persistence"]
            print(f"{tag:<10} {key:<4} {fmt_list(a['bin_rho_occupied_600s'])}"
                  f"   | window last/max = {p['last_over_max']:.2f}")
    print("\n=== urban ===")
    for tag in TAGS:
        for key in ("old", "new"):
            a = result[key].get(tag)
            if not a or not a["urban"]:
                continue
            u = a["urban"]
            print(f"{tag:<10} {key:<4} veh_mean={a['state']['urban_vehicles_mean']:8.1f} "
                  f"links_count={u['total_count_mean']:8.1f} spd={u['occupied_mean_speed_kph']:6.2f} "
                  f"stopped_mean={u['total_stopped_mean']:7.2f} stopped_share={u['stopped_share']*100:5.2f}%")
    print("\n=== ramp (meter connector links) ===")
    for tag in TAGS:
        for key in ("old", "new"):
            a = result[key].get(tag)
            if not a or not a["ramp"]:
                continue
            r = a["ramp"]
            print(f"{tag:<10} {key:<4} n_links={r['n_ramp_links']:3d} count_mean={r['total_count_mean']:7.2f} "
                  f"count_max={r['total_count_max']:7.1f} stopped_mean={r['total_stopped_mean']:6.2f} "
                  f"spd={r['occupied_mean_speed_kph']:6.2f}")
    print(f"\nJSON={args.out}")


if __name__ == "__main__":
    main()
