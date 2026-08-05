# 강제응답 그리드 - 합류(delta_merge) 여기 확인용 보조 분석.
#
# delta_merge 는 합류 유입 r_i 가 변해야만 식별된다. 램프 미터링을 조여도
# 램프 수요 자체가 미터링률보다 낮으면 r_i 가 안 변하고 항이 죽는다.
# 그래서 두 가지를 본다.
#  1) 램프 링크 점유(대기 형성) - 미터링이 실제로 구속하는가.
#  2) 합류 세그먼트 밀도/속도의 arm 간 차이 - r_i 변화가 본선에 보이는가.

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd

# calibration ramp_meter_connectors 의 from_link
RAMP_LINKS = [31, 32, 68, 69, 70]
MERGE_SEGMENTS = ["RW_FW_W_S2", "RW_FW_W_S4", "RW_FW_W_S5", "RW_FW_E_S3", "RW_FW_E_S5"]
NAME_RE = re.compile(r"^(?P<dem>fw\d+)_(?P<arm>[a-z0-9]+)_seed(?P<seed>\d+)$")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--run-dir", required=True)
    p.add_argument("--lo-sec", type=int, default=900)
    p.add_argument("--hi-sec", type=int, default=4500)
    p.add_argument("--out-csv", required=True)
    args = p.parse_args()

    rows = []
    for seg in sorted(Path(args.run_dir).glob("bottleneck_segments_*.csv")):
        name = seg.stem[len("bottleneck_segments_"):]
        m = NAME_RE.match(name)
        if not m:
            continue
        rec = {"name": name, **m.groupdict()}
        d = pd.read_csv(seg)
        w = d[(d.sim_sec >= args.lo_sec) & (d.sim_sec <= args.hi_sec)]
        mg = w[w.segment_id.isin(MERGE_SEGMENTS)]
        rec["merge_rho_mean"] = float(mg.density_veh_km_lane.mean())
        rec["merge_v_mean"] = float(mg.mean_speed_kph.mean())
        nm = w[~w.segment_id.isin(MERGE_SEGMENTS)]
        rec["nonmerge_rho_mean"] = float(nm.density_veh_km_lane.mean())
        rec["merge_minus_nonmerge_rho"] = rec["merge_rho_mean"] - rec["nonmerge_rho_mean"]

        link_csv = seg.parent / f"bottleneck_links_{name}.csv"
        if link_csv.exists():
            L = pd.read_csv(link_csv)
            Lw = L[(L.sim_sec >= args.lo_sec) & (L.sim_sec <= args.hi_sec)]
            r = Lw[Lw.link.isin(RAMP_LINKS)]
            rec["ramp_link_count_mean"] = float(r["count"].mean()) if len(r) else float("nan")
            rec["ramp_link_count_p95"] = float(r["count"].quantile(0.95)) if len(r) else float("nan")
            rec["ramp_link_stopped_mean"] = float(r["stopped_count"].mean()) if len(r) else float("nan")
            per = r.groupby("link")["count"].mean().round(2).to_dict()
            rec["ramp_link_count_by_link"] = json.dumps({int(k): v for k, v in per.items()})
        rows.append(rec)

    df = pd.DataFrame(rows).sort_values(["dem", "seed", "arm"])
    Path(args.out_csv).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.out_csv, index=False, encoding="utf-8-sig")
    show = ["name", "merge_rho_mean", "merge_v_mean", "merge_minus_nonmerge_rho",
            "ramp_link_count_mean", "ramp_link_count_p95", "ramp_link_stopped_mean"]
    print(df[[c for c in show if c in df.columns]].to_string(index=False))


if __name__ == "__main__":
    main()
