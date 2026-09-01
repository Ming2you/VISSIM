"""far 저수지 방류율을 VISSIM 실측으로 잰다 (2026-09-01).

왜. `mfd_far_cost_to_go` 의 배수율 셋이 전부 vendor 상수다 —
도시 G(자유 640 / 혼잡 500 veh/T_c), 본선 g_fw(300 veh/T_c),
램프 merge_rate(`ramp_capacity_veh_h` x recv, 우리 망은 1800/램프).
far 는 N^2/(2G) 형태라 G 가 배수 곱이 아니라 **곡률**을 정한다.

무엇을 세나. `state_<t>.json` 의 `vehicle_records.records` 가 전 차량 (veh_no, link_no)
스냅샷이다. 인접 결정 두 장을 대조해 **직전 150초에 저수지를 떠난 대수**를 센다.

    out(S) = #{ v : link(v, t-1) in S  and  (v 없음 at t  or  link(v, t) not in S) }

단위가 그대로 veh/T_c 라 G·g_fw 에 바로 들어간다. merge 는 far 가 veh/h 를 받으므로
x 3600/T_c 한다.

수요제약을 어떻게 거르나. 한산한 구간의 이탈은 용량이 아니라 수요다. 어댑터
`install_measured_movement_capacity` 가 쓰는 것과 같은 **감쇠 러닝맥스**를 쓴다.

저수지 셋 (링크 집합은 권역 정본 + 램프미터 VBS):
  urban   통제 17 SC 의 권역 링크 전부 (보호망)
  fw      FW_W + FW_E 체인
  ramp_r  램프 r 의 유입 링크 + 미터 커넥터
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]

# 램프미터 VBS scripts/install_real_world_freeway_controls.vbs:440-447
RAMP_CONN = {
    "R_D_W": [("10480", "31", "26"), ("10482", "32", "26")],
    "R_F_W": [("10646", "68", "26"), ("10644", "69", "26")],
    "R_F_E": [("10639", "70", "2"), ("10681", "68", "2")],
    "R_D_E": [("10490", "32", "2"), ("10484", "31", "24")],
}


def link_sets() -> dict[str, set[str]]:
    terr = json.loads((R / "outputs/urban_player_territory_v1_20260819.json").read_text(encoding="utf-8"))
    sig = json.loads((R / "evaluation/configs/canon_fdfit3_20260828.json").read_text(encoding="utf-8"))
    controlled = {str(x) for x in sig["config_overrides"]["network"]["signals"]}

    urban: set[str] = set()
    for player, legs in terr["territory"]["urban"].items():
        if str(player) not in controlled:
            continue
        for links in legs.values():
            urban |= {str(x) for x in links}

    fw: set[str] = set()
    for links in terr["territory"]["freeway"].values():
        fw |= {str(x) for x in links}
    # 램프 커넥터는 freeway 권역에 들어 있다. 본선 저수지에서 빼야 이중계상이 없다.
    ramp_all = {c for trips in RAMP_CONN.values() for (c, _f, _t) in trips}
    fw -= ramp_all

    out = {"urban": urban, "fw": fw}
    for ramp, trips in RAMP_CONN.items():
        # 유입 링크는 여러 램프가 공유한다(31·32·68). 커넥터만 쓰면 램프별로 갈린다.
        out["ramp_" + ramp] = {c for (c, _f, _t) in trips}
    return out


def veh_link(path: Path) -> dict[int, str]:
    d = json.loads(path.read_text(encoding="utf-8"))
    rs = ((d.get("vehicle_records") or {}).get("records")) or []
    return {int(r["veh_no"]): str(r["link_no"]) for r in rs}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--tc-sec", type=float, default=150.0)
    ap.add_argument("--decay", type=float, default=0.98)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    S = link_sets()
    print("저수지 링크수: " + " · ".join("%s %d" % (k, len(v)) for k, v in S.items()))
    doc: dict[str, object] = {"schema_version": "far-reservoir-rates/1", "generated": "2026-09-01",
                              "tc_sec": a.tc_sec, "decay": a.decay, "runs": {}}

    for run in a.runs:
        rd = R / "evaluation/runs" / run
        states = sorted(rd.glob("decisions_*/state_*.json"),
                        key=lambda p: int(re.findall(r"(\d+)", p.stem)[-1]))
        if len(states) < 2:
            print("%-34s 상태파일 %d장 — 건너뜀" % (run, len(states)))
            continue
        prev = veh_link(states[0])
        series: dict[str, list[float]] = {k: [] for k in S}
        for sp in states[1:]:
            cur = veh_link(sp)
            for key, ls in S.items():
                n = 0
                for v, lk in prev.items():
                    if lk in ls and cur.get(v) not in ls:
                        n += 1
                series[key].append(float(n))
            prev = cur

        rec: dict[str, object] = {"intervals": len(states) - 1, "rates": {}}
        for key, xs in series.items():
            est = 0.0
            for x in xs:                       # 감쇠 러닝맥스
                est = max(x, a.decay * est)
            mean = sum(xs) / len(xs) if xs else 0.0
            rec["rates"][key] = {"mean_veh_per_Tc": round(mean, 1),
                                 "max_veh_per_Tc": round(max(xs), 1) if xs else 0.0,
                                 "runmax_est_veh_per_Tc": round(est, 1),
                                 "runmax_est_veh_h": round(est * 3600.0 / a.tc_sec, 1)}
        doc["runs"][run] = rec
        print("\n%s  (구간 %d)" % (run, len(states) - 1))
        print("  %-14s %10s %10s %12s %10s" % ("저수지", "평균/T_c", "최대/T_c", "러닝맥스/T_c", "veh/h"))
        for key in ("urban", "fw", "ramp_R_D_W", "ramp_R_F_W", "ramp_R_D_E", "ramp_R_F_E"):
            r = rec["rates"][key]
            print("  %-14s %10.1f %10.1f %12.1f %10.1f" % (
                key, r["mean_veh_per_Tc"], r["max_veh_per_Tc"],
                r["runmax_est_veh_per_Tc"], r["runmax_est_veh_h"]))

    if a.out:
        Path(a.out).write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        print("\n-> %s" % a.out)


if __name__ == "__main__":
    main()
