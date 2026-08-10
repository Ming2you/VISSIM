# v3 N3-1b - 관측 링크속도를 모델 storage 링크로 접어 TrafficState 에 싣는 것을 고정한다
"""어댑터는 `link_speeds_kph` 를 읽지만(:1459) 진단으로만 흘리고 있었다.

상태 반영 블록(:2941-2957)이 ramp_queue / boundary_queue / urban_movement_queue /
urban_link_storage 넷만 쓰기 때문에, 지연 산식(`_link_delay_steps`)은 관측 속도를 전혀
못 본 채 전역 상수 `urban_avg_speed_km_h` 만 썼다.

두 가지를 못 박는다.

1. **접기 규칙** — 관측은 VISSIM 링크 키인데 모델은 storage 링크 키다. `link_to_origins`
   → `_storage_links_for_observed_origin` 경로로 접고, 대수 가중평균을 쓴다.
   단순평균이면 차 1대짜리 링크와 30대짜리 링크가 같은 무게를 갖는다.

2. **관측 없음 ≠ 속도 0** — VBS 의 링크속도는 `speed_sum / count` 라 표본이 없으면 0 이다.
   그 0 이 상태에 실리면 모델 쪽 하한(OBSERVED_SPEED_DELAY_CAP_RATIO)에 걸려
   지연이 자유류의 5배로 튄다. 표본 없는 링크는 **아예 기여하지 않아야** 한다.
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from evaluation.controllers import vissim_stackelberg_adapter as adapter


def _cfg() -> SimpleNamespace:
    network = SimpleNamespace(
        urban_link_storage_veh={"S1": 100.0, "S2": 100.0},
        off_ramp_storage_link={},
        urban_movements={},
        ramps=[],
        freeway_links=[],
        freeway_segments_per_link=0,
        freeway_segment_length_km=0.5,
        freeway_lanes=3.0,
        v_free=100.0,
    )
    return SimpleNamespace(network=network)


def _state_json() -> dict:
    return {
        "local_observation": {
            # L1/L2 -> S1 (표본 있음), L3 -> S2 (count 0), L4 -> S2 (속도 키 없음)
            "link_counts": {"L1": 10, "L2": 30, "L3": 0, "L4": 5},
            "link_speeds_kph": {"L1": 30, "L2": 10, "L3": 0},
        }
    }


def _mapping() -> dict:
    return {
        "link_to_origins": {"L1": ["S1"], "L2": ["S1"], "L3": ["S2"], "L4": ["S2"]},
        "link_to_movements": {},
    }


class StubTrafficState:
    """`traffic_state_from_vissim` 이 주입받는 TrafficState 자리의 최소 대역."""

    def __init__(self) -> None:
        self.time_sec = 0.0
        self.freeway_density: dict = {}
        self.freeway_speed: dict = {}
        self.freeway_flow: dict = {}
        self.freeway_effective_lanes: dict = {}
        self.ramp_queue: dict = {}
        self.boundary_queue: dict = {}
        self.urban_movement_queue: dict = {}
        self.urban_link_storage = {"S1": 100.0, "S2": 100.0}
        self.urban_link_speed_kph: dict = {}

    @classmethod
    def initial(cls, cfg) -> "StubTrafficState":  # noqa: ANN001
        return cls()

    def ensure_freeway_lane_profile(self, net) -> None:  # noqa: ANN001
        return None


class LegacyStubTrafficState(StubTrafficState):
    """관측 속도 필드가 없는 구 스냅샷(vendor/NumSim-mine) 대역."""

    def __init__(self) -> None:
        super().__init__()
        del self.urban_link_speed_kph


class ObservedLinkSpeedProjectionTests(unittest.TestCase):
    def test_summary_folds_observed_speeds_onto_storage_links(self) -> None:
        """대수 가중평균으로 접는다 — (10×30 + 30×10)/40 = 15.0."""
        summary = adapter.build_local_observation_summary(
            _state_json(), _cfg(), _mapping(), None
        )
        observed = summary.get("urban_link_speed_kph")
        self.assertIsNotNone(observed, "summary 에 urban_link_speed_kph 가 없다")
        self.assertAlmostEqual(observed["S1"], 15.0)
        # 단순평균이면 20.0 이다 — 가중이 실제로 걸렸는지 구분한다.
        self.assertNotAlmostEqual(observed["S1"], 20.0)

    def test_unsampled_link_contributes_no_zero_speed(self) -> None:
        """count=0(L3) 도 속도 키 없음(L4) 도 표본이 아니다 — S2 는 항목 자체가 없어야 한다."""
        summary = adapter.build_local_observation_summary(
            _state_json(), _cfg(), _mapping(), None
        )
        self.assertNotIn(
            "S2",
            summary["urban_link_speed_kph"],
            "표본 없는 링크가 0 km/h 로 실렸다 - 지연이 자유류의 5배로 튄다",
        )

    def test_traffic_state_receives_observed_link_speed(self) -> None:
        """상태 반영 — 어댑터가 만든 관측 속도가 TrafficState 에 실린다."""
        state = adapter.traffic_state_from_vissim(
            _state_json(),
            _cfg(),
            StubTrafficState,
            detector_mapping=_mapping(),
            calibration=None,
        )
        self.assertAlmostEqual(state.urban_link_speed_kph["S1"], 15.0)
        self.assertNotIn("S2", state.urban_link_speed_kph)

    def test_legacy_state_without_the_field_still_builds(self) -> None:
        """되돌림 안전장치 — 필드가 없는 구 스냅샷에서도 예외 없이 상태가 만들어진다.

        실런 기본 repo root 가 `vendor/NumSim-mine`(해시고정 스냅샷)이라 이 경로가 실제로 돈다.
        """
        state = adapter.traffic_state_from_vissim(
            _state_json(),
            _cfg(),
            LegacyStubTrafficState,
            detector_mapping=_mapping(),
            calibration=None,
        )
        self.assertFalse(hasattr(state, "urban_link_speed_kph"))


if __name__ == "__main__":
    unittest.main()
