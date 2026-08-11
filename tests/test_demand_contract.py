# state.demand 의 러너(VBS)-어댑터 규약을 실 산출물로 강제하는 계약 검사
"""`evaluation/controllers/demand_contract.md` 의 실행 가능한 형태.

두 부류가 들어 있다.

- `DemandContractInvariantTests` — 지금 성립하는 규약. 깨지면 회귀다.
- `DemandContractKnownMismatchTests` — 지금 **깨져 있는** 규약. 일부러 FAIL 한다.
  xfail 로 감추지 않는다. 계약 문서의 "알려진 불일치" 절과 1:1 대응한다.

문자열 대조가 아니라 **생산자·소비자 양쪽에서 단위를 계산해** 비교한다.
생산자 쪽은 `LoadInpxDemandSchedule`(vbs:2926-2954) 의 산식을 그대로 옮기고,
소비자 쪽은 어댑터의 `profiled_demand_rates` 를 실제로 호출한다.
"""

from __future__ import annotations

import csv
import re
import sys
import unittest
import xml.etree.ElementTree as ET
from functools import lru_cache
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
VENDOR = REPO / "vendor" / "NumSim-mine"
for _path in (str(REPO), str(VENDOR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from evaluation.controllers import vissim_stackelberg_adapter as adapter  # noqa: E402

# 실 15-SC 런이 쓰는 산출물. 출처는 봉인된 run_manifest_v2_1.json
# (evaluation/runs/n1_final_20260807/.../attempt_01_*/run_manifest_v2_1.json).
NETWORK_INPX = REPO / "network/real_world_gaepo_modi/modi_eval_rw_control.inpx"
ROLES_CSV = REPO / "evaluation/real_world_modi_inventory/vehicle_input_roles.csv"
TUNING_JSON = REPO / "evaluation/configs/real_world_modi_pstack_distributed_core15n41_20260805.json"
CALIBRATION_JSON = REPO / "evaluation/calibration/real_world_prediction_calibration_pshb4500fix_20260724.json"
RUNNER_VBS = REPO / "scripts/run_real_world_stackelberg_controller.vbs"

# run_real_world_stackelberg_controller.vbs:125 — RW_FREEWAY_INPUT_LINKS.
FREEWAY_INPUT_LINKS = frozenset({26, 74})

# 러너가 state.demand 에 쓰는 필드 집합 (vbs:2123).
PRODUCER_DEMAND_FIELDS = frozenset(
    {"urban_volume_vph", "freeway_volume_vph", "ramp_volume_vph", "demand_profile"}
)

# 알려진 불일치 대장. demand_contract.md "알려진 불일치" 절과 같은 값이어야 한다.
# 값이 바뀌면 (격자 재정렬이든 유입 재구성이든) 아래 대장 검사가 먼저 FAIL 해서
# 문서를 갱신하게 만든다.
KNOWN_URBAN_GATE_COUNT = 117
KNOWN_URBAN_INPUT_POINT_COUNT = 32
KNOWN_URBAN_INFLATION = KNOWN_URBAN_GATE_COUNT / KNOWN_URBAN_INPUT_POINT_COUNT  # 3.65625


def _first_int(text: str) -> int:
    """vbs:4274 `FirstInt` — 첫 정수(앞의 '-' 포함)를 뽑는다."""
    match = re.search(r"-?\d+", str(text))
    return int(match.group()) if match else 0


@lru_cache(maxsize=1)
def _vehicle_input_roles() -> dict[str, str]:
    roles: dict[str, str] = {}
    with ROLES_CSV.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            roles[str(row["no"]).strip()] = str(row["role"]).strip()
    return roles


@lru_cache(maxsize=1)
def _plant_demand_by_interval() -> dict[int, dict[str, float]]:
    """`LoadInpxDemandSchedule`(vbs:2926-2954) 의 집계를 그대로 재현한다.

    구간 시작초 -> {urban_sum, urban_n, freeway_sum, freeway_n}.
    scale·profile 배수는 실 런에서 1.0 이라 생략한다(run_manifest: demand_scale=1,
    demand_profile=None). 배수는 sum 과 mean 에 같은 비율로 걸리므로 배율에 무관하다.
    """
    roles = _vehicle_input_roles()
    by_sec: dict[int, dict[str, float]] = {}
    root = ET.parse(NETWORK_INPX).getroot()
    for node in root.iter("vehicleInput"):
        role_key = roles.get(str(node.get("no")), "").strip().lower()
        link_no = _first_int(node.get("link", ""))
        is_freeway = role_key.startswith("freeway") or link_no in FREEWAY_INPUT_LINKS
        prefix = "freeway" if is_freeway else "urban"
        for volume_node in node.iter("timeIntervalVehVolume"):
            # vbs:2982 TimeIntStartSec — "<set>-<index> <start_ms>" 의 마지막 토큰이 ms.
            start_sec = int(float(str(volume_node.get("timeInt", "0")).split(" ")[-1]) / 1000.0)
            bucket = by_sec.setdefault(
                start_sec,
                {"urban_sum": 0.0, "urban_n": 0.0, "freeway_sum": 0.0, "freeway_n": 0.0},
            )
            bucket[f"{prefix}_sum"] += float(volume_node.get("volume", "0"))
            bucket[f"{prefix}_n"] += 1.0
    return by_sec


@lru_cache(maxsize=1)
def _live_cfg():
    calibration = adapter.load_optional_json(str(CALIBRATION_JSON))
    tuning = adapter.load_optional_json(str(TUNING_JSON))
    cfg = adapter.build_config(
        VENDOR,
        control_interval=60.0,
        sim_period=3600.0,
        mode="full",
        calibration=calibration,
        tuning=tuning,
        local_observation=True,
    )
    return cfg, calibration


def _consumer_rates(start_sec: int):
    """러너가 그 구간에 쓸 state.demand 로 어댑터를 실제 호출한다."""
    cfg, calibration = _live_cfg()
    plant = _plant_demand_by_interval()[start_sec]
    state_json = {
        "sim_sec": float(start_sec),
        "demand": {
            # vbs:2949-2953 — 지점당 평균.
            "urban_volume_vph": plant["urban_sum"] / plant["urban_n"],
            "freeway_volume_vph": plant["freeway_sum"] / plant["freeway_n"],
            # vbs:2123 — 실 러너가 쓰는 리터럴.
            "ramp_volume_vph": 0,
            "demand_profile": "real_world_inpx_time_profile",
        },
    }
    freeway, urban, ramp, profile = adapter.profiled_demand_rates(
        state_json, cfg, calibration, {}
    )
    return cfg, freeway, urban, ramp, profile


class DemandContractInvariantTests(unittest.TestCase):
    """지금 성립하는 규약. 이 검사가 FAIL 하면 회귀다."""

    def test_producer_emits_exactly_the_four_contract_fields(self) -> None:
        source = RUNNER_VBS.read_text(encoding="utf-8", errors="replace")
        emit_lines = [line for line in source.splitlines() if '""demand"": {' in line]
        self.assertEqual(1, len(emit_lines), "러너가 demand 블록을 쓰는 줄은 하나여야 한다")
        line = emit_lines[0]
        fields = set(re.findall(r'""([a-z_]+)"":', line.split("{", 1)[1]))
        self.assertEqual(PRODUCER_DEMAND_FIELDS, fields)
        self.assertRegex(
            line,
            r'""ramp_volume_vph"": 0',
            "실 러너는 ramp_volume_vph 를 리터럴 0 으로 쓴다 (계약 문서 3절)",
        )

    def test_freeway_volume_vph_is_point_mean_and_model_total_matches_plant(self) -> None:
        """고속부는 유입 지점 수(2) == 모델 링크 수(2) 라서 총량이 맞는다."""
        for start_sec in sorted(_plant_demand_by_interval()):
            with self.subTest(start_sec=start_sec):
                cfg, freeway, _urban, _ramp, _profile = _consumer_rates(start_sec)
                plant = _plant_demand_by_interval()[start_sec]
                self.assertEqual(len(cfg.network.freeway_links), int(plant["freeway_n"]))
                self.assertAlmostEqual(
                    sum(freeway[str(link)] for link in cfg.network.freeway_links),
                    plant["freeway_sum"],
                    places=6,
                )

    def test_urban_boundary_arrivals_read_boundary_in_gates_only(self) -> None:
        """boundary_out 값은 외생 도착으로 안 쓰인다 — movement 정의로 확인한다.

        모델의 모든 외생 도시부 도착은 `kind == "boundary_in"` 인 movement 의
        `origin` 에서만 온다(urban_queue_model.py:133-137, 1004-1009,
        distributed_coordinator.py:3229-3233, urban_follower.py:153-155,
        simplified_inflow_outflow_allocation.py:146-148,
        wu_faithful_follower.py:486-487, free_flow_reference.py:121-122).
        그 origin 집합이 boundary_in_links 와 정확히 같고 boundary_out_links 와
        겹치지 않으면, boundary_out 항목은 주입 경로가 없다.
        """
        cfg, _calibration = _live_cfg()
        boundary_in = set(map(str, cfg.network.boundary_in_links))
        boundary_out = set(map(str, cfg.network.boundary_out_links))
        origins = {
            str(spec.get("origin", ""))
            for spec in cfg.network.urban_movements.values()
            if str(spec.get("kind", "")) == "boundary_in"
        }
        self.assertEqual(origins, boundary_in)
        self.assertEqual(set(), boundary_in & boundary_out)
        self.assertEqual(set(), origins & boundary_out)

    def test_boundary_out_entries_are_populated_and_only_leak_into_diagnostics(self) -> None:
        """어댑터는 boundary_out 에도 값을 채운다(adapter:2814-2817).

        주입에는 안 쓰이지만 `stackelberg_mpc._forecast_demand_metadata`(:2237-2246)
        가 전 키를 합산하므로 `leader_forecast_boundary_*` 진단값만 부풀어 있다.
        """
        cfg, _freeway, urban, _ramp, _profile = _consumer_rates(1800)
        injected = sum(urban[str(link)] for link in cfg.network.boundary_in_links)
        logged = sum(urban.values())
        self.assertGreater(logged, injected)
        expected_ratio = (
            len(cfg.network.boundary_in_links) + len(cfg.network.boundary_out_links)
        ) / len(cfg.network.boundary_in_links)
        self.assertAlmostEqual(logged / injected, expected_ratio, places=9)

    def test_ramp_volume_vph_zero_yields_zero_ramp_arrival_in_live_run(self) -> None:
        """실 런 캘리브레이션에는 램프 도착 예측이 없어 0 이 그대로 남는다."""
        _cfg, calibration = _live_cfg()
        prediction = calibration.get("prediction", {})
        self.assertNotIn("onramp_route_forecast", prediction)
        self.assertNotIn("local_ramp_arrival_forecast", prediction)
        cfg, _freeway, _urban, ramp, _profile = _consumer_rates(1800)
        self.assertEqual(sorted(ramp), sorted(map(str, cfg.network.ramps)))
        self.assertEqual({0.0}, set(ramp.values()))

    def test_known_urban_mismatch_ledger_matches_measurement(self) -> None:
        """대장(문서)과 실측이 어긋나면 먼저 여기서 잡힌다."""
        cfg, _calibration = _live_cfg()
        plant = _plant_demand_by_interval()[1800]
        self.assertEqual(KNOWN_URBAN_GATE_COUNT, len(cfg.network.boundary_in_links))
        self.assertEqual(KNOWN_URBAN_INPUT_POINT_COUNT, int(plant["urban_n"]))


class DemandContractKnownMismatchTests(unittest.TestCase):
    """지금 깨져 있는 규약. FAIL 이 정상이다 — demand_contract.md §4 참조.

    3.66배 자체는 이번 회차에서 고치지 않는다(격자 재정렬과 함께 결정할 사안).
    이 검사는 어긋남을 드러내는 것이 목적이다.
    """

    def test_urban_gate_count_equals_vissim_urban_input_point_count(self) -> None:
        cfg, _calibration = _live_cfg()
        plant = _plant_demand_by_interval()[1800]
        gates = len(cfg.network.boundary_in_links)
        points = int(plant["urban_n"])
        self.assertEqual(
            points,
            gates,
            f"KNOWN MISMATCH: boundary_in 게이트 {gates}개 vs VISSIM 도시부 유입지점 "
            f"{points}개 -> 총량 {gates / points:.4f}배. "
            "러너는 지점당 평균을 주는데 어댑터는 게이트당 값으로 읽는다 "
            "(vbs:2949-2950 / adapter:2814-2817). demand_contract.md §4.",
        )

    def test_urban_boundary_total_equals_plant_total_each_interval(self) -> None:
        for start_sec in sorted(_plant_demand_by_interval()):
            with self.subTest(start_sec=start_sec):
                cfg, _freeway, urban, _ramp, _profile = _consumer_rates(start_sec)
                plant = _plant_demand_by_interval()[start_sec]
                injected = sum(urban[str(link)] for link in cfg.network.boundary_in_links)
                self.assertAlmostEqual(
                    plant["urban_sum"],
                    injected,
                    delta=max(1.0, plant["urban_sum"] * 0.01),
                    msg=(
                        f"KNOWN MISMATCH @t={start_sec}s: 모델 주입 {injected:,.1f} veh/h vs "
                        f"플랜트 {plant['urban_sum']:,.1f} veh/h "
                        f"({injected / plant['urban_sum']:.4f}배). demand_contract.md §4."
                    ),
                )


if __name__ == "__main__":
    unittest.main()
