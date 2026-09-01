#!/usr/bin/env python3
"""leader 코너 탐색 경로별로 **목적값 손실**을 잰다.

## 왜

램프 결합을 켜면 leader 가 2^15 = 32,768 회 전체평가로 떨어져 결정당 6,700 초가 된다
(기준 220 초). 그 열거는 좌표하강의 **출발점**을 고르는 일인데, 열거로 실제로 얼마를 버는지가
확인된 적이 없다.

가법 경로와 대조했을 때 최종 목적값 차이가 0.0026 이었다 - 코너들이 사실상 동률이라는 신호다.
그렇다면 열거를 건너뛰어도 실질 손해가 작을 수 있다. 그것을 여러 앵커에서 분포로 확인한다.

## 방법

같은 상태 JSON 에 대해 어댑터를 두 번 돌린다.
  enumerate   현행 (RW_LEADER_CORNER_SKIP_ENUM 미설정)
  coordinate  열거 생략, base 코너에서 좌표하강만 (RW_LEADER_CORNER_SKIP_ENUM=1)
그리고 액션과 목적값을 대조한다. 결론은 목적값 손실의 분포이지 액션 동일성이 아니다 -
이 모드는 답을 바꾸는 것이 전제다.

VISSIM 을 띄우지 않는다. 다만 램프 결합 config 에서는 enumerate 쪽이 앵커당 수 시간이다.
"""
from __future__ import annotations
import argparse, json, os, subprocess, sys, time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
PY_EXE = os.environ.get("RW_SWEEP_PYTHON", r"C:\ProgramData\anaconda3\python.exe")
ADAPTER = REPO / "evaluation" / "controllers" / "vissim_stackelberg_adapter.py"
MAP = REPO / "evaluation/real_world_modi_control_distributed_20260728/control_mapping_distributed_pedovrx_20260814.json"
DET = REPO / "evaluation/real_world_modi_control_distributed_20260728/detector_local_mapping_distributed_pedovrx_20260814.json"
CAL = REPO / "evaluation/calibration/real_world_prediction_calibration_pshb4500fix_20260724.json"


def run(state: Path, tuning: Path, out_dir: Path, skip_enum: bool, tag: str) -> dict | None:
    env = dict(os.environ)
    env.update({
        "RW_WARMSTART_SEC": "900", "RW_ADAPTER_MODE": "",
        "RW_LANE_DELAY_CORRECTION": "0", "RW_NARROW_AXIS_SG": "0",
        "RW_QUEUE_ORIGIN_FILTER": "0", "RW_VALIDATION_FIXED_SIGNAL": "0",
        "RW_RESTORE_RELEASE_BUFFERS": "off", "RW_ADDITIVE_CORNER_WITH_RAMPS": "0",
        "RW_LEADER_CORNER_SKIP_ENUM": "1" if skip_enum else "0",
    })
    aj = out_dir / f"act_{tag}.json"
    t0 = time.time()
    proc = subprocess.run(
        [PY_EXE, str(ADAPTER), "--state-json", str(state), "--out-action-json", str(aj),
         "--out-action-csv", str(out_dir / f"act_{tag}.csv"), "--mapping-json", str(MAP),
         "--controller", "stackelberg", "--detector-mapping-json", str(DET),
         "--calibration-json", str(CAL), "--tuning-json", str(tuning)],
        capture_output=True, text=True, env=env, timeout=60 * 60 * 12)
    if proc.returncode != 0 or not aj.is_file():
        print(f"    실패 {tag}: rc={proc.returncode} {proc.stderr[-200:]}")
        return None
    d = json.loads(aj.read_text(encoding="utf-8"))
    m = d["metadata"]
    return {
        "wall_sec": time.time() - t0,
        "selected_objective": m.get("meta_leader_selected_objective"),
        "candidate_best_objective": m.get("meta_leader_candidate_best_objective"),
        "best_index": m.get("meta_leader_candidate_best_index"),
        "green_times": d.get("green_times"),
        "ramp_metering": d.get("ramp_metering"),
        "vsl": d.get("vsl"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--states", nargs="+", required=True)
    ap.add_argument("--tuning", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--skip-enumerate", action="store_true",
                    help="열거 쪽을 생략하고 coordinate 만 잰다(열거가 너무 느릴 때)")
    args = ap.parse_args()
    out_dir = args.out.parent / "corner_modes"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for i, s in enumerate(args.states):
        st = Path(s)
        print(f"=== [{i+1}/{len(args.states)}] {st.name} ===")
        coord = run(st, args.tuning, out_dir, True, f"{i}_coord")
        if coord:
            print(f"    coordinate  {coord['wall_sec']:8.1f}s  obj {coord['selected_objective']}")
        enum = None
        if not args.skip_enumerate:
            enum = run(st, args.tuning, out_dir, False, f"{i}_enum")
            if enum:
                print(f"    enumerate   {enum['wall_sec']:8.1f}s  obj {enum['selected_objective']}")
        if coord and enum:
            a, b = enum["selected_objective"], coord["selected_objective"]
            loss = (b - a) if (a is not None and b is not None) else None
            same = all(enum[k] == coord[k] for k in ("green_times", "ramp_metering", "vsl"))
            print(f"    -> 목적값 손실 {loss}   액션 {'동일' if same else '다름'}"
                  f"   속도 {enum['wall_sec'] / max(coord['wall_sec'], 1e-9):.1f}배")
            rows.append({"state": st.name, "enumerate": enum, "coordinate": coord,
                         "objective_loss": loss, "action_identical": same})
        elif coord:
            rows.append({"state": st.name, "coordinate": coord})

    args.out.write_text(json.dumps(
        {"schema_version": "leader-corner-mode-compare-v1",
         "tuning": str(args.tuning.name),
         "note": "목적값은 작을수록 좋다. loss > 0 이면 coordinate 가 그만큼 나쁘다. "
                 "이 모드는 답을 바꾸는 것이 전제이므로 결론은 손실의 크기이지 동일성이 아니다.",
         "rows": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"\n기록: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
