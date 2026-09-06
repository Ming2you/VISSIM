# -*- coding: utf-8 -*-
"""실런 `main()` 의 설치 순서를 **빠짐없이** 복제하는 오프라인 하네스.

`probe_far_components_20260901.build_cfg_and_state` 는 cfg 레벨 설치 일부만 한다 —
2026-09-04 에 대조한 결과 롤아웃에 닿는 것 넷이 빠져 있었다.

    apply_nonexistent_movement_beta_zero        beta 재배분
    install_boundary_out_ramp_split             경계 out 램프행 분할
    install_monitor_fixed_signal_runtime_patch  **green -> 유량 변환 자체**
    install_local_observation_runtime_guards    agent 마스킹

특히 셋째는 `_phase_green_fraction` 을 모듈 5개에 갈아끼운다. 그게 없으면 오프라인
측정이 vendor 원본 green 변환을 쓰게 되어 **실런과 다른 plant** 를 재게 된다.

순서는 어댑터 main() (9490~9560행) 그대로다. 바꾸지 마라 — 주석이 이유를 적어 두었다.
"""
import json
from pathlib import Path

R = Path(__file__).resolve().parent.parent
DEFAULT_CAL = "evaluation/calibration/real_world_prediction_calibration_core17legs4b_20260820.json"


def build(qb, TrafficState, tuning_path, state_path, prev_action_path):
    state_json = json.loads(Path(state_path).read_text(encoding="utf-8"))
    calibration = qb.load_optional_json(str(R / DEFAULT_CAL))
    tuning = qb.load_optional_json(str(tuning_path))
    qb.install_config_switches(tuning)
    dm_path = str(tuning.get("detector_mapping_json", "") or "").strip()
    if dm_path and not Path(dm_path).is_absolute():
        dm_path = str(R / dm_path)
    detector_mapping = qb.load_optional_json(dm_path)
    if not detector_mapping:
        raise SystemExit("detector mapping unreadable: %r" % dm_path)
    detector_mapping, _ = qb.filter_midblock_links_from_detector_mapping(detector_mapping, tuning)
    override = tuning.get("calibration_override", {})
    if isinstance(override, dict):
        calibration = qb.deep_update(dict(calibration), override)
    control_interval = float(state_json.get("control_interval_sec", 150.0))
    sim_period = float(state_json.get("sim_period_sec", 5400.0))
    local_observation = bool(
        qb._link_counts_from_local_observation(state_json) and detector_mapping)
    cfg = qb.build_config(R / "vendor/NumSim-mine", control_interval, sim_period, "fast-smoke",
                          calibration, tuning, local_observation=local_observation, flagship=True)
    m = {}
    m.update(qb.install_adapter_calibration_fingerprints(cfg, tuning))
    m.update(qb.install_vissim_calibration_runtime_patches(cfg, calibration))
    m.update(qb.install_tau_length_cap_patch(cfg))
    m.update(qb.apply_movement_phase_correction(cfg, tuning))
    m.update(qb.apply_nonexistent_movement_beta_zero(cfg, tuning))          # <- 추가
    m.update(qb.apply_dead_phase_beta_zero(cfg))
    m.update(qb.install_vsl_metanet_rollout_runtime_patch(cfg, tuning))
    m.update(qb.install_urban_stopline_storage(cfg, tuning))
    m.update(qb.install_measured_turn_beta(cfg, tuning))
    m.update(qb._relabel(qb.apply_dead_phase_beta_zero(cfg), "after_measured_beta"))
    m.update(qb.install_leg_ramp_split_fold(cfg, tuning))
    detector_mapping, _mm = qb.install_merged_movements(cfg, tuning, detector_mapping)
    m.update(_mm)
    m.update(qb.install_phase_vector_green_patch(cfg, tuning))
    m.update(qb.install_movement_capacity_by_lanes(cfg, tuning))
    m.update(qb.install_gate_onramp_queue(cfg, tuning))
    m.update(qb.install_offramp_direct_landing(cfg, tuning))
    m.update(qb.install_offramp_landing_runtime(cfg))
    m.update(qb.install_landing_storage(cfg, tuning))
    m.update(qb.install_landing_storage_runtime(cfg))
    m.update(qb.install_native_signal_structure(cfg, tuning))
    m.update(qb.install_measured_movement_capacity(cfg, tuning, state_json, prev_action_path))
    m.update(qb.install_measured_far_reservoir_rates(cfg, tuning, state_json, prev_action_path))
    m.update(qb.install_observed_backpressure_price(cfg, tuning, state_json, prev_action_path))
    m.update(qb.install_far_ramp_capacity_patch(cfg))
    m.update(qb.install_boundary_out_ramp_split(cfg, tuning))               # <- 추가
    m.update(qb.install_leg_ramp_split_runtime(cfg))
    state = qb.traffic_state_from_vissim(state_json, cfg, TrafficState, detector_mapping,
                                         calibration, physical_projection_input=None)
    m.update(qb.install_monitor_fixed_signal_runtime_patch(                 # <- 추가 (핵심)
        cfg, state_json, detector_mapping) or {})
    if local_observation:
        qb.install_local_observation_runtime_guards()                       # <- 추가
    m["_local_observation"] = float(local_observation)
    return cfg, state, state_json, m, detector_mapping, calibration, tuning
