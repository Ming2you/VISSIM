# 구성(FD x 토폴로지 x capacity drop)별로 G5 와 G6 를 같은 rollout 에서 함께 측정하는 그리드 드라이버.
"""run_gates.py 를 **수정하지 않고** 구성 축만 스윕한다.

  python run_config_grid.py --out-dir <dir>

무엇을 하는가.
  1) 채점 구성 5개(evaluation/configs/gates_scoring/*.json)를 차례로 실체화한다.
  2) 각 구성에서 `run_gates.run_g5` 로 teacher-forced rolling-origin G5 를 낸다(H=1/3/5).
  3) 같은 구성에서 `run_gates.run_g6` 를 **여러 t0** 에 대해 돌려 레코드를 합친다.
     - g6_branch_grid_20260802 는 t=1200 s 까지만 관측이 있다. 따라서
       H=5(300 s) 는 t0=900 에서만, H=3 은 t0<=1020, H=1 은 t0<=1140 에서만 성립한다.
     - decision_id 에 t0 를 박아 서로 다른 결정으로 센다(원본은 t0 를 안 넣어 충돌한다).
  4) shadow.py 로 채점하고 구성 간 비교표를 만든다.

산출물 <out>/<config>/ 아래는 run_gates 와 같은 파일 이름을 쓰고,
<out>/config_grid_summary.json 에 한 장 비교표를 쓴다.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import episode as ep  # noqa: E402
import g5_metrics as g5  # noqa: E402
import g6_core as core  # noqa: E402
import g6_records as rec  # noqa: E402
import run_gates as rg  # noqa: E402

ROOT = core.VISSIM_ROOT
CONFIG_DIR = ROOT / "evaluation" / "configs" / "gates_scoring"

# (키, 튜닝 파일, 사람이 읽는 라벨)
CONFIGS: list[tuple[str, Path, str]] = [
    ("a_FDA_pre", CONFIG_DIR / "gates_cfgA_pre.json",
     "(a) FD_A + 토폴로지 정정 전"),
    ("b_FDA_post", CONFIG_DIR / "gates_cfgB_post.json",
     "(b) FD_A + 토폴로지 정정 후"),
    ("c_FDC_post", CONFIG_DIR / "gates_cfgC_fdc_post.json",
     "(c) FD_C 자유분지 재적합 + 토폴로지 정정 후"),
    ("d_FDA_post_cd", CONFIG_DIR / "gates_cfgD_fda_post_cd.json",
     "(d) FD_A + 토폴로지 정정 후 + capacity drop phi=0.6"),
    ("e_FDC_post_cd", CONFIG_DIR / "gates_cfgE_fdc_post_cd.json",
     "(e) FD_C + 토폴로지 정정 후 + capacity drop phi=0.6"),
]

G5_RUN_DIRS = [
    ROOT / "evaluation/runs/new_baseline_ab_20260801/decisions_pstack_flagship_scale135_warm900_eval3600_seed13",
    ROOT / "evaluation/runs/new_baseline_ab_20260801/decisions_pstack_flagship_scale170_warm900_eval3600_seed13",
    ROOT / "evaluation/runs/new_baseline_ab_20260801/decisions_stackelberg_scale135_warm900_eval3600_seed13",
    ROOT / "evaluation/runs/new_baseline_ab_20260801/decisions_stackelberg_scale170_warm900_eval3600_seed13",
]
G6_RUN_DIR = ROOT / "evaluation/runs/g6_branch_grid_20260802"

# ★ t0 는 900 하나뿐이다 — 늘릴 수 없다.
#
# 처음에는 t0 ∈ {900, 960, 1020, 1080, 1140} 로 결정 수를 늘리려 했다. 실행해 보니
# 900 을 뺀 전부가 `ERROR=INITIAL_STATE_MISMATCH` 로 기각됐다. 옳은 기각이다 —
# 공통 접두 시드 리플레이는 t0=900 **까지만** 모든 arm 을 동일하게 유지하고, 그 뒤로는
# arm 마다 다른 액션이 집행되어 상태가 갈린다. t0=960 에서 14개 arm 은 서로 다른
# 초기상태에 있으므로 "같은 상태에서 후보를 비교한다"는 G6 의 전제가 깨진다.
# 아래 계획은 그 기각을 리포트에 남기기 위해 그대로 둔다(요청 t0 vs 채택 t0).
G6_T0_PLAN: list[tuple[int, list[int]]] = [
    (900, [1, 3, 5]),
    (960, [1, 3]),
    (1020, [1, 3]),
    (1080, [1]),
    (1140, [1]),
]


def _args(tuning: Path, **extra) -> SimpleNamespace:
    base = dict(
        out_dir=None,
        horizons="1,3,5",
        g5_run_dir=[str(p) for p in G5_RUN_DIRS],
        g5_t_min=900, g5_t_max=None, g5_stride=1, free_run=False,
        g6_run_dir=None, g6_t0=900, g6_persistence=True, spillback_threshold=0.90,
        mapping_json=core.DEFAULT_MAPPING,
        detector_mapping_json=core.DEFAULT_DETECTOR_MAPPING,
        calibration_json=core.DEFAULT_CALIBRATION,
        tuning_json=tuning,
    )
    base.update(extra)
    return SimpleNamespace(**base)


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str),
                    encoding="utf-8")


def _criteria(report: dict[str, Any], gate: str) -> dict[str, Any]:
    return {c["name"]: {"value": c["value"], "threshold": c["threshold"], "verdict": c["verdict"]}
            for c in report["gates"][gate]["criteria"]}


def run_g6_multi_t0(tuning: Path, out_dir: Path) -> dict[str, Any]:
    """여러 t0 에서 G6 레코드를 모아 하나로 채점한다."""

    records: list[dict[str, Any]] = []
    persistence: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    accepted_t0: list[int] = []
    rejected_t0: list[int] = []
    for t0, horizons in G6_T0_PLAN:
        args = _args(tuning, g6_run_dir=G6_RUN_DIR, g6_t0=t0,
                     horizons=",".join(str(h) for h in horizons))
        result = rg.run_g6(args, horizons)
        if not result or not result.get("records"):
            rejected_t0.append(t0)
            continue
        accepted_t0.append(t0)
        for record in result["records"]:
            record["decision_id"] = f"{record['decision_id']}_t{t0}"
            records.append(record)
        for record in result.get("persistence_records", []):
            record["decision_id"] = f"{record['decision_id']}_t{t0}"
            persistence.append(record)
        for row in result["rows"]:
            row["decision_id"] = f"{row['decision_id']}_t{t0}"
            row["t0_sec"] = t0
            rows.append(row)

    if not records:
        return {"error": "G6 레코드 0개"}

    rec.write_jsonl(out_dir / "g6_records.jsonl", records)
    _write(out_dir / "g6_rows.json", rows)
    report = rec.evaluate_and_write(records, out_dir / "g6_report.json")

    complete_ids = {d["decision_id"] for d in report["per_decision"]
                    if d["ranking_status"] != rec.NOT_EVALUATED}
    complete = [r for r in records if r["decision_id"] in complete_ids]
    strict = rec.evaluate_shadow_records(complete) if complete else None
    if strict is not None:
        _write(out_dir / "g6_report_complete_only.json", strict)

    by_h: dict[str, Any] = {}
    for horizon in (1, 3, 5):
        subset = [r for r in complete if f"_H{horizon}_t" in r["decision_id"]]
        if subset:
            evaluated = rec.evaluate_shadow_records(subset)
            by_h[str(horizon)] = {
                "horizon_sec": horizon * 60,
                "decision_count": evaluated["decision_count"],
                "spearman_rho": evaluated["aggregate"]["spearman_rho"],
                "pairwise": evaluated["aggregate"]["top_action_pairwise"]["agreement"],
                "spillback_f1": evaluated["aggregate"]["spillback"]["f1"],
                "spillback_oracle_complete": evaluated["aggregate"]["spillback_oracle_complete"],
                "g6_initial": evaluated["gates"]["g6_initial"]["verdict"],
            }
    _write(out_dir / "g6_by_horizon.json", by_h)

    if persistence:
        rec.write_jsonl(out_dir / "g6_records_persistence.jsonl", persistence)
        persistence_report = rec.evaluate_and_write(
            persistence, out_dir / "g6_report_persistence.json")
    else:
        persistence_report = None

    return {
        "report": report, "strict": strict, "by_horizon": by_h, "rows": rows,
        "t0_accepted": accepted_t0,
        "t0_rejected_initial_state_mismatch": rejected_t0,
        "persistence": None if persistence_report is None else {
            "decision_count": persistence_report["decision_count"],
            "spearman_rho": persistence_report["aggregate"]["spearman_rho"],
            "ranking_oracle_complete":
                persistence_report["aggregate"]["ranking_oracle_complete"],
            "verdict": persistence_report["gates"]["g6_initial"]["verdict"],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--only", default="", help="쉼표로 구분한 구성 키(디버그용)")
    parser.add_argument("--skip-g5", action="store_true")
    parser.add_argument("--skip-g6", action="store_true")
    parser.add_argument("--free-run", action="store_true",
                        help="참고 지표 (B) 개루프 자유주행도 기록한다")
    args_cli = parser.parse_args()

    out_root = Path(args_cli.out_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    wanted = {k.strip() for k in args_cli.only.split(",") if k.strip()}

    horizons = [1, 3, 5]
    summary: dict[str, Any] = {
        "protocol": "teacher_forced_rolling_origin",
        "horizons_steps": horizons,
        "horizon_sec": [h * 60 for h in horizons],
        "g5_run_dirs": [str(p) for p in G5_RUN_DIRS],
        "g6_run_dir": str(G6_RUN_DIR),
        "g6_t0_plan": [{"t0_sec": t0, "horizons": hs} for t0, hs in G6_T0_PLAN],
        "configs": {},
    }

    for key, tuning, label in CONFIGS:
        if wanted and key not in wanted:
            continue
        started = time.perf_counter()
        out_dir = out_root / key
        out_dir.mkdir(parents=True, exist_ok=True)
        entry: dict[str, Any] = {"label": label, "tuning": str(tuning)}

        # 구성이 실제로 무엇으로 실체화됐는지 리포트에 함께 남긴다.
        probe = ep.read_json(G5_RUN_DIRS[0] / "state_000900.json")
        rt_probe = core.build_runtime(probe, tuning_json=tuning)
        net = rt_probe.cfg.network
        profile = getattr(net, "freeway_segment_length_profile_km", {}) or {}
        entry["realized"] = {
            "v_free": float(net.v_free), "rho_crit": float(net.rho_crit),
            "a_m": float(getattr(net, "metanet_a_m", 0.0)),
            "q_cap_veh_h": float(net.freeway_capacity_veh_h),
            "seg_len_scalar_km": float(net.freeway_segment_length_km),
            "seg_len_FW_E_km": (profile.get("FW_E") or [None])[0],
            "seg_len_FW_W_km": (profile.get("FW_W") or [None])[0],
            "capacity_drop_phi": float(getattr(net, "capacity_drop_discharge_phi", 1.0) or 1.0),
            "control_interval_sec": float(rt_probe.cfg.simulation.control_interval),
        }

        if not args_cli.skip_g5:
            g5_result = rg.run_g5(_args(tuning, free_run=args_cli.free_run), horizons)
            if g5_result and "overall" in g5_result:
                overall = g5_result["overall"]
                _write(out_dir / "g5_report.json", overall)
                _write(out_dir / "g5_by_stratum.json",
                       {"by_stratum": g5_result["by_stratum"], "holdout": g5_result["holdout"]})
                if g5_result["free_run_reference"]:
                    _write(out_dir / "g5_free_run.json", g5_result["free_run_reference"])
                entry["g5"] = {
                    "episode_count": overall["episode_count"],
                    "initial": overall["gates"]["g5_initial"]["verdict"],
                    "promotion": overall["gates"]["g5_promotion"]["verdict"],
                    "criteria": _criteria(overall, "g5_initial"),
                    "aggregate": {level: {k: stats[k] for k in ("mae", "mape", "bias",
                                                                "mean_observed", "sample_count")}
                                  for level, stats in overall["aggregate"].items()},
                    "by_horizon": {
                        h: {"criteria": _criteria(report, "g5_initial"),
                            "verdict": report["gates"]["g5_initial"]["verdict"],
                            "persistence_skill": report.get("persistence_baseline", {})
                                                       .get("skill_score")}
                        for h, report in overall.get("by_horizon", {}).items()},
                    "persistence_skill": overall.get("persistence_baseline", {}).get("skill_score"),
                    "urban": {
                        "coverage_ratio": overall["urban"]["coverage"]["ratio"],
                        "evaluable": overall["urban"]["evaluable"],
                        "relative_error": overall["urban"]["relative_error"],
                    },
                    "holdout": g5_result["holdout"]["distinct_values"],
                }
                if g5_result["free_run_reference"]:
                    entry["g5"]["free_run_reference"] = [
                        {"decision_dir": Path(item["decision_dir"]).name,
                         "steps": item["steps"],
                         "cell_count_mae": item["report"]["aggregate"]["cell_count"]["mae"],
                         "cell_speed_mape": item["report"]["aggregate"]["cell_speed"]["mape"]}
                        for item in g5_result["free_run_reference"]]
            else:
                entry["g5"] = {"error": (g5_result or {}).get("error", "G5 실패")}

        if not args_cli.skip_g6:
            g6_result = run_g6_multi_t0(tuning, out_dir)
            if "error" in g6_result:
                entry["g6"] = g6_result
            else:
                report, strict = g6_result["report"], g6_result["strict"]
                entry["g6"] = {
                    "decision_count": report["decision_count"],
                    "all_decisions": {
                        "spearman_rho": report["aggregate"]["spearman_rho"],
                        "pairwise": report["aggregate"]["top_action_pairwise"]["agreement"],
                        "spillback_f1": report["aggregate"]["spillback"]["f1"],
                        "initial": report["gates"]["g6_initial"]["verdict"],
                    },
                    "complete_decisions_only": None if strict is None else {
                        "decision_count": strict["decision_count"],
                        "spearman_rho": strict["aggregate"]["spearman_rho"],
                        "pairwise": strict["aggregate"]["top_action_pairwise"]["agreement"],
                        "spillback_f1": strict["aggregate"]["spillback"]["f1"],
                        "spillback_oracle_complete":
                            strict["aggregate"]["spillback_oracle_complete"],
                        "initial": strict["gates"]["g6_initial"]["verdict"],
                        "release": strict["gates"]["g6_release"]["verdict"],
                    },
                    "by_horizon": g6_result["by_horizon"],
                    "persistence_control": g6_result["persistence"],
                    "t0_accepted": g6_result["t0_accepted"],
                    "t0_rejected_initial_state_mismatch":
                        g6_result["t0_rejected_initial_state_mismatch"],
                }

        entry["elapsed_sec"] = round(time.perf_counter() - started, 1)
        summary["configs"][key] = entry
        _write(out_root / "config_grid_summary.json", summary)
        print(f"[{key}] done in {entry['elapsed_sec']}s "
              f"G5={entry.get('g5', {}).get('initial')} "
              f"G6={entry.get('g6', {}).get('complete_decisions_only', {}) or {}}")

    _write(out_root / "config_grid_summary.json", summary)
    print(f"OUT={out_root / 'config_grid_summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
