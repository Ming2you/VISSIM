#!/usr/bin/env python3
"""차로보정 x 축좁힘 2x2 factorial A/B 를 대조한다.

`compare_warmstart_ab.py` 와 **같은 J 산식**을 쓴다 - `measure_eps_j_vissim` 의
`read_state_series` / `integrate_veh_hours` 를 그대로 가져오므로 재료성 하한도 같은
`eps_J_vissim`(1e-6 veh·h)이다. N8-1 의 `eps_J_endpoint`(1e-9)와 섞으면 안 된다.

## 왜 n=1 로 판정이 서는가

부모런과 base replay 로 VISSIM 이 같은 시드·같은 설정에서 비트 단위로 재현됨을 실측했다.
네 arm 이 시드·수요·망이 같고 오직 두 환경변수만 다르므로 J 차이는 잡음이 아니다.

## factorial 로 읽는 법

    base    lane=0 narrow=0      lane     lane=1 narrow=0
    narrow  lane=0 narrow=1      both     lane=1 narrow=1

주효과   lane   = (lane - base + both - narrow) / 2
주효과   narrow = (narrow - base + both - lane) / 2
상호작용        = (both - lane - narrow + base)

상호작용이 주효과만 하면 둘을 따로 켜고 끄는 판단이 무의미하므로 같이 보고한다.
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path
from typing import Sequence

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
from measure_eps_j_vissim import integrate_veh_hours, read_state_series  # noqa: E402

EPS_J_VISSIM = 1.0e-6
ARMS = ("base", "lane", "narrow", "both")


def run_name(arm: str, demand: float, tag: str) -> str:
    return f"{arm}_d{int(round(demand * 100)):03d}_{tag}"


def objective(run_dir: Path, name: str, start_sec: float, end_sec: float) -> float | None:
    path = run_dir / f"state_{name}.csv"
    if not path.is_file():
        return None
    points = read_state_series(path, "total_vehicles")
    return integrate_veh_hours(points, start_sec, end_sec)


def runlog_flags(run_dir: Path, name: str) -> dict[str, str]:
    """런로그에서 arm 이 실제로 그 설정으로 돌았는지 확인한다.

    환경변수가 러너까지 전달되지 않으면 네 arm 이 전부 같은 값이 나오고, 그러면 ΔJ 가
    0 이라 "효과 없음"으로 잘못 읽힌다. 발사 의도가 아니라 **런이 기록한 값**을 본다.
    """
    out: dict[str, str] = {}
    path = run_dir / f"runlog_{name}.txt"
    if not path.is_file():
        return out
    keys = (
        "RW_LANE_DELAY_CORRECTION", "RW_NARROW_AXIS_SG", "LANE_DELAY_CORRECTION",
        "NARROW_AXIS_SG", "DECISIONS_OK", "DECISIONS_FAILED", "OBSERVATION_FAILURES",
        "SIGNAL_NAME_RULE_FALLBACKS", "WARMSTART_SEC",
    )
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        for key in keys:
            if line.startswith(key + "="):
                out[key] = line.split("=", 1)[1].strip()
    return out


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-dir", type=Path,
                    default=REPO / "evaluation" / "runs" / "lane_narrow_ab_20260816")
    ap.add_argument("--tag", default="20260816")
    ap.add_argument("--demands", default="0.75,1.0,1.25")
    ap.add_argument("--control-start-sec", type=float, default=900.0)
    ap.add_argument("--end-sec", type=float, default=1800.0)
    args = ap.parse_args(argv)

    demands = [float(x) for x in str(args.demands).split(",") if x.strip()]
    missing: list[str] = []
    table: dict[tuple[str, float], float] = {}

    for demand in demands:
        for arm in ARMS:
            name = run_name(arm, demand, args.tag)
            value = objective(args.run_dir, name, args.control_start_sec, args.end_sec)
            if value is None:
                missing.append(name)
            else:
                table[(arm, demand)] = value

    print(f"run-dir = {args.run_dir}")
    print(f"J = total_vehicles 사다리꼴 적분 / 3600, 창 [{args.control_start_sec:.0f}, {args.end_sec:.0f}] s")
    print(f"재료성 하한 eps_J_vissim = {EPS_J_VISSIM:g} veh·h\n")

    if missing:
        print(f"아직 없는 런 {len(missing)}개: {', '.join(missing)}\n")

    header = f"{'수요':>6s} " + "".join(f"{a:>12s}" for a in ARMS)
    print(header)
    print("-" * len(header))
    for demand in demands:
        row = f"{demand:6.2f} "
        for arm in ARMS:
            v = table.get((arm, demand))
            row += f"{v:12.3f}" if v is not None else f"{'-':>12s}"
        print(row)

    print(f"\n{'수요':>6s} {'Δlane':>12s} {'Δnarrow':>12s} {'상호작용':>12s}  {'판정':>10s}")
    print("-" * 60)
    for demand in demands:
        b = table.get(("base", demand))
        l = table.get(("lane", demand))
        n = table.get(("narrow", demand))
        bo = table.get(("both", demand))
        if None in (b, l, n, bo):
            # 주 질문(차로보정)만이라도 답한다.
            if b is not None and l is not None:
                d = l - b
                mark = "재료성 있음" if abs(d) > EPS_J_VISSIM else "하한 미만"
                print(f"{demand:6.2f} {d:12.3f} {'-':>12s} {'-':>12s}  {mark:>10s}  (부분)")
            else:
                print(f"{demand:6.2f} {'-':>12s} {'-':>12s} {'-':>12s}  {'미완':>10s}")
            continue
        eff_lane = ((l - b) + (bo - n)) / 2.0
        eff_narrow = ((n - b) + (bo - l)) / 2.0
        inter = bo - l - n + b
        biggest = max(abs(eff_lane), abs(eff_narrow))
        mark = "상호작용 큼" if abs(inter) > 0.5 * biggest and biggest > EPS_J_VISSIM else "가법적"
        print(f"{demand:6.2f} {eff_lane:12.3f} {eff_narrow:12.3f} {inter:12.3f}  {mark:>10s}")

    print("\n음수 = J 감소 = 개선.\n")

    print("런이 실제로 그 설정으로 돌았는지 (발사 의도가 아니라 런로그 기록):")
    for demand in demands:
        for arm in ARMS:
            name = run_name(arm, demand, args.tag)
            flags = runlog_flags(args.run_dir, name)
            if flags:
                shown = " ".join(f"{k}={v}" for k, v in sorted(flags.items()))
                print(f"  {name:28s} {shown}")

    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
