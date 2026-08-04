# run_g6_shadow.py 오케스트레이터 자체 검증 — 합성 런 디렉터리를 만들어 엔드투엔드로 돌린다.
"""실제 VISSIM 관측 상태열이 아직 없으므로, 이미 있는 state_000900.json 을 씨앗으로
후보별 관측 궤적을 **인위적으로 합성**한다.

두 시나리오를 만든다.
  agree    — 관측 목적함수 순위를 모델 순위와 일치시키는 방향으로 합성(ρ ≈ +1 기대)
  reverse  — 정확히 반대로 합성(ρ ≈ −1 기대)

목적은 오케스트레이터의 배선(디렉터리 스캔 → 초기상태 동일성 검증 → rollout →
관측 투영 → shadow 레코드 → 게이트)이 실제로 도는지 확인하는 것이다.
"""

from __future__ import annotations

import copy
import json
import os
import tempfile
import shutil
import subprocess
import sys
from pathlib import Path

HARNESS = Path(__file__).resolve().parent
sys.path.insert(0, str(HARNESS))
import g6_core as core  # noqa: E402

SEED_STATE = (
    core.VISSIM_ROOT
    / "evaluation/runs/forced_response_grid_20260802/decisions_fw100_nc_seed13/state_000900.json"
)
SCRATCH = Path(os.environ.get("G6_SELFTEST_SCRATCH", tempfile.gettempdir())) / "g6_selftest"
SCRATCH.mkdir(parents=True, exist_ok=True)
PY = "C:/Users/alsrj/anaconda3/python.exe"


def scaled_state(base: dict, sim_sec: int, factor: float) -> dict:
    """차량 수를 factor 배로 스케일한 관측 상태. 목적함수는 재고에 단조증가한다."""

    out = copy.deepcopy(base)
    out["sim_sec"] = float(sim_sec)
    for link, rows in out["freeway_segments"].items():
        for row in rows:
            row["count"] = round(row["count"] * factor, 6)
            row["speed_sum"] = row["speed_sum"] * factor
    for key in ("total_vehicles", "urban_vehicles", "freeway_vehicles", "ramp_vehicles"):
        out[key] = round(out[key] * factor, 6)
    counts = out["local_observation"]["link_counts"]
    out["local_observation"]["link_counts"] = {k: round(v * factor, 6) for k, v in counts.items()}
    out["ramp_counts"] = {k: round(v * factor, 6) for k, v in out["ramp_counts"].items()}
    return out


def build_run_dir(root: Path, model_rank: list[str], mode: str, horizon_max: int = 5) -> None:
    if root.exists():
        shutil.rmtree(root)
    base = json.loads(SEED_STATE.read_text(encoding="utf-8"))
    order = model_rank if mode == "agree" else list(reversed(model_rank))
    for position, candidate_id in enumerate(order):
        factor = 1.0 + 0.04 * position          # 순위가 낮을수록(=뒤쪽) 재고를 더 크게
        decision_dir = root / f"decisions_synthcell_{candidate_id}_seed13"
        decision_dir.mkdir(parents=True, exist_ok=True)
        (decision_dir / "state_000900.json").write_text(
            SEED_STATE.read_text(encoding="utf-8"), encoding="utf-8"
        )
        for step in range(1, horizon_max + 1):
            sim_sec = 900 + 60 * step
            (decision_dir / f"state_{sim_sec:06d}.json").write_text(
                json.dumps(scaled_state(base, sim_sec, factor), ensure_ascii=False),
                encoding="utf-8",
            )


def model_ranking() -> list[str]:
    state_json = json.loads(SEED_STATE.read_text(encoding="utf-8"))
    runtime = core.build_runtime(state_json)
    initial = core.project_observed_state(runtime, state_json)
    forecast = core.build_forecast(runtime, state_json, 5)
    scores = {}
    for cand in core.ACTIVE_CANDIDATE_SET:
        control = core.build_control(runtime.cfg, runtime.ControlAction, cand)
        states = core.model_rollout_states(runtime, initial, control, forecast, 3)
        scores[cand.candidate_id] = core.objective_from_states(runtime, states, control)["g6_objective"]
    return [cid for cid, _ in sorted(scores.items(), key=lambda kv: kv[1])]


def run(mode: str) -> dict:
    run_dir = SCRATCH / f"g6_synth_run_{mode}"
    out_dir = SCRATCH / f"g6_synth_out_{mode}"
    build_run_dir(run_dir, RANK, mode)
    proc = subprocess.run(
        [PY, "-B", str(HARNESS / "run_g6_shadow.py"),
         "--run-dir", str(run_dir), "--out-dir", str(out_dir),
         "--t0", "900", "--horizons", "1,3,5"],
        capture_output=True, text=True, cwd=str(HARNESS),
    )
    print(f"--- mode={mode} exit={proc.returncode}")
    print(proc.stdout.strip())
    if proc.returncode != 0:
        print(proc.stderr[-3000:])
    return json.loads((out_dir / "g6_shadow_report.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    RANK = model_ranking()
    print("model rank (best first):", RANK)
    ok = True
    agree = run("agree")
    reverse = run("reverse")
    # 합성 관측은 H=3 모델 순위로 만들었으므로 **H=3 decision 에서만** ±1.0 이 나와야 한다.
    # H=1/H=5 는 모델 순위 자체가 다르므로 ±1.0 이 아닌 것이 정상이다(순위의 호라이즌 의존성).
    def pick(report, decision_id):
        return next(d for d in report["per_decision"] if d["decision_id"] == decision_id)

    a3 = pick(agree, "synthcell_seed13_H3")
    r3 = pick(reverse, "synthcell_seed13_H3")
    print("\nper-decision:")
    for label, report in (("AGREE", agree), ("REVERSE", reverse)):
        for item in report["per_decision"]:
            print(
                f"  {label:<8}{item['decision_id']:<24} rho={item['spearman_rho']:+.6f} "
                f"pairwise={item['top_action_pairwise']['agreement']:.4f}"
            )
    ok &= abs(a3["spearman_rho"] - 1.0) < 1e-12 and a3["top_action_pairwise"]["agreement"] == 1.0
    ok &= abs(r3["spearman_rho"] + 1.0) < 1e-12 and r3["top_action_pairwise"]["agreement"] == 0.0
    ok &= agree["decision_count"] == 3 and reverse["decision_count"] == 3
    ok &= agree["record_count"] == 42 and reverse["record_count"] == 42
    ok &= agree["gates"]["g6_initial"]["verdict"] != "PASS"      # spillback 미관측 → NOT_EVALUATED
    ok &= reverse["gates"]["g6_initial"]["verdict"] == "FAIL"
    print("\nORCHESTRATOR_SELFTEST=" + ("PASS" if ok else "FAIL"))
    raise SystemExit(0 if ok else 1)
