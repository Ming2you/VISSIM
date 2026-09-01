# -*- coding: utf-8 -*-
"""밖에서 기다린 차량의 veh·h 를 팔마다 적분한다. 우리 TTT 가 빠뜨린 양이다.

왜 (2026-08-28).

우리 TTT 는 `total_vehicles` 합인데 `boundary_vehicles` 가 전 팔·전 스텝 0 이고 상태 JSON 에
경계 큐 수집 채널이 아예 없다. `.fzp` 는 **망 안 차량만** 적으므로 밖에 선 차를 직접 못 본다.
회계로 본다 — `.inpx` 가 요구한 누적 대수와 VISSIM 이 실제로 생성한 누적 대수의 차이가
그 시각에 밖에 있는 차다. 그것을 시간 적분하면 빠진 TTT[veh·h] 가 나온다.

    shortfall(t) = demand_until(t) - generated_until(t)
    missing_TTT  = integral shortfall(t) dt   [veh·h]

주의. vehicleInput 이 `volType="STOCHASTIC"` 이라 생성 대수는 요구 주위로 흔들린다.
실제로 shortfall 이 **음수로도 간다**(canon_nolencap 최소 -34). 그래서 절대값을 큐로
읽으면 안 되고, **팔 사이 차이**만 의미가 있다. 무제어를 기준으로 상대값을 같이 낸다.

산출: outputs/boundary_queue_ttt_20260828.json
"""
import argparse
import io
import json
import re
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent


def demand_schedule(inpx: Path, sim_period: float):
    """구간 시작[s] -> 총 유량[veh/h]. `timeInt="<set> <ms>"` 의 두 번째가 시작 밀리초다."""
    text = inpx.read_text(encoding="utf-8", errors="replace")
    m = re.search(r'<timeIntervalSet no="VEHICLEINPUT">(.*?)</timeIntervalSet>', text, re.S)
    if not m:
        raise ValueError("VEHICLEINPUT 시간구간 정의를 못 찾았다")
    starts = sorted(float(x) for x in re.findall(r'<timeInterval start="([\d.]+)"', m.group(1)))
    rate = {s: 0.0 for s in starts}
    for b in re.finditer(r"<vehicleInput ([^>]*)>(.*?)</vehicleInput>", text, re.S):
        for e in re.finditer(r'<timeIntervalVehVolume[^>]*timeInt="(\d+)\s+(\d+)"[^>]*volume="([\d.]+)"',
                             b.group(2)):
            st = float(e.group(2)) / 1000.0
            if st in rate:
                rate[st] += float(e.group(3))
    return starts, rate


def demand_until(T, starts, rate, sim_period):
    tot = 0.0
    for i, s in enumerate(starts):
        e = starts[i + 1] if i + 1 < len(starts) else sim_period
        tot += rate.get(s, 0.0) * max(0.0, min(e, T) - s) / 3600.0
    return tot


def scan_fzp(path: Path):
    """시각 -> 그 시각까지 본 최대 차량번호(=누적 생성)."""
    cum = {}
    with io.open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line or line[0] in "*$":
                continue
            i = line.find(";")
            if i < 0:
                continue
            j = line.find(";", i + 1)
            if j < 0:
                continue
            try:
                t = float(line[:i]); no = int(line[i + 1:j])
            except ValueError:
                continue
            if no > cum.get(t, 0):
                cum[t] = no
    ts = sorted(cum)
    run = 0
    out = []
    for t in ts:
        if cum[t] > run:
            run = cum[t]
        out.append((t, run))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="*", default=[
        "nocontrolstep_20260826", "tau_20260826", "bstoA_20260827",
        "canon_plantfix_20260827", "canon_dpoff_20260828", "canon_phasefix_20260828",
        "canon_nolencap_20260828", "canon_gne_far_20260827", "canon_ingne_20260828"])
    ap.add_argument("--inpx", default="network/real_world_gaepo_modi/modi_eval_userfix_20260814e.inpx")
    ap.add_argument("--sim-period", type=float, default=5400.0)
    ap.add_argument("--baseline", default="nocontrolstep_20260826")
    ap.add_argument("--out", default="outputs/boundary_queue_ttt_20260828.json")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    starts, rate = demand_schedule(R / args.inpx, args.sim_period)
    total_demand = demand_until(args.sim_period, starts, rate, args.sim_period)
    print("요구 대수 %.0f · 구간 %s" % (total_demand, [int(s) for s in starts]))
    print()

    res = {}
    for run in args.runs:
        fzs = sorted((R / "evaluation/runs" / run).glob("vissim_eval/*.fzp"))
        if not fzs:
            print("%-28s (.fzp 없음)" % run)
            continue
        series = scan_fzp(fzs[0])
        integ = 0.0
        prev_t = None
        prev_s = 0.0
        smin = smax = None
        for t, gen in series:
            s = demand_until(t, starts, rate, args.sim_period) - gen
            smin = s if smin is None else min(smin, s)
            smax = s if smax is None else max(smax, s)
            if prev_t is not None:
                integ += 0.5 * (s + prev_s) * (t - prev_t)     # veh·s
            prev_t, prev_s = t, s
        res[run] = {
            "generated_veh": series[-1][1],
            "shortfall_final": demand_until(series[-1][0], starts, rate, args.sim_period) - series[-1][1],
            "shortfall_min": smin,
            "shortfall_max": smax,
            "missing_ttt_veh_h": integ / 3600.0,
        }
        print("%-28s 생성 %6d · 미진입 최종 %6.0f (최소 %6.0f 최대 %6.0f) · 빠진 TTT %8.1f veh·h"
              % (run, res[run]["generated_veh"], res[run]["shortfall_final"],
                 smin, smax, res[run]["missing_ttt_veh_h"]))

    base = res.get(args.baseline)
    if base:
        print()
        print("%-28s %14s %14s" % ("팔", "빠진 TTT", "무제어 대비"))
        for run, d in sorted(res.items(), key=lambda kv: kv[1]["missing_ttt_veh_h"]):
            print("%-28s %14.1f %14.1f"
                  % (run, d["missing_ttt_veh_h"], d["missing_ttt_veh_h"] - base["missing_ttt_veh_h"]))

    doc = {
        "schema_version": "boundary-queue-ttt/1",
        "generated": "2026-08-28",
        "why": "우리 TTT 는 boundary_vehicles=0 이라 밖에 선 차를 안 센다. 그 양을 회계로 적분한다.",
        "caveat": "vehicleInput 이 STOCHASTIC 이라 shortfall 이 음수로도 간다. 절대값을 큐로 "
                  "읽지 말고 팔 사이 차이만 읽어라.",
        "inpx": args.inpx,
        "total_demand_veh": total_demand,
        "baseline": args.baseline,
        "runs": res,
    }
    (R / args.out).write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print()
    print("-> %s" % args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
