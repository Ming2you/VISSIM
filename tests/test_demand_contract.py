# state.demand 의 러너(VBS)-어댑터 규약을 실 산출물로 강제하는 계약 검사
"""`evaluation/controllers/demand_contract.md` 의 실행 가능한 형태.

두 부류가 들어 있다.

- `DemandContractInvariantTests` — 지금 성립하는 규약. 깨지면 회귀다.
- `DemandContractKnownMismatchTests` — 지금 **깨져 있는** 규약. 일부러 FAIL 한다.
  xfail 로 감추지 않는다. 계약 문서의 "알려진 불일치" 절과 1:1 대응한다.

문자열 대조가 아니라 **생산자·소비자 양쪽에서 단위를 계산해** 비교한다.
생산자 쪽은 `LoadInpxDemandSchedule`(vbs) 의 산식(분류 -> 게이트 조인 -> 구간별 합)을
그대로 옮기고, 소비자 쪽은 어댑터의 `profiled_demand_rates` 를 실제로 호출한다.
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
GATE_MAP_CSV = REPO / "evaluation/real_world_modi_inventory/urban_input_gate_map_20260811.csv"
TUNING_JSON = REPO / "evaluation/configs/real_world_modi_pstack_distributed_core15n41_20260805.json"
CALIBRATION_JSON = REPO / "evaluation/calibration/real_world_prediction_calibration_pshb4500fix_20260724.json"
RUNNER_VBS = REPO / "scripts/run_real_world_stackelberg_controller.vbs"

# run_real_world_stackelberg_controller.vbs:125 — RW_FREEWAY_INPUT_LINKS.
FREEWAY_INPUT_LINKS = frozenset({26, 74})

# 러너가 state.demand 에 쓰는 필드 집합 (vbs:2123).
PRODUCER_DEMAND_FIELDS = frozenset(
    {
        "urban_volume_vph",
        "urban_volume_vph_by_gate",
        "urban_unmapped_volume_vph",
        "urban_internal_volume_vph",
        "freeway_volume_vph",
        "ramp_volume_vph",
        "demand_profile",
    }
)

# 대장. demand_contract.md 와 같은 값이어야 한다. 값이 바뀌면 (격자 재정렬이든 유입
# 재구성이든) 대장 검사가 먼저 FAIL 해서 문서를 갱신하게 만든다.
KNOWN_URBAN_GATE_COUNT = 117  # cfg.network.boundary_in_links
KNOWN_URBAN_INPUT_POINT_COUNT = 32  # VISSIM 도시부 vehicle input (dummy 10 포함)
KNOWN_URBAN_ENTRY_COUNT = 22  # 그중 진짜 망 입구 (dummy 제외)
KNOWN_URBAN_INTERNAL_COUNT = 10  # Dummy Link — 내부 발생 (사용자 확정)
KNOWN_URBAN_MAPPED_COUNT = 19  # 대장에서 게이트가 붙은 입구
KNOWN_UNMAPPED_STATUS_COUNT = {"leg_absent_at_node": 2, "leg_occupied_by_grid_neighbour": 1}


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
def _gate_map() -> dict[str, dict[str, str]]:
    """유입번호 -> 대장 행. 러너의 `LoadUrbanInputGateMap` 과 같은 파일을 읽는다."""
    rows: dict[str, dict[str, str]] = {}
    lines = [
        line
        for line in GATE_MAP_CSV.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    for row in csv.DictReader(lines):
        rows[str(row["no"]).strip()] = {k: (v or "").strip() for k, v in row.items()}
    return rows


@lru_cache(maxsize=1)
def _plant_demand_by_interval() -> dict[int, dict]:
    """`LoadInpxDemandSchedule`(vbs) 의 집계를 그대로 재현한다.

    구간 시작초 -> {urban_sum, urban_n, freeway_sum, freeway_n, by_gate, unmapped,
    internal, by_input}.
    scale·profile 배수는 실 런에서 1.0 이라 생략한다(run_manifest: demand_scale=1,
    demand_profile=None). 배수는 sum 과 mean 에 같은 비율로 걸리므로 배율에 무관하다.
    """
    roles = _vehicle_input_roles()
    gate_map = _gate_map()
    by_sec: dict[int, dict] = {}
    root = ET.parse(NETWORK_INPX).getroot()
    for node in root.iter("vehicleInput"):
        input_no = str(node.get("no"))
        role_key = roles.get(input_no, "").strip().lower()
        link_no = _first_int(node.get("link", ""))
        is_freeway = role_key.startswith("freeway") or link_no in FREEWAY_INPUT_LINKS
        prefix = "freeway" if is_freeway else "urban"
        entry = gate_map.get(input_no, {})
        for volume_node in node.iter("timeIntervalVehVolume"):
            # vbs:2982 TimeIntStartSec — "<set>-<index> <start_ms>" 의 마지막 토큰이 ms.
            start_sec = int(float(str(volume_node.get("timeInt", "0")).split(" ")[-1]) / 1000.0)
            bucket = by_sec.setdefault(
                start_sec,
                {
                    "urban_sum": 0.0,
                    "urban_n": 0.0,
                    "freeway_sum": 0.0,
                    "freeway_n": 0.0,
                    "by_gate": {},
                    "by_input": {},
                    "unmapped": 0.0,
                    "internal": 0.0,
                },
            )
            volume = float(volume_node.get("volume", "0"))
            bucket[f"{prefix}_sum"] += volume
            bucket[f"{prefix}_n"] += 1.0
            if is_freeway:
                continue
            bucket["by_input"][input_no] = volume
            status = entry.get("status", "")
            if status == "mapped":
                gate = entry["gate"]
                bucket["by_gate"][gate] = bucket["by_gate"].get(gate, 0.0) + volume
            elif status == "internal":
                bucket["internal"] += volume
            else:
                bucket["unmapped"] += volume
    return by_sec


@lru_cache(maxsize=1)
def _live_cfg():
    return _build_cfg()


def _build_cfg():
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


def _state_demand(start_sec: int) -> dict:
    """러너가 그 구간에 쓸 state.demand 를 생산자 산식대로 만든다."""
    plant = _plant_demand_by_interval()[start_sec]
    return {
        # vbs — 지점당 평균. 실 망에서는 게이트 앵커링이 쓰이므로 폴백 값으로만 남는다.
        "urban_volume_vph": plant["urban_sum"] / plant["urban_n"],
        "urban_volume_vph_by_gate": dict(plant["by_gate"]),
        "urban_unmapped_volume_vph": plant["unmapped"],
        "urban_internal_volume_vph": plant["internal"],
        "freeway_volume_vph": plant["freeway_sum"] / plant["freeway_n"],
        # vbs:2123 — 실 러너가 쓰는 리터럴.
        "ramp_volume_vph": 0,
        "demand_profile": "real_world_inpx_time_profile",
    }


def _consumer_rates(start_sec: int, cfg_pair=None):
    """러너가 그 구간에 쓸 state.demand 로 어댑터를 실제 호출한다."""
    cfg, calibration = cfg_pair if cfg_pair is not None else _live_cfg()
    state_json = {"sim_sec": float(start_sec), "demand": _state_demand(start_sec)}
    freeway, urban, ramp, profile = adapter.profiled_demand_rates(
        state_json, cfg, calibration, {}
    )
    return cfg, freeway, urban, ramp, profile


class DemandContractInvariantTests(unittest.TestCase):
    """지금 성립하는 규약. 이 검사가 FAIL 하면 회귀다."""

    def test_producer_emits_exactly_the_contract_fields(self) -> None:
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

    def test_each_gate_carries_its_own_vissim_input_volume(self) -> None:
        """앵커링의 본체 — 게이트값 == 그 게이트에 붙은 VISSIM 유입의 유량.

        스칼라 복제였을 때는 (합, 개수)만 맞으면 통과했다. 지점별로 대조한다.
        """
        gate_map = _gate_map()
        for start_sec in sorted(_plant_demand_by_interval()):
            with self.subTest(start_sec=start_sec):
                _cfg, _freeway, urban, _ramp, _profile = _consumer_rates(start_sec)
                plant = _plant_demand_by_interval()[start_sec]
                mapped = {
                    no: row for no, row in gate_map.items() if row["status"] == "mapped"
                }
                self.assertEqual(KNOWN_URBAN_MAPPED_COUNT, len(mapped))
                for no, row in mapped.items():
                    self.assertAlmostEqual(
                        plant["by_input"][no],
                        urban[row["gate"]],
                        places=6,
                        msg=f"유입 {no} ({row['name']}) -> {row['gate']}",
                    )

    def test_gates_without_a_vissim_input_get_zero(self) -> None:
        """유입이 없는 게이트는 0 이다. 유령 게이트가 수요를 만들어내지 않는다."""
        _cfg, _freeway, urban, _ramp, _profile = _consumer_rates(1800)
        plant = _plant_demand_by_interval()[1800]
        fed = set(plant["by_gate"])
        idle = [gate for gate in urban if gate not in fed]
        self.assertEqual(len(urban) - len(fed), len(idle))
        self.assertEqual({0.0}, {urban[gate] for gate in idle})

    def test_boundary_out_entries_are_populated_and_carry_zero(self) -> None:
        """boundary_out 은 키만 유지하고 값은 0 이다.

        주입에는 안 쓰이지만 `stackelberg_mpc._forecast_demand_metadata`(:2237-2246)
        가 전 키를 합산한다. 스칼라 복제 시절에는 그 진단값이 (117+119)/117 = 2.0171 배
        부풀었다. 게이트 앵커링 뒤에는 진단 합 == 주입 합이다.
        """
        cfg, _freeway, urban, _ramp, _profile = _consumer_rates(1800)
        for link in cfg.network.boundary_out_links:
            self.assertIn(str(link), urban)
            self.assertEqual(0.0, urban[str(link)])
        injected = sum(urban[str(link)] for link in cfg.network.boundary_in_links)
        logged = sum(urban.values())
        self.assertAlmostEqual(logged, injected, places=9)

    def test_unknown_gate_key_in_state_is_rejected(self) -> None:
        """모델이 모르는 게이트 이름이 오면 조용히 흘리지 않고 런을 세운다.

        대장과 격자가 따로 갱신되면 질량이 말없이 사라진다 — 3.66배와 같은 종류다.
        """
        cfg, calibration = _live_cfg()
        demand = _state_demand(1800)
        demand["urban_volume_vph_by_gate"] = dict(demand["urban_volume_vph_by_gate"])
        demand["urban_volume_vph_by_gate"]["in_SC_NOT_A_GATE"] = 123.0
        with self.assertRaises(ValueError) as ctx:
            adapter.profiled_demand_rates(
                {"sim_sec": 1800.0, "demand": demand}, cfg, calibration, {}
            )
        self.assertIn("in_SC_NOT_A_GATE", str(ctx.exception))

    def test_scalar_only_state_still_uses_the_point_mean_fallback(self) -> None:
        """8seg 러너·g6 harness 는 여전히 스칼라를 준다. 그 경로를 깨지 않는다."""
        cfg, calibration = _live_cfg()
        state_json = {
            "sim_sec": 1800.0,
            "demand": {"urban_volume_vph": 100.0, "freeway_volume_vph": 1000.0,
                       "ramp_volume_vph": 0, "demand_profile": "real_world_inpx_time_profile"},
        }
        _freeway, urban, _ramp, _profile = adapter.profiled_demand_rates(
            state_json, cfg, calibration, {}
        )
        self.assertEqual({100.0}, set(urban.values()))

    def test_ramp_volume_vph_zero_yields_zero_ramp_arrival_in_live_run(self) -> None:
        """실 런 캘리브레이션에는 램프 도착 예측이 없어 0 이 그대로 남는다."""
        _cfg, calibration = _live_cfg()
        prediction = calibration.get("prediction", {})
        self.assertNotIn("onramp_route_forecast", prediction)
        self.assertNotIn("local_ramp_arrival_forecast", prediction)
        cfg, _freeway, _urban, ramp, _profile = _consumer_rates(1800)
        self.assertEqual(sorted(ramp), sorted(map(str, cfg.network.ramps)))
        self.assertEqual({0.0}, set(ramp.values()))

    def test_producer_accounting_closes(self) -> None:
        """게이트 합 + 미배정 + 내부발생 == VISSIM 도시부 총량. 새는 곳이 없다."""
        for start_sec in sorted(_plant_demand_by_interval()):
            with self.subTest(start_sec=start_sec):
                plant = _plant_demand_by_interval()[start_sec]
                self.assertAlmostEqual(
                    plant["urban_sum"],
                    sum(plant["by_gate"].values()) + plant["unmapped"] + plant["internal"],
                    places=6,
                )

    def test_gate_anchoring_conserves_entry_demand_on_a_complete_grid(self) -> None:
        """격자가 입구 22개를 전부 갖고 있다면 총량이 정확히 보존된다.

        지금 격자에 없는 3곳(`in_SC1004_SW`, `in_SC1004_SE`, `in_SC13_S`)을 **가정으로만**
        추가해서 앵커링 기구 자체가 질량을 보존하는지 본다. 격자를 실제로 어떻게 고칠지는
        (신설이냐 병합이냐) 이 검사의 소관이 아니다. 몇 곳이 비어 있는지는 대장 검사
        (`test_known_ledger_matches_measurement`)가 지킨다 — 여기서 또 세지 않는다.
        격자가 완성되면 가정 집합이 비고 이 검사는 그대로 보존을 확인한다.
        """
        cfg, calibration = _build_cfg()
        gate_map = _gate_map()
        hypothetical = {
            no: f"in_{row['model_node']}_{row['leg']}"
            for no, row in gate_map.items()
            if row["status"] not in {"mapped", "internal", "freeway_excluded"}
        }
        cfg.network.boundary_in_links = list(cfg.network.boundary_in_links) + sorted(
            set(hypothetical.values())
        )
        for start_sec in sorted(_plant_demand_by_interval()):
            with self.subTest(start_sec=start_sec):
                plant = _plant_demand_by_interval()[start_sec]
                demand = _state_demand(start_sec)
                by_gate = dict(demand["urban_volume_vph_by_gate"])
                entry_total = sum(by_gate.values()) + plant["unmapped"]
                for no, gate in hypothetical.items():
                    by_gate[gate] = by_gate.get(gate, 0.0) + plant["by_input"][no]
                demand["urban_volume_vph_by_gate"] = by_gate
                demand["urban_unmapped_volume_vph"] = 0.0
                _freeway, urban, _ramp, _profile = adapter.profiled_demand_rates(
                    {"sim_sec": float(start_sec), "demand": demand}, cfg, calibration, {}
                )
                injected = sum(urban[str(link)] for link in cfg.network.boundary_in_links)
                self.assertAlmostEqual(entry_total, injected, places=6)

    def test_known_ledger_matches_measurement(self) -> None:
        """대장(문서)과 실측이 어긋나면 먼저 여기서 잡힌다."""
        cfg, _calibration = _live_cfg()
        plant = _plant_demand_by_interval()[1800]
        gate_map = _gate_map()
        self.assertEqual(KNOWN_URBAN_GATE_COUNT, len(cfg.network.boundary_in_links))
        self.assertEqual(KNOWN_URBAN_INPUT_POINT_COUNT, int(plant["urban_n"]))
        status_counts: dict[str, int] = {}
        for row in gate_map.values():
            status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1
        self.assertEqual(KNOWN_URBAN_MAPPED_COUNT, status_counts.get("mapped"))
        self.assertEqual(KNOWN_URBAN_INTERNAL_COUNT, status_counts.get("internal"))
        self.assertEqual(
            KNOWN_URBAN_ENTRY_COUNT,
            KNOWN_URBAN_INPUT_POINT_COUNT - KNOWN_URBAN_INTERNAL_COUNT,
        )
        for status, count in KNOWN_UNMAPPED_STATUS_COUNT.items():
            self.assertEqual(count, status_counts.get(status), status)
        # 대장 행이 실제 vehicle input 전수와 1:1 인가.
        self.assertEqual(set(_vehicle_input_roles()), set(gate_map))

    def test_gate_map_gates_exist_in_the_model_grid(self) -> None:
        """대장이 가리키는 게이트는 전부 모델 격자에 있어야 한다."""
        cfg, _calibration = _live_cfg()
        boundary_in = set(map(str, cfg.network.boundary_in_links))
        gates = [row["gate"] for row in _gate_map().values() if row["status"] == "mapped"]
        self.assertEqual(len(gates), len(set(gates)), "한 게이트에 유입이 둘 붙으면 안 된다")
        self.assertEqual(set(), set(gates) - boundary_in)


class DemandContractKnownMismatchTests(unittest.TestCase):
    """지금 깨져 있는 규약. FAIL 이 정상이다 — demand_contract.md §4 참조.

    남은 것은 **격자에 없는 입구 3곳**뿐이다. 게이트 신설 2 + leg 병합 1 은 격자
    재생성(생성기)의 몫이라 이 회차 범위 밖이다.
    """

    def test_every_vissim_urban_entry_has_a_model_gate(self) -> None:
        gate_map = _gate_map()
        missing = {
            no: row
            for no, row in gate_map.items()
            if row["status"] not in {"mapped", "internal", "freeway_excluded"}
        }
        self.assertEqual(
            {},
            missing,
            "KNOWN MISMATCH: 격자에 없는 입구 "
            + ", ".join(
                f"{no}({row['model_node']}_{row['leg']}, {row['status']}, "
                f"peak {float(row['peak_volume_vph']):,.0f} veh/h)"
                for no, row in sorted(missing.items())
            )
            + ". demand_contract.md §4.",
        )

    def test_urban_boundary_total_equals_plant_entry_total_each_interval(self) -> None:
        for start_sec in sorted(_plant_demand_by_interval()):
            with self.subTest(start_sec=start_sec):
                cfg, _freeway, urban, _ramp, _profile = _consumer_rates(start_sec)
                plant = _plant_demand_by_interval()[start_sec]
                entry_total = sum(plant["by_gate"].values()) + plant["unmapped"]
                injected = sum(urban[str(link)] for link in cfg.network.boundary_in_links)
                self.assertAlmostEqual(
                    entry_total,
                    injected,
                    delta=max(1.0, entry_total * 0.01),
                    msg=(
                        f"KNOWN MISMATCH @t={start_sec}s: 모델 주입 {injected:,.1f} veh/h vs "
                        f"플랜트 입구 {entry_total:,.1f} veh/h "
                        f"({injected / entry_total:.4f}배). 차액 {plant['unmapped']:,.1f} veh/h "
                        "는 격자에 게이트가 없는 입구 3곳이다. demand_contract.md §4."
                    ),
                )


if __name__ == "__main__":
    unittest.main()
