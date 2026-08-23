# -*- coding: utf-8 -*-
"""`.sig` 원본에서 신호별 타임라인(주기·유효녹색·현시겹침)을 유도한다.

왜 다시 만드나. 기존 `outputs/signal_timeline_measured_20260821.json` 의
`plan_total_sec` · `concurrency_factor` 가 원본과 안 맞는다 — SC5 가 246/1.64 인데
`.sig` 어디에서도 246 이 나오지 않는다(주기 150 · SG1-8 합 300 · SG9+ 408 · 전체 708).
그 값이 `install_native_signal_structure` 에서 **movement 용량 배율**로 쓰이므로
검증 안 된 수를 곱하고 있었다.

유도 규칙
- prog 는 `active_prog_no`(기본 1). `.sig` 의 cmds 는 display 전환점이다(3=녹색, 1=적색).
- **황색은 자동 삽입**이다. signalsequence "Red-Green-Amber" 의 Amber 상태가
  `isFixedDuration=true defaultDuration=3000` 이라 녹색 끝 3초가 황색이다.
  유효 녹색 = 원시 녹색 − 3초. (SC5: 46/26/50/28 -> 43/23/47/25, 합 138 = 150-4x3)
- **미드블록(SG 9+)은 제외**한다. 우리가 구동하지 않고, 섞으면 주교차로 값이 오염된다.
- 방향별 SG 는 짝이다(EBT+WBT 가 한 현시). NEMA 이름으로 현시에 접어 **합집합**을 쓴다 —
  안 그러면 모든 값이 2배가 된다(SC5 원시합 300 = 150 x 2).

산출
- cycle_sec, green_sec(=현시 합집합 초), all_red_sec, plan_total_sec(=현시별 유효녹색 합),
  concurrency_factor(= plan_total / green_sec), per-phase green, max_concurrent_phases
"""
from __future__ import annotations
import argparse, collections, json, sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEMA = {"NBT": "p1", "SBT": "p1", "NBL": "p2", "SBL": "p2",
        "EBT": "p3", "WBT": "p3", "EBL": "p4", "WBL": "p4"}
PHASES = ("p1", "p2", "p3", "p4")
GREEN, RED = "3", "1"


def amber_sec(root: ET.Element, seq_id: str) -> float:
    for seq in root.findall(".//signalsequences/signalsequence"):
        if str(seq.get("id")) != str(seq_id):
            continue
        for st in seq.findall("state"):
            if str(st.get("display")) == "4":
                return float(st.get("defaultDuration", 0)) / 1000.0
    return 0.0


def phase_seconds(sig_path: Path, prog_id: str, max_sg: int):
    root = ET.parse(sig_path).getroot()
    progs = root.findall(".//progs/prog") or root.findall(".//prog")
    prog = next((p for p in progs if str(p.get("id")) == str(prog_id)), progs[0] if progs else None)
    if prog is None:
        return None
    cycle = int(prog.get("cycletime", 0)) // 1000
    if cycle <= 0:
        return None
    names = {sg.get("id"): str(sg.get("name", "")).upper() for sg in root.findall(".//sgs/sg")}
    ph_on: dict[str, set[int]] = {p: set() for p in PHASES}
    raw_by_sg: dict[int, float] = {}
    for sgp in prog.findall(".//sgs/sg"):
        sid = sgp.get("sg_id") or sgp.get("id")
        try:
            sg_no = int(str(sid))
        except (TypeError, ValueError):
            continue
        if sg_no > max_sg:
            continue
        pid = NEMA.get(names.get(sid, ""))
        if pid is None:
            continue
        ev = {int(c.get("begin", 0)) // 1000: str(c.get("display")) for c in sgp.findall(".//cmds/cmd")}
        if not ev:
            continue
        amber = amber_sec(root, sgp.get("signal_sequence") or "7")
        # 주기 시작 상태 = 마지막 전환점의 display
        cur = ev[max(ev)]
        green = set()
        for s in range(cycle):
            if s in ev:
                cur = ev[s]
            if cur == GREEN:
                green.add(s)
        # 황색은 녹색 구간 **끝** 3초. 연속 구간마다 뒤에서 잘라낸다.
        eff = set(green)
        runs, run = [], []
        for s in range(cycle + 1):
            if s in green and s < cycle:
                run.append(s)
            elif run:
                runs.append(run); run = []
        if green and (cycle - 1) in green and 0 in green and runs and len(runs) > 1:
            runs[0] = runs[-1] + runs[0]; runs.pop()   # 주기 경계에서 이어진 구간 병합
        for r in runs:
            for s in r[-int(round(amber)):] if amber > 0 else []:
                eff.discard(s)
        raw_by_sg[sg_no] = len(green)
        ph_on[pid] |= eff
    union = set().union(*ph_on.values()) if ph_on else set()
    per_phase = {p: len(ph_on[p]) for p in PHASES}
    max_conc = max((sum(1 for p in PHASES if s in ph_on[p]) for s in range(cycle)), default=0)
    return {
        "cycle_sec": float(cycle),
        "green_sec": float(len(union)),
        "all_red_sec": float(cycle - len(union)),
        "plan_total_sec": float(sum(per_phase.values())),
        "concurrency_factor": (sum(per_phase.values()) / len(union)) if union else 1.0,
        "max_concurrent_phases": int(max_conc),
        "phase_green_sec": per_phase,
        "live_phases": [p for p in PHASES if per_phase[p] > 0],
        "amber_sec": amber_sec(root, "7"),
        "raw_sg_green_sec": {str(k): v for k, v in sorted(raw_by_sg.items())},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--timing", default="outputs/signal_group_timing_core17legs4b_20260819.json")
    ap.add_argument("--max-sg", type=int, default=8)
    ap.add_argument("--out", default="outputs/signal_timeline_from_sig_20260823.json")
    args = ap.parse_args()
    src = json.loads((ROOT / args.timing).read_text(encoding="utf-8"))
    prog_id = str(src.get("active_prog_no", 1))
    signals, missing = {}, []
    for c in src.get("controllers", []):
        sid = f"SC{c.get('sc_no')}"
        p = ROOT / str(c.get("sig_path", ""))
        if not p.is_file():
            missing.append((sid, str(c.get("sig_path"))))
            continue
        r = phase_seconds(p, prog_id, args.max_sg)
        if r:
            r["sig_path"] = str(c.get("sig_path"))
            r["program_offset_sec"] = c.get("program_offset_sec")
            signals[sid] = r
    out = ROOT / args.out
    out.write_text(json.dumps({
        "schema": "signal_timeline_from_sig/core17legs4b",
        "generated": "2026-08-23",
        "active_prog_no": prog_id,
        "max_sg": args.max_sg,
        "derivation": ".sig 원본 cmds 전개 -> SG9+ 제외 -> NEMA 로 현시 접기(합집합) -> 녹색 끝 황색 3초 제거",
        "signals": signals,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"신호 {len(signals)}개 유도 · 누락 {len(missing)}")
    print(f"{'신호':>8s}{'주기':>6s}{'유효녹색':>9s}{'all_red':>8s}{'현시합':>7s}{'배율':>7s}{'최대동시':>9s}{'live':>6s}")
    for sid, v in signals.items():
        print(f"{sid:>8s}{v['cycle_sec']:6.0f}{v['green_sec']:9.0f}{v['all_red_sec']:8.0f}"
              f"{v['plan_total_sec']:7.0f}{v['concurrency_factor']:7.2f}{v['max_concurrent_phases']:9d}"
              f"{len(v['live_phases']):6d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
