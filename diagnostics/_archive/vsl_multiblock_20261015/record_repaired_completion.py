"""Record verified native and cached-analysis completion; launches nothing."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "native_analysis_repaired_20261016"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    plan = read(ROOT / "plan.json")
    summary = read(ROOT / "summary.json")
    closure = read(OUT / "runtime_closure.json")
    native = read(OUT / "summary.json")
    horizon = read(OUT / "horizon_summary.json")
    assert closure["all_owned_processes_closed"] and closure["wrapper_closed"]
    assert closure["owner_exit_code"] == 0 and closure["normal_native_end_sec"] == 2700
    assert native["existing_forecast_comparison_qualified"] and native["counterfactual_valid"]
    assert horizon["new_forecasts"] == 0 and horizon["new_fzp_scans"] == 0
    stamp = datetime.now(timezone.utc).isoformat()
    receipt = {
        "completed_utc": stamp,
        "status": "replacement_native_and_qualified_cached_comparison_complete",
        "additional_native_attempts": 1,
        "prior_failed_native_attempts_preserved": 1,
        "automatic_native_retries": 0,
        "normal_sim_done_sec": 2700,
        "owner_exit_code": 0,
        "all_owned_processes_closed": True,
        "native_execution_passed": True,
        "strict_lsa_coverage_passed": False,
        "approved_ldp_substitute_preserved": True,
        "forecast_comparison_qualified": True,
        "successful_native_analyses": 1,
        "cached_horizon_summaries": 1,
        "analysis_launch_lifecycle_recovery": str(OUT / "analysis_execution_recovery.json"),
        "new_predictions_this_completion": 0,
        "new_production_or_coefficient_edits": 0,
        "comparison450": horizon["comparisons"]["selected"]["450"],
        "interpretation": "Near-neutral conditional native response; model overpredicts late east-mainline outflow/inventory penalty. No robust VSL benefit or8100 policy gain established.",
        "next_offline_focus": "Identify east-mainline VSL outflow/offramp/inventory recovery mismatch against existing independent cases before a localized correction; native internal flow is unavailable in this cache. No blanket gain factor or unsupported coefficient change.",
        "goal_status_observed": "blocked",
        "goal_complete": False,
        "monitor_action": "pause_after_result_report",
        "report": str(OUT / "RESULTS.md"),
        "artifact_pins": {
            str(OUT / name): hashlib.sha256((OUT / name).read_bytes()).hexdigest()
            for name in ["runtime_closure.json", "summary.json", "horizon_summary.json", "component_comparison.json", "analysis_exit.json", "horizon_exit.json", "RESULTS.md"]
        },
    }
    write(OUT / "completion_receipt.json", receipt)
    plan["status"] = receipt["status"]
    plan["updated_utc"] = stamp
    plan["app_goal_registration"] = "Goal exists; get_goal on2026-10-16 returned BLOCKED and incomplete. Explicit replacement authorization was executed; do not mark overall calibration complete."
    plan["app_goal_status"] = "blocked"
    plan["next"] = receipt["next_offline_focus"] + " Finite native result is complete; pause vissim-2. Do not repeat analyses, predictions, optimizer, native, freezer, or push."
    plan["completed"]["new_native_runs"] = 2
    plan["completed"]["new_native_runs_definition"] = "One failed20261015 attempt plus one explicitly approved20261016 replacement, normal_completions1; automatic retries0."
    plan["completed"]["normal_native_completions"] = 1
    plan["completed"]["qualified_native_analyses"] = 1
    stage = plan["next_stage"]
    stage["status"] = receipt["status"]
    stage["postprocess"]["status"] = "completed_qualified_once"
    stage["postprocess"]["analysis_lifecycle_recovery"] = receipt["analysis_launch_lifecycle_recovery"]
    stage["cached_horizon_postprocess"]["status"] = "completed_once_from_cache"
    stage["completion_receipt"] = str(OUT / "completion_receipt.json")
    stage["result_report"] = receipt["report"]
    stage["remaining_native_budget"] = 0
    stage["updated_utc"] = stamp
    plan["result_20261016"] = {key: receipt[key] for key in ["comparison450", "interpretation", "next_offline_focus", "new_production_or_coefficient_edits", "goal_complete"]}
    write(ROOT / "plan.json", plan)
    summary["status"] = receipt["status"]
    summary["updated_utc"] = stamp
    summary["native_runs"] = 2
    summary["normal_native_completions"] = 1
    summary["native_run_accounting"] = "One failed attempt plus one explicitly approved replacement; zero automatic retries."
    summary["app_goal_status"] = "blocked"
    summary["metadata_repair"]["replacement_native_authorization"] = "Explicitly approved2026-10-16; replacement1 consumed and normal2700 completed."
    summary["offline_vsl_transport_audit"]["replacement_native_authorization"] = "Explicit approval received and consumed; no further native budget."
    summary["authorized_replacement_20261016"].update({
        "status": receipt["status"],
        "completion_receipt": str(OUT / "completion_receipt.json"),
        "result_report": receipt["report"],
        "normal_sim_done_sec": 2700,
        "all_owned_processes_closed": True,
    })
    summary["conditional_native_result_20261016"] = plan["result_20261016"]
    write(ROOT / "summary.json", summary)
    readme = ROOT / "README.md"
    marker = "## 2026-10-16 수정본 정상 완료 및 조건부 VSL 비교"
    if marker not in readme.read_text(encoding="utf-8-sig"):
        with readme.open("a", encoding="utf-8") as stream:
            stream.write("\n\n" + marker + "\n\n")
            stream.write("추가 승인된 1회는 SIM_DONE2700/runner exit0이며 wrapper 포함 13개 소유 기록 종료를 확인했다. 명령 19회 모두 성공, 실패·유지 0회다. 이전 실패 자료와 STOP을 보존했고 자동 재시도는 없다. 실제 DSD 및 승인된 LDP 검증을 통과했으나 LSA coverage 누락은 유지했다. 입력 15시각·초기 미시상태·전체 prefix 일치로 기존 예측 대조 자격을 통과했다.\n\n")
            stream.write("두 구역90의450초 Ω TTT는507.233169대·시간,110기준507.279002 대비−0.045833(약−0.009%)로 거의 중립이다. 모델은+1.111329 손해를 예측했다.150/300초 실제 차이는+0.041556/+0.138722다. 동측 본선의 모델 유출·진출 감소와 재고 회복 반응이 우선 점검 대상이며, 실제 내부 유량이 없는 현재 캐시로 특정 계수의 결함을 확정하지 않는다. 작은 부호를 맞추는 보정/생산 계수 변경은 하지 않았다.\n\n")
            stream.write("분석 detached 프로세스의 도구 부모 종료에 따른 정리를 최소 생명주기 검사로 확인해 부모 대기 방식으로 실행했다. 성공한 native 분석1회/캐시 horizon 요약1회, 새 예측0이다. 상세 영역·외부대기·유출·잔여와 한계는 [결과 보고서](native_analysis_repaired_20261016/RESULTS.md), 정본 완료는 native_analysis_repaired_20261016/completion_receipt.json이다. 이 문단이 앞선 진행/승인 대기 상태보다 우선한다. 이번 유한 자동확인은 결과 보고 후PAUSED, 앱 목표의 실제 상태는BLOCKED·미완료다.\n")
    print(json.dumps({"status": plan["status"], "report": receipt["report"], "native_attempts": 2, "normal_completions": 1, "goal_complete": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
