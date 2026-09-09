# -*- coding: utf-8 -*-
"""수요 수준별 무제어 런 진단 — 정본 수요를 고르기 위한 표 (2026-09-07).

무엇을 재나 (결정 상태 파일의 vehicle_records 로, fzp 재독 없이):
  실현 진입   : link 74(EB) · link 26(NB) 에 새로 나타난 차량 수 / 구간 → veh/h
  요구 수요   : .inpx 프로파일 x 본선 배율 (구간 900 s)
  미실현      : 요구 - 실현. 원점에 붙잡힌 몫이다(TTT 에 안 잡히므로 수요를 올려도 안 보인다).
  통과        : 각 방향 마지막 세그먼트 이탈 = 실제로 회랑을 통과한 유량
사용: python demand_level_report_20260907.py
"""
import io, json, re, glob, sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE_PROFILE = [5544.0, 7920.0, 8316.0, 7128.0, 5544.0, 3960.0]      # 900 s 구간 6개 (x18 기준)
RUNS = [("x04", 0.2222, "fd_x04_nocontrol_ver2_20260907"),
        ("x08", 0.4444, "fd_x08_nocontrol_ver2_20260907"),
        ("x12", 0.6667, "fd_x12_nocontrol_ver2_20260907"),
        ("x15", 0.8333, "fd_x15_nocontrol_ver2_20260907"),
        ("x18", 1.0000, "v0_nocontrol_ver2_x18_20260907")]
ENTRY = {"74": "FW_E", "26": "FW_W"}


def entries(run):
    D = R / "evaluation/runs" / run / ("decisions_%s" % run)
    files = sorted(glob.glob(str(D / "state_*.json")), key=lambda p: int(re.search(r"(\d+)\.json", p).group(1)))
    seen = set()
    ent = {"FW_E": 0, "FW_W": 0}
    tprev = None
    t0 = t1 = None
    for p in files:
        t = int(re.search(r"(\d+)\.json", p).group(1))
        j = json.load(io.open(p, encoding="utf-8"))
        recs = (j.get("vehicle_records") or {}).get("records") or []
        for r in recs:
            v = r.get("veh_no")
            if v in seen:
                continue
            seen.add(v)
            d = ENTRY.get(str(r.get("link_no")))
            if d and t >= 900:
                ent[d] += 1
        if t >= 900:
            if t0 is None:
                t0 = t
            t1 = t
    span_h = max(1e-9, (t1 - t0) / 3600.0) if t0 is not None else 1.0
    return {k: v / span_h for k, v in ent.items()}, (t0, t1)


def main():
    print("본선 수요 sweep 진단 — 도시 수요는 전 수준 1.00 고정")
    print("실현 진입은 t>=900 결정 상태의 신규 차량(150 s 간격 스냅샷이라 짧은 체류는 과소).\n")
    print("%-5s %8s | %-28s | %-28s" % ("수준", "첨두수요", "FW_E (진입 74, 4차로)", "FW_W (진입 26, 3차로)"))
    print("%-5s %8s | %9s %9s %8s | %9s %9s %8s" % ("", "vph", "요구", "실현", "미실현%", "요구", "실현", "미실현%"))
    CAP = {"FW_E": 2024.0 * 4, "FW_W": 1867.0 * 3}
    for tag, mult, run in RUNS:
        prof = [v * mult for v in BASE_PROFILE]
        # t>=900 구간 = 프로파일 구간 2~6 (900~5400)
        demand_mean = sum(prof[1:]) / 5.0
        try:
            realized, span = entries(run)
        except Exception as exc:
            print("%-5s  런 없음/오류 %s" % (tag, exc))
            continue
        cells = []
        for d in ("FW_E", "FW_W"):
            req = demand_mean
            got = realized[d]
            miss = 100.0 * max(0.0, req - got) / max(req, 1e-9)
            cells.append((req, got, miss))
        print("%-5s %8.0f | %9.0f %9.0f %7.1f%% | %9.0f %9.0f %7.1f%%" % (
            tag, max(prof), cells[0][0], cells[0][1], cells[0][2], cells[1][0], cells[1][1], cells[1][2]))
    print("\n실측 평지 용량 기준선: FW_E 4차로 %.0f vph · FW_W 3차로 %.0f vph" % (CAP["FW_E"], CAP["FW_W"]))
    print("(위빙 셀 용량은 더 낮다 — E S3 925/차로 = 3700 vph, W S2 1508/차로 = 4524 vph)")


if __name__ == "__main__":
    main()
