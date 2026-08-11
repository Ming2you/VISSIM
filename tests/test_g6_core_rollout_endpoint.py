# G6 하네스의 모델 rollout 이 상류 production endpoint 를 거치는지(우회 호출 0)와 이동 전 구현과 수치가 같은지 검증한다.
"""N7 잔여 — `harness/g6/g6_core.py:model_rollout_states` 의 직접 plant 호출 이동 검증.

참조 구현 `_ref_model_rollout` 은 **이동 직전 루프를 그대로 옮긴 것**이다
(`tests/test_vissim_stackelberg_adapter_fidelity.py` 의 `_ref_sup_score` / `_ref_one_step`
선례와 같은 패턴). 세 축을 대조한다.

  1. demand-from-state 동일성 — `build_forecast` 가 정확히 H 개를, 전부 같은 값으로 낸다.
     이동 후 endpoint 는 `forecast[:depth]` 로 자르므로 이 불변식이 클램프 제거의 근거다.
  2. H-step 동일성 — 상태열 전체(dataclass 필드 전부, time_sec 포함)가 비트 동일.
  3. objective 동일성 — `objective_from_states` 항 전체와 `spillback_flag` 가 동일.
"""

from __future__ import annotations

import dataclasses
import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
G6_DIR = REPO / "harness" / "g6"
if str(G6_DIR) not in sys.path:
    sys.path.insert(0, str(G6_DIR))

import g6_core as core  # noqa: E402

REAL_STATE = (
    REPO
    / "evaluation/runs/forced_response_grid_20260802/decisions_fw100_nc_seed13/state_000900.json"
)

# 대조에 쓰는 후보 — 네 채널(vsl / ramp / green / offset)과 앵커·복합을 덮는다.
REFERENCE_CANDIDATE_IDS = (
    "c00_anchor",
    "c03_vsl80",
    "c12_rampd691",
    "c20_major75",
    "c30_offset30",
    "c41_combined_extreme",
)


def _ref_model_rollout(rt, initial_state, control, forecast, horizon_steps: int) -> list:
    """`model_rollout_states` 이동 직전 루프(g6_core.py:365-374) 그대로."""
    from src.simulation.coupling import run_coupled_interval

    state = initial_state.copy()
    t0 = float(getattr(initial_state, "time_sec", 0.0))
    interval = float(rt.cfg.simulation.control_interval)
    out: list = []
    for step in range(int(horizon_steps)):
        demand = forecast[min(step, len(forecast) - 1)]
        run_coupled_interval(state, control, demand, rt.cfg)
        state.time_sec = t0 + interval * (step + 1)
        out.append(state.copy())
    return out


def _probe(fn):
    """fn 실행 중 run_coupled_interval 이 endpoint 프레임 밖에서 불린 횟수를 센다."""
    import src.controllers.rollout_endpoint as rep
    import src.simulation.coupling as coupling

    original = coupling.run_coupled_interval
    counts = {"inside": 0, "outside": 0}

    def probed(*args, **kwargs):
        counts["inside" if rep.endpoint_active() else "outside"] += 1
        return original(*args, **kwargs)

    coupling.run_coupled_interval = probed
    try:
        out = fn()
    finally:
        coupling.run_coupled_interval = original
    return counts, out


def _dump(states) -> str:
    """상태열을 dataclass 필드 전부로 직렬화 — 비트 동일 비교용."""
    return json.dumps([dataclasses.asdict(s) for s in states], sort_keys=True)


@unittest.skipUnless(REAL_STATE.exists(), f"실 상태 JSON 없음: {REAL_STATE}")
class G6ModelRolloutEndpointTests(unittest.TestCase):
    """실 관측 상태 하나로 이동 전/후를 대조한다."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.state_json = json.loads(REAL_STATE.read_text(encoding="utf-8"))
        cls.rt = core.build_runtime(cls.state_json)
        cls.initial = core.project_observed_state(cls.rt, cls.state_json)

    def _control(self, candidate_id: str):
        cand = core.candidate_by_id(candidate_id)
        return core.build_control(self.rt.cfg, self.rt.ControlAction, cand)

    def test_forecast_is_exactly_h_identical_steps(self) -> None:
        """클램프 제거 근거 — demand_from_state 가 정확히 H 개를 같은 값으로 낸다."""
        for horizon in (1, 3, 5):
            forecast = core.build_forecast(self.rt, self.state_json, horizon)
            self.assertEqual(len(forecast), horizon)
            for step in forecast[1:]:
                self.assertIs(step, forecast[0])

    def test_model_rollout_states_has_no_bypass(self) -> None:
        """우회 호출 0 — plant 전진이 전부 endpoint 프레임 안에서 일어난다."""
        forecast = core.build_forecast(self.rt, self.state_json, 3)
        control = self._control("c00_anchor")
        counts, states = _probe(
            lambda: core.model_rollout_states(self.rt, self.initial, control, forecast, 3)
        )
        self.assertEqual(len(states), 3)
        self.assertGreater(counts["inside"], 0)
        self.assertEqual(counts["outside"], 0)

    def test_model_rollout_states_matches_reference_states(self) -> None:
        """H-step 동일성 — 후보 6종 x H in {1,3,5} 에서 상태열이 비트 동일."""
        for horizon in (1, 3, 5):
            forecast = core.build_forecast(self.rt, self.state_json, horizon)
            for candidate_id in REFERENCE_CANDIDATE_IDS:
                control = self._control(candidate_id)
                got = core.model_rollout_states(
                    self.rt, self.initial, control, forecast, horizon
                )
                want = _ref_model_rollout(
                    self.rt, self.initial, control, forecast, horizon
                )
                with self.subTest(candidate=candidate_id, horizon=horizon):
                    self.assertEqual(len(got), len(want))
                    self.assertEqual(
                        [float(s.time_sec) for s in got],
                        [float(s.time_sec) for s in want],
                    )
                    self.assertEqual(_dump(got), _dump(want))

    def test_objective_and_spillback_match_reference(self) -> None:
        """objective 동일성 — 목적함수 항 전체와 spillback 판정이 동일."""
        horizon = 3
        forecast = core.build_forecast(self.rt, self.state_json, horizon)
        for candidate_id in REFERENCE_CANDIDATE_IDS:
            control = self._control(candidate_id)
            got = core.model_rollout_states(self.rt, self.initial, control, forecast, horizon)
            want = _ref_model_rollout(self.rt, self.initial, control, forecast, horizon)
            with self.subTest(candidate=candidate_id):
                self.assertEqual(
                    json.dumps(core.objective_from_states(self.rt, got, control), sort_keys=True),
                    json.dumps(core.objective_from_states(self.rt, want, control), sort_keys=True),
                )
                self.assertEqual(
                    core.spillback_flag(self.rt, got),
                    core.spillback_flag(self.rt, want),
                )

    def test_longer_forecast_than_horizon_is_truncated_not_clamped(self) -> None:
        """호출처 규약(len(forecast) >= H) 에서 endpoint 절단과 구 클램프가 같은 수요를 쓴다."""
        forecast = core.build_forecast(self.rt, self.state_json, 5)
        control = self._control("c03_vsl80")
        got = core.model_rollout_states(self.rt, self.initial, control, forecast, 3)
        want = _ref_model_rollout(self.rt, self.initial, control, forecast, 3)
        self.assertEqual(len(got), 3)
        self.assertEqual(_dump(got), _dump(want))


if __name__ == "__main__":
    unittest.main(verbosity=2)
