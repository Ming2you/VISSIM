# persistence(Δ=0) 대조군을 G6 에 실제로 넣어 본다 — G5 에서 전 조합을 이겼던 예측자가 여기서 어떻게 되는가.
"""persistence 예측자는 "상태가 안 변한다"고 답한다. 즉 예측 상태열이 초기상태의 반복이고
**액션에 의존하지 않는다.** 그러면 후보 간 예측 목적함수가 전부 같아지고, Spearman 의
x_scale 이 0 이 되어 ρ 가 정의되지 않는다(shadow.py:225-227) → 그 decision 은
`ranking_oracle_complete=False` → 게이트가 PASS 가 아니라 **NOT_EVALUATED** 로 내려간다.

단, 이것을 단정하지 말고 재야 한다. `Leader.objective_terms` 에는 상태 항 외에 **액션 항**
(제어 벌점)이 섞여 있을 수 있고, 그렇다면 persistence 도 후보별로 값이 달라져 순위를 갖는다.
이 스크립트는 그 값을 실제로 계산해서 (a) 후보 간 값이 몇 개나 구별되는지, (b) 그 순위가
VISSIM 순위와 얼마나 맞는지를 함께 보고한다.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import g6_core as core
import g6_records as rec
import run_g6_shadow as orch


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--t0", type=int, default=900)
    parser.add_argument("--horizons", default="1,3,5")
    parser.add_argument("--tuning-json", type=Path, default=core.DEFAULT_TUNING)
    args = parser.parse_args()

    horizons = [int(h) for h in str(args.horizons).split(",") if h.strip()]
    cells = orch.discover_cells(args.run_dir, args.t0)
    if not cells:
        print(f"ERROR=NO_CELLS run_dir={args.run_dir}")
        return 2

    policy_hash = rec.hash_payload({"predictor": "persistence", "tuning": str(args.tuning_json)})
    build_hash = rec.file_hash(core.ADAPTER_DIR / "vissim_stackelberg_adapter.py")
    schema_hash = rec.hash_payload({"candidate_set": [c.candidate_id for c in core.ACTIVE_CANDIDATE_SET]})

    records: list[dict] = []
    distinct_report: list[dict] = []

    for (cell, seed), arms in sorted(cells.items()):
        anchor_dir = arms[sorted(arms)[0]]
        init_json = orch.load_state_json(orch.state_path(anchor_dir, args.t0))
        runtime = core.build_runtime(init_json, tuning_json=args.tuning_json)
        init_hashes = {a: rec.file_hash(orch.state_path(p, args.t0)) for a, p in arms.items()}
        if len(set(init_hashes.values())) != 1:
            print(f"ERROR=INITIAL_STATE_MISMATCH cell={cell} seed={seed}")
            continue
        state_hash = next(iter(init_hashes.values()))
        initial_state = core.project_observed_state(runtime, init_json)
        interval = int(round(float(runtime.cfg.simulation.control_interval)))

        for horizon in horizons:
            decision_id = f"{cell}_seed{seed}_H{horizon}"
            values: dict[str, float] = {}
            for arm, decision_dir in sorted(arms.items()):
                try:
                    cand = core.candidate_by_id(arm)
                except KeyError:
                    continue
                control = core.build_control(runtime.cfg, runtime.ControlAction, cand)
                # persistence — 예측 상태열은 초기상태의 단순 반복이다.
                predicted = [initial_state.copy() for _ in range(horizon)]
                terms = core.objective_from_states(runtime, predicted, control)
                values[arm] = terms["g6_objective"]
                spill = core.spillback_flag(runtime, predicted)

                observed_states = []
                missing = False
                for step in range(1, horizon + 1):
                    path = orch.state_path(decision_dir, args.t0 + interval * step)
                    if not path.exists():
                        missing = True
                        break
                    observed_states.append(
                        core.project_observed_state(runtime, orch.load_state_json(path))
                    )
                if missing:
                    obs_obj = obs_spill = None
                else:
                    obs_obj = core.objective_from_states(runtime, observed_states, control)["g6_objective"]
                    obs_spill = core.spillback_flag(runtime, observed_states)

                records.append(
                    rec.build_record(
                        decision_id=decision_id, candidate_id=arm,
                        model_objective=terms["g6_objective"], vissim_objective=obs_obj,
                        model_spillback=spill, vissim_spillback=obs_spill,
                        action_payload={"variant": cand.variant, "predictor": "persistence",
                                        "horizon_steps": horizon},
                        policy_hash=policy_hash, build_hash=build_hash,
                        action_schema_hash=schema_hash,
                        topology_hash=rec.hash_payload({"predictor": "persistence"}),
                        program_hash=rec.hash_payload({"cell": cell, "seed": seed, "t0": args.t0}),
                        state_hash=state_hash, model_runtime_sec=0.0,
                    )
                )
            distinct_report.append({
                "decision_id": decision_id,
                "candidate_count": len(values),
                "distinct_predicted_values": len(set(round(v, 9) for v in values.values())),
                "value_range": (max(values.values()) - min(values.values())) if values else None,
                "values": values,
            })

    args.out_dir.mkdir(parents=True, exist_ok=True)
    rec.write_jsonl(args.out_dir / "g6_persistence_records.jsonl", records)
    (args.out_dir / "g6_persistence_distinct.json").write_text(
        json.dumps(distinct_report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    report = rec.evaluate_and_write(records, args.out_dir / "g6_persistence_report.json")
    agg = report["aggregate"]
    print(f"RECORDS={len(records)} DECISIONS={report['decision_count']}")
    print(f"SPEARMAN={agg['spearman_rho']} RANKING_ORACLE_COMPLETE={agg['ranking_oracle_complete']}")
    print(f"PAIRWISE={agg['top_action_pairwise']['agreement']}")
    print(f"G6_INITIAL={report['gates']['g6_initial']['verdict']}")
    for item in distinct_report:
        print(f"  {item['decision_id']:28s} distinct={item['distinct_predicted_values']}/"
              f"{item['candidate_count']} range={item['value_range']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
