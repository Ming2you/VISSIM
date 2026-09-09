# -*- coding: utf-8 -*-
"""램프 미터 전달함수를 Ver2 에서 재측정한다 — green[s] -> 차로당·주기당 통과대수 (2026-09-09).

왜. 사다리 조각 METER 의 `per_lane_veh_per_cycle` 은 **옛 망(lcd1000)** 에서 잰 표다.
2026-09-08 사다리에서 METER+MF1 이 혼자 +203.8 veh·h 를 까먹었는데, 같은 사다리에서
**Ver2 에서 재측정한** 조각(SATV2)은 -181.3 으로 최대 이득을 냈다. 손해가 아이디어가 아니라
옆 망 상수 때문일 수 있다는 뜻이라, 이 표를 Ver2 자료로 다시 만든다.

어떻게. 어댑터는 이렇게 쓴다(vissim_stackelberg_adapter._meter_flow_vph):

    flow_vph = lanes * per_lane_veh_per_cycle[green] * 3600 / cycle_sec

그러므로 표의 값은 **차로 하나가 주기 하나에 통과시키는 대수**다. 실측에서 뒤집으면

    n(green) = volume_veh_h * cycle_sec / (3600 * lanes)

**계측기는 fzp 가 아니라 VISSIM 링크평가다.** 커넥터는 짧아서 5초 스냅샷 스캔이 체류 5초 미만
차량을 통째로 놓친다(CLAUDE.md 'far 배수율은 실측이다' 절: 150초 스냅샷 차분이 램프에서 250 vph
로 틀렸고 실측은 886 이었다). 상태 JSON 의 `local_observation.far_measurement.link_volume_veh_h`
가 그 링크평가이고 8개 RM 커넥터가 전부 들어 있다.

**시각 정렬.** 링크평가는 `Last` = 마지막으로 **완료된** 구간이다. 그래서 sim_sec T 의 상태가
보고하는 볼륨은 [T-150, T) 구간이고, 그 구간을 지배한 것은 T-150 에 커밋된 green 이다.
즉 action(T-150) <-> volume(T) 로 짝짓는다.

사용: python measure_meter_transfer_ver2_20260909.py <out_json> <run> [run...]
"""
import collections
import csv
import io
import json
import statistics
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
LANES = {"RM_C10482": 2.0, "RM_C10681": 2.0}      # 나머지는 1차로 (망에서 확인)
CYCLE_SEC = 10.0
MIN_SAMPLES = 3


def load_run(run):
    """(green_sec, meter_id) -> [veh/lane/cycle ...] 표본."""
    d = R / "evaluation/runs" / run
    acts = {}
    ap = d / ("action_%s.csv" % run)
    if not ap.is_file():
        return {}, "action CSV 없음"
    for r in csv.DictReader(io.open(ap, encoding="utf-8")):
        if r.get("kind") != "ramp_meter":
            continue
        try:
            t = float(r["sim_sec"]); g = float(r["green_sec"] or 0.0)
        except (TypeError, ValueError):
            continue
        acts[(t, r["id"])] = g

    out = collections.defaultdict(list)
    dd = list(d.glob("decisions_*"))
    if not dd:
        return {}, "decisions 없음"
    for sp in sorted(dd[0].glob("state_*.json")):
        try:
            js = json.load(io.open(sp, encoding="utf-8"))
        except Exception:
            continue
        t = float(js.get("sim_sec", 0.0))
        fm = ((js.get("local_observation") or {}).get("far_measurement") or {})
        lv = fm.get("link_volume_veh_h") or {}
        iv = float(fm.get("interval_sec") or 0.0)
        if not lv or iv <= 0:
            continue
        for mid, lanes in [(m, LANES.get(m, 1.0)) for m in
                           ("RM_C10480", "RM_C10482", "RM_C10484", "RM_C10490",
                            "RM_C10639", "RM_C10644", "RM_C10646", "RM_C10681")]:
            conn = mid.split("_C")[-1]
            if conn not in lv:
                continue
            g = acts.get((t - iv, mid))          # 이 볼륨을 지배한 green
            if g is None:
                continue
            n = float(lv[conn]) * CYCLE_SEC / (3600.0 * lanes)
            out[(int(round(g)), mid)].append(n)
    return out, None


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    outj, runs = sys.argv[1], sys.argv[2:]
    pooled = collections.defaultdict(list)
    per_meter = collections.defaultdict(list)
    for run in runs:
        s, err = load_run(run)
        if err:
            print("  %-50s %s" % (run[:50], err))
            continue
        n = sum(len(v) for v in s.values())
        print("  %-50s 표본 %d" % (run[:50], n))
        for (g, mid), vals in s.items():
            pooled[g].extend(vals)
            per_meter[(g, mid)].extend(vals)

    # **용량은 상위 포락선이다.** 미터가 완전개방이면 흐르는 것은 수요이지 용량이 아니라,
    # 중앙값은 그 구간의 수요를 잰다(실측: green=10 표본 1,143개의 중앙 0.90 < green=7 의 2.80).
    # 저장소 규율과 같다 — 'far 배수율은 실측이다' 절의 감쇠 러닝맥스도 용량을 추정한다.
    print("\n=== green[s] -> 차로당·주기당 통과대수 (Ver2 실측) ===")
    print("  %5s %7s %8s %8s %8s %8s   %s" % ("green", "표본", "중앙", "p90", "p95", "최대", "옛 표"))
    old = {2: 0.71, 3: 0.99, 4: 1.44, 5: 1.89, 6: 2.34, 7: 2.79, 8: 3.24, 9: 3.69, 10: 4.20}

    def q(v, f):
        return v[min(len(v) - 1, int(f * len(v)))]

    raw = {}
    for g in sorted(pooled):
        v = sorted(pooled[g])
        if not v:
            continue
        mark = "" if len(v) >= MIN_SAMPLES else "  (표본 부족)"
        print("  %5d %7d %8.3f %8.3f %8.3f %8.3f   %s%s"
              % (g, len(v), statistics.median(v), q(v, 0.90), q(v, 0.95), v[-1],
                 ("%.2f" % old[g]) if g in old else "-", mark))
        if len(v) >= MIN_SAMPLES and g > 0:
            raw[g] = q(v, 0.95)
    # 단조 보정: 용량은 green 에 대해 줄어들 수 없다. 표본이 얕은 칸이 아래로 튀면 위를 따라간다.
    table, run_max = {}, 0.0
    for g in sorted(raw):
        run_max = max(run_max, raw[g])
        table[str(g)] = round(run_max, 3)
    print("\n  단조 보정 후(p95 누적최대): %s" % table)

    print("\n=== 미터별 (green=10, 완전개방) ===")
    for (g, mid), vals in sorted(per_meter.items()):
        if g != 10 or len(vals) < MIN_SAMPLES:
            continue
        print("  %-12s 차로 %.0f  표본 %3d  중앙 %.3f  -> %.0f vph"
              % (mid, LANES.get(mid, 1.0), len(vals), statistics.median(vals),
                 LANES.get(mid, 1.0) * statistics.median(vals) * 3600.0 / CYCLE_SEC))

    doc = {"schema": "meter_transfer_v1", "generated": "2026-09-09",
           "source_runs": runs, "cycle_sec": CYCLE_SEC, "lanes": LANES,
           "instrument": "local_observation.far_measurement.link_volume_veh_h (VISSIM 링크평가 150 s). "
                         "fzp 5초 스캔은 커넥터 체류 5초 미만 차량을 놓치므로 쓰지 않는다.",
           "alignment": "링크평가 Last = 마지막 완료 구간. action(T-interval) <-> volume(T).",
           "min_samples": MIN_SAMPLES,
           "per_lane_veh_per_cycle": table,
           "old_table_lcd1000": old,
           "samples": {str(g): len(pooled[g]) for g in sorted(pooled)}}
    io.open(outj, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False, indent=1))
    print("\n-> %s  (항목 %d개)" % (outj, len(table)))


if __name__ == "__main__":
    main()
