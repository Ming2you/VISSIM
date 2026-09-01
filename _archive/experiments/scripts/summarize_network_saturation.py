# 런별 네트워크 포화 요약 — 도시부가 과포화되지 않았는지 확인하는 용도.
#
# 램프 지향 수요를 키우거나 route 를 재설계할 때, 램프만 채우고 도시부 격자는
# 건드리지 않는 것이 목표다. 그게 지켜졌는지 한 줄로 본다.
# 기준값(2026-08-04 v6 앵커): urban 4,594 / total 6,880 / 정지율 30.2 % / 평균 32.7 kph.
#
# 사용:
#   python scripts/summarize_network_saturation.py --case "라벨:decisions_dir" [--case ...] [--t0 2700]
import argparse
import glob
import io
import json
import os
import statistics as st
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", action="append", required=True, help="라벨:decisions_dir")
    ap.add_argument("--t0", type=float, default=2700.0)
    ap.add_argument("--json-out", default="")
    args = ap.parse_args()

    print(f"{'라벨':<14}{'도시부':>8}{'고속':>7}{'램프':>7}{'총':>8}{'정지':>7}{'정지율':>8}"
          f"{'평균v':>8}{'고속v':>8}{'스텝':>6}")
    payload = {}
    for spec in args.case:
        if ":" not in spec:
            print(f"SKIP 형식 오류: {spec}")
            continue
        label, d = spec.split(":", 1)
        paths = [p for p in sorted(glob.glob(os.path.join(d, "state_*.json")))
                 if os.path.basename(p)[6:12].isdigit() and int(os.path.basename(p)[6:12]) >= args.t0]
        if not paths:
            print(f"{label:<14}(상태 파일 없음: {d})")
            continue
        acc = {k: [] for k in ("urban", "freeway", "ramp", "total", "stopped", "mean", "fmean")}
        for p in paths:
            s = json.load(open(p, encoding="utf-8"))
            acc["urban"].append(float(s.get("urban_vehicles", 0)))
            acc["freeway"].append(float(s.get("freeway_vehicles", 0)))
            acc["ramp"].append(float(s.get("ramp_vehicles", 0)))
            acc["total"].append(float(s.get("total_vehicles", 0)))
            acc["stopped"].append(float(s.get("stopped_vehicles", 0)))
            acc["mean"].append(float(s.get("mean_speed_kph", 0)))
            acc["fmean"].append(float(s.get("freeway_mean_speed_kph", 0)))
        m = {k: st.median(v) for k, v in acc.items()}
        rate = 100.0 * m["stopped"] / max(m["total"], 1.0)
        print(f"{label:<14}{m['urban']:>8.0f}{m['freeway']:>7.0f}{m['ramp']:>7.0f}{m['total']:>8.0f}"
              f"{m['stopped']:>7.0f}{rate:>7.1f}%{m['mean']:>8.1f}{m['fmean']:>8.1f}{len(paths):>6}")
        payload[label] = dict(m, stopped_pct=rate, steps=len(paths))

    if args.json_out:
        os.makedirs(os.path.dirname(os.path.abspath(args.json_out)) or ".", exist_ok=True)
        json.dump(payload, open(args.json_out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"\nJSON={args.json_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
