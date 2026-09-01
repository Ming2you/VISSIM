"""far 저수지 방류율을 .fzp 차량궤적에서 직접 잰다 (2026-09-01).

왜 .fzp 인가. scripts/measure_far_reservoir_rates_20260901.py 는 decisions_*/state_*.json
스냅샷(150초 간격)을 대조한다 — 구간 경계에서만 보므로 구간 안에서 들어왔다 나간
차량을 놓친다. .fzp 는 훨씬 촘촘한 원자료라 그 누락을 메운다.

**해상도 주의.** 이 .fzp 는 1초가 아니라 5초 간격이다
(SimSec 1,6,11,...,5396; 델타 5.0 이 1079/1079). 따라서
  - A/B (urban·fw 이탈) 는 5초 전이 30개를 150초 구간마다 합산한다. 저수지가 크므로
    5초 안에 들어왔다 나가는 차량은 사실상 없다 — 견고하다.
  - C (램프 미터 커넥터) 는 커넥터가 짧아 5초 안에 통과하면 한 번도 안 찍힌다.
    그래서 두 가지를 다 낸다:
      conn  = 커넥터에 나타난 유일 차량 수 (과제가 지정한 정의)
      cross = 상류->하류 전이 계수 (커넥터 스냅샷을 건너뛴 차량까지 포함)

저수지 링크 집합은 scripts/measure_far_reservoir_rates_20260901.py 의 link_sets()
를 그대로 import 해서 쓴다 (권역 정본에서 유도).
"""
from __future__ import annotations
import argparse, importlib.util, json, sys, time
from pathlib import Path

R = Path(__file__).resolve().parents[1]


def _load_link_sets():
    p = R / "scripts/measure_far_reservoir_rates_20260901.py"
    spec = importlib.util.spec_from_file_location("_far_res", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.link_sets(), m.RAMP_CONN


def stats(xs, decay, tc):
    if not xs:
        return {}
    est = 0.0
    for x in xs:
        est = max(x, decay * est)
    return {"mean_veh_per_Tc": round(sum(xs) / len(xs), 2),
            "max_veh_per_Tc": round(max(xs), 1),
            "runmax_decay_veh_per_Tc": round(est, 2),
            "mean_veh_h": round(sum(xs) / len(xs) * 3600.0 / tc, 1),
            "max_veh_h": round(max(xs) * 3600.0 / tc, 1),
            "runmax_decay_veh_h": round(est * 3600.0 / tc, 1)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fzp", default="evaluation/runs/canon_ramparr_20260831/vissim_eval/"
                                     "modi_eval_userfix_20260814e_001.fzp")
    ap.add_argument("--tc-sec", type=float, default=150.0)
    ap.add_argument("--decay", type=float, default=0.98)
    # 900 s 는 calibrate_ramp_arrival_20260830.py 의 t0 와 같다. 그 아래는 망 채우는 과도구간.
    ap.add_argument("--warmup-sec", type=float, default=900.0)
    ap.add_argument("--out", default="outputs/far_rates_fzp_truth_20260901.json")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    TC = a.tc_sec

    S, RAMP_CONN = _load_link_sets()
    URBAN, FW = S["urban"], S["fw"]
    RAMPS = list(RAMP_CONN)
    CONN2R = {c: r for r, tr in RAMP_CONN.items() for (c, _f, _t) in tr}
    # (상류링크, 하류링크) -> 램프.  커넥터 스냅샷을 건너뛴 차량을 잡는다.
    PAIR2R = {(f, t): r for r, tr in RAMP_CONN.items() for (_c, f, t) in tr}
    RAMP_UNIV = set(CONN2R) | {x for p in PAIR2R for x in p}
    print("저수지: urban %d - fw %d - ramp %s"
          % (len(URBAN), len(FW), {r: len(S["ramp_" + r]) for r in RAMPS}))
    print("fw 링크: %s" % sorted(FW, key=int))
    print("램프 전이쌍: %s" % {"%s->%s" % (f, t): r for (f, t), r in PAIR2R.items()})

    path = R / a.fzp
    A, B = {}, {}                                  # bin -> exit count
    Cc = {}                                        # bin -> {ramp: set(veh)}  커넥터 관측
    Cx = {}                                        # bin -> {ramp: set(veh)}  전이 계수
    ntrans = {}                                    # bin -> 5초 전이 수
    conn_dwell = {r: 0 for r in RAMPS}
    conn_veh = {r: set() for r in RAMPS}
    cross_veh = {r: set() for r in RAMPS}
    # 창 단위 유일차량 (구간별 유일수의 합이 아니다 — 구간경계를 걸친 차량 중복을 없앤다).
    # calibrate_ramp_arrival_20260830.throughput_from_fzp 와 정의가 동일하다.
    win_veh = {r: set() for r in RAMPS}
    # 합류 '사건' 수 (유일차량 수가 아니다). 일부 차량은 램프를 두 번 이상 통과한다 —
    # 31->10480->26->...->32->10490->2->...->31 로 도는 폐루프 경로가 존재한다(주기 ~120s).
    # 유량 측정에서는 그 반복을 각각 세는 것이 맞다.
    cross_events = {r: 0 for r in RAMPS}
    cross_n = {}                                   # (veh, ramp) -> 통과 횟수

    prev_u, prev_f, prev_ramp = set(), set(), {}
    cur_u, cur_f, cur_ramp = set(), set(), {}
    cur_t = None
    nrec = 0
    t0 = time.time()

    def flush(t):
        """스냅샷 t 완성 -> 직전 스냅샷과 대조."""
        nonlocal prev_u, prev_f, prev_ramp
        b = int((t - 1) // TC)
        if prev_u or prev_f or prev_ramp:
            A[b] = A.get(b, 0) + len(prev_u - cur_u)
            B[b] = B.get(b, 0) + len(prev_f - cur_f)
            ntrans[b] = ntrans.get(b, 0) + 1
            cxb = Cx.setdefault(b, {r: set() for r in RAMPS})
            for v, pl in prev_ramp.items():
                cl = cur_ramp.get(v)
                if cl == pl:
                    continue
                r = None
                if pl in CONN2R:                    # 커넥터를 떠났다 = 합류 완료
                    r = CONN2R[pl]
                elif cl is not None:
                    r = PAIR2R.get((pl, cl))        # 커넥터 관측을 건너뛴 경우
                if r is not None:
                    cxb[r].add(v)
                    cross_veh[r].add(v)
                    cross_events[r] += 1
                    cross_n[(v, r)] = cross_n.get((v, r), 0) + 1
        ccb = Cc.setdefault(b, {r: set() for r in RAMPS})
        inwin = t >= a.warmup_sec
        for v, cl in cur_ramp.items():
            r = CONN2R.get(cl)
            if r is not None:
                ccb[r].add(v)
                conn_veh[r].add(v)
                conn_dwell[r] += 1
                if inwin:
                    win_veh[r].add(v)
        prev_u, prev_f, prev_ramp = cur_u, cur_f, cur_ramp

    with open(path, "r", encoding="latin-1") as f:
        for ln in f:
            c0 = ln[0]
            if c0 == "$" or c0 == "*":
                continue
            nrec += 1
            p = ln.split(";", 3)
            ts, no, lk = p[0], p[1], p[2]
            if ts != cur_t:
                if cur_t is not None:
                    flush(float(cur_t))
                    cur_u, cur_f, cur_ramp = set(), set(), {}
                cur_t = ts
                if nrec % 250000 < 80:
                    print("  ... SimSec %s  rec %d  %.0fs" % (ts, nrec, time.time() - t0),
                          flush=True)
            if lk in URBAN:
                cur_u.add(no)
            elif lk in FW:
                cur_f.add(no)
            if lk in RAMP_UNIV:
                cur_ramp[no] = lk
    if cur_t is not None:
        flush(float(cur_t))
    t_end = float(cur_t)
    print("파싱 완료: %d rec, %.0fs" % (nrec, time.time() - t0))

    bins = sorted(ntrans)
    full = max(ntrans.values())
    doc = {"schema_version": "far-rates-fzp-truth/1", "generated": "2026-09-01",
           "fzp": a.fzp, "tc_sec": TC, "decay": a.decay,
           "resolution_sec": 5.0, "records": nrec, "simsec_end": t_end,
           "link_sets": {"urban_n": len(URBAN), "fw_n": len(FW),
                         "fw_links": sorted(FW, key=int),
                         "ramp_connectors": {r: sorted(S["ramp_" + r]) for r in RAMPS}},
           "bins": [], "series": {}, "summary": {}, "totals": {}}

    for b in bins:
        doc["bins"].append({"bin": b, "t_start": b * TC + 1, "t_end": (b + 1) * TC,
                            "transitions": ntrans[b], "complete": ntrans[b] == full})
    doc["series"]["urban_exit_veh_per_Tc"] = [A.get(b, 0) for b in bins]
    doc["series"]["fw_exit_veh_per_Tc"] = [B.get(b, 0) for b in bins]
    for r in RAMPS:
        doc["series"]["merge_conn_" + r] = [len(Cc[b][r]) for b in bins]
        doc["series"]["merge_cross_" + r] = [len(Cx.get(b, {}).get(r, ())) for b in bins]

    keep = [i for i, b in enumerate(bins) if ntrans[b] == full]
    # 정답지는 warmup 뒤 구간이다. 0~900 s 는 망을 채우는 과도구간이라 방류가 수요제약이다.
    keepw = [i for i in keep if bins[i] * TC + 1 >= a.warmup_sec]
    doc["warmup_sec"] = a.warmup_sec
    doc["summary_post_warmup"] = {}
    for k, ser in doc["series"].items():
        doc["summary"][k] = stats([float(ser[i]) for i in keep], a.decay, TC)
        doc["summary_post_warmup"][k] = stats([float(ser[i]) for i in keepw], a.decay, TC)

    # 온라인 채널이 각 구간에서 실제로 들고 있을 값 = 감쇠 러닝맥스 궤적.
    doc["runmax_series"] = {}
    for k, ser in doc["series"].items():
        est, traj = 0.0, []
        for i in keep:
            est = max(float(ser[i]), a.decay * est)
            traj.append(round(est, 2))
        doc["runmax_series"][k] = traj

    hours = (t_end - 1.0) / 3600.0
    doc["overall_hours"] = round(hours, 4)
    for r in RAMPS:
        doc["totals"][r] = {"conn_unique_veh": len(conn_veh[r]),
                            "cross_veh": len(cross_veh[r]),
                            "conn_snapshot_obs": conn_dwell[r],
                            "mean_snapshots_on_conn":
                                round(conn_dwell[r] / max(1, len(conn_veh[r])), 3),
                            "conn_veh_h_overall": round(len(conn_veh[r]) / hours, 1),
                            "cross_veh_h_overall": round(len(cross_veh[r]) / hours, 1),
                            # 구간별 conn 유일수의 합 / 전체 유일수. 1 보다 크면 구간경계를
                            # 걸친 차량을 두 구간에서 각각 셌다는 뜻 (커넥터 체류가 길어서다).
                            "bin_sum_conn": sum(doc["series"]["merge_conn_" + r]),
                            "bin_sum_cross": sum(doc["series"]["merge_cross_" + r]),
                            "conn_boundary_inflation":
                                round(sum(doc["series"]["merge_conn_" + r])
                                      / max(1, len(conn_veh[r])), 3),
                            "conn_dwell_sec": round(conn_dwell[r] / max(1, len(conn_veh[r])) * 5.0, 1),
                            "cross_events": cross_events[r],
                            "cross_events_veh_h": round(cross_events[r] / hours, 1),
                            "repeat_excess": sum(n - 1 for (v, rr), n in cross_n.items()
                                                 if rr == r and n > 1)}

    loop_veh = {v for (v, r), n in cross_n.items() if n > 1}
    doc["repeat_crossings"] = {
        "loop_vehicles": len(loop_veh),
        "share_of_merging_vehicles": round(len(loop_veh)
                                           / max(1, len({v for v, _ in cross_n})), 4),
        "excess_events": sum(n - 1 for n in cross_n.values() if n > 1),
        "share_of_all_events": round(sum(n - 1 for n in cross_n.values() if n > 1)
                                     / max(1, sum(cross_events.values())), 4),
        "per_ramp_excess": {r: doc["totals"][r]["repeat_excess"] for r in RAMPS},
        "note": "31->10480->26->...->32->10490->2->...->31 폐루프를 도는 차량이 있다(주기 ~120s). "
                "D 램프 둘에 몰려 있다. 유량으로는 반복 통과를 각각 세는 것이 맞으므로 "
                "cross_events 가 정답이고, 유일차량 계수(conn/cross_veh)는 그만큼 과소하다.",
    }

    # --- 교차검증: calibrate_ramp_arrival_20260830 과 같은 창/정의로 재현 ---
    REF_VPH = {"R_D_W": 752.0, "R_F_W": 1212.0, "R_D_E": 938.0, "R_F_E": 555.0}
    wh = (5400.0 - a.warmup_sec) / 3600.0
    xc = {"window_sec": [a.warmup_sec, 5400.0],
          "reference": "outputs/ramp_arrival_calibration_20260830.json :: "
                       "per_run.ncsweep_x22_20260828.throughput_vph (무제어 x2.2)",
          "note": "기준값은 무제어 수요 x2.2 런이고 이 파일은 제어(wu-link) 수요 x1.0 런이다. "
                  "같은 창/정의로 재면 램프별 0.94~1.02, 총량 1.6% 이내 — 정의는 일치한다.",
          "per_ramp": {}}
    for r in RAMPS:
        v = len(win_veh[r]) / wh
        xc["per_ramp"][r] = {"unique_veh": len(win_veh[r]), "veh_h": round(v, 1),
                             "reference_veh_h": REF_VPH[r],
                             "ratio": round(v / REF_VPH[r], 3)}
    xc["total_veh_h"] = round(sum(x["veh_h"] for x in xc["per_ramp"].values()), 1)
    xc["reference_total_veh_h"] = round(sum(REF_VPH.values()), 1)
    xc["total_ratio"] = round(xc["total_veh_h"] / xc["reference_total_veh_h"], 3)
    doc["cross_check_vs_ramp_arrival_calibration"] = xc

    # --- far 가 실제로 쓰는 상수와 비교 ---
    sw = doc["summary_post_warmup"]
    doc["far_constants_vs_measured"] = {
        "urban_G_veh_per_Tc": {"far_free": 640.0, "far_congested": 500.0,
                               "measured_mean": sw["urban_exit_veh_per_Tc"]["mean_veh_per_Tc"],
                               "measured_max": sw["urban_exit_veh_per_Tc"]["max_veh_per_Tc"],
                               "measured_runmax": sw["urban_exit_veh_per_Tc"]["runmax_decay_veh_per_Tc"]},
        "fw_g_veh_per_Tc": {"far": 300.0,
                            "measured_mean": sw["fw_exit_veh_per_Tc"]["mean_veh_per_Tc"],
                            "measured_max": sw["fw_exit_veh_per_Tc"]["max_veh_per_Tc"],
                            "measured_runmax": sw["fw_exit_veh_per_Tc"]["runmax_decay_veh_per_Tc"]},
        "merge_veh_h": {"far_per_ramp": 1800.0,
                        "measured_runmax": {r: sw["merge_conn_" + r]["runmax_decay_veh_h"] for r in RAMPS},
                        "measured_mean": {r: sw["merge_conn_" + r]["mean_veh_h"] for r in RAMPS}},
    }

    op = R / a.out
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n-> %s" % op)

    for lab, sm, ks in (("전체 완전구간 %d개" % len(keep), doc["summary"], keep),
                        ("warmup(%.0fs) 이후 %d개  <= 정답지" % (a.warmup_sec, len(keepw)),
                         doc["summary_post_warmup"], keepw)):
        print("\n=== 150초 구간 요약 · %s (전이 %d개/구간) ===" % (lab, full))
        print("%-26s %10s %10s %12s %10s"
              % ("계열", "평균/Tc", "최대/Tc", "러닝맥스/Tc", "러닝맥스vph"))
        for k in doc["series"]:
            s = sm[k]
            print("%-26s %10.2f %10.1f %12.2f %10.1f" % (
                k, s["mean_veh_per_Tc"], s["max_veh_per_Tc"],
                s["runmax_decay_veh_per_Tc"], s["runmax_decay_veh_h"]))

    print("\n=== 램프 총량 (전체 %.4f h) ===" % hours)
    print("%-8s %8s %8s %10s %10s %8s %9s %9s"
          % ("램프", "conn대수", "cross", "conn vph", "cross vph", "체류s",
             "구간합conn", "경계중복"))
    for r in ("R_D_W", "R_F_W", "R_D_E", "R_F_E"):
        t = doc["totals"][r]
        print("%-8s %8d %8d %10.1f %10.1f %8.1f %9d %9.3f" % (
            r, t["conn_unique_veh"], t["cross_veh"], t["conn_veh_h_overall"],
            t["cross_veh_h_overall"], t["conn_dwell_sec"],
            t["bin_sum_conn"], t["conn_boundary_inflation"]))
    print("  구간별 conn 유일수는 커넥터 체류(24~58s)가 150s 경계를 걸쳐 중복계수된다.")
    print("  구간 유량으로는 merge_cross 를 써라.")
    rc = doc["repeat_crossings"]
    print("\n  반복통과: 차량 %d대(합류차량의 %.2f%%)가 초과 %d회 = 전체 합류사건의 %.2f%%  램프별 %s"
          % (rc["loop_vehicles"], 100 * rc["share_of_merging_vehicles"],
             rc["excess_events"], 100 * rc["share_of_all_events"], rc["per_ramp_excess"]))
    print("  합류사건 총계 %s = %.0f veh/h (유일차량 계수는 그만큼 과소)"
          % ({r: doc["totals"][r]["cross_events"] for r in RAMPS},
             sum(doc["totals"][r]["cross_events"] for r in RAMPS) / hours))

    print("\n=== 교차검증 vs ramp_arrival_calibration_20260830 (창 %.0f~5400 s) ==="
          % a.warmup_sec)
    print("%-8s %10s %10s %10s %8s" % ("램프", "유일대수", "veh/h", "기준veh/h", "비"))
    for r in ("R_D_W", "R_F_W", "R_D_E", "R_F_E"):
        c = xc["per_ramp"][r]
        print("%-8s %10d %10.1f %10.1f %8.3f"
              % (r, c["unique_veh"], c["veh_h"], c["reference_veh_h"], c["ratio"]))
    print("%-8s %10s %10.1f %10.1f %8.3f"
          % ("합계", "", xc["total_veh_h"], xc["reference_total_veh_h"], xc["total_ratio"]))

    fc = doc["far_constants_vs_measured"]
    print("\n=== far 상수 vs 실측 (warmup 이후) ===")
    u = fc["urban_G_veh_per_Tc"]
    print("urban G   far 자유 640 / 혼잡 500   실측 평균 %.1f · 최대 %.1f · 러닝맥스 %.1f  [veh/150s]"
          % (u["measured_mean"], u["measured_max"], u["measured_runmax"]))
    g = fc["fw_g_veh_per_Tc"]
    print("본선 g_fw far 300                  실측 평균 %.1f · 최대 %.1f · 러닝맥스 %.1f  [veh/150s]"
          % (g["measured_mean"], g["measured_max"], g["measured_runmax"]))
    m = fc["merge_veh_h"]
    print("merge     far 1800/램프            실측 러닝맥스 %s  [veh/h]"
          % {r: m["measured_runmax"][r] for r in ("R_D_W", "R_F_W", "R_D_E", "R_F_E")})


if __name__ == "__main__":
    main()
