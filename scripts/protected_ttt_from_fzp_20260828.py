# -*- coding: utf-8 -*-
"""`.fzp` 로 TTT 를 권역별로 정확히 분해한다. 제어 17 SC · monitor 9 SC · freeway · ramp.

왜 (2026-08-28).

평가 지표가 `state_*.csv` 의 `total_vehicles` 전량인데, 권역 정본의 urban 은 **26개 SC** 를
담고 그중 제어는 **17개**뿐이다. 나머지 아홉(SC102·103·104·106·SC2001~2005)은 monitor 라
러너가 COM 으로 건드리지 않고 native 신호대로 돈다. 컨트롤러가 못 바꾸는 영역이다.

상태 JSON 의 `local_observation` 으로 갈라 봤더니 monitor 가 관측 차량시간의 18~19% 였고
제어를 켤 때마다 그 구간이 나빠졌다(+27~+43 veh·h). 다만 그 계산은 결정 시점 스냅샷
(150초 간격 37점)이라 러너 CSV(30초 간격)와 적분 해상도가 다르고, 관측 못 하는 링크가
팔마다 다르게 빠진다(무제어는 CSV 대비 86 낮고 nolencap 은 17.7 낮았다).

`.fzp` 는 그 문제가 없다 — **5초 간격 전 차량**이고 링크가 행마다 찍혀 있다. 여기서
분해하면 표본 누락도 해상도 차이도 없다.

    TTT_구역 = (구역 링크 위 차량 수의 시각별 합) x dt / 3600   [veh·h]

산출: outputs/protected_ttt_20260828.json
"""
import argparse
import json
import io
import sys
from collections import defaultdict
from pathlib import Path

R = Path(__file__).resolve().parent.parent

CONTROLLED = {"SC1", "SC5", "SC6", "SC7", "SC11", "SC12", "SC16", "SC101", "SC105",
              "SC107", "SC108", "SC109", "SC1001", "SC1002", "SC1003", "SC1004", "SC1005"}


def link_sets(territory_path: Path, detector_path: Path):
    doc = json.loads(territory_path.read_text(encoding="utf-8"))
    terr = doc.get("territory") or {}
    ctrl, mon = set(), set()
    for sc, legs in (terr.get("urban") or {}).items():
        bag = ctrl if sc in CONTROLLED else mon
        if isinstance(legs, dict):
            for _leg, links in legs.items():
                bag.update(str(x) for x in (links or []))
        elif isinstance(legs, list):
            bag.update(str(x) for x in legs)
    mon -= ctrl                                   # 제어 우선 귀속
    fw = set()
    for _k, links in (terr.get("freeway") or {}).items():
        fw.update(str(x) for x in (links or []))
    ctrl -= fw
    mon -= fw
    det = json.loads(detector_path.read_text(encoding="utf-8"))
    ramp = {str(k) for k in (det.get("ramp_link_to_queues") or {})}
    ctrl -= ramp
    mon -= ramp
    return {"controlled": ctrl, "monitor": mon, "freeway": fw, "ramp": ramp}


def scan(fzp: Path, sets):
    """시각별 구역 차량 수 -> 구역 TTT[veh·h]. dt 는 기록 간격에서 유도한다."""
    per_t = defaultdict(lambda: defaultdict(float))
    keys = ("controlled", "monitor", "freeway", "ramp")
    lookup = {}
    for k in keys:
        for lk in sets[k]:
            lookup[lk] = k
    with io.open(fzp, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line or line[0] in "*$":
                continue
            a = line.find(";")
            if a < 0:
                continue
            b = line.find(";", a + 1)
            c = line.find(";", b + 1)
            if b < 0 or c < 0:
                continue
            try:
                t = float(line[:a])
            except ValueError:
                continue
            per_t[t][lookup.get(line[b + 1:c], "other")] += 1.0
    ts = sorted(per_t)
    if len(ts) < 2:
        return None
    dt = ts[1] - ts[0]
    out = {k: 0.0 for k in keys}
    out["other"] = 0.0
    for t in ts:
        for k, v in per_t[t].items():
            out[k] = out.get(k, 0.0) + v
    for k in list(out):
        out[k] = out[k] * dt / 3600.0
    out["dt_sec"] = dt
    out["time_steps"] = len(ts)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="*", default=[
        "nocontrolstep_20260826", "tau_20260826", "bstoA_20260827",
        "canon_plantfix_20260827", "canon_dpoff_20260828", "canon_phasefix_20260828",
        "canon_nolencap_20260828", "canon_gne_far_20260827", "canon_ingne_20260828"])
    ap.add_argument("--territory", default="outputs/urban_player_territory_v1_20260819.json")
    ap.add_argument("--detector", default="evaluation/real_world_modi_control_distributed_20260728/"
                                          "detector_local_mapping_distributed_core17legs4f_20260826.json")
    ap.add_argument("--baseline", default="nocontrolstep_20260826")
    ap.add_argument("--out", default="outputs/protected_ttt_20260828.json")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    sets = link_sets(R / args.territory, R / args.detector)
    print("권역 링크  제어 %d · monitor %d · freeway %d · ramp %d"
          % (len(sets["controlled"]), len(sets["monitor"]), len(sets["freeway"]), len(sets["ramp"])))
    print()

    res = {}
    for run in args.runs:
        fzs = sorted((R / "evaluation/runs" / run).glob("vissim_eval/*.fzp"))
        if not fzs:
            print("%-26s (.fzp 없음)" % run)
            continue
        v = scan(fzs[0], sets)
        if v is None:
            continue
        v["protected_plus_freeway"] = v["controlled"] + v["freeway"] + v["ramp"]
        v["all"] = v["controlled"] + v["monitor"] + v["freeway"] + v["ramp"] + v["other"]
        res[run] = v
        print("%-26s 제어 %8.1f · monitor %7.1f · freeway %7.1f · ramp %6.1f · 기타 %6.1f · 전체 %8.1f"
              % (run, v["controlled"], v["monitor"], v["freeway"], v["ramp"], v["other"], v["all"]))

    base = res.get(args.baseline)
    if base:
        print()
        print("무제어 대비 (음수가 개선)")
        print("%-26s %12s %12s %12s %16s %12s"
              % ("팔", "제어권역", "monitor", "freeway", "제어+fw+ramp", "전체"))
        rows = sorted(res.items(), key=lambda kv: kv[1]["protected_plus_freeway"])
        for run, v in rows:
            if run == args.baseline:
                continue
            print("%-26s %12.1f %12.1f %12.1f %16.1f %12.1f"
                  % (run, v["controlled"] - base["controlled"], v["monitor"] - base["monitor"],
                     v["freeway"] - base["freeway"],
                     v["protected_plus_freeway"] - base["protected_plus_freeway"],
                     v["all"] - base["all"]))
        print()
        print("monitor 몫: %.1f%% ~ %.1f%%"
              % (100 * min(v["monitor"] / v["all"] for v in res.values()),
                 100 * max(v["monitor"] / v["all"] for v in res.values())))

    doc = {
        "schema_version": "protected-ttt/1",
        "generated": "2026-08-28",
        "why": "평가 TTT 가 전량이라 제어 불가능한 monitor 9개 SC 가 섞인다. .fzp 5초 해상도로 분해한다.",
        "controlled_sc": sorted(CONTROLLED),
        "link_counts": {k: len(v) for k, v in sets.items()},
        "baseline": args.baseline,
        "runs": res,
    }
    (R / args.out).write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print()
    print("-> %s" % args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
