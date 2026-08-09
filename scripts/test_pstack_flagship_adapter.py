# pstack-flagship 어댑터 이식 검증: 구성 전수 assert + MS_ADAPT 래치 단위검증 + 합성 state 스모크 + stackelberg 회귀.
"""실행 예:
    python scripts/test_pstack_flagship_adapter.py

NumSim 저장소는 NUMSIM_REPO_ROOT env 또는 어댑터 DEFAULT_REPO_ROOT(NumSim-mine)를 쓴다.
모든 테스트 PASS 시 종료코드 0, 실패 시 1.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Any, Mapping

WORKSPACE = Path(__file__).resolve().parents[1]
ADAPTER_DIR = WORKSPACE / "evaluation" / "controllers"
ADAPTER_PY = ADAPTER_DIR / "vissim_stackelberg_adapter.py"
FLAGSHIP_TUNING = WORKSPACE / "evaluation" / "configs" / "real_world_modi_pstack_flagship_20260731.json"

if str(ADAPTER_DIR) not in sys.path:
    sys.path.insert(0, str(ADAPTER_DIR))

import vissim_stackelberg_adapter as ada  # noqa: E402

REPO_ROOT = ada.DEFAULT_REPO_ROOT


def _check(condition: bool, message: str, failures: list[str]) -> None:
    if not condition:
        failures.append(message)


def _flagship_cfg_and_tuning():
    """main()과 같은 방식으로 flagship cfg를 구성한다(calibration_override 병합 포함)."""
    tuning = ada.load_optional_json(str(FLAGSHIP_TUNING))
    calibration = ada.load_optional_json(str(ada.DEFAULT_CALIBRATION))
    calibration_override = tuning.get("calibration_override", {})
    if isinstance(calibration_override, Mapping):
        calibration = ada.deep_update(dict(calibration), calibration_override)
    cfg = ada.build_config(
        REPO_ROOT,
        60.0,
        180.0,
        "fast-smoke",
        calibration,
        tuning,
        local_observation=False,
        flagship=True,
    )
    return cfg, tuning


def test_flagship_configuration() -> list[str]:
    """(1) 구성 검증: pstack-flagship 진입 후 controller/nash_solver/cfg 속성 전수 assert."""
    failures: list[str] = []
    cfg, tuning = _flagship_cfg_and_tuning()
    controller = ada.build_pstack_flagship_controller(cfg, tuning)
    try:
        mpc = cfg.mpc
        _check(type(controller).__name__ == "F1StackelbergWuMeteredController",
               f"controller 클래스: {type(controller).__name__}", failures)
        # 러너 build_cfg 원문(grid; plan.md의 continuous가 아님) + default.yaml 실효 예산.
        _check(str(mpc.leader_search_mode) == "grid", f"leader_search_mode={mpc.leader_search_mode}", failures)
        _check(bool(mpc.relaxed_quantized_controls), "relaxed_quantized_controls != True", failures)
        _check(int(mpc.leader_candidate_count) == 49, f"leader_candidate_count={mpc.leader_candidate_count}", failures)
        _check(int(mpc.max_nash_iter) == 10, f"max_nash_iter={mpc.max_nash_iter}", failures)
        _check(int(mpc.horizon_steps) == 3, f"horizon_steps={mpc.horizon_steps}", failures)
        _check(int(mpc.leader_value_depth) == 3, f"leader_value_depth={mpc.leader_value_depth}", failures)
        # NASH_SMAX 실효: env가 있으면 src의 s_max = max(1, int(env)) — 하드캡 min(iter,5) 해제.
        env_smax = os.environ.get("NASH_SMAX")
        _check(env_smax == "10", f"NASH_SMAX env={env_smax!r}", failures)
        effective_smax = max(1, int(env_smax)) if env_smax else max(1, min(int(mpc.max_nash_iter), 5))
        _check(effective_smax == 10, f"effective nash s_max={effective_smax}", failures)
        # seg13 박스 + box_walk + NP + far + bias_pow.
        _check(float(mpc.seg13_meter_box_veh_h) == 300.0, f"seg13_meter_box_veh_h={mpc.seg13_meter_box_veh_h}", failures)
        _check(float(mpc.seg13_vsl_box_kmh) == 20.0, f"seg13_vsl_box_kmh={mpc.seg13_vsl_box_kmh}", failures)
        _check(bool(mpc.leader_rollout_box_walk), "leader_rollout_box_walk != True", failures)
        _check(bool(mpc.leader_rollout_box_walk_vg), "leader_rollout_box_walk_vg != True", failures)
        _check(bool(mpc.baseline_move_box), "baseline_move_box != True", failures)
        _check(int(mpc.np_primal_dual_iters) == 4, f"np_primal_dual_iters={mpc.np_primal_dual_iters}", failures)
        _check(bool(mpc.np_bias_correction), "np_bias_correction != True", failures)
        _check(bool(mpc.leader_mfd_far_state_aware), "leader_mfd_far_state_aware != True", failures)
        _check(bool(mpc.leader_mfd_far_real_speed), "leader_mfd_far_real_speed != True", failures)
        _check(abs(float(mpc.leader_bias_sample_pow) - 0.4) < 1e-12,
               f"leader_bias_sample_pow={mpc.leader_bias_sample_pow}", failures)
        # OPT12 동적 속성(setattr 주입).
        _check(bool(getattr(mpc, "leader_skip_local_refinement", False)), "OPT1 leader_skip_local_refinement 미설정", failures)
        _check(bool(getattr(mpc, "leader_rollout_early_stop", False)), "OPT2 leader_rollout_early_stop 미설정", failures)
        # BIAS_SAMPLE 활성(러너 방식: _continuous_low_discrepancy_samples 몽키패치).
        _check(hasattr(controller, "_orig_low_discrepancy"), "enable_biased_sampling 미적용", failures)
        # follower smoothness.
        _check(float(cfg.freeway_follower.vsl_smoothness_weight) == 0.0,
               f"vsl_smoothness_weight={cfg.freeway_follower.vsl_smoothness_weight}", failures)
        # vissimdsd 체인의 VSL 메뉴(20 간격).
        _check([float(v) for v in cfg.freeway_follower.vsl_set] == [80.0, 100.0, 120.0],
               f"vsl_set={cfg.freeway_follower.vsl_set}", failures)
        # nash_solver 속성(SEG13, spillback 0, joint/offset, 가격 채널).
        nash = controller.nash_solver
        _check(bool(getattr(nash, "segment_agents", False)), "nash_solver.segment_agents != True", failures)
        _check(float(nash.f1_spillback_weight) == 0.0, f"f1_spillback_weight={nash.f1_spillback_weight}", failures)
        _check(bool(nash.joint_green_offset_enabled), "joint_green_offset_enabled != True", failures)
        _check(bool(nash.ramp_offset_enabled), "ramp_offset_enabled != True", failures)
        # 가격 4채널 ON + inner iters + cross 2종 OFF + δ/trust 짝 + hinge 기본 OFF.
        _check(bool(controller.signal_price_enabled), "signal_price_enabled != True", failures)
        _check(bool(controller.metering_price_enabled), "metering_price_enabled != True", failures)
        _check(bool(controller.vsl_price_enabled), "vsl_price_enabled != True", failures)
        _check(bool(controller.offset_price_enabled), "offset_price_enabled != True", failures)
        _check(int(controller.offset_price_inner_iters) == 4,
               f"offset_price_inner_iters={controller.offset_price_inner_iters}", failures)
        _check(not bool(controller.green_offset_cross_price_enabled), "green_offset_cross_price_enabled != False", failures)
        _check(not bool(controller.vsl_meter_cross_price_enabled), "vsl_meter_cross_price_enabled != False", failures)
        _check(float(controller.metering_price_delta_veh_h) == 300.0,
               f"metering_price_delta_veh_h={controller.metering_price_delta_veh_h}", failures)
        _check(abs(float(controller.metering_price_trust_frac) - 0.20) < 1e-12,
               f"metering_price_trust_frac={controller.metering_price_trust_frac}", failures)
        _check(not bool(getattr(controller, "price_hinge_enabled", False)), "price_hinge_enabled != False", failures)
    finally:
        if hasattr(controller, "close"):
            try:
                controller.close()
            except Exception:
                pass
    return failures


def test_ms_adapt_latch() -> list[str]:
    """(2) MS_ADAPT 래치 단위검증: 첫 스텝/미달/트리거/hold 만료/재트리거/다중 링크."""
    failures: list[str] = []
    update = ada.flagship_ms_adapt_update
    thr, hold, w = 10.0, 5, 0.013

    # 첫 스텝(prev 없음): dmax 0 → latch 0 → weight w (러너 초기 동작과 동일).
    dmax, latch, weight = update({}, {"FW_E": 20.0}, 0, thr, hold, w)
    _check((dmax, latch, weight) == (0.0, 0, w), f"첫 스텝: {(dmax, latch, weight)}", failures)

    # 문턱 미달: latch 유지 0, weight w.
    dmax, latch, weight = update({"FW_E": 20.0}, {"FW_E": 29.9}, 0, thr, hold, w)
    _check(abs(dmax - 9.9) < 1e-9 and latch == 0 and weight == w, f"미달: {(dmax, latch, weight)}", failures)

    # 트리거: dmax > thr → latch=hold, weight 0.
    dmax, latch, weight = update({"FW_E": 20.0}, {"FW_E": 31.0}, 0, thr, hold, w)
    _check(abs(dmax - 11.0) < 1e-9 and latch == hold and weight == 0.0, f"트리거: {(dmax, latch, weight)}", failures)

    # hold 만료: 트리거 후 무변화 5스텝 → latch 4,3,2,1,0 / weight 0,0,0,0,w.
    seq = []
    latch_run = hold
    for _ in range(5):
        _, latch_run, weight_run = update({"FW_E": 31.0}, {"FW_E": 31.0}, latch_run, thr, hold, w)
        seq.append((latch_run, weight_run))
    _check(seq == [(4, 0.0), (3, 0.0), (2, 0.0), (1, 0.0), (0, w)], f"hold 만료 시퀀스: {seq}", failures)

    # 재트리거: hold 중 재발 → latch가 hold로 리셋.
    _, latch_re, weight_re = update({"FW_E": 31.0}, {"FW_E": 45.0}, 3, thr, hold, w)
    _check(latch_re == hold and weight_re == 0.0, f"재트리거: {(latch_re, weight_re)}", failures)

    # 다중 링크: 링크별 |Δρ|의 최대값 사용.
    dmax, _, _ = update({"FW_E": 20.0, "FW_W": 40.0}, {"FW_E": 21.0, "FW_W": 20.0}, 0, thr, hold, w)
    _check(abs(dmax - 20.0) < 1e-9, f"다중 링크 dmax={dmax}", failures)

    # prev에 없는 링크는 무시(러너 L1109-1110의 `if lk in prev` 게이트).
    dmax, _, _ = update({"FW_E": 20.0}, {"FW_E": 20.0, "FW_W": 99.0}, 0, thr, hold, w)
    _check(dmax == 0.0, f"신규 링크 무시 dmax={dmax}", failures)
    return failures


def _make_state_json(sim_sec: float, count_per_seg: float, speed_kph: float) -> dict[str, Any]:
    """VBS WriteStateJson(run_real_world_stackelberg_controller.vbs L920-959) 스키마의 합성 state."""
    def rows() -> list[dict[str, float]]:
        return [
            {"count": float(count_per_seg), "speed_sum": float(count_per_seg) * float(speed_kph),
             "length_km": 1.0, "lanes": 4}
            for _ in range(8)
        ]

    return {
        "sim_sec": float(sim_sec),
        "sim_period_sec": 3600.0,
        "control_interval_sec": 60.0,
        "total_vehicles": 500,
        "urban_vehicles": 220,
        "freeway_vehicles": 230,
        "ramp_vehicles": 30,
        "boundary_vehicles": 20,
        "other_vehicles": 0,
        "mean_speed_kph": 45.0,
        "freeway_mean_speed_kph": float(speed_kph),
        "stopped_vehicles": 40,
        "demand": {
            "urban_volume_vph": 1200.0,
            "freeway_volume_vph": 3600.0,
            "ramp_volume_vph": 0,
            "demand_profile": "baseline",
        },
        "ramp_counts": {"D": 12, "F": 6},
        "freeway_segments": {"FW_E": rows(), "FW_W": rows()},
    }


def _run_adapter(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(ADAPTER_PY)] + args
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, errors="replace", timeout=1800)


def _smoke_tuning_dict() -> dict[str, Any]:
    """스모크 전용 저예산 tuning(flagship 체인 extends). 8-seg 별도 config 없이 임시 파일로 충분."""
    return {
        "extends": str(FLAGSHIP_TUNING),
        "name": "pstack_flagship_smoke_test",
        "config_overrides": {
            "mpc": {
                "horizon_steps": 1,
                "control_horizon_steps": 1,
                "leader_candidate_count": 3,
                "leader_refinement_candidate_count": 3,
                "max_nash_iter": 2,
                "leader_value_depth": 1,
            },
            "urban_follower": {
                "allocation_pso_particles": 4,
                "allocation_pso_iterations": 4,
            },
            "freeway_follower": {
                "horizon_beam_width": 1,
                "horizon_ramp_candidate_limit": 1,
                "horizon_vsl_candidate_limit_per_link": 1,
            },
        },
        "adapter": {
            "flagship": {
                "nash_smax": 2
            }
        },
    }


def test_flagship_smoke(tmp: Path) -> list[str]:
    """(3) 합성 state 스모크: pstack-flagship 결정 2회(사이드카 연속성 + MS 트리거 + fargate)."""
    failures: list[str] = []
    tuning_path = tmp / "smoke_tuning.json"
    tuning_path.write_text(json.dumps(_smoke_tuning_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    # 1회차: 저밀도(15 veh/km/lane, 85 kph) → fargate OFF → SUP_PFO 발화.
    state1 = tmp / "state1.json"
    state1.write_text(json.dumps(_make_state_json(300.0, count_per_seg=60.0, speed_kph=85.0)), encoding="utf-8")
    out1_json, out1_csv = tmp / "action1.json", tmp / "action1.csv"
    proc = _run_adapter([
        "--state-json", str(state1),
        "--out-action-json", str(out1_json),
        "--out-action-csv", str(out1_csv),
        "--controller", "pstack-flagship",
        "--tuning-json", str(tuning_path),
        "--repo-root", str(REPO_ROOT),
    ], cwd=tmp)
    if proc.returncode != 0:
        failures.append(f"1회차 returncode={proc.returncode}\nstdout={proc.stdout[-2000:]}\nstderr={proc.stderr[-2000:]}")
        return failures
    payload1 = json.loads(out1_json.read_text(encoding="utf-8"))
    meta1 = payload1.get("metadata", {})
    _check(meta1.get("controller_status") == "ok",
           f"1회차 controller_status={meta1.get('controller_status')} error={meta1.get('controller_error')}", failures)
    _check(meta1.get("controller") == "F1StackelbergWuMeteredController",
           f"1회차 controller={meta1.get('controller')}", failures)
    _check(float(meta1.get("flagship_runtime_first_step", -1.0)) == 1.0,
           f"1회차 flagship_runtime_first_step={meta1.get('flagship_runtime_first_step')}", failures)
    _check(float(meta1.get("flagship_fargate_on", -1.0)) == 0.0,
           f"1회차 flagship_fargate_on={meta1.get('flagship_fargate_on')}", failures)
    _check(abs(float(meta1.get("flagship_ms_friction", -1.0)) - 0.013) < 1e-12,
           f"1회차 flagship_ms_friction={meta1.get('flagship_ms_friction')}", failures)
    _check("flagship_sup_pick_pfo" in meta1, "1회차 sup_pick 미기록(감독자 미발화)", failures)
    _check(float(meta1.get("flagship_post_guard_pfo_baseline_forced_off", 0.0)) == 1.0,
           "post_guard PFO 기준선 기본 OFF 미적용", failures)
    for key in ("ramp_metering", "vsl", "green_times"):
        _check(bool(payload1.get(key)), f"1회차 action json에 {key} 없음", failures)
    _check(out1_csv.exists() and "ramp_meter" in out1_csv.read_text(encoding="utf-8"),
           "1회차 action csv에 ramp_meter 행 없음", failures)
    sidecar = tmp / ada.FLAGSHIP_RUNTIME_FILENAME
    _check(sidecar.exists(), "사이드카 미생성", failures)
    runtime1 = json.loads(sidecar.read_text(encoding="utf-8")) if sidecar.exists() else {}
    _check(bool(runtime1.get("ms_prev_rho")), f"사이드카 ms_prev_rho 비어 있음: {runtime1}", failures)
    _check(float(runtime1.get("sim_sec", -1.0)) == 300.0, f"사이드카 sim_sec={runtime1.get('sim_sec')}", failures)

    # 2회차: 고밀도(35 veh/km/lane, 30 kph) → |Δρ|=20 → MS 래치 5·마찰 0 + capdrop → fargate ON.
    state2 = tmp / "state2.json"
    state2.write_text(json.dumps(_make_state_json(360.0, count_per_seg=140.0, speed_kph=30.0)), encoding="utf-8")
    out2_json, out2_csv = tmp / "action2.json", tmp / "action2.csv"
    proc2 = _run_adapter([
        "--state-json", str(state2),
        "--previous-action-json", str(out1_json),
        "--out-action-json", str(out2_json),
        "--out-action-csv", str(out2_csv),
        "--controller", "pstack-flagship",
        "--tuning-json", str(tuning_path),
        "--repo-root", str(REPO_ROOT),
    ], cwd=tmp)
    if proc2.returncode != 0:
        failures.append(f"2회차 returncode={proc2.returncode}\nstdout={proc2.stdout[-2000:]}\nstderr={proc2.stderr[-2000:]}")
        return failures
    payload2 = json.loads(out2_json.read_text(encoding="utf-8"))
    meta2 = payload2.get("metadata", {})
    _check(meta2.get("controller_status") == "ok",
           f"2회차 controller_status={meta2.get('controller_status')} error={meta2.get('controller_error')}", failures)
    _check(float(meta2.get("flagship_runtime_first_step", -1.0)) == 0.0,
           f"2회차 flagship_runtime_first_step={meta2.get('flagship_runtime_first_step')}", failures)
    _check(float(meta2.get("flagship_ms_dmax", 0.0)) > 10.0,
           f"2회차 flagship_ms_dmax={meta2.get('flagship_ms_dmax')}", failures)
    _check(float(meta2.get("flagship_ms_latch", -1.0)) == 5.0,
           f"2회차 flagship_ms_latch={meta2.get('flagship_ms_latch')}", failures)
    _check(float(meta2.get("flagship_ms_friction", -1.0)) == 0.0,
           f"2회차 flagship_ms_friction={meta2.get('flagship_ms_friction')}", failures)
    _check(float(meta2.get("flagship_fargate_on", -1.0)) == 1.0,
           f"2회차 flagship_fargate_on={meta2.get('flagship_fargate_on')}", failures)
    _check(float(meta2.get("flagship_sup_gated_off", -1.0)) == 1.0,
           f"2회차 flagship_sup_gated_off={meta2.get('flagship_sup_gated_off')}", failures)
    runtime2 = json.loads(sidecar.read_text(encoding="utf-8"))
    _check(float(runtime2.get("sim_sec", -1.0)) == 360.0, f"2회차 사이드카 sim_sec={runtime2.get('sim_sec')}", failures)
    _check(int(runtime2.get("ms_latch", -1)) == 5, f"2회차 사이드카 ms_latch={runtime2.get('ms_latch')}", failures)
    _check(bool(runtime2.get("fargate_stress", False)), "2회차 사이드카 fargate_stress != True", failures)
    return failures


def test_stackelberg_regression(tmp: Path) -> list[str]:
    """(4) 회귀: 동일 state로 기존 stackelberg 모드 무오류(계약 보존)."""
    failures: list[str] = []
    state = tmp / "state_reg.json"
    state.write_text(json.dumps(_make_state_json(300.0, count_per_seg=60.0, speed_kph=85.0)), encoding="utf-8")
    out_json, out_csv = tmp / "action_reg.json", tmp / "action_reg.csv"
    proc = _run_adapter([
        "--state-json", str(state),
        "--out-action-json", str(out_json),
        "--out-action-csv", str(out_csv),
        "--controller", "stackelberg",
        "--repo-root", str(REPO_ROOT),
    ], cwd=tmp)
    if proc.returncode != 0:
        failures.append(f"stackelberg returncode={proc.returncode}\nstdout={proc.stdout[-2000:]}\nstderr={proc.stderr[-2000:]}")
        return failures
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    meta = payload.get("metadata", {})
    _check(meta.get("controller_status") == "ok",
           f"stackelberg controller_status={meta.get('controller_status')} error={meta.get('controller_error')}", failures)
    _check(meta.get("controller") == "StackelbergMPCController",
           f"stackelberg controller={meta.get('controller')}", failures)
    # flagship 전용 사이드카/메타데이터가 기존 모드에 새지 않아야 한다.
    _check(not (tmp / ada.FLAGSHIP_RUNTIME_FILENAME).exists() or "flagship" not in json.dumps(meta),
           "stackelberg 모드에 flagship 흔적 유출", failures)
    _check("flagship_ms_friction" not in meta, "stackelberg metadata에 flagship 키 유출", failures)
    return failures


def main() -> int:
    results: list[tuple[str, list[str]]] = []
    tmp = Path(tempfile.mkdtemp(prefix="pstack_flagship_test_"))
    reg_tmp = Path(tempfile.mkdtemp(prefix="pstack_flagship_reg_"))
    tests = [
        ("flagship_configuration", lambda: test_flagship_configuration()),
        ("ms_adapt_latch", lambda: test_ms_adapt_latch()),
        ("flagship_smoke", lambda: test_flagship_smoke(tmp)),
        ("stackelberg_regression", lambda: test_stackelberg_regression(reg_tmp)),
    ]
    for name, fn in tests:
        try:
            failures = fn()
        except Exception:
            failures = [f"예외 발생:\n{traceback.format_exc()}"]
        results.append((name, failures))
        status = "PASS" if not failures else "FAIL"
        print(f"[{status}] {name}")
        for failure in failures:
            print(f"    - {failure}")
    total_fail = sum(1 for _, f in results if f)
    print(f"\n{len(results) - total_fail}/{len(results)} PASS (작업 디렉터리: {tmp}, {reg_tmp})")
    return 1 if total_fail else 0


if __name__ == "__main__":
    sys.exit(main())
