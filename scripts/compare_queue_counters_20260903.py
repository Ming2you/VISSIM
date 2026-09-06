# -*- coding: utf-8 -*-
"""VISSIM 큐 카운터 대 우리 파생 큐 — 대조.

왜. 지금 큐 관측은 결정 시점의 **순간 표본**이고, 제어주기(150s)가 신호주기(150s)와
같아 그 표본이 늘 신호 위상의 같은 지점에 떨어진다. SC105 실측: SG1 은 항상 적색
30초째, SG3 은 항상 149초째(최소=최대). 큐가 적색 경과에 비례해 쌓이므로 공정한
기준(주기평균 R/2) 대비 0.51~2.41 배로 어긋난다. .fzp 지상검증에서도 링크 102개의
결정시점/주기평균 비가 0.36~2.45(상대 6.8배)였다.

VISSIM 큐 카운터는 매 시뮬 스텝으로 재고 구간 집계를 내므로 그 편향이 원천에서 없다.
이 스크립트는 둘을 맞대어 **우리 파생 큐가 얼마나 틀렸는지**를 숫자로 낸다.

쓰는 법:
    python scripts/compare_queue_counters_20260903.py --run smoke_qc_20260903
"""
from __future__ import annotations
import argparse, collections, glob, io, json, os, statistics as st, sys
from pathlib import Path

R = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_counter_map():
    p = R / "outputs/queue_counter_map_20260903.json"
    if not p.is_file():
        return {}
    return json.loads(p.read_text(encoding="utf-8")).get("counters") or {}


def derived_queues(state_json, cfg, TrafficState, dm, cal, adapter):
    s = adapter.traffic_state_from_vissim(state_json, cfg, TrafficState, dm, cal)
    return s


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--config", default="evaluation/configs/canon_outflow_d00_x18_20260901.json")
    a = ap.parse_args(argv)

    d = R / "evaluation/runs" / a.run
    states = sorted(glob.glob(str(d / ("decisions_%s" % a.run) / "state_*.json")))
    if not states:
        print("상태 파일 없음: %s" % d); return 2

    cmap = load_counter_map()
    print("카운터 대장 %d개" % len(cmap))

    # 1) 카운터가 실제로 나오는가
    got, miss, neg = 0, 0, 0
    series = collections.defaultdict(list)
    for f in states:
        sj = json.loads(io.open(f, encoding="utf-8").read())
        qc = (sj.get("local_observation") or {}).get("queue_counters")
        if not isinstance(qc, dict):
            miss += 1; continue
        got += 1
        for no, v in (qc.get("counters") or {}).items():
            if isinstance(v, list) and len(v) >= 2:
                if v[0] < 0: neg += 1
                series[str(no)].append((float(v[0]), float(v[1])))
    print("결정 %d개 중 queue_counters 있음 %d · 없음 %d · QLen<0(읽기실패) %d" % (len(states), got, miss, neg))
    if not got:
        print("\n**카운터가 안 나온다.** 확인할 것: RW_QUEUE_COUNTER=1 · 망이 _qc.inpx 인가 ·"
              " 런로그에 QUEUE_COUNTER=1 이 찍혔나")
        return 1

    print("\n=== 램프 카운터 (신규 8개) ===")
    print("%-8s %-8s %-10s %10s %10s" % ("no", "램프", "링크", "QLen중앙", "QLenMax중앙"))
    for no in sorted(k for k, v in cmap.items() if v.get("ramp")):
        vs = series.get(no) or []
        if not vs:
            print("%-8s %-8s %-10s %10s %10s" % (no, cmap[no]["ramp"], cmap[no]["link"], "-", "-")); continue
        print("%-8s %-8s %-10s %10.1f %10.1f" % (
            no, cmap[no]["ramp"], cmap[no]["link"],
            st.median(x[0] for x in vs), st.median(x[1] for x in vs)))

    print("\n=== 도시 카운터 상위 12 (QLen 중앙 큰 순) ===")
    rows = []
    for no, vs in series.items():
        if not vs or cmap.get(no, {}).get("ramp"):
            continue
        rows.append((no, cmap.get(no, {}).get("name") or "",
                     cmap.get(no, {}).get("link") or "",
                     st.median(x[0] for x in vs), st.median(x[1] for x in vs),
                     ";".join((cmap.get(no, {}).get("legs") or [])[:2])))
    rows.sort(key=lambda r: -r[3])
    print("%-8s %-22s %-11s %9s %9s  %s" % ("no", "이름", "링크", "QLen", "QLenMax", "leg"))
    for r in rows[:12]:
        print("%-8s %-22s %-11s %9.1f %9.1f  %s" % r)

    # 2) 파생 큐와 대조
    sys.path.insert(0, str(R)); sys.path.insert(0, str(R / "vendor/NumSim-mine"))
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "qb", R / "evaluation/controllers/vissim_stackelberg_adapter.py")
    qb = importlib.util.module_from_spec(spec); spec.loader.exec_module(qb)
    tun = qb.load_optional_json(str(R / a.config)); qb.install_config_switches(tun)
    cal = qb.load_optional_json(str(R / "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json"))
    cfg = qb.build_config(R / "vendor/NumSim-mine", 150.0, 5400.0, "wu-link", cal, tun,
                          local_observation=True, flagship=True)
    cm = qb.load_optional_json(str(R / "evaluation/real_world_modi_control_distributed_20260728/control_mapping_distributed_core17legs4b_20260819.json"))
    cm, _ = qb.install_merged_movements(cfg, tun, cm)
    dm = qb.load_optional_json(str(R / tun["detector_mapping_json"]))
    from src.models.state import TrafficState  # noqa

    print("\n=== 램프: 카운터 대 파생(피더 역산) ===")
    print("%-8s %12s %12s %10s" % ("램프", "카운터합", "파생", "비"))
    agg = collections.defaultdict(lambda: [[], []])
    for f in states:
        sj = json.loads(io.open(f, encoding="utf-8").read())
        qc = (sj.get("local_observation") or {}).get("queue_counters")
        if not isinstance(qc, dict): continue
        s = qb.traffic_state_from_vissim(sj, cfg, TrafficState, dm, cal)
        by = collections.defaultdict(float)
        for no, v in (qc.get("counters") or {}).items():
            rp = cmap.get(str(no), {}).get("ramp")
            if rp and isinstance(v, list) and v[0] >= 0: by[rp] += v[0]
        for rp in cfg.network.ramps:
            agg[rp][0].append(by.get(rp, 0.0))
            agg[rp][1].append(float(s.ramp_queue.get(rp, 0.0)))
    for rp in sorted(agg):
        c, dv = agg[rp]
        if not c: continue
        mc, md = st.median(c), st.median(dv)
        print("%-8s %12.1f %12.1f %10s" % (rp, mc, md, ("%.2f" % (mc / md)) if md > 0 else "-"))
    print("\n(카운터는 미터 정지선에서 상류 500m, 파생은 검지 링크 count 배분. 비가 1 에서 멀면 둘 중 하나가 틀렸다)")

    # 3) 위상편향 검증 — 카운터가 구간집계라면 결정시점 잠금이 없어야 한다
    print("")
    print("=== 위상편향: SC105 현시별 파생 큐 대 카운터 ===")
    print("결정시점 파생 큐는 적색 경과에 잠겨 왜곡된다 (SG1 항상 30초째 · SG3 항상 149초째,")
    print("공정기준 R/2 대비 0.51~2.41 배). 카운터는 구간집계라 그 잠금이 없어야 한다.")
    byph = collections.defaultdict(list)
    for f in states:
        sj = json.loads(io.open(f, encoding="utf-8").read())
        if not isinstance((sj.get("local_observation") or {}).get("queue_counters"), dict):
            continue
        s = qb.traffic_state_from_vissim(sj, cfg, TrafficState, dm, cal)
        d = collections.defaultdict(float)
        for m, spec in cfg.network.urban_movements.items():
            if str(spec.get("signal")) == "SC105":
                d[str(spec.get("phase"))] += float(s.urban_movement_queue.get(m, 0.0))
        for ph in ("SC105_p1", "SC105_p2", "SC105_p3", "SC105_p4"):
            byph[ph].append(d.get(ph, 0.0))
    tot = sum(st.median(v) for v in byph.values() if v) or 1.0
    BIAS = {"SC105_p1": 1.62, "SC105_p2": 2.41, "SC105_p3": 1.19, "SC105_p4": 0.51}
    print("%-12s %10s %7s %10s %7s" % ("현시", "파생", "몫", "편향보정", "몫"))
    adj = {ph: st.median(v) / BIAS.get(ph, 1.0) for ph, v in byph.items() if v}
    ta = sum(adj.values()) or 1.0
    for ph in sorted(byph):
        if not byph[ph]: continue
        m = st.median(byph[ph])
        print("%-12s %10.1f %6.0f%% %10.1f %6.0f%%" % (ph, m, 100 * m / tot, adj[ph], 100 * adj[ph] / ta))
    sc105 = {no: v for no, v in cmap.items()
             if any(str(l).startswith("SC105|") for l in (v.get("legs") or []))}
    print("")
    print("SC105 를 덮는 카운터 %d개 (QLen 큰 순):" % len(sc105))
    rank = sorted((no for no in sc105 if series.get(no)),
                  key=lambda k: -st.median([x[0] for x in series[k]]))
    for no in rank[:8]:
        vs = series[no]
        print("   no=%-8s link=%-11s QLen %7.1f  QLenMax %7.1f  %s" % (
            no, sc105[no]["link"], st.median(x[0] for x in vs), st.median(x[1] for x in vs),
            ";".join((sc105[no].get("legs") or [])[:2])))
    print("")
    print("(현시 단위로 맞추려면 카운터->movement 매핑이 더 필요하다. 지금은 leg 까지 신뢰한다)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
