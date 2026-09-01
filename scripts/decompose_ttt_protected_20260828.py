# -*- coding: utf-8 -*-
"""우리 TTT 가 무엇을 세고 있는지 분해한다. 제어 권역 대 monitor 권역 대 freeway.

왜 (2026-08-28).

평가 지표를 `state_*.csv` 의 `total_vehicles` 합으로 쓰고 있는데, 권역 정본
`urban_player_territory_v1_20260819.json` 의 urban 권역은 **26개 SC** 를 담고
그중 제어는 **17개**뿐이다(SC102·103·104·106·SC2001~2005 아홉이 monitor).

monitor 노드는 러너가 COM 으로 안 건드리고 native 신호 프로그램대로 돈다. 즉 컨트롤러가
바꿀 수 없는 영역이다. 그 구간의 차량이 TTT 에 섞이면 효과가 희석되고 잡음만 늘어난다.

무엇을 세는가. 상태 JSON 의 `local_observation.link_counts`(관측 670링크)를 권역으로 갈라
스텝합 x 30초로 veh·h 를 낸다. 링크가 제어 SC 와 monitor SC 에 함께 걸리면 **제어 우선**이다
(보호망 경계 판정의 "경계면 우선" 규칙과 같은 방향 — 통제 가능한 쪽에 귀속).

산출: outputs/ttt_decomposition_20260828.json
"""
import argparse
import csv
import io
import json
import sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent

CONTROLLED = {"SC1", "SC5", "SC6", "SC7", "SC11", "SC12", "SC16", "SC101", "SC105",
              "SC107", "SC108", "SC109", "SC1001", "SC1002", "SC1003", "SC1004", "SC1005"}


def link_sets(territory_path: Path, detector_path: Path):
    doc = json.loads(territory_path.read_text(encoding="utf-8"))
    terr = doc.get("territory") or {}
    urban = terr.get("urban") or {}
    fwmap = terr.get("freeway") or {}

    ctrl, mon = set(), set()
    for sc, legs in urban.items():
        bag = ctrl if sc in CONTROLLED else mon
        if isinstance(legs, dict):
            for _leg, links in legs.items():
                bag.update(str(x) for x in (links or []))
        elif isinstance(legs, list):
            bag.update(str(x) for x in legs)
    mon -= ctrl                                  # 제어 우선
    fw = set()
    for _k, links in fwmap.items():
        fw.update(str(x) for x in (links or []))
    ctrl -= fw
    mon -= fw

    det = json.loads(detector_path.read_text(encoding="utf-8"))
    ramp = {str(k) for k in (det.get("ramp_link_to_queues") or {})}
    ctrl -= ramp
    mon -= ramp
    return {"controlled": ctrl, "monitor": mon, "freeway": fw, "ramp": ramp}


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
    ap.add_argument("--out", default="outputs/ttt_decomposition_20260828.json")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    sets = link_sets(R / args.territory, R / args.detector)
    print("권역 링크  제어 %d · monitor %d · freeway %d · ramp %d"
          % (len(sets["controlled"]), len(sets["monitor"]), len(sets["freeway"]), len(sets["ramp"])))

    res = {}
    for run in args.runs:
        d = R / "evaluation/runs" / run
        fs = sorted(d.glob("decisions_*/state_*.json"))
        if not fs:
            print("%-28s (상태 없음)" % run)
            continue
        acc = {k: 0.0 for k in sets}
        acc["unclassified"] = 0.0
        acc["observed_total"] = 0.0
        n = 0
        for f in fs:
            lo = json.loads(f.read_text(encoding="utf-8")).get("local_observation") or {}
            lc = lo.get("link_counts") or {}
            if not lc:
                continue
            n += 1
            for link, cnt in lc.items():
                c = float(cnt or 0.0)
                acc["observed_total"] += c
                lk = str(link)
                for key in ("controlled", "monitor", "freeway", "ramp"):
                    if lk in sets[key]:
                        acc[key] += c
                        break
                else:
                    acc["unclassified"] += c
        if not n:
            continue
        # 결정 간격 150s -> veh·h. 상태는 결정 시점 스냅샷이므로 150초를 대표시킨다.
        H = 150.0 / 3600.0
        res[run] = {k: v * H for k, v in acc.items()}
        res[run]["decisions"] = n
        # 러너 CSV 기준 TTT(30초 스캔)도 같이
        p = list(d.glob("state_%s.csv" % run))
        if p:
            rows = list(csv.DictReader(io.open(p[0], encoding="utf-8-sig")))
            res[run]["csv_total_ttt"] = sum(float(r.get("total_vehicles") or 0) for r in rows) * 30.0 / 3600.0

    print()
    print("%-24s %10s %10s %10s %9s %10s %10s"
          % ("팔", "제어권역", "monitor", "freeway", "ramp", "미분류", "CSV TTT"))
    for run, v in res.items():
        print("%-24s %10.1f %10.1f %10.1f %9.1f %10.1f %10.1f"
              % (run, v["controlled"], v["monitor"], v["freeway"], v["ramp"],
                 v["unclassified"], v.get("csv_total_ttt", 0.0)))

    base = res.get(args.baseline)
    if base:
        print()
        print("무제어 대비 (음수가 개선)")
        print("%-24s %12s %12s %12s %14s" % ("팔", "제어권역", "monitor", "freeway", "제어+freeway"))
        for run, v in res.items():
            if run == args.baseline:
                continue
            c = v["controlled"] - base["controlled"]
            m = v["monitor"] - base["monitor"]
            f = v["freeway"] - base["freeway"]
            print("%-24s %12.1f %12.1f %12.1f %14.1f" % (run, c, m, f, c + f))

    doc = {
        "schema_version": "ttt-decomposition/1",
        "generated": "2026-08-28",
        "why": "평가 TTT 가 total_vehicles 전량이라 컨트롤러가 못 건드리는 monitor 9개 SC 가 "
               "섞인다. 제어 권역 + freeway 만 보는 지표와 대조한다.",
        "controlled_sc": sorted(CONTROLLED),
        "link_counts": {k: len(v) for k, v in sets.items()},
        "runs": res,
    }
    (R / args.out).write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print()
    print("-> %s" % args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
