# G6 순위가 어디서 뒤집히는지 분해한다 — 축별 민감도, 불일치 쌍, 램프 미터링 기여 분리.
"""구성 그리드 산출물(g6_rows.json)에서 순위 뒤집힘의 위치를 특정한다.

세 가지를 낸다.
  1) 축별 민감도 — 앵커(c00) 대비 목적함수 변화량을 모델/VISSIM 양쪽에서. 모델이
     그 채널에 **반응하지 않으면** 순위를 매길 수 없다는 것이 여기서 드러난다.
  2) 불일치 쌍 — 부호가 반대인 (i,j) 쌍을 크기순으로. 특히 top-action 을 포함한 쌍.
  3) 축 제거 실험 — 어떤 축의 후보를 빼면 rho 가 얼마나 회복되는지. 어느 채널이
     실패를 만들고 있는지를 기여도로 분리한다.

또한 공통 접두 리플레이가 t0 이후 갈라진다는 사실을 state 해시로 직접 확인한다
(G6 를 t0=900 하나로 제한할 수밖에 없는 이유의 증거).
"""

from __future__ import annotations

import hashlib
import json
import sys
from itertools import combinations
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import episode as ep  # noqa: E402
import g6_core as core  # noqa: E402
import g6_records as rec  # noqa: E402

GRID = core.VISSIM_ROOT / "outputs" / "gates_config_grid_20260802"
G6_RUN_DIR = core.VISSIM_ROOT / "evaluation/runs/g6_branch_grid_20260802"
AXIS = {c.candidate_id: c.axis for c in core.ACTIVE_CANDIDATE_SET}
CONFIGS = ["a_FDA_pre", "b_FDA_post", "c_FDC_post", "d_FDA_post_cd", "e_FDC_post_cd"]


def load_rows(config: str) -> list[dict[str, Any]]:
    rows = json.loads((GRID / config / "g6_rows.json").read_text(encoding="utf-8"))
    return [r for r in rows
            if r["decision_id"].startswith("fw100_seed13") and r["vissim_objective"] is not None]


def rank_map(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    ordered = sorted(rows, key=lambda r: (r[key], r["candidate_id"]))
    return {r["candidate_id"]: i + 1 for i, r in enumerate(ordered)}


def discordant_pairs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """모델과 VISSIM 의 부호가 반대인 쌍. 크기는 VISSIM 쪽 격차로 잰다."""

    out = []
    for left, right in combinations(rows, 2):
        dm = left["model_objective"] - right["model_objective"]
        dv = left["vissim_objective"] - right["vissim_objective"]
        if dm * dv < 0:
            out.append({
                "pair": f"{left['candidate_id']} vs {right['candidate_id']}",
                "axes": f"{AXIS[left['candidate_id']]}/{AXIS[right['candidate_id']]}",
                "model_delta": round(dm, 4), "vissim_delta": round(dv, 4),
                "vissim_gap_abs": abs(dv),
            })
    out.sort(key=lambda item: -item["vissim_gap_abs"])
    return out


def axis_sensitivity(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    anchor = next(r for r in rows if r["candidate_id"] == "c00_anchor")
    out = []
    for row in sorted(rows, key=lambda r: r["candidate_id"]):
        if row["candidate_id"] == "c00_anchor":
            continue
        dm = row["model_objective"] - anchor["model_objective"]
        dv = row["vissim_objective"] - anchor["vissim_objective"]
        out.append({
            "candidate": row["candidate_id"], "axis": AXIS[row["candidate_id"]],
            "model_delta_vs_anchor": round(dm, 4),
            "vissim_delta_vs_anchor": round(dv, 4),
            "sign_agrees": (dm * dv > 0) or (abs(dm) < 1e-9 and abs(dv) < 1e-9),
        })
    return out


def rho_without_axis(records: list[dict[str, Any]], drop_axis: str) -> float | None:
    keep = [r for r in records if AXIS.get(r["candidate_id"]) != drop_axis]
    if not keep:
        return None
    report = rec.evaluate_shadow_records(keep)
    return report["aggregate"]["spearman_rho"]


def rho_only_axis(records: list[dict[str, Any]], axes: set[str]) -> float | None:
    keep = [r for r in records if AXIS.get(r["candidate_id"]) in axes]
    report = rec.evaluate_shadow_records(keep)
    return report["aggregate"]["spearman_rho"]


def prefix_replay_divergence() -> dict[str, Any]:
    """arm 들의 state 해시가 t0=900 이후 언제 갈라지는지 직접 확인한다."""

    arms = sorted(p for p in G6_RUN_DIR.glob("decisions_fw100_*_seed13") if p.is_dir())
    out: dict[str, Any] = {"arm_count": len(arms), "by_t": {}}
    for t in (900, 960, 1020, 1080, 1140, 1200):
        hashes = set()
        present = 0
        for arm in arms:
            path = arm / f"state_{t:06d}.json"
            if path.exists():
                hashes.add(hashlib.sha256(path.read_bytes()).hexdigest())
                present += 1
        out["by_t"][str(t)] = {"arms_with_state": present, "distinct_state_hashes": len(hashes),
                               "identical": len(hashes) == 1}
    return out


def main() -> int:
    result: dict[str, Any] = {
        "prefix_replay_divergence": prefix_replay_divergence(),
        "by_config": {},
    }
    for config in CONFIGS:
        rows = load_rows(config)
        records = [json.loads(line) for line in
                   (GRID / config / "g6_records.jsonl").read_text(encoding="utf-8").splitlines()
                   if line.strip()]
        records = [r for r in records
                   if r["decision_id"].startswith("fw100_seed13")
                   and r.get("vissim_observed_objective") is not None]
        entry: dict[str, Any] = {}
        for horizon in (1, 3, 5):
            sub_rows = [r for r in rows if r["horizon_steps"] == horizon]
            sub_records = [r for r in records if f"_H{horizon}_t900" in r["decision_id"]]
            if not sub_rows:
                continue
            mrank, vrank = rank_map(sub_rows, "model_objective"), rank_map(sub_rows, "vissim_objective")
            table = [{
                "candidate": r["candidate_id"], "axis": AXIS[r["candidate_id"]],
                "model_objective": round(r["model_objective"], 4),
                "vissim_objective": round(r["vissim_objective"], 4),
                "model_rank": mrank[r["candidate_id"]], "vissim_rank": vrank[r["candidate_id"]],
                "rank_error": mrank[r["candidate_id"]] - vrank[r["candidate_id"]],
            } for r in sorted(sub_rows, key=lambda r: mrank[r["candidate_id"]])]
            vissim_values = [r["vissim_objective"] for r in sub_rows]
            model_values = [r["model_objective"] for r in sub_rows]
            entry[f"H{horizon}"] = {
                "table": table,
                "axis_sensitivity": axis_sensitivity(sub_rows),
                "discordant_pairs_top": discordant_pairs(sub_rows)[:10],
                "discordant_pair_count": len(discordant_pairs(sub_rows)),
                "oracle_tie_groups": len(vissim_values) - len(set(vissim_values)),
                "model_spread": round(max(model_values) - min(model_values), 4),
                "vissim_spread": round(max(vissim_values) - min(vissim_values), 4),
                "ablation_rho": {
                    "all": rec.evaluate_shadow_records(sub_records)["aggregate"]["spearman_rho"],
                    "drop_ramp": rho_without_axis(sub_records, "ramp"),
                    "drop_green": rho_without_axis(sub_records, "green"),
                    "drop_combined": rho_without_axis(sub_records, "combined"),
                    "drop_vsl": rho_without_axis(sub_records, "vsl"),
                    "only_vsl_anchor": rho_only_axis(sub_records, {"vsl", "anchor"}),
                    "only_ramp_anchor": rho_only_axis(sub_records, {"ramp", "anchor"}),
                    "only_green_anchor": rho_only_axis(sub_records, {"green", "anchor"}),
                },
            }
        result["by_config"][config] = entry

    out_path = GRID / "g6_flip_analysis.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OUT={out_path}")

    print("\n=== 공통 접두 리플레이 분기 ===")
    for t, info in result["prefix_replay_divergence"]["by_t"].items():
        print(f"  t={t:>5} s  arms={info['arms_with_state']:>2}  "
              f"distinct_hashes={info['distinct_state_hashes']:>2}  identical={info['identical']}")

    print("\n=== 축 제거 rho (H=3) ===")
    for config in CONFIGS:
        entry = result["by_config"][config].get("H3")
        if entry:
            ab = entry["ablation_rho"]
            print(f"  {config:<14} " + "  ".join(
                f"{k}={'None' if v is None else round(v, 3)}" for k, v in ab.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
