# G6 측정 매트릭스 러너 — FD 구성 x 셀그룹으로 run_g6_shadow.py 를 돌리고 호라이즌별로 재채점한다.
"""FD 파라미터는 **모델 쪽에만** 들어간다. 플랜트(VISSIM) 런은 FD 와 무관하므로
한 번만 돌린 관측 궤적을 여러 FD 구성으로 재채점하면 된다. 이 스크립트가 그 이중루프다.

산출물.
  <out>/<config>/<cellgroup>/g6_shadow_records.jsonl   : run_g6_shadow.py 원본 산출
  <out>/<config>/merged_records.jsonl                  : 셀그룹 병합
  <out>/<config>/report_all.json / report_H<h>.json    : 전체 및 호라이즌별 shadow 리포트
  <out>/g6_matrix_summary.json                         : 구성 x 호라이즌 지표표
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
import g6_records as rec  # noqa: E402

PYTHON = sys.executable

# tag -> 채점 튜닝 JSON (VISSIM 저장소 루트 기준 상대경로)
CONFIGS = {
    "fdA": "evaluation/configs/real_world_modi_pstack_flagship_segvsl_fdrefit_20260802.json",
    "fdC": "evaluation/configs/g6_scoring/g6_score_fdC.json",
    "fdA_cd": "evaluation/configs/g6_scoring/g6_score_fdA_cd.json",
    "fdC_cd": "evaluation/configs/g6_scoring/g6_score_fdC_cd.json",
}

# (셀그룹 이름, 런 디렉터리, t0)
CELL_GROUPS = [
    ("freeflow", "evaluation/runs/g6_branch_grid_20260802", 900),
    ("cong4200", "evaluation/runs/g6_cong4200_20260802", 4200),
    ("cong3600", "evaluation/runs/g6_cong3600_20260802", 3600),
]


def horizon_of(decision_id: str) -> str:
    return decision_id.rsplit("_H", 1)[-1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=HERE.parents[1])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--horizons", default="1,3,5")
    parser.add_argument("--configs", default=",".join(CONFIGS))
    args = parser.parse_args()

    repo = args.repo.resolve()
    horizons = [h.strip() for h in args.horizons.split(",") if h.strip()]
    summary: dict[str, dict] = {}

    for tag in [c.strip() for c in args.configs.split(",") if c.strip()]:
        tuning = repo / CONFIGS[tag]
        merged: list[dict] = []
        per_group: dict[str, dict] = {}
        for group, run_dir_rel, t0 in CELL_GROUPS:
            run_dir = repo / run_dir_rel
            if not run_dir.exists():
                print(f"SKIP group={group} (런 디렉터리 없음: {run_dir})")
                continue
            out_dir = args.out / tag / group
            cmd = [
                PYTHON, "-B", str(HERE / "run_g6_shadow.py"),
                "--run-dir", str(run_dir),
                "--out-dir", str(out_dir),
                "--t0", str(t0),
                "--horizons", ",".join(horizons),
                "--tuning-json", str(tuning),
            ]
            print(f"RUN config={tag} group={group} t0={t0}")
            proc = subprocess.run(cmd, cwd=str(HERE), capture_output=True, text=True, encoding="utf-8")
            sys.stdout.write(proc.stdout or "")
            if proc.returncode != 0:
                sys.stderr.write(proc.stderr or "")
                print(f"FAIL config={tag} group={group} rc={proc.returncode}")
                continue
            group_records = rec.load_jsonl(out_dir / "g6_shadow_records.jsonl")
            # decision_id 에 셀그룹 접두를 붙여 병합 시 충돌을 막는다.
            for item in group_records:
                item["decision_id"] = f"{group}__{item['decision_id']}"
            merged.extend(group_records)
            per_group[group] = rec.evaluate_shadow_records(group_records)

        if not merged:
            print(f"NO_RECORDS config={tag}")
            continue

        cfg_dir = args.out / tag
        cfg_dir.mkdir(parents=True, exist_ok=True)
        rec.write_jsonl(cfg_dir / "merged_records.jsonl", merged)
        report_all = rec.evaluate_and_write(merged, cfg_dir / "report_all.json")

        by_h = {}
        for h in horizons:
            subset = [r for r in merged if horizon_of(r["decision_id"]) == h]
            if not subset:
                continue
            by_h[h] = rec.evaluate_and_write(subset, cfg_dir / f"report_H{h}.json")

        summary[tag] = {
            "tuning_json": str(tuning),
            "all": _digest(report_all),
            "by_horizon": {h: _digest(r) for h, r in by_h.items()},
            "by_group": {g: _digest(r) for g, r in per_group.items()},
            "by_group_horizon": {
                g: {
                    h: _digest(rec.evaluate_shadow_records(
                        [r for r in merged
                         if r["decision_id"].startswith(g + "__") and horizon_of(r["decision_id"]) == h]
                    ))
                    for h in horizons
                    if any(r["decision_id"].startswith(g + "__") and horizon_of(r["decision_id"]) == h
                           for r in merged)
                }
                for g in per_group
            },
        }

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "g6_matrix_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nOUT={args.out / 'g6_matrix_summary.json'}")
    for tag, block in summary.items():
        a = block["all"]
        print(f"{tag:8s} rho={a['spearman_rho']} pair={a['pairwise']} f1={a['spillback_f1']} "
              f"initial={a['g6_initial']} release={a['g6_release']}")
    return 0


def _digest(report: dict) -> dict:
    agg = report["aggregate"]
    return {
        "decision_count": report["decision_count"],
        "spearman_rho": agg["spearman_rho"],
        "pairwise": agg["top_action_pairwise"]["agreement"],
        "spillback_f1": agg["spillback"]["f1"],
        "spillback_confusion": {
            k: agg["spillback"].get(k)
            for k in ("true_positive", "false_positive", "false_negative", "true_negative",
                      "precision", "recall")
        },
        "g6_initial": report["gates"]["g6_initial"]["verdict"],
        "g6_release": report["gates"]["g6_release"]["verdict"],
        "per_decision": [
            {"decision_id": d["decision_id"], "rho": d["spearman_rho"],
             "pairwise": d["top_action_pairwise"]["agreement"], "status": d["ranking_status"]}
            for d in report["per_decision"]
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main())
