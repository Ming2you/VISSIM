# -*- coding: utf-8 -*-
"""`.fzp` 전 차량 궤적으로 (1) 경계 큐가 실재하는지 (2) 모델 누적이 맞는지 지상검증한다.

왜 (2026-08-28).

리더 목적함수의 `boundary_in_queue_penalty` 는 가중치가 0.0 인데 물리량은 중앙 670대다.
그런데 우리가 재는 TTT 는 `boundary_vehicles` 를 포함하고 그 값이 **전 팔·전 스텝 0** 이며
상태 JSON 에 경계 큐 수집 채널이 아예 없다. 그러면 둘 중 하나다.

  실재한다  ->  우리 사다리 전부가 밖에 서 있는 차를 안 센 불완전 지표다.
  허구다    ->  누적에 벌점을 매기는 순간 없는 것을 상대로 최적화한다.

`.fzp` 는 **망 안에 있는 차량만** 적는다. 그래서 경계 큐를 직접 못 본다. 대신 회계로 본다 —
`.inpx` 의 vehicleInput 이 요구한 대수와 VISSIM 이 실제로 생성한 대수(차량번호 최대값)를
맞대면, 못 넣은 차가 곧 밖에 선 차다.

부수로 도시부 누적 궤적을 실측해 모델의 `protected_accumulation_veh` 와 대조한다.

산출: outputs/boundary_queue_ground_truth_20260828.json
"""
import argparse
import io
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

R = Path(__file__).resolve().parent.parent


def inpx_demand(inpx: Path):
    """vehicleInput 을 시간구간별로 적분해 요구 대수를 낸다.

    `<vehicleInput no= name= link=>` 아래 `<timeIntervalVehVolume ... volume= ...>` 이
    구간별 유량[veh/h]이다. 구간 경계는 `timeIntervals` 정의에 있다.
    """
    text = inpx.read_text(encoding="utf-8", errors="replace")
    # 시간구간 정의: <timeInterval no="..." start="...">
    ivs = {}
    for m in re.finditer(r'<timeInterval\b[^>]*\bno="(\d+)"[^>]*\bstart="([\d.]+)"[^>]*/?>', text):
        ivs[m.group(1)] = float(m.group(2))
    inputs = []
    for m in re.finditer(r"<vehicleInput\b(.*?)</vehicleInput>|<vehicleInput\b([^>]*)/>", text, re.S):
        blob = m.group(0)
        no = re.search(r'\bno="([^"]+)"', blob)
        link = re.search(r'\blink="([^"]+)"', blob)
        vols = []
        for v in re.finditer(r'<timeIntervalVehVolume\b[^>]*>', blob):
            s = v.group(0)
            ti = re.search(r'\btimeInt="([^"]+)"', s)
            vol = re.search(r'\bvolume="([\d.]+)"', s)
            if vol:
                key = (ti.group(1).split()[0] if ti else "")
                vols.append((key, float(vol.group(1))))
        if vols:
            inputs.append({"no": no.group(1) if no else "", "link": link.group(1) if link else "", "volumes": vols})
    return inputs, ivs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="canon_nolencap_20260828")
    ap.add_argument("--inpx", default="network/real_world_gaepo_modi/modi_eval_userfix_20260814e.inpx")
    ap.add_argument("--detector", default="evaluation/real_world_modi_control_distributed_20260728/"
                                          "detector_local_mapping_distributed_core17legs4f_20260826.json")
    ap.add_argument("--sim-period", type=float, default=5400.0)
    ap.add_argument("--out", default="outputs/boundary_queue_ground_truth_20260828.json")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    rundir = R / "evaluation/runs" / args.run
    fzps = sorted(rundir.glob("vissim_eval/*.fzp"))
    if not fzps:
        print("!! .fzp 없음: %s" % rundir)
        return 1
    fzp = fzps[0]
    det = json.loads((R / args.detector).read_text(encoding="utf-8"))
    urban = {str(k) for k in (det.get("link_to_origins") or {})}
    fw = {str(k) for k in (det.get("freeway_link_to_model_link") or {})}
    core = urban - fw

    # --- .fzp 스캔 ---
    per_t_all = defaultdict(int)
    per_t_core = defaultdict(int)
    per_t_speed = defaultdict(float)
    max_no = 0
    seen_first = {}
    rows = 0
    with io.open(fzp, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line or line[0] in "*$":
                continue
            p = line.rstrip("\n").split(";")
            if len(p) < 7:
                continue
            rows += 1
            try:
                t = float(p[0]); no = int(p[1]); link = p[2]; spd = float(p[6])
            except ValueError:
                continue
            if no > max_no:
                max_no = no
            if no not in seen_first:
                seen_first[no] = t
            per_t_all[t] += 1
            per_t_speed[t] += spd
            if link in core:
                per_t_core[t] += 1
    print("%s  행 %d · 시각 %d개 · 최대 차량번호 %d · 서로 다른 차량 %d"
          % (fzp.name, rows, len(per_t_all), max_no, len(seen_first)))

    # --- .inpx 요구 대수 ---
    inputs, ivs = inpx_demand(R / args.inpx)
    print("vehicleInput %d개 · 시간구간 정의 %d개" % (len(inputs), len(ivs)))
    # 구간 경계를 정렬해 각 구간 길이를 낸다. 마지막 구간은 sim_period 까지.
    bounds = sorted(set(ivs.values()))
    if not bounds:
        bounds = [0.0]
    spans = {}
    for i, s in enumerate(bounds):
        e = bounds[i + 1] if i + 1 < len(bounds) else args.sim_period
        spans[s] = max(0.0, min(e, args.sim_period) - s)
    key_to_start = {k: v for k, v in ivs.items()}
    demanded = 0.0
    per_input = []
    for it in inputs:
        tot = 0.0
        for key, vol in it["volumes"]:
            start = key_to_start.get(key)
            if start is None:
                # 구간 참조가 없으면 전 구간으로 본다 (보수적)
                dur = args.sim_period
            else:
                dur = spans.get(start, 0.0)
            tot += vol * dur / 3600.0
        demanded += tot
        per_input.append({"no": it["no"], "link": it["link"], "demanded_veh": tot})
    print("요구 대수(.inpx 적분)  %.0f" % demanded)
    print("생성 대수(.fzp 차량번호) %d" % max_no)
    gap = demanded - max_no
    print("차이 %.0f  (%.2f%%)" % (gap, 100.0 * gap / demanded if demanded else 0.0))

    # --- 누적 궤적 실측 ---
    ts = sorted(per_t_all)
    import statistics as stx
    core_series = [per_t_core[t] for t in ts]
    all_series = [per_t_all[t] for t in ts]
    print()
    print("망 전체 차량 수   중앙 %d · 최대 %d" % (stx.median(all_series), max(all_series)))
    print("도시부 core 누적  중앙 %d · 최대 %d" % (stx.median(core_series), max(core_series)))

    doc = {
        "schema_version": "boundary-queue-ground-truth/1",
        "generated": "2026-08-28",
        "run": args.run,
        "fzp": fzp.name,
        "why": "리더의 boundary_in 가중치가 0인데 물리량은 670대이고, 우리 TTT 는 "
               "boundary_vehicles=0 이라 경계 큐를 안 센다. 실재 여부를 회계로 가른다.",
        "method": ".fzp 는 망 안 차량만 적는다. .inpx vehicleInput 적분(요구) 대 "
                  "차량번호 최대값(생성)의 차이가 못 들어간 차 = 밖에 선 차다.",
        "rows": rows,
        "time_steps": len(per_t_all),
        "generated_veh": max_no,
        "distinct_veh_seen": len(seen_first),
        "demanded_veh_inpx": demanded,
        "shortfall_veh": gap,
        "shortfall_pct": (100.0 * gap / demanded) if demanded else None,
        "network_vehicles_median": stx.median(all_series),
        "network_vehicles_max": max(all_series),
        "core_accumulation_median": stx.median(core_series),
        "core_accumulation_max": max(core_series),
        "per_input_top": sorted(per_input, key=lambda x: -x["demanded_veh"])[:12],
    }
    (R / args.out).write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print()
    print("-> %s" % args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
