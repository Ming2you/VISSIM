#!/usr/bin/env python3
"""warm-start A/B 두 제어런을 대조한다.

## 왜 n=1 로 판정이 서는가

부모런과 base replay 로 **VISSIM 이 같은 시드·같은 설정에서 비트 단위로 재현된다**는 것을
실측했다(교통 열 721행 전부 차이 0, `eps_J_vissim` = 하한 1e-6). 두 런이 같은 시드·같은
수요·같은 망이고 오직 `RW_WARMSTART_SEC` 만 다르므로, J 차이가 나면 그것은 잡음이 아니라
warm-start 효과다. 노이즈 바닥을 먼저 깔아 둔 것이 여기서 값을 한다.

## J

`state_<run>.csv` 의 `total_vehicles` 를 제어창 [control_start, end] 에서 사다리꼴 적분해
3600 으로 나눈 veh·h(TTT). `measure_eps_j_vissim.py` 와 같은 산식이다.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path
from typing import Sequence

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
from measure_eps_j_vissim import integrate_veh_hours, read_state_series  # noqa: E402

EPS_J_VISSIM = 1.0e-6

COLS = (
    "total_vehicles", "urban_vehicles", "freeway_vehicles",
    "stopped_vehicles", "mean_speed_kph", "freeway_mean_speed_kph",
)


def series(path: Path, col: str):
    return read_state_series(path, col)


def runlog_counts(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        for key in ("DECISIONS_OK", "DECISIONS_FAILED", "OBSERVATION_FAILURES", "SIGNAL_SG_PLAN_ROWS"):
            if line.startswith(key + "="):
                out[key] = line.split("=", 1)[1].strip()
    return out


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--baseline", required=True, help="warm-start 꺼진 런 이름")
    ap.add_argument("--treatment", required=True, help="warm-start 켜진 런 이름")
    ap.add_argument("--control-start-sec", type=float, default=900.0)
    ap.add_argument("--end-sec", type=float, default=1800.0)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args(argv)

    d = args.run_dir.resolve()
    rows = {}
    for label, name in (("baseline", args.baseline), ("treatment", args.treatment)):
        state = d / f"state_{name}.csv"
        if not state.is_file():
            print(f"없음: {state}")
            return 2
        rec = {"name": name, "runlog": runlog_counts(d / f"runlog_{name}.txt")}
        for col in COLS:
            pts = series(state, col)
            rec[col] = integrate_veh_hours(pts, args.control_start_sec, args.end_sec)
            rec[col + "_final"] = pts[-1][1] if pts else float("nan")
        rows[label] = rec

    j_base = rows["baseline"]["total_vehicles"]
    j_treat = rows["treatment"]["total_vehicles"]
    delta = j_treat - j_base
    payload = {
        "schema_version": "warmstart-ab-v1",
        "window_sec": [args.control_start_sec, args.end_sec],
        "objective": "TTT = trapezoid(total_vehicles)/3600 (veh·h)",
        "why_n1_is_enough": (
            "VISSIM 재현성을 실측으로 입증했다(교통 열 721행 차이 0, eps_J_vissim=하한). "
            "두 런의 차이는 오직 RW_WARMSTART_SEC 이므로 ΔJ 는 잡음이 아니다."
        ),
        "baseline": rows["baseline"],
        "treatment": rows["treatment"],
        "delta_j_veh_h": delta,
        "delta_j_pct": (100.0 * delta / j_base) if j_base else None,
        # 2026-08-16: 하한이 1.0e-9 였다. 그건 N8-1 의 `eps_J_endpoint` 이고 이 스크립트가
        # 재는 것은 VISSIM 재현성 하한 `eps_J_vissim` = 1e-6 이다(docstring 도 1e-6 이라
        # 적고 있어 코드와 3자릿수가 어긋나 있었다). 두 하한을 섞으면 안 된다.
        # 8/15 판정에는 영향이 없다 - 그때 Δ가 -4.68 ~ -7.93 veh·h 로 두 하한 모두보다
        # 여섯 자릿수 이상 컸다.
        "eps_j_vissim": EPS_J_VISSIM,
        "verdict": (
            "동일 — warm-start 가 결정에 영향 없음(또는 env 미전파)"
            if abs(delta) < EPS_J_VISSIM
            else ("개선" if delta < 0 else "악화")
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
                        encoding="utf-8", newline="\n")

    print(f"창 [{args.control_start_sec:.0f}, {args.end_sec:.0f}] s")
    print(f"{'지표':24s} {'baseline':>12s} {'treatment':>12s} {'차이':>12s}")
    for col in COLS:
        a, b = rows["baseline"][col], rows["treatment"][col]
        print(f"{col:24s} {a:12.3f} {b:12.3f} {b - a:+12.3f}")
    print()
    print(f"ΔJ = {delta:+.3f} veh·h ({payload['delta_j_pct']:+.2f}%)  -> {payload['verdict']}")
    for label in ("baseline", "treatment"):
        print(f"  {label:10s} {rows[label]['runlog']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
