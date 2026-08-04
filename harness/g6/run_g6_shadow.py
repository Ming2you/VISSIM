# G6 오케스트레이터 — 후보별 모델 rollout 목적함수와 VISSIM 관측 목적함수를 짝지어 shadow 레코드로 굽는다.
"""사용법.

  python run_g6_shadow.py --run-dir <VISSIM 런 디렉터리> --t0 900 --horizons 1,3,5 \
      --out-dir <산출물 디렉터리>

런 디렉터리 규약(= run_real_world_single_watchdog.ps1 산출 구조).

  <run-dir>/decisions_<cell>_<candidate_id>_seed<seed>/state_000900.json   # 공통 초기상태
  <run-dir>/decisions_<cell>_<candidate_id>_seed<seed>/state_000960.json   # 관측 궤적
  ...

decision_id 는 `<cell>_seed<seed>_H<h>` 로 만든다. 즉 **같은 초기상태·수요·시드에서
호라이즌 h 를 고정한 후보 묶음**이 shadow 의 한 decision 이 되고, 그 안에서 순위가 매겨진다.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any

import g6_core as core
import g6_records as rec

STATE_RE = re.compile(r"^state_(\d{6})\.json$")


def load_state_json(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def state_path(decision_dir: Path, sim_sec: int) -> Path:
    return decision_dir / f"state_{int(sim_sec):06d}.json"


def discover_cells(run_dir: Path, t0: int) -> dict[tuple[str, str], dict[str, Path]]:
    """decisions_* 디렉터리를 (cell, seed) → {candidate_id: dir} 로 묶는다.

    디렉터리 이름은 `decisions_<cell>_<arm>_seed<seed>` 이고, <arm> 은
    run_g6_batch 가 candidate_id 를 그대로 넣는다.
    """

    # candidate_id 에 밑줄이 들어가므로(`c00_anchor`) 토큰 분해로는 arm 을 못 가른다.
    # 알려진 candidate_id 목록과 접미 일치로 자른다.
    known = sorted((c.candidate_id for c in core.ACTIVE_CANDIDATE_SET), key=len, reverse=True)
    cells: dict[tuple[str, str], dict[str, Path]] = {}
    for child in sorted(run_dir.glob("decisions_*")):
        if not child.is_dir() or not state_path(child, t0).exists():
            continue
        name = child.name[len("decisions_"):]
        match = re.match(r"^(?P<head>.+)_seed(?P<seed>\d+)$", name)
        if not match:
            continue
        head, seed = match.group("head"), match.group("seed")
        arm = next((cid for cid in known if head == cid or head.endswith("_" + cid)), None)
        if arm is None:
            print(f"WARN=UNKNOWN_ARM dir={child.name} (candidate set v1 에 없는 arm)")
            continue
        cell = head[: len(head) - len(arm)].rstrip("_") or "default"
        cells.setdefault((cell, seed), {})[arm] = child
    return cells


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--t0", type=int, default=900)
    parser.add_argument("--horizons", default="1,3,5")
    parser.add_argument("--mapping-json", type=Path, default=core.DEFAULT_MAPPING)
    parser.add_argument("--detector-mapping-json", type=Path, default=core.DEFAULT_DETECTOR_MAPPING)
    parser.add_argument("--calibration-json", type=Path, default=core.DEFAULT_CALIBRATION)
    parser.add_argument("--tuning-json", type=Path, default=core.DEFAULT_TUNING)
    parser.add_argument("--spillback-threshold", type=float, default=0.90)
    parser.add_argument(
        "--allow-missing-observation",
        action="store_true",
        help="관측 궤적이 없는 후보를 스킵 대신 미관측 레코드로 남긴다(shadow 가 NOT_EVALUATED 로 처리).",
    )
    args = parser.parse_args()

    horizons = [int(h) for h in str(args.horizons).split(",") if h.strip()]
    cells = discover_cells(args.run_dir, args.t0)
    if not cells:
        print(f"ERROR=NO_CELLS run_dir={args.run_dir} t0={args.t0}")
        return 2

    policy_hash = rec.hash_payload({"tuning": str(args.tuning_json), "calibration": str(args.calibration_json)})
    build_hash = rec.file_hash(core.ADAPTER_DIR / "vissim_stackelberg_adapter.py")
    schema_hash = rec.hash_payload({"candidate_set": [c.candidate_id for c in core.ACTIVE_CANDIDATE_SET]})

    records: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []

    for (cell, seed), arms in sorted(cells.items()):
        anchor_dir = arms[sorted(arms)[0]]
        init_json = load_state_json(state_path(anchor_dir, args.t0))
        runtime = core.build_runtime(
            init_json,
            mapping_json=args.mapping_json,
            detector_mapping_json=args.detector_mapping_json,
            calibration_json=args.calibration_json,
            tuning_json=args.tuning_json,
        )

        # 초기상태 동일성 검증 — G6 의 전제. 다르면 그 셀은 통째로 버린다.
        init_hashes = {
            arm: rec.file_hash(state_path(path, args.t0)) for arm, path in arms.items()
        }
        if len(set(init_hashes.values())) != 1:
            print(f"ERROR=INITIAL_STATE_MISMATCH cell={cell} seed={seed} hashes={init_hashes}")
            continue
        state_hash = next(iter(init_hashes.values()))
        topology_hash = rec.hash_payload({"mapping": str(args.mapping_json)})
        program_hash = rec.hash_payload({"cell": cell, "seed": seed, "t0": args.t0})

        initial_state = core.project_observed_state(runtime, init_json)
        max_h = max(horizons)
        forecast = core.build_forecast(runtime, init_json, max_h)
        interval = int(round(float(runtime.cfg.simulation.control_interval)))

        for horizon in horizons:
            decision_id = f"{cell}_seed{seed}_H{horizon}"
            for arm, decision_dir in sorted(arms.items()):
                try:
                    cand = core.candidate_by_id(arm)
                except KeyError:
                    print(f"WARN=UNKNOWN_CANDIDATE arm={arm} (candidate set v1 에 없음)")
                    continue
                control = core.build_control(runtime.cfg, runtime.ControlAction, cand)

                started = time.perf_counter()
                predicted = core.model_rollout_states(runtime, initial_state, control, forecast, horizon)
                model_runtime = time.perf_counter() - started
                model_terms = core.objective_from_states(runtime, predicted, control)
                model_spill = core.spillback_flag(runtime, predicted, threshold=args.spillback_threshold)

                observed_states = []
                missing: list[int] = []
                for step in range(1, horizon + 1):
                    sim_sec = args.t0 + interval * step
                    path = state_path(decision_dir, sim_sec)
                    if not path.exists():
                        missing.append(sim_sec)
                        continue
                    observed_states.append(core.project_observed_state(runtime, load_state_json(path)))

                if missing and not args.allow_missing_observation:
                    print(
                        f"WARN=MISSING_OBSERVED_STATES decision={decision_id} candidate={arm} "
                        f"sim_sec={missing} — 이 후보는 관측 없음으로 기록한다"
                    )
                if missing:
                    observed_terms = None
                    observed_spill = None
                else:
                    observed_terms = core.objective_from_states(runtime, observed_states, control)
                    observed_spill = core.spillback_flag(
                        runtime, observed_states, threshold=args.spillback_threshold
                    )

                records.append(
                    rec.build_record(
                        decision_id=decision_id,
                        candidate_id=arm,
                        model_objective=model_terms["g6_objective"],
                        vissim_objective=None if observed_terms is None else observed_terms["g6_objective"],
                        model_spillback=model_spill,
                        vissim_spillback=observed_spill,
                        action_payload={
                            "variant": cand.variant,
                            "vsl_kph": cand.vsl_kph,
                            "d_ramp_vph": cand.d_ramp_vph,
                            "f_ramp_vph": cand.f_ramp_vph,
                            "major_green_sec": cand.major_green_sec,
                            "minor_green_sec": cand.minor_green_sec,
                            "offset_sec": cand.offset_sec,
                            "horizon_steps": horizon,
                        },
                        policy_hash=policy_hash,
                        build_hash=build_hash,
                        action_schema_hash=schema_hash,
                        topology_hash=topology_hash,
                        program_hash=program_hash,
                        state_hash=state_hash,
                        model_runtime_sec=model_runtime,
                    )
                )
                rows.append(
                    {
                        "decision_id": decision_id,
                        "candidate_id": arm,
                        "variant": cand.variant,
                        "axis": cand.axis,
                        "horizon_steps": horizon,
                        "model_objective": model_terms["g6_objective"],
                        "model_ttt_veh_h": model_terms["g6_ttt_veh_h"],
                        "vissim_objective": None if observed_terms is None else observed_terms["g6_objective"],
                        "vissim_ttt_veh_h": None if observed_terms is None else observed_terms["g6_ttt_veh_h"],
                        "model_spillback": model_spill,
                        "vissim_spillback": observed_spill,
                        "model_terms": model_terms,
                        "vissim_terms": observed_terms,
                    }
                )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = args.out_dir / "g6_shadow_records.jsonl"
    rows_path = args.out_dir / "g6_candidate_rows.json"
    report_path = args.out_dir / "g6_shadow_report.json"
    rec.write_jsonl(jsonl_path, records)
    rows_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    report = rec.evaluate_and_write(records, report_path)

    print(f"RECORDS={len(records)} DECISIONS={report['decision_count']}")
    print(f"SPEARMAN={report['aggregate']['spearman_rho']}")
    print(f"PAIRWISE={report['aggregate']['top_action_pairwise']['agreement']}")
    print(f"SPILLBACK_F1={report['aggregate']['spillback']['f1']}")
    print(
        f"G6_INITIAL={report['gates']['g6_initial']['verdict']} "
        f"G6_RELEASE={report['gates']['g6_release']['verdict']}"
    )
    print(f"OUT={report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
